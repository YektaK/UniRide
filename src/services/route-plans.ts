/**
 * Route Plans Service
 * Handles route plan API calls from frontend
 */

import type { VehicleRoute, OptimizationResult } from "@/services/optimizer-service";
import { getAuthToken } from "@/lib/admin-api";
import { buildSolverProvenance, type SolverProvenance } from "@/services/solver-provenance";

export interface RoutePlan {
    id: string;
    plan_date: string;
    direction: 'pickup' | 'dropoff';
    algorithm_used: string;
    clustering_used: string;
    total_vehicles: number;
    total_duration_minutes: number;
    execution_time_seconds?: number;
    status: 'draft' | 'confirmed' | 'active' | 'completed' | 'cancelled';
    routes: VehicleRoute[] | Record<string, unknown>[];
    student_count: number;
    driver_assignments?: Record<string, unknown>[];
    notes?: string;
    created_by?: string;
    /** What the optimizer reported when the plan was calculated; null/absent = unknown (old plans). */
    solver_provenance?: SolverProvenance | null;
    created_at: string;
    confirmed_at?: string;
    completed_at?: string;
}

export interface SaveRoutePlanRequest {
    planDate: string;
    direction: 'pickup' | 'dropoff';
    algorithmUsed: string;
    clusteringUsed?: string;
    totalVehicles: number;
    totalDurationMinutes: number;
    executionTimeSeconds?: number;
    routes: VehicleRoute[] | Record<string, unknown>[];
    studentCount: number;
    notes?: string;
    /** Only the fields the optimizer reported; absent when it reported none. */
    solverProvenance?: SolverProvenance;
}

export interface UpdateRoutePlanRequest {
    id: string;
    status?: 'draft' | 'confirmed' | 'active' | 'completed' | 'cancelled';
    driverAssignments?: Record<string, unknown>[];
    notes?: string;
}

export async function saveRoutePlan(plan: SaveRoutePlanRequest): Promise<RoutePlan> {
    const token = await getAuthToken();
    if (!token) throw new Error("Not authenticated");

    const response = await fetch('/api/route-plans', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(plan),
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || 'Failed to save route plan');
    }

    return data.data;
}

export async function getRoutePlans(filters?: {
    date?: string;
    status?: string;
    direction?: string;
}): Promise<RoutePlan[]> {
    const token = await getAuthToken();
    if (!token) throw new Error("Not authenticated");

    const params = new URLSearchParams();

    if (filters?.date) {
        params.set('date', filters.date);
    }
    if (filters?.status) {
        params.set('status', filters.status);
    }
    if (filters?.direction) {
        params.set('direction', filters.direction);
    }

    const queryString = params.toString();
    const url = queryString ? `/api/route-plans?${queryString}` : '/api/route-plans';

    const response = await fetch(url, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
        },
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || 'Failed to fetch route plans');
    }

    return data.data;
}

export async function updateRoutePlan(update: UpdateRoutePlanRequest): Promise<RoutePlan> {
    const token = await getAuthToken();
    if (!token) throw new Error("Not authenticated");

    const response = await fetch('/api/route-plans', {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(update),
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || 'Failed to update route plan');
    }

    return data.data;
}

export async function deleteRoutePlan(id: string): Promise<void> {
    const token = await getAuthToken();
    if (!token) throw new Error("Not authenticated");

    const response = await fetch(`/api/route-plans?id=${id}`, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${token}`,
        },
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || 'Failed to delete route plan');
    }
}

type CalculationResult = OptimizationResult & { assignments?: Array<Record<string, unknown>>; meta?: Record<string, unknown>; requiredVehicles?: number; totalDuration?: number };

/**
 * M26: when the optimizer served a fallback instead of the selected solver, the algorithm that
 * actually ran is what gets persisted (and shown), never the UI-selected strategy.
 */
export function resolvePersistedAlgorithm(optimizationResult: CalculationResult, selectedAlgorithm: string): string {
    const meta = optimizationResult.meta as { algorithmUsed?: unknown; fallbackReason?: unknown } | undefined;
    const fallbackReason = optimizationResult.fallback_reason ?? meta?.fallbackReason;
    const metaAlgorithm = typeof meta?.algorithmUsed === "string" && meta.algorithmUsed ? meta.algorithmUsed : undefined;
    return fallbackReason
        ? (metaAlgorithm ?? optimizationResult.algorithm_used ?? "greedy_fallback")
        : selectedAlgorithm;
}

export function formatRoutePlanForSave(
    optimizationResult: CalculationResult,
    planDate: string,
    requestedDirection: 'pickup' | 'dropoff',
    algorithmUsed: string,
    clusteringUsed: string
): SaveRoutePlanRequest {
    const returned = optimizationResult.direction;
    if (returned !== 'pickup' && returned !== 'dropoff') {
        throw new Error("Calculation result has no valid direction; save is blocked");
    }
    if (returned !== requestedDirection) {
        throw new Error("Calculation result direction does not match the requested direction");
    }

    const persistedAlgorithm = resolvePersistedAlgorithm(optimizationResult, algorithmUsed);

    const routes = (optimizationResult.routes ?? optimizationResult.assignments ?? []) as VehicleRoute[] | Record<string, unknown>[];

    function countStudents(route: VehicleRoute | Record<string, unknown>): number {
        if (Array.isArray((route as VehicleRoute).student_ids)) {
            return (route as VehicleRoute).student_ids.length;
        }
        const r = route as Record<string, unknown>;
        const students = r.students as unknown[] | undefined;
        const studentIds = r.studentIds as unknown[] | undefined;
        return students?.length ?? studentIds?.length ?? 0;
    }

    const studentCount = routes.reduce((sum: number, route) => sum + countStudents(route), 0);

    const solverProvenance = buildSolverProvenance(optimizationResult, persistedAlgorithm);

    return {
        planDate,
        direction: returned,
        algorithmUsed: persistedAlgorithm,
        clusteringUsed,
        totalVehicles: optimizationResult.requiredVehicles ?? optimizationResult.total_vehicles ?? routes.length,
        totalDurationMinutes: optimizationResult.totalDuration ?? optimizationResult.total_duration_minutes ?? 0,
        executionTimeSeconds: optimizationResult.execution_time_seconds,
        routes,
        studentCount,
        ...(solverProvenance ? { solverProvenance } : {}),
    };
}
