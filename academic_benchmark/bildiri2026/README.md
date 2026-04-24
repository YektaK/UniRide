# Bildiri 2026 — Engelsiz Ulaşım SBRP Optimizasyon Çalışması

Bu klasör, **"Engelsiz Ulaşım"** projesi kapsamında Okul Servisi Rotalama Problemi (SBRP) için algoritmik karşılaştırma deneylerini içerir. Tüm akış bağımsız Python scriptleri üzerinden yürütülür; herhangi bir web arayüzü gerekmez.

---

## 📁 Dizin Yapısı

```
bildiri2026/
├── core/                          # Temel algoritma modülleri
│   ├── __init__.py
│   ├── base_solver.py             # BaseTSPSolver arayüzü, TSPResult veri yapısı
│   │                              #   ↳ _dist_matrix_np önbelleği (Geliştirme #1)
│   │                              #   ↳ _tour_length_fast() Numba hızlandırması (Geliştirme #2)
│   ├── numba_accel.py             # Numba JIT hızlandırılmış 2-opt ve Or-opt kernelleri
│   ├── two_opt.py                 # 2-opt Yerel Arama (Croes, 1958)
│   ├── three_opt.py               # 3-opt Yerel Arama (Lin, 1965)
│   ├── or_opt.py                  # Or-opt Yerel Arama (Or, 1976)
│   ├── ga_solver.py               # Hibrit Genetik Algoritma (Holland, 1975)
│   └── pso_solver.py              # Memetik PSO (Kennedy & Eberhart, 1995)
├── configs/                       # Aşama 1 tarafından üretilen JSON konfigürasyon dosyaları
├── data/
│   ├── tsplib/                    # TSPLIB .tsp dosyaları
│   └── student_matrix.json        # 29 öğrenci gerçek zaman matrisi
├── results/
│   ├── benchmark_progress_*.csv   # Aşama 3'ün anlık çıktısı (append-only, Ctrl+C güvenli)
│   ├── benchmark_summary_*.csv    # Aşama 3'ün özet tablosu
│   ├── tuning_progress_*.csv      # Aşama 2'nin anlık çıktısı
│   ├── tuned_parameters_db.json   # Tüm tuning sonuçlarının kalıcı veritabanı
│   ├── histories/                 # Yakınsama geçmişi JSON dosyaları (Aşama 3 → Aşama 5)
│   ├── plots/                     # Aşama 5'in ürettiği akademik grafikler (PNG, 300 DPI)
│   └── reports/                   # analyze_benchmark.py'nin ürettiği Markdown raporları
├── archive_old/                   # Artık kullanılmayan eski dosyalar
├── 1_generate_config.py           # Aşama 1: İnteraktif konfigürasyon üretici
├── 2_run_tuning.py                # Aşama 2: Paralel & akıllı parametre optimizasyonu
├── 3_run_benchmark.py             # Aşama 3: Dirençli toplu benchmark (gece koşusu)
├── 5_visualize.py                 # Aşama 5: Akademik görselleştirme paketi
├── analyze_tuning.py              # Tuning sonuçlarını analiz eder (Taguchi, sıralama)
├── analyze_benchmark.py           # Benchmark sonuçlarını analiz eder (ANOVA, Wilcoxon)
├── config_manager.py              # Config yükleme yardımcısı
├── data_manager.py                # Veri yükleme yardımcısı
├── requirements.txt               # Python bağımlılıkları
├── GELiSTiRME_ONERiLERi.md        # Geliştirme önerileri ve uygulama durumu
└── README.md                      # Bu dosya
```

---

## 🔄 Akış Diyagramı (Pipeline)

```
Aşama 1: 1_generate_config.py
    → Problem seç (TSPLIB veya student_matrix)
    → Parametre aralıklarını belirle
    → configs/config_<problem>_<timestamp>.json üret
         |
         v
Aşama 2: 2_run_tuning.py
    → Config dosyasını seç (birden fazla seçilebilir)
    → Paralel çalışma: ProcessPoolExecutor ile tüm çekirdekler
    → Kaldığı yerden devam: Biten kombinasyonlar otomatik atlanır
    → results/tuned_parameters_db.json güncellenir
         |
         v
Aşama 3: 3_run_benchmark.py
    → Tuned model seç, hedef problemleri seç
    → Tekrar sayısını girin (akademik standart: 30)
    → results/benchmark_progress_*.csv (anlık, kayıpsız)
    → results/benchmark_summary_*.csv (özet)
    → results/histories/convergence_*.json (Aşama 5 için)
         |
         +---> analyze_tuning.py   → Taguchi analizi, Markdown rapor
         +---> analyze_benchmark.py → ANOVA, Wilcoxon, Markdown rapor
         |
         v
Aşama 5: 5_visualize.py
    → histories/*.json      → Yakınsama eğrisi grafikleri
    → benchmark_progress_*  → Box-plot grafikleri
    → tuning_progress_*     → Taguchi ana etki grafikleri
    → results/plots/ klasörüne PNG (300 DPI)
```

---

## 🚀 Hızlı Başlangıç

### 1. Gereksinimleri Kur

```bash
cd academic_benchmark/bildiri2026
pip install -r requirements.txt
```

### 2. Konfigürasyon Oluştur (Aşama 1)

```bash
python 1_generate_config.py
```

İnteraktif menüden eğitim problemi ve parametre aralıklarını seçin.  
`configs/config_<problem>_<timestamp>.json` olarak kaydedilir.

### 3. Parametre Optimizasyonu (Aşama 2)

```bash
python 2_run_tuning.py
```

