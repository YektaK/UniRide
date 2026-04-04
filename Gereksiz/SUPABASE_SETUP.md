# Supabase Setup Guide - UniRide Project

## 🚀 Adım 1: Supabase Hesabı Oluştur

1. **Supabase'e Git:**
   - Tarayıcıda https://supabase.com adresine git
   - "Start your project" butonuna tıkla
   - GitHub ile giriş yap (önerilir) veya email ile kayıt ol

2. **Yeni Proje Oluştur:**
   - "New Project" butonuna tıkla
   - Organization seç (yoksa oluştur)
   - Proje detayları:
     - **Name:** `uniride` (veya istediğin isim)
     - **Database Password:** Güçlü bir şifre oluştur (SAKLA! - Notepad'e kopyala)
     - **Region:** `West Europe (Ireland)` veya Türkiye'ye yakın bir bölge
   - "Create new project" butonuna tıkla
   - Proje hazırlanması 2-3 dakika sürebilir (bekle)

---

## 📊 Adım 2: Database Schema Oluştur

1. **Supabase Dashboard'da SQL Editor'e Git:**
   - Sol menüden "SQL Editor" seç
   - "New query" butonuna tıkla

2. **Schema SQL'ini Çalıştır:**
   
   `schema.sql` dosyasındaki SQL'i kopyala ve Supabase SQL Editor'de çalıştır.

   Bu şunları oluşturur:
   - `users` tablosu
   - `weekly_schedules` tablosu
   - `schedule_entries` tablosu (nested array yerine ayrı tablo)
   - `ride_requests` tablosu
   - `vehicles` tablosu
   - `routes` tablosu
   - `route_assignments` tablosu
   - `notifications` tablosu
   - İlişkiler ve indeksler

---

## 🔐 Adım 3: Authentication Ayarları

1. **Authentication'a Git:**
   - Sol menüden "Authentication" seç
   - "Providers" altında "Email" aktif olmalı (varsayılan olarak aktif)

2. **Email Template'leri (Opsiyonel):**
   - "Email Templates" sekmesine git
   - İstersen Türkçe email template'leri oluşturabilirsin

3. **Auth Settings:**
   - "Settings" sekmesine git
   - "Site URL" alanına development URL'i ekle: `http://localhost:9002`
   - "Redirect URLs" alanına ekle: `http://localhost:9002/**`

---

## 🔑 Adım 4: API Keys ve Environment Variables

1. **Project Settings'e Git:**
   - Sol menüden "Project Settings" (⚙️) seç
   - "API" sekmesine git

2. **Keys'i Kopyala:**
   - **Project URL:** `https://xxxxx.supabase.co`
   - **anon public key:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   - **service_role key:** SAKLA! (sadece server-side için)

3. **`.env.local` Dosyasını Oluştur/Güncelle:**
   
   **Windows 11 - PowerShell:**
   ```powershell
   Set-Content -Path ".env.local" -Value @"
   NEXT_PUBLIC_USE_SUPABASE=true
   NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   "@
   ```
   
   **VEYA Manuel (Önerilen - VS Code):**
   - VS Code'da `.env.local` dosyası oluştur veya aç
   - İçine yaz (kendi değerlerinle değiştir):
     ```
     NEXT_PUBLIC_USE_SUPABASE=true
     NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
     NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
     ```
   - Kaydet (Ctrl+S)
   
   **Önemli:** `xxxxx` yerine Supabase URL'inizi, `eyJhbG...` yerine anon key'inizi yazın!

---

## 📦 Adım 5: Supabase Client Kurulumu

**Windows 11 - PowerShell veya CMD:**

Supabase client paketini yükle:

```powershell
npm install @supabase/supabase-js
```

VEYA CMD:
```cmd
npm install @supabase/supabase-js
```

---

## ✅ Adım 6: Test

1. **Development Server'ı Başlat:**
   
   **Windows 11 - PowerShell:**
   ```powershell
   npm run dev
   ```
   
   **Windows 11 - CMD:**
   ```cmd
   npm run dev
   ```

2. **Test Et:**
   - Tarayıcıda http://localhost:9002/login adresine git
   - Yeni kullanıcı oluştur (Register sayfası)
   - Giriş yap (Login sayfası)
   - Tüm özellikleri test et

---

## 🔒 Adım 7: Row Level Security (RLS) Ayarları

Supabase SQL Editor'de `rls_policies.sql` dosyasındaki RLS policy'lerini çalıştır.

Bu şunları sağlar:
- Kullanıcılar sadece kendi verilerini görebilir
- Admin'ler tüm verileri görebilir
- Şoförler sadece kendi görevlendirmelerini görebilir

---

## 📝 Notlar

1. **Free Tier Limits:**
   - 500MB veritabanı
   - 50K aylık aktif kullanıcı
   - 2GB dosya depolama
   - 2GB bant genişliği
   - Projeler için genellikle yeterli!

2. **Backup:**
   - Supabase otomatik backup alır
   - Proje Settings'ten manuel backup da alabilirsin

3. **Monitoring:**
   - Dashboard'dan database usage'ı takip edebilirsin
   - Logs sekmesinden sorguları görebilirsin

---

## 🆘 Sorun Giderme

**"relation does not exist" hatası:**
- SQL schema'yı doğru çalıştırdığından emin ol
- Tablo isimlerinin doğru olduğunu kontrol et

**Authentication hatası:**
- API keys'lerin doğru olduğundan emin ol
- Environment variables'ın yeniden yüklendiğinden emin ol (server restart)

**Connection hatası:**
- Supabase URL'inin doğru olduğunu kontrol et
- Internet bağlantını kontrol et

---

## 🎯 Sonraki Adımlar

1. ✅ Supabase kurulumu tamamlandı
2. ⏳ Kodları Supabase'e migrate et (otomatik yapılacak)
3. ⏳ Test et ve deploy et

Supabase kurulumu tamamlandığında haber ver, kod migration'ını yapalım! 🚀

