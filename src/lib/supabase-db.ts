/**
 * Supabase Database Helper Functions
 * Replaces firebase-db.ts
 */

import { getSupabaseClient } from "./supabase";
import type {
    FirestoreUser,
    FirestoreWeeklySchedule,
    FirestoreRideRequest,
    FirestoreVehicle,
    RouteAssignment,
    Route,
} from "@/types/firestore";
import type { ScheduleEntry } from "@/types";

// Helper to get Supabase client
const getClient = () => getSupabaseClient();

// ==================== HELPERS ====================

/**
 * Convert snake_case keys to camelCase
 */
const toCamelCase = (obj: any): any => {
    if (obj === null || obj === undefined) {
        return obj;
    }
    if (Array.isArray(obj)) {
        return obj.map((v) => toCamelCase(v));
    } else if (obj.constructor === Object) {
        return Object.keys(obj).reduce(
            (result, key) => {
                const camelKey = key.replace(/_([a-z])/g, (g) => g[1].toUpperCase());
                result[camelKey] = toCamelCase(obj[key]);
                return result;
            },
            {} as any
        );
    }
    return obj;
};

/**
 * Convert camelCase keys to snake_case
 */
const toSnakeCase = (obj: any): any => {
    if (obj === null || obj === undefined) {
        return obj;
    }
    if (Array.isArray(obj)) {
        return obj.map((v) => toSnakeCase(v));
    } else if (obj.constructor === Object) {
        return Object.keys(obj).reduce(
            (result, key) => {
                const snakeKey = key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
                result[snakeKey] = toSnakeCase(obj[key]);
                return result;
            },
            {} as any
        );
    }
    return obj;
};

// ==================== USER OPERATIONS ====================

export const getUserById = async (userId: string): Promise<FirestoreUser | null> => {
    const { data, error } = await getClient()
        .from("users")
        .select("*")
        .eq("id", userId)
        .single();

    if (error) {
        if (error.code === "PGRST116") return null; // Not found
        console.error("Error getting user:", error);
        throw error;
    }

    return toCamelCase(data) as FirestoreUser;
};

export const getUserByEmail = async (email: string): Promise<FirestoreUser | null> => {
    const { data, error } = await getClient()
        .from("users")
        .select("*")
        .eq("email", email.toLowerCase())
        .single();

    if (error) {
        // PGRST116 = not found, 42501 = RLS policy violation (expected when no session)
        if (error.code === "PGRST116" || error.code === "42501") return null;
        console.error("Error getting user by email:", error);
        throw error;
    }

    return toCamelCase(data) as FirestoreUser;
};

export const getUserByStudentNumber = async (studentNumber: string): Promise<FirestoreUser | null> => {
    const { data, error } = await getClient()
        .from("users")
        .select("*")
        .eq("student_number", studentNumber)
        .single();

    if (error) {
        if (error.code === "PGRST116") return null;
        console.error("Error getting user by student number:", error);
        throw error;
    }

    return toCamelCase(data) as FirestoreUser;
};

export const getAllUsers = async (): Promise<FirestoreUser[]> => {
    const { data, error } = await getClient().from("users").select("*");

    if (error) {
        console.error("Error getting all users:", error);
        throw error;
    }

    return data.map(toCamelCase) as FirestoreUser[];
};

export const createUser = async (
    userData: Omit<FirestoreUser, "id" | "createdAt" | "updatedAt"> | FirestoreUser,
    userId?: string
): Promise<FirestoreUser> => {
    const now = new Date().toISOString();

    // Remove any existing id, createdAt, updatedAt from userData to avoid conflicts
    const { id: _id, createdAt: _ca, updatedAt: _ua, ...cleanUserData } = userData as any;

    const dbData = toSnakeCase({
        ...cleanUserData,
        id: userId,
        created_at: now,
        updated_at: now,
    });

    // If userId is not provided, let Supabase generate it
    if (!userId) {
        delete dbData.id;
    }

    const { data, error } = await getClient()
        .from("users")
        .insert(dbData)
        .select()
        .single();

    if (error) {
        console.error("Error creating user:", error);
        throw error;
    }

    return toCamelCase(data) as FirestoreUser;
};

export const updateUser = async (
    userId: string,
    updates: Partial<Omit<FirestoreUser, "id" | "createdAt">>
): Promise<void> => {
    const dbUpdates = toSnakeCase({
        ...updates,
        updated_at: new Date().toISOString(),
    });

    const { error } = await getClient()
        .from("users")
        .update(dbUpdates)
        .eq("id", userId);

    if (error) {
        console.error("Error updating user:", error);
        throw error;
    }
};

