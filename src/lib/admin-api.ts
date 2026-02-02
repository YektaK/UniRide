/**
 * Admin API Client
 * Frontend helper to call admin API routes
 */

import { getSupabaseClient } from "./supabase";

// Helper to get auth token with automatic refresh
async function getAuthToken(): Promise<string | null> {
    const supabase = getSupabaseClient();

    // First try to get fresh session - this will auto-refresh if needed
    const { data: { session }, error } = await supabase.auth.getSession();

    if (error) {
        console.error("Error getting session:", error);
        // Try to refresh manually
        const { data: refreshData } = await supabase.auth.refreshSession();
        return refreshData.session?.access_token || null;
    }

    // If session exists but might be stale, verify with getUser
    if (session?.access_token) {
        // getUser() will fail if token is truly expired, triggering a refresh
        const { error: userError } = await supabase.auth.getUser();
        if (userError) {
            // Token is expired, try refresh
            const { data: refreshData } = await supabase.auth.refreshSession();
            return refreshData.session?.access_token || null;
        }
        return session.access_token;
    }

    return null;
}

// Helper to make authenticated API requests
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
        async getAll() {
            const res = await adminFetch("/api/admin/users");
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

        async update(id: string, updates: Partial<{
            name: string;
            role: string;
            studentNumber: string;
            homeAddress: string;
            accessibilityNeeds: string[];
        }>) {
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

        async update(id: string, updates: Partial<{
            name: string;
            type: string;
            plateNumber: string;
            wheelchairCapacity: number;
            seatingCapacity: number;
            status: string;
        }>) {
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
        async getAll(filters?: { status?: string; userId?: string }) {
            let url = "/api/admin/ride-requests";
            const params = new URLSearchParams();
            if (filters?.status) params.set("status", filters.status);
            if (filters?.userId) params.set("userId", filters.userId);
            if (params.toString()) url += `?${params.toString()}`;

            const res = await adminFetch(url);
            if (!res.ok) {
                const error = await res.json();
                throw new Error(error.error || "Failed to fetch ride requests");
            }
            return res.json();
        },

        async updateStatus(id: string, updates: {
            status?: string;
            vehicleId?: string;
            notes?: string;
        }) {
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
