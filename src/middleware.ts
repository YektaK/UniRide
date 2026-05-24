import createMiddleware from 'next-intl/middleware';
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { routing } from './i18n/routing';

const intlMiddleware = createMiddleware(routing);

export function middleware(request: NextRequest) {
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
