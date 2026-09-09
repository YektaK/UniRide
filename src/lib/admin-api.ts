/**
 * Admin API Client - FIXED VERSION
 * Frontend helper to call admin API routes
 * 
 * FIXES:
 * 1. Race condition in auth token handling
 * 2. Added proper token caching with mutex
 * 3. Better error handling
 */

import { getSupabaseClient } from "./supabase";
import type { DudulluReadinessReport } from "@/services/dudullu-readiness";
import { parseDudulluReadinessReport } from "@/services/dudullu-readiness-response";

export class AdminApiAuthenticationError extends Error {
  constructor() {
    super("Not authenticated");
    this.name = "AdminApiAuthenticationError";
  }
}

export class DudulluReadinessRequestError extends Error {
  constructor(public readonly kind: "authorization" | "configuration") {
    super("Dudullu readiness request failed");
    this.name = "DudulluReadinessRequestError";
  }
}

// Token cache with mutex to prevent race conditions
let cachedToken: string | null = null;
let tokenPromise: Promise<string | null> | null = null;
let tokenExpiry: number = 0;
let tokenGeneration = 0;

// Token refresh threshold (refresh if expiring within 5 minutes)
const TOKEN_REFRESH_THRESHOLD_MS = 5 * 60 * 1000;

/**
 * Check if token is about to expire
 */
function isTokenExpiring(expiresAt: number): boolean {
  return Date.now() + TOKEN_REFRESH_THRESHOLD_MS > expiresAt * 1000;
}

function cacheToken(
  generation: number,
  token: string,
  expiresAt?: number,
): string | null {
  if (generation !== tokenGeneration) return null;

  cachedToken = token;
  tokenExpiry = expiresAt ? expiresAt * 1000 : Date.now() + 3600000;
  return token;
}

function clearTokenForGeneration(generation: number): null {
  if (generation === tokenGeneration) {
    cachedToken = null;
    tokenExpiry = 0;
  }
  return null;
}

/**
 * Get auth token with automatic refresh - FIXED with mutex
 */
export async function getAuthToken(): Promise<string | null> {
  const supabase = getSupabaseClient();
  
  console.log("[AdminAPI] getAuthToken called.");
  // If we have a cached token that's not expiring, use it
  if (cachedToken && tokenExpiry > Date.now()) {
    console.log("[AdminAPI] Using cached token.");
    return cachedToken;
  }
  
  // If there's already a refresh in progress, wait for it
  if (tokenPromise) {
    console.log("[AdminAPI] Waiting for existing tokenPromise...");
    return tokenPromise;
  }
  
  console.log("[AdminAPI] Starting new token fetch...");
  // Start a new token fetch
  const generation = tokenGeneration;
  const acquisition = (async () => {
    try {
      console.log("[AdminAPI] Calling supabase.auth.getSession()...");
      // Get session - this will auto-refresh if needed
      const { data: { session }, error } = await supabase.auth.getSession();
      
      console.log("[AdminAPI] getSession returned. Error:", error ? error.message : "None", "Session exists:", !!session);

      if (generation !== tokenGeneration) return null;
      
      if (error) {
        console.error("[AdminAPI] Error getting session:", error);
        // Try manual refresh
        const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession();
        
        if (refreshError) {
          console.error("[AdminAPI] Token refresh failed:", refreshError);
          return clearTokenForGeneration(generation);
        }
        
        if (refreshData.session) {
          return cacheToken(
            generation,
            refreshData.session.access_token,
            refreshData.session.expires_at,
          );
        }
        return clearTokenForGeneration(generation);
      }
      
      if (!session) {
        return clearTokenForGeneration(generation);
      }
      
      // Check if token is about to expire
      if (session.expires_at && isTokenExpiring(session.expires_at)) {
        // Proactively refresh
        const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession();
        
        if (!refreshError && refreshData.session) {
          return cacheToken(
            generation,
            refreshData.session.access_token,
            refreshData.session.expires_at,
          );
        }
      }
      
      return cacheToken(generation, session.access_token, session.expires_at);
      
    } catch (error) {
      console.error("[AdminAPI] Unexpected error in getAuthToken:", error);
      return clearTokenForGeneration(generation);
    }
  })();
  tokenPromise = acquisition;
  const detach = () => {
    if (generation === tokenGeneration && tokenPromise === acquisition) {
      tokenPromise = null;
    }
  };
  void acquisition.then(detach, detach);

  return acquisition;
}

