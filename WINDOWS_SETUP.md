# Windows 11 Kurulum Rehberi - UniRide Projesi

## 🪟 Windows 11 için Özel Notlar

Windows 11'de komutlar PowerShell veya CMD'de çalışır. Bu rehber Windows komutlarını içerir.

---

## 📋 Ön Gereksinimler

1. **Node.js Kurulumu:**
   - https://nodejs.org adresinden Node.js LTS sürümünü indir
   - Kurulum sırasında "Add to PATH" seçeneğinin işaretli olduğundan emin ol
   - Kurulumu tamamladıktan sonra PowerShell'i yeniden başlat

2. **Git (Opsiyonel):**
   - https://git-scm.com adresinden Git'i indir
   - Proje klonlamak için gereklidir

3. **VS Code (Önerilen):**
   - https://code.visualstudio.com adresinden VS Code'u indir
   - TypeScript ve React için uzantıları yükle

---

## 🚀 Hızlı Başlangıç (Mock Database)

### PowerShell Komutları (Önerilen)

1. **Proje klasörüne git:**
   ```powershell
   cd "C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide"
   ```

2. **.env.local dosyası oluştur:**
   ```powershell
   Set-Content -Path ".env.local" -Value "NEXT_PUBLIC_USE_MOCK_DB=true"
   ```

   VEYA manuel olarak:
   - VS Code'da `.env.local` dosyası oluştur
   - İçine şunu yaz: `NEXT_PUBLIC_USE_MOCK_DB=true`
   - Kaydet

3. **Paketleri yükle (ilk defa):**
   ```powershell
   npm install
   ```

4. **Development server'ı başlat:**
   ```powershell
   npm run dev
   ```

5. **Tarayıcıda aç:**
   - http://localhost:9002 adresine git
   - Test kullanıcıları ile giriş yap

---

### CMD Komutları (Alternatif)

1. **Proje klasörüne git:**
   ```cmd
   cd /d "C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide"
   ```

2. **.env.local dosyası oluştur:**
   ```cmd
   echo NEXT_PUBLIC_USE_MOCK_DB=true > .env.local
   ```

3. **Paketleri yükle:**
   ```cmd
   npm install
   ```

4. **Server'ı başlat:**
   ```cmd
   npm run dev
   ```

---

## 🔧 Ortak Sorunlar ve Çözümleri

### 1. "npm komut bulunamadı" Hatası

**Sorun:** Node.js PATH'e eklenmemiş.

**Çözüm:**
1. Node.js'i yeniden kur (PATH'e ekle seçeneği ile)
2. PowerShell'i **yönetici olarak** yeniden başlat
3. Şunu kontrol et:
   ```powershell
   node --version
   npm --version
   ```

### 2. ".env.local dosyası oluşturulamıyor"

**Çözüm 1 - VS Code ile:**
1. VS Code'da proje klasörünü aç
2. `.env.local` dosyası oluştur (yeni dosya)
3. İçine yaz: `NEXT_PUBLIC_USE_MOCK_DB=true`
4. Kaydet

**Çözüm 2 - Notepad ile:**
1. Notepad'i aç
2. İçine yaz: `NEXT_PUBLIC_USE_MOCK_DB=true`
3. "Farklı Kaydet" > Dosya adı: `.env.local`
4. "Tüm dosyalar" seç
5. Proje klasörüne kaydet

### 3. "Port 9002 kullanımda" Hatası

**Çözüm:**
```powershell
# Port'u kullanan process'i bul ve kapat
netstat -ano | findstr :9002
# PID'yi not et, sonra:
taskkill /PID [PID_NUMARASI] /F
```

VEYA farklı port kullan:
```powershell
$env:PORT=9003; npm run dev
```

### 4. PowerShell Execution Policy Hatası

**Sorun:** PowerShell script çalıştırma izni yok.

**Çözüm (Yönetici PowerShell):**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 5. "node_modules eksik" Hatası

**Çözüm:**
```powershell
# node_modules klasörünü sil
Remove-Item -Recurse -Force node_modules

# package-lock.json'ı sil (opsiyonel)
Remove-Item package-lock.json

# Yeniden yükle
npm install
```

---

## 📁 Dosya Yolları (Windows)

Windows'ta dosya yolları ters eğik çizgi kullanır:

**Doğru:**
```
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide
```

**Yanlış:**
```
C:/Users/yektakayman/Desktop/AiCode/FirebaseUniRide/UniRide
```

PowerShell'de her ikisi de çalışır, ama CMD'de sadece `\` çalışır.

---

## 🔄 Environment Variables (Windows)

### PowerShell'de:

```powershell
# Geçici olarak ayarla (sadece o session için)
$env:NEXT_PUBLIC_USE_MOCK_DB="true"

# Kalıcı olarak ayarla (kullanıcı için)
[System.Environment]::SetEnvironmentVariable('NEXT_PUBLIC_USE_MOCK_DB', 'true', 'User')
```

### .env.local Dosyası (Önerilen):

`.env.local` dosyası proje klasöründe olsun:
```
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.env.local
```

İçeriği:
```
NEXT_PUBLIC_USE_MOCK_DB=true
```

---

## 🧪 Test Kullanıcıları

Mock database ile test için hazır kullanıcılar:

| Email | Şifre | Rol |
|-------|-------|-----|
| admin@uniride.com | admin | Admin |
| student@uniride.com | studentpassword | Öğrenci |
| driver@uniride.com | driverpassword | Şoför |

---

## 📝 Hızlı Komutlar (Kopyala-Yapıştır)

### Mock Database ile Başla:
```powershell
cd "C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide"
Set-Content -Path ".env.local" -Value "NEXT_PUBLIC_USE_MOCK_DB=true"
npm install
npm run dev
```

### Supabase için .env.local:
```powershell
Set-Content -Path ".env.local" -Value @"
NEXT_PUBLIC_USE_SUPABASE=true
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
"@
```

---

## 🎯 Sonraki Adımlar

1. ✅ Node.js kuruldu mu? → `node --version` kontrol et
2. ✅ Proje klasöründe miyim? → `pwd` veya `cd` kontrol et
3. ✅ .env.local oluşturuldu mu? → Dosya var mı kontrol et
4. ✅ npm install yapıldı mı? → `node_modules` klasörü var mı kontrol et
5. ✅ npm run dev çalışıyor mu? → http://localhost:9002 açılıyor mu kontrol et

---

## 🆘 Yardım

Sorun yaşarsan:
1. PowerShell'i **yönetici olarak** çalıştır
2. Hata mesajını tam olarak kopyala
3. Hata mesajı ile birlikte tekrar dene

---

**Windows 11'de çalışmaya hazır!** 🎉

