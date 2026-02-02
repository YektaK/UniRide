/**
 * Admin Authentication Helper
 * Validates that the current user has admin role
 */

import { headers } from "next/headers";
import { getSupabaseAdmin } from "./supabase-admin";
import { createClient } from "@supabase/supabase-js";

// Get current user from the Authorization header
export async function getCurrentUserFromRequest(): Promise<{
    id: string;
    email: string;
    role: string;
} | null> {
    const headersList = await headers();
    const authHeader = headersList.get("authorization");

    if (!authHeader || !authHeader.startsWith("Bearer ")) {
        return null;
    }

    const token = authHeader.split(" ")[1];

    // Verify the token with Supabase
    const supabase = createClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );

    const { data: { user }, error } = await supabase.auth.getUser(token);

    if (error || !user) {
        return null;
    }

    // Get user role from database using admin client (bypasses RLS)
    const adminClient = getSupabaseAdmin();
    const { data: userData, error: dbError } = await adminClient
        .from("users")
        .select("id, email, role")
        .eq("id", user.id)
        .single();

    if (dbError || !userData) {
        return null;
    }

    return userData;
}

// Check if current user is admin
export async function requireAdmin(): Promise<{
    id: string;
    email: string;
    role: string;
}> {
    const user = await getCurrentUserFromRequest();

    if (!user) {
        throw new Error("Unauthorized: Not logged in");
    }

    if (user.role !== "admin") {
        throw new Error("Forbidden: Admin access required");
    }

    return user;
}

// Helper to create error response
export function createErrorResponse(message: string, status: number) {
    return Response.json({ error: message }, { status });
}

// Helper to create success response
export function createSuccessResponse(data: any, status: number = 200) {
    return Response.json(data, { status });
}
