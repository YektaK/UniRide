const { createClient } = require('@supabase/supabase-js');
const xlsx = require('xlsx');
const path = require('path');
const dotenv = require('dotenv');

// Load env vars
dotenv.config({ path: path.resolve(__dirname, '.env.local') });
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !supabaseServiceKey) {
    console.error('Hata: .env.local bulunamadı.');
    process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseServiceKey, {
    auth: { autoRefreshToken: false, persistSession: false },
});

async function importMatrix() {
    const excelPath = path.resolve(__dirname, 'Veri.xlsx');
    console.log(`Excel dosyası okunuyor: ${excelPath}`);

    const workbook = xlsx.readFile(excelPath);

    // Try 'Time' sheet, fall back to first sheet
    const sheetName = workbook.SheetNames.includes('Time')
        ? 'Time'
        : workbook.SheetNames[0];
    console.log(`Sayfa kullanılıyor: "${sheetName}"`);

    const sheet = workbook.Sheets[sheetName];

    // Read as raw array of arrays (no automatic header parsing)
    // Row 0 = headers: ["Konumlar", "D.Kampus", "Sw1", "Sw2", ...]
    // Row 1+ = data:   ["D.Kampus",  0,           40,    24, ...]
    const rawData = xlsx.utils.sheet_to_json(sheet, { header: 1, defval: 0 });

    // Row 0 is the header row
    const headerRow = rawData[0];
    // Column A (index 0) is "Konumlar", Columns B+ (index 1+) are destination names
    const destinations = headerRow.slice(1).map(h => String(h).trim()).filter(h => h);
    console.log(`${destinations.length} varış noktası bulundu: ${destinations.join(', ')}`);

    const batchInserts = [];

    // Data rows start from index 1
    for (let rowIdx = 1; rowIdx < rawData.length; rowIdx++) {
        const row = rawData[rowIdx];
        const originName = row[0];

        // Skip empty rows
        if (!originName || String(originName).trim() === '') continue;

        const origin = String(originName).trim();

        // Read each destination duration in this row
        for (let colIdx = 0; colIdx < destinations.length; colIdx++) {
            const destination = destinations[colIdx];
            if (origin === destination) continue; // Skip diagonal (self-to-self)

            const rawVal = row[colIdx + 1]; // +1 because column A is origin name
            let duration = 0.0;
            if (rawVal !== undefined && rawVal !== null && !isNaN(rawVal)) {
                duration = parseFloat(rawVal);
                if (duration < 0) duration = 0;
            }

            batchInserts.push({
                origin_code: origin,
                destination_code: destination,
                duration_minutes: duration
            });
        }
    }

    console.log(`Toplam ${batchInserts.length} rota kombinasyonu Supabase'e yükleniyor...`);

    // Upsert in batches of 500
    const batchSize = 500;
    for (let i = 0; i < batchInserts.length; i += batchSize) {
        const chunk = batchInserts.slice(i, i + batchSize);
        const { error } = await supabase
            .from('time_matrix')
            .upsert(chunk, { onConflict: 'origin_code,destination_code' });

        if (error) {
            console.error(`Hata (${i}-${i + batchSize}):`, error.message);
        } else {
            console.log(`[✓] Yüklendi: ${Math.min(i + batchSize, batchInserts.length)}/${batchInserts.length}`);
        }
    }

    console.log('\n--- Zaman Matrisi Aktarımı Tamamlandı ---');

    // Print a quick verification sample
    const { data: sample } = await supabase
        .from('time_matrix')
        .select('origin_code, destination_code, duration_minutes')
        .eq('origin_code', 'D.Kampus')
        .limit(5);

    if (sample) {
        console.log('\n[Doğrulama] D.Kampus -> Diğer Noktalar (İlk 5):');
        sample.forEach(r => console.log(`  ${r.origin_code} -> ${r.destination_code}: ${r.duration_minutes} dk`));
    }
}

importMatrix();
