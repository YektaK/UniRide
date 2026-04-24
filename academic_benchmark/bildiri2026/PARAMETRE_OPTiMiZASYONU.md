# Parametre Optimizasyonu Önerileri - Bildiri 2026

Bu döküman, TSPLIB benchmark ve SBRP uygulaması için algoritma parametrelerini optimize etmek üzere önerilen deney tasarımı yaklaşımlarını açıklar.

## 1. Genel Yaklaşım: İki Aşamalı Optimizasyon

### Aşama 1: TSPLIB Üzerinde Parametre Taraması (Offline)
- **Amaç:** Her algoritma için en iyi parametre setini bulmak
- **Yöntem:** Grid Search veya Latin Hypercube Sampling (LHS)
- **Metrik:** Gap (%) = (Bulunan - Optimal) / Optimal × 100
- **Sonuç:** Her algoritma için "en iyi" (default) parametre seti

### Aşama 2: 29 Öğrenci Senaryosu Üzerinde Karşılaştırma (Online)
- **Amaç:** Gerçek veri üzerinde algoritmaları karşılaştırmak
- **Yöntem:** Aşama 1'de bulunan en iyi parametrelerle 30 bağımsız çalıştırma
- **Metrik:** Toplam süre (dakika) ve hesaplama süresi (ms)

---

## 2. Algoritma Bazlı Parametre Taraması

### 2.1 Genetik Algoritma (GA)

| Parametre | Başlangıç | Aralık | Adım | Deney Sayısı |
|-----------|-----------|--------|------|--------------|
| `population_size` | 50 | 20-200 | 20 | 10 |
| `generations` | 300 | 100-1000 | 100 | 10 |
| `crossover_rate` | 0.85 | 0.5-1.0 | 0.1 | 6 |
| `mutation_rate` | 0.15 | 0.01-0.3 | 0.05 | 6 |
| `elite_count` | 2 | 1-10 | 1 | 10 |
| `tournament_size` | 3 | 2-10 | 1 | 9 |

**Önerilen Deney Sayısı:** 50 * 3 problemlerde = 150 deney
**Değerlendirme:** Her parametre kombinasyonu 3 kere çalıştırılır, ortalama gap'e göre sıralanır.

**Optimize Edilmiş Parametreler (Beklenen):**
- `population_size`: 100
- `generations`: 300-500
- `crossover_rate`: 0.80-0.90
- `mutation_rate`: 0.10-0.20
- `elite_count`: 2-3
- `tournament_size`: 3-5

### 2.2 Parçacık Sürü Optimizasyonu (PSO)

| Parametre | Başlangıç | Aralık | Önem |
|-----------|-----------|--------|------|
| `swarm_size` | 50 | 20-100 | Yüksek |
| `max_iterations` | 300 | 100-1000 | Yüksek |
| `inertia_weight` | 0.729 | 0.4-0.9 | Çok Yüksek (Clerc) |
| `cognitive_coeff` | 1.49445 | 0.5-2.5 | Orta |
| `social_coeff` | 1.49445 | 0.5-2.5 | Orta |

**Önemli Not:** `inertia_weight` = 0.729 ve `c1=c2=1.49445` Clerc tarafından önerilen daraltma (constriction) faktörüdür. Bu değerler genellikle en iyidir.

**Önerilen Alternatif Aralıklar:**
- `inertia_weight`: [0.6, 0.7, 0.729, 0.8, 0.9]
- `cognitive_coeff + social_coeff` toplamı sabit tutularak `w = 1.0, c1 = 1.5, c2 = 1.5` gibi varyasyonlar test edilebilir.

### 2.3 3-opt Yerel Arama

| Parametre | Öneri |
|-----------|-------|
| `max_iterations` | 500-1000 (her iterasyon O(n³)) |
| `first_improvement` | `False` (en iyi iyileşmeyi bekle) |
| `multi_start` | `True` (5-10 başlangıç) |

