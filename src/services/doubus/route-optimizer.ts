/**
 * Route Optimizer Service
 * High-level service that coordinates multi-vehicle routing and vehicle assignment
 */

import type { RideRequest } from "@/types";
import type { Vehicle } from "@/types";
import type { FirestoreRoute, RouteAssignment } from "@/types/firestore";
import { optimizeAllTimeSlots, type MultiVehicleRoutingResult } from "./multi-vehicle-routing";
import { getOptimalRoute, type LocationCode } from "./route";
import { addressToLocationCode } from "./location-mapper";
import { format } from "date-fns";

/**
 * Convert DouBus route to Firestore Route format
 */
const convertToFirestoreRoute = (
  vehicleRoute: MultiVehicleRoutingResult["routes"][0],
  date: string,
  timeslot: string,
  type: "pickup" | "dropoff"
): Omit<FirestoreRoute, "id" | "createdAt"> => {
  const optimizedPath = vehicleRoute.route.routeDetails.map((detail, index) => ({
    location: detail.location2,
    order: index + 1,
    estimatedArrival: new Date(
      new Date(vehicleRoute.estimatedStartTime).getTime() +
        vehicleRoute.route.routeDetails
          .slice(0, index + 1)
          .reduce((sum, d) => sum + d.duration, 0) *
          60 *
          1000
    ).toISOString(),
    studentIds: vehicleRoute.studentIds.filter((studentId, idx) => {
      // This is simplified - in production, map students to specific locations
      return idx < vehicleRoute.studentIds.length;
    }),
  }));

  return {
    date,
    timeslot,
    type,
    waypoints: vehicleRoute.route.routeDetails.map((d) => d.location2),
    optimizedPath,
    totalDuration: vehicleRoute.route.durationMinutes,
    totalDistance: vehicleRoute.route.distanceKm,
    vehicleCount: 1, // One vehicle per route
  };
};

/**
 * Optimize routes for a specific date and create route assignments
 */
export const optimizeRoutesForDate = async (
  requests: RideRequest[],
  vehicles: Vehicle[],
  targetDate: Date
): Promise<{
  routes: Omit<FirestoreRoute, "id" | "createdAt">[];
  assignments: Omit<RouteAssignment, "id" | "createdAt" | "updatedAt">[];
  unassignedRequests: RideRequest[];
}> => {
  const dateStr = format(targetDate, "yyyy-MM-dd");
  const timeSlotResults = await optimizeAllTimeSlots(requests, vehicles, targetDate);

  const routes: Omit<FirestoreRoute, "id" | "createdAt">[] = [];
  const assignments: Omit<RouteAssignment, "id" | "createdAt" | "updatedAt">[] = [];
  const allUnassignedRequests: RideRequest[] = [];

  for (const [slotKey, result] of timeSlotResults) {
    const [type, startTime] = slotKey.split("_");
    const routeType = type as "pickup" | "dropoff";

    for (const vehicleRoute of result.routes) {
      const timeslot = `${routeType}.${format(new Date(startTime), "HH:mm")}`;
      const firestoreRoute = convertToFirestoreRoute(
        vehicleRoute,
        dateStr,
        timeslot,
        routeType
      );

      routes.push(firestoreRoute);

      // Create route assignment
      assignments.push({
        date: dateStr,
        vehicleId: vehicleRoute.vehicleId,
        routeId: `route_${dateStr}_${timeslot}_${vehicleRoute.vehicleId}`, // Will be replaced with actual route ID
        studentIds: vehicleRoute.studentIds,
        pickupTime: vehicleRoute.estimatedStartTime,
        estimatedDropoffTime: vehicleRoute.estimatedEndTime,
        status: "scheduled",
      });
    }

    allUnassignedRequests.push(...result.unassignedRequests);
  }

  return {
    routes,
    assignments,
    unassignedRequests: allUnassignedRequests,
  };
};

/**
 * Calculate ETA for a specific location based on route
 */
export const calculateETA = (
  route: FirestoreRoute,
  currentLocation: LocationCode,
  currentTime: Date
): Date | null => {
  const pathEntry = route.optimizedPath.find((p) => p.location === currentLocation);
  if (!pathEntry) return null;

  // Find the estimated arrival time for this location
  const estimatedArrival = new Date(pathEntry.estimatedArrival);
  
  // Adjust based on current time
  const timeDiff = estimatedArrival.getTime() - currentTime.getTime();
  if (timeDiff < 0) {
    // Already passed, estimate based on remaining route
    const remainingPath = route.optimizedPath.filter(
      (p) => new Date(p.estimatedArrival) > currentTime
    );
    if (remainingPath.length === 0) return null;
    
    // Estimate based on average speed from remaining path
    const lastEntry = route.optimizedPath[route.optimizedPath.length - 1];
    return new Date(lastEntry.estimatedArrival);
  }

  return estimatedArrival;
};

