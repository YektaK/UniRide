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
});

const updateUserSchema = z.object({
    id: z.string().uuid("Geçerli bir kullanıcı kimliği (UUID) gerekli"),
    name: z.string().min(2, "İsim en az 2 karakter olmalıdır").optional(),
    role: z.enum(["student", "driver", "admin"]).optional(),
    studentNumber: z.string().optional(),
    homeAddress: z.string().optional(),
    accessibilityNeeds: z.array(z.string()).optional(),
});

// GET /api/admin/users - Get all users
export async function GET(request: NextRequest) {
    try {
        await requireAdmin();

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
        await requireAdmin();

        const body = await request.json();
        const validatedData = createUserSchema.parse(body);
        const { email, password, name, role, studentNumber, homeAddress, accessibilityNeeds } = validatedData;

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

        // Create database user
        const { data: userData, error: dbError } = await (adminClient as any)
            .from("users")
            .insert({
                id: authData.user.id,
                email,
                name,
                role,
                student_number: studentNumber,
                home_address: homeAddress || "",
                accessibility_needs: accessibilityNeeds || [],
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
            })
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
        await requireAdmin();

        const body = await request.json();
        const validatedData = updateUserSchema.parse(body);
        const { id, ...updates } = validatedData;

        const adminClient = getSupabaseAdmin();

        // Convert camelCase to snake_case for database
        const dbUpdates: any = {
            updated_at: new Date().toISOString(),
        };

        if (updates.name) dbUpdates.name = updates.name;
        if (updates.role) dbUpdates.role = updates.role;
        if (updates.studentNumber !== undefined) dbUpdates.student_number = updates.studentNumber;
        if (updates.homeAddress !== undefined) dbUpdates.home_address = updates.homeAddress;
        if (updates.accessibilityNeeds !== undefined) dbUpdates.accessibility_needs = updates.accessibilityNeeds;

        const { data, error } = await (adminClient as any)
            .from("users")
            .update(dbUpdates)
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
        await requireAdmin();

        const { searchParams } = new URL(request.url);
        const id = searchParams.get("id");

        if (!id) {
            return createErrorResponse("User ID is required", 400);
        }

        const adminClient = getSupabaseAdmin();

        // Delete from database first
        const { error: dbError } = await adminClient
            .from("users")
            .delete()
            .eq("id", id);

        if (dbError) {
            return createErrorResponse(dbError.message, 500);
        }

        // Delete from auth
        const { error: authError } = await adminClient.auth.admin.deleteUser(id);

        if (authError) {
            return createErrorResponse(authError.message, 500);
        }

        return createSuccessResponse({ message: "User deleted successfully" });
    } catch (error) {
        return handleApiError(error);
    }
}
