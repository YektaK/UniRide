import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import {
    buildContentSecurityPolicy,
    buildHstsHeader,
    generateNonce,
} from '@/lib/security-headers';

function getSupabaseAnon() {
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    return url && key ? createClient(url, key) : null;
}

function isGatedApiPath(pathname: string): boolean {
    return (
        pathname === '/api/admin' ||
        pathname.startsWith('/api/admin/') ||
        pathname === '/api/benchmark' ||
        pathname.startsWith('/api/benchmark/')
    );
}

function withHsts<T extends NextResponse>(response: T): T {
    const hsts = buildHstsHeader(process.env.NODE_ENV === 'production');
    if (hsts) response.headers.set('Strict-Transport-Security', hsts);
    return response;
}

/**
 * Per-request nonce CSP for page responses (audit M8 / QW8). Next.js reads
 * the nonce from the *request* Content-Security-Policy header and applies it
 * to its own scripts; the same value is returned on the response.
 */
function nextWithCsp(request: NextRequest, extraRequestHeaders?: Headers) {
    const nonce = generateNonce();
    const csp = buildContentSecurityPolicy({
        nonce,
        isProduction: process.env.NODE_ENV === 'production',
        supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL,
        optimizerUrls: [
            process.env.OPTIMIZER_API_URL,
            process.env.NEXT_PUBLIC_OPTIMIZER_API_URL,
        ],
    });

    const headers = new Headers(extraRequestHeaders ?? request.headers);
    headers.set('x-nonce', nonce);
    headers.set('Content-Security-Policy', csp);

    const response = NextResponse.next({ request: { headers } });
    response.headers.set('Content-Security-Policy', csp);
    return withHsts(response);
}

export async function proxy(request: NextRequest) {
    if (!isGatedApiPath(request.nextUrl.pathname)) {
        return nextWithCsp(request);
    }

    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return withHsts(NextResponse.json(
            { error: 'Unauthorized: Missing or invalid token in request header' },
            { status: 401 }
        ));
    }

    const token = authHeader.slice(7);
    // Verify the JWT token with Supabase
    const supabaseAnon = getSupabaseAnon();
    if (!supabaseAnon) {
        return withHsts(NextResponse.json(
            { error: 'Authentication service unavailable' },
            { status: 503 }
        ));
    }

    const { data: { user }, error } = await supabaseAnon.auth.getUser(token);
    if (error || !user) {
        return withHsts(NextResponse.json(
            { error: 'Unauthorized: Invalid or expired token' },
            { status: 401 }
        ));
    }

    // Forward user info via headers for downstream use
    const headers = new Headers(request.headers);
    headers.set('x-user-id', user.id);
    return nextWithCsp(request, headers);
}

export const config = {
    matcher: [
        '/api/admin/:path*',
        '/api/benchmark/:path*',
        {
            // Pages only: skip other API routes, static assets and image optimisation.
            source: '/((?!api|_next/static|_next/image|favicon.ico).*)',
            missing: [
                { type: 'header', key: 'next-router-prefetch' },
                { type: 'header', key: 'purpose', value: 'prefetch' },
            ],
        },
    ],
};
