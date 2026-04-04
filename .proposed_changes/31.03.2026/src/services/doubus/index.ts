/**
 * DouBus Service - Main Export
 * Centralized exports for all DouBus route optimization services
 */

// Route optimization
export { getOptimalRoute, calculateDistance, ALL_LOCATIONS } from "./route";
export type { Route, RouteDetail, LocationCode } from "./route";

// Location mapping
export {
  addressToLocationCode,
  coordinatesToLocationCode,
  isValidLocationCode,
  getAllLocationCodes,
} from "./location-mapper";

// Multi-vehicle routing
export {
  groupRequestsByTimeSlot,
  optimizeTimeSlotRoutes,
  optimizeAllTimeSlots,
} from "./multi-vehicle-routing";
export type {
  TimeSlot,
  VehicleRoute,
  MultiVehicleRoutingResult,
} from "./multi-vehicle-routing";

// Route optimizer
export { optimizeRoutesForDate, calculateETA, convertToDbRoute } from "./route-optimizer";

// Vehicle assignment
export {
  createVehicleAssignment,
  createBatchAssignments,
} from "./vehicle-assignment";
export type { AssignmentInput, AssignmentResult } from "./vehicle-assignment";

