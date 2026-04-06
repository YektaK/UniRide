/**
 * Optimizer Service
 * Calls Python Optimization API for route optimization
 * Provides fallback to local calculation if API is unavailable
 * 
 * UPDATE: Added local_search_type support and two_opt strategy
 */

import { OPTIMIZER_API_URL } from "@/lib/config";

// Local Search Type - can be used within any strategy
export type LocalSearchType = "2opt" | "3opt" | "or_opt" | "hybrid";

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
    algorithm?: "genetic_algorithm" | "ga" | "pso" | "gwo" | "grey_wolf" | "hho" | "harris_hawks" | "two_opt" | "2opt" | "greedy" | "permutation_tsp" | "ortools_cvrp";
    max_travel_time?: number;
    sw_capacity?: number;
    so_capacity?: number;
    // Local search type - applies to all meta-heuristic algorithms
    local_search_type?: LocalSearchType;
    ga_config?: {
        population_size?: number;
        max_iterations?: number;
        crossover_rate?: number;
        mutation_rate?: number;
        local_search_rate?: number;
        local_search_type?: LocalSearchType;
    };
    pso_config?: {
        swarm_size?: number;
        max_iterations?: number;
        inertia_weight?: number;
        local_search_rate?: number;
        local_search_type?: LocalSearchType;
    };
    gwo_config?: {
        population_size?: number;
        max_iterations?: number;
        initial_a?: number;
        exploration_rate?: number;
        local_search_type?: LocalSearchType;
    };
    hho_config?: {
        population_size?: number;
        max_iterations?: number;
        initial_energy?: number;
        jump_probability?: number;
        local_search_type?: LocalSearchType;
    };
    two_opt_config?: {
        max_iterations?: number;
        multi_start?: boolean;
        num_starts?: number;
        first_improvement?: boolean;
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
    supports_local_search?: boolean;
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
        return [
            {
                name: "genetic_algorithm",
                display_name: "Genetik Algoritma",
                description: "Popülasyon tabanlı meta-sezgisel optimizasyon",
                complexity: "O(g × p × n²)",
                recommended: true,
                supports_local_search: true,
            },
            {
                name: "pso",
                display_name: "Parçacık Sürü Optimizasyonu",
                description: "Sürü zekası tabanlı meta-sezgisel",
                complexity: "O(i × s × n²)",
                recommended: true,
                supports_local_search: true,
            },
            {
                name: "gwo",
                display_name: "Gri Kurt Optimizasyonu",
                description: "Sosyal hiyerarşi tabanlı meta-sezgisel",
                complexity: "O(i × p × n²)",
                recommended: true,
                supports_local_search: true,
            },
            {
                name: "hho",
                display_name: "Harris Hawks Optimizasyonu",
                description: "Şahin avlanma davranışı tabanlı meta-sezgisel",
                complexity: "O(i × h × n²)",
                recommended: true,
                supports_local_search: true,
            },
            {
                name: "two_opt",
                display_name: "2-Opt Yerel Arama",
                description: "Klasik yerel arama. Hızlı ve etkili.",
                complexity: "O(k × n²)",
                recommended: false,
                supports_local_search: false,
            },
            {
                name: "greedy",
                display_name: "Greedy (En Yakın Komşu)",
                description: "Hızlı sezgisel algoritma",
                complexity: "O(n²)",
                recommended: false,
                supports_local_search: false,
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
                local_search_type: options.local_search_type,
                ga_config: options.ga_config,
                pso_config: options.pso_config,
                gwo_config: options.gwo_config,
                hho_config: options.hho_config,
                two_opt_config: options.two_opt_config,
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
                local_search_type: options.local_search_type,
                algorithms,
            }),
            signal: AbortSignal.timeout(300000),
        });

        if (!response.ok) throw new Error(`Compare API error: ${response.status}`);

        const data = await response.json();
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
        return { success: false, results: [], best_algorithm: "", fastest_algorithm: "", summary: {} };
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
    "two_opt": "2-Opt Yerel Arama",
    "2opt": "2-Opt Yerel Arama",
    "greedy": "Greedy (En Yakın Komşu)",
    "nearest_neighbor": "Greedy (En Yakın Komşu)",
    "permutation_tsp": "Permütasyon (Optimal)",
    "ortools_cvrp": "OR-Tools CVRP",
};

/**
 * Local Search display names for UI
 */
export const LOCAL_SEARCH_DISPLAY_NAMES: Record<string, string> = {
    "2opt": "2-Opt (Klasik)",
    "3opt": "3-Opt (Daha Güçlü)",
    "or_opt": "Or-Opt (Node Relocation)",
    "hybrid": "Hibrit (2-Opt + Or-Opt)",
};

export function getAlgorithmDisplayName(algorithm: string): string {
    return ALGORITHM_DISPLAY_NAMES[algorithm] || algorithm;
}

export function getLocalSearchDisplayName(localSearchType: string): string {
    return LOCAL_SEARCH_DISPLAY_NAMES[localSearchType] || localSearchType;
}

export const ALGORITHMS_WITH_LOCAL_SEARCH = [
    "genetic_algorithm", "ga", "pso", "gwo", "grey_wolf", "hho", "harris_hawks",
];

export function algorithmSupportsLocalSearch(algorithm: string): boolean {
    return ALGORITHMS_WITH_LOCAL_SEARCH.includes(algorithm.toLowerCase());
}
