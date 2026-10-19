/**
 * Self-Service Profile Password Update API
 * Allows any logged-in user to update their own password and password hint
 */

import { NextRequest } from "next/server";
import { z } from "zod";
import { getSupabaseAdmin } from "@/lib/supabase-admin";
import {
    createErrorResponse,
    createSuccessResponse,
    handleApiError,
    requireAuthenticatedUser,
} from "@/lib/admin-auth";

/**
 * Map a Supabase Auth admin error to an HTTP status and a fixed client message.
 * Provider text is never returned; it goes to the server log only.
 */
function mapPasswordProviderError(error: { status?: number; code?: string }) {
    const status = error.status;
    if (error.code === "weak_password" || error.code === "same_password" || status === 400 || status === 422) {
        return { status: 400, message: "Şifre kabul edilmedi. Lütfen farklı ve daha güçlü bir şifre deneyin." };
    }
    if (status === 401 || status === 404 || error.code === "user_not_found") {
        return { status: 401, message: "Oturum geçersiz. Lütfen tekrar giriş yapın." };
    }
    if (status === 403) {
        return { status: 403, message: "Şifre değiştirme yetkiniz yok." };
    }
    return { status: 500, message: "Şifre güncellenemedi." };
}

const updatePasswordSchema = z.object({
    newPassword: z.string().min(6, "Şifre en az 6 karakter olmalıdır.").optional(),
    passwordHint: z.string().optional(),
}).refine(data => data.newPassword !== undefined || data.passwordHint !== undefined, {
    message: "newPassword veya passwordHint alanlarından en az biri gereklidir.",
});

// PATCH /api/profile/password
// Body: { newPassword?: string, passwordHint?: string }
export async function PATCH(request: NextRequest) {
    try {
        const user = await requireAuthenticatedUser(request);

        const rawBody = await request.json();
        const parseResult = updatePasswordSchema.safeParse(rawBody);
        if (!parseResult.success) {
            return createErrorResponse(parseResult.error.errors[0].message, 400);
        }

        const { newPassword, passwordHint } = parseResult.data;
        const adminClient = getSupabaseAdmin();

        // 1. Update password in Supabase Auth (if provided)
        if (newPassword) {
            const { error: pwError } = await adminClient.auth.admin.updateUserById(user.id, {
                password: newPassword,
            });
            if (pwError) {
                console.error("Profile password update failed:", pwError);
                const mapped = mapPasswordProviderError(pwError);
                return createErrorResponse(mapped.message, mapped.status);
            }
        }

        // 2. Update password_hint in users table (if provided)
        if (passwordHint !== undefined) {
            const { error: dbError } = await adminClient
                .from("users")
                .update({ password_hint: passwordHint, updated_at: new Date().toISOString() } as never)
                .eq("id", user.id);
            if (dbError) {
                console.error("Profile password hint update failed:", dbError);
                return createErrorResponse("Şifre ipucu güncellenemedi.", 500);
            }
        }

        return createSuccessResponse({ message: "Bilgiler başarıyla güncellendi." });
    } catch (error: unknown) {
        // AppError keeps its 401/403 status; anything else becomes a fixed 500 (details logged).
        return handleApiError(error);
    }
}
