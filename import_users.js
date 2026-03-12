const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');

// Load environment variables from .env.local
dotenv.config({ path: path.resolve(__dirname, '.env.local') });

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !supabaseServiceKey) {
    console.error('Hata: .env.local dosyasında NEXT_PUBLIC_SUPABASE_URL veya SUPABASE_SERVICE_ROLE_KEY bulunamadı.');
    process.exit(1);
}

// Initialize Supabase Admin Client
const supabase = createClient(supabaseUrl, supabaseServiceKey, {
    auth: { autoRefreshToken: false, persistSession: false },
});

// A simple CSV parser (Assumes comma delimited, no commas inside values for simplicity)
function parseCSV(filePath) {
    let content = fs.readFileSync(filePath, 'utf8');

    // Remove BOM (Byte Order Mark) if it exists so first header reads correctly
    if (content.charCodeAt(0) === 0xFEFF) {
        content = content.substring(1);
    }

    const lines = content.split(/\r?\n/).filter((line) => line.trim().length > 0);

    // Auto-detect delimiter based on first line
    const delimiter = lines[0].includes(';') ? ';' : ',';
    const headers = lines[0].split(delimiter).map((h) => h.trim());

    const results = [];
    for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(delimiter).map((v) => v.trim());
        const obj = {};
        headers.forEach((header, index) => {
            obj[header] = values[index] || null;
        });
        results.push(obj);
    }
    return results;
}

// Function to handle Turkish comma decimals (e.g., "40,825" -> 40.825)
function parseCoordinate(coordStr) {
    if (!coordStr) return null;
    // Replace comma with dot and parse as float
    const floatVal = parseFloat(coordStr.replace(',', '.'));
    return isNaN(floatVal) ? null : floatVal;
}

async function importUsers() {
    const csvPath = path.resolve(__dirname, 'test_users.csv');

    if (!fs.existsSync(csvPath)) {
        console.error(`Hata: ${csvPath} dosyası bulunamadı.`);
        console.log('Lütfen Excel tablonuzu "test_users.csv" adıyla bu klasöre kaydedin.');
        process.exit(1);
    }

    const users = parseCSV(csvPath);
    console.log(`Tabloda ${users.length} kullanıcı bulundu. İçe aktarım başlıyor...`);

    for (const user of users) {
        if (!user.email || !user.password) {
            console.warn(`Uyarı: Şifre veya E-posta eksik (Satır atlanıyor: ${JSON.stringify(user)})`);
            continue;
        }

        try {
            // 1. Create user in auth.users
            console.log(`İşleniyor: ${user.email} (${user.name})...`);
            const { data: authData, error: authError } = await supabase.auth.admin.createUser({
                email: user.email.toLowerCase(),
                password: user.password,
                email_confirm: true, // Auto-confirm for testing
            });

            if (authError) {
                console.error(`Auth Hatası (${user.email}):`, authError.message);
                continue;
            }

            const userId = authData.user.id;
            const now = new Date().toISOString();

            // 2. Parse geographical coordinates if provided
            const lat = parseCoordinate(user.lat);
            const lng = parseCoordinate(user.lng);
            let home_coordinates = null;
            if (lat !== null && lng !== null) {
                // Note: Supabase stores JSONB as stringified or raw objects. 
                // In our schema if it's a jsonb column, passing the object directly works.
                home_coordinates = { lat, lng };
            }

            // 3. Create user in public.users
            const publicUserData = {
                id: userId,
                name: user.name || 'İsimsiz Kullanıcı',
                email: user.email.toLowerCase(),
                role: user.role || 'student',
                student_number: user.studentNumber || null,
                password_hint: user.passwordHint || null,
                disability_type: user.disabilityType || null,
                location_code: user.locationCode || null,
                home_coordinates: home_coordinates,
                home_address: '', // Default empty
                created_at: now,
                updated_at: now,
            };

            const { error: dbError } = await supabase.from('users').insert([publicUserData]);

            if (dbError) {
                console.error(`Veritabanı Kayıt Hatası (${user.email}):`, dbError.message);
                // Optionally delete auth user here to keep consistency, but we'll leave it simple
                continue;
            }

            // 3. Create Weekly Schedule if Student
            if ((user.role || 'student') === 'student') {
                const scheduleData = {
                    user_id: userId,
                    entries: [],
                    last_updated: now,
                    created_at: now,
                    updated_at: now,
                };

                const { data: scheduleReturn, error: scheduleError } = await supabase
                    .from('weekly_schedules')
                    .insert([scheduleData])
                    .select()
                    .single();

                if (scheduleError) {
                    console.error(`Program Oluşturma Hatası (${user.email}):`, scheduleError.message);
                } else if (scheduleReturn) {
                    // Update user with schedule ID
                    await supabase.from('users').update({ weekly_schedule_id: scheduleReturn.id }).eq('id', userId);
                }
            }

            console.log(`✅ Başarılı: ${user.email}`);
        } catch (e) {
            console.error(`Sistem Hatası (${user.email}):`, e.message);
        }
    }

    console.log('--- İçe Aktarma İşlemi Tamamlandı ---');
}

importUsers();
