import { NextResponse } from 'next/server';
import { getSupabaseAdmin } from '@/lib/supabase-admin';
import type { Database } from '@/lib/supabase';

// ==================== RATE LIMITING ====================
// Simple in-memory rate limiter (per IP, 5 requests per minute)
const RATE_LIMIT_WINDOW_MS = 60 * 1000; // 1 minute
const RATE_LIMIT_MAX = 5;

const rateLimitMap = new Map<string, { count: number; resetTime: number }>();

function isRateLimited(ip: string): boolean {
    const now = Date.now();
    const entry = rateLimitMap.get(ip);

    if (!entry || now > entry.resetTime) {
        rateLimitMap.set(ip, { count: 1, resetTime: now + RATE_LIMIT_WINDOW_MS });
        return false;
    }

    entry.count++;
    if (entry.count > RATE_LIMIT_MAX) {
        return true;
    }
    return false;
}

// Periodically clean up expired entries to prevent memory leaks
setInterval(() => {
    const now = Date.now();
    for (const [key, value] of rateLimitMap) {
        if (now > value.resetTime) {
            rateLimitMap.delete(key);
        }
    }
}, 5 * 60 * 1000); // Clean every 5 minutes

// ==================== HANDLER ====================

export async function POST(request: Request) {
    try {
        // Rate limit check
        const ip = request.headers.get('x-forwarded-for')?.split(',')[0]?.trim()
            || request.headers.get('x-real-ip')
            || 'unknown';

        if (isRateLimited(ip)) {
            return NextResponse.json(
                { error: 'Çok fazla istek gönderildi. Lütfen bir dakika bekleyin.' },
                { status: 429 }
            );
        }

        const { emailOrStudentNumber } = await request.json();

        if (!emailOrStudentNumber) {
            return NextResponse.json({ error: 'E-posta veya öğrenci numarası gerekli' }, { status: 400 });
        }
        if (typeof emailOrStudentNumber !== "string") {
            return NextResponse.json({ error: 'Geçersiz kullanıcı bilgisi formatı' }, { status: 400 });
        }

        const normalizedInput = emailOrStudentNumber.trim();
        if (!normalizedInput) {
            return NextResponse.json({ error: 'E-posta veya öğrenci numarası gerekli' }, { status: 400 });
        }

        // Use admin client to bypass RLS — password_hint is intentionally non-sensitive
        const adminClient = getSupabaseAdmin();
        const baseQuery = adminClient
            .from('users')
            .select('password_hint')
            .limit(1);

        const emailRegex = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        const studentNumberRegex = /^[a-zA-Z0-9_-]{3,32}$/;

        const query = emailRegex.test(normalizedInput)
            ? baseQuery.eq("email", normalizedInput.toLowerCase())
            : studentNumberRegex.test(normalizedInput)
                ? baseQuery.eq("student_number", normalizedInput)
                : null;

        if (!query) {
            return NextResponse.json({ error: 'Geçersiz e-posta veya öğrenci numarası formatı' }, { status: 400 });
        }

        const { data, error } = await query.single();

        if (error || !data) {
            // Return generic message to avoid user enumeration
            return NextResponse.json(
                { hint: null, message: "Kullanıcı bulunamadı veya ipucu ayarlanmamış." },
                { status: 200 }
            );
        }

        const userWithHint = data as Pick<Database["public"]["Tables"]["users"]["Row"], "password_hint">;
        return NextResponse.json({
            hint: userWithHint.password_hint || "Bu hesap için özel bir ipucu tanımlanmamış."
        }, { status: 200 });

    } catch (error) {
        console.error('Error fetching password hint:', error);
        return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
    }
}
