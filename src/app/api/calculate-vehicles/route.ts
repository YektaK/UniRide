/**
 * API Route: Calculate Required Vehicles
 * POST /api/calculate-vehicles
 *
 * Araç planlama sayfasından gelen isteği Python Optimizer API'ye iletir.
 * Öğrencileri kümeleyip her küme için rota optimize eder.
 *
 * Mimari karar KN1: İşlev bazlı Next.js proxy
 * Bkz: docs/ARCHITECTURE.md
 */

import { NextRequest, NextResponse } from "next/server";
import {
    optimizeRoutes,
    type StudentForOptimization,
    type Depot,
} from "@/services/optimizer-service";
import { normalizeAlgorithmName } from "@/lib/algorithm-constants";

// Varsayılan depot (Düzce Üniversitesi Kampüs)
const DEFAULT_DEPOT: Depot = {
    id: "D.Kampus",
    lat: 40.841,
    lng: 31.1478,
};

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();

        const {
            students,
            maxTourTime = 120,
            swCapacity = 4,
            soCapacity = 5,
            strategy = "genetic_algorithm",
            clusteringAlgorithm = "kmeans",
        } = body;

        // Girdi doğrulama
        if (!students || !Array.isArray(students)) {
            return NextResponse.json(
                { error: "students array is required" },
                { status: 400 }
            );
        }

        // Öğrencileri Python API formatına dönüştür
        const validStudents: StudentForOptimization[] = [];
        const studentLookup: Record<string, any> = {};

        for (const student of students) {
            // Geçersiz kayıtları atla
            const locationCode = student.location_code || student.locationCode;
            const disabilityType = student.disability_type || student.disabilityType;

            if (!student.id || !locationCode || !disabilityType) {
                continue;
            }

            if (!["Sw", "So"].includes(disabilityType)) {
                continue;
            }

            validStudents.push({
                id: student.id,
                name: student.name || `Öğrenci ${student.id.slice(0, 6)}`,
                location_code: locationCode,
                coordinates: student.coordinates || student.home_coordinates || null,
                disability_type: disabilityType as "Sw" | "So",
            });

            // Sonuçları UI formatına çevirirken öğrenci bilgilerine erişmek için
            studentLookup[student.id] = {
                id: student.id,
                name: student.name || `Öğrenci ${student.id.slice(0, 6)}`,
                locationCode: locationCode,
                disabilityType: disabilityType,
                coordinates: student.coordinates || student.home_coordinates || null,
            };
        }

        if (validStudents.length === 0) {
            return NextResponse.json(
                { error: "No valid students provided" },
                { status: 400 }
            );
        }

        // Algoritma adını Python registry formatına dönüştür
        const normalizedAlgorithm = normalizeAlgorithmName(strategy);

        // Python API'yi çağır
        const startTime = Date.now();

        const result = await optimizeRoutes(validStudents, DEFAULT_DEPOT, {
            algorithm: normalizedAlgorithm as any,
            max_travel_time: maxTourTime,
            sw_capacity: swCapacity,
            so_capacity: soCapacity,
            clustering_algorithm: clusteringAlgorithm,
        });

        const calculationTime = Date.now() - startTime;

        if (!result.success) {
            return NextResponse.json(
                {
                    success: false,
                    error: result.error_message || "Optimization failed",
                    algorithm_used: result.algorithm_used,
                },
                { status: 500 }
            );
        }

        // Python yanıtını UI'ın beklediği formata dönüştür
        // Python: { routes[], total_vehicles, total_duration_minutes }
        // UI: { requiredVehicles, assignments[], totalDuration, message }
        const assignments = (result.routes || []).map((route: any, index: number) => {
            // Rota içindeki öğrenci bilgilerini al
            const routeStudents = (route.student_ids || []).map((sid: string) => {
                const s = studentLookup[sid];
                if (s) return s;
                // Fallback: ID varsa basit obje döndür
                return { id: sid, name: sid, locationCode: "?", disabilityType: "So" };
            });

            return {
                vehicleIndex: index + 1,
                students: routeStudents,
                route: route.route_details || [],
                totalDuration: route.total_duration_minutes || 0,
                swCount: route.sw_count || 0,
                soCount: route.so_count || 0,
            };
        });

        return NextResponse.json({
            success: true,
            requiredVehicles: result.total_vehicles || assignments.length,
            assignments,
            totalDuration: Math.round(result.total_duration_minutes || 0),
            message: `${result.total_vehicles} araç ile optimizasyon tamamlandı (${result.algorithm_used})`,
            meta: {
                calculationTimeMs: calculationTime,
                inputStudentCount: students.length,
                validStudentCount: validStudents.length,
                algorithmUsed: result.algorithm_used,
                executionTimeSeconds: result.execution_time_seconds,
                options: {
                    maxTourTime,
                    swCapacity,
                    soCapacity,
                    strategy: normalizedAlgorithm,
                    clusteringAlgorithm,
                },
            },
        });
    } catch (error: any) {
        console.error("Vehicle calculation error:", error);
        return NextResponse.json(
            { error: error.message || "Calculation failed" },
            { status: 500 }
        );
    }
}
