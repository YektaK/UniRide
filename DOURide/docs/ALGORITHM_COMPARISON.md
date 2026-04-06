# 📊 UniRide Algoritma Karşılaştırması

> **Proje:** UniRide - Engelli Öğrenci Taşımacılık Sistemi  
> **Son Güncelleme:** 26 Mart 2026

---

## 1. Mevcut vs Yeni Yaklaşım (Çift Pipeline Mimarisi)

> **Pipeline A:** Cluster-First (Sweep/CW → Sezgisel)  
> **Pipeline B:** Route-First (Giant Tour → Split Decoder)  
> **Detay:** [ARCHITECTURE.md §3](./ARCHITECTURE.md)

| Metrik | Mevcut (K-Means) | Yeni (Split) | İyileştirme |
|--------|------------------|--------------|-------------|
| Ort. Araç Sayısı | 7-8 | 5-6 | -20% |
| Tek Öğrenci Rotalar | %15-20 | <%5 | -75% |
| Feasibility | %92 | %100 | +8% |
| Time Matrix | Duyarsız | Duyarlı | ✓ |

---

## 2. Algoritma Detayları

### Mevcut Algoritmalar (K-Means + Meta-Heuristic)

| Algoritma | Dosya | Parametre | Artı | Eksi |
|-----------|-------|-----------|------|------|
| GA | `ga_strategy.py` | Pop:50, Iter:100, CX:0.85, Mut:0.15 | Kanıtlanmış, çeşitli | K-Means bağımlı, yavaş yakınsama |
| PSO | `pso_strategy.py` | Swarm:30, w:0.729, c1/c2:1.49 | Hızlı yakınsama, basit | K-Means bağımlı, lokal optimum riski |
| HHO | `hho_strategy.py` | Pop:30, Iter:100, E₀:1.0 | Lévy Flight kaçışı, adaptif | K-Means bağımlı, karmaşık |
| GWO | `gwo_strategy.py` | Pop:30, Iter:100, a₀:2.0 | Sosyal hiyerarşi, dengeli | K-Means bağımlı |
| OR-Tools | `ortools_cvrp.py` | Time limit: 30s | C++ hız, endüstri standardı | Kara kutu |
| Greedy | `greedy_heuristic.py` | — | Çok hızlı | Kalite düşük |
| Permutation | `permutation_tsp.py` | — | Exact çözüm | N>10 çok yavaş |
| Two-Opt | `two_opt_strategy.py` | — | Basit iyileştirme | Yalnız başına yetersiz |

### Bağımsız (Holistik) Çözücüler

| Çözücü | Dosya | Motor | Artı | Eksi |
|--------|-------|-------|------|------|
| OR-Tools | `ortools_cvrp.py` | C++ (Google) | Endüstri standardı, hızlı | Kara kutu |
| **PyVRP** | `pyvrp_strategy.py` | C++ + Python (HGS) | DIMACS 2021 birincisi, heterojen fleet, TW | Yeni, az bilinen |
| **VROOM** | `vroom_strategy.py` | C++ (pyvroom) | Ultra-hızlı, 1000+ nokta <5s, PDPTW | Sınırlı kalite kontrolü |

### Yeni Algoritmalar (Giant Tour + Split)

| Algoritma | Dosya | Durum | Avantaj |
|-----------|-------|-------|---------|
| GA-Split | `ga_split_strategy.py` | 🔵 Planlanıyor | Kanıtlanmış + Split güvencesi |
| PSO-Split | `pso_split_strategy.py` | 🔵 Planlanıyor | Hız-kalite dengesi (Önerilen) |
| HHO-Split | `hho_split_strategy.py` | 🔵 Planlanıyor | En iyi kalite (Lévy Flight) |
| GWO-Split | `gwo_split_strategy.py` | 🔵 Planlanıyor | Akademik yayın potansiyeli |

---

## 3. Performans Karşılaştırması

### N=30 (Mevcut Ölçek) `[TAHMİNİ — Benchmark Görev 1.5.10 ile doğrulanacak]`

