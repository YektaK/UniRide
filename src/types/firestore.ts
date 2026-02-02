import type { User, WeeklySchedule, RideRequest, Vehicle, AdminSettings } from "./index";

/**
 * Firestore document types with Firestore-specific fields
 * These extend the base types with Firestore metadata
 */

export interface FirestoreUser extends Omit<User, "password"> {
  passwordHash?: string; // Hashed password (for future use if needed)
  createdAt: string; // ISO date string
  updatedAt: string; // ISO date string
}

export interface FirestoreWeeklySchedule extends WeeklySchedule {
  createdAt: string; // ISO date string
  updatedAt: string; // ISO date string
}

export interface FirestoreRideRequest extends RideRequest {
  updatedAt: string; // ISO date string
}

export interface FirestoreVehicle extends Vehicle {
  createdAt: string; // ISO date string
  updatedAt: string; // ISO date string
}

export interface FirestoreAdminSettings extends AdminSettings {
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