**Parametre Taraması İhtiyacı:** Düşük. Çünkü 3-opt determinantistiktir (seed belirse bile ilk tur rastgele).

### 2.4 Or-opt Yerel Arama

| Parametre | Öneri |
|-----------|-------|
| `max_iterations` | 500-1000 |
| `max_segment_size` | 3 (1, 2 ve 3 düğüm taşıma) |
| `multi_start` | `True` (5-10 başlangıç) |

**Parametre Taraması İhtiyacı:** Düşük. Segment boyutu 3 sabit kalabilir.

---

## 3. Deney Tasarımı Önerileri

### 3.1 Grid Search (Kapsamlı Ama Pahalı)
```python
# GA için örnek kombinasyon sayısı
combinations = (
    10 *  # population_size
    10 *  # generations
    6 *   # crossover_rate
    6 *   # mutation_rate
    5     # tournament_size
) = 18,000 kombinasyon

# Her biri 3 kere çalıştırılırsa = 54,000 deney
```
**Uygun Değil:** Çok fazla. Daha akıllı arama gerekli.

### 3.2 Latin Hypercube Sampling (LHS) - Önerilen
```python
# 50 rastgele ancak düzgün dağılmış kombinasyon
# Her biri 3 kere çalıştırılırsa = 150 deney
```
**Faydası:** Daha az deneyle parametre uzayını kapsar.

### 3.3 İki Seviyeli Fraktör analizi (Fraktionel Faktoryel)
- Her parametre için 2 seviye (düşük/yüksek)
- En etkili parametreler belirlenir
- Bu parametreler detaylı taranır

**GA için Örnek:**
| Parametre | Düşük (-) | Yüksek (+) |
|-----------|-----------|------------|
| Popülasyon | 50 | 150 |
| Jenerasyon | 200 | 500 |
| Crossover | 0.7 | 0.9 |
| Mutation | 0.05 | 0.20 |

**Toplam Kombinasyon:** 2^4 = 16 kombinasyon × 3 tekrar = 48 deney

### 3.4 Taguchi Dizaynı (Önerilen - Denge)
- Doğrusal varyans analizi ile en etkili parametreleri bulmayı hedefler.
- Daha az deneyle daha iyi sonuç.
- Taguchi L16 (16 deney) veya L8 (8 deney) orthogonal dizaynları.

**Örnek L8 Dizaynı (7 faktör, 2 seviye):**
```
| Deney | Pop | Gen | Cross | Mut | Elite | Tour | Multi |
|-------|-----|-----|-------|-----|-------|------|-------|
| 1     | -   | -   | -     | -   | -     | -    | -     |
| 2     | -   | -   | -     | +   | +     | +    | +     |
| 3     | -   | +   | +     | -   | -     | +    | +     |
| ...   | ... | ... | ...   | ... | ...   | ...  | ...   |
| 8     | +   | +   | +     | +   | +     | +    | +     |
```

**Toplam:** 8 kombinasyon × 3 tekrar = 24 deney

---

## 4. Değerlendirme Metrikleri (Response Variables)

Her parametre kombinasyonu için:

1. **Gap Ortalaması:** (Bulunan - Optimal) / Optimal × 100
2. **Gap Standart Sapması:** Tekrarlanabilirlik
3. **Hesaplama Süresi:** Milisaniye cinsinden
4. **Başarı Oranı:** %5 gap altında kaç kez? (1/0)

**Çok Amaçlı Optimizasyon:**
- Gap ve süre birlikte düşürülmeye çalışılır.
- Pareto ön cephesi bulunur.

---

## 5. Uygulama Akışı

