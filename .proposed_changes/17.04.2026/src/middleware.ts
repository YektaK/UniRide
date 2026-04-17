import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Next.js Middleware
 * Runs on Edge runtime before requests are completed.
 * Centralized protection for admin routes.
 */
export function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl;

    // Protect all /api/admin/* routes
    if (pathname.startsWith('/api/admin')) {
        const authHeader = request.headers.get('authorization');

        // Fast-fail if no token is provided. 
        // Note: The actual JWT validation and role checking (RBAC) 
        // is independently handled inside the API route via `requireAdmin()` 
        // because Edge runtime poses limitations for querying Supabase DB roles.
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return NextResponse.json(
                { error: 'Unauthorized: Missing or invalid token in request header' },
                { status: 401 }
            );
        }
    }

    return NextResponse.next();
}

// Specify the paths where this middleware should run
export const config = {
    matcher: [
        '/api/admin/:path*',
    ],
};
