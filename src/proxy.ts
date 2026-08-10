import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { createClient } from '@supabase/supabase-js';

function getSupabaseAnon() {
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    return url && key ? createClient(url, key) : null;
}

export async function proxy(request: NextRequest) {
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return NextResponse.json(
            { error: 'Unauthorized: Missing or invalid token in request header' },
            { status: 401 }
        );
    }

    const token = authHeader.slice(7);
    // Verify the JWT token with Supabase
    const supabaseAnon = getSupabaseAnon();
    if (!supabaseAnon) {
        return NextResponse.json(
            { error: 'Authentication service unavailable' },
            { status: 503 }
        );
    }

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

export const config = {
    matcher: ['/api/admin/:path*'],
};