```
┌─────────────────────────────────────────┐
│ 1. TSPLIB Problemlerini Seç             │
│    - eil51, berlin52, st70, eil76       │
│    - Optimal değerleri bilinen          │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ 2. Parametre Taraması Yap               │
│    - Taguchi L8 veya LHS                │
│    - Her kombinasyonu 3 kere çalıştır   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ 3. En İyi Parametreleri Belirle         │
│    - En düşük ortalama gap              │
│    - Makul hesaplama süresi             │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ 4. 30 Bağımsız Çalışma Yap              │
│    - En iyi parametrelerle              │
│    - İstatistiksel analiz için          │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ 5. 29 Öğrenci Verisi Üzerinde Uygula    │
│    - Time matrix kullan                 │
│    - 30 bağımsız çalışma                │
│    - Sonuçları grafikleştir             │
└─────────────────────────────────────────┘
```

---

## 6. Python Kod Örneği: Taguchi L8 Parametre Taraması

Bu örnek, GA için Taguchi L8 dizaynıyla parametre taraması yapar.

```python
import itertools
from core import GAOptimizer

# Taguchi L8 Orthogonal Array for 7 factors at 2 levels
L8 = [
    [-1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, +1, +1, +1, +1],
    [-1, +1, +1, -1, -1, +1, +1],
    [-1, +1, +1, +1, +1, -1, -1],
    [+1, -1, +1, -1, +1, -1, +1],
    [+1, -1, +1, +1, -1, +1, -1],
    [+1, +1, -1, -1, +1, +1, -1],
    [+1, +1, -1, +1, -1, -1, +1],
]

# Factor definitions
factors = {
    "population_size": (50, 150),   # -1, +1
    "generations": (200, 500),
    "crossover_rate": (0.7, 0.9),
    "mutation_rate": (0.05, 0.20),
    "elite_count": (1, 5),
    "tournament_size": (2, 7),
    "multi_start": (False, True),
}

for exp_idx, row in enumerate(L8):
    params = {}
    for fidx, (fname, (low, high)) in enumerate(factors.items()):
        level = row[fidx]
        params[fname] = low if level == -1 else high
    
    print(f"\nExperiment {exp_idx + 1}: {params}")
    # Run GA with these params on TSPLIB problems...
```

---

## 7. Bulgularınızın Bildiride Sunumu

Parametre optimizasyonu sonuçlarını şu şekilde sunabilirsiniz:

### Tablo 1: Parametre Taraması Sonuçları (Örnek)
| Parametre Seti | Gap Avg (%) | Gap Std (%) | Time Avg (ms) | Time Std (ms) |
|----------------|-------------|-------------|---------------|---------------|
| Default | 2.45 | 0.32 | 120 | 15 |
| Set 1 | 1.89 | 0.28 | 145 | 20 |
| Set 2 | 2.10 | 0.30 | 110 | 12 |
| **Optimal** | **1.72** | **0.25** | **135** | **18** |

### Tablo 2: ANOVA Sonuçları (Örnek)
| Faktör | F-değeri | p-değeri | Etki | Önem |
|--------|----------|----------|------|------|
| Popülasyon Boyutu | 15.3 | <0.001 | **Yüksek** | *** |
| Jenerasyon Sayısı | 8.7 | 0.003 | **Yüksek** | ** |
| Crossover Oranı | 3.2 | 0.045 | Orta | * |
| Mutation Oranı | 2.1 | 0.089 | Düşük | - |

### Şekil: Parametre Etki Grafikleri
- Main Effect Plot (Ana etki grafikleri)
- Interaction Plot (Etkileşim grafikleri)

---

## 8. Öneriler

1. **Hızlı Sonuç İçin:** Taguchi L8 ile başlayın (8 kombinasyon × 3 tekrar = 24 deney)
2. **Daha Derinlemesine:** LHS ile 50 kombinasyon deneyin
3. **Multi-Start 3-opt ve Or-opt:** `num_starts=5-10` yeterli olacaktır
4. **GA ve PSO:** `max_no_improvement` ile erken durdurma ekleyin
5. **Paralellik:** NumPy ve ThreadPoolExecutor ile hızlandırılabilir

---

**Hazırlayan:** Bildiri 2026 Ekibi  
**Güncelleme:** 23 Nisan 2026