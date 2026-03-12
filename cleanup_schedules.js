const { createClient } = require('@supabase/supabase-js');
const path = require('path');
const dotenv = require('dotenv');

dotenv.config({ path: path.resolve(__dirname, '.env.local') });

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

const supabase = createClient(supabaseUrl, supabaseServiceKey);

async function cleanupSchedules() {
    console.log('--- Kayıt Temizliği Başlıyor ---\n');

    // 1. Tüm kayıtları al (tarihe göre sıralı)
    const { data: schedules, error } = await supabase
        .from('weekly_schedules')
        .select('id, user_id, created_at, entries')
        .order('created_at', { ascending: false });

    if (error) {
        console.error('Hata:', error.message);
        return;
    }

    const seenUsers = new Set();
    const toDelete = [];
    const validSchedules = {};

    schedules.forEach(s => {
        if (seenUsers.has(s.user_id)) {
            toDelete.push(s.id);
        } else {
            seenUsers.add(s.user_id);
            validSchedules[s.user_id] = s.id;
        }
    });

    console.log(`Silinecek mükerrer kayıt sayısı: ${toDelete.length}`);

    if (toDelete.length > 0) {
        // Toplu silme yapalım (200'erli gruplar halinde)
        for (let i = 0; i < toDelete.length; i += 200) {
            const chunk = toDelete.slice(i, i + 200);
            const { error: delError } = await supabase
                .from('weekly_schedules')
                .delete()
                .in('id', chunk);

            if (delError) console.error('Silme Hatası:', delError.message);
            else console.log(`${chunk.length} kayıt silindi.`);
        }
    }

    // 2. Kullanıcıların weekly_schedule_id referanslarını güncelle (garantiye alalım)
    console.log('\nKullanıcı referansları güncelleniyor...');
    for (const [userId, scheduleId] of Object.entries(validSchedules)) {
        await supabase
            .from('users')
            .update({ weekly_schedule_id: scheduleId })
            .eq('id', userId);
    }

    console.log('\n--- Temizlik Tamamlandı ---');
}

cleanupSchedules();
