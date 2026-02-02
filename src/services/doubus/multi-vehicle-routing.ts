/**
 * Multi-Vehicle Routing Service
 * Optimizes routes for multiple vehicles based on time slots and capacity constraints
 */

import type { RideRequest } from "@/types";
import type { Vehicle } from "@/types";
import { getOptimalRoute, calculateDistance, type LocationCode } from "./route";
import { addressToLocationCode } from "./location-mapper";
import type { Route as DouBusRoute } from "./route";
import type { Route as FirestoreRoute } from "@/types/firestore";

export interface TimeSlot {
  startTime: string; // ISO datetime
  endTime: string; // ISO datetime
  requests: RideRequest[];
  type: "pickup" | "dropoff";
}

export interface VehicleRoute {
  vehicleId: string;
  route: DouBusRoute;
  studentIds: string[];
  estimatedStartTime: string; // ISO datetime
  estimatedEndTime: string; // ISO datetime
}

export interface MultiVehicleRoutingResult {
  routes: VehicleRoute[];
  unassignedRequests: RideRequest[];
  totalVehiclesUsed: number;
  totalDuration: number;
  totalDistance: number;
}

/**
 * Group ride requests by time slots
 */
export const groupRequestsByTimeSlot = (
  requests: RideRequest[],
  timeWindowMinutes: number = 30
): TimeSlot[] => {
  // Separate pickup and dropoff requests
  const pickupRequests = requests.filter(
    (req) => req.type === "scheduled" && req.status === "confirmed"
  );
  const dropoffRequests = requests.filter(
    (req) => req.type === "scheduled" && req.status === "confirmed"
  );

  const timeSlots: TimeSlot[] = [];

  // Group pickup requests
  const sortedPickups = [...pickupRequests].sort(
    (a, b) =>
      new Date(a.requestedPickupTime).getTime() -
      new Date(b.requestedPickupTime).getTime()
  );

  for (const request of sortedPickups) {
    const requestTime = new Date(request.requestedPickupTime);
    let assigned = false;

    for (const slot of timeSlots) {
      if (slot.type === "pickup") {
        const slotStart = new Date(slot.startTime);
        const slotEnd = new Date(slot.endTime);
        const timeDiff = Math.abs(requestTime.getTime() - slotStart.getTime()) / (1000 * 60);

        if (timeDiff <= timeWindowMinutes) {
          slot.requests.push(request);
          if (requestTime < slotStart) slot.startTime = request.requestedPickupTime;
          if (requestTime > slotEnd) slot.endTime = request.requestedPickupTime;
          assigned = true;
          break;
        }
      }
    }

    if (!assigned) {
      timeSlots.push({
        startTime: request.requestedPickupTime,
        endTime: request.requestedPickupTime,
        requests: [request],
        type: "pickup",
      });
    }
  }

  // Group dropoff requests
  const sortedDropoffs = [...dropoffRequests].sort(
    (a, b) =>
      new Date(a.requestedDropoffTime).getTime() -
      new Date(b.requestedDropoffTime).getTime()
  );

  for (const request of sortedDropoffs) {
    const requestTime = new Date(request.requestedDropoffTime);
    let assigned = false;

    for (const slot of timeSlots) {
      if (slot.type === "dropoff") {
        const slotStart = new Date(slot.startTime);
        const slotEnd = new Date(slot.endTime);
        const timeDiff = Math.abs(requestTime.getTime() - slotStart.getTime()) / (1000 * 60);

        if (timeDiff <= timeWindowMinutes) {
          slot.requests.push(request);
          if (requestTime < slotStart) slot.startTime = request.requestedDropoffTime;
          if (requestTime > slotEnd) slot.endTime = request.requestedDropoffTime;
          assigned = true;
          break;
        }
      }
    }

    if (!assigned) {
      timeSlots.push({
        startTime: request.requestedDropoffTime,
        endTime: request.requestedDropoffTime,
        requests: [request],
        type: "dropoff",
      });
    }
  }

  return timeSlots;
};

/**
 * Optimize routes for a time slot with multiple vehicles
 */
