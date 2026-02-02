/**
 * Vehicle Calculator Service
 * Calculates required number of vehicles and assigns students to vehicles
 * Based on MATLAB VRP code: calculate_vehicles_with_vrp_fixed_v11.m
 */

import type { Coordinates } from "@/lib/coordinates";
import { kMeansClustering, validateClusterCapacity, splitCluster, type Cluster, type ClusterablePoint } from "./clustering";
import { calculateDistance } from "./doubus/route";
import { getStrategy } from "./doubus/route-strategies";
import type { RouteDetail } from "./doubus/route-strategies/types";

export interface StudentForAssignment {
    id: string;
    name: string;
    locationCode: string; // Sw1, So5, etc.
    coordinates?: Coordinates;
    disabilityType: "Sw" | "So";
}

export interface VehicleCapacity {
    swCapacity: number; // Wheelchair capacity
    soCapacity: number; // Regular seating capacity
}

export interface VehicleAssignment {
    vehicleIndex: number;
    students: StudentForAssignment[];
    route: RouteDetail[];
    totalDuration: number;
    swCount: number;
    soCount: number;
}

export interface VehicleCalculationResult {
    success: boolean;
    requiredVehicles: number;
    assignments: VehicleAssignment[];
    totalDuration: number;
    unassignedStudents: StudentForAssignment[];
    message: string;
}

export interface VehicleCalculationOptions {
    maxTourTime: number; // Maximum tour time in minutes
    vehicleCapacity: VehicleCapacity;
    strategy: string; // Route optimization strategy
}

const DEFAULT_OPTIONS: VehicleCalculationOptions = {
    maxTourTime: 120,
    vehicleCapacity: { swCapacity: 4, soCapacity: 5 },
    strategy: "two-opt",
};

/**
 * Main function to calculate required vehicles and assign students
 */
export async function calculateRequiredVehicles(
    students: StudentForAssignment[],
    options: Partial<VehicleCalculationOptions> = {}
): Promise<VehicleCalculationResult> {
    const opts = { ...DEFAULT_OPTIONS, ...options };

    if (students.length === 0) {
        return {
            success: true,
            requiredVehicles: 0,
            assignments: [],
            totalDuration: 0,
            unassignedStudents: [],
            message: "Öğrenci listesi boş",
        };
    }

    // Count students by type
    const swCount = students.filter(s => s.disabilityType === "Sw").length;
    const soCount = students.filter(s => s.disabilityType === "So").length;

    // Initial vehicle estimate (from MATLAB)
    let numVehicles = Math.max(
        Math.ceil(swCount / opts.vehicleCapacity.swCapacity),
        Math.ceil(soCount / opts.vehicleCapacity.soCapacity)
    );
    numVehicles = Math.max(numVehicles, 1);

    // Convert students to clusterable points
    const points: ClusterablePoint[] = students.map(s => ({
        id: s.id,
        coordinates: s.coordinates || { lat: 0, lng: 0 },
        disabilityType: s.disabilityType,
    }));

    // Try to find valid assignments with increasing vehicle count
    let attempts = 0;
    const maxAttempts = students.length; // Never need more vehicles than students

    while (attempts < maxAttempts) {
        const result = await tryAssignment(students, points, numVehicles, opts);

        if (result.success) {
            return result;
        }

        numVehicles++;
        attempts++;
    }

    // Fallback: assign one student per vehicle
    return createFallbackAssignment(students, opts);
}

/**
 * Try to assign students to a specific number of vehicles
 */