| Algoritma | Araç | Süre (dk) | Exec (s) | Feasible |
|-----------|------|-----------|----------|----------|
| GA | 8 | 85 | 2.3 | %90 |
| PSO | 7 | 82 | 1.8 | %92 |
| HHO | 7 | 80 | 2.1 | %94 |
| GWO | 7 | 81 | 1.9 | %93 |
| OR-Tools | 6 | 75 | 0.5 | %100 |
| **GA-Split** | 6 | 65 | 2.5 | %100 |
| **PSO-Split** | 5 | 62 | 2.0 | %100 |
| **HHO-Split** | 5 | 60 | 2.3 | %100 |
| **GWO-Split** | 5 | 61 | 2.1 | %100 |
| **PyVRP** | 5 | 58 | 0.8 | %100 |
| **VROOM** | 5 | 63 | 0.3 | %100 |

### N=300 (Hedef Ölçek) `[TAHMİNİ — Benchmark Görev 1.5.10 ile doğrulanacak]`

| Algoritma | Exec Time | Bellek | Kalite |
|-----------|-----------|--------|--------|
| GA | ~30s | Orta | Orta |
| PSO | ~25s | Düşük | Orta |
| HHO | ~28s | Düşük | İyi |
| GWO | ~26s | Düşük | İyi |
| OR-Tools | ~5s | Düşük | İyi |
| **GA-Split** | ~35s | Orta | İyi |
| **PSO-Split** | ~30s | Düşük | İyi |
| **HHO-Split** | ~32s | Düşük | Çok İyi |
| **GWO-Split** | ~30s | Düşük | Çok İyi |
| **PyVRP** | ~8s | Düşük | Çok İyi |
| **VROOM** | ~3s | Düşük | İyi |

---

## 4. Kullanım Önerileri

| Senaryo | Önerilen | Gerekçe |
|---------|----------|---------|
| Hız kritik | OR-Tools | C++, en hızlı |
| Kalite kritik | HHO-Split | Lévy Flight |
| Dengeli | PSO-Split | Hız + kalite |
| Basit setup | GA-Split | Az parametre |
| Akademik | GWO-Split | Yayın potansiyeli |
| Büyük ölçek (N>300) | PyVRP veya VROOM | Holistik C++ motorları |
| Referans baseline | OR-Tools + PyVRP | Endüstri + akademik |

---

## 5. Benchmark Planı

### Test Senaryoları

| ID | N | Sw% | So% | Açıklama |
|----|---|-----|-----|----------|
| S1 | 30 | 30% | 70% | Mevcut ölçek |
| S2 | 50 | 30% | 70% | Küçük büyüme |
| S3 | 100 | 30% | 70% | Orta ölçek |
| S4 | 300 | 30% | 70% | Hedef ölçek |
| S5 | 100 | 50% | 50% | Dengeli |
| S6 | 100 | 70% | 30% | Ağır Sw |

### Metrikler

| Metrik | Birim | İdeal |
|--------|-------|-------|
| Total Vehicles | Adet | Min |
| Total Duration | Dakika | Min |
| Avg Route Duration | Dakika | ≤90 |
| Single-Student Routes | % | <5% |
| Execution Time | Saniye | <60s |
| Feasibility | % | 100% |

### İstatistiksel Analiz

Her senaryo için: 10 run → Mean, Std, Min, Max, ANOVA testi, Wilcoxon rank-sum

---

## Referanslar

1. Prins, C. (2004). A simple and effective evolutionary algorithm for VRP.
2. Heidari, A. A., et al. (2019). Harris hawks optimization.
3. Mirjalili, S., et al. (2014). Grey wolf optimizer.
4. Kennedy, J., & Eberhart, R. (1995). PSO.
5. Vidal, T. (2022). Hybrid genetic search for the CVRP: Open-source implementation and SWAP* neighborhood. *Computers & OR*.
6. Wouda, N., et al. (2024). PyVRP: A high-performance VRP solver package. *INFORMS Journal on Computing*.
7. Coupey, J. (2024). VROOM — Vehicle Routing Open-source Optimization Machine. GitHub.
