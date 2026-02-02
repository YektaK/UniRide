/**
 * Supabase Client
 * Initialize Supabase client for database and auth operations
 */

import { createClient } from "@supabase/supabase-js";
// Database type will be generated from Supabase schema
// For now, we'll use any to avoid type errors
type Database = any;

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

