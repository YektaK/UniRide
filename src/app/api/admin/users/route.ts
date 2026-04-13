/**
 * Admin Users API Route
 * Handles CRUD operations for users (admin only)
 */

import { NextRequest } from "next/server";
import { getSupabaseAdmin } from "@/lib/supabase-admin";
import {
    requireAdmin,
    createErrorResponse,
    createSuccessResponse,
    handleApiError,
} from "@/lib/admin-auth";
import { z } from "zod";
import type { DbUserRow } from "@/types/db";

const createUserSchema = z.object({
    email: z.string().email("Geçerli bir e-posta adresi girin"),
    password: z.string().min(6, "Şifre en az 6 karakter olmalıdır"),
    name: z.string().min(2, "İsim en az 2 karakter olmalıdır"),
    role: z.enum(["student", "driver", "admin"], {
        errorMap: () => ({ message: "Geçersiz rol seçimi" })
    }),
    studentNumber: z.string().optional(),
    homeAddress: z.string().optional(),
    accessibilityNeeds: z.array(z.string()).optional(),
    disabilityType: z.enum(["Sw", "So"]).nullable().optional(),
});

const updateUserSchema = z.object({
    id: z.string().uuid("Geçerli bir kullanıcı kimliği (UUID) gerekli"),
    name: z.string().min(2, "İsim en az 2 karakter olmalıdır").optional(),
    role: z.enum(["student", "driver", "admin"]).optional(),
    studentNumber: z.string().optional(),
    homeAddress: z.string().optional(),
    accessibilityNeeds: z.array(z.string()).optional(),
    disabilityType: z.enum(["Sw", "So"]).nullable().optional(),
});

// GET /api/admin/users - Get all users
export async function GET(request: NextRequest) {
    try {
        await requireAdmin(request);

        const adminClient = getSupabaseAdmin();
        const { data, error } = await adminClient
            .from("users")
            .select("*")
            .order("created_at", { ascending: false });

        if (error) {
            return createErrorResponse(error.message, 500);
        }

        return createSuccessResponse(data);
    } catch (error) {
        return handleApiError(error);
    }
}

// POST /api/admin/users - Create new user
export async function POST(request: NextRequest) {
    try {
        await requireAdmin(request);

        const body = await request.json();
        const validatedData = createUserSchema.parse(body);
        const { email, password, name, role, studentNumber, homeAddress, accessibilityNeeds, disabilityType } = validatedData;

        const adminClient = getSupabaseAdmin();

        // Create auth user
        const { data: authData, error: authError } = await adminClient.auth.admin.createUser({
            email,
            password,
            email_confirm: true,
        });

        if (authError) {
            return createErrorResponse(authError.message, 400);
        }

        // Logic check: Admin and Driver should have null disability_type
        const finalDisabilityType = (role === "admin" || role === "driver") ? null : (disabilityType || null);

        // Create database user
        // Payload is typed as DbUserRow fields but Supabase's overload resolution
        // requires `as never` at the method boundary — same pattern as supabase-db.ts:153
        // and profile/password/route.ts:47 throughout the codebase.
        const insertPayload: Partial<DbUserRow> = {
            id: authData.user.id,
            email,
            name,
            role,
            student_number: studentNumber ?? null,
            home_address: homeAddress ?? null,
            accessibility_needs: accessibilityNeeds || [],
            disability_type: finalDisabilityType,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        };
        const { data: userData, error: dbError } = await adminClient
            .from("users")
            .insert(insertPayload as never)
            .select()
            .single();

        if (dbError) {
            // Rollback auth user creation
            await adminClient.auth.admin.deleteUser(authData.user.id);
            return createErrorResponse(dbError.message, 500);
        }

        return createSuccessResponse(userData, 201);
    } catch (error) {
        return handleApiError(error);
    }
}

// PUT /api/admin/users - Update user
export async function PUT(request: NextRequest) {
    try {
        await requireAdmin(request);

        const body = await request.json();
        const validatedData = updateUserSchema.parse(body);
        const { id, ...updates } = validatedData;

        const adminClient = getSupabaseAdmin();

        // Convert camelCase to snake_case for database
        const dbUpdates: Partial<Omit<DbUserRow, "id">> = {
            updated_at: new Date().toISOString(),
        };

        if (updates.name !== undefined) dbUpdates.name = updates.name;
        if (updates.role !== undefined) dbUpdates.role = updates.role;
        if (updates.studentNumber !== undefined) dbUpdates.student_number = updates.studentNumber;
        if (updates.homeAddress !== undefined) dbUpdates.home_address = updates.homeAddress;
        if (updates.accessibilityNeeds !== undefined) dbUpdates.accessibility_needs = updates.accessibilityNeeds;
        if (updates.disabilityType !== undefined) dbUpdates.disability_type = updates.disabilityType;

        // Logic check: If role changed to admin/driver, clear disability_type
        if (dbUpdates.role === "admin" || dbUpdates.role === "driver") {
            dbUpdates.disability_type = null;
            dbUpdates.accessibility_needs = [];
        }

        const { data, error } = await adminClient
            .from("users")
            .update(dbUpdates as never)
            .eq("id", id)
            .select()
            .single();

        if (error) {
            return createErrorResponse(error.message, 500);
        }

        return createSuccessResponse(data);
    } catch (error) {
        return handleApiError(error);
    }
}

// DELETE /api/admin/users - Delete user
export async function DELETE(request: NextRequest) {
    try {
        await requireAdmin(request);

        const { searchParams } = new URL(request.url);
        const id = searchParams.get("id");

        if (!id) {
            return createErrorResponse("User ID is required", 400);
        }

        const adminClient = getSupabaseAdmin();

        // 1. Delete from Auth first (Primary action)
        const { error: authError } = await adminClient.auth.admin.deleteUser(id);

        if (authError) {
            // If user doesn't exist in Auth anymore, we might still want to try deleting from DB
            if (!authError.message.includes("not found")) {
                return createErrorResponse(`Auth deletion failed: ${authError.message}`, 500);
            }
        }

        // 2. Delete from database (Secondary action/cleanup)
        const { error: dbError } = await adminClient
            .from("users")
            .delete()
            .eq("id", id);

        if (dbError) {
            return createErrorResponse(`Database deletion failed: ${dbError.message}`, 500);
        }

        return createSuccessResponse({ message: "User deleted successfully" });
    } catch (error) {
        return handleApiError(error);
    }
}
