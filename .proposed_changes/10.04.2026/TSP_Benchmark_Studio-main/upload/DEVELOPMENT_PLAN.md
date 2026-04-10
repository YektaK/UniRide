# TSP Benchmark Studio — Detaylı Geliştirme Planı (v2)

> **Durum**: Planlama Modu | **Tarih**: Haziran 2026
> **Son Güncelleme**: Dosya yapıları detaylı incelendikten sonra revize edildi
> **Onay**: ⏳ Kullanıcı onayı bekleniyor

---

## 0. ÖZET: PLANIN KAPSAMI

Bu plan **TSP Benchmark Studio**'nun Next.js frontend'inden Python benchmark CLI'ya kadar tüm geliştirme sürecini kapsar:

1. **CSV Sonuçları Görselleştirme** — Mevcut benchmark sonuçlarını okuma ve grafiklerle sunma
2. **Deney Tasarımcısı** — Algoritma seçimi, problem seçimi, parametre yapılandırması
3. **Algoritma Çalıştırma Entegrasyonu** — Frontend'den Python koduna deney konfigürasyonu gönderme, çalıştırma ve sonuç toplama
4. **İstatistiksel Analiz** — Akademik düzeyde karşılaştırma ve raporlama
5. **Polish & Export** — Profesyonel görünüm, PDF/CSV/LaTeX export

