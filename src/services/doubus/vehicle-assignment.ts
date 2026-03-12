/**
 * Vehicle Assignment Service
 * Assigns vehicles, drivers, and students to optimized routes
 */

import type { Vehicle } from "@/types";
import type { DbUser } from "@/types/db";
import type { RouteAssignment } from "@/types/db";
import { getAllVehicles, getAllUsers } from "@/lib/database";

export interface AssignmentInput {
  vehicleId: string;
  studentIds: string[];
  routeId: string;
  pickupTime: string; // ISO datetime
  estimatedDropoffTime: string; // ISO datetime
  date: string; // YYYY-MM-DD
}

export interface AssignmentResult {
  assignment: Omit<RouteAssignment, "id" | "createdAt" | "updatedAt">;
  vehicle: Vehicle;
  driver?: DbUser;
  students: DbUser[];
  canAssign: boolean;
  reason?: string;
}

/**
 * Check if vehicle has capacity for students
 */
const checkVehicleCapacity = (
  vehicle: Vehicle,
  students: DbUser[]
): { canFit: boolean; reason?: string } => {
  const wheelchairUsers = students.filter((s) =>
    s.accessibilityNeeds?.includes("wheelchair")
  );
  const regularUsers = students.filter(
    (s) => !s.accessibilityNeeds?.includes("wheelchair")
  );

  if (wheelchairUsers.length > vehicle.wheelchairCapacity) {
    return {
      canFit: false,
      reason: `Araç ${vehicle.wheelchairCapacity} tekerlekli sandalye kapasitesine sahip, ${wheelchairUsers.length} gerekiyor.`,
    };
  }

  const totalCapacity = vehicle.seatingCapacity + vehicle.wheelchairCapacity;
  if (students.length > totalCapacity) {
    return {
      canFit: false,
      reason: `Araç ${totalCapacity} kişi kapasitesine sahip, ${students.length} öğrenci atanmaya çalışılıyor.`,
    };
  }

  return { canFit: true };
};

/**
 * Assign driver to vehicle (simple assignment - can be enhanced)
 */
const assignDriver = async (
  vehicleId: string,
  date: string
): Promise<DbUser | undefined> => {
  const allUsers = await getAllUsers();
  const drivers = allUsers.filter((u) => u.role === "driver");

  if (drivers.length === 0) {
    return undefined; // No drivers available
  }

  // Simple round-robin assignment
  // In production, consider driver availability, preferences, etc.
  const driverIndex =
    (parseInt(date.replace(/-/g, "")) + parseInt(vehicleId.slice(-1))) %
    drivers.length;
  return drivers[driverIndex];
};

/**
 * Create vehicle assignment
 */
export const createVehicleAssignment = async (
  input: AssignmentInput
): Promise<AssignmentResult> => {
  // Get vehicle
  const vehicles = await getAllVehicles();
  const vehicle = vehicles.find((v) => v.id === input.vehicleId);

  if (!vehicle) {
    throw new Error(`Vehicle ${input.vehicleId} not found`);
  }

  if (vehicle.status !== "active") {
    return {
      assignment: {
        date: input.date,
        vehicleId: input.vehicleId,
        routeId: input.routeId,
        studentIds: input.studentIds,
        pickupTime: input.pickupTime,
        estimatedDropoffTime: input.estimatedDropoffTime,
        status: "cancelled",
      },
      vehicle,
      students: [],
      canAssign: false,
      reason: `Araç ${vehicle.status} durumunda, aktif değil.`,
    };
  }

  // Get students
  const allUsers = await getAllUsers();
  const students = allUsers.filter((u) => input.studentIds.includes(u.id));

  if (students.length !== input.studentIds.length) {
    const foundIds = students.map((s) => s.id);
    const missingIds = input.studentIds.filter((id) => !foundIds.includes(id));
    return {
      assignment: {
        date: input.date,
        vehicleId: input.vehicleId,
        routeId: input.routeId,
        studentIds: input.studentIds,
        pickupTime: input.pickupTime,
        estimatedDropoffTime: input.estimatedDropoffTime,
        status: "cancelled",
      },
      vehicle,
      students,
      canAssign: false,
      reason: `Bazı öğrenciler bulunamadı: ${missingIds.join(", ")}`,
    };
  }

  // Check capacity
  const capacityCheck = checkVehicleCapacity(vehicle, students);
  if (!capacityCheck.canFit) {
    return {
      assignment: {
        date: input.date,
        vehicleId: input.vehicleId,
        routeId: input.routeId,
        studentIds: input.studentIds,
        pickupTime: input.pickupTime,
        estimatedDropoffTime: input.estimatedDropoffTime,
        status: "cancelled",
      },
      vehicle,
      students,
      canAssign: false,
      reason: capacityCheck.reason,
    };
  }

  // Assign driver
  const driver = await assignDriver(input.vehicleId, input.date);

  const assignment: Omit<RouteAssignment, "id" | "createdAt" | "updatedAt"> = {
    date: input.date,
    vehicleId: input.vehicleId,
    driverId: driver?.id,
    routeId: input.routeId,
    studentIds: input.studentIds,
    pickupTime: input.pickupTime,
    estimatedDropoffTime: input.estimatedDropoffTime,
    status: "scheduled",
  };

  return {
    assignment,
    vehicle,
    driver,
    students,
    canAssign: true,
  };
};

/**
 * Batch create assignments for multiple routes
 */
export const createBatchAssignments = async (
  inputs: AssignmentInput[]
): Promise<{
  successful: AssignmentResult[];
  failed: AssignmentResult[];
}> => {
  const successful: AssignmentResult[] = [];
  const failed: AssignmentResult[] = [];

  for (const input of inputs) {
    try {
      const result = await createVehicleAssignment(input);
      if (result.canAssign) {
        successful.push(result);
      } else {
        failed.push(result);
      }
    } catch (error: any) {
      failed.push({
        assignment: {
          date: input.date,
          vehicleId: input.vehicleId,
          routeId: input.routeId,
          studentIds: input.studentIds,
          pickupTime: input.pickupTime,
          estimatedDropoffTime: input.estimatedDropoffTime,
          status: "cancelled",
        },
        vehicle: {} as Vehicle,
        students: [],
        canAssign: false,
        reason: error.message || "Bilinmeyen hata",
      });
    }
  }

  return { successful, failed };
};

