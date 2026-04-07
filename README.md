# UniRide

UniRide, üniversite içi öğrenci taşımacılığını optimize etmek için geliştirilmiş bir **CVRPTW (Capacitated Vehicle Routing Problem with Time Windows)** platformudur.  
Sistem; yönetici, sürücü ve öğrenci akışlarını tek uygulamada toplar, rota planlamayı Python tabanlı optimizasyon servisine delege eder.

## Öne Çıkanlar

- Next.js tabanlı web uygulaması (admin/driver/student akışları)
- Supabase (PostgreSQL + Auth) entegrasyonu
- FastAPI tabanlı optimizasyon mikroservisi
- Çoklu algoritma desteği (GA, PSO, GWO, HHO, Greedy, Two-Opt, OR-Tools, split stratejileri)
- Zaman pencereli planlama (pickup/dropoff yönleri)
- Route planları ve sandbox senaryoları için kalıcılık API’leri

## Mimari Özeti

1. **Frontend + API Katmanı (Next.js)**  
   `src/app` altındaki sayfalar ve `src/app/api/*` endpoint’leri istekleri yönetir.
2. **Optimizasyon Katmanı (Python/FastAPI)**  
   `optimizer_api/main.py` üzerinden `/api/v1/optimize`, `/api/v1/compare`, `/api/v1/strategies` servisleri sunulur.
3. **Veri Katmanı (Supabase/PostgreSQL)**  
   Şema ve migration dosyaları `supabase/` altında yer alır.

## Depo Yapısı

```text
src/                 # Next.js uygulaması (UI, API routes, servisler)
optimizer_api/       # Python optimizasyon motoru
supabase/            # SQL şema, RLS ve migration dosyaları
docs/                # Mimari, yol haritası, changelog ve teknik notlar
academic_benchmark/  # Akademik benchmark araçları
```

## Gereksinimler

- Node.js 18+ (öneri: 20+)
- npm
- Python 3.9+
- Supabase projesi (uygulamayı gerçek veriyle çalıştırmak için)

## Kurulum

### 1) Frontend bağımlılıkları

```bash
npm install --legacy-peer-deps
```

> Not: Mevcut bağımlılık ağacında peer dependency çakışması olduğu için `--legacy-peer-deps` gerekebilir.

### 2) Ortam değişkenleri

Kök dizinde `.env.local` oluşturun:

```bash
NEXT_PUBLIC_SUPABASE_URL=https://<your-project-id>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>

# Opsiyonel (default: http://127.0.0.1:8000)
OPTIMIZER_API_URL=http://127.0.0.1:8000
# veya
NEXT_PUBLIC_OPTIMIZER_API_URL=http://127.0.0.1:8000
```

### 3) Python optimizasyon servisi

```bash
cd optimizer_api
pip install -r requirements.txt
python main.py
```

Opsiyonel benchmark bağımlılıkları:

```bash
pip install -r requirements-benchmark.txt
```

### 4) Next.js uygulamasını başlatma

```bash
# repo root
npm run dev
```

- Web: `http://localhost:9002`
- Optimizer API: `http://127.0.0.1:8000`

## Veritabanı

Supabase tarafında ilgili SQL dosyalarını sırasıyla uygulayın:

- `supabase/schema.sql`
- `supabase/migrations/*`
- `supabase/rls_policies.sql`

## NPM Komutları

| Komut | Açıklama |
|---|---|
| `npm run dev` | Geliştirme sunucusu (Turbopack, port 9002) |
| `npm run build` | Production build |
| `npm run start` | Production sunucusu |
| `npm run typecheck` | TypeScript tip kontrolü |
| `npm run test` | Vitest (⚠️ test dosyası yoksa başarısız döner) |
| `npm run lint` | Next.js lint komutu (⚠️ mevcut script bu ortamda hataya düşebiliyor) |

## Optimizer API Uç Noktaları

- `GET /health`
- `GET /api/v1/strategies`
- `POST /api/v1/optimize`
- `POST /api/v1/compare`
- `POST /api/v1/extract-time-windows`

## Dokümantasyon Haritası

- `docs/01_Implementation_Status.md` → güncel durum ve eksikler
- `docs/02_Architecture.md` → mimari açıklamalar
- `docs/03_Roadmap.md` → yol haritası
- `docs/04_Changelog.md` → sürüm/değişiklik geçmişi
- `docs/ALGORITHM_COMPARISON.md` → algoritma karşılaştırmaları
- `optimizer_api/README_TESTS.md` → Python test ve benchmark notları

## Bilinen Durum Notları

- `npm run lint` mevcut script yapısıyla bu ortamda hataya düşebilir (`next lint` çağrısı).
- `npm run test` komutu, test dosyası bulunmadığında başarısız döner.

## Lisans

Depoda açık bir lisans dosyası bulunmuyor. Kullanım koşulları için depo sahibiyle iletişime geçin.