- Mevcut config dosyalarını listeler; birini veya birkaçını seçin (`1,2` ya da `all`).
- Çok çekirdekli paralel çalışma otomatik etkindir (`ProcessPoolExecutor`).
- İşlem yarıda kesilirse tekrar çalıştırın — biten kombinasyonlar atlanır.

Tuning analizi için:
```bash
python analyze_tuning.py
```

### 4. Benchmark Koşusu (Aşama 3)

```bash
python 3_run_benchmark.py
```

- Tuned model ve hedef problemi seçin.
- Tekrar sayısını girin (akademik standart: **30**).
- `Ctrl+C` ile güvenle durdurulabilir; biten testler kaybolmaz.

Benchmark analizi (ANOVA + Wilcoxon) için:
```bash
python analyze_benchmark.py --problem eil76
```

Rapor `results/reports/FINAL_BENCHMARK_ANALYSIS_<problem>_<timestamp>.md` olarak üretilir.

### 5. Görselleştirme (Aşama 5)

```bash
python 5_visualize.py
```

Üretilen grafikler `results/plots/` klasörüne kaydedilir:

| Grafik Türü | Kaynak Veri | Dosya Adı |
|-------------|-------------|-----------|
| Yakınsama Eğrisi | `histories/convergence_*.json` | `convergence_<problem>.png` |
| Box-plot (Dağılım) | `benchmark_progress_*.csv` | `boxplot_<problem>.png` |
| Taguchi Ana Etki | `tuning_progress_*.csv` | `taguchi_<algo>_<problem>.png` |

---

## ⚙️ Algoritma Referansı

| Algoritma | Sınıf | Dosya | Özellik |
|-----------|-------|-------|---------|
| 2-opt | `TwoOptSolver` | `core/two_opt.py` | Yerel arama, Numba JIT |
| 3-opt | `ThreeOptSolver` | `core/three_opt.py` | Yerel arama, Numba JIT |
| Or-opt | `OrOptSolver` | `core/or_opt.py` | Segment taşıma, Numba JIT |
| GA | `GAOptimizer` | `core/ga_solver.py` | Hibrit: OX çaprazlama + 2-opt polisaj |
| PSO | `PSOOptimizer` | `core/pso_solver.py` | Memetik: swap-sequence + periyodik yeniden başlatma |

Tüm algoritmalar hem **Öklid koordinat (TSPLIB)** hem de **zaman matrisi (gerçek dünya)** girişlerini destekler.

### Performans Optimizasyonları

- **`_dist_matrix_np`** *(base_solver.py)*: Mesafe matrisi problem kurulumunda yalnızca **bir kez** `np.ndarray`'e dönüştürülüp önbelleklenir. Her döngüde yeniden dönüşüm yapılmaz.
- **`_tour_length_fast()`** *(base_solver.py)*: Önbelleklenmiş numpy array + Numba JIT kerneli ile hızlandırılmış tur uzunluğu hesabı. Numba yoksa Python fallback otomatik devreye girer.

---

## 📊 Çıktı Formatları

### `results/benchmark_progress_*.csv`

| Sütun | Açıklama |
|-------|----------|
| `problem` | Problem adı (eil76, berlin52 vb.) |
| `algorithm` | Algoritma adı (GA, PSO vb.) |
| `model_id` | `tuned_parameters_db.json`'daki model ID |
| `run` | Tekrar numarası |
| `duration` | Tur uzunluğu veya süre (problem tipine göre) |
| `elapsed_ms` | Hesaplama süresi (ms) |

### `results/histories/convergence_*.json`

Her benchmark koşusundaki en iyi modelin yakınsama geçmişini içerir. `5_visualize.py` tarafından tüketilir.

```json
{
  "eil76_GA_model9": {
    "problem": "eil76",
    "algorithm": "GA",
    "model_id": 9,
    "history": [600.0, 580.0, 565.0, 554.0, "..."]
  }
}
```

---

## 📝 Metodoloji

### TSPLIB Deneyleri
- **Problemler:** eil51, berlin52, st70, eil76, eil101 ve diğerleri
- **Algoritmalar:** GA, PSO, 2-opt, 3-opt, Or-opt
- **Tekrar:** 30 bağımsız çalışma (farklı seed ile)
- **Metrik:** Tur uzunluğu, hesaplama süresi (ms), Gap (%)
- **İstatistik:** Ortalama, standart sapma, Wilcoxon Signed-Rank, ANOVA

### 29 Öğrenci (Gerçek Dünya) Deneyleri
- **Girdi:** Gerçek zaman matrisi — İstanbul trafik koşulları (30×30)
- **Algoritmalar:** GA, PSO, 2-opt
- **Hedef:** Minimum toplam yolculuk süresi
- **Tekrar:** 30 bağımsız çalışma

---

## 📚 Kaynaklar

- Croes, G. (1958). A method for solving traveling salesman problems. *Operations Research*, 6(6), 791–812.
- Lin, S. (1965). Computer solutions of the traveling salesman problem. *Bell System Technical Journal*, 44(10), 2245–2269.
- Or, I. (1976). *Traveling salesman-type combinatorial problems*. Northwestern University.
- Holland, J. H. (1975). *Adaptation in Natural and Artificial Systems*. University of Michigan Press.
- Kennedy, J., & Eberhart, R. (1995). Particle swarm optimization. *Proceedings of ICNN'95*, 1942–1948.
- TSPLIB: http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/

---

**Proje:** UniRide — Engelsiz Ulaşım  
**Son Güncelleme:** 25 Nisan 2026