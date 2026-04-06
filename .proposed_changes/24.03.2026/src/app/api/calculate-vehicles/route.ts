/**
 * API Route: Calculate Required Vehicles
 * POST /api/calculate-vehicles
 * 
 * Calculates the number of vehicles needed and assigns students to vehicles
 * based on capacity constraints and tour time limits.
 */

import { NextRequest, NextResponse } from "next/server";
import { calculateRequiredVehicles, type StudentForAssignment } from "@/services/vehicle-calculator";

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();

        const {
            students,
            maxTourTime = 120,
            swCapacity = 4,
            soCapacity = 5,
            strategy = "genetic_algorithm",
            local_search_type = "two_opt",
        } = body;

        // Validate input
        if (!students || !Array.isArray(students)) {
            return NextResponse.json(
                { error: "students array is required" },
                { status: 400 }
            );
        }

        // Convert and validate students
        const validStudents: StudentForAssignment[] = [];
        for (const student of students) {
            if (!student.id || !student.locationCode || !student.disabilityType) {
                continue; // Skip invalid entries
            }

            if (!["Sw", "So"].includes(student.disabilityType)) {
                continue; // Skip invalid disability types
            }

            validStudents.push({
                id: student.id,
                name: student.name || `Öğrenci ${student.id}`,
                locationCode: student.locationCode,
                coordinates: student.coordinates,
                disabilityType: student.disabilityType,
            });
        }

        if (validStudents.length === 0) {
            return NextResponse.json(
                { error: "No valid students provided" },
                { status: 400 }
            );
        }

        // Calculate vehicles
        const startTime = Date.now();
        const result = await calculateRequiredVehicles(validStudents, {
            maxTourTime,
            vehicleCapacity: { swCapacity, soCapacity },
            strategy,
            local_search_type,
        });
        const calculationTime = Date.now() - startTime;

        return NextResponse.json({
            ...result,
            meta: {
                calculationTimeMs: calculationTime,
                inputStudentCount: students.length,
                validStudentCount: validStudents.length,
                options: {
                    maxTourTime,
                    swCapacity,
                    soCapacity,
                    strategy,
                    local_search_type,
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