> **Evet, algoritma çalıştırma seçenekleri (algoritma seçimi → parametre yapılandırma → Python'a gönderme → gerçek zamanlı ilerleme → sonuç toplama) bu planın temel bir parçasıdır.** Sprint 4 bu konuyu detaylı olarak ele alır. Ayrıca Sprint 2'deki deney tasarımcısı, Sprint 4'teki çalıştırma entegrasyonunun ön koşuludur.

---

## 1. MEVCUT DURUM ANALİZİ

### 1.1 Benchmark Veritabanı Yapısı

**Konum**: `upload/academic_benchmark/benchmark_db/` (kullanıcı direktifi: kalıcı olarak burada kalacak)

```
upload/academic_benchmark/
├── benchmark_db/
│   ├── latest_metadata.json          ← 17 problem × 5 strateji (cache'lenmiş sonuçlar)
│   └── history/
│       ├── smart_run_20260404_163110.csv          (87 row, 17 problem × 5 algo — EN KAPSAMLI)
│       ├── final_benchmark_20260403_000737.csv    (31 row, 7 problem × 5 algo)
│       ├── final_benchmark_20260403_000737.json    (11 KB)
│       ├── progress_benchmark_20260402_*.csv/json  (4 progress dosyası)
│       └── progress_benchmark_20260403*.csv/json  (1 progress dosyası)
├── run_smart_benchmark_numba.py        ← Ana benchmark runner (NUMBA, PRIMARY)
├── run_smart_benchmark.py              ← Alternatif runner (non-Numba fallback)
├── run_interactive_benchmark_v2_numba.py ← Core engine: STRATEGIES, TSPLIB parser, run_single_test()
├── utils_benchmark.py                  ← Metadata/cache yardımcıları (SHA-256 hash, get/save metadata)
├── dataset_loader.py                   ← TSPLIB loader (.tsp dosyaları), BenchmarkDatasetLoader
├── local_search_numba.py               ← NUMBA JIT local search (CORE — 7 algoritma tipi)
├── base_strategy.py                    ← BaseRoutingStrategy (meta-heuristic abstract class)
├── ga_strategy.py                      ← Genetic Algorithm (pop:50, gen:100, cr:0.85, mr:0.15)
├── pso_strategy.py                     ← PSO (swarm:30, iter:100, w:0.729, c1:1.494, c2:1.494)
├── gwo_strategy.py                     ← GWO (pop:30, iter:100, a:2.0)
├── hho_strategy.py                     ← HHO (pop:30, iter:100, jump:0.5)
├── greedy_heuristic.py                 ← Greedy heuristic
└── zai1_extracted/                     ← Eski arşiv kopyası (kullanılmıyor)
```

**NOT**: Python kaynak dosyaları `upload/` kökünde, `upload/academic_benchmark/` altında DEĞİL. `academic_benchmark/` klasörü SADECE `benchmark_db/` veri klasörünü içeriyor.

### 1.2 CSV Veri Formatı

**Sütunlar**:
```
problem | dimension | category | optimal | strategy | avg_length | avg_gap | best_length | best_gap | avg_time_ms | n_runs [,timestamp]
```

**Örnek Satır**:
```
berlin52,52,small,7542,2-opt,8884.667,17.803,8864,17.529,42.32,3
```

**Önemli Notlar**:
- `strategy` alanı Python'daki isimle birebir aynı: `2-opt`, `3-opt`, `Or-opt`, `Swap`, `Hybrid`
- `category` sınırları: small (n≤152), medium (150<n≤500), large (n>500)
- `final_` dosyalarında `timestamp` sütunu var, `smart_run_` dosyasında YOK
- `avg_gap` hesaplama: `((avg_length - optimal) / optimal) × 100`
- Or-opt anomali: Büyük problemlerde (n>100) GAP %100-600 arası çıkabiliyor (Numba implementasyon bug'ı)

### 1.3 JSON Metadata Formatı (`latest_metadata.json`)

```json
{
  "file_hashes": { "LocalSearchEngine_NUMBA": "<sha256>" },
  "results": {
    "berlin52": {
      "2-opt": { "avg_length": 8884.67, "avg_gap": 17.80, "best_gap": 17.53, "avg_time_ms": 42.32, "timestamp": "..." },
      "3-opt": { ... },
      "Or-opt": { ... },
      "Swap": { ... },
      "Hybrid": { ... }
    }
  },
  "last_updated": "2026-04-04T16:31:10"
}
```

### 1.4 Mevcut Benchmark Sonuçları Özeti

| Kategori | Problem Sayısı | Test Edilen | Algoritma Sayısı |
|----------|---------------|------------|------------------|
| Small (n≤152) | 17 | 17 ✅ | 5 (Local Search) |
| Medium (150-500) | 13 | 0 ❌ | - |
| Large (500+) | 15 | 0 ❌ | - |
| **Toplam** | **45** | **17** | **5** |

### 1.5 ALGORİMA DETAYLARI VE PARAMETRELERİ

#### A. Local Search Algoritmaları (HAZIR — Mevcut CSV Sonuçları Var)

**Python Konumu**: `local_search_numba.py` → `LocalSearchType` enum + JIT compiled sınıflar

| # | Algoritma | Python Tipi | Benchmark Default | Min-Max | Karmaşıklık |
|---|-----------|-------------|-------------------|---------|-------------|
| 1 | **2-opt** | `LocalSearchType.TWO_OPT` | max_iterations=2000 | 100-50000 | O(n²) |
| 2 | **3-opt** | `LocalSearchType.THREE_OPT` | max_iterations=200 | 10-5000 | O(n³) |
| 3 | **Or-opt** | `LocalSearchType.OR_OPT` | max_iterations=1000 | 100-30000 | O(n²) |
| 4 | **Swap** | `LocalSearchType.SWAP` | max_iterations=5000 | 100-100000 | O(n²) |
| 5 | **Hybrid** | `LocalSearchType.HYBRID` | cycles=5 | 1-50 | O(n³) |

**Ek Parametreler** (Python kodunda mevcut, UI'da ileride gösterilebilir):
- `first_improvement: bool` (default: False) — 2-opt, 3-opt, Swap
- `max_segment_size: int` (default: 3) — Or-opt (1-3 arası)
- `use_random_order: bool` (default: False) — Hybrid
- `include_cross_exchange: bool` (default: True) — Hybrid

**Python Fonksiyon İmzası**:
```python
# En temel çalıştırma fonksiyonu:
def run_single_test(
    problem: TSPLIBProblem,     # Problem instance (name, dimension, coordinates, optimal)
    ls_type: LocalSearchType,   # Algorithm enum
    seed: int,                  # Random seed
    max_iterations: int = 500   # Max iterations
) -> Dict:
    # Returns: {"tour_length": float, "gap": float, "time_ms": float}
```

```python
# STRATEGIES tuple (run_interactive_benchmark_v2_numba.py, satır 63):
STRATEGIES = [
    ("2-opt",   LocalSearchType.TWO_OPT,  2000),
    ("3-opt",   LocalSearchType.THREE_OPT, 200),
    ("Or-opt",  LocalSearchType.OR_OPT,   1000),
    ("Swap",    LocalSearchType.SWAP,     5000),
    ("Hybrid",  LocalSearchType.HYBRID,   5),    # 5 cycles (max_iterations burada cycle sayısı)
]
```

#### B. Meta-Heuristic Algoritmaları (PLANLANIYOR — Henüz CSV Sonucu Yok)

**Python Konumu**: `upload/ga_strategy.py`, `pso_strategy.py`, `gwo_strategy.py`, `hho_strategy.py`

| # | Algoritma | Sınıf | Parametreler | Default Değerler |
|---|-----------|------|-------------|------------------|
| 6 | **GA** | `GeneticAlgorithmStrategy` | population_size, max_iterations, crossover_rate, mutation_rate, elite_count, tournament_size, max_no_improvement, seed, local_search_type | 50, 100, 0.85, 0.15, 2, 3, 20, None, "two_opt" |
| 7 | **PSO** | `PSOStrategy` | swarm_size, max_iterations, inertia_weight, cognitive_weight, social_weight, velocity_clamp, max_no_improvement, seed, local_search_type | 30, 100, 0.729, 1.49445, 1.49445, 0.9, 25, None, "hybrid" |
| 8 | **GWO** | `GreyWolfOptimizerStrategy` | population_size, max_iterations, initial_a, exploration_rate, max_no_improvement, seed, local_search_type | 30, 100, 2.0, 0.5, 20, None, "two_opt" |
| 9 | **HHO** | `HarrisHawksOptimizerStrategy` | population_size, max_iterations, initial_energy, jump_probability, max_no_improvement, seed, local_search_type | 30, 100, 1.0, 0.5, 20, None, "hybrid" |

**Ortak Özellikler**:
- Tümü `BaseRoutingStrategy.optimize(OptimizationRequest)` arayüzünü uygular
- Tümü `local_search_type` parametresine sahip: `"none"`, `"two_opt"`, `"hybrid"`
- Tümü `seed` parametresi ile tekrarlanabilir
- Tümü `max_no_improvement` ile erken durma (early stopping) destekler

### 1.6 Mevcut Next.js Proje Durumu

**Aktif TSP Benchmark Studio Kodu** (önceki oturumda oluşturulmuş, MUHAFAZA EDİLECEK):

| Dosya | Satır | İçerik |
|------|------|--------|
| `src/app/page.tsx` | 1512 | Dashboard, Deney Tasarımcısı, Sonuç Tablosu, Algoritma Bilgileri |
| `src/store/benchmark-store.ts` | 687 | 9 algoritma tanımı, 45 problem tanımı, demo data, CSV/JSON yükleme |
| `src/app/layout.tsx` | ~20 | ThemeProvider, Sonner Toaster, Geist font |
| `src/app/globals.css` | 618 | Tailwind v4 theme, glassmorphism, animasyonlar |
| `src/lib/utils.ts` | ~5 | cn() utility |
| `src/hooks/use-mobile.ts` | ~10 | Mobile breakpoint hook |
| `src/components/ui/` | 44 dosya | shadcn/ui bileşenleri |

**Eski Kanban Kodu (SİLİNECEK)**:

| Dosya | Satır | Neden Silinecek |
|------|------|----------------|
| `src/store/task-store.ts` | 1495 | Eski kanban store, hiçbir aktif kod import etmiyor |
| `src/app/api/tasks/route.ts` | ~50 | Kanban task CRUD API |
| `src/app/api/tasks/[id]/route.ts` | ~50 | Tek task API |
| `src/app/api/tasks/[id]/subtasks/route.ts` | ~30 | Subtask API |
| `src/app/api/tasks/[id]/subtasks/[subtaskId]/route.ts` | ~20 | Subtask detay API |
| `src/app/api/tasks/[id]/subtasks/reorder/route.ts` | ~15 | Subtask sıralama API |
| `src/app/api/tasks/[id]/dependencies/route.ts` | ~30 | Task dependency API |
| `src/app/api/tasks/seed/route.ts` | ~150 | Seed veri API |
| `src/app/api/route.ts` | ~5 | Hello world (ölü) |
| `prisma/schema.prisma` | 52 | Task/Subtask/TaskDependency modelleri |
| `db/custom.db` | 44KB | Eski SQLite veritabanı |
| `download/` | 17MB | Eski QA screenshot'ları |

**Eski Kanban Kodundan Çıkarılacak Faydalı Kalıplar** (silmeden önce not alınacak):
- Zustand store yapısı: slice pattern, computed getters
- API route yapıları: Next.js App Router CRUD pattern
- Prisma schema pattern: model tanımlama, ilişkiler

### 1.7 Mevcut Cron Job'lar

✅ **TÜMÜ DURDURULDU** — 8 adet otomatik QA cron job önceki oturumda silindi.

---

## 2. TEMEL MİMARİ KARARLARI

### 2.1 Veri Akışı (Genel Mimari)

```
┌──────────────────────────────────────────────────────────────────────┐
│                        KULLANICI AKIŞI                               │
│                                                                       │
│  ┌─────────────────┐    ┌───────────────────┐    ┌────────────────┐  │
│  │  ALGORİTMA      │    │  PARAMETRE        │    │  PROBLEM       │  │
│  │  SEÇİMİ         │───▶│  YAPILANDIRMASI    │───▶│  SEÇİMİ        │  │
│  │  (UI Kartları)   │    │  (Dinamik Form)   │    │  (Kategori)    │  │
│  └─────────────────┘    └───────────────────┘    └────────────────┘  │
│           │                      │                      │            │
│           └──────────────────────┼──────────────────────┘            │
│                                  ▼                                   │
│                    ┌────────────────────────┐                         │
│                    │  DENEY KONFİGÜRASYONU  │                         │
│                    │  (ExperimentConfig)    │                         │
│                    │  - algorithms[]        │                         │
│                    │  - problems[]          │                         │
│                    │  - params{}            │                         │
│                    │  - n_runs, workers     │                         │
│                    └───────────┬────────────┘                         │
│                                │                                     │
│              ┌─────────────────┼─────────────────┐                   │
│              ▼                 ▼                 ▼                   │
│   ┌─────────────┐   ┌─────────────────┐  ┌──────────────┐           │
│   │ ÇALIŞTIRMA   │   │ SONUÇ OKUMA     │  │ GÖRSELLEŞME   │           │
│   │ (Sprint 4)   │   │ (Sprint 1)      │  │ (Sprint 1-3) │           │
│   │              │   │                 │  │              │           │
│   │ Frontend     │   │ API Route       │  │ Recharts     │           │
│   │ ➜ Next.js    │   │ ➜ CSV dosyası   │  │ Grafikler    │           │
│   │ API ➜ Python │   │ ➜ JSON parse    │  │ Tablolar     │           │
│   │ Mini Service │   │ ➜ Store         │  │ Heatmap      │           │
│   │ ➜ CSV yazma  │   │ ➜ UI update     │  │ Export       │           │
│   └─────────────┘   └─────────────────┘  └──────────────┘           │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Veri Okuma Yaklaşımı

**Karar**: **Dosya tabanlı** yaklaşım.
- Python benchmark arka planda çalışır, CSV'ye incremental kaydeder
- Next.js API route CSV dosyasını okur, parse eder
- Uzun süren deneyler için timeout sorunu yok
- Sonuçlar CSV dosyasında kalıcı olarak saklanır

### 2.3 Benchmark DB Konumu

**Karar**: `upload/academic_benchmark/benchmark_db/` kalıcı konum.
- Kullanıcı direktifi: "benchmark_db bu şekilde academic_benchmark klasörünün altında olacak"
- Mevcut CSV dosyaları bu konumda zaten mevcut
- Next.js API route bu klasörü okuyacak
- Python mini service yeni CSV dosyalarını bu klasöre yazacak

### 2.4 Prisma Kullanımı

**Karar**: Eski Task/Subtask modelleri **silinecek**. TSP Benchmark Studio öncelikli olarak CSV dosyalarından çalışacak. İleride deney konfigürasyonu saklamak için yeni Prisma modeli eklenebilir (Sprint 6+).

### 2.5 Algoritma Çalıştırma Akışı (Sprint 4 Detayı)

```
KULLANICI                          FRONTEND (Next.js)              BACKEND (Python)
─────────                          ─────────────────              ────────────────
1. Algoritma seç       ──▶    ExperimentConfig oluşturulur
2. Problem seç                  (algorithms, problems,
3. Parametre ayarla             params, n_runs, workers)
4. "ÇALIŞTIR" butonu    ──▶    
                              ┌─────────────────────────────┐
                              │  POST /api/benchmark/run     │
                              │  Body: ExperimentConfig      │
                              └──────────┬──────────────────┘
                                         │
                                         ▼ HTTP POST (XTransformPort=3003)
                              ┌─────────────────────────────┐
                              │  Mini Service (port 3003)    │
                              │  benchmark_runner/           │
                              │                              │
                              │  1. Config'ı al              │
                              │  2. Multiprocessing Pool     │
                              │  3. Her worker:              │
                              │     - Problemi yükle         │
                              │     - Algoritmayı çalıştır   │
                              │     - Sonucu CSV'ye yaz      │
                              │  4. WebSocket: ilerleme      │
                              │  5. Tamamlandığında:         │
                              │     final CSV dosyası        │
                              └──────────┬──────────────────┘
                                         │
              ┌──────────────────────────┤
              │ WebSocket (ilerleme)      │
              ▼                          ▼
       İlerleme çubuğu           Tamamlanan sonuçlar
       (% XX, problem X/algo Y)  anında UI'a eklenir
                                         │
                                         ▼ (CSV yazıldıktan sonra)
                              ┌─────────────────────────────┐
                              │  GET /api/benchmark/results │
                              │  ?file=latest                │
                              └─────────────────────────────┘
                                         │
                                         ▼
                               Tüm sonuçları göster
```

---

## 3. SPRINT PLANLAMASI

### SPRINT 0: Temizlik ve Hazırlık [~30 dk]

**Hedef**: Eski kodu temizle, temeli güçlendir, geliştirmeye hazır hale getir.

| # | Görev | Detay | Öncelik |
|---|-------|------|--------|
| 0.1 | Eski kanban kodunu sil | `task-store.ts`, `api/tasks/**`, `api/route.ts` (hello world) | 🔴 Yüksek |
| 0.2 | Eski veritabanını sil | `db/custom.db` sil | 🔴 Yüksek |
| 0.3 | Prisma schema'yı temizle | Task/Subtask/TaskDependency modellerini kaldır | 🔴 Yüksek |
| 0.4 | Eski screenshot'ları sil | `download/` klasörünü sil (17MB gereksiz) | 🟡 Orta |
| 0.5 | globals.css temizliği | Duplicate tanımları sil (.dot-pattern, .pulse-ring 2 kez tanımlı) | 🟡 Orta |
| 0.6 | Layout metadata güncelle | Title/description "TSP Benchmark Studio" olarak güncelle | 🟡 Orta |
| 0.7 | tailwind.config.ts inceleme | Tailwind v4 ile uyumlu mu kontrol et, gereksizse sil | 🟢 Düşük |

**Sprint 0 Çıktısı**: Temiz proje, lint hatası yok, geliştirmeye hazır.

---

### SPRINT 1: CSV Sonuçları Sunumu — Vizyon [~2-3 saat]

**Hedef**: Mevcut benchmark CSV sonuçlarını okuyan, parse eden ve görselleştiren tam fonksiyonel sayfa.

| # | Görev | Detay | Öncelik |
|---|-------|------|--------|
| 1.1 | API Route: CSV listeleme | `GET /api/benchmark/csv-files` — `benchmark_db/history/` içindeki CSV dosyalarını listele (name, size, date, row_count) | 🔴 Yüksek |
| 1.2 | API Route: CSV parse | `GET /api/benchmark/results?file=X` — CSV oku, parse et, JSON olarak döndür | 🔴 Yüksek |
| 1.3 | API Route: Metadata | `GET /api/benchmark/metadata` — `latest_metadata.json` oku | 🔴 Yüksek |
| 1.4 | API Route: Problem info | `GET /api/benchmark/problems` — Tüm TSPLIB problem bilgileri (hardcoded) | 🟡 Orta |
| 1.5 | Store: loadFromServer() | Zustand store'a server-side CSV yükleme metodu ekle | 🔴 Yüksek |
| 1.6 | UI: Otomatik CSV yükleme | Sayfa açılışında en kapsamlı CSV'yi otomatik yükle | 🔴 Yüksek |
| 1.7 | UI: Veri Kaynağı Seçici | Dropdown ile CSV dosyaları arasından seçim | 🔴 Yüksek |
| 1.8 | UI: Dashboard — Real data | Demo data kaldır, real CSV verisi ile dashboard'u doldur | 🔴 Yüksek |
| 1.9 | UI: Sonuç Tablosu | Sıralama, filtreleme, pagination | 🟡 Orta |
| 1.10 | UI: GAP karşılaştırma bar chart | Problem bazlı GAP karşılaştırması (Recharts GroupedBarChart) | 🔴 Yüksek |
| 1.11 | UI: Süre karşılaştırma chart | Algoritma bazlı ortalama süre grafiği | 🟡 Orta |
| 1.12 | UI: Scatter Plot | X=dimension, Y=GAP, renk=algorithm | 🟡 Orta |
| 1.13 | UI: GAP Heatmap | Problem × Algorithm matrisinde renk kodlu GAP | 🟢 Düşük |

**Sprint 1 Çıktısı**: 17 problem × 5 algoritma = 85 deney sonucunu CSV'den okuyup grafiklerle görselleştirme.

---

### SPRINT 2: Deney Tasarımcısı Geliştirme [~2-3 saat]

**Hedef**: Kullanıcının algoritma seçimi, problem seçimi, parametre yapılandırması yapmasını sağlayan tam fonksiyonel arayüz.

> **NOT**: Bu sprint, Sprint 4'teki algoritma çalıştırma entegrasyonunun **ön koşuludur**. Sprint 2'de oluşturulan ExperimentConfig, doğrudan Python koduna gönderilecektir.

| # | Görev | Detay | Öncelik |
|---|-------|------|--------|
| 2.1 | Algoritma seçim kartları | 9 algoritma kartı (5 ready, 4 planned), renk kodlu, toggle seçim | 🔴 Yüksek |
| 2.2 | **Dinamik parametre formu** | Seçilen algoritma için otomatik parametre alanları oluşturma | 🔴 Yüksek |
| 2.3 | Local Search parametreleri | max_iterations/cycles slider + number input, doğrulama | 🔴 Yüksek |
| 2.4 | Meta-Heuristic parametreleri | pop_size, max_gen, crossover_rate vb. — her algoritma için özelleştirilmiş | 🔴 Yüksek |
| 2.5 | Local Search Type seçimi | Meta-heuristic algoritmalar için post-refinement seçimi (none/2-opt/hybrid) | 🔴 Yüksek |
| 2.6 | Problem seçimi | Kategori filtresi (small/medium/large), toplu seçim, arama | 🔴 Yüksek |
| 2.7 | Genel ayarlar formu | n_runs (1-100), workers (1-8), seed, skip_cached toggle | 🔴 Yüksek |
| 2.8 | Deney matrisi özeti | Toplam deney sayısı = algos × problems × n_runs, tahmini süre | 🟡 Orta |
| 2.9 | Coverage matrix | Hangi problem-algoritma kombinasyonu zaten test edilmiş göster | 🟡 Orta |
| 2.10 | Konfigürasyon export/import | JSON formatında kaydet/geri yükle (localStorage + dosya) | 🟢 Düşük |
| 2.11 | Parametre preset'leri | "Hızlı", "Standart", "Detaylı" gibi hazır parametre setleri | 🟢 Düşük |

**ExperimentConfig Çıktı Formatı** (Sprint 4'te Python'a gönderilecek):
```typescript
{
  "algorithms": [
    { "id": "two_opt", "params": { "max_iterations": 2000 } },
    { "id": "ga", "params": { "population_size": 50, "max_iterations": 100, "crossover_rate": 0.85, ... } }
  ],
  "problems": ["berlin52", "eil51", "kroA100", ...],
  "settings": { "n_runs": 3, "workers": 4, "seed": 42, "skip_cached": true }
}
```

**Sprint 2 Çıktısı**: Kullanıcı deney tasarlayabilecek, parametreleri yapılandırabilecek. Bu konfigürasyon Sprint 4'te Python'a gönderilecek.

---

### SPRINT 3: İstatistiksel Analiz ve Karşılaştırma [~2-3 saat]

**Hedef**: Algoritmalar arası istatistiksel karşılaştırma ve akademik düzeyde analiz.

| # | Görev | Detay | Öncelik |
|---|-------|------|--------|
| 3.1 | Algoritma performans tablosu | Ort. GAP, Min GAP, Max GAP, Std GAP, Ort. Süre — tablo formatında | 🔴 Yüksek |
| 3.2 | Problem bazlı en iyi algoritma | Her problem için en düşük GAP'li algoritma vurgula | 🔴 Yüksek |
| 3.3 | Ranking tablosu | Algoritmaları ortalama GAP'e göre 1., 2., 3. sırala | 🔴 Yüksek |
| 3.4 | Box plot | Algoritma bazlı GAP dağılımı (problem üzerinden) | 🟡 Orta |
| 3.5 | Pareto front | Kalite (GAP) vs Süre trade-off grafiği | 🟡 Orta |
| 3.6 | Detaylı problem görünümü | Tek problem seçildiğinde tüm algoritmaların karşılaştırmalı sonuçları | 🟡 Orta |
| 3.7 | Kategori bazlı analiz | Small/Medium/Large karşılaştırması | 🟢 Düşük |
| 3.8 | Convergence indicator | (Hazırlık) İleride iterasyon bazlı convergence curve için altyapı | 🟢 Düşük |

**Sprint 3 Çıktısı**: Akademik makaleye uygun profesyonel istatistiksel analiz araçları.

---

### SPRINT 4: ALGORİTMA ÇALIŞTIRMA ENTEGRASYONU [~3-4 saat]

**Hedef**: Frontend'den algoritma seçeneklerini yapılandırma, Python koduna gönderme, gerçek zamanlı ilerleme takibi ve sonuç toplama.

> **Bu sprint, kullanıcının sorduğu "algoritma çalıştırma seçeneklerini seçeceğiz, python koduna göndereceğiz" işlevinin tamamını kapsar.**

#### 4.1 Mini Service: Python Benchmark Runner (port 3003)

```
mini-services/benchmark-runner/
├── index.ts              ← HTTP + WebSocket sunucusu (Bun)
├── package.json          ← Bağımsız bağımlılıklar
└── runner.py             ← (Opsiyonel) Python subprocess wrapper
```

**Mini Service API**:
```
POST /run                 ← Deney başlat (body: ExperimentConfig)
GET /status               ← Çalışan deney durumu
POST /stop                ← Deneyi durdur
WebSocket /               ← Gerçek zamanlı ilerleme
```

**WebSocket Mesaj Formatı**:
```json
// Server → Client: İlerleme
{
  "type": "progress",
  "data": {
    "completed": 15,
    "total": 85,
    "percentage": 17.6,
    "current": { "problem": "berlin52", "algorithm": "2-opt", "run": 2 },
    "elapsed_ms": 5432,
    "eta_ms": 25000
  }
}

// Server → Client: Tek deney sonucu (incremental)
{
  "type": "result",
  "data": {
    "problem": "berlin52",
    "algorithm": "2-opt",
    "avg_gap": 3.21,
    "best_gap": 2.45,
    "avg_time_ms": 42.3,
    "avg_length": 7821,
    "n_runs": 3
  }
}

// Server → Client: Tamamlandı
{
  "type": "complete",
  "data": {
    "csv_file": "smart_run_20260615_143000.csv",
    "total_results": 85,
    "total_time_ms": 125000
  }
}

// Server → Client: Hata
{
  "type": "error",
  "data": { "message": "NUMBA compilation failed", "code": "COMPILE_ERROR" }
}
```

#### 4.2 Next.js API Routes

```
POST /api/benchmark/run          ← Konfigürasyonu al, mini service'e ileti
GET  /api/benchmark/run/status   ← Çalışan deney durumu
POST /api/benchmark/run/stop     ← Deneyi durdur
```

**API Akışı**:
1. Frontend `POST /api/benchmark/run` gönderir (ExperimentConfig ile)
2. Next.js API route konfigürasyonu doğrular
3. Mini service'e `POST http://localhost:3003/run` gönderir (XTransformPort=3003)
4. Mini service benchmark çalıştırır, CSV yazar
5. WebSocket ile ilerleme bildirir
6. Frontend anında güncellenir

#### 4.3 Deney Çalıştırma UI Bileşenleri

| # | Görev | Detay | Öncelik |
|---|-------|------|--------|
| 4.1 | Mini service oluşturma | HTTP + WebSocket sunucusu (Bun, port 3003) | 🔴 Yüksek |
| 4.2 | API Route: run | `POST /api/benchmark/run` — Konfigürasyon doğrulama ve iletme | 🔴 Yüksek |
| 4.3 | API Route: status | `GET /api/benchmark/run/status` — Çalışan deney durumu | 🔴 Yüksek |
| 4.4 | API Route: stop | `POST /api/benchmark/run/stop` — Güvenli durdurma | 🟡 Orta |
| 4.5 | UI: Çalıştırma paneli | Deney tasarımcısında "▶ Çalıştır" butonu + onay dialog | 🔴 Yüksek |
| 4.6 | UI: İlerleme çubuğu | Animated progress bar, % completed, ETA, current problem/algo | 🔴 Yüksek |
| 4.7 | UI: Canlı sonuç akışı | Tamamlanan deneyler anında tabloya eklenir (WebSocket) | 🔴 Yüksek |
| 4.8 | UI: Log paneli | Gerçek zamanlı log mesajları (scrollable, auto-scroll) | 🟡 Orta |
| 4.9 | UI: Durdurma butonu | Çalışan deneyi güvenli şekilde durdurma (Ctrl+C equiv.) | 🟡 Orta |
| 4.10 | Cache mekanizması | skip_cached: aynı config ile tekrar çalıştırma | 🟡 Orta |
| 4.11 | Hata yönetimi | NUMBA compile error, timeout, memory error, graceful handling | 🟡 Orta |
| 4.12 | Sonuç refresh | Deney tamamlandığında otomatik CSV yeniden yükleme | 🔴 Yüksek |

**Sprint 4 Çıktısı**: Kullanıcı frontend'den algoritma seçeneklerini seçer, parametreleri ayarlar, "Çalıştır" basar ve gerçek zamanlı sonuçları izler.

---

### SPRINT 5: Gelişmiş Özellikler ve Polish [~2-3 saat]

**Hedef**: Profesyonel görünümlü, detaylı raporlama ve export.

| # | Görev | Detay | Öncelik |
|---|-------|------|--------|
| 5.1 | CSV export | Filtrelenmiş sonuçları CSV olarak indirme | 🔴 Yüksek |
| 5.2 | PDF export | Tablo ve grafikleri PDF olarak dışa aktarma | 🟡 Orta |
| 5.3 | LaTeX export | Akademik tablo formatında LaTeX çıktı | 🟢 Düşük |
| 5.4 | Dark/Light tema iyileştirmeleri | Tüm yeni bileşenler her iki temada çalışmalı | 🟡 Orta |
| 5.5 | Responsive tasarım | Mobil uyumluluk kontrolü ve iyileştirme | 🟡 Orta |
| 5.6 | Print-friendly görünüm | Yazdırma için optimize görünüm | 🟢 Düşük |
| 5.7 | Keyboard shortcuts | Hızlı erişim tuşları | 🟢 Düşük |
| 5.8 | Animasyon ve mikro etkileşimler | Hover, click, transition iyileştirmeleri | 🟢 Düşük |

**Sprint 5 Çıktısı**: Üretim seviyesinde profesyonel arayüz.

---

## 4. ÖNCELİK SIRASI VE ZAMAN TAHMİNİ

| Sprint | Süre | Kümülatif | Öncelik | Durum |
|--------|------|-----------|--------|-------|
| **Sprint 0**: Temizlik | ~30 dk | ~30 dk | ⚠️ ZORUNLU | Bekliyor |
| **Sprint 1**: CSV Vizyon | ~2-3 saat | ~3 saat | 🔴 EN YÜKSEK | Bekliyor |
| **Sprint 2**: Deney Tasarımcısı | ~2-3 saat | ~6 saat | 🔴 YÜKSEK | Bekliyor |
| **Sprint 3**: İstatistiksel Analiz | ~2-3 saat | ~9 saat | 🟡 ORTA | Bekliyor |
| **Sprint 4**: Algoritma Çalıştırma | ~3-4 saat | ~13 saat | 🔴 YÜKSEK | Bekliyor |
| **Sprint 5**: Polish | ~2-3 saat | ~16 saat | 🟢 DÜŞÜK | Bekliyor |

**MVP**: Sprint 0 + Sprint 1 (~3.5 saat) — Mevcut CSV sonuçlarını görselleştiren çalışan sayfa
**Full Product**: Sprint 0-5 (~16 saat) — Deney tasarlayıp çalıştırabilecek tam platform

---

## 5. TEKNİK DETAYLAR

### 5.1 API Route Tasarımı

```
── VERİ OKUMA (Sprint 1) ──
GET  /api/benchmark/csv-files           — CSV dosya listesi (name, size, date, rows)
GET  /api/benchmark/results?file=X      — CSV parse + JSON sonuçlar
GET  /api/benchmark/metadata            — latest_metadata.json
GET  /api/benchmark/problems            — Tüm TSPLIB problemleri
GET  /api/benchmark/algorithms          — Algoritma bilgileri + parametreler

── DENEY ÇALIŞTIRMA (Sprint 4) ──
POST /api/benchmark/run                 — Deney başlat (body: ExperimentConfig)
GET  /api/benchmark/run/status          — Çalışan deney durumu
POST /api/benchmark/run/stop            — Deneyi güvenli durdur
WS   /?XTransformPort=3003              — Gerçek zamanlı ilerleme (socket.io)
```

### 5.2 Python → Frontend Parametre Eşleştirmesi

| Frontend Param Key | Python Karşılığı | Algoritma |
|--------------------|-----------------|-----------|
| `max_iterations` | `max_iterations` | 2-opt, 3-opt, Or-opt, Swap |
| `cycles` | `max_iterations` (cycle sayısı) | Hybrid |
| `population_size` | `population_size` | GA, GWO, HHO |
| `swarm_size` | `swarm_size` | PSO |
| `max_iterations` / `max_generations` | `max_iterations` | GA, PSO, GWO, HHO |
| `crossover_rate` | `crossover_rate` | GA |
| `mutation_rate` | `mutation_rate` | GA |
| `elite_count` | `elite_count` | GA |
| `tournament_size` | `tournament_size` | GA |
| `inertia_weight` | `inertia_weight` | PSO |
| `cognitive_weight` | `cognitive_weight` | PSO |
| `social_weight` | `social_weight` | PSO |
| `velocity_clamp` | `velocity_clamp` | PSO |
| `initial_a` | `initial_a` | GWO |
| `exploration_rate` | `exploration_rate` | GWO |
| `jump_probability` | `jump_probability` | HHO |
| `local_search_type` | `local_search_type` | GA, PSO, GWO, HHO |
| `seed` | `seed` | Tümü |
| `n_runs` | `N_RUNS` | Genel |

### 5.3 Store Mimarisi

```
Zustand Store (benchmark-store.ts) — MEVCUT + EKLENECEKLER:
├── State (MEVCUT)
│   ├── results: BenchmarkResult[]
│   ├── dataMode: 'demo' | 'loaded'
│   ├── activeView: ActiveView
│   ├── dashboardFilter / dashboardAlgorithmFilter / dashboardSearch
│   ├── sortField / sortDir / resultsPerPage / resultsPage
│   └── experiment: ExperimentConfig
│
├── State (EKLENECEK — Sprint 1)
│   ├── availableCSVFiles: FileInfo[]
│   ├── selectedCSVFile: string | null
│   └── metadata: MetadataJson | null
│
├── State (EKLENECEK — Sprint 4)
│   ├── isRunning: boolean
│   ├── runProgress: { completed, total, percentage, current, elapsed, eta }
│   ├── runResults: BenchmarkResult[]  // incremental results
│   └── runError: string | null
│
├── Actions (EKLENECEK — Sprint 1)
│   ├── fetchCSVFiles()                    // API'den dosya listesi çek
│   ├── loadFromServer(fileName: string)   // API'den CSV çek + parse
│   └── loadMetadata()                     // API'den metadata çek
│
├── Actions (EKLENECEK — Sprint 4)
│   ├── startExperiment(config)            // Deney başlat
│   ├── stopExperiment()                   // Deneyi durdur
│   ├── subscribeToProgress()              // WebSocket dinle
│   └── refreshResults()                   // CSV'yi yeniden yükle
│
└── Computed (MEVCUT — çalışıyor)
    ├── getFilteredResults()
    ├── getStats()
    ├── getAlgorithmSummary()
    ├── getProblemSummary()
    └── getExperimentMatrixCount()
```

### 5.4 Bileşen Mimarisi

```
src/
├── app/
│   ├── page.tsx                    ← Ana sayfa (TSP Benchmark Studio)
│   ├── layout.tsx                  ← Layout wrapper (GÜNCELLENECEK)
│   ├── globals.css                 ← Global stiller (TEMİZLENECEK)
│   └── api/
│       └── benchmark/
│           ├── csv-files/route.ts          ← CSV dosya listesi
│           ├── results/route.ts            ← CSV parse + sonuçlar
│           ├── metadata/route.ts           ← Metadata okuma
│           ├── problems/route.ts           ← Problem bilgileri
│           ├── algorithms/route.ts         ← Algoritma bilgileri
│           ├── run/route.ts                ← Deney başlat (Sprint 4)
│           ├── run/status/route.ts         ← Deney durumu (Sprint 4)
│           └── run/stop/route.ts           ← Deney durdur (Sprint 4)
├── store/
│   └── benchmark-store.ts          ← Ana Zustand store (GÜNCELLENECEK)
├── components/
│   └── benchmark/                  ← Sprint 1+ ile oluşturulacak
│       ├── DashboardView.tsx
│       ├── StatsCards.tsx
│       ├── GapComparisonChart.tsx
│       ├── TimeComparisonChart.tsx
│       ├── ScatterPlot.tsx
│       ├── GapHeatmap.tsx
│       ├── ProblemCoverageTable.tsx
│       ├── ResultsTableView.tsx
│       ├── ExperimentDesignerView.tsx
│       ├── AlgorithmSelector.tsx
│       ├── AlgorithmParamForm.tsx       ← DİNAMİK PARAMETRE FORMU
│       ├── ProblemSelector.tsx
│       ├── GeneralSettings.tsx
│       ├── RunControlPanel.tsx          ← SPRINT 4: Çalıştır/Durdur
│       ├── RunProgressBar.tsx           ← SPRINT 4: İlerleme
│       ├── LiveLogPanel.tsx             ← SPRINT 4: Log paneli
│       └── AlgorithmInfoPanel.tsx
└── ui/                               ← shadcn/ui (44 component — mevcut)
```

### 5.5 Renk Paleti

| Algoritma | Renk | Hex |
|-----------|------|-----|
| 2-opt | Emerald | `#10b981` |
| 3-opt | Amber | `#f59e0b` |
| Or-opt | Indigo | `#6366f1` |
| Swap | Red | `#ef4444` |
| Hybrid | Violet | `#8b5cf6` |
| GA | Cyan | `#06b6d4` |
| PSO | Orange | `#f97316` |
| GWO | Teal | `#14b8a6` |
| HHO | Pink | `#ec4899` |

### 5.6 GAP Renk Kodlaması

| GAP Aralığı | Renk | Anlam |
|-------------|------|------|
| < 2% | Emerald | Mükemmel |
| 2-5% | Amber | İyi |
| 5-10% | Slate | Kabul edilebilir |
| > 10% | Rose | Zayıf |

---

## 6. RİSKLER VE UYUMLAR

### 6.1 Teknik Riskler

| Risk | Etki | Azaltma |
|------|------|---------|
| Benchmark DB yolu sabit olmalı | Yüksek | Environment variable ile yapılandırma |
| Büyük CSV dosyaları (1000+ satır) | Orta | Streaming parse, pagination |
| Python mini service crash | Orta | Auto-restart, health check |
| NUMBA ilk derleme süresi uzun (~30s) | Düşük | "Compiling NUMBA..." splash screen |
| Python bağımlılıkları eksik | Orta | requirements.txt kontrol, error mesajı |
| WebSocket bağlantı kopması | Düşük | Auto-reconnect, polling fallback |

### 6.2 Uyumluluk Notları

| Konu | Detay |
|------|-------|
| **benchmark_db yolu** | `upload/academic_benchmark/benchmark_db/` (sabit) |
| **CSV encoding** | UTF-8, BOM desteklemeli |
| **Problem adları** | CSV'de lowercase (`berlin52`), Python kodunda da lowercase |
| **Kategori sınırları** | Small: n≤152, Medium: 150<n≤500, Large: n>500 |
| **Or-opt anomali** | Büyük problemlerde %100-600+ GAP (Numba bug'ı, bilinen sorun) |
| **Strategy ad eşleşmesi** | Python: `2-opt` ↔ Frontend store: `two_opt` (id) / `2-opt` (shortName) |
| **Hybrid max_iterations** | Python'da "cycle sayısı" (5), diğerlerinde "iterasyon sayısı" |

### 6.3 Bağımlılık Zinciri

```
Sprint 0 ──▶ Sprint 1 ──▶ Sprint 2 ──▶ Sprint 3 ──▶ Sprint 4 ──▶ Sprint 5
 (Temizlik)    (CSV)       (Tasarım)    (Analiz)     (Çalıştırma)   (Polish)
                  │             │
                  │             └──▶ Sprint 4'ün ön koşulu
                  │                  (ExperimentConfig üretir)
                  └──▶ Sprint 2-4'ün veri kaynağı
                       (CSV okuma API'leri)
```

---

## 7. ÖNERİLEN SONRAKİ İLERLEME (Sprint 6+)

- SA (Simulated Annealing) algoritması
- TS (Tabu Search) algoritması
- Hybrid kombinasyonlar (GA+2opt, PSO+Hybrid)
- Convergence curve (iterasyon bazlı iyileşme grafiği)
- Akademik rapor otomatik üretimi
- Çoklu CSV karşılaştırma (fark analizi)
- Database-based sonuç saklama (Prisma ile)
- Çoklu kullanıcılı destek

---

*Bu plan, `upload/academic_benchmark/` altındaki tüm dosya yapıları detaylı incelenerek ve mevcut Next.js projesi analiz edilerek hazırlandıdır.*
*Onay sonrası Sprint 0 ile başlanacaktır.*