export const deleteUser = async (userId: string): Promise<void> => {
    const { error } = await getClient().from("users").delete().eq("id", userId);

    if (error) {
        console.error("Error deleting user:", error);
        throw error;
    }
};

// ==================== SCHEDULE OPERATIONS ====================

export const getScheduleById = async (scheduleId: string): Promise<FirestoreWeeklySchedule | null> => {
    const { data, error } = await getClient()
        .from("weekly_schedules")
        .select("*")
        .eq("id", scheduleId)
        .single();

    if (error) {
        if (error.code === "PGRST116") return null;
        console.error("Error getting schedule:", error);
        throw error;
    }

    // entries is JSONB, so it might need special handling if toCamelCase doesn't cover it deep enough
    // But toCamelCase is recursive, so it should be fine.
    return toCamelCase(data) as FirestoreWeeklySchedule;
};

export const getScheduleByUserId = async (userId: string): Promise<FirestoreWeeklySchedule | null> => {
    const { data, error } = await getClient()
        .from("weekly_schedules")
        .select("*")
        .eq("user_id", userId)
        .single();

    if (error) {
        if (error.code === "PGRST116") return null;
        console.error("Error getting schedule by user id:", error);
        throw error;
    }

    return toCamelCase(data) as FirestoreWeeklySchedule;
};

export const createSchedule = async (
    scheduleData: Omit<FirestoreWeeklySchedule, "id" | "createdAt" | "updatedAt">,
    scheduleId?: string
): Promise<FirestoreWeeklySchedule> => {
    const now = new Date().toISOString();
    const dbData = toSnakeCase({
        ...scheduleData,
        id: scheduleId,
        last_updated: now,
        created_at: now,
        updated_at: now,
    });

    if (!scheduleId) delete dbData.id;

    const { data, error } = await getClient()
        .from("weekly_schedules")
        .insert(dbData)
        .select()
        .single();

    if (error) {
        console.error("Error creating schedule:", error);
        throw error;
    }

    return toCamelCase(data) as FirestoreWeeklySchedule;
};

export const updateSchedule = async (
    scheduleId: string,
    updates: Partial<Omit<FirestoreWeeklySchedule, "id" | "createdAt">>
): Promise<void> => {
    const dbUpdates = toSnakeCase({
        ...updates,
        last_updated: new Date().toISOString(),
        updated_at: new Date().toISOString(),
    });

    const { error } = await getClient()
        .from("weekly_schedules")
        .update(dbUpdates)
        .eq("id", scheduleId);

    if (error) {
        console.error("Error updating schedule:", error);
        throw error;
    }
};

export const updateScheduleEntries = async (
    scheduleId: string,
    entries: any[]
): Promise<void> => {
    // entries is a JSON array, Supabase handles it as JSONB
    await updateSchedule(scheduleId, { entries, lastUpdated: new Date().toISOString() } as any);
};

// ==================== RIDE REQUEST OPERATIONS ====================

export const getRideRequestById = async (requestId: string): Promise<FirestoreRideRequest | null> => {
    const { data, error } = await getClient()
        .from("ride_requests")
        .select("*")
        .eq("id", requestId)
        .single();

    if (error) {
        if (error.code === "PGRST116") return null;
        console.error("Error getting ride request:", error);
        throw error;
    }

    return toCamelCase(data) as FirestoreRideRequest;
};

export const getAllRideRequests = async (
    filters?: {
        userId?: string;
        status?: string;
        type?: string;
        dateFrom?: string;
        dateTo?: string;
    }
): Promise<FirestoreRideRequest[]> => {
    let query = getClient().from("ride_requests").select("*");

    if (filters?.userId) query = query.eq("user_id", filters.userId);
    if (filters?.status) query = query.eq("status", filters.status);
    if (filters?.type) query = query.eq("type", filters.type);
    if (filters?.dateFrom) query = query.gte("requested_pickup_time", filters.dateFrom);
    if (filters?.dateTo) query = query.lte("requested_pickup_time", filters.dateTo);

    query = query.order("created_at", { ascending: false });

    const { data, error } = await query;

    if (error) {
        console.error("Error getting ride requests:", error);
        throw error;
    }

    return data.map(toCamelCase) as FirestoreRideRequest[];
};

export const createRideRequest = async (
    requestData: Omit<FirestoreRideRequest, "id" | "createdAt" | "updatedAt">,
    requestId?: string
): Promise<FirestoreRideRequest> => {
    const now = new Date().toISOString();
    const dbData = toSnakeCase({
        ...requestData,
        id: requestId,
        created_at: now,
        updated_at: now,
    });

    if (!requestId) delete dbData.id;

    const { data, error } = await getClient()
        .from("ride_requests")
        .insert(dbData)
        .select()
        .single();

    if (error) {
        console.error("Error creating ride request:", error);
        throw error;
    }

    return toCamelCase(data) as FirestoreRideRequest;
};

