# TSP Benchmark Studio → UniRide Migration Guide

> **Durum**: Sprint 0 temizliği tamamlandı — taşımaya hazır  
> **Hedef konum**: `UniRide/proposed_changes/TSP_Benchmark_Studio/`  
> **Kaynak repo**: https://github.com/YektaK/TSP_Benchmark_Studio

---

## 1. Hızlı Başlangıç (UniRide reposunda)

```bash
# UniRide reposunun kökünden çalıştır:
curl -fsSL https://raw.githubusercontent.com/YektaK/TSP_Benchmark_Studio/main/scripts/migrate-to-uniride.sh | bash
```

Bu script:
- `proposed_changes/TSP_Benchmark_Studio/` klasörünü oluşturur
- TSP Benchmark Studio'nun tüm temizlenmiş dosyalarını indirir
- Gereksiz dosyaları (agent-ctx/, worklog.md, bun.lock) kaldırır

---

## 2. Taşınan Dosya Yapısı

```
UniRide/
└── proposed_changes/
    └── TSP_Benchmark_Studio/        ← Bu klasör
        ├── MIGRATION_TO_UNIRIDE.md  ← Bu dosya (okumaya devam et)
        ├── src/                     ← Next.js frontend (benchmark UI)
        │   ├── app/
        │   │   ├── page.tsx         ← Ana benchmark sayfası (3742 satır)
        │   │   ├── layout.tsx       ← ThemeProvider, Toaster
        │   │   ├── globals.css      ← Glassmorphism animasyonlar (548 satır)
        │   │   └── api/benchmark/   ← WebSocket + HTTP API routes
        │   ├── components/ui/       ← 44 shadcn/ui bileşeni
        │   ├── store/
        │   │   └── benchmark-store.ts  ← Zustand store (9 algo, 45 problem)
        │   ├── hooks/use-mobile.ts
        │   └── lib/utils.ts
        ├── upload/                  ← Python benchmark motoru
        │   ├── local_search_numba.py          ← CORE: NUMBA JIT (7 algo)
        │   ├── run_smart_benchmark_numba.py   ← Ana runner
        │   ├── run_interactive_benchmark_v2_numba.py  ← STRATEGIES + run_single_test()
        │   ├── ga_strategy.py                 ← Genetic Algorithm
        │   ├── pso_strategy.py                ← Particle Swarm Optimization
        │   ├── gwo_strategy.py                ← Grey Wolf Optimizer
        │   ├── hho_strategy.py                ← Harris Hawks Optimizer
        │   ├── base_strategy.py               ← BaseRoutingStrategy (abstract)
        │   ├── dataset_loader.py              ← TSPLIB .tsp dosyası yükleyici
        │   ├── utils_benchmark.py             ← SHA-256 hash, metadata cache
        │   ├── academic_benchmark/
        │   │   └── benchmark_db/              ← GERÇEK SONUÇLAR (koru!)
        │   │       ├── latest_metadata.json   ← 17 problem × 5 algo cache
        │   │       └── history/               ← 10+ CSV/JSON sonuç dosyası
        │   ├── DEVELOPMENT_PLAN.md            ← Detaylı sprint planı
        │   └── ACADEMIC_BENCHMARK_DEVELOPER_GUIDE.md
        ├── tsp-benchmark-cli/       ← Python CLI aracı
        │   ├── core/algorithms/     ← 6 algoritma (local search, GA, SA, TS, ACO)
        │   ├── benchmark/           ← Runner + Reporter
        │   ├── cli.py               ← CLI giriş noktası
        │   ├── pyproject.toml
        │   └── requirements.txt
        ├── mini-services/
        │   └── benchmark-runner/
        │       ├── index.ts         ← Bun HTTP + WebSocket server (port 3003)
        │       └── package.json
        ├── benchmark-results/       ← Gerçek benchmark çalıştırma sonuçları
        │   └── *.csv / *.json       ← 17 problem × 5 algo (small kategori)
        ├── package.json             ← Next.js 16 bağımlılıkları (referans)
        ├── next.config.ts
        ├── components.json          ← shadcn/ui konfigürasyonu
        └── scripts/
            └── migrate-to-uniride.sh  ← Bu migration scripti
```

---

## 3. Her Bileşen Ne İşe Yarar?

### 3.1 Python Algoritma Motoru (`upload/`) — En Değerli Parça

| Dosya | Değer |
|-------|-------|
| `local_search_numba.py` | **CORE** — NUMBA JIT ile 7 local search algoritması (2-opt, 3-opt, Or-opt, Swap, Hybrid, LK, NN). TSP üzerinde gerçek hız testi yapılmış, optimize edilmiş. |
| `run_interactive_benchmark_v2_numba.py` | `run_single_test()` fonksiyonu — tek problem + algoritma çalıştırma. UniRide'ın rota optimizasyon servisine doğrudan entegre edilebilir. |
| `ga_strategy.py` / `pso_strategy.py` / `gwo_strategy.py` / `hho_strategy.py` | Meta-heuristik algoritmalar. `BaseRoutingStrategy.optimize(OptimizationRequest)` arayüzünü uyguluyorlar — UniRide'ın mevcut routing servisiyle uyumlu olabilir. |
| `dataset_loader.py` | TSPLIB `.tsp` dosyası parser'ı — standart koordinat + distance matrix yüklemesi. |
| `academic_benchmark/benchmark_db/` | **17 problem × 5 algoritma gerçek sonuçları** — CSV formatında. UniRide'ın demo datası olarak kullanılabilir. |

