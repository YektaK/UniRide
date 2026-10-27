/**
 * Sandbox API Route
 * Handles sandbox mode operations for IE fine-tuning
 * POST /api/sandbox - Re-optimize with custom vehicle config.
 * Scenario persistence lives in the browser (localStorage) in the sandbox page;
 * the former GET/PUT/DELETE scenario handlers were unused and were removed
 * (audit L3-c, MT6F-08).
 */

import { NextRequest } from "next/server";
import {
    requireAdmin,
    createErrorResponse,
    createSuccessResponse,
    handleApiError,
} from "@/lib/admin-auth";
import { optimizerFetch } from "@/lib/optimizer-server";
import {
    classifyOptimizerMatrixError,
    MATRIX_ERROR_HTTP_STATUS,
    MATRIX_ERROR_MESSAGES,
    readOptimizerErrorDetail,
} from "@/services/optimizer-matrix-errors";
import type { IERawData, IEResponseData, HourlyDemandData, BottleneckData, TimeShiftSuggestion } from "@/types/ie-resource";
import { DUDULLU_DEPOT } from "@/services/dudullu-campus";
import { isClusteringAlgorithmName } from "@/lib/clustering-algorithms";

// Default depot — Doğuş Üniversitesi Dudullu Kampüsü
const DEFAULT_DEPOT = { ...DUDULLU_DEPOT };

interface VehicleConfig {
    id?: string;
    name: string;
    swCapacity: number;
    soCapacity: number;
    cooldownMinutes?: number;
}

interface ReoptimizeRequest {
    students: any[];
    vehicles: VehicleConfig[];
    maxTourTime?: number;
    allowTimeShift?: boolean;
    strategy?: string;
    clusteringAlgorithm?: string;
}

/**
 * Transform raw ie_data from the Python optimizer into the frontend IEResponseData shape.
 * Mirrors the logic in calculate-vehicles/route.ts#transformIEData.
 */
