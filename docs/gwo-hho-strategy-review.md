# GWO ve HHO Strategy Versiyonları — Akademik Değerlendirme

**Tarih:** 2026-04-30
**Kapsam:** `optimizer_api/strategies/gwo_strategy.py`, `optimizer_api/strategies/hho_strategy.py`
**Referanslar:**
- Mirjalili, S., Mirjalili, S. M., & Lewis, A. (2014). Grey wolf optimizer. *Advances in Engineering Software*, 69, 46-61.
- Heidari, A. A., et al. (2019). Harris hawks optimization: Algorithm and applications. *Future Generation Computer Systems*, 97, 849-872.

---

## 1. GWO Strategy (`gwo_strategy.py`) — Bulgular

### 1.1 Doğru Uygulanan Kısımlar

| Özellik | Satır | Durum |
|---------|-------|-------|
| α, β, δ hiyerarşisi | 218-221 | ✅ |
| `a` parametresi (2→0 lineer) | 228 | ✅ |
| Keşif-sömürü ayrımı (`exploration_rate * a`) | 234 | ✅ |
| Local search iyileştirme (2-opt) | 286-288 | ✅ |
| Erken durdurma (`max_no_improvement`) | 269 | ✅ |

### 1.2 Eksiklikler ve Hatalar

#### EKSİK 1: `A` ve `C` Vektörleri (KRİTİK)

**Mevcut kod (satır 108-128):**
```python
def _get_difference_vector(self, leader, wolf, a):
    swaps = []
    for i in range(n):
        if wolf[i] != leader[i]:
            j = wolf.index(leader[i])
            if self.rng.random() < a / 2:  # ❌ Sabit olasılık
                swaps.append((i, j))
    return swaps
```

**Orijinal formül (Mirjalili Eq. 3.1-3.2):**
```
A = 2·a·r₁ - a    (r₁ ∈ [0,1])
C = 2·r₂           (r₂ ∈ [0,1])
D = |C·X_p(t) - X(t)|
X(t+1) = X_p(t) - A·D
```

**Sorun:** `A` vektörü yok. `|A| > 1` keşif, `|A| < 1` sömürü mekanizması ihmal ediliyor. Mevcut kod sadece `a / 2` olasılığıyla swap yapıyor.

**Etki:** Keşif-sömürü dengesi zayıf. Algoritma erken yakınsama yapabilir.

#### EKSİK 2: Dinamik Ağırlıklar (YÜKSEK)

**Mevcut kod (satır 163-179):**
```python
# Alpha has highest weight
for swap in alpha_swaps:
    if self.rng.random() < 0.7:  # ❌ Sabit
        all_swaps.append(swap)
# Beta has medium weight
for swap in beta_swaps:
    if self.rng.random() < 0.5:  # ❌ Sabit
        all_swaps.append(swap)
# Delta has lower weight
for swap in delta_swaps:
    if self.rng.random() < 0.3:  # ❌ Sabit
        all_swaps.append(swap)
```

**Orijinal formül:** Ağırlıklar `A` ve `C` vektörlerine bağlı olmalı, sabit değil.

#### EKSİK 3: Çevreleme Mekanizması (ORTA)

**Mevcut kod:** Swap tabanlı diferans vektörü kullanıyor.
**Orijinal:** `X(t+1) = X_p - A·|C·X_p - X(t)|` formülü ile avın etrafında spiral hareket.

TSP adaptasyonunda swap tabanlı yaklaşım kabul edilebilir (Panwar & Deep, 2021), ama `A` ve `C` ile parametrize edilmeli.

### 1.3 Önerilen Düzeltmeler

```python
def _update_position(self, wolf, alpha, beta, delta, a):
    new_position = wolf.position.copy()
    for leader in [alpha, beta, delta]:
        r1 = self.rng.random()
        r2 = self.rng.random()
        A = 2 * a * r1 - a
        C = 2 * r2
        if abs(A) > 1:
            # Keşif: rastgele pak üyesine doğru
            random_wolf = self.rng.choice(self.pack)
            strength = min(0.9, abs(A) * 0.3)
        else:
            # Sömürü: liderlere doğru
            strength = max(0.1, abs(C) * 0.5)
        swaps = self._get_difference_vector(leader.position, new_position, strength)
        new_position = self._apply_swaps(new_position, swaps)
    return new_position
```

---

## 2. HHO Strategy (`hho_strategy.py`) — Bulgular

### 2.1 Doğru Uygulanan Kısımlar

| Özellik | Satır | Durum |
|---------|-------|-------|
| `E₀` rastgele [-1,1] | 305 | ✅ |
| `E = 2·E₀·(1-t/T)` | 306 | ✅ |
| 4 strateji (soft/hard besiege, dives) | 173-267 | ✅ |
| Lévy flight | 114-140 | ✅ |
| `r` kaçış olasılığı | 312 | ✅ |
| Keşif-sömürü ayrımı (`|E|≥1` vs `|E|<1`) | 315 | ✅ |
| Local search iyileştirme | 387-389 | ✅ |

### 2.2 Eksiklikler ve Hatalar

#### EKSİK 1: Lévy Flight Skalası (DÜŞÜK)

**Mevcut kod (satır 126-127):**
```python
beta = 1.5
sigma = (math.gamma(1 + beta) * math.sin(math.pi * beta / 2) /
         (math.gamma((1 + beta) / 2) * beta * 2 ** ((beta - 1) / 2))) ** (1 / beta)
```

**Sorun:** `beta = 1.5` sabit. Orijinal makalede β ∈ [1, 2] aralığı öneriliyor. Ayrıca `scale` parametresi hardcode (`0.5`).

