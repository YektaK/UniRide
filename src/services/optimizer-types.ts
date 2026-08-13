export interface AppliedPolicyLimitInfo {
  value: number;
  source: "profile_default" | "server_override" | "caller" | "strategy_default";
  enforcement: string;
}

export interface AppliedComputePolicyInfo {
  profile_id: string;
  algorithm_requested?: string;
  algorithm_canonical?: string;
  student_count: number;
  vehicle_count: number;
  cancellation_mode: "none" | "soft_response_deadline";
  limits: Record<string, AppliedPolicyLimitInfo>;
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
  departure_time?: string;
  arrival_times?: Record<string, string>;
  time_window_violations?: number;
}

export interface AlgorithmCompareResult {
  algorithm: string;
  success: boolean;
  routes: VehicleRoute[];
  total_vehicles: number;
  total_duration_minutes: number;
  execution_time_seconds: number;
  error_message?: string;
  algorithm_requested?: string;
  feasibility_certificate?: unknown;
  applied_policy?: AppliedComputePolicyInfo;
}

export interface CompareResult {
  success: boolean;
  results: AlgorithmCompareResult[];
  best_algorithm: string;
  fastest_algorithm: string;
  summary: Record<string, { total_vehicles: number; total_duration_minutes: number; execution_time_seconds: number; success: boolean }>;
  algorithm_requested?: string;
  feasibility_certificate?: unknown;
  applied_policy?: AppliedComputePolicyInfo;
}
