const { createClient } = require('@supabase/supabase-js');
const path = require('path');
const dotenv = require('dotenv');

dotenv.config({ path: path.resolve(__dirname, '.env.local') });

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

const supabase = createClient(supabaseUrl, supabaseServiceKey);

async function analyzeSchedules() {
    console.log('--- Veritabanı Analizi Başlıyor ---\n');

    // 1. Tüm kullanıcıları al
    const { data: users } = await supabase.from('users').select('id, email, student_number');
    const userIds = new Set(users.map(u => u.id));
    console.log(`Sistemdeki toplam kullanıcı sayısı: ${users.length}`);

    // 2. Tüm haftalık çizelgeleri al
    const { data: schedules } = await supabase.from('weekly_schedules').select('id, user_id, created_at');
    console.log(`Haftalık çizelge tablosundaki toplam kayıt sayısı: ${schedules.length}`);

    const schedulesByUser = {};
    const orphanedSchedules = [];

    schedules.forEach(s => {
        if (!userIds.has(s.user_id)) {
            orphanedSchedules.push(s);
        } else {
            if (!schedulesByUser[s.user_id]) schedulesByUser[s.user_id] = [];
            schedulesByUser[s.user_id].push(s);
        }
    });

    console.log(`\nYetim (Kullanıcısı olmayan) kayıtlar: ${orphanedSchedules.length}`);
    if (orphanedSchedules.length > 0) {
        console.table(orphanedSchedules);
    }

    const duplicates = Object.keys(schedulesByUser).filter(uid => schedulesByUser[uid].length > 1);
    console.log(`\nMükerrer (Birden fazla kaydı olan) kullanıcılar: ${duplicates.length}`);

    if (duplicates.length > 0) {
        duplicates.forEach(uid => {
            const user = users.find(u => u.id === uid);
            console.log(`\n>>> Kullanıcı: ${user.email} (${uid})`);
            console.table(schedulesByUser[uid]);
        });
    }

    console.log('\n--- Analiz Tamamlandı ---');
}

analyzeSchedules();
