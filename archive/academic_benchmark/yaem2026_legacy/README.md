# YAEM 2026 — GWO / HHO ile TSP Taguchi Parametre Optimizasyonu

Bu çalışma, önceki bildirilerdeki (ISARC) GA/PSO tabanlı Taguchi DOE yaklaşımını tamamen bir kenara bırakarak, **YAEM 2026** kongresi için özel olarak hazırlanmış modern bir **Memetik (Hibrit) Yapay Zeka** boru hattını (pipeline) içerir.

## Algoritmalar

| Algoritma | Açıklama |
|-----------|----------|
| GWO-2opt | Memetik GWO (başlangıç + periyodik + final 2-opt polish) |
| GWO-LKH | GWO (Lin-Kernighan / 3-opt polish hibrit) |
| GWO-ALNS | GWO (Adaptive Large Neighborhood Search polish hibrit) |
| GWO-Pure | Saf GWO (hiçbir lokal arama / polish yok) |
| HHO-2opt | Memetik HHO (başlangıç + periyodik + final 2-opt polish) |
| HHO-LKH | HHO (Lin-Kernighan / 3-opt polish hibrit) |
| HHO-ALNS | HHO (Adaptive Large Neighborhood Search polish hibrit) |
| HHO-Pure | Saf HHO (hiçbir lokal arama / polish yok) |
| GA, PSO, 2-opt, 3-opt, Or-opt | ISARC referans algoritmaları (karşılaştırma için) |

## Çalıştırma

```bash
# 1. Konfigürasyon oluştur
python 1_generate_config.py

# 2. Taguchi DOE parametre optimizasyonu
python 2_run_tuning.py

# 3. Optimize edilmiş parametrelerle benchmark
python 3_run_benchmark.py

# 4. ANOVA / Taguchi analizi
python analyze_tuning.py

# 5. Benchmark analizi (Wilcoxon, LaTeX tablo)
python analyze_benchmark.py

# 6. Görselleştirme
python 5_visualize.py
```

Veya tek komutla tüm pipeline:
```bash
python orchestrate_batch.py
```

## Dizin Yapısı

```
yaem2026/
  core/                  # TSP çözüm algoritmaları
    gwo_solver.py        # GWOOptimizer + PureGWOOptimizer
    hho_solver.py        # HHOOptimizer + PureHHOOptimizer
    ...
  benchmarks/            # TSPLIB benchmark modülü
  configs/               # Oluşturulan konfigürasyonlar
  results/               # Çıktı dosyaları
    reports/             # Analiz raporları
    plots/               # Görselleştirmeler
    histories/           # Yakınsama eğrileri
  data/
    tsplib/              # TSPLIB problem dosyaları
    tuned_parameters_db.json  # En iyi parametreler
```

## Notlar

- Saf (Pure) varyantlar, sadece metaheuristik arama yapar — 2-opt polish kullanmaz.
- Memetik varyantlar, başlangıç popülasyonunda + periyodik + final 2-opt polish uygular.
- Tüm algoritmalar Numba JIT hızlandırmalı tur uzunluğu hesaplaması kullanır.
- Pipeline kesintilere dayanıklıdır: CSV'ye anlık kayıt ile kaldığı yerden devam eder.
