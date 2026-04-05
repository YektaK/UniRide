/**
 * Admin Ride Requests API Route
 * Handles ride request management (admin only)
 */

import { NextRequest } from "next/server";
import { z } from "zod";
import { getSupabaseAdmin } from "@/lib/supabase-admin";
import {
    requireAdmin,
    createErrorResponse,
    createSuccessResponse,
    handleApiError,
} from "@/lib/admin-auth";

const updateRideRequestSchema = z.object({
    id: z.string().min(1, "Request ID is required"),
    status: z.string().optional(),
    vehicleId: z.string().nullable().optional(),
    notes: z.string().nullable().optional(),
});

// GET /api/admin/ride-requests - Get all ride requests
export async function GET(request: NextRequest) {
    try {
        await requireAdmin();

        const { searchParams } = new URL(request.url);
        const status = searchParams.get("status");
        const userId = searchParams.get("userId");

        const adminClient = getSupabaseAdmin();
        let query = adminClient
            .from("ride_requests")
            .select("*, users(name, email, student_number)")
            .order("created_at", { ascending: false });

        if (status) {
            query = query.eq("status", status);
        }
        if (userId) {
            query = query.eq("user_id", userId);
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

// PUT /api/admin/ride-requests - Update ride request status
export async function PUT(request: NextRequest) {
    try {
        await requireAdmin();

        const rawBody = await request.json();
        const parseResult = updateRideRequestSchema.safeParse(rawBody);
        if (!parseResult.success) {
            return createErrorResponse(parseResult.error.errors[0].message, 400);
        }

        const { id, status, vehicleId, notes } = parseResult.data;

        const adminClient = getSupabaseAdmin();

        const dbUpdates: Record<string, unknown> = {
            updated_at: new Date().toISOString(),
        };

        if (status) dbUpdates.status = status;
        if (vehicleId !== undefined) dbUpdates.vehicle_id = vehicleId;
        if (notes !== undefined) dbUpdates.notes = notes;

        const { data, error } = await adminClient
            .from("ride_requests")
            .update(dbUpdates as never)
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

// DELETE /api/admin/ride-requests - Delete ride request
export async function DELETE(request: NextRequest) {
    try {
        await requireAdmin();

        const { searchParams } = new URL(request.url);
        const id = searchParams.get("id");

        if (!id) {
            return createErrorResponse("Request ID is required", 400);
        }

        const adminClient = getSupabaseAdmin();
        const { error } = await adminClient
            .from("ride_requests")
            .delete()
            .eq("id", id);

        if (error) {
            return createErrorResponse(error.message, 500);
        }

        return createSuccessResponse({ message: "Ride request deleted successfully" });
    } catch (error) {
        return handleApiError(error);
    }
}
