/**
 * API Route: Calculate Required Vehicles
 * POST /api/calculate-vehicles
 * 
 * Proxies the calculation request to the Python Optimization API
 */

import { NextRequest, NextResponse } from "next/server";
import { OPTIMIZER_API_URL } from "@/lib/config";

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();

        const {
            students,
            maxTourTime = 120,
            swCapacity = 4,
            soCapacity = 5,
            strategy = "ortools_cvrp",
            clusteringAlgorithm = "kmeans",
        } = body;

        // Validate input
        if (!students || !Array.isArray(students)) {
            return NextResponse.json({ error: "students array is required" }, { status: 400 });
        }

        // Map frontend legacy frontend names to backend Python payload
        const validStudents = students.map((s: any) => ({
            id: s.id || s.student_id,
            name: s.name || `Öğrenci ${s.id || ''}`,
            location_code: s.locationCode || s.location_code,
            coordinates: s.coordinates || s.homeCoordinates || null,
            disability_type: s.disabilityType || s.disability_type || "So",
        })).filter(s => s.id && s.location_code && ["Sw", "So"].includes(s.disability_type));

        if (validStudents.length === 0) {
            return NextResponse.json({ error: "No valid students provided" }, { status: 400 });
        }

        // Forward to Python optimizer service
        const startTime = Date.now();
        const response = await fetch(`${OPTIMIZER_API_URL}/api/v1/vehicle-calculator`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                algorithm: strategy === "two-opt" ? "genetic_algorithm" : strategy,
                clustering_algorithm: clusteringAlgorithm,
                students: validStudents,
                depot: { id: "D.Kampus", lat: 40.8410, lng: 31.1478, type: "depot" },
                max_travel_time: maxTourTime,
                sw_capacity: swCapacity,
                so_capacity: soCapacity
            }),
            // Use AbortSignal.timeout(X) for Node >= 17.3
            signal: AbortSignal.timeout(120000)
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Python API error: ${response.status}`);
        }

        const data = await response.json();
        const calculationTime = Date.now() - startTime;

        // Return legacy shape expected by Next.js frontend + native new shape
        return NextResponse.json({
            // Legacy mapping for older UIs
            requiredVehicles: data.total_vehicles,
            isValid: data.success,
            totalDuration: data.total_duration_minutes,
            assignments: (data.routes || []).map((route: any, i: number) => {
                const mappedStudents = (route.students || route.student_ids || []).map((s: any) => {
                    if (typeof s === "string") {
                        const original = validStudents.find((vs: any) => vs.id === s);
                        return original ? {
                            id: original.id,
                            name: original.name,
                            locationCode: original.location_code,
                            disabilityType: original.disability_type
                        } : { id: s, name: `Öğrenci ${s}`, disabilityType: "So" };
                    }
                    return {
                        id: s.id || s.student_id,
                        name: s.name,
                        locationCode: s.location_code || s.locationCode,
                        disabilityType: s.disability_type || s.disabilityType || "So"
                    };
                });

                // Strip "Araç " from Python route.vehicle_id to avoid "Araç Araç 1" in UI
                let vIndex = route.vehicle_id || route.vehicle_index || (i + 1);
                if (typeof vIndex === 'string') {
                    vIndex = vIndex.replace(/^Araç\s+/i, '');
                }

                return {
                    vehicleIndex: vIndex,
                    students: mappedStudents,
                    swCount: route.sw_count || 0,
                    soCount: route.so_count || 0,
                    totalDuration: route.total_duration_minutes || 0,
                    routeTime: route.total_duration_minutes || 0,
                    route: route.route_details || route.route || route.steps || []
                };
            }),
            
            // New native data payload
            ...data,

            // Metadata overlay
            meta: {
                calculationTimeMs: calculationTime,
                inputStudentCount: students.length,
                validStudentCount: validStudents.length,
                options: { maxTourTime, swCapacity, soCapacity, strategy },
            },
        });
    } catch (error: any) {
        console.error("Vehicle calculation API proxy error:", error);
        return NextResponse.json({ error: error.message || "Calculation proxy failed" }, { status: 500 });
    }
}