async function tryAssignment(
    students: StudentForAssignment[],
    points: ClusterablePoint[],
    numVehicles: number,
    opts: VehicleCalculationOptions
): Promise<VehicleCalculationResult> {
    // K-means clustering
    let clusters = kMeansClustering(points, numVehicles);

    // Validate and split over-capacity clusters
    const validatedClusters: Cluster[] = [];
    for (const cluster of clusters) {
        if (validateClusterCapacity(cluster, opts.vehicleCapacity.swCapacity, opts.vehicleCapacity.soCapacity)) {
            validatedClusters.push(cluster);
        } else {
            // Split the cluster and validate again
            const splitClusters = splitCluster(cluster);
            for (const sc of splitClusters) {
                if (validateClusterCapacity(sc, opts.vehicleCapacity.swCapacity, opts.vehicleCapacity.soCapacity)) {
                    validatedClusters.push(sc);
                } else {
                    // Still over capacity - need more vehicles
                    return {
                        success: false,
                        requiredVehicles: numVehicles,
                        assignments: [],
                        totalDuration: 0,
                        unassignedStudents: students,
                        message: `Kapasite aşımı: ${numVehicles} araç yeterli değil`,
                    };
                }
            }
        }
    }

    // Calculate routes for each cluster
    const assignments: VehicleAssignment[] = [];
    let totalDuration = 0;

    for (let i = 0; i < validatedClusters.length; i++) {
        const cluster = validatedClusters[i];
        const clusterStudents = students.filter(s =>
            cluster.points.some(p => p.id === s.id)
        );

        // Get location codes for routing
        const waypoints = clusterStudents.map(s => s.locationCode);

        // Calculate optimal route
        const routeResult = await calculateClusterRoute(waypoints, opts.strategy);

        // Check tour time constraint
        if (routeResult.totalDuration > opts.maxTourTime) {
            return {
                success: false,
                requiredVehicles: numVehicles,
                assignments: [],
                totalDuration: 0,
                unassignedStudents: students,
                message: `Tur süresi aşımı: Araç ${i + 1} için ${routeResult.totalDuration} dk > ${opts.maxTourTime} dk`,
            };
        }

        assignments.push({
            vehicleIndex: i + 1,
            students: clusterStudents,
            route: routeResult.routeDetails,
            totalDuration: routeResult.totalDuration,
            swCount: cluster.swCount,
            soCount: cluster.soCount,
        });

        totalDuration += routeResult.totalDuration;
    }

    return {
        success: true,
        requiredVehicles: validatedClusters.length,
        assignments,
        totalDuration,
        unassignedStudents: [],
        message: `${validatedClusters.length} araç ile optimum rota bulundu`,
    };
}

/**
 * Calculate optimal route for a cluster of students
 */
async function calculateClusterRoute(
    waypoints: string[],
    strategyName: string
): Promise<{ routeDetails: RouteDetail[]; totalDuration: number }> {
    if (waypoints.length === 0) {
        return { routeDetails: [], totalDuration: 0 };
    }

    const strategy = getStrategy(strategyName);
    if (!strategy) {
        // Fallback to simple route
        return calculateSimpleRoute(waypoints);
    }

    try {
        const result = await strategy.calculateOptimalRoute(
            "D.Kampus",
            "D.Kampus",
            waypoints,
            calculateDistance
        );
        return result;
    } catch (error) {
        console.error("Route calculation error:", error);
        return calculateSimpleRoute(waypoints);
    }
}

/**
 * Simple route calculation (fallback)
 */
function calculateSimpleRoute(
    waypoints: string[]
): { routeDetails: RouteDetail[]; totalDuration: number } {
    const routeDetails: RouteDetail[] = [];
    let totalDuration = 0;

    // Start from D.Kampus
    let current = "D.Kampus";

    for (const wp of waypoints) {
        const duration = calculateDistance(current, wp);
        routeDetails.push({
            location1: current,
            location2: wp,
            duration: duration === Infinity ? 15 : duration, // Fallback 15 min
        });
        totalDuration += duration === Infinity ? 15 : duration;
        current = wp;
    }

    // Return to D.Kampus
    const returnDuration = calculateDistance(current, "D.Kampus");
    routeDetails.push({
        location1: current,
        location2: "D.Kampus",
        duration: returnDuration === Infinity ? 15 : returnDuration,
    });
    totalDuration += returnDuration === Infinity ? 15 : returnDuration;

    return { routeDetails, totalDuration };
}

/**
 * Fallback: assign one student per vehicle
 */
function createFallbackAssignment(
    students: StudentForAssignment[],
    opts: VehicleCalculationOptions
): VehicleCalculationResult {
    const assignments: VehicleAssignment[] = students.map((student, i) => ({
        vehicleIndex: i + 1,
        students: [student],
        route: [],
        totalDuration: 0,
        swCount: student.disabilityType === "Sw" ? 1 : 0,
        soCount: student.disabilityType === "So" ? 1 : 0,
    }));

    return {
        success: true,
        requiredVehicles: students.length,
        assignments,
        totalDuration: 0,
        unassignedStudents: [],
        message: `Fallback: Her öğrenci için ayrı araç (${students.length} araç)`,
    };
}
