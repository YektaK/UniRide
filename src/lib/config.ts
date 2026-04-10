/**
 * Application Configuration
 * Centralized configuration for environment variables and constants
 */

// API URLs
export const OPTIMIZER_API_URL = 
  process.env.OPTIMIZER_API_URL || 
  process.env.NEXT_PUBLIC_OPTIMIZER_API_URL || 
  "http://127.0.0.1:8000";

// Supabase Configuration
export const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
export const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";
export const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || "";

// Application Settings
export const APP_NAME = "UniRide";
export const DEFAULT_TIME_WINDOW_MINUTES = 30;
export const DEFAULT_MAX_TRAVEL_TIME = 120;
export const DEFAULT_SW_CAPACITY = 4;
export const DEFAULT_SO_CAPACITY = 5;

// Pagination defaults
export const DEFAULT_PAGE_SIZE = 50;
export const MAX_PAGE_SIZE = 100;

// Rate limiting (requests per minute)
// TODO(CR-6): This constant is exported but not yet connected to any middleware.
// To enable global rate limiting, import this in src/middleware.ts and wire it
// to a Redis-backed limiter (the in-process Map in auth/hint/route.ts is
// insufficient for multi-process deployments).
export const RATE_LIMIT_REQUESTS_PER_MINUTE = 60;

// Logging
export const LOG_LEVEL = process.env.NODE_ENV === "production" ? "error" : "debug";
