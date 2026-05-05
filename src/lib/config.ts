/**
 * Application Configuration
 * Centralized configuration for environment variables and constants
 */

// API URLs
export const OPTIMIZER_API_URL = 
  process.env.OPTIMIZER_API_URL || 
  process.env.NEXT_PUBLIC_OPTIMIZER_API_URL || 
  "http://127.0.0.1:8000";

// Supabase configuration is intentionally NOT re-exported from here.
// Each consumer reads process.env directly and handles missing values:
//   - src/lib/supabase.ts        → warns + sets client to null; getSupabaseClient() throws
//   - src/lib/supabase-admin.ts  → throws immediately if URL or SERVICE_ROLE_KEY missing

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
// Current state: auth/hint/route.ts uses an in-process Map-based limiter (sufficient
// for single-process dev). For multi-process production, wire this to a Redis-backed
// limiter in src/middleware.ts. Tracked in docs/05_Code_Quality_Roadmap.md → Faz D.
export const RATE_LIMIT_REQUESTS_PER_MINUTE = 60;

// Logging
export const LOG_LEVEL = process.env.NODE_ENV === "production" ? "error" : "debug";