export const optimizeTimeSlotRoutes = async (
  timeSlot: TimeSlot,
  vehicles: Vehicle[],
  startLocation: LocationCode = "D.Kampus"
): Promise<MultiVehicleRoutingResult> => {
  const activeVehicles = vehicles.filter((v) => v.status === "active");
  const vehicleRoutes: VehicleRoute[] = [];
  const unassignedRequests: RideRequest[] = [];

  // Map requests to location codes
  const requestLocations = new Map<RideRequest, LocationCode>();
  for (const request of timeSlot.requests) {
    const address =
      timeSlot.type === "pickup"
        ? request.pickupLocation.address
        : request.dropoffLocation.address;
    const locationCode = addressToLocationCode(address);
    if (locationCode) {
      requestLocations.set(request, locationCode);
    } else {
      unassignedRequests.push(request);
    }
  }

  // Group requests by location
  const locationGroups = new Map<LocationCode, RideRequest[]>();
  for (const [request, location] of requestLocations) {
    if (!locationGroups.has(location)) {
      locationGroups.set(location, []);
    }
    locationGroups.get(location)!.push(request);
  }

  // Simple greedy assignment: assign vehicles to routes based on capacity
  let remainingRequests = [...timeSlot.requests.filter((r) => !unassignedRequests.includes(r))];
  let vehicleIndex = 0;

  while (remainingRequests.length > 0 && vehicleIndex < activeVehicles.length) {
    const vehicle = activeVehicles[vehicleIndex];
    const vehicleCapacity = vehicle.seatingCapacity + vehicle.wheelchairCapacity;

    // Get requests that fit in this vehicle
    const vehicleRequests: RideRequest[] = [];
    const vehicleLocations: LocationCode[] = [];

    for (const request of remainingRequests) {
      if (vehicleRequests.length >= vehicleCapacity) break;

      const location = requestLocations.get(request);
      if (!location) continue;

      // Check accessibility needs (simplified - in production, load user data beforehand)
      // For now, we'll check this later when we have user data loaded
      const needsWheelchair = false; // Will be determined from user data

      if (needsWheelchair && vehicleRequests.filter((r) => {
        const u = requestLocations.get(r);
        return u === location;
      }).length >= vehicle.wheelchairCapacity) {
        continue; // No wheelchair capacity left
      }

      vehicleRequests.push(request);
      if (!vehicleLocations.includes(location)) {
        vehicleLocations.push(location);
      }
    }

    if (vehicleLocations.length > 0) {
      // Calculate optimal route for this vehicle
      const waypoints = vehicleLocations.filter((loc) => loc !== startLocation);
      const endLocation = waypoints.length > 0 ? waypoints[waypoints.length - 1] : startLocation;

      try {
        const route = await getOptimalRoute(startLocation, endLocation, waypoints);

        const estimatedStartTime = timeSlot.startTime;
        const estimatedEndTime = new Date(
          new Date(estimatedStartTime).getTime() + route.durationMinutes * 60 * 1000
        ).toISOString();

        vehicleRoutes.push({
          vehicleId: vehicle.id,
          route,
          studentIds: vehicleRequests.map((r) => r.userId),
          estimatedStartTime,
          estimatedEndTime,
        });

        // Remove assigned requests
        remainingRequests = remainingRequests.filter(
          (r) => !vehicleRequests.includes(r)
        );
      } catch (error) {
        console.error(`Error optimizing route for vehicle ${vehicle.id}:`, error);
        unassignedRequests.push(...vehicleRequests);
        remainingRequests = remainingRequests.filter(
          (r) => !vehicleRequests.includes(r)
        );
      }
    }

    vehicleIndex++;
  }

  // Add remaining unassigned requests
  unassignedRequests.push(...remainingRequests);

  const totalDuration = vehicleRoutes.reduce(
    (sum, vr) => sum + vr.route.durationMinutes,
    0
  );
  const totalDistance = vehicleRoutes.reduce(
    (sum, vr) => sum + vr.route.distanceKm,
    0
  );

  return {
    routes: vehicleRoutes,
    unassignedRequests,
    totalVehiclesUsed: vehicleRoutes.length,
    totalDuration,
    totalDistance,
  };
};

/**
 * Optimize all time slots for a given date
 */
export const optimizeAllTimeSlots = async (
  requests: RideRequest[],
  vehicles: Vehicle[],
  targetDate: Date
): Promise<Map<string, MultiVehicleRoutingResult>> => {
  const timeSlots = groupRequestsByTimeSlot(requests);
  const results = new Map<string, MultiVehicleRoutingResult>();

  for (const slot of timeSlots) {
    const slotKey = `${slot.type}_${slot.startTime}`;
    const result = await optimizeTimeSlotRoutes(slot, vehicles);
    results.set(slotKey, result);
  }

  return results;
};

