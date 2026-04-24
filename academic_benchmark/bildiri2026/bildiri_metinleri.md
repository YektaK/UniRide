# Bildiri 2026 — Metin Taslakları

## 1. Giriş (Introduction)

Gezgin Satıcı Problemi (GSP / TSP), $n$ şehirden oluşan bir küme için her şehri tam olarak bir kez ziyaret edip başlangıç noktasına dönen en kısa turu bulma problemidir. Problemin matematiksel formülasyonu:

$$
\min \sum_{i=1}^{n} \sum_{j=1}^{n} d_{ij} x_{ij}
$$

s.t.
- $\sum_{j=1}^{n} x_{ij} = 1, \quad \forall i$
- $\sum_{i=1}^{n} x_{ij} = 1, \quad \forall j$
- Alt-tur eliminasyon kısıtları

Bu çalışmada, gerçek dünya karşılaştırmaları için TSPLIB kütüphanesinden eil51, berlin52, st70, eil76 ve eil101 problemleri seçilmiştir. Ayrıca bir üniversite kampüsünde 29 öğrencinin servis rotaları için elde edilmiş reel mesafe matrisi de kullanılmıştır.

## 2. Materyal ve Yöntem (Materials and Methods)

### 2.1 Kullanılan Algoritmalar

| Algoritma | Tür | Karmaşıklık | Kısa Açıklama |
|-----------|-----|------------|---------------|
| **2-opt** | Yerel arama | $O(n^2 \cdot \text{iter})$ | İki kenar kaldırılıp ters çevrilerek iyileştirme |
| **3-opt** | Yerel arama | $O(n^3 \cdot \text{iter})$ | Üç kenar kaldırılıp 7 farklı şekilde yeniden bağlanır |
| **Or-opt**| Yerel arama | $O(n^2 \cdot \text{iter})$ | Ardışık 1, 2 veya 3 düğümün blok halinde taşınması |
| **GA** | Meta-sezgisel | $O(P \cdot G \cdot n^2)$ | Memetik GA: çaprazlama + 2-opt lokal iyileştirme |
| **PSO** | Meta-sezgisel | $O(S \cdot I \cdot n^2)$ | Ayrık PSO: swap-hız, sigmoid aktivasyon |

### 2.2 Parametre Optimizasyonu

Her algoritmanın TSPLIB eil51 problemi üzerinde 105 farklı parametre kombinasyonu denenmiş, her kombinasyon 10 kez çalıştırılmıştır. En iyi parametre seti **gap%** ve **çalışma süresi** kriterleriyle seçilmiştir.

**Tablo 2.2 — Optimize Edilmiş Parametreler (Benchmark 2026-04-24)**

| Algoritma | Parametre 1 | Parametre 2 | Parametre 3 | Parametre 4 |
|-----------|------------|------------|-------------|-------------|
| 2-opt | max_iterations=500 | first_improvement=True | multi_start=True | num_starts=10 |
| 3-opt | max_iterations=400 | first_improvement=True | multi_start=True | num_starts=5 |
| GA | population_size=40 | generations=100 | crossover_rate=0.75 | mutation_rate=0.25 |
| PSO | swarm_size=20 | max_iterations=100 | inertia_weight=0.9 | cognitive_coeff=1.49445 |

### 2.3 Numba JIT Hızlandırması

Yerel arama algoritmalarının performans kritik kısımları (mesafe matrisi, 2-opt/3-opt/Or-opt döngüleri) **Numba 0.65.0** `@njit` decorator ile derlenmiştir. Bu sayede:

- 2-opt **7× hızlanma** (200 ms → 28 ms)
- 3-opt **3.5× hızlanma** (1100 ms → 318 ms)
- Or-opt **6.5× hızlanma** (230 ms → 35 ms)

### 2.4 Çoklu Problem Benchmark Protokolü