### 3.2 Frontend Benchmark UI (`src/`) — Referans + Adaptasyon

`page.tsx` (3742 satır) doğrudan kopyalanamaz, ancak şunlar UniRide'a taşınabilir:

| Bileşen | Önerilen Hedef |
|---------|----------------|
| Dashboard istatistik kartları | UniRide admin panelindeki rota istatistikleri |
| GAP comparison bar chart (Recharts) | Algoritma karşılaştırma görünümü |
| Algorithm Detail Sheet (pseudocode panel) | UniRide docs veya algorithm info modal |
| Glassmorphism CSS sınıfları (`globals.css`) | UniRide tema sistemi ile birleştir |
| `benchmark-store.ts` (Zustand store) | UniRide'ın routing state store'una entegre et |

### 3.3 Benchmark API Routes (`src/app/api/benchmark/`)

| Route | Açıklama |
|-------|----------|
| `POST /api/benchmark/run` | Deney başlat — ExperimentConfig'i Python'a gönder |
| `GET /api/benchmark/run/status` | Çalışan deney durumu |
| `POST /api/benchmark/run/stop` | Deneyi durdur |

UniRide'ın mevcut API yapısıyla çakışmıyorsa olduğu gibi eklenebilir.

### 3.4 Mini Service (`mini-services/benchmark-runner/`)

Bun.js HTTP + WebSocket sunucusu (port 3003). Frontend ↔ Python köprüsü.  
UniRide'ın zaten bir Python servisi varsa bu katman atlanabilir.

### 3.5 Python CLI (`tsp-benchmark-cli/`)

Bağımsız komut satırı aracı. UniRide'a doğrudan entegrasyon gerekmez — isteğe bağlı.

---

## 4. Agent'a Verilecek Görev (Entegrasyon)

UniRide'da bir Copilot agent'ı açtığında şu prompt'u kullan:

```
proposed_changes/TSP_Benchmark_Studio/ klasöründe bir TSP rota optimizasyon 
benchmark platformu var. MIGRATION_TO_UNIRIDE.md dosyasını rehber alarak şunları 
UniRide ana projesine entegre et:

1. ÖNCE: upload/ klasöründeki Python algoritmalarını (local_search_numba.py, 
   ga_strategy.py, pso_strategy.py, gwo_strategy.py, hho_strategy.py, 
   base_strategy.py, dataset_loader.py) UniRide'ın optimizer/routing servisine ekle.
   Mevcut servis yapısına uyum sağla, çakışmaları çöz.

2. SONRA: src/app/api/benchmark/ route'larını UniRide Next.js app'ine ekle.
   Eğer UniRide'ın zaten bir Python API servisi varsa mini-services/ atlanabilir.

3. OPSIYONEL: src/app/page.tsx içindeki benchmark dashboard UI'ını yeni bir 
   /benchmark route olarak ekle (app/benchmark/page.tsx). Büyük dosyayı önce 
   bileşenlere böl.

4. benchmark-results/*.csv ve upload/academic_benchmark/benchmark_db/ içindeki 
   gerçek sonuç verilerini UniRide'ın uygun veri klasörüne taşı.

Entegrasyon tamamlandıktan sonra bildir.
```

---

## 5. Entegrasyon Sonrası Temizlik

```bash
# 1. Başarılı entegrasyondan sonra proposed_changes'dan sil:
rm -rf proposed_changes/TSP_Benchmark_Studio

# 2. TSP_Benchmark_Studio reposunu GitHub'da arşivle:
#    GitHub → Settings → Danger Zone → Archive this repository
#    (Silmek yerine arşivlemek önerilir — geçmişe başvurmak için)
```

---

## 6. Bağımlılıklar (Referans)

### Python
```
numba>=0.59         # JIT compilation (kritik — local_search_numba.py için)
numpy>=1.26
pandas>=2.0
```

### Next.js (package.json'dan)
```
next 15.x, react 19.x, typescript 5.x
zustand (state), recharts (charts), framer-motion (animations)
@radix-ui/* (shadcn/ui), sonner (toast), next-themes (dark mode)
socket.io-client (WebSocket)
```

---

## 7. Dikkat Edilecekler

1. **NUMBA JIT soğuk başlama**: İlk çalıştırmada `local_search_numba.py` JIT derleme yapar (~5-15 sn). Sonraki çalıştırmalar önbellekten hızlıdır.

2. **Or-opt anomalisi**: Büyük problemlerde (n > 100) GAP %100-600 arası çıkabiliyor. Bilinen bir Numba implementasyon bug'ı — DEVELOPMENT_PLAN.md'de not edilmiş.

3. **page.tsx boyutu**: 3742 satır — doğrudan entegrasyon yerine bileşenlere bölünmeli (`components/benchmark/dashboard/`, `components/benchmark/results/` vb.).

4. **Prisma**: `prisma/schema.prisma` sadece boş bir shell (datasource var, model yok). UniRide'ın kendi şemasıyla çakışma riski yok; eklenirse birleştirilebilir.
