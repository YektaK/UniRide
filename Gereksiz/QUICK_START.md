# Hızlı Başlangıç - Firebase Alternatifi

## 🎯 Seçenekler

### Seçenek 1: Mock Database ile Devam (5 dakika) ⚡

**Avantajlar:**
- ✅ Hemen çalışır
- ✅ Hiçbir kurulum gerekmez
- ✅ Firebase sorunu olmadan test
- ✅ Tüm özellikler test edilebilir

**Eksiler:**
- ❌ Veriler kalıcı değil (sayfa yenilenince kaybolur)
- ❌ Production'da kullanılamaz
- ❌ Multi-user çalışmaz

**Yapılacaklar (Windows 11):**

1. **`.env.local` dosyası oluştur:**
   
   PowerShell:
   ```powershell
   Set-Content -Path ".env.local" -Value "NEXT_PUBLIC_USE_MOCK_DB=true"
   ```
   
   VEYA CMD:
   ```cmd
   echo NEXT_PUBLIC_USE_MOCK_DB=true > .env.local
   ```
   
   VEYA Manuel: VS Code ile `.env.local` oluştur, içine `NEXT_PUBLIC_USE_MOCK_DB=true` yaz

2. **Server'ı başlat:**
   ```powershell
   npm run dev
   ```
   
3. **Test et:**
   - http://localhost:9002 aç
   - Admin ile giriş: `admin@uniride.com` / `admin`

---

### Seçenek 2: Supabase Kurulumu (30-60 dakika) 🚀

**Avantajlar:**
- ✅ Production-ready
- ✅ Veriler kalıcı
- ✅ Multi-user desteği
- ✅ Authentication dahil
- ✅ Ücretsiz tier yeterli

**Yapılacaklar:**
1. Supabase hesabı oluştur (https://supabase.com)
2. Yeni proje oluştur
3. Database schema oluştur
4. Auth ayarları yap
5. Kodları Supabase'e migrate et

---

## 🚀 Hangisini Seçmeli?

**Şu an için test/geliştirme:** → **Mock Database**
**Production için:** → **Supabase**

**Öneri:** İkisini de hazırlayabilirim! 
- Önce mock database ile hızlı test
- Sonra Supabase'e geçiş yap

---

## Hangi Seçeneği İstiyorsun?

1. **Mock Database** - Hemen çalışır (5 dk)
2. **Supabase** - Production ready (30-60 dk)
3. **İkisini de** - Önce mock, sonra Supabase

Hangi seçeneği tercih edersin? İstediğini hazırlayabilirim! 🎯

