/**
 * Admin Vehicles API Route
 * Handles CRUD operations for vehicles (admin only)
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

const createVehicleSchema = z.object({
    name: z.string().min(1, "Name is required"),
    type: z.string().min(1, "Type is required"),
    plateNumber: z.string().optional(),
    wheelchairCapacity: z.number().int().min(0).optional(),
    seatingCapacity: z.number().int().min(0).optional(),
    cooldownMinutes: z.number().int().min(0).max(60).optional(),
    status: z.string().optional(),
});

const updateVehicleSchema = z.object({
    id: z.string().min(1, "Vehicle ID is required"),
    name: z.string().optional(),
    type: z.string().optional(),
    plateNumber: z.string().optional(),
    plate_number: z.string().optional(),
    wheelchairCapacity: z.number().int().min(0).optional(),
    wheelchair_capacity: z.number().int().min(0).optional(),
    seatingCapacity: z.number().int().min(0).optional(),
    seating_capacity: z.number().int().min(0).optional(),
    cooldownMinutes: z.number().int().min(0).max(60).optional(),
    cooldown_minutes: z.number().int().min(0).max(60).optional(),
    status: z.string().optional(),
});

// GET /api/admin/vehicles - Get all vehicles
export async function GET(request: NextRequest) {
    try {
        await requireAdmin(request);

        const adminClient = getSupabaseAdmin();
        const { data, error } = await adminClient
            .from("vehicles")
            .select("*")
            .order("created_at", { ascending: false });

        if (error) {
            return createErrorResponse(error.message, 500);
        }

        return createSuccessResponse(data);
    } catch (error) {
        return handleApiError(error);
    }
}

// POST /api/admin/vehicles - Create new vehicle
export async function POST(request: NextRequest) {
    try {
        await requireAdmin(request);

        const rawBody = await request.json();
        const parseResult = createVehicleSchema.safeParse(rawBody);
        if (!parseResult.success) {
            return createErrorResponse(parseResult.error.errors[0].message, 400);
        }

        const { name, type, plateNumber, wheelchairCapacity, seatingCapacity, cooldownMinutes, status } = parseResult.data;

        // Validate at least one capacity is > 0
        if ((wheelchairCapacity ?? 0) <= 0 && (seatingCapacity ?? 0) <= 0) {
            return createErrorResponse("At least one capacity (wheelchair or seating) must be greater than 0", 400);
        }

        const cooldown = cooldownMinutes ?? 10;

        const adminClient = getSupabaseAdmin();
        const { data, error } = await adminClient
            .from("vehicles")
            .insert({
                name,
                type,
                plate_number: plateNumber,
                wheelchair_capacity: wheelchairCapacity ?? 0,
                seating_capacity: seatingCapacity ?? 0,
                cooldown_minutes: cooldown,
                status: status ?? "active",
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
            } as never)
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

// PUT /api/admin/vehicles - Update vehicle
export async function PUT(request: NextRequest) {
    try {
        await requireAdmin(request);

        const rawBody = await request.json();
        const parseResult = updateVehicleSchema.safeParse(rawBody);
        if (!parseResult.success) {
            return createErrorResponse(parseResult.error.errors[0].message, 400);
        }

        const { id, ...updates } = parseResult.data;

        // Validate at least one capacity is > 0 if capacities are being updated
        const newWheelchairCapacity = updates.wheelchairCapacity !== undefined ? updates.wheelchairCapacity : updates.wheelchair_capacity;
        const newSeatingCapacity = updates.seatingCapacity !== undefined ? updates.seatingCapacity : updates.seating_capacity;
        
        if (newWheelchairCapacity !== undefined && newSeatingCapacity !== undefined) {
            if (newWheelchairCapacity <= 0 && newSeatingCapacity <= 0) {
                return createErrorResponse("At least one capacity (wheelchair or seating) must be greater than 0", 400);
            }
        }

        // Validate cooldown range if provided
        const cooldownValue = updates.cooldownMinutes ?? updates.cooldown_minutes;
        if (cooldownValue !== undefined && (cooldownValue < 0 || cooldownValue > 60)) {
            return createErrorResponse("Cooldown minutes must be between 0 and 60", 400);
        }

        const adminClient = getSupabaseAdmin();

        // Convert camelCase to snake_case for database
        const dbUpdates: Record<string, unknown> = {
            updated_at: new Date().toISOString(),
        };

        if (updates.name) dbUpdates.name = updates.name;
        if (updates.type) dbUpdates.type = updates.type;
        if (updates.plateNumber !== undefined) dbUpdates.plate_number = updates.plateNumber;
        if (updates.wheelchairCapacity !== undefined) dbUpdates.wheelchair_capacity = updates.wheelchairCapacity;
        if (updates.seatingCapacity !== undefined) dbUpdates.seating_capacity = updates.seatingCapacity;
        if (updates.cooldownMinutes !== undefined) dbUpdates.cooldown_minutes = updates.cooldownMinutes;
        if (updates.status) dbUpdates.status = updates.status;

        const { data, error } = await adminClient
            .from("vehicles")
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

// DELETE /api/admin/vehicles - Delete vehicle
export async function DELETE(request: NextRequest) {
    try {
        await requireAdmin(request);

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
    } catch (error) {
        return handleApiError(error);
    }
}
