import { NextResponse } from "next/server";
import { z } from "zod";
import { createClient } from "@supabase/supabase-js";
import { requireRole } from "@/lib/admin-auth";

// Create Supabase client with service role for admin operations
const supabaseAdmin = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
);

const updateAssignmentSchema = z.object({
    id: z.string().min(1, "Assignment ID is required"),
    status: z.enum(["in_progress", "completed"]),
});

export async function GET(request: Request) {
    try {
        const user = await requireRole(request, ["driver", "admin"]);

        // Get route assignments for this driver
        let query = supabaseAdmin
            .from("route_assignments")
            .select("*")
            .order("pickup_time", { ascending: true });

        // If driver, filter by their ID only
        if (user.role === "driver") {
            query = query.eq("driver_id", user.id);
        }

        const { data, error } = await query;

        if (error) {
            console.error("Error fetching assignments:", error);
            return NextResponse.json({ error: error.message }, { status: 500 });
        }

        // Transform snake_case to camelCase
        const assignments = (data ?? []).map((assignment) => ({
            id: assignment.id,
            date: assignment.date,
            vehicleId: assignment.vehicle_id,
            driverId: assignment.driver_id,
            routeId: assignment.route_id,
            studentIds: assignment.student_ids ?? [],
            pickupTime: assignment.pickup_time,
            estimatedDropoffTime: assignment.estimated_dropoff_time,
            status: assignment.status,
            createdAt: assignment.created_at,
            updatedAt: assignment.updated_at,
        }));

        return NextResponse.json(assignments);
    } catch (error: unknown) {
        console.error("Driver assignments API error:", error);
        return NextResponse.json({ error: "Internal server error" }, { status: 500 });
    }
}

export async function PUT(request: Request) {
    try {
        const user = await requireRole(request, ["driver"]);

        const rawBody = await request.json();
        const parseResult = updateAssignmentSchema.safeParse(rawBody);
        if (!parseResult.success) {
            return NextResponse.json(
                { error: "Invalid request body", details: parseResult.error.flatten() },
                { status: 400 }
            );
        }

        const { id, status } = parseResult.data;

        // Drivers can only update status of their own assignments
        const { data: existingAssignment } = await supabaseAdmin
            .from("route_assignments")
            .select("driver_id")
            .eq("id", id)
            .single();

        if (!existingAssignment || existingAssignment.driver_id !== user.id) {
            return NextResponse.json({ error: "Assignment not found or not authorized" }, { status: 404 });
        }

        const { data, error } = await supabaseAdmin
            .from("route_assignments")
            .update({
                status,
                updated_at: new Date().toISOString()
            })
            .eq("id", id)
            .select()
            .single();

        if (error) {
            console.error("Error updating assignment:", error);
            return NextResponse.json({ error: error.message }, { status: 500 });
        }

        return NextResponse.json({
            id: data.id,
            status: data.status,
            message: "Assignment updated successfully"
        });
    } catch (error: unknown) {
        console.error("Driver assignments API error:", error);
        return NextResponse.json({ error: "Internal server error" }, { status: 500 });
    }
}
