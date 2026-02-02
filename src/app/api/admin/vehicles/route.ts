/**
 * Admin Vehicles API Route
 * Handles CRUD operations for vehicles (admin only)
 */

import { NextRequest } from "next/server";
import { getSupabaseAdmin } from "@/lib/supabase-admin";
import {
    requireAdmin,
    createErrorResponse,
    createSuccessResponse,
} from "@/lib/admin-auth";

// GET /api/admin/vehicles - Get all vehicles
export async function GET(request: NextRequest) {
    try {
        await requireAdmin();

        const adminClient = getSupabaseAdmin();
        const { data, error } = await adminClient
            .from("vehicles")
            .select("*")
            .order("created_at", { ascending: false });

        if (error) {
            return createErrorResponse(error.message, 500);
        }

        return createSuccessResponse(data);
    } catch (error: any) {
        if (error.message.includes("Unauthorized")) {
            return createErrorResponse(error.message, 401);
        }
        if (error.message.includes("Forbidden")) {
            return createErrorResponse(error.message, 403);
        }
        return createErrorResponse(error.message, 500);
    }
}

// POST /api/admin/vehicles - Create new vehicle
export async function POST(request: NextRequest) {
    try {
        await requireAdmin();

        const body = await request.json();
        const { name, type, plateNumber, wheelchairCapacity, seatingCapacity, status } = body;

        if (!name || !type) {
            return createErrorResponse("Name and type are required", 400);
        }

        const adminClient = getSupabaseAdmin();
        const { data, error } = await adminClient
            .from("vehicles")
            .insert({
                name,
                type,
                plate_number: plateNumber,
                wheelchair_capacity: wheelchairCapacity || 0,
                seating_capacity: seatingCapacity || 0,
                status: status || "active",
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
            })
            .select()
            .single();

        if (error) {
            return createErrorResponse(error.message, 500);
        }

        return createSuccessResponse(data, 201);
    } catch (error: any) {
        if (error.message.includes("Unauthorized")) {
            return createErrorResponse(error.message, 401);
        }
        if (error.message.includes("Forbidden")) {
            return createErrorResponse(error.message, 403);
        }
        return createErrorResponse(error.message, 500);
    }
}

// PUT /api/admin/vehicles - Update vehicle
export async function PUT(request: NextRequest) {
    try {
        await requireAdmin();

        const body = await request.json();
        const { id, ...updates } = body;

        if (!id) {
            return createErrorResponse("Vehicle ID is required", 400);
        }

        const adminClient = getSupabaseAdmin();

        // Convert camelCase to snake_case for database
        const dbUpdates: any = {
            updated_at: new Date().toISOString(),
        };

        if (updates.name) dbUpdates.name = updates.name;
        if (updates.type) dbUpdates.type = updates.type;
        if (updates.plateNumber !== undefined) dbUpdates.plate_number = updates.plateNumber;
        if (updates.wheelchairCapacity !== undefined) dbUpdates.wheelchair_capacity = updates.wheelchairCapacity;
        if (updates.seatingCapacity !== undefined) dbUpdates.seating_capacity = updates.seatingCapacity;
        if (updates.status) dbUpdates.status = updates.status;

        const { data, error } = await adminClient
            .from("vehicles")
            .update(dbUpdates)
            .eq("id", id)
            .select()
            .single();

        if (error) {
            return createErrorResponse(error.message, 500);
        }

        return createSuccessResponse(data);
    } catch (error: any) {
        if (error.message.includes("Unauthorized")) {
            return createErrorResponse(error.message, 401);
        }
        if (error.message.includes("Forbidden")) {
            return createErrorResponse(error.message, 403);
        }
        return createErrorResponse(error.message, 500);
    }
}

// DELETE /api/admin/vehicles - Delete vehicle
export async function DELETE(request: NextRequest) {
    try {
        await requireAdmin();

        const { searchParams } = new URL(request.url);
        const id = searchParams.get("id");

        if (!id) {
            return createErrorResponse("Vehicle ID is required", 400);
        }

        const adminClient = getSupabaseAdmin();
        const { error } = await adminClient
            .from("vehicles")
            .delete()
            .eq("id", id);

        if (error) {
            return createErrorResponse(error.message, 500);
        }

        return createSuccessResponse({ message: "Vehicle deleted successfully" });
    } catch (error: any) {
        if (error.message.includes("Unauthorized")) {
            return createErrorResponse(error.message, 401);
        }
        if (error.message.includes("Forbidden")) {
            return createErrorResponse(error.message, 403);
        }
        return createErrorResponse(error.message, 500);
    }
}
