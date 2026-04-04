/**
 * Route Plans Service
 * Handles route plan API calls from frontend
 */

import { createClient } from "@/lib/supabase";

const SUPABASEAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

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
    routes: any;
    student_count: number;
    driver_assignments?: any[];
    notes?: string;
    created_by?: string;
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
    routes: any;
    studentCount: number;
    notes?: string;
}

export interface UpdateRoutePlanRequest {
    id: string;
    status?: 'draft' | 'confirmed' | 'active' | 'completed' | 'cancelled';
    driverAssignments?: any;
    notes?: string;
}

export async function saveRoutePlan(plan: SaveRoutePlanRequest): Promise<RoutePlan> {
    const response = await fetch('/api/route-plans', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
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
        },
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || 'Failed to fetch route plans');
    }

    return data.data;
}

export async function updateRoutePlan(update: UpdateRoutePlanRequest): Promise<RoutePlan> {
    const response = await fetch('/api/route-plans', {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
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
    const response = await fetch(`/api/route-plans?id=${id}`, {
        method: 'DELETE',
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || 'Failed to delete route plan');
    }
}

export function formatRoutePlanForSave(
    optimizationResult: any,
    planDate: string,
    direction: 'pickup' | 'dropoff',
    algorithmUsed: string,
    clusteringUsed: string
): SaveRoutePlanRequest {
    const routes = optimizationResult.routes || optimizationResult.assignments || [];
    const studentCount = routes.reduce(
        (sum: number, route: any) => sum + (route.students?.length || route.studentIds?.length || 0),
        0
    );

    return {
        planDate,
        direction,
        algorithmUsed,
        clusteringUsed,
        totalVehicles: optimizationResult.requiredVehicles || routes.length,
        totalDurationMinutes: optimizationResult.totalDuration || 0,
        executionTimeSeconds: optimizationResult.executionTime || optimizationResult.meta?.executionTime,
        routes,
        studentCount,
    };
}