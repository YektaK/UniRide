/**
 * Route Optimization API
 * Calls Python Optimization API
 */

import { NextResponse } from "next/server";
import { headers } from "next/headers";
import { createClient } from "@supabase/supabase-js";
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
    } catch (error: any) {
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}

/**
 * POST /api/optimize-route
 * Optimizes routes using Python API
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

        const body = await request.json();
        const { 
            students, 
            depot, 
            algorithm, 
            max_travel_time, 
            sw_capacity, 
            so_capacity,
            ga_config,
            pso_config
        } = body;

        // Validate input
        if (!students || !Array.isArray(students) || students.length === 0) {
            return NextResponse.json(
                { error: "Students array is required and must not be empty" },
                { status: 400 }
            );
        }

        if (!depot) {
            return NextResponse.json(
                { error: "Depot is required" },
                { status: 400 }
            );
        }

        // Convert students to optimization format
        const optimizationStudents: StudentForOptimization[] = students.map((s: any) => ({
            id: s.id || s.student_id,
            name: s.name || `Öğrenci ${s.id}`,
            location_code: s.location_code || s.locationCode,
            coordinates: s.coordinates || s.home_coordinates || null,
            disability_type: s.disability_type || s.disabilityType || "So",
        }));

        // Default depot (Düzce University Campus)
        const optimizationDepot: Depot = {
            id: depot.id || "D.Kampus",
            lat: depot.lat || 40.8410,
            lng: depot.lng || 31.1478,
        };

        // Call Python API
        const result = await optimizeRoutes(
            optimizationStudents,
            optimizationDepot,
            {
                algorithm: algorithm || "genetic_algorithm",
                max_travel_time: max_travel_time || 120,
                sw_capacity: sw_capacity || 4,
                so_capacity: so_capacity || 5,
                ga_config,
                pso_config,
            }
        );

        if (!result.success) {
            return NextResponse.json(
                { 
                    error: result.error_message || "Optimization failed",
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
        });
    } catch (error: any) {
        console.error("Route optimization error:", error);
        return NextResponse.json(
            { error: error.message || "Internal server error" },
            { status: 500 }
        );
    }
}