**Etki:** Düşük. Lévy flight mevcut ama parametrize edilmemiş.

#### EKSİK 2: Keşif Fazında Rastgele Konumlanma (ORTA)

**Mevcut kod (satır 315-324):**
```python
if abs(E) >= 1:
    if self.rng.random() < 0.5:
        # Perch near prey
        intensity = self.rng.random()
        swaps = self._get_difference_swaps(hawk.position, prey.position, intensity)
        new_position = self._apply_swaps(hawk.position, swaps)
    else:
        # Random perch (Lévy flight)
        new_position = self._levvy_flight(hawk.position)
```

**Orijinal (Heidari Eq. 4.2-4.3):**
```
X(t+1) = X_rand(t) - r₁·|X_rand(t) - 2·r₂·X(t)|
```
veya
```
X(t+1) = (X_best(t) - X_m(t)) - r₃·(LB + r₄·(UB - LB))
```

**Sorun:** Keşif fazında `X_rand` (rastgele şahin) kullanılıyor ama formül basitleştirilmiş. Orijinalde iki farklı keşif stratejisi var.

#### EKSİK 3: Soft/Hard Besiege Ayrımında J Parametresi (DÜŞÜK)

**Mevcut kod (satır 185):**
```python
J = 2 * (1 - self.rng.random())  # J ∈ [0, 2]
```

**Orijinal (Heidari Eq. 4.5):**
```
J = 2 * (1 - r₅)    (r₅ ∈ [0,1])
```

**Sorun:** `J` formülü doğru uygulanmış ama `r₅` yerine `self.rng.random()` kullanılıyor — matematiksel olarak eşdeğer, sorun yok.

#### EKSİK 4: Hard Besiege + Dives'da Ortalama Pozisyon (DÜŞÜK)

**Mevcut kod (satır 259-267):**
```python
def _hard_besiege_with_dives(self, hawk, prey, escape_energy, ...):
    mean_intensity = abs(escape_energy)
    swaps = self._get_difference_swaps(hawk.position, prey.position, mean_intensity)
    candidate = self._apply_swaps(hawk.position, swaps)
    candidate = self._levvy_flight(candidate, scale=0.2)
    return candidate
```

**Orijinal (Heidari Eq. 4.7):**
```
X(t+1) = (Prey - E·|Prey - X(t)|) + Lévy(D)
```
veya
```
Y = Prey - E·|J·Prey - X(t)|
Z = Y + S·LF(D)  (S: rastgele vektör, LF: Lévy flight)
```

**Sorun:** `S·LF(D)` rastgele vektör eksik. Mevcut kod sadece Lévy flight swap uyguluyor.

### 2.3 Akademik Literatür Karşılaştırması

| Özellik | Orijinal (2019) | Mevcut Kod | Panwar D-GWO (2021) | Gharehchopogh (2022) |
|---------|-----------------|------------|---------------------|----------------------|
| E₀ rastgele | ✅ | ✅ | — | ✅ |
| 4 strateji | ✅ | ✅ | — | ✅ |
| Lévy flight | ✅ | ✅ | — | ✅ |
| 2-opt local search | ❌ | ✅ | ✅ | ✅ |
| Keşif formülü | Eq. 4.2-4.3 | Basitleştirilmiş | — | Eq. 4.2-4.3 |
| r ayrımı | ✅ | ✅ | — | ✅ |

### 2.4 Önerilen Düzeltmeler

1. **Keşif formülünü iyileştir** — `X_rand` tabanlı iki farklı strateji ekle
2. **`beta` parametresini** [1,2] aralığında yap
3. **Hard besiege + dives'da** `S·LF(D)` rastgele vektör ekle
4. **`scale` parametresini** config'den alınabilir yap

---

## 3. Genel Değerlendirme

### GWO Strategy: ORTA SEVIYE — 6/10

- Temel yapı doğru (α, β, δ + `a` parametresi)
- `A` ve `C` vektörleri eksik → keşif-sömürü dengesi zayıf
- Sabit ağırlıklar dinamik formüllerin yerini almış
- Swap tabanlı TSP adaptasyonu kabul edilebilir

### HHO Strategy: İYİ SEVIYE — 8/10

- Tüm 4 strateji mevcut
- Lévy flight doğru implemente edilmiş
- Keşif formülü basitleştirilmiş ama fonksiyonel
- `E₀` ve `r` parametreleri doğru
- Küçük iyileştirmeler yapılabilir ama akademik olarak kabul edilebilir seviyede

### Benchmark Versiyonları (düzeltilmiş): 9/10

- `_run_gwo`: `a`, `A`, `C` vektörleri, dinamik strength eklendi
- `_run_hho`: 4 strateji, Lévy flight, `E₀`, `r` parametreleri eklendi
- Her iki versiyon da orijinal makalelere uygun

---

## 4. Kaynakça

1. Mirjalili, S., Mirjalili, S. M., & Lewis, A. (2014). Grey wolf optimizer. *Advances in Engineering Software*, 69, 46-61.
2. Heidari, A. A., Mirjalili, S., Faris, H., Aljarah, I., Mafarja, M., & Chen, H. (2019). Harris hawks optimization: Algorithm and applications. *Future Generation Computer Systems*, 97, 849-872.
3. Panwar, K., & Deep, K. (2021). Discrete Grey Wolf Optimizer for symmetric TSP. *Applied Soft Computing*, 107, 107414.
4. Gharehchopogh, F. S., & Abdollahzadeh, B. (2022). An efficient HHO for solving TSP. *Cluster Computing*, 25, 2729-2747.
