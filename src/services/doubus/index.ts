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

// Route strategies
export {
  getStrategy,
  getAvailableStrategies,
  getStrategyInfo,
  getStrategyInfoByName,
  getDefaultStrategy,
  GeneticAlgorithmStrategy,
  PSOStrategy,
} from "./route-strategies";
export type {
  RouteStrategy,
  StrategyCalculationResult,
  GAConfig,
  PSOConfig,
} from "./route-strategies/types";
export type { StrategyInfo } from "./route-strategies";
