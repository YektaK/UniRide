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

// Token cache with mutex to prevent race conditions
let cachedToken: string | null = null;
let tokenPromise: Promise<string | null> | null = null;
let tokenExpiry: number = 0;

// Token refresh threshold (refresh if expiring within 5 minutes)
const TOKEN_REFRESH_THRESHOLD_MS = 5 * 60 * 1000;

/**
 * Check if token is about to expire
 */
function isTokenExpiring(expiresAt: number): boolean {
  return Date.now() + TOKEN_REFRESH_THRESHOLD_MS > expiresAt * 1000;
}

/**
 * Get auth token with automatic refresh - FIXED with mutex
 */
async function getAuthToken(): Promise<string | null> {
  const supabase = getSupabaseClient();
  
  // If we have a cached token that's not expiring, use it
  if (cachedToken && tokenExpiry > Date.now()) {
    return cachedToken;
  }
  
  // If there's already a refresh in progress, wait for it
  if (tokenPromise) {
    return tokenPromise;
  }
  
  // Start a new token fetch
  tokenPromise = (async () => {
    try {
      // Get session - this will auto-refresh if needed
      const { data: { session }, error } = await supabase.auth.getSession();
      
      if (error) {
        console.error("[AdminAPI] Error getting session:", error);
        // Try manual refresh
        const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession();
        
        if (refreshError) {
          console.error("[AdminAPI] Token refresh failed:", refreshError);
          cachedToken = null;
          tokenExpiry = 0;
          return null;
        }
        
        if (refreshData.session) {
          cachedToken = refreshData.session.access_token;
          tokenExpiry = refreshData.session.expires_at ? refreshData.session.expires_at * 1000 : Date.now() + 3600000;
          return cachedToken;
        }
        return null;
      }
      
      if (!session) {
        cachedToken = null;
        tokenExpiry = 0;
        return null;
      }
      
      // Check if token is about to expire
      if (session.expires_at && isTokenExpiring(session.expires_at)) {
        // Proactively refresh
        const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession();
        
        if (!refreshError && refreshData.session) {
          cachedToken = refreshData.session.access_token;
          tokenExpiry = refreshData.session.expires_at ? refreshData.session.expires_at * 1000 : Date.now() + 3600000;
          return cachedToken;
        }
      }
      
      cachedToken = session.access_token;
      tokenExpiry = session.expires_at ? session.expires_at * 1000 : Date.now() + 3600000;
      return session.access_token;
      
    } catch (error) {
      console.error("[AdminAPI] Unexpected error in getAuthToken:", error);
      cachedToken = null;
      tokenExpiry = 0;
      return null;
    } finally {
      // Clear the promise so future calls can start fresh
      tokenPromise = null;
    }
  })();
  
  return tokenPromise;
}

/**
 * Clear cached token (call on logout)
 */
export function clearAuthTokenCache(): void {
  cachedToken = null;
  tokenExpiry = 0;
  tokenPromise = null;
}

/**
 * Helper to make authenticated API requests
 */
async function adminFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = await getAuthToken();

  if (!token) {
    throw new Error("Not authenticated");
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

// ==================== USERS ====================

export const adminApi = {
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
    }) {
      const res = await adminFetch("/api/optimize-route", {
        method: "POST",
        body: JSON.stringify(params),
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || "Failed to optimize route");
      }
      return res.json();
    },
  },
};
