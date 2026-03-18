/**
 * Optimizer Service
 * Calls Python Optimization API for route optimization
 */

import { OPTIMIZER_API_URL } from "@/lib/config";

// Types
export interface StudentForOptimization {
    id: string;
    name: string;
    location_code: string;
    coordinates?: { lat: number; lng: number };
    disability_type: "Sw" | "So";
}

export interface Depot {
    id: string;
    lat: number;
    lng: number;
}

export interface OptimizationOptions {
    algorithm?: "genetic_algorithm" | "pso" | "greedy" | "permutation_tsp" | "ortools_cvrp";
    max_travel_time?: number;
    sw_capacity?: number;
    so_capacity?: number;
    ga_config?: {
        population_size?: number;
        max_iterations?: number;
        crossover_rate?: number;
        mutation_rate?: number;
    };
    pso_config?: {
        swarm_size?: number;
        max_iterations?: number;
        inertia_weight?: number;
    };
}

export interface RouteStep {
    location1: string;
    location2: string;
    duration: number;
    distance: number;
}

export interface VehicleRoute {
    vehicle_id: string;
    route_details: RouteStep[];
    total_duration_minutes: number;
    total_distance_km: number;
    sw_count: number;
    so_count: number;
    student_ids: string[];
}

export interface OptimizationResult {
    success: boolean;
    algorithm_used: string;
    routes: VehicleRoute[];
    total_vehicles: number;
    total_duration_minutes: number;
    execution_time_seconds: number;
    error_message?: string;
}

export interface AlgorithmResult {
    algorithm: string;
    success: boolean;
    total_vehicles: number;
    total_duration_minutes: number;
    execution_time_seconds: number;
    routes: VehicleRoute[];
    error_message?: string;
}

export interface CompareResult {
    success: boolean;
    results: AlgorithmResult[];
    best_algorithm: string;
    fastest_algorithm: string;
    summary: Record<string, { 
        total_vehicles: number; 
        total_duration_minutes: number; 
        execution_time_seconds: number;
        success: boolean;
    }>;
}

export interface StrategyInfo {
    name: string;
    display_name: string;
    description: string;
    complexity: string;
    recommended: boolean;
}

/**
 * Check if Python API is available
 */
export async function checkApiHealth(): Promise<boolean> {
    try {
        const response = await fetch(`${OPTIMIZER_API_URL}/health`, {
            method: "GET",
            signal: AbortSignal.timeout(5000),
        });
        return response.ok;
    } catch {
        return false;
    }
}

/**
 * Get available optimization strategies
 */
export async function getAvailableStrategies(): Promise<StrategyInfo[]> {
    try {
        const response = await fetch(`${OPTIMIZER_API_URL}/api/v1/strategies`, {
            method: "GET",
            signal: AbortSignal.timeout(5000),
        });

        if (!response.ok) throw new Error("Failed to fetch strategies");
        return await response.json();
    } catch (error) {
        console.error("Error fetching strategies:", error);
        return [
            { name: "genetic_algorithm", display_name: "Genetik Algoritma", description: "Popülasyon tabanlı meta-sezgisel", complexity: "O(g × p × n²)", recommended: true },
            { name: "pso", display_name: "PSO", description: "Sürü zekası tabanlı", complexity: "O(i × s × n²)", recommended: true },
            { name: "greedy", display_name: "Greedy", description: "Hızlı sezgisel", complexity: "O(n²)", recommended: false },
            { name: "permutation_tsp", display_name: "Permütasyon TSP", description: "Optimal (n≤10)", complexity: "O(n!)", recommended: false },
        ];
    }
}

/**
 * Optimize routes using Python API
 */
export async function optimizeRoutes(
    students: StudentForOptimization[],
    depot: Depot,
    options: OptimizationOptions = {}
): Promise<OptimizationResult> {
    const algorithm = options.algorithm || "genetic_algorithm";

    try {
        const response = await fetch(`${OPTIMIZER_API_URL}/api/v1/optimize`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                algorithm,
                students: students.map(s => ({
                    id: s.id,
                    name: s.name,
                    location_code: s.location_code,
                    coordinates: s.coordinates,
                    disability_type: s.disability_type,
                })),
                depot: { id: depot.id, lat: depot.lat, lng: depot.lng, type: "depot" },
                max_travel_time: options.max_travel_time || 120,
                sw_capacity: options.sw_capacity || 4,
                so_capacity: options.so_capacity || 5,
                ga_config: options.ga_config,
                pso_config: options.pso_config,
            }),
            signal: AbortSignal.timeout(120000),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `API error: ${response.status}`);
        }

        const data = await response.json();
        return {
            success: data.success,
            algorithm_used: data.algorithm_used,
            routes: data.routes || [],
            total_vehicles: data.total_vehicles || 0,
            total_duration_minutes: data.total_duration_minutes || 0,
            execution_time_seconds: data.execution_time_seconds || 0,
            error_message: data.error_message,
        };
    } catch (error: any) {
        console.error("Optimization API error:", error);
        return {
            success: false,
            algorithm_used: algorithm,
            routes: [],
            total_vehicles: 0,
            total_duration_minutes: 0,
            execution_time_seconds: 0,
            error_message: error.message || "Optimization failed",
        };
    }
}

/**
 * Compare all algorithms on the same problem
 */
export async function compareAllAlgorithms(
    students: StudentForOptimization[],
    depot: Depot,
    options: OptimizationOptions = {},
    algorithms?: string[]
): Promise<CompareResult> {
    try {
        const response = await fetch(`${OPTIMIZER_API_URL}/api/v1/compare`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                students: students.map(s => ({
                    id: s.id,
                    name: s.name,
                    location_code: s.location_code,
                    coordinates: s.coordinates,
                    disability_type: s.disability_type,
                })),
                depot: { id: depot.id, lat: depot.lat, lng: depot.lng, type: "depot" },
                max_travel_time: options.max_travel_time || 120,
                sw_capacity: options.sw_capacity || 4,
                so_capacity: options.so_capacity || 5,
                algorithms,
            }),
            signal: AbortSignal.timeout(300000),
        });

        if (!response.ok) throw new Error(`Compare API error: ${response.status}`);

        const data = await response.json();
        return {
            success: data.success,
            results: data.results || [],
            best_algorithm: data.best_algorithm || "",
            fastest_algorithm: data.fastest_algorithm || "",
            summary: data.summary || {},
        };
    } catch (error: any) {
        console.error("Compare API error:", error);
        return { success: false, results: [], best_algorithm: "", fastest_algorithm: "", summary: {} };
    }
}