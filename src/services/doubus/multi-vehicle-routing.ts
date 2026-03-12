/**
 * Multi-Vehicle Routing Service
 * Optimizes routes for multiple vehicles based on time slots and capacity constraints
 */

import type { RideRequest } from "@/types";
import type { Vehicle } from "@/types";
import { getOptimalRoute, calculateDistance, type LocationCode } from "./route";
import { addressToLocationCode } from "./location-mapper";
import type { Route as DouBusRoute } from "./route";
import type { Route as DbRoute } from "@/types/db";

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
 * NEW: Uses the Python Microservice Optimization API (Strategy Pattern)
 */
export const optimizeTimeSlotRoutes = async (
  timeSlot: TimeSlot,
  vehicles: Vehicle[],
  startLocation: LocationCode = "D.Kampus"
): Promise<MultiVehicleRoutingResult> => {
  const activeVehicles = vehicles.filter((v) => v.status === "active");

  const sw_capacity = activeVehicles.length > 0 ? activeVehicles[0].wheelchairCapacity : 4;
  const so_capacity = activeVehicles.length > 0 ? activeVehicles[0].seatingCapacity : 5;

  const requestLocations = new Map<RideRequest, LocationCode>();
  const unassignedRequests: RideRequest[] = [];
  const studentsPayload: { id: string; type: string }[] = [];
  const locToRequests = new Map<string, RideRequest[]>();

  for (const request of timeSlot.requests) {
    const address =
      timeSlot.type === "pickup"
        ? request.pickupLocation.address
        : request.dropoffLocation.address;

    const locationCode = addressToLocationCode(address);
    if (locationCode) {
      requestLocations.set(request, locationCode);

      const type = locationCode.startsWith("Sw") ? "Sw" : "So";
      studentsPayload.push({
        id: locationCode,
        type: type,
      });

      if (!locToRequests.has(locationCode)) {
        locToRequests.set(locationCode, []);
      }
      locToRequests.get(locationCode)!.push(request);
    } else {
      unassignedRequests.push(request);
    }
  }

  if (studentsPayload.length === 0) {
    return {
      routes: [],
      unassignedRequests: unassignedRequests,
      totalVehiclesUsed: 0,
      totalDuration: 0,
      totalDistance: 0,
    };
  }

  const payload = {
    algorithm: "ortools_cvrp",
    students: studentsPayload,
    depot: { id: startLocation, type: "D" },
    max_travel_time: 120,
    sw_capacity: sw_capacity,
    so_capacity: so_capacity,
  };

  try {
    const response = await fetch("http://127.0.0.1:8000/api/v1/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Python API Status: ${response.status}`);
    }

    const data = await response.json();

    if (!data.success || !data.routes) {
      throw new Error(data.error_message || "Unknown error from Python engine");
    }

    const vehicleRoutes: VehicleRoute[] = [];
    let totalDuration = 0;
    let totalDistance = 0;

    data.routes.forEach((pyRoute: any, idx: number) => {
      const assignedVehicleId =
        idx < activeVehicles.length ? activeVehicles[idx].id : `Ekstra-Araç-${idx + 1}`;

      const waypoints: LocationCode[] = [];
      const studentIds: string[] = [];
      const matchedRequests: RideRequest[] = [];

      pyRoute.route_details.forEach((step: any) => {
        if (step.location2 !== startLocation && step.location2 !== "D.Kampus") {
          const locCode = step.location2 as LocationCode;
          waypoints.push(locCode);

          if (locToRequests.has(locCode)) {
            const reqs = locToRequests.get(locCode)!;
            if (reqs.length > 0) {
              const req = reqs.shift()!;
              matchedRequests.push(req);
              studentIds.push(req.userId);
            }
          }
        }
      });

      const routeDetails: any[] = pyRoute.route_details.map((step: any) => ({
        location1: step.location1 || "unknown",
        location2: step.location2,
        duration: step.duration || 0,
      }));

      const douBusRoute: DouBusRoute = {
        start: startLocation,
        end: startLocation,
        routeDetails,
        distanceKm: pyRoute.total_distance_km,
        durationMinutes: pyRoute.total_duration_minutes,
      };

      const estimatedStartTime = timeSlot.startTime;
      const estimatedEndTime = new Date(
        new Date(estimatedStartTime).getTime() + douBusRoute.durationMinutes * 60 * 1000
      ).toISOString();

      vehicleRoutes.push({
        vehicleId: assignedVehicleId,
        route: douBusRoute,
        studentIds: studentIds,
        estimatedStartTime,
        estimatedEndTime,
      });

      totalDuration += douBusRoute.durationMinutes;
      totalDistance += douBusRoute.distanceKm;
    });

    locToRequests.forEach((reqs) => {
      unassignedRequests.push(...reqs);
    });

    return {
      routes: vehicleRoutes,
      unassignedRequests,
      totalVehiclesUsed: vehicleRoutes.length,
      totalDuration,
      totalDistance,
    };
  } catch (error) {
    console.error("Python VRP API Hatası:", error);
    return {
      routes: [],
      unassignedRequests: [...timeSlot.requests],
      totalVehiclesUsed: 0,
      totalDuration: 0,
      totalDistance: 0,
    };
  }
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

