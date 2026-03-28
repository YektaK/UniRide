const { createClient } = require('@supabase/supabase-js');
const XLSX = require('xlsx');
const path = require('path');
const dotenv = require('dotenv');

// Load environment variables
dotenv.config({ path: path.resolve(__dirname, '.env.local') });

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !supabaseServiceKey) {
    console.error('Hata: .env.local dosyasında gerekli değişkenler bulunamadı.');
    process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseServiceKey);

const DAY_MAP = {
    'G1': 'monday',
    'G2': 'tuesday',
    'G3': 'wednesday',
    'G4': 'thursday',
    'G5': 'friday'
};

async function processExcelSchedules(dryRun = true) {
    console.log(`--- Ders Programı Aktarımı Başlıyor (${dryRun ? 'DRY RUN - Yazma Yapılmıyor' : 'CANLI - Veritabanına Yazılıyor'}) ---`);

    const filePath = path.resolve('Veri.xlsx');
    const workbook = XLSX.readFile(filePath);

    const studentsSchedules = {};

    // 1. Pick (Okula Geliş) Verilerini Oku
    const pickSheet = workbook.Sheets['Pick'];
    const pickData = XLSX.utils.sheet_to_json(pickSheet, { header: 1 });
    const pickHeaders = pickData[0];

    for (let i = 1; i < pickData.length; i++) {
        const row = pickData[i];
        const ogrenciCode = row[1]; // Ogrenci column
        if (!ogrenciCode) continue;

        if (!studentsSchedules[ogrenciCode]) studentsSchedules[ogrenciCode] = {};

        pickHeaders.forEach((header, idx) => {
            if (typeof header === 'string' && header.startsWith('Pick.') && row[idx] === 1) {
                const parts = header.split('.');
                const dayKey = parts[1]; // G1, G2...
                const hourKey = parts[2]; // S09, S10...

                const day = DAY_MAP[dayKey];
                const hour = hourKey.replace('S', '') + ':00';

                if (day) {
                    if (!studentsSchedules[ogrenciCode][day]) studentsSchedules[ogrenciCode][day] = {};
                    studentsSchedules[ogrenciCode][day].start = hour;
                }
            }
        });
    }

    // 2. Drop (Okuldan Dönüş) Verilerini Oku
    const dropSheet = workbook.Sheets['Drop'];
    const dropData = XLSX.utils.sheet_to_json(dropSheet, { header: 1 });
    const dropHeaders = dropData[0];

    for (let i = 1; i < dropData.length; i++) {
        const row = dropData[i];
        const ogrenciCode = row[1];
        if (!ogrenciCode || !studentsSchedules[ogrenciCode]) continue;

        dropHeaders.forEach((header, idx) => {
            if (typeof header === 'string' && header.startsWith('Drop.') && row[idx] === 1) {
                const parts = header.split('.');
                const dayKey = parts[1];
                const hourKey = parts[2];

                const day = DAY_MAP[dayKey];
                const hour = hourKey.replace('S', '') + ':00';

                if (day && studentsSchedules[ogrenciCode][day]) {
                    studentsSchedules[ogrenciCode][day].end = hour;
                }
            }
        });
    }

    // 3. Supabase ile Eşleştir ve Göster/Aktar
    const { data: dbUsers, error: userError } = await supabase
        .from('users')
        .select('id, student_number, email, location_code')
        .eq('role', 'student');

    if (userError) throw userError;

    console.log(`\nToplam ${dbUsers.length} öğrenci sistemde kayıtlı.`);

    for (const user of dbUsers) {
        // Excel'deki "Ogrenci" sütunu (Sw1, So1...) bizim DB'deki location_code'umuza karşılık geliyor
        const lookupKey = user.location_code;
        const scheduleData = studentsSchedules[lookupKey];

        if (!scheduleData) {
            // console.log(`[!] ${lookupKey} için Excel'de veri bulunamadı.`);
            continue;
        }

        const entries = Object.keys(scheduleData).map((day, idx) => ({
            id: `entry_${Date.now()}_${idx}`,
            dayOfWeek: day,
            startTime: scheduleData[day].start || '09:00',
            endTime: scheduleData[day].end || (scheduleData[day].start ? parseInt(scheduleData[day].start) + 3 + ':00' : '17:00'),
            location: 'Dogus Kampus',
            courseName: 'Ders Programı'
        }));

        console.log(`\n>>> Öğrenci: ${user.student_number} (${user.email})`);
        console.table(entries.map(e => ({ Gün: e.dayOfWeek, Giriş: e.startTime, Çıkış: e.endTime })));

        if (!dryRun) {
            const { data: newSchedule, error: scError } = await supabase
                .from('weekly_schedules')
                .upsert({
                    user_id: user.id,
                    entries: entries,
                    last_updated: new Date().toISOString()
                })
                .select()
                .single();

            if (scError) {
                console.error(`Hata (${user.student_number}):`, scError.message);
            } else {
                await supabase.from('users').update({ weekly_schedule_id: newSchedule.id }).eq('id', user.id);
                console.log(`✅ ${user.student_number} için program güncellendi.`);
            }
        }
    }

    console.log('\n--- İşlem Tamamlandı ---');
}

// Varsayılan olarak dry-run modunda çalıştır
const isLive = process.argv.includes('--live');
processExcelSchedules(!isLive).catch(console.error);
