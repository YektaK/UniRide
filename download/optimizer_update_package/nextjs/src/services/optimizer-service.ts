/**
 * Optimizer Service
 * Calls Python Optimization API for route optimization
 * Provides fallback to local calculation if API is unavailable
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
    algorithm?: "genetic_algorithm" | "ga" | "pso" | "gwo" | "grey_wolf" | "hho" | "harris_hawks" | "greedy" | "permutation_tsp" | "ortools_cvrp";
    max_travel_time?: number;  // minutes
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
    gwo_config?: {
        population_size?: number;
        max_iterations?: number;
        initial_a?: number;
        exploration_rate?: number;
    };
    hho_config?: {
        population_size?: number;
        max_iterations?: number;
        initial_energy?: number;
        jump_probability?: number;
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

/**
 * Result from a single algorithm in comparison
 * Note: Uses 'algorithm' not 'algorithm_used' to match Python AlgorithmResult schema
 */
export interface AlgorithmCompareResult {
    algorithm: string;
    success: boolean;
    routes: VehicleRoute[];
    total_vehicles: number;
    total_duration_minutes: number;
    execution_time_seconds: number;
    error_message?: string;
}

export interface CompareResult {
    success: boolean;
    results: AlgorithmCompareResult[];
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

        if (!response.ok) {
            throw new Error("Failed to fetch strategies");
        }

        return await response.json();
    } catch (error) {
        console.error("Error fetching strategies:", error);
        // Return default strategies including GWO and HHO
        return [
            {
                name: "genetic_algorithm",
                display_name: "Genetik Algoritma",
                description: "Popülasyon tabanlı meta-sezgisel optimizasyon",
                complexity: "O(g × p × n²)",
                recommended: true,
            },
            {
                name: "pso",
                display_name: "Parçacık Sürü Optimizasyonu",
                description: "Sürü zekası tabanlı meta-sezgisel",
                complexity: "O(i × s × n²)",
                recommended: true,
            },
            {
                name: "gwo",
                display_name: "Gri Kurt Optimizasyonu",
                description: "Sosyal hiyerarşi tabanlı meta-sezgisel. Keşif-sömürü dengesi güçlü.",
                complexity: "O(i × p × n²)",
                recommended: true,
            },
            {
                name: "hho",
                display_name: "Harris Hawks Optimizasyonu",
                description: "Şahin avlanma davranışı tabanlı meta-sezgisel. Kaçış enerjisi ile adaptif arama.",
                complexity: "O(i × h × n²)",
                recommended: true,
            },
            {
                name: "greedy",
                display_name: "Greedy (En Yakın Komşu)",
                description: "Hızlı sezgisel algoritma",
                complexity: "O(n²)",
                recommended: false,
            },
            {
                name: "permutation_tsp",
                display_name: "Permütasyon TSP",
                description: "Optimal çözüm (n≤10 için)",
                complexity: "O(n!)",
                recommended: false,
            },
            {
                name: "ortools_cvrp",
                display_name: "OR-Tools CVRP",
                description: "Google OR-Tools ile endüstri standardı çözüm",
                complexity: "O(n³)",
                recommended: false,
            },
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
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                algorithm,
                students: students.map(s => ({
                    id: s.id,
                    name: s.name,
                    location_code: s.location_code,
                    coordinates: s.coordinates,
                    disability_type: s.disability_type,
                })),
                depot: {
                    id: depot.id,
                    lat: depot.lat,
                    lng: depot.lng,
                    type: "depot",
                },
                max_travel_time: options.max_travel_time || 120,
                sw_capacity: options.sw_capacity || 4,
                so_capacity: options.so_capacity || 5,
                ga_config: options.ga_config,
                pso_config: options.pso_config,
                gwo_config: options.gwo_config,
                hho_config: options.hho_config,
            }),
            signal: AbortSignal.timeout(120000), // 2 minute timeout
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
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                students: students.map(s => ({
                    id: s.id,
                    name: s.name,
                    location_code: s.location_code,
                    coordinates: s.coordinates,
                    disability_type: s.disability_type,
                })),
                depot: {
                    id: depot.id,
                    lat: depot.lat,
                    lng: depot.lng,
                    type: "depot",
                },
                max_travel_time: options.max_travel_time || 120,
                sw_capacity: options.sw_capacity || 4,
                so_capacity: options.so_capacity || 5,
                algorithms,
            }),
            signal: AbortSignal.timeout(300000), // 5 minute timeout for comparison
        });

        if (!response.ok) {
            throw new Error(`Compare API error: ${response.status}`);
        }

        const data = await response.json();

        // Map results to use AlgorithmCompareResult interface
        // Note: Python returns 'algorithm' field, not 'algorithm_used'
        const mappedResults: AlgorithmCompareResult[] = (data.results || []).map((r: any) => ({
            algorithm: r.algorithm,
            success: r.success,
            routes: r.routes || [],
            total_vehicles: r.total_vehicles || 0,
            total_duration_minutes: r.total_duration_minutes || 0,
            execution_time_seconds: r.execution_time_seconds || 0,
            error_message: r.error_message,
        }));

        return {
            success: data.success,
            results: mappedResults,
            best_algorithm: data.best_algorithm || "",
            fastest_algorithm: data.fastest_algorithm || "",
            summary: data.summary || {},
        };
    } catch (error: any) {
        console.error("Compare API error:", error);
        return {
            success: false,
            results: [],
            best_algorithm: "",
            fastest_algorithm: "",
            summary: {},
        };
    }
}

/**
 * Calculate vehicle requirements using Python API
 */
export async function calculateVehicles(
    students: StudentForOptimization[],
    depot: Depot,
    options: OptimizationOptions = {}
): Promise<OptimizationResult> {
    // Vehicle calculation uses the same optimize endpoint
    // with default algorithm (GA) if not specified
    return optimizeRoutes(students, depot, {
        ...options,
        algorithm: options.algorithm || "genetic_algorithm",
    });
}

/**
 * Algorithm display names for UI
 */
export const ALGORITHM_DISPLAY_NAMES: Record<string, string> = {
    "genetic_algorithm": "Genetik Algoritma",
    "ga": "Genetik Algoritma",
    "pso": "Parçacık Sürü Optimizasyonu",
    "gwo": "Gri Kurt Optimizasyonu",
    "grey_wolf": "Gri Kurt Optimizasyonu",
    "hho": "Harris Hawks Optimizasyonu",
    "harris_hawks": "Harris Hawks Optimizasyonu",
    "greedy": "Greedy (En Yakın Komşu)",
    "nearest_neighbor": "Greedy (En Yakın Komşu)",
    "permutation_tsp": "Permütasyon (Optimal)",
    "ortools_cvrp": "OR-Tools CVRP",
};

/**
 * Get display name for algorithm
 */
export function getAlgorithmDisplayName(algorithm: string): string {
    return ALGORITHM_DISPLAY_NAMES[algorithm] || algorithm;
}
