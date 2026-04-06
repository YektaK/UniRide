# Database Configuration Guide

UniRide projesi şu anda **3 farklı database** seçeneği destekliyor:

1. **Mock Database** (Hızlı test için)
2. **Firebase Firestore** (Production - kota sorunu var)
3. **Supabase** (Önerilen - Production ready)

---

## 🎯 Hızlı Başlangıç

### Seçenek 1: Mock Database ile Test (5 dakika) ⚡

**En hızlı yol - hemen çalışır!**

1. **`.env.local` dosyası oluştur:**
   
   **Windows 11 - PowerShell:**
   ```powershell
   Set-Content -Path ".env.local" -Value "NEXT_PUBLIC_USE_MOCK_DB=true"
   ```
   
   **Windows 11 - CMD:**
   ```cmd
   echo NEXT_PUBLIC_USE_MOCK_DB=true > .env.local
   ```
   
   **VEYA Manuel (Önerilen):**
   - VS Code veya Notepad ile `.env.local` dosyası oluştur
   - İçine yaz: `NEXT_PUBLIC_USE_MOCK_DB=true`
   - Proje klasörüne kaydet

2. **Server'ı başlat:**
   ```powershell
   npm run dev
   ```

3. **Test kullanıcıları:**
   - Admin: `admin@uniride.com` / `admin`
   - Öğrenci: `student@uniride.com` / `studentpassword`

✅ **Hazır!** Tüm özellikler çalışır, veriler bellekte tutulur (sayfa yenilenince kaybolur).

---

### Seçenek 2: Supabase (Production) 🚀

**En önerilen seçenek - production ready!**

1. **Supabase hesabı oluştur:**
   - https://supabase.com adresine git
   - Ücretsiz hesap oluştur
   - Yeni proje oluştur

2. **Database schema'sını oluştur:**
   - Supabase Dashboard > SQL Editor
   - `supabase/schema.sql` dosyasını çalıştır
   - `supabase/rls_policies.sql` dosyasını çalıştır

3. **API Keys'i al:**
   - Supabase Dashboard > Settings > API
   - Project URL ve anon key'i kopyala

4. **`.env.local` dosyasını güncelle:**
   
   **Windows 11 - PowerShell:**
   ```powershell
   Set-Content -Path ".env.local" -Value @"
   NEXT_PUBLIC_USE_SUPABASE=true
   NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   "@
   ```
   
   **VEYA Manuel (Önerilen):**
   - VS Code ile `.env.local` dosyasını aç
   - İçine yaz:
     ```
     NEXT_PUBLIC_USE_SUPABASE=true
     NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
     NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
     ```
   - Kaydet

5. **Supabase client paketini yükle:**
   ```powershell
   npm install @supabase/supabase-js
   ```

6. **Detaylı setup:**
   - `SUPABASE_SETUP.md` dosyasını takip et

✅ **Hazır!** Production ready database ile çalışıyorsun.

---

### Seçenek 3: Firebase (Eski - Kota Sorunu Var) ⚠️

Firebase'de proje kotası dolmuş durumda. Ancak kodlar hala hazır, Firebase kurulumu yapıldığında çalışır.

Detaylı setup için: `FIREBASE_SETUP.md`

---

## 🔄 Database Seçimi

Database seçimi `.env.local` dosyasındaki environment variable'larla kontrol edilir:

```env
# Mock Database (test için)
NEXT_PUBLIC_USE_MOCK_DB=true

# VEYA

# Supabase (production için)
NEXT_PUBLIC_USE_SUPABASE=true
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...

# VEYA

# Firebase (varsayılan - eğer hiçbiri set edilmemişse)
# Herhangi bir variable set etme
```

**Önemli:** Her seferinde sadece birini aktif et!

---

## 📊 Database Karşılaştırması

| Özellik | Mock DB | Supabase | Firebase |
|---------|---------|----------|----------|
| Ücretsiz | ✅ | ✅ | ✅ |
| Production Ready | ❌ | ✅ | ✅ |
| Kurulum Süresi | 1 dk | 30-60 dk | 30 dk |
| Veri Kalıcılığı | ❌ | ✅ | ✅ |
| Authentication | Mock | ✅ | ✅ |
| Realtime | ❌ | ✅ | ✅ |
| Kota Sorunu | ❌ | ❌ | ⚠️ Var |

---

## 🚀 Önerilen Yaklaşım

1. **Development/Test için:**
   - Mock Database kullan
   - Hızlı test için ideal

2. **Production için:**
   - Supabase kullan
   - Ücretsiz tier yeterli
   - Firebase'e benzer API

3. **Gelecek için:**
   - Supabase Pro ($25/ay) gerekirse
   - Veya Firebase kota sorunu çözülürse Firebase'e dönebilirsin

---

## 📝 Notlar

- Kodlar **3 seçeneği de destekler** - sadece environment variable değiştir
- Mock database için **hiçbir setup gerekmez**
- Supabase için **detaylı setup** rehberi: `SUPABASE_SETUP.md`
- Firebase için **detaylı setup** rehberi: `FIREBASE_SETUP.md`

---

## 🆘 Sorun Giderme

**"Missing Supabase environment variables" hatası:**
- `.env.local` dosyasında `NEXT_PUBLIC_USE_SUPABASE=true` olduğundan emin ol
- Supabase URL ve key'lerin doğru olduğunu kontrol et

**Database değişikliği çalışmıyor:**
- Server'ı yeniden başlat (environment variables değişince gerekir)
- `.env.local` dosyasının doğru yerde olduğunu kontrol et (proje root'unda)

**Mock database çalışmıyor:**
- `.env.local` dosyasında `NEXT_PUBLIC_USE_MOCK_DB=true` olduğundan emin ol
- Diğer database variable'larını sil veya comment out et

---

## 📚 Detaylı Dokümantasyon

- **Mock Database:** `src/lib/mock-database.ts`
- **Supabase Setup:** `SUPABASE_SETUP.md`
- **Firebase Setup:** `FIREBASE_SETUP.md`
- **Alternatifler:** `ALTERNATIVES.md`

---

**Hangi database'i kullanacağını seç ve ilgili rehberi takip et!** 🎯

