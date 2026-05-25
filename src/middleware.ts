import createMiddleware from 'next-intl/middleware';
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { routing } from './i18n/routing';
import { createClient } from '@supabase/supabase-js';

const intlMiddleware = createMiddleware(routing);

// Supabase anon client for JWT verification in middleware
// Uses anon key (safe for middleware — no service role exposure)
const supabaseAnon = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL ?? '',
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? '',
);

export async function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl;

    if (pathname.startsWith('/api')) {
        if (pathname.startsWith('/api/admin')) {
            const authHeader = request.headers.get('authorization');
            if (!authHeader || !authHeader.startsWith('Bearer ')) {
                return NextResponse.json(
                    { error: 'Unauthorized: Missing or invalid token in request header' },
                    { status: 401 }
                );
            }
            const token = authHeader.slice(7);
            // Verify the JWT token with Supabase
            const { data: { user }, error } = await supabaseAnon.auth.getUser(token);
            if (error || !user) {
                return NextResponse.json(
                    { error: 'Unauthorized: Invalid or expired token' },
                    { status: 401 }
                );
            }
            // Forward user info via headers for downstream use
            const headers = new Headers(request.headers);
            headers.set('x-user-id', user.id);
            return NextResponse.next({ request: { headers } });
        }
        return NextResponse.next();
    }

    return intlMiddleware(request);
}

export const config = {
    matcher: [
        '/((?!_next|_vercel|.*\\..*).*)',
    ],
};