export const updateRideRequest = async (
    requestId: string,
    updates: Partial<Omit<FirestoreRideRequest, "id" | "createdAt">>
): Promise<void> => {
    const dbUpdates = toSnakeCase({
        ...updates,
        updated_at: new Date().toISOString(),
    });

    const { error } = await getClient()
        .from("ride_requests")
        .update(dbUpdates)
        .eq("id", requestId);

    if (error) {
        console.error("Error updating ride request:", error);
        throw error;
    }
};

export const deleteRideRequest = async (requestId: string): Promise<void> => {
    const { error } = await getClient().from("ride_requests").delete().eq("id", requestId);

    if (error) {
        console.error("Error deleting ride request:", error);
        throw error;
    }
};

// ==================== VEHICLE OPERATIONS ====================

export const getAllVehicles = async (): Promise<FirestoreVehicle[]> => {
    const { data, error } = await getClient().from("vehicles").select("*");

    if (error) {
        console.error("Error getting vehicles:", error);
        throw error;
    }

    return data.map(toCamelCase) as FirestoreVehicle[];
};

export const getVehicleById = async (vehicleId: string): Promise<FirestoreVehicle | null> => {
    const { data, error } = await getClient()
        .from("vehicles")
        .select("*")
        .eq("id", vehicleId)
        .single();

    if (error) {
        if (error.code === "PGRST116") return null;
        console.error("Error getting vehicle:", error);
        throw error;
    }

    return toCamelCase(data) as FirestoreVehicle;
};

export const createVehicle = async (
    vehicleData: Omit<FirestoreVehicle, "id" | "createdAt" | "updatedAt">,
    vehicleId?: string
): Promise<FirestoreVehicle> => {
    const now = new Date().toISOString();
    const dbData = toSnakeCase({
        ...vehicleData,
        id: vehicleId,
        created_at: now,
        updated_at: now,
    });

    if (!vehicleId) delete dbData.id;

    const { data, error } = await getClient()
        .from("vehicles")
        .insert(dbData)
        .select()
        .single();

    if (error) {
        console.error("Error creating vehicle:", error);
        throw error;
    }

    return toCamelCase(data) as FirestoreVehicle;
};

export const updateVehicle = async (
    vehicleId: string,
    updates: Partial<Omit<FirestoreVehicle, "id" | "createdAt">>
): Promise<void> => {
    const dbUpdates = toSnakeCase({
        ...updates,
        updated_at: new Date().toISOString(),
    });

    const { error } = await getClient()
        .from("vehicles")
        .update(dbUpdates)
        .eq("id", vehicleId);

    if (error) {
        console.error("Error updating vehicle:", error);
        throw error;
    }
};

export const deleteVehicle = async (vehicleId: string): Promise<void> => {
    const { error } = await getClient().from("vehicles").delete().eq("id", vehicleId);

    if (error) {
        console.error("Error deleting vehicle:", error);
        throw error;
    }
};

// ==================== ROUTE ASSIGNMENTS ====================

export const getAllRouteAssignments = async (
    filters?: {
        date?: string;
        vehicleId?: string;
        driverId?: string;
        status?: RouteAssignment["status"];
    }
): Promise<RouteAssignment[]> => {
    let query = getClient().from("route_assignments").select("*");

    if (filters?.date) query = query.eq("date", filters.date);
    if (filters?.vehicleId) query = query.eq("vehicle_id", filters.vehicleId);
    if (filters?.driverId) query = query.eq("driver_id", filters.driverId);
    if (filters?.status) query = query.eq("status", filters.status);

    query = query.order("pickup_time", { ascending: true });

    const { data, error } = await query;

    if (error) {
        console.error("Error getting route assignments:", error);
        throw error;
    }

    return data.map(toCamelCase) as RouteAssignment[];
};

export const getRouteAssignmentById = async (id: string): Promise<RouteAssignment | null> => {
    const { data, error } = await getClient()
        .from("route_assignments")
        .select("*")
        .eq("id", id)
        .single();

    if (error) {
        if (error.code === "PGRST116") return null;
        console.error("Error getting route assignment:", error);
        throw error;
    }

    return toCamelCase(data) as RouteAssignment;
};

export const createRouteAssignment = async (
    data: Omit<RouteAssignment, "id" | "createdAt" | "updatedAt">,
    id?: string
): Promise<RouteAssignment> => {
    const now = new Date().toISOString();
    const dbData = toSnakeCase({
        ...data,
        id,
        created_at: now,
        updated_at: now,
    });

    if (!id) delete dbData.id;

    const { data: result, error } = await getClient()
        .from("route_assignments")
        .insert(dbData)
        .select()
        .single();

    if (error) {
        console.error("Error creating route assignment:", error);
        throw error;
    }

    return toCamelCase(result) as RouteAssignment;
};

