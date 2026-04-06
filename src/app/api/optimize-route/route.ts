/**
 * Route Optimization API
 * Calls Python Optimization API
 */

import { NextResponse } from "next/server";
import { headers } from "next/headers";
import { createClient } from "@supabase/supabase-js";
import { z } from "zod";
import { 
    optimizeRoutes, 
    getAvailableStrategies,
    type StudentForOptimization, 
    type Depot 
} from "@/services/optimizer-service";

// Create Supabase client
const supabaseAdmin = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
);

const studentSchema = z.object({
    id: z.string().optional(),
    student_id: z.string().optional(),
    name: z.string().optional(),
    location_code: z.string().optional(),
    locationCode: z.string().optional(),
    coordinates: z.object({ lat: z.number(), lng: z.number() }).optional().nullable(),
    home_coordinates: z.object({ lat: z.number(), lng: z.number() }).optional().nullable(),
    disability_type: z.string().optional(),
    disabilityType: z.string().optional(),
    pickup_time: z.string().optional(),
    pickupTime: z.string().optional(),
    dropoff_time: z.string().optional(),
    dropoffTime: z.string().optional(),
});

const optimizeRouteSchema = z.object({
    students: z.array(studentSchema).min(1, "At least one student is required"),
    depot: z.object({
        id: z.string().optional(),
        lat: z.number().optional(),
        lng: z.number().optional(),
    }),
    algorithm: z.string().optional(),
    max_travel_time: z.number().optional(),
    sw_capacity: z.number().optional(),
    so_capacity: z.number().optional(),
    ga_config: z.record(z.unknown()).optional(),
    pso_config: z.record(z.unknown()).optional(),
    gwo_config: z.record(z.unknown()).optional(),
    hho_config: z.record(z.unknown()).optional(),
    direction: z.enum(["pickup", "dropoff"]).optional(),
    use_time_windows: z.boolean().optional(),
    target_time: z.string().optional(),
    time_window_size: z.number().optional(),
    offset_minutes: z.number().optional(),
});

// Create Supabase client
const supabaseAdmin = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
);

// Verify JWT and get user
async function verifyAuth(authHeader: string | null) {
    if (!authHeader?.startsWith("Bearer ")) {
        return null;
    }

    const token = authHeader.split(" ")[1];
    const { data: { user }, error } = await supabaseAdmin.auth.getUser(token);

    if (error || !user) {
        return null;
    }

    const { data: profile } = await supabaseAdmin
        .from("users")
        .select("*")
        .eq("id", user.id)
        .single();

    return profile;
}

/**
 * GET /api/optimize-route
 * Returns available algorithms
 */
export async function GET() {
    try {
        const strategies = await getAvailableStrategies();
        
        return NextResponse.json({
            strategies,
            defaultStrategy: "genetic_algorithm",
            pythonApiEnabled: true,
        });
    } catch (error: unknown) {
        return NextResponse.json({ error: error instanceof Error ? error.message : "Internal server error" }, { status: 500 });
    }
}

/**
 * POST /api/optimize-route
 * Optimizes routes using Python API
 * Supports CVRPTW with direction and time window parameters
 */
export async function POST(request: Request) {
    try {
        const headersList = await headers();
        const authHeader = headersList.get("authorization");
        const user = await verifyAuth(authHeader);

        if (!user) {
            return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
        }

        // Only admins can optimize routes
        if (user.role !== "admin") {
            return NextResponse.json({ error: "Forbidden - Admin only" }, { status: 403 });
        }

        const rawBody = await request.json();
        const parseResult = optimizeRouteSchema.safeParse(rawBody);
        if (!parseResult.success) {
            return NextResponse.json(
                { error: "Invalid request body", details: parseResult.error.flatten() },
                { status: 400 }
            );
        }

        const { 
            students, 
            depot, 
            algorithm, 
            max_travel_time, 
            sw_capacity, 
            so_capacity,
            ga_config,
            pso_config,
            gwo_config,
            hho_config,
            direction,
            use_time_windows,
            target_time,
            time_window_size,
            offset_minutes,
        } = parseResult.data;

        // Convert students to optimization format
        const optimizationStudents: StudentForOptimization[] = students.map((s) => ({
            id: s.id ?? s.student_id ?? "",
            name: s.name ?? `Öğrenci ${s.id ?? s.student_id}`,
            location_code: s.location_code ?? s.locationCode ?? "",
            coordinates: s.coordinates ?? s.home_coordinates ?? undefined,
            disability_type: (s.disability_type ?? s.disabilityType ?? "So") as "Sw" | "So",
            // CVRPTW fields
            pickup_time: s.pickup_time ?? s.pickupTime,
            dropoff_time: s.dropoff_time ?? s.dropoffTime,
        }));

        // Default depot (Doğuş Üniversitesi, Dudullu Kampüsü)
        const optimizationDepot: Depot = {
            id: depot.id || "D.Kampus",
            lat: depot.lat || 41.001,
            lng: depot.lng || 29.177,
        };

        // Call Python API with CVRPTW options
        const result = await optimizeRoutes(
            optimizationStudents,
            optimizationDepot,
            {
                algorithm: (algorithm ?? "genetic_algorithm") as import("@/services/optimizer-service").OptimizationOptions["algorithm"],
                max_travel_time: max_travel_time ?? 120,
                sw_capacity: sw_capacity ?? 4,
                so_capacity: so_capacity ?? 5,
                ga_config: ga_config as import("@/services/optimizer-service").OptimizationOptions["ga_config"],
                pso_config: pso_config as import("@/services/optimizer-service").OptimizationOptions["pso_config"],
                gwo_config: gwo_config as import("@/services/optimizer-service").OptimizationOptions["gwo_config"],
                hho_config: hho_config as import("@/services/optimizer-service").OptimizationOptions["hho_config"],
                // CVRPTW options
                direction: direction ?? "pickup",
                use_time_windows: use_time_windows ?? false,
                target_time,
                time_window_size,
                offset_minutes,
            }
        );

        if (!result.success) {
            return NextResponse.json(
                { 
                    error: result.error_message ?? "Optimization failed",
                    algorithm_used: result.algorithm_used,
                },
                { status: 500 }
            );
        }

        return NextResponse.json({
            success: true,
            algorithm_used: result.algorithm_used,
            routes: result.routes,
            total_vehicles: result.total_vehicles,
            total_duration_minutes: result.total_duration_minutes,
            execution_time_seconds: result.execution_time_seconds,
            student_count: students.length,
            // CVRPTW response fields
            direction: result.direction,
            time_windows_used: result.time_windows_used,
            total_time_window_violations: result.total_time_window_violations,
        });
    } catch (error: unknown) {
        console.error("Route optimization error:", error);
        return NextResponse.json(
            { error: error instanceof Error ? error.message : "Internal server error" },
            { status: 500 }
        );
    }
}