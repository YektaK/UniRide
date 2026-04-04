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
import type { IEResponseData, HourlyDemandData, BottleneckData, TimeShiftSuggestion } from "@/types/ie-resource";

// Varsayılan depot (Doğuş Üniversitesi, Dudullu Kampüsü)
const DEFAULT_DEPOT: Depot = {
    id: "D.Kampus",
    lat: 41.001,
    lng: 29.177,
};

function transformIEData(
    ieData: any,
    validStudents: StudentForOptimization[],
    studentLookup: Record<string, any>,
    totalVehicles: number
): IEResponseData | undefined {
    if (!ieData) return undefined;

    // Count Sw/So students from validStudents array
    const swCount = validStudents.filter((s) => s.disability_type === "Sw").length;
    const soCount = validStudents.filter((s) => s.disability_type === "So").length;
    const totalStudents = validStudents.length;

    // Transform hourly_demand format to match frontend
    const hourlyDemand: Record<string, HourlyDemandData> = {};
    if (ieData.hourly_demand) {
        for (const [hour, data] of Object.entries(ieData.hourly_demand)) {
            const demand = data as any;
            const pickupSw = demand.sw?.pickup || 0;
            const pickupSo = demand.so?.pickup || 0;
            const dropoffSw = demand.sw?.dropoff || 0;
            const dropoffSo = demand.so?.dropoff || 0;

            hourlyDemand[hour] = {
                hour,
                pickupSw,
                pickupSo,
                dropoffSw,
                dropoffSo,
                totalPickup: pickupSw + pickupSo,
                totalDropoff: dropoffSw + dropoffSo,
                totalSw: pickupSw + dropoffSw,
                totalSo: pickupSo + dropoffSo,
                isInfeasible: (pickupSw + pickupSo + dropoffSw + dropoffSo) > totalVehicles,
            };
        }
    }

    // Map bottlenecks with severity based on type
    const bottlenecks: BottleneckData[] = (ieData.bottlenecks || []).map((b: any) => ({
        hour: b.time || "",
        type: b.type === "infeasible" ? "infeasible" : b.type === "resource_conflict" ? "resource_conflict" : "low_efficiency",
        severity: b.type === "infeasible" ? "high" : b.type === "resource_conflict" ? "medium" : "low",
        description: b.reason || "",
        swNeeded: 0,
        soNeeded: 0,
        swAvailable: 0,
        soAvailable: 0,
        vehiclesNeeded: 0,
        vehiclesAvailable: totalVehicles,
    }));

    // Transform shift suggestions with student names
    const shiftSuggestions: TimeShiftSuggestion[] = (ieData.time_shift_suggestions || []).map((s: any) => ({
        studentId: s.student_id || "",
        studentName: studentLookup[s.student_id]?.name || s.student_id || "",
        currentTime: s.current_time || "",
        suggestedTime: s.suggested_time || "",
        shiftMinutes: 0,
        reason: `Save ${s.savings_vehicles} vehicle(s)`,
        savingsVehicles: s.savings_vehicles || 0,
    }));

    // Calculate standard vehicle needs
    const standardVehiclesNeeded = ieData.standard_vehicles_needed || 0;

    // Calculate utilization percentages
    const swCapacityNeeded = Math.ceil(swCount / 4);
    const soCapacityNeeded = Math.ceil(soCount / 5);
    const maxNeeded = Math.max(swCapacityNeeded, soCapacityNeeded);

    const swUtilization = swCapacityNeeded > 0 ? (swCount / (swCapacityNeeded * 4)) * 100 : 0;
    const soUtilization = soCapacityNeeded > 0 ? (soCount / (soCapacityNeeded * 5)) * 100 : 0;
    const totalUtilization = maxNeeded > 0 ? (totalStudents / (maxNeeded * 5)) * 100 : 0;

    const standardNeeds = {
        totalStudents,
        swCount,
        soCount,
        standardVehiclesNeeded,
        byCapacity: {
            bySw: swCapacityNeeded,
            bySo: soCapacityNeeded,
            maxNeeded,
        },
        utilizationPercent: Math.round(totalUtilization * 100) / 100,
        utilizationBreakdown: {
            sw: Math.round(swUtilization * 100) / 100,
            so: Math.round(soUtilization * 100) / 100,
        },
    };

    return {
        summary: {
            totalStudents,
            availableVehicles: totalVehicles,
            standardVehiclesNeeded,
            bottleneckCount: bottlenecks.length,
            shiftSuggestionsCount: shiftSuggestions.length,
        },
        standardNeeds,
        hourlyDemand,
        bottlenecks,
        shiftSuggestions,
    };
}

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();

        const {
            students,
            maxTourTime = 120,
            swCapacity = 4,
            soCapacity = 5,
            strategy = "genetic_algorithm",
            clusteringAlgorithm = "sweep",
            vehicles: customVehicles,
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
            vehicles: customVehicles,
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

        // Transform IE data from Python API
        const ieData = transformIEData(
            result.ie_data,
            validStudents,
            studentLookup,
            result.total_vehicles || 0
        );

        return NextResponse.json({
            success: true,
            requiredVehicles: result.total_vehicles || assignments.length,
            assignments,
            totalDuration: Math.round(result.total_duration_minutes || 0),
            message: `${result.total_vehicles} araç ile optimizasyon tamamlandı (${result.algorithm_used})`,
            ieData,
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