export const updateRouteAssignment = async (
    id: string,
    data: Partial<Omit<RouteAssignment, "id" | "createdAt">>
): Promise<boolean> => {
    const dbUpdates = toSnakeCase({
        ...data,
        updated_at: new Date().toISOString(),
    });

    const { error } = await getClient()
        .from("route_assignments")
        .update(dbUpdates)
        .eq("id", id);

    if (error) {
        console.error("Error updating route assignment:", error);
        throw error;
    }
    return true;
};

export const deleteRouteAssignment = async (id: string): Promise<boolean> => {
    const { error } = await getClient().from("route_assignments").delete().eq("id", id);

    if (error) {
        console.error("Error deleting route assignment:", error);
        throw error;
    }
    return true;
};

// ==================== ROUTES ====================

export const getAllRoutes = async (
    filters?: {
        date?: string;
        type?: Route["type"];
        timeslot?: string;
    }
): Promise<Route[]> => {
    let query = getClient().from("routes").select("*");

    if (filters?.date) query = query.eq("date", filters.date);
    if (filters?.type) query = query.eq("type", filters.type);
    if (filters?.timeslot) query = query.eq("timeslot", filters.timeslot);

    query = query.order("date", { ascending: true }).order("timeslot", { ascending: true });

    const { data, error } = await query;

    if (error) {
        console.error("Error getting routes:", error);
        throw error;
    }

    return data.map(toCamelCase) as Route[];
};

export const getRouteById = async (id: string): Promise<Route | null> => {
    const { data, error } = await getClient()
        .from("routes")
        .select("*")
        .eq("id", id)
        .single();

    if (error) {
        if (error.code === "PGRST116") return null;
        console.error("Error getting route:", error);
        throw error;
    }

    return toCamelCase(data) as Route;
};

export const createRoute = async (
    data: Omit<Route, "id" | "createdAt">,
    id?: string
): Promise<Route> => {
    const now = new Date().toISOString();
    const dbData = toSnakeCase({
        ...data,
        id,
        created_at: now,
    });

    if (!id) delete dbData.id;

    const { data: result, error } = await getClient()
        .from("routes")
        .insert(dbData)
        .select()
        .single();

    if (error) {
        console.error("Error creating route:", error);
        throw error;
    }

    return toCamelCase(result) as Route;
};

export const updateRoute = async (
    id: string,
    data: Partial<Omit<Route, "id" | "createdAt">>
): Promise<boolean> => {
    const dbUpdates = toSnakeCase(data);

    const { error } = await getClient()
        .from("routes")
        .update(dbUpdates)
        .eq("id", id);

    if (error) {
        console.error("Error updating route:", error);
        throw error;
    }
    return true;
};

export const deleteRoute = async (id: string): Promise<boolean> => {
    const { error } = await getClient().from("routes").delete().eq("id", id);

    if (error) {
        console.error("Error deleting route:", error);
        throw error;
    }
    return true;
};

// ==================== COMPATIBILITY HELPERS ====================

export const getStudentSchedule = getScheduleById;

export const createNewUserSchedule = async (
    userId: string,
    scheduleId?: string
): Promise<FirestoreWeeklySchedule> => {
    return createSchedule(
        {
            userId,
            entries: [],
            lastUpdated: new Date().toISOString(),
        },
        scheduleId
    );
};

export const updateStudentScheduleEntries = async (
    scheduleId: string,
    entries: any[]
): Promise<boolean> => {
    try {
        await updateScheduleEntries(scheduleId, entries);
        return true;
    } catch (error) {
        console.error("Error updating student schedule entries:", error);
        return false;
    }
};

export const updateRideRequestStatus = async (
    requestId: string,
    status: string
): Promise<boolean> => {
    try {
        await updateRideRequest(requestId, { status: status as any });
        return true;
    } catch (error) {
        console.error("Error updating ride request status:", error);
        return false;
    }
};

export const addRideRequest = createRideRequest;
export const getRideRequests = getAllRideRequests;
export const getUsers = getAllUsers;

export const getUserByEmailOrStudentNumber = async (
    identifier: string,
    passwordInput: string
): Promise<FirestoreUser | null> => {
    // In Supabase, we use Auth, so this is only for checking user existence
    let user = await getUserByEmail(identifier.toLowerCase());
    if (!user) {
        user = await getUserByStudentNumber(identifier);
    }
    return user;
};
