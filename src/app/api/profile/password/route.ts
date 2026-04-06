/**
 * Self-Service Profile Password Update API
 * Allows any logged-in user to update their own password and password hint
 */

import { NextRequest } from "next/server";
import { z } from "zod";
import { createClient } from "@supabase/supabase-js";
import { getSupabaseAdmin } from "@/lib/supabase-admin";
import { createErrorResponse, createSuccessResponse } from "@/lib/admin-auth";

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
        // Authenticate the calling user via Bearer token
        const authHeader = request.headers.get("authorization");
        if (!authHeader?.startsWith("Bearer ")) {
            return createErrorResponse("Unauthorized: Not logged in", 401);
        }
        const token = authHeader.split(" ")[1];

        const supabase = createClient(
            process.env.NEXT_PUBLIC_SUPABASE_URL!,
            process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
        );
        const { data: { user }, error: authError } = await supabase.auth.getUser(token);
        if (authError || !user) {
            return createErrorResponse("Unauthorized: Invalid session", 401);
        }

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
                return createErrorResponse(pwError.message, 500);
            }
        }

        // 2. Update password_hint in users table (if provided)
        if (passwordHint !== undefined) {
            const { error: dbError } = await adminClient
                .from("users")
                .update({ password_hint: passwordHint, updated_at: new Date().toISOString() } as never)
                .eq("id", user.id);
            if (dbError) {
                return createErrorResponse(dbError.message, 500);
            }
        }

        return createSuccessResponse({ message: "Bilgiler başarıyla güncellendi." });
    } catch (error: unknown) {
        return createErrorResponse(error instanceof Error ? error.message : "Internal server error", 500);
    }
}
