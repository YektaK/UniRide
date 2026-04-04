import { NextResponse } from 'next/server';
import { getSupabaseAdmin } from '@/lib/supabase-admin';

// DEV ONLY: Password reset for test accounts with fake emails.
// Automatically disabled when NODE_ENV=production.

export async function POST(request: Request) {
    // Block in production
    if (process.env.NODE_ENV === 'production') {
        return NextResponse.json(
            { error: 'Bu endpoint yalnızca geliştirme ortamında kullanılabilir.' },
            { status: 403 }
        );
    }

    try {
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
