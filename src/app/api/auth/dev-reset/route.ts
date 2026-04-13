import { NextResponse } from 'next/server';
import { getSupabaseAdmin } from '@/lib/supabase-admin';

// DEV ONLY: Password reset for test accounts with fake emails.
// Automatically disabled when NODE_ENV=production.

export async function POST(request: Request) {
    const isLocalEnv = (process.env.NODE_ENV !== 'production') && (
        process.env.VERCEL_ENV === undefined ||
        process.env.VERCEL_ENV === 'development'
    );
    const isDevResetEnabled = process.env.ENABLE_DEV_RESET === 'true';
    const expectedSecret = process.env.DEV_RESET_SECRET;

    if (!isLocalEnv || !isDevResetEnabled) {
        return NextResponse.json(
            { error: 'Bu endpoint yalnızca geliştirme ortamında kullanılabilir.' },
            { status: 403 }
        );
    }

    try {
        if (expectedSecret) {
            const authHeader = request.headers.get('authorization');
            if (!authHeader?.startsWith('Bearer ') || authHeader.slice('Bearer '.length).trim() !== expectedSecret) {
                return NextResponse.json({ error: 'Yetkisiz erişim.' }, { status: 401 });
            }
        }

        const { email, newPassword } = await request.json();

        if (!email || !newPassword) {
            return NextResponse.json({ error: 'E-posta ve yeni şifre gerekli' }, { status: 400 });
        }

        const supabase = getSupabaseAdmin();

        // Find user by email
        const { data: users, error: findError } = await supabase.from('users').select('id, email').eq('email', email.toLowerCase()).single();

        if (findError || !users) {
            return NextResponse.json({ error: 'Kullanıcı bulunamadı.' }, { status: 404 });
        }

        // Update password via Supabase Admin Auth
        const { error: authError } = await supabase.auth.admin.updateUserById(
            (users as any).id,
            { password: newPassword }
        );

        if (authError) {
            console.error('Admin update failed:', authError);
            return NextResponse.json({
                error: 'Şifre güncellenemedi.',
                details: authError.message
            }, { status: 500 });
        }

        return NextResponse.json({ success: true, message: 'Şifre başarıyla güncellendi.' }, { status: 200 });

    } catch (error) {
        console.error('Dev reset error:', error);
        return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
    }
}
