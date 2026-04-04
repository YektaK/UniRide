/**
 * Algorithm Comparison API
 */

import { NextResponse } from "next/server";
import { headers } from "next/headers";
import { createClient } from "@supabase/supabase-js";
import { compareAllAlgorithms, type StudentForOptimization, type Depot } from "@/services/optimizer-service";

const supabaseAdmin = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
);

async function verifyAuth(authHeader: string | null) {
    if (!authHeader?.startsWith("Bearer ")) return null;
    const token = authHeader.split(" ")[1];
    const { data: { user }, error } = await supabaseAdmin.auth.getUser(token);
    if (error || !user) return null;
    const { data: profile } = await supabaseAdmin.from("users").select("*").eq("id", user.id).single();
    return profile;
}

export async function POST(request: Request) {
    try {
        const headersList = await headers();
        const authHeader = headersList.get("authorization");
        const user = await verifyAuth(authHeader);

        if (!user || user.role !== "admin") {
            return NextResponse.json({ error: "Unauthorized - Admin only" }, { status: 401 });
        }

        const body = await request.json();
        const { students, depot, algorithms, clusteringAlgorithm = "sweep" } = body;

        if (!students || students.length === 0) {
            return NextResponse.json({ error: "Students required" }, { status: 400 });
        }

        const optimizationStudents: StudentForOptimization[] = students.map((s: any) => ({
            id: s.id || s.student_id,
            name: s.name || `Öğrenci ${s.id}`,
            location_code: s.location_code || s.locationCode,
            coordinates: s.coordinates || s.home_coordinates || null,
            disability_type: s.disability_type || s.disabilityType || "So",
        }));

        const optimizationDepot: Depot = {
            id: depot?.id || "D.Kampus",
            lat: depot?.lat || 41.001,
            lng: depot?.lng || 29.177,
        };

        const result = await compareAllAlgorithms(
            optimizationStudents, 
            optimizationDepot, 
            { clustering_algorithm: clusteringAlgorithm }, 
            algorithms
        );

        return NextResponse.json({
            success: result.success,
            results: result.results.map(r => ({
                algorithm: r.algorithm,
                success: r.success,
                total_vehicles: r.total_vehicles,
                total_duration_minutes: r.total_duration_minutes,
                execution_time_seconds: r.execution_time_seconds,
                routes: r.routes,
                error_message: r.error_message,
            })),
            best_algorithm: result.best_algorithm,
            fastest_algorithm: result.fastest_algorithm,
            summary: result.summary,
            student_count: students.length,
        });
    } catch (error: any) {
        console.error("Compare algorithms error:", error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}