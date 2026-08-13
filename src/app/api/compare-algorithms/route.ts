/**
 * Algorithm Comparison API
 */

import { NextResponse } from "next/server";
import { z } from "zod";
import { compareAllAlgorithms, type StudentForOptimization, type Depot } from "@/services/optimizer-service";
import { requireAdmin } from "@/lib/admin-auth";

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
});

const compareAlgorithmsSchema = z.object({
    students: z.array(studentSchema).min(1, "At least one student is required"),
    depot: z.object({
        id: z.string().optional(),
        lat: z.number().optional(),
        lng: z.number().optional(),
    }).optional(),
    algorithms: z.array(z.string()).optional(),
    clusteringAlgorithm: z.string().default("sweep"),
});

export async function POST(request: Request) {
    try {
        await requireAdmin(request);

        const rawBody = await request.json();
        const parseResult = compareAlgorithmsSchema.safeParse(rawBody);
        if (!parseResult.success) {
            return NextResponse.json(
                { error: "Invalid request body", details: parseResult.error.flatten() },
                { status: 400 }
            );
        }

        const { students, depot, algorithms, clusteringAlgorithm } = parseResult.data;

        const optimizationStudents: StudentForOptimization[] = students.map((s) => ({
            id: s.id ?? s.student_id ?? "",
            name: s.name ?? `Öğrenci ${s.id ?? s.student_id}`,
            location_code: s.location_code ?? s.locationCode ?? "",
            coordinates: s.coordinates ?? s.home_coordinates ?? undefined,
            disability_type: (s.disability_type ?? s.disabilityType ?? "So") as "Sw" | "So",
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
                algorithm_requested: r.algorithm_requested,
                feasibility_certificate: r.feasibility_certificate,
                applied_policy: r.applied_policy,
            })),
            best_algorithm: result.best_algorithm,
            fastest_algorithm: result.fastest_algorithm,
            summary: result.summary,
            student_count: students.length,
            algorithm_requested: result.algorithm_requested,
            feasibility_certificate: result.feasibility_certificate,
            applied_policy: result.applied_policy,
        });
    } catch (error: unknown) {
        console.error("Compare algorithms error:", error);
        return NextResponse.json({ error: error instanceof Error ? error.message : "Internal server error" }, { status: 500 });
    }
}
