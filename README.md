# UniRide

UniRide, üniversite içi öğrenci taşımacılığını optimize etmek için geliştirilmiş bir **CVRPTW (Capacitated Vehicle Routing Problem with Time Windows)** platformudur.
Sistem; yönetici, sürücü ve öğrenci akışlarını tek uygulamada toplar, rota planlamayı Python tabanlı optimizasyon servisine delege eder.

## Öne Çıkanlar

- Next.js 16 tabanlı web uygulaması (admin/driver/student akışları)
- Supabase (PostgreSQL + Auth) entegrasyonu
- FastAPI tabanlı optimizasyon mikroservisi
- **20+ algoritma desteği:**
  - Pipeline A (Cluster-First): GA, PSO, GWO (Grey Wolf), HHO (Harris Hawks)
  - Pipeline B (Split + Optimal Decoder): GA-Split, PSO-Split, GWO-Split, HHO-Split
  - Holistic Solvers: OR-Tools, PyVRP\* (HGS), VROOM\*
  - Heuristics: Two-Opt, Greedy / Nearest Neighbor, Permutation TSP
- **SOTA Framework FAZ 0-3 TAMAMLANDI** 🏆
  - E²BSO: eil51=%0.47, berlin52=%0.00 (OPTIMAL)
  - R²DMA: 6-boyutlu rezonans metriği, eil51=%0.47, berlin52=%0.00 (OPTIMAL)
  - P-AOEA: eil51=**%0.00 OPTIMAL**, berlin52=**%0.00 OPTIMAL**
  - SOTA Infrastructure v3.0.0, DNA Coverage 10/10
- 7 clustering stratejisi: K-Means, Fuzzy C-Means, K-Medoids, Clarke-Wright, Sweep, FCM-Enhanced, Hierarchical-FCM
- Zaman pencereli planlama (pickup/dropoff yönleri)
- Route planları ve sandbox senaryoları için kalıcılık API'leri
- IE (Industrial Engineering) Resource Dashboard
- Akademik benchmark paketi (TSPLib, Numba JIT)
- CLI→Web Import Bridge (`/api/v1/benchmark/cli/import`)

\*PyVRP ve VROOM opsiyonel; `pip install -r requirements-benchmark.txt` ile etkinleştirilebilir.

## Mimari Özeti

1. **Frontend + API Katmanı (Next.js 16)**
   `src/app` altındaki sayfalar ve `src/app/api/*` endpoint'leri istekleri yönetir.
2. **Optimizasyon Katmanı (Python/FastAPI)**
   `optimizer_api/main.py` üzerinden optimize, compare, strategies servisleri sunulur.
3. **Veri Katmanı (Supabase/PostgreSQL)**
   Şema ve migration dosyaları `supabase/` altında yer alır.

## Depo Yapısı

```text
src/                 # Next.js uygulaması (UI, API routes, servisler)
optimizer_api/       # Python optimizasyon motoru
supabase/            # SQL şema, RLS ve migration dosyaları
docs/                # Mimari, yol haritası, changelog ve teknik notlar
academic_benchmark/  # Akademik benchmark araçları (TSPLib + Numba)
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

> Not: Next.js 16 ve @genkit-ai/next arasında peer dependency çakışması olduğu için `--legacy-peer-deps` gereklidir.

### 2) Ortam değişkenleri

Kök dizinde `.env.local` oluşturun:

```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>

# Opsiyonel (default: http://127.0.0.1:8000)
OPTIMIZER_API_URL=http://127.0.0.1:8000
```

### 3) Python optimizasyon servisi

```bash
cd optimizer_api
pip install -r requirements.txt
python main.py
```

Opsiyonel SOTA benchmark bağımlılıkları (PyVRP, VROOM):

```bash
pip install -r requirements-benchmark.txt
```

### 4) Next.js uygulamasını başlatma

```bash
# repo root
npm run dev
```

- Web: `http://localhost:9002`
- Optimizer API: `http://127.0.0.1:8000` (prod: 8099)

## Veritabanı

Supabase tarafında ilgili SQL dosyalarını sırasıyla uygulayın:

- `supabase/schema.sql`
- `supabase/migrations/*`
- `supabase/rls_policies.sql`

## NPM Komutları

| Komut | Açıklama | Durum |
|---|---|---|
| `npm run dev` | Geliştirme sunucusu (Turbopack, port 9002) | ✅ |
| `npm run build` | Production build | ✅ (ağ kısıtlarında font fetch hatası görülebilir) |
| `npm run start` | Production sunucusu | ✅ (`build` sonrası) |
| `npm run typecheck` | TypeScript tip kontrolü | ⚠️ repo'da mevcut baseline hata var |
| `npm run test` | Vitest | ⚠️ test dosyası yoksa başarısız döner |
| `npm run lint` | Next.js lint komutu | ⚠️ mevcut script bu ortamda hataya düşebiliyor |

## Optimizer API Uç Noktaları

| Method | Path | Açıklama |
|---|---|---|
| GET | `/health` | Sağlık kontrolü |
| GET | `/api/v1/strategies` | Kullanılabilir stratejiler |
| POST | `/api/v1/optimize` | Tek algoritmayla rota optimizasyonu |
| POST | `/api/v1/compare` | Tüm algoritmaları karşılaştır |
| POST | `/api/v1/extract-time-windows` | Haftalık programdan zaman penceresi çıkar |
| POST | `/api/v1/schedule-to-students` | Program → öğrenci node listesi |
| POST | `/api/v1/vehicle-calculator` | Araç kapasitesi hesaplama |
| GET | `/api/v1/benchmark/cli/files` | CLI JSON dosyalarını listele |
| POST | `/api/v1/benchmark/cli/import` | CLI → Web format dönüşümü |
| GET | `/api/v1/benchmark/cli/preview` | Import önizlemesi |

## SOTA CLI Araçları

```bash
# FAZ 0-3 interaktif optimizasyon
cd optimizer_api && python faz0_interactive.py

# Standalone demo (web gerekmez)
cd optimizer_api && python faz0_standalone_demo.py

# Belirli problem
cd optimizer_api && python faz0_standalone_demo.py berlin52
```

## Dokümantasyon Haritası

- `docs/01_Implementation_Status.md` → güncel tamamlanma durumu ve eksikler
- `docs/02_Architecture.md` → mimari açıklamalar
- `docs/03_Roadmap.md` → geliştirme yol haritası
- `docs/04_Changelog.md` → sürüm/değişiklik geçmişi
- `docs/05_Code_Quality_Roadmap.md` → kod kalitesi düzeltme yol haritası (09.04.2026)
- `docs/09_04_2026_Codebase_Analysis_Report.md` → kapsamlı kod tabanı analiz raporu
- `docs/ALGORITHM_COMPARISON.md` → algoritma karşılaştırmaları
- `docs/sota_framework_plan_2026/` → SOTA algoritma ve akademik makale vizyonu
- `optimizer_api/README_TESTS.md` → Python test ve benchmark notları

## Bilinen Durum Notları

- `npm run lint` bu sandbox ortamında başarısız olabiliyor (bkz. NPM Komutları tablosu)
- Typecheck'te birkaç baseline hata mevcut (bkz. `docs/01_Implementation_Status.md`)
- `docs/09_04_2026_Codebase_Analysis_Report.md` — tespit edilen sorunlar ve düzeltme planı

## Lisans

Depoda açık bir lisans dosyası bulunmuyor. Kullanım koşulları için depo sahibiyle iletişime geçin.