/**
 * Clear cached token (call on logout)
 */
export function clearAuthTokenCache(): void {
  tokenGeneration += 1;
  cachedToken = null;
  tokenExpiry = 0;
  tokenPromise = null;
}

function waitForPromiseWithSignal<T>(promise: Promise<T>, signal: AbortSignal): Promise<T> {
  if (signal.aborted) return Promise.reject(signal.reason);

  return new Promise<T>((resolve, reject) => {
    const cleanup = () => signal.removeEventListener("abort", onAbort);
    const onAbort = () => {
      cleanup();
      reject(signal.reason);
    };

    signal.addEventListener("abort", onAbort, { once: true });
    promise.then(
      (value) => {
        cleanup();
        resolve(value);
      },
      (error) => {
        cleanup();
        reject(error);
      },
    );
  });
}

/**
 * Helper to make authenticated API requests
 */
async function adminFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const tokenRequest = getAuthToken();
  const token = options.signal
    ? await waitForPromiseWithSignal(tokenRequest, options.signal)
    : await tokenRequest;

  if (!token) {
    throw new AdminApiAuthenticationError();
  }

  return fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
      ...options.headers,
    },
  });
}

const DUDULLU_READINESS_TIMEOUT_MS = 15_000;

async function getDudulluReadiness(): Promise<DudulluReadinessReport> {
  let response: Response;
  try {
    response = await adminFetch("/api/admin/dudullu-readiness", {
      method: "GET",
      cache: "no-store",
      signal: AbortSignal.timeout(DUDULLU_READINESS_TIMEOUT_MS),
    });
  } catch (error) {
    throw new DudulluReadinessRequestError(
      error instanceof AdminApiAuthenticationError ? "authorization" : "configuration",
    );
  }

  if (response.status === 401 || response.status === 403) {
    throw new DudulluReadinessRequestError("authorization");
  }
  if (!response.ok) {
    throw new DudulluReadinessRequestError("configuration");
  }

  try {
    return parseDudulluReadinessReport(await response.json());
  } catch {
    throw new DudulluReadinessRequestError("configuration");
  }
}

// ==================== USERS ====================