function transformIEData(ieData: IERawData | undefined, totalVehicles: number): IEResponseData | undefined {
    if (!ieData) return undefined;

    const hourlyDemand: Record<string, HourlyDemandData> = {};
    if (ieData.hourly_demand) {
        for (const [hour, demand] of Object.entries(ieData.hourly_demand)) {
            const pickupSw = demand.sw?.pickup ?? 0;
            const pickupSo = demand.so?.pickup ?? 0;
            const dropoffSw = demand.sw?.dropoff ?? 0;
            const dropoffSo = demand.so?.dropoff ?? 0;
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

    const bottlenecks: BottleneckData[] = (ieData.bottlenecks ?? []).map((b) => ({
        hour: b.time ?? "",
        type: b.type === "infeasible" ? "infeasible" : b.type === "resource_conflict" ? "resource_conflict" : "low_efficiency",
        severity: b.type === "infeasible" ? "high" : b.type === "resource_conflict" ? "medium" : "low",
        description: b.reason ?? "",
        swNeeded: 0,
        soNeeded: 0,
        swAvailable: 0,
        soAvailable: 0,
        vehiclesNeeded: 0,
        vehiclesAvailable: totalVehicles,
    }));

    const shiftSuggestions: TimeShiftSuggestion[] = (ieData.time_shift_suggestions ?? []).map((s) => ({
        studentId: s.student_id ?? "",
        studentName: s.student_id ?? "",
        currentTime: s.current_time ?? "",
        suggestedTime: s.suggested_time ?? "",
        shiftMinutes: 0,
        reason: `Save ${s.savings_vehicles ?? 0} vehicle(s)`,
        savingsVehicles: s.savings_vehicles ?? 0,
    }));

    const standardVehiclesNeeded = ieData.standard_vehicles_needed ?? 0;

    return {
        summary: {
            totalStudents: 0,
            availableVehicles: totalVehicles,
            standardVehiclesNeeded,
            bottleneckCount: bottlenecks.length,
            shiftSuggestionsCount: shiftSuggestions.length,
        },
        standardNeeds: {
            totalStudents: 0,
            swCount: 0,
            soCount: 0,
            standardVehiclesNeeded,
            byCapacity: { bySw: 0, bySo: 0, maxNeeded: standardVehiclesNeeded },
            utilizationPercent: 0,
            utilizationBreakdown: { sw: 0, so: 0 },
        },
        hourlyDemand,
        bottlenecks,
        shiftSuggestions,
    };
}

// POST /api/sandbox/reoptimize - Re-optimize with custom vehicle config
export async function POST(request: NextRequest) {
    try {
        await requireAdmin(request);

        const body = await request.json() as ReoptimizeRequest;
        const {
            students,
            vehicles,
            maxTourTime = 120,
            allowTimeShift = false,
            strategy = "genetic_algorithm",
            clusteringAlgorithm = "sweep"
        } = body as Omit<ReoptimizeRequest, "clusteringAlgorithm"> & { clusteringAlgorithm?: unknown };

        // Shared allowlist: an unknown name never reaches the optimizer.
        if (!isClusteringAlgorithmName(clusteringAlgorithm)) {
            return createErrorResponse("Invalid clusteringAlgorithm", 400);
        }

        if (!students || students.length === 0) {
            return createErrorResponse("Öğrenci listesi gerekli", 400);
        }

        if (!vehicles || vehicles.length === 0) {
            return createErrorResponse("Araç konfigürasyonu gerekli", 400);
        }

        // Calculate total capacity for IE transform
        const totalSwCapacity = vehicles.reduce((sum, v) => sum + (v.swCapacity || 0), 0);
        const totalSoCapacity = vehicles.reduce((sum, v) => sum + (v.soCapacity || 0), 0);
        const totalVehicles = vehicles.length;

        // Map frontend vehicles to Python VehicleConfig schema
        // Python expects: { vehicle_id, sw_capacity, so_capacity, cooldown_minutes }
        const mappedVehicles = vehicles.map((v, idx) => ({
            vehicle_id: v.id ?? `vehicle_${idx + 1}`,
            sw_capacity: v.swCapacity,
            so_capacity: v.soCapacity,
            cooldown_minutes: v.cooldownMinutes ?? 15,
        }));

        // Map frontend students to Python StudentNode schema.
        // Students arrive as snake_case DbUserRow objects from the admin API.
        const mappedStudents = students.map((s: any) => ({
            id: s.id ?? s.student_id ?? String(s.id),
            name: s.name ?? "",
            location_code: s.location_code ?? s.locationCode ?? "",
            coordinates: s.home_coordinates ?? s.coordinates ?? null,
            disability_type: s.disability_type ?? s.disabilityType ?? "So",
            pickup_time: s.pickup_time ?? s.pickupTime ?? null,
            dropoff_time: s.dropoff_time ?? s.dropoffTime ?? null,
        }));

        // Call the optimization API with correct request shape (depot + vehicles required)
        const response = await optimizerFetch("/api/v1/optimize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                algorithm: strategy,
                students: mappedStudents,
                depot: DEFAULT_DEPOT,
                vehicles: mappedVehicles,
                max_travel_time: maxTourTime,
                allow_time_shift: allowTimeShift,
                clustering_algorithm: clusteringAlgorithm,
            }),
        });

        if (!response.ok) {
            // C2: the optimizer fails closed (503/422) when the stored
            // travel-time matrix cannot answer. Surface a clear, redacted error.
            const matrixError = classifyOptimizerMatrixError(
                response.status,
                await readOptimizerErrorDetail(response)
            );
            if (matrixError) {
                return Response.json(
                    { error: MATRIX_ERROR_MESSAGES[matrixError], code: matrixError },
                    { status: MATRIX_ERROR_HTTP_STATUS[matrixError] }
                );
            }
            return createErrorResponse("Optimization failed", response.status);
        }

        const result = await response.json();

        // ie_data is embedded in the optimize response by the Python ResourceProfiler (A-3 fix).
        // Transform it from the raw Python shape to the frontend IEResponseData shape.
        const ieData = transformIEData(result.ie_data as IERawData | undefined, totalVehicles);

        return createSuccessResponse({
            ...result,
            totalSwCapacity,
            totalSoCapacity,
            ieData,
        });
    } catch (error) {
        return handleApiError(error);
    }
}

