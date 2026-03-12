export type UserRole = "student" | "admin" | "driver";

export interface User {
  id: string;
  name: string;
  email: string;
  password?: string; // Added password field
  passwordHint?: string; // Custom hint created during registration
  role: UserRole;
  studentNumber?: string; // Added student number
  homeAddress?: string;
  homeCoordinates?: { lat: number; lng: number };
  accessibilityNeeds?: string[]; // e.g., ["visual_impairment", "hearing_impairment"]
  disabilityType?: "Sw" | "So"; // Sw = wheelchair, So = other disability
  locationCode?: string; // Test data reference: Sw1, So5, etc.
  weeklyScheduleId?: string; // Reference to a schedule document/object
}

export interface Vehicle {
  id: string;
  name: string; // e.g., "Servis A", "Mavi Minibüs"
  type: "minibus" | "bus" | "van";
  plateNumber?: string;
  wheelchairCapacity: number;
  seatingCapacity: number;
  status: "active" | "inactive" | "maintenance";
}

export interface ScheduleEntry {
  id: string;
  dayOfWeek: "monday" | "tuesday" | "wednesday" | "thursday" | "friday" | "saturday" | "sunday";
  courseName?: string; // Optional, could be general "Okulda Olma"
  startTime: string; // HH:mm format
  endTime: string; // HH:mm format
  location?: string; // e.g., "Mühendislik Fakültesi A Blok"
}

export interface WeeklySchedule {
  id: string;
  userId: string;
  entries: ScheduleEntry[];
  lastUpdated: string; // ISO date string
}

export type RideStatus = "pending_student_confirmation" | "confirmed" | "cancelled_by_student" | "cancelled_by_admin" | "in_progress" | "completed" | "pending_admin_approval";

export interface RideRequest {
  id: string;
  userId: string;
  type: "scheduled" | "adhoc"; // Scheduled based on weekly plan, or one-off
  requestedPickupTime: string; // ISO datetime string
  requestedDropoffTime: string; // ISO datetime string (back to home)
  actualPickupTime?: string; // ISO datetime string
  actualDropoffTime?: string; // ISO datetime string
  pickupLocation: { address: string; coordinates?: { lat: number; lng: number } };
  dropoffLocation: { address: string; coordinates?: { lat: number; lng: number } }; // Typically university for arrival, home for departure
  status: RideStatus;
  vehicleId?: string;
  createdAt: string; // ISO datetime string
  notes?: string; // Special instructions from student or admin
}

export interface AdminSettings {
  notificationTime: string; // e.g., "20:00" for previous day, or "2 hours before"
  arrivalNotificationTemplate: string;
  departureNotificationTemplate: string;
  departureReminderTime: string; // e.g., "2 hours before departure"
}
