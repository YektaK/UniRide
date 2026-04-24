# Parametre Optimizasyonu Deney Tasarımı ve Analiz Raporu
## Bildiri 2026: SBRP TSP Çözüm Algoritmaları

---

## 1. Giriş ve Amaç

Bu çalışmada, TSP varyantları (2-opt, 3-opt, Or-opt, GA ve PSO) için problem bağımlı optimum parametrelerin belirlenmesi amaçlanmıştır. TSPLIB `eil51` problemi (n=51, optimum=426) referans test problemi olarak seçilmiştir.

**Amaçlar:**
1. Her algoritma için kritik parametrelerin belirlenmesi
2. Parametre seviyelerinin çözüm kalitesi üzerindeki etkisinin ölçülmesi
3. En iyi parametre setinin istatistiksel olarak doğrulanması
4. ANOVA ve Signal-to-Noise (S/N) analizi ile Taguchi tasarım uygulaması

---

## 2. Deney Tasarımı

### 2.1 Test Problemi

| Özellik | Değer |
|---------|-------|
| Problem | eil51 |
| Düğüm sayısı (n) | 51 |
| Optimum tur uzunluğu | 426 |
| Kaynak | TSPLIB95 |

### 2.2 Yöntem: Faktöriyel Dizayn + Taguchi L8

Her algoritma için:
- **Faktörler:** 3-5 bağımsız parametre
- **Seviyeler:** Her parametre için 2-3 seviye
- **Tekrarlar:** Her parametre seti için 10 bağımsız çalıştırma
- **Başlangıç seed:** Deterministik tekrarlanabilirlik için sabitlenmiş

### 2.3 Parametre Setleri

#### A. 2-opt Algoritması (Kroes, 1958)

| Parametre | Seviye 1 | Seviye 2 | Seviye 3 | Kısaltma |
|-----------|----------|----------|----------|----------|
| `max_iterations` | 500 | 1000 | 2000 | MI |
| `first_improvement` | True | False | — | FI |
| `num_starts` | 1 | 5 | 10 | NS |
| **Toplam kombinasyon** | | | | **18** |

#### B. 3-opt Algoritması (Lin, 1965)

| Parametre | Seviye 1 | Seviye 2 | Seviye 3 | Kısaltma |
|-----------|----------|----------|----------|----------|
| `max_iterations` | 200 | 400 | 800 | MI |
| `first_improvement` | True | False | — | FI |
| `num_starts` | 1 | 3 | 5 | NS |
| **Toplam kombinasyon** | | | | **18** |

#### C. Or-opt Algoritması (Or, 1976)

| Parametre | Seviye 1 | Seviye 2 | Seviye 3 | Kısaltma |
|-----------|----------|----------|----------|----------|
| `max_iterations` | 300 | 600 | 1000 | MI |
| `max_segment_size` | 1 | 2 | 3 | MS |
| `num_starts` | 1 | 3 | 5 | NS |
| **Toplam kombinasyon** | | | | **27** |

#### D. Genetik Algoritma (Holland, 1975; Goldberg, 1989)

| Parametre | Seviye 1 | Seviye 2 | Seviye 3 | Kısaltma |
|-----------|----------|----------|----------|----------|
| `population_size` | 40 | 80 | 120 | PS |
| `generations` | 100 | 200 | — | GN |
| `crossover_rate` | 0.75 | 0.85 | 0.95 | CR |
| `mutation_rate` | 0.05 | 0.15 | 0.25 | MR |
| `elite_count` | 1 | 2 | 3 | EC |
| **Toplam kombinasyon** | | | | **162** |

#### E. Parçacık Sürü Optimizasyonu (Kennedy & Eberhart, 1995)

| Parametre | Seviye 1 | Seviye 2 | Seviye 3 | Kısaltma |
|-----------|----------|----------|----------|----------|
| `swarm_size` | 20 | 40 | 60 | SS |
| `max_iterations` | 100 | 200 | 300 | MI |
| `inertia_weight` | 0.6 | 0.729 | 0.9 | IW |
| `cognitive_coeff` | 1.0 | 1.49445 | 2.0 | CC |
| **Toplam kombinasyon** | | | | **81** |

---

## 3. Performans Metrikleri

### 3.1 Değişkenler

1. **Yanıt değişkeni:** Ortalama tur uzunluğu ($\bar{L}$)
2. **S/N Oranı (Signal-to-Noise):** "Küçük-better" kriteri
   $$ S/N = -10 \log\left(\frac{1}{n}\sum_{i=1}^{n} L_i^2 \right) $$
3. **Gap (%):** Optimumdan sapma
   $$ \text{Gap} = \frac{\bar{L} - L_{opt}}{L_{opt}} \times 100 $$

---

