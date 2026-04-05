/**
 * Optimizer Service
 * Calls Python Optimization API for route optimization
 * Provides fallback to local calculation if API is unavailable
 */

import { OPTIMIZER_API_URL } from "@/lib/config";
import type { IERawData } from "@/types/ie-resource";

// Types
export type LocalSearchType = "none" | "two_opt" | "three_opt" | "or_opt" | "hybrid";
export type DirectionType = "pickup" | "dropoff";

export interface StudentForOptimization {
    id: string;
    name: string;
    location_code: string;
    coordinates?: { lat: number; lng: number };
    disability_type: "Sw" | "So";
    // CVRPTW fields
    pickup_time?: string;  // Target arrival at school (HH:MM)
    dropoff_time?: string; // Target departure from school (HH:MM)
}

export interface Depot {
    id: string;
    lat: number;
    lng: number;
}

export interface VehicleConfig {
    vehicleId: string;
    swCapacity: number;
    soCapacity: number;
    cooldownMinutes?: number;
}

export interface OptimizationOptions {
    algorithm?: "genetic_algorithm" | "ga" | "pso" | "gwo" | "grey_wolf" | "hho" | "harris_hawks" | "two_opt" | "greedy" | "permutation_tsp" | "ortools_cvrp" | "ga_split" | "pso_split" | "gwo_split" | "hho_split";
    max_travel_time?: number;  // minutes
    sw_capacity?: number;
    so_capacity?: number;
    local_search_type?: LocalSearchType;
    clustering_algorithm?: string;
    // IE Sandbox mode - custom vehicle configurations
    vehicles?: VehicleConfig[];
    // CVRPTW options
    direction?: DirectionType;           // "pickup" or "dropoff"
    use_time_windows?: boolean;          // Enable time window constraints
    target_time?: string;                // Global target time (HH:MM)
    time_window_size?: number;           // Time window size in minutes (default: 30)
    offset_minutes?: number;             // Buffer for driver notification (default: 10)
    ga_config?: {
        population_size?: number;
        max_iterations?: number;
        crossover_rate?: number;
        mutation_rate?: number;
        local_search_type?: LocalSearchType;
    };
    pso_config?: {
        swarm_size?: number;
        max_iterations?: number;
        inertia_weight?: number;
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
    // CVRPTW fields
    departure_time?: string;              // Vehicle departure time (HH:MM)
    arrival_times?: Record<string, string>; // Arrival at each location {location: HH:MM}
    time_window_violations?: number;       // Number of time window violations
}

export interface OptimizationResult {
    success: boolean;
    algorithm_used: string;
    routes: VehicleRoute[];
    total_vehicles: number;
    total_duration_minutes: number;
    execution_time_seconds: number;
    error_message?: string;
    // IE Resource analysis data (raw from Python API)
    ie_data?: IERawData;
    // CVRPTW fields
    direction?: DirectionType;
    time_windows_used?: boolean;
    total_time_window_violations?: number;
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
        // Return default strategies including GWO, HHO, and Two-Opt
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
                name: "two_opt",
                display_name: "Two-Opt Local Search",
                description: "Klasik 2-opt yerel arama algoritması. Küçük-orta ölçekli problemler için ideal.",
                complexity: "O(n²)",
                recommended: false,
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
                    // CVRPTW fields
                    pickup_time: s.pickup_time,
                    dropoff_time: s.dropoff_time,
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
                local_search_type: options.local_search_type || "two_opt",
                clustering_algorithm: options.clustering_algorithm || "sweep",
                vehicles: options.vehicles,
                // CVRPTW options
                direction: options.direction || "pickup",
                use_time_windows: options.use_time_windows ?? false,
                target_time: options.target_time,
                time_window_size: options.time_window_size || 30,
                offset_minutes: options.offset_minutes || 10,
                // Algorithm configs
                ga_config: options.ga_config,
                pso_config: options.pso_config,
                gwo_config: options.gwo_config,
                hho_config: options.hho_config,
                two_opt_config: options.two_opt_config,
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
            // CVRPTW fields
            direction: data.direction,
            time_windows_used: data.time_windows_used,
            total_time_window_violations: data.total_time_window_violations,
        };
    } catch (error: unknown) {
        console.error("Optimization API error:", error);
        return {
            success: false,
            algorithm_used: algorithm,
            routes: [],
            total_vehicles: 0,
            total_duration_minutes: 0,
            execution_time_seconds: 0,
            error_message: error instanceof Error ? error.message : "Optimization failed",
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
                    // CVRPTW fields
                    pickup_time: s.pickup_time,
                    dropoff_time: s.dropoff_time,
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
                // CVRPTW options
                direction: options.direction || "pickup",
                use_time_windows: options.use_time_windows ?? false,
            }),
            signal: AbortSignal.timeout(300000), // 5 minute timeout for comparison
        });

        if (!response.ok) {
            throw new Error(`Compare API error: ${response.status}`);
        }

        const data = await response.json();

        // Map results to use AlgorithmCompareResult interface
        // Note: Python returns 'algorithm' field, not 'algorithm_used'
        const mappedResults: AlgorithmCompareResult[] = (data.results || []).map((r: AlgorithmCompareResult) => ({
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
    } catch (error: unknown) {
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
    "two_opt": "Two-Opt Local Search",
    "greedy": "Greedy (En Yakın Komşu)",
    "nearest_neighbor": "Greedy (En Yakın Komşu)",
    "permutation_tsp": "Permütasyon (Optimal)",
    "ortools_cvrp": "OR-Tools CVRP",
    // Split algorithms (Pipeline B)
    "ga_split": "GA-Split (Route-First)",
    "pso_split": "PSO-Split (Route-First)",
    "gwo_split": "GWO-Split (Route-First)",
    "hho_split": "HHO-Split (Route-First)",
};

/**
 * Local search display names for UI
 */
export const LOCAL_SEARCH_DISPLAY_NAMES: Record<LocalSearchType, string> = {
    "none": "Yok",
    "two_opt": "2-Opt (Klasik)",
    "three_opt": "3-Opt (Yüksek Kalite)",
    "or_opt": "Or-Opt (Kümeleme)",
    "hybrid": "Hibrit (Kombine)",
};

/**
 * Direction display names for UI
 */
export const DIRECTION_DISPLAY_NAMES: Record<DirectionType, string> = {
    "pickup": "Geliş (Okula Getirme)",
    "dropoff": "Gidiş (Okuldan Bırakma)",
};

/**
 * Get display name for algorithm
 */
export function getAlgorithmDisplayName(algorithm: string): string {
    return ALGORITHM_DISPLAY_NAMES[algorithm] || algorithm;
}

/**
 * Get display name for local search type
 */
export function getLocalSearchDisplayName(type: LocalSearchType): string {
    return LOCAL_SEARCH_DISPLAY_NAMES[type] || type;
}

/**
 * Get display name for direction
 */
export function getDirectionDisplayName(direction: DirectionType): string {
    return DIRECTION_DISPLAY_NAMES[direction] || direction;
}
