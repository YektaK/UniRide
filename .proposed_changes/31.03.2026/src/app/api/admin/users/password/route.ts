/**
 * Admin Password Reset API Route
 * Allows admins to reset any user's password
 */

import { NextRequest } from "next/server";
import { getSupabaseAdmin } from "@/lib/supabase-admin";
import { requireAdmin, createErrorResponse, createSuccessResponse, handleApiError } from "@/lib/admin-auth";
import { z } from "zod";

const passwordUpdateSchema = z.object({
    userId: z.string().uuid("Geçerli bir kullanıcı kimliği (UUID) gerekli"),
    newPassword: z.string().min(6, "Şifre en az 6 karakter olmalıdır"),
});

// PATCH /api/admin/users/password - Reset a user's password
export async function PATCH(request: NextRequest) {
    try {
        await requireAdmin();

        const body = await request.json();
        const validatedData = passwordUpdateSchema.parse(body);
        const { userId, newPassword } = validatedData;

        const adminClient = getSupabaseAdmin();

        const { error } = await adminClient.auth.admin.updateUserById(userId, {
            password: newPassword,
        });

        if (error) {
            return createErrorResponse(error.message, 500);
        }

        return createSuccessResponse({ message: "Şifre başarıyla güncellendi." });
    } catch (error) {
        return handleApiError(error);
    }
}
