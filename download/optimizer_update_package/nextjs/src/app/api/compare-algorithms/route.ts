/**
 * Algorithm Comparison API
 * Compares all algorithms on the same problem
 */

import { NextResponse } from "next/server";
import { headers } from "next/headers";
import { createClient } from "@supabase/supabase-js";
import { 
    compareAllAlgorithms,
    getAlgorithmDisplayName,
    type StudentForOptimization,
    type Depot,
    type AlgorithmCompareResult
} from "@/services/optimizer-service";

const supabaseAdmin = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
);

async function verifyAuth(authHeader: string | null) {
    if (!authHeader?.startsWith("Bearer ")) return null;
    const token = authHeader.split(" ")[1];
    const { data: { user }, error } = await supabaseAdmin.auth.getUser(token);
    if (error || !user) return null;
    const { data: profile } = await supabaseAdmin
        .from("users")
        .select("*")
        .eq("id", user.id)
        .single();
    return profile;
}

/**
 * GET /api/compare-algorithms
 * Returns available algorithms for comparison
 */
export async function GET() {
    return NextResponse.json({
        algorithms: [
            { name: "genetic_algorithm", display_name: "Genetik Algoritma", recommended: true },
            { name: "pso", display_name: "Parçacık Sürü Optimizasyonu", recommended: true },
            { name: "gwo", display_name: "Gri Kurt Optimizasyonu", recommended: true },
            { name: "hho", display_name: "Harris Hawks Optimizasyonu", recommended: true },
            { name: "greedy", display_name: "Greedy (En Yakın Komşu)", recommended: false },
            { name: "permutation_tsp", display_name: "Permütasyon (Optimal)", recommended: false },
            { name: "ortools_cvrp", display_name: "OR-Tools CVRP", recommended: false },
        ],
        description: "Tüm algoritmaları karşılaştır ve en iyi sonucu bul",
    });
}

/**
 * POST /api/compare-algorithms
 * Compare all algorithms and return results
 */
export async function POST(request: Request) {
    try {
        const headersList = await headers();
        const authHeader = headersList.get("authorization");
        const user = await verifyAuth(authHeader);

        if (!user || user.role !== "admin") {
            return NextResponse.json({ error: "Unauthorized - Admin only" }, { status: 401 });
        }

        const body = await request.json();
        const { students, depot, algorithms } = body;

        if (!students || students.length === 0) {
            return NextResponse.json({ error: "Students required" }, { status: 400 });
        }

        // Convert students
        const optimizationStudents: StudentForOptimization[] = students.map((s: any) => ({
            id: s.id || s.student_id,
            name: s.name || `Öğrenci ${s.id}`,
            location_code: s.location_code || s.locationCode,
            coordinates: s.coordinates || s.home_coordinates || null,
            disability_type: s.disability_type || s.disabilityType || "So",
        }));

        const optimizationDepot: Depot = {
            id: depot?.id || "D.Kampus",
            lat: depot?.lat || 40.8410,
            lng: depot?.lng || 31.1478,
        };

        // Run comparison
        const result = await compareAllAlgorithms(
            optimizationStudents,
            optimizationDepot,
            {},
            algorithms
        );

        // Map results with correct field names (algorithm, not algorithm_used)
        // This matches Python AlgorithmResult schema
        const mappedResults = result.results.map((r: AlgorithmCompareResult) => ({
            algorithm: r.algorithm,
            algorithm_display_name: getAlgorithmDisplayName(r.algorithm),
            success: r.success,
            total_vehicles: r.total_vehicles,
            total_duration_minutes: Math.round(r.total_duration_minutes * 100) / 100,
            execution_time_seconds: Math.round(r.execution_time_seconds * 1000) / 1000,
            routes: r.routes,
            error_message: r.error_message,
        }));

        return NextResponse.json({
            success: result.success,
            results: mappedResults,
            best_algorithm: result.best_algorithm,
            best_algorithm_display_name: getAlgorithmDisplayName(result.best_algorithm),
            fastest_algorithm: result.fastest_algorithm,
            fastest_algorithm_display_name: getAlgorithmDisplayName(result.fastest_algorithm),
            summary: result.summary,
            student_count: students.length,
            timestamp: new Date().toISOString(),
        });
    } catch (error: any) {
        console.error("Compare algorithms error:", error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
