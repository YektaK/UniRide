/**
 * Route Plans API Route
 * Handles route plan CRUD operations
 * POST /api/route-plans - Create new plan
 * GET /api/route-plans - List plans (with filters)
 * PATCH /api/route-plans - Update plan status
 */

import { NextRequest } from "next/server";
import { getSupabaseAdmin } from "@/lib/supabase-admin";
import {
    requireAdmin,
    createErrorResponse,
    createSuccessResponse,
    handleApiError,
} from "@/lib/admin-auth";

import type { VehicleRoute } from "@/services/optimizer-service";

interface RoutePlanRequest {
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
}

interface RoutePlanUpdate {
    id: string;
    status?: 'draft' | 'confirmed' | 'active' | 'completed' | 'cancelled';
    driverAssignments?: Record<string, unknown>[];
    notes?: string;
}

// POST /api/route-plans - Create new route plan
export async function POST(request: NextRequest) {
    try {
        await requireAdmin();

        const body = await request.json() as RoutePlanRequest;
        const {
            planDate,
            direction,
            algorithmUsed,
            clusteringUsed = 'kmeans',
            totalVehicles,
            totalDurationMinutes,
            executionTimeSeconds,
            routes,
            studentCount,
            notes
        } = body;

        // Validation
        if (!planDate || !direction || !algorithmUsed || !routes) {
            return createErrorResponse("Missing required fields", 400);
        }

        if (!['pickup', 'dropoff'].includes(direction)) {
            return createErrorResponse("Invalid direction", 400);
        }

        const adminClient = getSupabaseAdmin();

        // Get authenticated user
        const { data: { user } } = await adminClient.auth.getUser();

        const { data, error } = await adminClient
            .from("route_plans")
            .insert({
                plan_date: planDate,
                direction,
                algorithm_used: algorithmUsed,
                clustering_used: clusteringUsed,
                total_vehicles: totalVehicles,
                total_duration_minutes: totalDurationMinutes,
                execution_time_seconds: executionTimeSeconds,
                routes,
                student_count: studentCount,
                notes,
                status: 'draft',
                created_by: user?.id,
            })
            .select()
            .single();

        if (error) {
            return createErrorResponse(error.message, 500);
        }

        return createSuccessResponse(data, 201);
    } catch (error) {
        return handleApiError(error);
    }
}

// GET /api/route-plans - List route plans
export async function GET(request: NextRequest) {
    try {
        await requireAdmin();

        const { searchParams } = new URL(request.url);
        const planDate = searchParams.get("date");
        const status = searchParams.get("status");
        const direction = searchParams.get("direction");

        const adminClient = getSupabaseAdmin();
        let query = adminClient
            .from("route_plans")
            .select("*")
            .order("created_at", { ascending: false });

        if (planDate) {
            query = query.eq("plan_date", planDate);
        }
        if (status) {
            query = query.eq("status", status);
        }
        if (direction) {
            query = query.eq("direction", direction);
        }

        const { data, error } = await query;

        if (error) {
            return createErrorResponse(error.message, 500);
        }

        return createSuccessResponse(data);
    } catch (error) {
        return handleApiError(error);
    }
}

// PATCH /api/route-plans - Update route plan
export async function PATCH(request: NextRequest) {
    try {
        await requireAdmin();

        const body = await request.json() as RoutePlanUpdate;
        const { id, status, driverAssignments, notes } = body;

        if (!id) {
            return createErrorResponse("Plan ID is required", 400);
        }

        const adminClient = getSupabaseAdmin();

        const dbUpdates: Record<string, unknown> = {
            updated_at: new Date().toISOString(),
        };

        if (status) {
            if (!['draft', 'confirmed', 'active', 'completed', 'cancelled'].includes(status)) {
                return createErrorResponse("Invalid status", 400);
            }
            dbUpdates.status = status;

            // Set confirmed_at or completed_at
            if (status === 'confirmed') {
                dbUpdates.confirmed_at = new Date().toISOString();
            } else if (status === 'completed') {
                dbUpdates.completed_at = new Date().toISOString();
            }
        }
        if (driverAssignments !== undefined) {
            dbUpdates.driver_assignments = driverAssignments;
        }
        if (notes !== undefined) {
            dbUpdates.notes = notes;
        }

        const { data, error } = await adminClient
            .from("route_plans")
            .update(dbUpdates)
            .eq("id", id)
            .select()
            .single();

        if (error) {
            return createErrorResponse(error.message, 500);
        }

        return createSuccessResponse(data);
    } catch (error) {
        return handleApiError(error);
    }
}

// DELETE /api/route-plans - Delete route plan
export async function DELETE(request: NextRequest) {
    try {
        await requireAdmin();

        const { searchParams } = new URL(request.url);
        const id = searchParams.get("id");

        if (!id) {
            return createErrorResponse("Plan ID is required", 400);
        }

        const adminClient = getSupabaseAdmin();
        const { error } = await adminClient
            .from("route_plans")
            .delete()
            .eq("id", id);

        if (error) {
            return createErrorResponse(error.message, 500);
        }

        return createSuccessResponse({ message: "Route plan deleted successfully" });
    } catch (error) {
        return handleApiError(error);
    }
}