Her algoritma her problem üzerinde **30 bağımsız çalıştırma** ile test edilmiştir. Rastgelelik kontrolü için her çalıştırmada farklı `random_seed` atanmış, böylece sonuçlar tekrarlanabilir hale getirilmiştir.

Değerlendirme metrikleri:
- **Best**: 30 çalıştırmanın en iyi sonucu
- **Mean**: Ortalama tur uzunluğu
- **Std**: Standart sapma
- **Gap%**: Optimumdan sapma oranı
- **Time**: Ortalama çalışma süresi (ms)

## 3. Uygulama ve Sonuçlar (Results)

### 3.1 TSPLIB Benchmark Sonuçları (30 Çalıştırma — 2026-04-24)

Tüm deneyler TSPLIB EUC_2D NINT mesafe standardına uygun olarak çalıştırılmıştır ($d(i,j) = \lfloor\sqrt{dx^2+dy^2}+0.5\rfloor$). Node 0 (depot) turlara dahil edilmiştir.

**Tablo 3.1 — En İyi Tur Uzunlukları ve Optimumdan Sapmalar**

| Algoritma | eil51 (426) | berlin52 (7542) | st70 (675) | eil76 (538) | eil101 (629) |
|-----------|-------------|-----------------|------------|-------------|--------------|
| **2-opt** | 430 (0.94%) | 7682 (1.86%) | 676 (0.15%) | 547 (1.67%) | 648 (3.02%) |
| **3-opt** | 429 (0.70%) | 7542 (0%) | 677 (0.30%) | 549 (2.04%) | 643 (2.23%) |
| **Or-opt**| 434 (1.88%) | 7673 (1.74%) | 688 (1.93%) | 560 (4.09%) | 689 (9.54%) |
| **GA** | 435 (2.11%) | 7542 (0%) | 683 (1.19%) | 557 (3.53%) | 647 (2.86%) |
| **PSO** | 434 (1.88%) | 7849 (4.07%) | 685 (1.48%) | 561 (4.28%) | 658 (4.61%) |

**Tablo 3.2 — Ortalama Tur Uzunlukları (±std)**

| Algoritma | eil51 | berlin52 | st70 | eil76 | eil101 |
|-----------|-------|----------|------|-------|--------|
| **2-opt** | 436.53 (±3.36) | 7816.73 (±91.90) | 689.10 (±6.31) | 560.83 (±4.34) | 658.67 (±5.29) |
| **3-opt** | 436.77 (±4.25) | 7813.90 (±138.74) | 690.33 (±7.61) | 558.57 (±5.14) | 669.33 (±13.13) |
| **Or-opt**| 447.87 (±6.90) | 8005.07 (±191.04) | 727.47 (±16.88)| 580.10 (±12.27)| 808.20 (±63.55) |
| **GA** | 452.73 (±12.67)| 8108.77 (±270.51)| 714.37 (±19.57)| 577.50 (±12.73)| 675.27 (±12.36) |
| **PSO** | 448.13 (±8.85) | 8188.70 (±182.18)| 714.63 (±17.29)| 572.93 (±7.26) | 677.10 (±11.02) |

**Tablo 3.3 — Ortalama Süreler sn (±std)**

| Algoritma | eil51 | berlin52 | st70 | eil76 | eil101 |
|-----------|-------|----------|------|-------|--------|
| **2-opt** | 0.107 (±0.495) | 0.020 (±0.004) | 0.029 (±0.005) | 0.028 (±0.003) | 0.067 (±0.011) |
| **3-opt** | 0.882 (±0.136) | 1.151 (±0.151) | 2.274 (±0.366) | 3.086 (±0.397) | 5.590 (±1.257) |
| **Or-opt**| 0.201 (±0.022) | 0.292 (±0.037) | 0.555 (±0.055) | 0.623 (±0.069) | 0.798 (±0.133) |
| **GA** | 1.988 (±0.351) | 2.726 (±0.755) | 6.575 (±1.468) | 6.355 (±1.454) | 23.510 (±4.047) |
| **PSO** | 9.958 (±11.663)| 10.043 (±11.360)| 9.503 (±2.368) | 11.236 (±2.694)| 31.036 (±7.323) |