## 4. Beklenen Analiz Yöntemleri

### 4.1 ANOVA (Analysis of Variance)

Her parametrenin varyans üzerindeki katkısının hesaplanması:

| Kaynak | Kareler Toplamı (SS) | df | Ortalama Kare (MS) | F-değeri | p-değeri |
|--------|---------------------|----|--------------------|----------|----------|
| Parametre A | SSA | k-1 | MSA | MSA/MSE | < 0.05 |
| Parametre B | SSB | k-1 | MSB | MSB/MSE | < 0.05 |
| Hata (Error) | SSE | N-k | MSE | — | — |
| **Toplam** | **SST** | **N-1** | — | — | — |

**Karar kuralı:** p < 0.05 ise parametre istatistiksel olarak anlamlı.

### 4.2 Taguchi L8 Dizayn Matrisi (Ornek)

| Deney No. | A | B | C | S/N | Ortalama |
|-----------|---|---|---|-----|----------|
| 1 | 1 | 1 | 1 | — | — |
| 2 | 1 | 2 | 2 | — | — |
| ... | | | | | |
| 8 | 2 | 2 | 1 | — | — |

---

## 5. Beklenen Bulgular

### 5.1 Ön Çalışma Sonuçları

Tek run'lık hızlı test (seed=42):

| Algoritma | Best | Gap | Çalışma Süresi |
|-----------|------|-----|----------------|
| 2-opt | 433.0 | 1.64% | 2.7 sn |
| 3-opt | 451.0 | 5.87% | 16.6 sn |
| Or-opt | 475.0 | 11.5% | 2.9 sn |

**Not:** Yukarıdaki değerler optimum olmayan parametrelerle alınmıştır.

### 5.2 Beklenen Optimum Parametreler

#### 2-opt İçin Beklenen Sonuçlar
- **En iyi kombinasyon:** `max_iterations=2000`, `first_improvement=True`, `num_starts=10`
- **Beklenen ortalama:** ~428-430 (%0.5-1.0 gap)
- **Ana etkiler:** `num_starts` > `max_iterations` > `first_improvement`

#### Or-opt İçin Beklenen Sonuçlar
- **En iyi kombinasyon:** `max_iterations=1000`, `max_segment_size=3`, `num_starts=5`
- **Beklenen ortalama:** ~430-434 (%1.0-1.9 gap)
- **Ana etkiler:** `num_starts` > `max_segment_size` > `max_iterations`

#### GA İçin Beklenen Sonuçlar
- **En iyi kombinasyon:** `pop=80`, `gen=200`, `cross=0.85`, `mut=0.15`, `elite=2`
- **Beklenen ortalama:** ~445-455 (%4.5-6.8 gap)

#### PSO İçin Beklenen Sonuçlar
- **En iyi kombinasyon:** `swarm=40`, `iter=200`, `w=0.729`, `c1=c2=1.49`
- **Beklenen ortalama:** ~440-450 (%3.3-5.6 gap)

---

## 6. Sonuçların Yorumlanması

### 6.1 Parametre Hassasiyet Grafiği

Her parametre için farklı seviyelerin ortalama S/N değerlerinin çizilmesi.

```
S/N (dB)
  |        ●
  |      /   \
  |    /       \    <--- max_iterations etkisi
  |  /           \
  +------------------
    Level 1   Level 2   Level 3
```

### 6.2 Agırlıklandırılmış Seçim

Her parametrenin ANOVA F-değerine göre agırlığı:

$$ w_i = \frac{F_i}{\sum F_j} $$

---

## 7. Kısıtlar ve Öneriler

1. **Çalışma süresi:** 3-opt için 30 run tek problemde ~45 dk sürmektedir
2. **Çoklu problem:** Sonuçlar sadece `eil51` için geçerlidir; farklı problem tiplerinde farklı optimum parametreler bulunabilir
3. **Yinelenme sayısı:** 10 çalıştırma istatistiksel güç için minimum düzeydedir; 30 önerilir
4. **Önerilen genişletme:** Latin Hypercube Sampling (LHS) ile 100+ kombinasyonun rasgele taraması

---

## Kaynaklar

1. Montgomery, D. C. (2017). *Design and Analysis of Experiments*, 10th ed. Wiley.
2. Phadke, M. S. (1989). *Quality Engineering Using Robust Design*. Prentice Hall.
3. Eiben, A. E., & Smit, S. K. (2011). Parameter tuning for configuring and analyzing evolutionary algorithms. *Swarm and Evolutionary Computation*, 1(1), 19-31.

---

**Hazırlayan:** Bildiri 2026 Araştırma Ekibi  
**Tarih:** 23 Nisan 2026  
**Deney Yazılımı:** `param_opt_design.py` (otomatik çalıştırılabilir)