export const adminApi = {
  readiness: {
    getDudullu: getDudulluReadiness,
  },

  users: {
    /**
     * Get all users with pagination
     */
    async getAll(page: number = 1, limit: number = 50) {
      const params = new URLSearchParams({
        page: String(page),
        limit: String(Math.min(limit, 100)),
      });
      const res = await adminFetch(`/api/admin/users?${params}`);
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || "Failed to fetch users");
      }
      return res.json();
    },

    async create(userData: {
      email: string;
      password: string;
      name: string;
      role: string;
      studentNumber?: string;
      homeAddress?: string;
      accessibilityNeeds?: string[];
    }) {
      const res = await adminFetch("/api/admin/users", {
        method: "POST",
        body: JSON.stringify(userData),
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || "Failed to create user");
      }
      return res.json();
    },

    async update(
      id: string,
      updates: Partial<{
        name: string;
        role: string;
        studentNumber: string;
        homeAddress: string;
        accessibilityNeeds: string[];
      }>
    ) {
      const res = await adminFetch("/api/admin/users", {
        method: "PUT",
        body: JSON.stringify({ id, ...updates }),
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || "Failed to update user");
      }
      return res.json();
    },

    async delete(id: string) {
      const res = await adminFetch(`/api/admin/users?id=${id}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || "Failed to delete user");
      }
      return res.json();
    },

    async resetPassword(userId: string, newPassword: string) {
      const res = await adminFetch("/api/admin/users/password", {
        method: "PATCH",
        body: JSON.stringify({ userId, newPassword }),
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || "Şifre güncellenemedi.");
      }
      return res.json();
    },
  },

  // ==================== VEHICLES ====================

  vehicles: {
    async calculate(input: {
      students: Array<Record<string, unknown>>;
      maxTourTime?: number;
      swCapacity?: number;
      soCapacity?: number;
      strategy?: string;
      clusteringAlgorithm?: string;
      local_search_type?: "none" | "two_opt" | "three_opt" | "or_opt" | "hybrid";
      direction?: "pickup" | "dropoff";
    }) {
      const response = await adminFetch("/api/calculate-vehicles", {
        method: "POST",
        body: JSON.stringify(input),
      });
      if (!response.ok) throw new Error("Vehicle calculation failed");
      return response.json();
    },

    async getAll() {
      const res = await adminFetch("/api/admin/vehicles");
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || "Failed to fetch vehicles");
      }
      return res.json();
    },

    async create(vehicleData: {
      name: string;
      type: string;
      plateNumber?: string;
      wheelchairCapacity?: number;
      seatingCapacity?: number;
      cooldownMinutes?: number;
      status?: string;
    }) {
      const res = await adminFetch("/api/admin/vehicles", {
        method: "POST",
        body: JSON.stringify(vehicleData),
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || "Failed to create vehicle");
      }
      return res.json();
    },

    async update(
      id: string,
      updates: Partial<{
        name: string;
        type: string;
        plateNumber: string;
        wheelchairCapacity: number;
        seatingCapacity: number;
        cooldownMinutes: number;
        status: string;
      }>
    ) {
      const res = await adminFetch("/api/admin/vehicles", {
        method: "PUT",
        body: JSON.stringify({ id, ...updates }),
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || "Failed to update vehicle");
      }
      return res.json();
    },

    async delete(id: string) {
      const res = await adminFetch(`/api/admin/vehicles?id=${id}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || "Failed to delete vehicle");
      }
      return res.json();
    },
  },

  // ==================== RIDE REQUESTS ====================

  rideRequests: {
    async getAll(filters?: { status?: string; userId?: string; page?: number; limit?: number }) {
      const params = new URLSearchParams();
      if (filters?.status) params.set("status", filters.status);
      if (filters?.userId) params.set("userId", filters.userId);
      if (filters?.page) params.set("page", String(filters.page));
      if (filters?.limit) params.set("limit", String(Math.min(filters.limit, 100)));
      
      const url = `/api/admin/ride-requests${params.toString() ? `?${params.toString()}` : ""}`;
      const res = await adminFetch(url);
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || "Failed to fetch ride requests");
      }
      return res.json();
    },

    async updateStatus(
      id: string,
      updates: {
        status?: string;
        vehicleId?: string;
        notes?: string;
      }
    ) {
      const res = await adminFetch("/api/admin/ride-requests", {
        method: "PUT",
        body: JSON.stringify({ id, ...updates }),
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || "Failed to update ride request");
      }
      return res.json();
    },

    async delete(id: string) {
      const res = await adminFetch(`/api/admin/ride-requests?id=${id}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || "Failed to delete ride request");
      }
      return res.json();
    },
  },

  // ==================== ROUTE OPTIMIZATION ====================

  routes: {
    async getStrategies() {
      const res = await adminFetch("/api/optimize-route");
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || "Failed to fetch strategies");
      }
      return res.json();
    },

    async optimize(params: {
      start: string;
      end: string;
      waypoints: string[];
      strategy?: string;
      local_search_type?: "none" | "two_opt" | "three_opt" | "or_opt" | "hybrid";
      max_travel_time?: number;
    }) {
      // Map route-test simple waypoints format to standard API format
      const students = params.waypoints.map((wp, index) => ({
        id: `test-${index}`,
        name: `Test Waypoint ${wp}`,
        location_code: wp,
        disability_type: wp.startsWith("Sw") ? "Sw" : "So"
      }));

      const payload = {
        students,
        depot: { id: params.start || "D.Kampus", lat: 41.001, lng: 29.177 },
        algorithm: params.strategy || "genetic_algorithm",
        local_search_type: params.local_search_type,
        max_travel_time: params.max_travel_time ?? 120,
        sw_capacity: 4,
        so_capacity: 5
      };

      const res = await adminFetch("/api/optimize-route", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || "Failed to optimize route");
      }
      return res.json();
    },
  },
};
