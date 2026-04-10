# TSP Benchmark CLI v1.0.0

**TSP (Gezgin Satıcı Problemi) Optimizasyon Algoritmaları Karşılaştırma Aracı**

9 farklı optimizasyon algoritmasını TSPLIB problem örnekleri üzerinde benchmark edebilen, sonuçları CSV/JSON olarak dışa aktaran Python CLI aracı.

---

## 📋 İçindekiler

1. [Bu Araç Ne İşe Yarar?](#-bu-arac-ne-i̇şe-yarar)
2. [Desteklenen Algoritmalar](#-desteklenen-algoritmalar)
3. [Kurulum](#-kurulum)
4. [Proje Yapısı](#-proje-yapısı)
5. [Kullanım — Komut Satırı](#-kullanım--komut-satırı)
6. [CLI Parametreleri](#-cli-parametreleri)
7. [Örnek Kullanım Senaryoları](#-örnek-kullanım-senaryoları)
8. [Sonuç Dosyaları](#-sonuç-dosyaları)
9. [TSPLIB Dosya Formatı](#-tsplib-dosya-formatı)
10. [Numba JIT Desteği](#-numba-jit-desteği)
11. [Gelişmiş Özellikler](#-gelişmiş-özellikler)
12. [Algoritma Detayları](#-algoritma-detayları)
13. [Sonuçları Yorumlama](#-sonuçları-yorumlama)
14. [Sık Kullanılan Komutlar](#-sık-kullanılan-komutlar--hızlı-başvuru)
15. [Sorun Giderme](#-sorun-giderme)

---

## ❓ Bu Araç Ne İşe Yarar?

TSP Benchmark CLI, **Gezgin Satıcı Problemi (Traveling Salesman Problem)** için geliştirilmiş 9 optimizasyon algoritmasının performansını karşılaştırmanıza olanak tanır.

### Temel İşlevler:
- ✅ **9 farklı TSP algoritmasını** aynı anda test etme
- ✅ **TSPLIB formatındaki** standart .tsp dosyalarını yükleme
- ✅ **Çoklu çalıştırma (multi-run)** ile ortalama ve en iyi sonuçları hesaplama
- ✅ **GAP hesaplama** — optima ne kadar yakınsınız?
- ✅ **Paralel çalıştırma** — multiprocessing ile birden fazla worker
- ✅ **CSV ve JSON** olarak sonuç dışa aktarma
- ✅ **Cache sistemi** — daha önce çalıştırılan testleri atlama
- ✅ **Zaman limiti** ve **graceful shutdown** (Ctrl+C ile güvenli çıkış)

### Neden Kullanmalısınız?
- Akademik çalışma veya tez için algoritma karşılaştırma verisi üretmek
- Hangi algoritmanın hangi problem boyutunda daha iyi performans gösterdiğini ölçmek
- Yeni bir algoritma geliştirip mevcut ones ile kıyaslamak
- Referans sonuçlar (baseline) oluşturmak

---

## 🧮 Desteklenen Algoritmalar

### Yerel Arama (Local Search)

| Kısa Ad | Tam Ad | Açıklama |
|---------|--------|----------|
| `2-opt` | 2-opt Local Search | Turdaki kesişen kenarları tersine çevirerek düzeltir |
| `3-opt` | 3-opt Local Search | 3 kenarı kaldırıp 7 farklı yeniden bağlantı dener |
| `or-opt` | Or-opt Local Search | 1-3 düğümlük segmentleri farklı pozisyonlara taşır |
| `swap` | Swap Local Search | İki düğümün yerini değiştirir |
| `hybrid` | Hybrid Local Search | Tüm yerel arama yöntemlerini sırayla uygular |

### Meta-sezgisel (Metaheuristic)

| Kısa Ad | Tam Ad | Açıklama |
|---------|--------|----------|
| `sa` | Simulated Annealing | Sıcaklık tabanlı olasılıksal kabul, yerel optımumdan kaçış |
| `ga` | Genetic Algorithm | Popülasyon tabanlı evrim, çaprazlama ve mutasyon |
| `aco` | Ant Colony Optimization | Karınca koloni optimizasyonu, feromon tabanlı |
| `ts` | Tabu Search | Kısa süreli tabu listesi ile döngü engelleme |

---

## 📦 Kurulum

### 1. Projenizi Kopyalayın

```bash
# tsp-benchmark-cli klasörünü projenize kopyalayın
cp -r tsp-benchmark-cli /your-project/
```

### 2. Bağımlılıkları Yükleyin

```bash
# Temel bağımlılık (sadece numpy)
pip install numpy

# Opsiyonel: Numba JIT desteği ile 10-100x hız artışı
pip install numba
```

> **Numba yüklenmezse ne olur?** Araç sorunsuz çalışır, tüm algoritmalar "pure Python" modunda çalışır. Numba yüklendiğinde 2-opt, 3-opt, Or-opt, Swap ve Hybrid algoritmaları JIT ile derlenerek çok daha hızlı çalışır.

### 3. Doğrulama

```bash
# Aracın çalıştığını doğrulayın
cd tsp-benchmark-cli
python -m tsp_benchmark_cli list-algorithms
```

Çıktıda 9 algoritma listelenmelidir:

```
============================================================
  AVAILABLE TSP ALGORITHMS
============================================================

  NUMBA JIT: ✅ ENABLED   (veya ⚠️ DISABLED)

  LOCAL SEARCH:
    2-opt    — 2-opt Local Search
    3-opt    — 3-opt Local Search
    or-opt   — Or-opt Local Search
    swap     — Swap Local Search
    hybrid   — Hybrid Local Search

  METAHEURISTICS:
    sa       — Simulated Annealing
    ga       — Genetic Algorithm
    aco      — Ant Colony Optimization
    ts       — Tabu Search

  Total: 9 algorithms
```

---

## 📁 Proje Yapısı

```
tsp-benchmark-cli/
├── README.md                          # Bu dokümantasyon dosyası
├── pyproject.toml                     # Python paket yapılandırması
├── requirements.txt                   # pip bağımlılıkları
├── __init__.py                        # Paket başlatma (v1.0.0)
├── __main__.py                        # Modül girişi: python -m tsp_benchmark_cli
├── cli.py                             # CLI arayüzü (argparse)
│
├── core/                              # Çekirdek modüller
│   ├── __init__.py
│   ├── tsp_problem.py                 # TSPProblem veri sınıfı, TSPLIB ayrıştırıcı
│   ├── numba_utils.py                 # Numba JIT derlenmiş fonksiyonlar
│   └── algorithms/                    # Algoritma implementasyonları
│       ├── __init__.py                # ALGORITHM_REGISTRY, get_algorithm()
│       ├── base.py                    # TSPAlgorithm (soyut), AlgorithmResult
│       ├── local_search.py            # 2-opt, 3-opt, Or-opt, Swap, Hybrid
│       ├── simulated_annealing.py     # Simulated Annealing
│       ├── genetic_algorithm.py       # Genetic Algorithm (OX/PMX crossover)
│       ├── ant_colony.py              # Ant Colony Optimization (ACS)
│       └── tabu_search.py             # Tabu Search
│
├── benchmark/                         # Benchmark çalıştırma ve raporlama
│   ├── __init__.py
│   ├── runner.py                      # BenchmarkRunner (sıralı/paralel)
│   └── reporter.py                    # CSV/JSON export, konsol çıktısı
│
└── results/                           # Varsayılan sonuç çıktı dizini
    ├── benchmark_TIMESTAMP.csv
    ├── benchmark_TIMESTAMP.json
    └── metadata.json                  # Cache (artımlı benchmark için)
```

---

## 🚀 Kullanım — Komut Satırı

Araç 4 ana komut sunar:

### `run` — Tam Benchmark Çalıştırma

```bash
python -m tsp_benchmark_cli run -p <dizin_veya_dosya> -a <algoritmalar>
```

### `quick` — Hızlı Test (Demo)

```bash
python -m tsp_benchmark_cli quick
```

3 dahili demo problemi üzerinde tüm 9 algoritmayı 1'er kez çalıştırır.

### `list-algorithms` — Algoritma Listesi

```bash
python -m tsp_benchmark_cli list-algorithms
```

### `info` — Algoritma Detayları

```bash
python -m tsp_benchmark_cli info -a sa
```

Belirli bir algoritmanın parametrelerini ve özelliklerini gösterir.

---

## ⚙️ CLI Parametreleri

### `run` Komutu Parametreleri

| Parametre | Kısa | Varsayılan | Açıklama |
|-----------|------|-----------|----------|
| `--problems` | `-p` | *(zorunlu)* | .tsp dosyası veya dizin yolu |
| `--algorithms` | `-a` | `all` | Virgülle ayrılmış algoritma adları veya `all` |
| `--runs` | `-n` | `3` | Her (problem, algoritma) çifti için çalıştırma sayısı |
| `--seed` | | `42` | Rastgele tohum (tekrar edilebilirlik) |
| `--time-limit` | | `300` | Her çözüm için maksimum süre (saniye) |
| `--parallel` | | `false` | Paralel çalıştırma aktif et |
| `--workers` | | `min(CPU, 4)` | Paralel worker sayısı |
| `--output-dir` | `-o` | `results` | Sonuç çıktı dizini |
| `--format` | `-f` | `both` | Çıktı formatı: `csv`, `json`, `both` |
| `--skip-cached` | | `false` | Önbellekteki sonuçları atla |
| `--no-display` | | `false` | Konsola yazdırma (sadece dosyaya kaydet) |
| `--category` | | *(yok)* | Problem boyutu filtresi: `small`, `medium`, `large` |

### `quick` Komutu Parametreleri

| Parametre | Kısa | Varsayılan | Açıklama |
|-----------|------|-----------|----------|
| `--problems` | `-p` | *(demo)* | Özel .tsp dosyası/dizin (boşsa dahili demo) |

---

## 📖 Örnek Kullanım Senaryoları

### Senaryo 1: Hızlı Demo Test

```bash
python -m tsp_benchmark_cli quick
```

**Ne yapar?**
- 3 dahili demo problemi oluşturur (5, 10 ve 20 şehir)
- 9 algoritmanın hepsini çalıştırır
- Sonuçları konsola yazdırır ve `results/` dizinine kaydeder
- Toplam süre: ~20-40 saniye

**Örnek Çıktı:**
```
======================================================================
  TSP BENCHMARK CLI v1.0.0
======================================================================
  Problemler  : 3
  Algoritmalar: 2-opt, 3-opt, or-opt, swap, hybrid, sa, ga, aco, ts
  Çalıştırma  : 1 run / test
  Toplam test : 27
======================================================================

[1/3] demo_5 (n=5, opt=0)
  [2-opt    ]   3.7% ~0dk 00sn ⭐ GAP: 0.00% (best: 0.00%) (1.3sn)
  [3-opt    ]   7.4% ~0dk 00sn ⭐ GAP: 0.00% (best: 0.00%) (0.0sn)
  ...
```

### Senaryo 2: Belirli Algoritmaları Test Etme

```bash
python -m tsp_benchmark_cli run -p problems/ -a 2-opt,sa,ga -n 5
```

**Ne yapar?**
- `problems/` dizinindeki tüm .tsp dosyalarını yükler
- Sadece 2-opt, SA ve GA algoritmalarını çalıştırır
- Her testi 5 kez tekrarlar (ortalama ve en iyi değer hesaplar)

### Senaryo 3: Tek Bir Problem Dosyası

```bash
python -m tsp_benchmark_cli run -p berlin52.tsp -a all -n 3
```

### Senaryo 4: Paralel Çalıştırma (4 Worker)

```bash
python -m tsp_benchmark_cli run -p data/tsplib/ -a all --parallel --workers 4
```

### Senaryo 5: Büyük Problemler İçin Zaman Limiti

```bash
python -m tsp_benchmark_cli run -p large_problems/ -a sa,ga,aco --time-limit 600 -n 1
```

### Senaryo 6: Sadece Küçük Problemleri Filtreleme

```bash
python -m tsp_benchmark_cli run -p all_problems/ -a all --category small
```

### Senaryo 7: Önbellek ile Artımlı Benchmark

```bash
# İlk çalıştırma: tüm testler
python -m tsp_benchmark_cli run -p data/ -a all -n 3

# İkinci çalıştırma: yeni eklenen testleri çalıştır, öncekileri atla
python -m tsp_benchmark_cli run -p data/ -a all -n 3 --skip-cached
```

### Senaryo 8: Algoritma Detaylarını İnceleme

```bash
python -m tsp_benchmark_cli info -a ga
```

```
============================================================
  Genetic Algorithm (ga)
============================================================

  Type: Metaheuristic
  NUMBA: Pure Python fallback

  Parameters:
    population_size: 60
    generations: 500
    elite_count: 4
    tournament_size: 5
    crossover_method: ox
    mutation_rate: 0.2
    mutation_method: inversion
    local_search_interval: 20
    construction: random
```

---

## 📊 Sonuç Dosyaları

Benchmark çalıştırıldıktan sonra `results/` dizininde (veya `--output-dir` ile belirtilen dizinde) şu dosyalar oluşur:

### JSON Dosyası (`benchmark_TIMESTAMP.json`)

```json
{
  "benchmark_tool": "tsp-benchmark-cli",
  "version": "1.0.0",
  "timestamp": "2026-04-08T14:47:34.762044",
  "total_results": 27,
  "results": [
    {
      "problem": "berlin52",
      "dimension": 52,
      "category": "small",
      "optimal": 7542,
      "algorithm": "sa",
      "avg_length": 7623.45,
      "avg_gap": 1.08,
      "best_gap": 0.52,
      "avg_time_ms": 2340.12,
      "n_runs": 5,
      "timestamp": "2026-04-08T14:47:13.755318"
    }
  ]
}
```

### CSV Dosyası (`benchmark_TIMESTAMP.csv`)

| problem | dimension | category | optimal | algorithm | tour_length | gap | avg_gap | best_gap | execution_time_ms | avg_time_ms | n_runs | timestamp |
|---------|-----------|----------|---------|-----------|-------------|-----|---------|----------|-------------------|-------------|--------|-----------|
| berlin52 | 52 | small | 7542 | sa | 7623.45 | 1.08 | 1.08 | 0.52 | 2340.12 | 2340.12 | 5 | 2026-04-08... |

### Metadata Dosyası (`metadata.json`)

Önbellek sistemi tarafından kullanılır. Her (problem, algoritma) çiftinin ortalama sonuçlarını saklar. `--skip-cached` parametresiyle kullanılır.

### Sonuç Alanları Açıklaması

| Alan | Açıklama |
|------|----------|
| `problem` | Problem adı (.tsp dosyasından) |
| `dimension` | Şehir/düğüm sayısı |
| `category` | Boyut kategorisi: small (≤100), medium (101-500), large (>500) |
| `optimal` | Bilinen en iyi tur uzunluğu (0 = bilinmiyor) |
| `algorithm` | Kullanılan algoritmanın kısa adı |
| `avg_length` | Tüm çalıştırmalardaki ortalama tur uzunluğu |
| `avg_gap` | Optimala olan ortalama yüzde fark |
| `best_gap` | Tüm çalıştırmalardaki en iyi GAP |
| `avg_time_ms` | Ortalama çalışma süresi (milisaniye) |
| `n_runs` | Çalıştırma sayısı |

---

## 📄 TSPLIB Dosya Formatı

Araç standart TSPLIB `.tsp` formatını destekler. Minimum örnek:

```
NAME: berlin52
TYPE: TSP
COMMENT: 52 locations in Berlin
DIMENSION: 52
EDGE_WEIGHT_TYPE: EUC_2D
NODE_COORD_SECTION
  1  565.0  575.0
  2  1215.0  245.0
  3  1515.0  582.0
  ...
EOF
```

### Desteklenen Mesafe Tipleri

| Tip | Açıklama |
|-----|----------|
| `EUC_2D` | 2D Öklid mesafesi (varsayılan, numpy ile hızlı hesaplama) |
| `CEIL_2D` | Tavanhane öklid mesafesi (TSPLIB CEIL_2D) |
| `GEO` | Coğrafi mesafe (TSPLIB GEO) |

### Optimal Tur (`.opt.tour`)

Eğer `.tsp` dosyasının yanında `.opt.tour` dosyası varsa, araç otomatik olarak optimal tur uzunluğunu hesaplar:

```
TOUR_SECTION
1 2 3 4 5 ... 52 -1
EOF
```

Bu sayede GAP hesaplaması otomatik olarak yapılabilir.

---

## ⚡ Numba JIT Desteği

### Numba Ne Yapıyor?

Numba, Python kodunu derleme zamanında makine koduna dönüştürür (JIT derleme). TSP Benchmark CLI'da şu fonksiyonlar Numba ile derlenir:

- `calc_tour_length_numba()` — Tur uzunluğu hesaplama
- `two_opt_improve()` — 2-opt yerel arama
- `three_opt_improve()` — 3-opt yerel arama (7 yeniden bağlantı)
- `or_opt_improve()` — Or-opt yerel arama
- `swap_improve()` — Swap yerel arama
- `nearest_neighbor_route()` — En yakın komşu yapılandırma
- `random_route()` — Rastgele tur oluşturma

### Numba Durumunu Kontrol Etme

```bash
python -m tsp_benchmark_cli list-algorithms
# Çıktıda: "NUMBA JIT: ✅ ENABLED" veya "⚠️ DISABLED"
```

### Performans Farkı

| İşlem | Pure Python | Numba JIT | Fark |
|-------|-------------|-----------|------|
| 2-opt (52 şehir) | ~50ms | ~0.5ms | **~100x** |
| 3-opt (52 şehir) | ~5000ms | ~20ms | **~250x** |
| Hybrid (52 şehir) | ~6000ms | ~50ms | **~120x** |

> **Not:** Meta-sezgisel algoritmalar (SA, GA, ACO, TS) Python seviyesinde çalışır, Numba'nın etkisi daha sınırlıdır.

### Numba Yükleme

```bash
pip install numba
```

Numba yüklenemezse (örn. ARM mimarisi veya eski Python), araç **otomatik olarak pure Python fallback** kullanır — **hiçbir hata vermez**.

---

## 🔧 Gelişmiş Özellikler

### Çoklu Çalıştırma (Multi-Run)

Her (problem, algoritma) çiftini birden fazla kez çalıştırarak istatistiksel olarak daha güvenilir sonuçlar elde edin:

```bash
python -m tsp_benchmark_cli run -p data/ -a sa,ga -n 10
```

- `avg_length`: 10 çalıştırmanın ortalaması
- `best_gap`: 10 çalıştırmadaki en iyi GAP
- Her çalıştırma farklı seed kullanır (tekrar edilebilir)

### Paralel Çalıştırma

Büyük benchmark'ları hızlandırmak için multiprocessing kullanın:

```bash
python -m tsp_benchmark_cli run -p data/ -a all --parallel --workers 8
```

- `--workers`: Worker sayısı (varsayılan: `min(CPU çekirdeği, 4)`)
- Her worker bağımsız bir süreçte çalışır
- Sonuçlar otomatik olarak toplanır ve raporlanır

### Artımlı Benchmark (Cache)

Büyük testler uzun sürdüğünde, daha önce çalıştırılan testleri atlayabilirsiniz:

```bash
# İlk: 100 test, 30 dakika
python -m tsp_benchmark_cli run -p data/ -a all -n 5

# Yeni algoritma eklediniz, sadece onu çalıştırın:
python -m tsp_benchmark_cli run -p data/ -a new-algo -n 5 --skip-cached
```

`metadata.json` dosyası her (problem, algoritma) çiftinin sonucunu saklar.

### Graceful Shutdown (Ctrl+C)

Uzun benchmark'larda `Ctrl+C` ile güvenli çıkabilirsiniz:

```
⚠️  DURDURMA İSTEĞİ ALINDI!
📝 Mevcut sonuçlar kaydediliyor...
💾 CSV: results/benchmark_20260408_150000.csv
💾 JSON: results/benchmark_20260408_150000.json
```

Tamamlanan sonuçlar kaydedilir, devam eden testler iptal edilir.

### Zaman Limiti

Her çözüm için maksimum süre belirleyebilirsiniz:

```bash
# Her çözüm max 60 saniye
python -m tsp_benchmark_cli run -p data/ -a sa,ga --time-limit 60
```

Algoritma zaman limitini aşarsa, o ana kadar bulunan en iyi çözüm döndürülür.

### Problem Boyutu Filtreleme

```bash
# Sadece küçük problemler (≤100 şehir)
python -m tsp_benchmark_cli run -p data/ -a all --category small

# Sadece orta boyutlu (101-500)
python -m tsp_benchmark_cli run -p data/ -a all --category medium

# Sadece büyük (>500)
python -m tsp_benchmark_cli run -p data/ -a all --category large
```

---

## 📚 Algoritma Detayları

### 2-opt Local Search (`2-opt`)

**Prensip:** Turdaki kesişen iki kenarı keser ve bağlantı noktalarını yer değiştirir.

```
Önce: A ─── B        Sonra: A ─── C
              ↗  ↘            ↗       ↘
            D      C          D         B
```

**Parametreler:**
- `max_iterations`: 1000 (maksimum dış döngü sayısı)
- `first_improvement`: False (ilk iyileştirmede dur)
- `construction`: "nearest" (başlangıç turu: nearest neighbor)

### 3-opt Local Search (`3-opt`)

**Prensip:** 3 kenarı kaldırır ve 7 farklı yeniden bağlantı dener. 2-opt'tan daha güçlüdür ama daha yavaştır.

**Parametreler:**
- `max_iterations`: 500
- `first_improvement`: False
- `construction`: "nearest"

> **Not:** 3-opt, Numba segfault riskini önlemek için pure Python modunda çalışır.

### Or-opt Local Search (`or-opt`)

**Prensip:** 1-3 düğümlük segmentleri tur içindeki farklı pozisyonlara taşır.

**Parametreler:**
- `max_iterations`: 500
- `max_segment_size`: 3 (taşınacak maksimum segment boyutu)
- `construction`: "nearest"

### Swap Local Search (`swap`)

**Prensip:** İki düğümün yerini değiştirir (bitişik olmayanlar).

**Parametreler:**
- `max_iterations`: 1000
- `first_improvement`: False
- `construction`: "nearest"

### Hybrid Local Search (`hybrid`)

**Prensip:** Swap → 2-opt → Or-opt → 3-opt sırasını her döngüde uygular. Genellikle en iyi yerel arama sonucunu verir.

**Parametreler:**
- `max_cycles`: 5 (tam döngü sayısı)
- `construction`: "nearest"

### Simulated Annealing (`sa`)

**Prensip:** Yüksek sıcaklıkta kötü çözümleri kabul etme olasılığı yüksek, giderek azalır. Böylece yerel optımumdan kaçar.

**Parametreler:**
- `initial_temp`: 10000.0
- `cooling_rate`: 0.9995
- `min_temp`: 0.01
- `reheat_interval`: 10000 (iyileşme yoksa yeniden ısıt)
- `neighborhood`: "2opt"
- `max_iterations`: 500000
- `local_search_final`: True (son 2-opt geçişi)

### Genetic Algorithm (`ga`)

**Prensip:** Tur popülasyonu oluşturur, seçim-çaprazlama-mutasyon ile evrimleşir.

**Parametreler:**
- `population_size`: 60
- `generations`: 500
- `elite_count`: 4 (en iyi bireyleri taşı)
- `tournament_size`: 5
- `crossover_method`: "ox" (Order Crossover)
- `mutation_rate`: 0.2
- `mutation_method`: "inversion"
- `local_search_interval`: 20 (her N jenerasyonda 2-opt)

### Ant Colony Optimization (`aco`)

**Prensip:** Sanal karıncalar feromon izleri ve mesafe bilgisiyle olasılıksal tur inşa eder.

**Parametreler:**
- `num_ants`: 25 (her iterasyondaki karınca sayısı)
- `alpha`: 1.0 (feromon ağırlığı)
- `beta`: 3.0 (sezgisel ağırlık, 1/mesafe)
- `evaporation_rate`: 0.5
- `q`: 100.0 (feromon depozito faktörü)
- `elite_factor`: 0.5 (global en iyiye ek depozito)
- `max_iterations`: 500
- `local_search_interval`: 25

### Tabu Search (`ts`)

**Prensip:** Son yapılan hamleleri "tabu" listesine ekler, böylece döngü önlenir. Aspirasyon kriteri ile tabu hamleler kabul edilebilir.

**Parametreler:**
- `tabu_tenure`: 20 (tabu kalma süresi)
- `max_iterations`: 10000
- `neighborhood`: "2opt" (veya "swap", "mixed")
- `max_neighbors`: 0 (tüm komşular = 0)
- `intensification_interval`: 50 (iyileşme yoksa en iyiye dön)
- `local_search_final`: True

---

## 📈 Sonuçları Yorumlama

### GAP (Genelic Approximation Percentage)

GAP, algoritmanın bulduğu çözüm ile bilinen optimal değer arasındaki yüzde farktır:

```
GAP% = (bulunan_tur_uzunluğu - optimal_değer) / optimal_değer × 100
```

**GAP Yorumlama:**

| GAP% | Değerlendirme | Emoji |
|------|---------------|-------|
| ≤ 1% | Mükemmel | ⭐ |
| 1-3% | Çok İyi | ✅ |
| 3-5% | İyi | 👍 |
| 5-10% | Kabul Edilebilir | ⚠️ |
| > 10% | Zayıf | ❌ |

> **Not:** Eğer optimal değer bilinmiyorsa (0), GAP hesaplanmaz ve "N/A" gösterilir.

### Konsol Çıktısı Örneği

```
======================================================================
  TSP BENCHMARK RESULTS
======================================================================

Problem         n │ Algorithm │    Length │    Gap% │       Time
--------------------------------------------------------------------------------
demo_5           5 │ 2-opt     │      44.14 │    0.00% │       1.3sn
demo_5           5 │ 3-opt     │      44.14 │    0.00% │       0.0sn
demo_5           5 │ hybrid    │      44.14 │    0.00% │       0.1sn
demo_10         10 │ 2-opt     │      28.41 │    0.00% │       0.0sn
demo_10         10 │ 3-opt     │      27.58 │    0.00% │       2.9sn
...
--------------------------------------------------------------------------------
  Problems: 3  |  Algorithms: 9  |  Total tests: 27

======================================================================
  ALGORITHM RANKING (sorted by average GAP)
======================================================================

Algorithm       │   Avg GAP% │  Best GAP% │    Avg Time │  Tests
--------------------------------------------------------------------------------
hybrid          │      0.00% │      0.00% │       0.0sn │      9
sa              │      0.00% │      0.00% │       1.5sn │      9
ga              │      0.00% │      0.00% │       0.8sn │      9
...
--------------------------------------------------------------------------------
```

---

## ⚡ Sık Kullanılan Komutlar (Hızlı Başvuru)

```bash
# Hızlı demo test
python -m tsp_benchmark_cli quick

# Tüm algoritmaları çalıştır
python -m tsp_benchmark_cli run -p data/ -a all

# Belirli algoritmalar
python -m tsp_benchmark_cli run -p data/ -a 2-opt,sa,ga,ts

# Çoklu çalıştırma (istatistiksel güvenilirlik)
python -m tsp_benchmark_cli run -p data/ -a sa,ga -n 10

# Paralel çalıştırma
python -m tsp_benchmark_cli run -p data/ -a all --parallel --workers 4

# Zaman limiti
python -m tsp_benchmark_cli run -p data/ -a sa,ga,aco --time-limit 60

# Sadece küçük problemler
python -m tsp_benchmark_cli run -p data/ -a all --category small

# Sadece CSV çıktı
python -m tsp_benchmark_cli run -p data/ -a all -f csv

# Özel çıktı dizini
python -m tsp_benchmark_cli run -p data/ -a all -o my_results/

# Cache ile artımlı benchmark
python -m tsp_benchmark_cli run -p data/ -a all --skip-cached

# Algoritma bilgisi
python -m tsp_benchmark_cli info -a ga

# Algoritma listesi
python -m tsp_benchmark_cli list-algorithms
```

---

## 🔨 Sorun Giderme

### "Unknown algorithm: 'xxx'"
```
❌ Unknown algorithm: 'SA'
   Available: 2-opt, 3-opt, or-opt, swap, hybrid, sa, ga, aco, ts
```
**Çözüm:** Algoritma adları **küçük harf** kullanılmalıdır. `SA` → `sa`

### "Path not found: data/"
```
❌ Path not found: data/
```
**Çözüm:** Dizin veya dosya yolunu kontrol edin. Mutlak veya göreli yol kullanılabilir.

### "No problems to benchmark"
```
❌ No problems to benchmark.
```
**Çözüm:** Dizin içinde `.tsp` uzantılı dosya bulunamadı. Dosya uzantılarını kontrol edin.

### Numba Import Hatası
```
WARNING: Numba not available, using pure Python fallback
```
**Bu bir hata değil!** Araç sorunsuz çalışır, sadece daha yavaş. Düzeltmek için:
```bash
pip install numba
```

### Bellek Sorunu (Büyük Problemler)
Büyük problemlerde (>1000 şehir) mesafe matrisi çok bellek tüketir.
- **3-opt ve Hybrid** algoritmaları O(n³) karmaşıklığa sahiptir
- `--time-limit` kullanın
- `--category small` veya `medium` ile filtreleyin

### Numba Segfault (3-opt)
3-opt algoritması, Numba JIT derlemesinde bazı ortamlarda segfault verebilir.
Araç bu durumu otomatik olarak algılar ve **pure Python 3-opt** kullanır.

---

## 📄 Lisans

Bu araç TSP Benchmark CLI projesi kapsamında geliştirilmiştir.

---

> **İpucu:** Sonuçlarınızı `results/` dizininden CSV veya JSON olarak indirip Excel, Python (pandas), R veya MATLAB ile analiz edebilirsiniz.
