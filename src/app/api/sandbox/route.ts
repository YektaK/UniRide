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

        // Calculate total capacity
        const totalSwCapacity = vehicles.reduce((sum, v) => sum + (v.swCapacity || 0), 0);
        const totalSoCapacity = vehicles.reduce((sum, v) => sum + (v.soCapacity || 0), 0);

        // Call the optimization API with custom vehicle config
        const response = await fetch(process.env.OPTIMIZER_API_URL + "/api/v1/optimize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                students,
                vehicles,
                max_travel_time: maxTourTime,
                allow_time_shift: allowTimeShift,
                algorithm: strategy,
                clustering_algorithm: clusteringAlgorithm,
            }),
        });

        if (!response.ok) {
            const errorText = await response.text();
            return createErrorResponse(`Optimizasyon hatası: ${errorText}`, response.status);
        }

        const result = await response.json();

        // Get IE data
        let ieData = null;
        try {
            const ieResponse = await fetch(`${process.env.OPTIMIZER_API_URL}/api/v1/ie/analyze`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    vehicles,
                    pickup_times: result.pickup_times || [],
                    dropoff_times: result.dropoff_times || [],
                    routes: result.routes || [],
                }),
            });

            if (ieResponse.ok) {
                ieData = await ieResponse.json();
            }
        } catch (ieError) {
            console.error("IE analysis error:", ieError);
        }

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
