/**
 * Self-Service Profile Password Update API
 * Allows any logged-in user to update their own password and password hint
 */

import { NextRequest } from "next/server";
import { createClient } from "@supabase/supabase-js";
import { getSupabaseAdmin } from "@/lib/supabase-admin";
import { createErrorResponse, createSuccessResponse, handleApiError } from "@/lib/admin-auth";

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

        const body = await request.json();
        const { newPassword, passwordHint } = body;

        const adminClient = getSupabaseAdmin();

        // 1. Update password in Supabase Auth (if provided)
        if (newPassword) {
            if (newPassword.length < 6) {
                return createErrorResponse("Şifre en az 6 karakter olmalıdır.", 400);
            }
            const { error: pwError } = await adminClient.auth.admin.updateUserById(user.id, {
                password: newPassword,
            });
            if (pwError) {
                return createErrorResponse(pwError.message, 500);
            }
        }

        // 2. Update password_hint in users table (if provided)
        if (passwordHint !== undefined) {
            const { error: dbError } = await (adminClient as any)
                .from("users")
                .update({ password_hint: passwordHint, updated_at: new Date().toISOString() })
                .eq("id", user.id);
            if (dbError) {
                return createErrorResponse(dbError.message, 500);
            }
        }

        return createSuccessResponse({ message: "Bilgiler başarıyla güncellendi." });
    } catch (error: any) {
        return createErrorResponse(error.message, 500);
    }
}
