# 🔬 SOTA Mimari Vizyonu 2026

> **Oluşturulma:** 03 Nisan 2026
> **Son Güncelleme:** 04 Nisan 2026 (04.04.2026 - Ekleyen: Z.ai)
> **Hedef:** Akademik Makale (Performance Comparison of Meta-Heuristics and SOTA Solvers on UniRide Dataset)

---

## 1. Giriş

Bu doküman, UniRide projesinin akademik ayağını oluşturan "State of the Art" (SOTA) çözücü entegrasyonu ve ALNS (Adaptive Large Neighborhood Search) geliştirme planını kapsar. Amaç, ticari ürünün ötesinde, literatürdeki en iyi çözücülerle (PyVRP, VROOM, OR-Tools) yarışabilecek bir akademik framework oluşturmaktır.

## 2. Mimari Yaklaşım: Dual-Track (Çift Kanallı) Yapı

Proje iki ana hat üzerinde ilerler:

1.  **Live/Commercial Track (Hibrit Motor):**
    *   **Strateji:** Sweep + CW + Meta-Heuristics (GA, PSO).
    *   **Öncelik:** Hız, determinizm, düşük kaynak kullanımı.
    *   **Kullanıcı:** Okul idaresi, günlük operasyon.

2.  **Academic/Research Track (SOTA Engine):**
    *   **Strateji:** Giant Tour + Split + ALNS + SOTA Baselines.
    *   **Öncelik:** Maksimum optimizasyon (Minimum araç/mesafe), akademik tekrarlanabilirlik.
    *   **Kullanıcı:** Araştırmacılar, performans kıyaslama makalesi.

---

## 3. SOTA Baseline Çözücüler (04.04.2026 - Z.ai)

Makalede "SOTA" iddiasını doğrulamak için aşağıdaki çözücüler baseline (referans) noktası olarak kullanılacaktır:

### 3.1 PyVRP (DIMACS 2021 Winner)
- **Algoritma:** Hybrid Genetic Search (HGS-CVRP).
- **Rol:** Kalite (Best-Known Solution) referansı.
- **Implementasyon:** `optimizer_api/strategies/pyvrp_strategy.py`

### 3.2 OR-Tools (Industry Standard)
- **Motor:** Guided Local Search (GLS).
- **Rol:** Endüstri standardı referansı.
- **Implementasyon:** `optimizer_api/strategies/ortools_cvrp.py`

### 3.3 VROOM (Ultra-Fast C++)
- **Özellik:** Büyük ölçekli (>1000 nokta) optimizasyon.
- **Rol:** Ölçeklenebilirlik referansı.
- **Implementasyon:** `optimizer_api/strategies/vroom_strategy.py`

---

## 4. Akademik Yol Haritası (Phased Evolution)

### Faz A: Altyapı ve Veri Seti (Tamamlandı)
- TSPLIB formatında öğrenci datası oluşturma.
- `academic_benchmark` izole test ortamının kurulması.
- `dataset_loader.py` ile otomatik optimum mesafe hesabı.

### Faz B: Split ve Meta-Sezgisel Entegrasyonu (Devam Ediyor)
- Giant Tour optimizasyonu üzerinden DP tabanlı Split Decoder kullanımı.
- PSO-Split, HHO-Split, GWO-Split algoritmalarının benchmarğa dahil edilmesi.

### Faz C: ALNS (Adaptive Large Neighborhood Search) Gelişimi
- Destroy ve Repair operatörlerinin tasarlanması:
    *   **Destroy:** Random, Worst, Shaw, Proximity removal.
    *   **Repair:** Greedy, Regret-N, Local Search.
- Adaptif skorlama mekanizması (Operator performance tracking).

### Faz D: Yazım ve Yayın
- Benchmark sonuçlarının (Gap, Time) tablolaştırılması.
- Literatürdeki diğer çalışmalarla kıyaslama.

---

## 5. Kritik Teknik Prensipler (Reproduction Rules)

1.  **Seed Sabitleme:** Tüm benchmark testleri aynı Random Seed ile yapılmalıdır.
2.  **Donanım Standardı:** Karşılaştırmalı testler aynı CPU/Bellek limitleri altında koşulmalıdır.
3.  **SHA256 Takibi:** Algoritma kodunda bir karakter bile değişirse, eski benchmark sonuçları geçersiz sayılmalı ve yeniden koşturulmalıdır (Bkz: `academic_benchmark/utils_benchmark.py`).

---

## 6. Referans Literatür

1.  **Prins, C. (2004):** Giant tours and split procedure for VRP.
2.  **Vidal, T. et al. (2012):** Hybrid genetic algorithms for VRP.
3.  **Ropke & Pisinger (2006):** Adaptive Large Neighborhood Search.
4.  **Wouda et al. (2024):** PyVRP framework.
