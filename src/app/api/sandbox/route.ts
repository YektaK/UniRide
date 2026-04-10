/**
 * Sandbox API Route
 * Handles sandbox mode operations for IE fine-tuning
 * POST /api/sandbox/reoptimize - Re-optimize with custom vehicle config
 * POST /api/sandbox/save-scenario - Save sandbox scenario
 * GET /api/sandbox/scenarios - Get saved scenarios
 * DELETE /api/sandbox/scenarios - Delete scenario
 */

import { NextRequest } from "next/server";
import { getSupabaseAdmin } from "@/lib/supabase-admin";
import {
    requireAdmin,
    createErrorResponse,
    createSuccessResponse,
    handleApiError,
} from "@/lib/admin-auth";
import type { Database } from "@/lib/supabase";
import type { IERawData, IEResponseData, HourlyDemandData, BottleneckData, TimeShiftSuggestion } from "@/types/ie-resource";

// Default depot — Doğuş Üniversitesi Dudullu Kampüsü
const DEFAULT_DEPOT = { id: "D.Kampus", lat: 41.001, lng: 29.177 };

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

interface SaveScenarioRequest {
    name: string;
    vehicles: VehicleConfig[];
    studentIds: string[];
    timeWindowMinutes: number;
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
        } = body;

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
        const response = await fetch(process.env.OPTIMIZER_API_URL + "/api/v1/optimize", {
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
            const errorText = await response.text();
            return createErrorResponse(`Optimizasyon hatası: ${errorText}`, response.status);
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

// GET /api/sandbox/scenarios - Get saved scenarios
export async function GET(request: NextRequest) {
    try {
        await requireAdmin(request);

        const { searchParams } = new URL(request.url);
        const scenarioId = searchParams.get("id");

        const adminClient = getSupabaseAdmin();

        if (scenarioId) {
            const { data, error } = await adminClient
                .from("sandbox_scenarios")
                .select("*")
                .eq("id", scenarioId)
                .single();

            if (error) {
                return createErrorResponse(error.message, 500);
            }

            return createSuccessResponse(data);
        }

        const { data, error } = await adminClient
            .from("sandbox_scenarios")
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

// POST /api/sandbox/scenarios - Save scenario
export async function PUT(request: NextRequest) {
    try {
        const adminUser = await requireAdmin(request);

        const body = await request.json() as SaveScenarioRequest;
        const { name, vehicles, studentIds, timeWindowMinutes } = body;

        if (!name) {
            return createErrorResponse("Senaryo adı gerekli", 400);
        }

        const adminClient = getSupabaseAdmin();

        const insertPayload: Database["public"]["Tables"]["sandbox_scenarios"]["Insert"] = {
            name,
            vehicles: JSON.stringify(vehicles),
            student_ids: studentIds,
            time_window_minutes: timeWindowMinutes,
            created_by: adminUser.id,
            updated_at: null,
        };

        const { data, error } = await adminClient
            .schema("public")
            .from("sandbox_scenarios")
            .insert(insertPayload)
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

// DELETE /api/sandbox/scenarios - Delete scenario
export async function DELETE(request: NextRequest) {
    try {
        await requireAdmin(request);

        const { searchParams } = new URL(request.url);
        const id = searchParams.get("id");

        if (!id) {
            return createErrorResponse("Senaryo ID gerekli", 400);
        }

        const adminClient = getSupabaseAdmin();
        const { error } = await adminClient
            .from("sandbox_scenarios")
            .delete()
            .eq("id", id);

        if (error) {
            return createErrorResponse(error.message, 500);
        }

        return createSuccessResponse({ message: "Senaryo silindi" });
    } catch (error) {
        return handleApiError(error);
    }
}
