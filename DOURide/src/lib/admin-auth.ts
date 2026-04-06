/**
 * Admin Authentication Helper
 * Validates that the current user has admin role
 */

import { headers } from "next/headers";
import { getSupabaseAdmin } from "./supabase-admin";
import { createClient } from "@supabase/supabase-js";

// ==================== AppError ====================

/**
 * Custom error class with HTTP status code.
 * Use this instead of plain Error in API routes for consistent error handling.
 */
export class AppError extends Error {
    public readonly statusCode: number;

    constructor(message: string, statusCode: number = 500) {
        super(message);
        this.name = "AppError";
        this.statusCode = statusCode;
    }

    /** 400 Bad Request */
    static badRequest(message: string) {
        return new AppError(message, 400);
    }

    /** 401 Unauthorized */
    static unauthorized(message: string = "Unauthorized: Not logged in") {
        return new AppError(message, 401);
    }

    /** 403 Forbidden */
    static forbidden(message: string = "Forbidden: Admin access required") {
        return new AppError(message, 403);
    }

    /** 404 Not Found */
    static notFound(message: string = "Resource not found") {
        return new AppError(message, 404);
    }
}

// ==================== Auth Helpers ====================

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

// Check if current user is admin — throws AppError instead of plain Error
export async function requireAdmin(): Promise<{
    id: string;
    email: string;
    role: string;
}> {
    const user = await getCurrentUserFromRequest();

    if (!user) {
        throw AppError.unauthorized();
    }

    if (user.role !== "admin") {
        throw AppError.forbidden();
    }

    return user;
}

// ==================== Response Helpers ====================

// Helper to create error response
export function createErrorResponse(message: string, status: number) {
    return Response.json({ error: message }, { status });
}

// Helper to create success response
export function createSuccessResponse(data: any, status: number = 200) {
    return Response.json(data, { status });
}

import { z } from "zod";

/**
 * Centralized error handler for API routes.
 * Checks for AppError instances instead of fragile string matching.
 */
export function handleApiError(error: unknown) {
    if (error instanceof z.ZodError) {
        // Return first validation error message
        const message = error.errors[0]?.message || "Validasyon hatası";
        return createErrorResponse(message, 400);
    }

    if (error instanceof AppError) {
        return createErrorResponse(error.message, error.statusCode);
    }
    // Fallback for unexpected errors
    const message = error instanceof Error ? error.message : "Internal server error";
    console.error("Unhandled API error:", error);
    return createErrorResponse(message, 500);
}
