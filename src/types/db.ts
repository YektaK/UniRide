import type { User, WeeklySchedule, RideRequest, Vehicle, AdminSettings } from "./index";

/**
 * Exact row shape returned by Supabase for the `users` table.
 * Uses snake_case column names matching the PostgreSQL schema.
 * Note: `password_hint` is added via migration, not in the base schema.sql —
 * see supabase/migrations/20260305_add_missing_user_columns.sql.
 *
 * When to use this type vs DbUser:
 *   - Use `DbUserRow` for direct database operations (insert/update/select in API routes and DB helpers)
 *   - Use `DbUser` (camelCase) for application logic — after fetching data and converting via toCamelCase()
 */
export interface DbUserRow {
    id: string;
    email: string;
    name: string;
    role: "student" | "admin" | "driver";
    student_number: string | null;
    home_address: string | null;
    home_coordinates: { lat: number; lng: number } | null;
    accessibility_needs: string[] | null;
    disability_type: "Sw" | "So" | null;
    location_code: string | null;
    weekly_schedule_id: string | null;
    password_hint: string | null;
    created_at: string;
    updated_at: string;
}

/**
 * Database document types with DB metadata fields
 * These extend the base types with timestamps and other database-specific fields
 */

export interface DbUser extends Omit<User, "password"> {
  passwordHash?: string; // Hashed password (for future use if needed)
  createdAt: string; // ISO date string
  updatedAt: string; // ISO date string
}

export interface DbWeeklySchedule extends WeeklySchedule {
  createdAt: string; // ISO date string
  updatedAt: string; // ISO date string
}

export interface DbRideRequest extends RideRequest {
  updatedAt: string; // ISO date string
}

export interface DbVehicle extends Vehicle {
  createdAt: string; // ISO date string
  updatedAt: string; // ISO date string
}

export interface DbAdminSettings extends AdminSettings {
  updatedAt: string; // ISO date string
}

/**
 * Route Assignment - Links vehicles, drivers, students, and routes
 */
export interface RouteAssignment {
  id: string;
  date: string; // ISO date string (YYYY-MM-DD)
  vehicleId: string;
  driverId?: string; // User ID of driver
  routeId: string; // Reference to optimized route
  studentIds: string[]; // Array of student user IDs
  pickupTime: string; // ISO datetime string
  estimatedDropoffTime: string; // ISO datetime string
  status: "scheduled" | "in_progress" | "completed" | "cancelled";
  createdAt: string; // ISO date string
  updatedAt: string; // ISO date string
}

/**
 * Route - Optimized route from DouBus
 */
export interface Route {
  id: string;
  date: string; // ISO date string (YYYY-MM-DD)
  timeslot: string; // e.g., "Pick.G1.S09" or "Drop.G1.S10"
  type: "pickup" | "dropoff"; // Pickup from home or dropoff to home
  waypoints: string[]; // Array of location codes (e.g., ["Sw1", "Sw3", "So1"])
  optimizedPath: {
    location: string; // Location code
    order: number; // Order in route
    estimatedArrival: string; // ISO datetime string
    studentIds: string[]; // Students at this location
  }[];
  totalDuration: number; // Total duration in minutes
  totalDistance: number; // Total distance in kilometers
  vehicleCount: number; // Number of vehicles needed
  createdAt: string; // ISO date string
}

/**
 * Notification - System notifications for users
 */
export interface Notification {
  id: string;
  userId: string; // User who receives the notification
  type: "ride_confirmation" | "ride_reminder" | "route_update" | "system";
  title: string;
  message: string;
  relatedRequestId?: string; // Optional reference to ride request
  relatedRouteId?: string; // Optional reference to route
  read: boolean;
  createdAt: string; // ISO date string
}

