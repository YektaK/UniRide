# Ayrı demo sürümü — 6 Ekim 2026

Demo dalı: `codex/demo-safe-fixes`. Başlangıç: `6135319`.
Yolculuk sınırı düzeltmesi `codex/ride-limit-fix`, filo sonucu düzeltmesi `codex/fleet-evidence-fix` dallarında ayrı tutulur. Mevcut `WIP` dalına birleştirme yapılmaz.

## Çalıştırma

İki PowerShell terminali açın. `9003` ve `8001` portları boş olmalı. Bu komutlar mevcut `9002/8000` süreçlerini durdurmaz.

**Terminal 1 — optimizer:**

```powershell
$demoRoot = '<repo>\.temp\worktrees\codex-demo-safe-fixes'
$env:PYTHONPATH = "$demoRoot;$demoRoot\optimizer_api"
$env:OPTIMIZER_PORT = '8001'
$env:OPTIMIZER_HOST = '127.0.0.1'
$env:UNIRIDE_API_RELOAD = '0'
$env:ALLOWED_ORIGINS = 'http://127.0.0.1:9003,http://localhost:9003'
Set-Location -LiteralPath "$demoRoot\optimizer_api"
& '<repo>\.venv-jit\Scripts\python.exe' -B main.py
```

**Terminal 2 — web:**

```powershell
Set-Location -LiteralPath '<repo>\.temp\worktrees\codex-demo-safe-fixes'
$env:OPTIMIZER_API_URL = 'http://127.0.0.1:8001'
$env:NEXT_PUBLIC_OPTIMIZER_API_URL = 'http://127.0.0.1:8001'
node node_modules/next/dist/bin/next dev --webpack --hostname 127.0.0.1 --port 9003
```

Adres: <http://127.0.0.1:9003/admin/daily-plan>. Gerekirse bu portta yönetici hesabıyla yeniden giriş yapın. Durdurmak için iki terminalde de `Ctrl+C` kullanın. Mevcut sürüme dönmek için onun normal çalışma dizinini/başlatma komutunu ve `9002` adresini kullanın; dal değiştirmeniz gerekmez.

Doğrulama sonrası deneme süreçleri kapatıldı; demoyu başlatmak için yukarıdaki komutları çalıştırın. Ayrıntılı değişiklik ve doğrulama kaydı: `docs/DEMO_SAFE_FIXES_RAPORU_2026-10-06.md`.

## Hazırlanan ortam

- `node_modules` mevcut kurulu bağımlılıklara bağlıdır; yeni paket kurulmadı.
- Python yorumlayıcısı mevcut `.venv-jit` ortamından gelir. `PYTHONPATH`, kodun bu demo dizininden yüklenmesini sağlar; bu satırı atlamayın.
- `.env.local` ve `optimizer_api/.env` aday dizinine kopyalandı. Yalnız bu kopyalarda ortak bir iç API anahtarı oluşturuldu; Git'e eklenmedi ve mevcut sürümün ayarları değiştirilmedi.
- Kod ve portlar ayrıdır; **veritabanı aynı Supabase yapılandırmasını kullanır**. Kod dalları veritabanını kopyalamaz. Bu çalışmada canlı veriye yazma işlemi yapılmadı.

## Doğrulama durumu

Birleşik kod commit'i: `f63716d`. `npx.cmd vitest run`: 48 dosya / 552 test geçti. TypeScript kontrolü geçti. Lint: 0 hata / 167 uyarı; uyarı sayısı başlangıç sürümüyle aynı. Değişikliklerin `git diff --check` kontrolü geçti.

Belgedeki port/ortam ayarlarıyla optimizer sağlık kontrolü ve iç API handshake HTTP200, günlük plan sayfası HTTP200, oturumsuz yönetici API kontrolü HTTP401 döndürdü. Yeni web origin'inin CORS izni ve Python kaynaklarının aday dizininden çözülmesi doğrulandı.

Sağlık/handshake ve anonim sayfa açılışı, giriş yapılmış hesapla canlı önizleme veya uçtan uca demo doğrulaması anlamına gelmez. Canlı yönetici hesabıyla önizleme ve üretim build'i bu çalışmada sınanmadı. Geliştirme modu için yukarıdaki komutlar kullanıldı.