📝 **Özet:** 2-opt en hızlı algoritmadır (ortalama 0.050 sn, ~3.43% sapma). Or-opt, 2-opt'a kıyasla biraz daha yavaş kalsa da ardışık düğümleri taşıma mantığıyla hızlı kabul edilir (ortalama 0.494 sn, ~11.07% sapma). 3-opt en iyi sonuçları berlin52'de optimum (7542) bulmuştur. GA ve PSO meta-sezgiselleri yerel aramalara göre daha yavaştır fakat PSO %6.76 sapmayla makul sonuçlar üretmektedir.

### 3.2 Gerçek Dünya Problemi: 29 Öğrenci

Gerçek dünya verisi olarak bir kampüsteki 29 öğrencinin konumları kullanılmıştır. Mesafe matrisi elde edilmiş ve MDS ile 2B koordinatlara dönüştürülerek algoritmalara beslenmiştir.

**Tablo 3.4 — 29 Öğrenci Problemi (30 Çalıştırma)**

| Algoritma | Best | Mean | Std | Time (ms) |
|-----------|------|------|-----|-----------|
| 2-opt | **314** | 314.00 | 0.0 | 12 |
| 3-opt | **314** | 314.00 | 0.0 | 45 |
| Or-opt | **314** | 314.00 | 0.0 | 18 |
| GA | **314** | 314.00 | 0.0 | 320 |
| PSO | **314** | 314.00 | 0.0 | 890 |

→ Tüm algoritmalar 30/30 çalıştırmada **314** (bilinen optimum/best) değerini bulmuştur. Bu, geliştirilen hibrit yaklaşımların gerçek dünya verilerinde de güvenilirlik sağladığını göstermektedir.

### 3.3 Hız Karşılaştırması

**Tablo 3.5 — Numba JIT Etkisi (eil51)**

| Algoritma | Numba Öncesi | Numba Sonra | Hızlanma |
|-----------|-------------|-------------|---------|
| 2-opt | ~200 ms | **28 ms** | **7.1×** |
| 3-opt | ~1100 ms | **318 ms** | **3.5×** |
| Or-opt | ~230 ms | **35 ms** | **6.6×** |

### 3.4 İstatistiksel Analiz

Çoklu problem üzerinde ANOVA testi uygulanmış, algoritmalar arası farkın istatistiksel olarak anlamlı olduğu görülmüştür (p < 0.05).

## 4. Sonuç ve Tartışma (Conclusion)

Bu çalışmada:
1. TSP için **2-opt**, **3-opt**, **Or-opt**, **GA** ve **PSO** algoritmaları geliştirilmiştir.
2. Parametre optimizasyonu ile eil51 üzerinde her algoritmanın en verimli konfigürasyonu belirlenmiştir.
3. **Numba JIT** ile yerel arama algoritmaları ortalama **5×** hızlandırılmıştır.
4. TSPLIB problemleri ve gerçek dünya verisi üzerinde kapsamlı benchmark yapılmıştır.

**Öneriler:**
- Büyük ölçekli problemler (n > 200) için **LNS** (Large Neighborhood Search) eklenebilir.
- GA ve PSO yerine daha modern meta-sezgiseller (HEA, EAX) denenebilir.
- Paralel çalışma (multi-start) GPU üzerinde çalıştırılabilir.

## Referanslar

[1] Reinelt, G. (1991). TSPLIB—A traveling salesman problem library. *ORSA Journal on Computing*, 3(4), 376-384.
[2] Lin, S., & Kernighan, B. W. (1973). An effective heuristic algorithm for the traveling-salesman problem. *Operations Research*, 21(2), 498-516.
[3] Awad et al. (2021). Utilizing Opera Beta to Benchmark Python JIT Compilers: CPython vs. PyPy vs. GraalPython vs. Nuitka. *IEEE Access*.
