# Supabase Kurulum Sonrası Adımlar

Mock database kaldırıldı, Supabase kurulumuna geçebiliriz!

## ✅ Yapılan Değişiklikler

1. ✅ Mock database kodları kaldırıldı
2. ✅ Conditional export hatası düzeltildi
3. ✅ `next.config.ts` eslint hatası düzeltildi
4. ✅ Supabase placeholder dosyaları oluşturuldu
5. ✅ `@supabase/supabase-js` paketi `package.json`'a eklendi

## 🚀 Şimdi Yapılacaklar

### 1. Supabase Paketini Yükle

**Windows 11 - PowerShell:**
```powershell
npm install @supabase/supabase-js
```

### 2. Supabase Hesabı Oluştur

1. https://supabase.com adresine git
2. Ücretsiz hesap oluştur (GitHub ile önerilir)
3. Yeni proje oluştur:
   - **Name:** `uniride`
   - **Database Password:** Güçlü bir şifre oluştur (SAKLA!)
   - **Region:** `West Europe (Ireland)` veya Türkiye'ye yakın bir bölge

### 3. Database Schema Oluştur

1. Supabase Dashboard > SQL Editor
2. `supabase/schema.sql` dosyasındaki SQL'i kopyala ve çalıştır
3. `supabase/rls_policies.sql` dosyasındaki SQL'i kopyala ve çalıştır

### 4. API Keys'i Al

1. Supabase Dashboard > Settings > API
2. **Project URL** ve **anon public key**'i kopyala

### 5. .env.local Dosyasını Oluştur

**Windows 11 - PowerShell:**
```powershell
Set-Content -Path ".env.local" -Value @"
NEXT_PUBLIC_USE_SUPABASE=true
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
"@
```

**VEYA VS Code ile:**
1. `.env.local` dosyası oluştur
2. İçine yaz:
   ```
   NEXT_PUBLIC_USE_SUPABASE=true
   NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```
3. Kaydet (Ctrl+S)

### 6. Supabase Database Adapter'ı Oluştur

`src/lib/supabase-db.ts` dosyasını implement et (TODO: İleride yapılacak)

### 7. Supabase Authentication'ı Oluştur

`src/lib/supabase-auth.ts` dosyasını implement et (TODO: İleride yapılacak)

---

## ⏳ Şimdilik

- Kodlar **Firebase** ile çalışmaya devam ediyor
- Supabase setup dosyaları hazır
- Supabase client hazır (`src/lib/supabase.ts`)
- Database adapter ve auth **TODO** - Supabase kurulumundan sonra implement edilecek

---

## 📝 Notlar

- Mock database kaldırıldı - artık sadece Firebase ve Supabase var
- Conditional export hatası düzeltildi
- `next.config.ts` eslint config'i kaldırıldı
- Supabase kurulumu için `SUPABASE_SETUP.md` dosyasını takip et

---

**Supabase kurulumu yapıldıktan sonra haber ver, database adapter'ı implement edelim!** 🚀

