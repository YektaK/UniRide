# 📊 UniRide Algoritma Karşılaştırması

> **Proje:** UniRide - Engelli Öğrenci Taşımacılık Sistemi
> **Son Güncelleme:** 04 Nisan 2026 (04.04.2026 - Ekleyen: Z.ai)

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

---

## 6. SOTA Çözücü Entegrasyon Durumu (04.04.2026 - Ekleyen: Z.ai)

### 6.1 Mevcut Dosya ve Kullanım Analizi

| Çözücü | Dosya Var mı? | Registry'de Kayıtlı mı? | requirements.txt'de mi? | Aktif Kullanım |
|--------|---------------|-------------------------|-------------------------|----------------|
| **OR-Tools** | ✅ `ortools_cvrp.py` | ✅ Evet | ✅ `ortools>=9.8.0` | ✅ Aktif |
| **PyVRP** | ✅ `pyvrp_strategy.py` | ✅ Evet (graceful fallback) | ❌ YOK | ❌ Pasif |
| **VROOM** | ✅ `vroom_strategy.py` | ✅ Evet (graceful fallback) | ❌ YOK | ❌ Pasif |

### 6.2 Kod Analizi Özeti (04.04.2026 - Z.ai)

**PyVRP (`pyvrp_strategy.py`):**
- ✅ Kapsamlı implementasyon mevcut (505 satır)
- ✅ DIMACS 2021 birincisi HGS algoritması
- ✅ Heterojen fleet desteği (Sw/So kapasite)
- ✅ Time window desteği
- ⚠️ `graceful fallback` ile import ediliyor (yüklü değilse None döner)
- ❌ `requirements.txt`'de tanımlı DEĞİL

**VROOM (`vroom_strategy.py`):**
- ✅ Kapsamlı implementasyon mevcut (429 satır)
- ✅ Ultra-hızlı C++ tabanlı
- ✅ PDPTW ve Multi-trip desteği
- ✅ OSRM entegrasyonu için hazır
- ⚠️ `graceful fallback` ile import ediliyor
- ❌ `requirements.txt`'de tanımlı DEĞİL

**OR-Tools (`ortools_cvrp.py`):**
- ✅ Tam entegre ve aktif kullanımda
- ✅ GLS (Guided Local Search) metaheuristic
- ✅ Heterojen kapasite kısıtları
- ✅ Time limit desteği (30s default)

### 6.3 Akademik Makale Perspektifi (04.04.2026 - Z.ai)

**Neden SOTA Çözücüler Benchmark'a Eklenmeli?**

| Kriter | Değerlendirme | Açıklama |
|--------|---------------|----------|
| **Referans Noktası** | ⭐⭐⭐⭐⭐ Kritik | "Bizim ALNS algoritmamız, DIMACS birincisi PyVRP'ye X% yaklaşıyor" ifadesi makale güvenilirliğini artırır |
| **SOTA Kanıtı** | ⭐⭐⭐⭐⭐ Zorunlu | Makalede "State-of-the-Art" iddiası için SOTA çözücülerle kıyaslanmak ZORUNLU |
| **Reviewer Cevabı** | ⭐⭐⭐⭐⭐ Gerekli | "Neden kendi algoritmanız daha iyi?" sorusuna quantified cevap verilebilir |
| **Literatür Bağlantısı** | ⭐⭐⭐⭐ Önemli | Vidal (2022), Wouda (2024) referansları ile literatüre oturum |

**Makale Tablosu Örneği (Önerilen Format):**

| Instance | N | Optimal | PyVRP | OR-Tools | VROOM | **Ours (ALNS)** |
|----------|---|---------|-------|----------|-------|-----------------|
| berlin52 | 52 | 7542 | 7542 (0.00%) | 7542 (0.00%) | 7542 (0.00%) | **TBD** |
| kroA100 | 100 | 21282 | 21345 (0.30%) | 21420 (0.65%) | 21500 (1.02%) | **TBD** |
| d198 | 198 | 15780 | 15820 (0.25%) | 15900 (0.76%) | 15850 (0.44%) | **TBD** |

### 6.4 Önerilen Entegrasyon Adımları (04.04.2026 - Z.ai)

1. **requirements.txt Güncellemesi:**
   ```
   # SOTA Solvers (Akademik Benchmark için)
   pyvrp>=0.9.0    # DIMACS 2021 Winner - HGS
   pyvroom>=1.0.0  # Ultra-fast C++ solver
   ```

2. **Benchmark STRATEGIES Listesine Ekleme (`run_interactive_benchmark_v2.py`):**
   ```python
   # SOTA Baseline Solvers (04.04.2026 - Z.ai)
   ("PyVRP", "pyvrp", 30),      # DIMACS Winner - Gold Standard
   ("OR-Tools", "ortools", 30), # Industry Standard
   ("VROOM", "vroom", 5),       # Ultra-Fast - Scalability Test
   ```

3. **Makale İçin Strateji Kategorizasyonu:**
   - **[A] Kendi Algoritmalarımız** (Makale Konusu): Hybrid LS, ALNS, Linear Split
   - **[B] SOTA Baseline** (Karşılaştırma İçin): PyVRP, OR-Tools, VROOM
   - **[C] Klasik Sezgiseller** (Literatür Referansı): NN, Sweep, CW

### 6.5 Riskler ve Çözümler (04.04.2026 - Z.ai)

| Risk | Olasılık | Çözüm |
|------|----------|-------|
| PyVRP/VROOM kurulu değil | Yüksek | `pip install pyvrp pyvroom` basit kurulum |
| TSPLIB format uyumsuzluğu | Düşük | Mevcut `dataset_loader.py` zaten TSPLIB okuyor |
| Heterojen fleet (Sw/So) | Orta | TSPLIB CVRP instance'ları için homojen fleet kullan |
| Süre farkı | Düşük | PyVRP 30s, VROOM 5s limit ile çalıştır |

### 6.6 Sonuç (04.04.2026 - Z.ai)

**KESİNLİKLE EKLENMELİ** ✅

SOTA çözücüler (PyVRP, VROOM) akademik makale için kritik öneme sahiptir. Kod zaten hazır, sadece kurulum ve benchmark entegrasyonu gerekli. Bu olmadan makalede "SOTA" iddiası yapmak reviewer'lardan "Where is your comparison with PyVRP/HGS?" sorusu alınmasına neden olur.
