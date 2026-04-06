/**
 * Supabase Client
 * Initialize Supabase client for database and auth operations
 */

import { createClient } from "@supabase/supabase-js";
import type { DbUser, DbVehicle, DbRideRequest, DbWeeklySchedule, RouteAssignment, Route as DbRoute } from "@/types/db";

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export interface Database {
  public: {
    Tables: {
      users: {
        Row: DbUser;
        Insert: Partial<DbUser>;
        Update: Partial<DbUser>;
        Relationships: [];
      };
      vehicles: {
        Row: DbVehicle;
        Insert: Partial<DbVehicle>;
        Update: Partial<DbVehicle>;
        Relationships: [];
      };
      ride_requests: {
        Row: DbRideRequest;
        Insert: Partial<DbRideRequest>;
        Update: Partial<DbRideRequest>;
        Relationships: [];
      };
      weekly_schedules: {
        Row: DbWeeklySchedule;
        Insert: Partial<DbWeeklySchedule>;
        Update: Partial<DbWeeklySchedule>;
        Relationships: [];
      };
      route_assignments: {
        Row: RouteAssignment;
        Insert: Partial<RouteAssignment>;
        Update: Partial<RouteAssignment>;
        Relationships: [];
      };
      routes: {
        Row: DbRoute;
        Insert: Partial<DbRoute>;
        Update: Partial<DbRoute>;
        Relationships: [];
      };
      route_plans: {
        Row: Record<string, unknown>;
        Insert: Record<string, unknown>;
        Update: Record<string, unknown>;
        Relationships: [];
      };
      sandbox_scenarios: {
        Row: Record<string, unknown>;
        Insert: Record<string, unknown>;
        Update: Record<string, unknown>;
        Relationships: [];
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      [_ in never]: never;
    };
    Enums: {
      [_ in never]: never;
    };
  };
}


const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// Only initialize Supabase if URL and key are provided
let supabase: ReturnType<typeof createClient<Database>> | null = null;

if (supabaseUrl && supabaseAnonKey) {
  try {
    supabase = createClient<Database>(supabaseUrl, supabaseAnonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
      },
    });
  } catch (error) {
    console.warn("[Supabase] Failed to initialize client:", error);
  }
} else {
  console.warn(
    "[Supabase] Missing environment variables. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in .env.local"
  );
}

export { supabase };

// Helper to get Supabase client (with error handling)
export const getSupabaseClient = () => {
  if (!supabase) {
    throw new Error("Supabase not initialized. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in .env.local");
  }
  return supabase;
};
