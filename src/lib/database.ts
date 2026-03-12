/**
 * Database Adapter
 * This file provides a unified interface for Database
 * Currently uses Supabase by default
 * To use Supabase, set NEXT_PUBLIC_USE_SUPABASE=true in .env.local
 * 
 * Note: Conditional exports are not supported in ES modules
 * We'll implement Supabase integration in a separate phase
 */

// Export Supabase database functions
export {
  // User functions
  getUserById,
  getUserByEmail,
  getUserByStudentNumber,
  getAllUsers as getUsers,
  getAllUsers,
  createUser,
  updateUser,
  deleteUser,
  getUserByEmailOrStudentNumber,

  // Schedule functions
  getScheduleById,
  getScheduleByUserId,
  getScheduleById as getStudentSchedule, // Alias for compatibility
  createSchedule,
  updateSchedule,
  updateScheduleEntries,


  // Ride Request functions
  getRideRequestById,
  getAllRideRequests,
  createRideRequest,
  updateRideRequest,
  deleteRideRequest,

  // Vehicle functions
  getAllVehicles as getVehicles,
  getAllVehicles,
  getVehicleById,
  createVehicle,
  updateVehicle,
  deleteVehicle,

  // Route Assignment functions
  getAllRouteAssignments,
  getRouteAssignmentById,
  createRouteAssignment,
  updateRouteAssignment,
  deleteRouteAssignment,

  // Route functions
  getAllRoutes,
  getRouteById,
  createRoute,
  updateRoute,
  deleteRoute,

  // Compatibility functions (these wrap or alias the functions above)
  createNewUserSchedule,
  updateStudentScheduleEntries,
  updateRideRequestStatus,
  addRideRequest,
  getRideRequests,
} from "./supabase-db";

// Re-export types for convenience
export type {
  DbUser,
  DbWeeklySchedule,
  DbRideRequest,
  DbVehicle,
  RouteAssignment,
  Route,
} from "@/types/db";
