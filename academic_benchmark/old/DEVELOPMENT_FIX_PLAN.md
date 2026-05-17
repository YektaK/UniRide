# Master Numba vs Bildiri2026 Uyumlastirma — Gelisme ve Duzeltme Plani

**Tarih:** 2026-05-13  
**Kapsam:** `academic_benchmark/` + `optimizer_api/tests/run_interactive_benchmark_v2_numba.py`  
**Amac:** Master Numba motorunu Bildiri2026'nin memetic hybrid yapisina uyumlastirarak akademik karsilastirma gecerliligini saglamak  
**Durum:** HAZIR — Uygulama bekleniyor

---

## 0. Onceden Duzeltilmis Sorunlar (2026-05-09)

| # | Sorun | Durum | Kanit |
|---|-------|-------|-------|
| I-01 | SOTA cache-resume seed tekrari | ✅ DUZELTILDI | `master_sota_engine.py:712` |
| I-02 | Raw vs Aggregate cikti karisimi | ✅ DUZELTILDI | `result_type` alani eklendi |
| I-07 | nb_three_opt semantic stub | ✅ DUZELTILDI | `numba_accel.py:198` |
| I-08 | MultiLayerLS iteratif yakinsama | ✅ DUZELTILDI | `ls_engine.py:218-234` |
| I-09 | 3-opt/swap Numba hizlandirma | ✅ DUZELTILDI | `numba_accel.py:365-401` |
| I-10 | P-AOEA mutasyon on-ek onyargisi | ✅ DUZELTILDI | `paoea_tsp.py:207` |
| I-04 | R2DMA rotasyon duyarliligi | ✅ DUZELTILDI | `r2dma_tsp.py:103-118` |
| I-05 | Numba loader harmonizasyonu | ✅ DUZELTILDI | `master_numba_engine.py:268` |

**Kalan kritik sorun: Master Numba motorundaki meta-sezgisellerin memetic hybrid yapisi eksik.**

---

## 1. SORUN TANIMI

### 1.1 Kok Neden Ozeti

Bildiri2026 solver'lari ayni parametrelerle calistirildiginda Master Numba solver'larindan %20-40 daha iyi sonuc veriyor. Bunun 5 kok nedeni tespit edilmistir:

| # | Kok Neden | Etki Orani | Dosya |
|---|-----------|-----------|-------|
| K1 | Populasyon baslatmada 2-opt eksik | %40-60 | `run_interactive_benchmark_v2_numba.py` |
| K2 | Final polishing cok zayif (iter=5 vs 300) | %15-25 | `run_interactive_benchmark_v2_numba.py` |
| K3 | PSO diversity re-init eksik | %10-20 | `run_interactive_benchmark_v2_numba.py` |
| K4 | Profile sistemi parametreleri bozuyor | %5-15 | `run_interactive_benchmark_v2_numba.py` |
| K5 | Dict-based mesafe matrisi (performans) | %5-10 | `run_interactive_benchmark_v2_numba.py` |

### 1.2 Etkilenen Dosyalar

```
optimizer_api/tests/run_interactive_benchmark_v2_numba.py  ← ANA HEDEF (K1-K5)
academic_benchmark/master_numba_engine.py                  ← DoE parametre uzayi + pipeline
academic_benchmark/bildiri2026/core/numba_accel.py         ← Numba kernel'lar (referans)
```

---

## 2. GOREVLER

### GOREV 1: GA Memetic Initialization (K1 — En Yuksek Etki)

**Dosya:** `optimizer_api/tests/run_interactive_benchmark_v2_numba.py`  
**Fonksiyon:** `_run_ga()` (satir 481-512)  
**Oncelik:** P0  
**Etki:** %40-60 GAP iyilestirmesi

#### Mevcut Durum
```python
# SATIR 488-492: Saf rastgele populasyon
for _ in range(pop_size):
    candidate = initial_route[:]
    rng.shuffle(candidate)
    population.append(candidate)
# ❌ 2-opt YOK
```

#### Hedef Durum
```python
# Her bireye 2-opt uygula (bildiri2026 ile ayni)
for _ in range(pop_size):
    candidate = initial_route[:]
    rng.shuffle(candidate)
    # ✅ Memetic 2-opt initialization
    candidate = _apply_2opt_to_route(candidate, duration_func, max_iter=10)
    population.append(candidate)
```

#### Uygulama Adimlari

1. **Yeni yardimci fonksiyon ekle** (satir ~475):
```python
def _apply_2opt_to_route(
    route: List[str],
    duration_func: Callable[[List[str]], float],
    max_iter: int = 10,
) -> List[str]:
    """Memetic initialization icin 2-opt iyilestirme."""
    from optimizer_api.utils.local_search_numba import apply_local_search, LocalSearchType
    try:
        improved, _ = apply_local_search(
            route, duration_func, LocalSearchType.TWO_OPT,
            max_iterations=max_iter,
        )
        return improved
    except Exception:
        return route
```

2. **`_run_ga()` fonksiyonunu guncelle** (satir 488-492):
   - Populasyon baslatmada her bireye `_apply_2opt_to_route(candidate, duration_func, max_iter=10)` uygula
   - `population[0]` icin de ayni islemi uygula

3. **Test:** berlin52 uzerinde GA calistir, bildiri2026 GA ile karsilastir

---

### GOREV 2: PSO Memetic Initialization (K1)

**Dosya:** `optimizer_api/tests/run_interactive_benchmark_v2_numba.py`  
**Fonksiyon:** `_run_pso()` (satir 535-574)  
**Oncelik:** P0  
**Etki:** %40-60 GAP iyilestirmesi

#### Mevcut Durum
```python
# SATIR 544-547: Saf rastgele swarm
for _ in range(swarm_size):
    route = initial_route[:]
    rng.shuffle(route)
    swarm.append({"route": route, ...})
# ❌ 2-opt YOK
```

#### Hedef Durum
```python
for _ in range(swarm_size):
    route = initial_route[:]
    rng.shuffle(route)
    # ✅ Memetic 2-opt initialization (iter=30)
    route = _apply_2opt_to_route(route, duration_func, max_iter=30)
    swarm.append({"route": route, ...})
```

#### Uygulama Adimlari

1. `_run_pso()` baslangic dongusunde her parcaciga `_apply_2opt_to_route(route, duration_func, max_iter=30)` uygula

---

### GOREV 3: PSO Diversity Re-initialization (K3)

**Dosya:** `optimizer_api/tests/run_interactive_benchmark_v2_numba.py`  
**Fonksiyon:** `_run_pso()` (satir 556-572)  
**Oncelik:** P0  
**Etki:** %10-20 GAP iyilestirmesi

#### Mevcut Durum
```python
# SATIR 556-572: Dongu boyunca hic re-init yok
for _ in range(iterations):
    for particle in swarm:
        # ... pozisyon guncelleme ...
    gbest = min(swarm, key=lambda p: p["best_cost"])["best"][:]
# ❌ Re-initialization YOK
```

#### Hedef Durum
```python
reinit_interval = int(params.get("reinit_interval", 50))

for it in range(iterations):
    for particle in swarm:
        # ... pozisyon guncelleme ...
    gbest = min(swarm, key=lambda p: p["best_cost"])["best"][:]

    # ✅ Periyodik re-initialization (her 50 iterasyonda)
    if it > 0 and it % reinit_interval == 0:
        swarm = _reinit_swarm_pso(swarm, gbest, rng, duration_func)
```

#### Yeni Yardimci Fonksiyon
```python
def _reinit_swarm_pso(
    swarm: List[Dict], global_best: List[str],
    rng: random.Random, duration_func: Callable,
) -> List[Dict]:
    """PSO surusunu cesitlilik icin yeniden baslatir."""
    new_swarm = []
    for p in swarm:
        if rng.random() < 0.9:
            pos = p["best"][:]
            for _ in range(rng.randint(1, 3)):
                i, j = rng.sample(range(len(pos)), 2)
                pos[i], pos[j] = pos[j], pos[i]
        else:
            pos = global_best[:]
            rng.shuffle(pos)
        # Re-init sonrasi 2-opt
        pos = _apply_2opt_to_route(pos, duration_func, max_iter=30)
        cost = _route_cost(pos, duration_func)
        new_swarm.append({
            "route": pos, "best": p["best"][:],
            "best_cost": p["best_cost"],
        })
        if cost < new_swarm[-1]["best_cost"]:
            new_swarm[-1]["best"] = pos[:]
            new_swarm[-1]["best_cost"] = cost
    return new_swarm
```

---

### GOREV 4: Final Polishing Gucu Artirimi (K2)

**Dosya:** `optimizer_api/tests/run_interactive_benchmark_v2_numba.py`  
**Fonksiyon:** `_refine_route()` (satir 156-175)  
**Oncelik:** P0  
**Etki:** %15-25 GAP iyilestirmesi

#### Mevcut Durum
```python
# SATIR 161-162: quality_first profilinde bile cok zayif
ls_type = LocalSearchType.HYBRID
max_iterations = 5  # ❌ Cok dusuk
```

#### Hedef Durum
```python
if profile == "baseline":
    ls_type = LocalSearchType.TWO_OPT
    max_iterations = 50
else:
    ls_type = LocalSearchType.TWO_OPT  # HYBRID yerine 2-opt (bildiri2026 ile uyumlu)
    max_iterations = 300               # ✅ bildiri2026 ile ayni
```

#### Uygulama Adimlari

1. `_refine_route()` fonksiyonundaki `max_iterations` degerlerini guncelle:
   - `baseline`: 2 → 50
   - `quality_first`: 5 → 300
2. `ls_type` degerini `HYBRID` yerine `TWO_OPT` yap (bildiri2026 ile uyumlu)

---

### GOREV 5: Profile Bypass Modu (K4)

**Dosya:** `optimizer_api/tests/run_interactive_benchmark_v2_numba.py`  
**Fonksiyon:** `_tune_meta_params()` (satir 94-153)  
**Oncelik:** P1  
**Etki:** %5-15 GAP iyilestirmesi

#### Mevcut Durum
```python
# SATIR 108-112: quality_first profilinde parametreleri yeniden olcekliyor
if profile == "quality_first":
    pop_size = int(pop_size * 0.7)        # %30 kucultuyor
    generations = int(generations * 1.15)  # %15 artiriyor
```

#### Hedef Durum

Yeni bir profil ekle: `"bildiri_aligned"` — parametreleri hic degistirmez.

```python
VALID_BENCHMARK_PROFILES = {"baseline", "quality_first", "bildiri_aligned"}

# _tune_meta_params() icinde:
if profile == "bildiri_aligned":
    return tuned  # Parametreleri oldugu gibi dondur
```

#### Uygulama Adimlari

1. `VALID_BENCHMARK_PROFILES` setine `"bildiri_aligned"` ekle
2. `_tune_meta_params()` fonksiyonunun basina kontrol ekle:
   - `profile == "bildiri_aligned"` ise `tuned`'i oldugu gibi dondur
3. `_run_meta_heuristic()` cagrisinda profil `"bildiri_aligned"` kullanilabilir

---

### GOREV 6: DoE Parametre Uzayi Uyumlulugu

**Dosya:** `academic_benchmark/master_numba_engine.py`  
**Fonksiyon:** `_build_numba_parameter_space()` (satir 352-382)  
**Oncelik:** P1  
**Etki:** DoE tuning sonuclarinin bildiri2026 ile karsilastirilabilir olmasini saglar

#### Mevcut Durum vs Bildiri2026

| Parametre | Mevcut DoE Uzayi | Bildiri2026 Degeri | Uyumsuzluk |
|-----------|-----------------|-------------------|-----------|
| GA `pop_size` | [80, 120, 150] | 100 | ✅ Kapsiyor |
| GA `generations` | [250, 350, 500] | 500 | ✅ Kapsiyor |
| GA `mutation_rate` | [0.08, 0.12, 0.16] | 0.15 | ✅ Kapsiyor |
| GA `elite_size` | [4, 6, 8] | 2 | ❌ Kapsamiyor (min=4) |
| GA `crossover_rate` | YOK | 0.85 | ❌ EKSIK |
| PSO `swarm_size` | [50, 80, 120] | 50 | ✅ Kapsiyor |
| PSO `iterations` | [200, 300, 450] | 500 | ❌ Kapsamiyor (max=450) |
| PSO `reinit_interval` | YOK | 50 | ❌ EKSIK |
| GWO `pack_size` | [50, 80, 120] | N/A | N/A (bildiri2026'da GWO yok) |
| HHO `hawks` | [50, 80, 120] | N/A | N/A (bildiri2026'da HHO yok) |

#### Uygulama Adimlari

1. GA parametre uzayini guncelle:
```python
if name == "GA":
    return {
        "pop_size": [60, 80, 100, 120],
        "generations": [300, 500, 700],
        "mutation_rate": [0.10, 0.15, 0.18],
        "elite_size": [2, 4, 6],
        "crossover_rate": [0.75, 0.85, 0.95],  # ✅ YENI
    }
```

2. PSO parametre uzayini guncelle:
```python
if name == "PSO":
    return {
        "swarm_size": [50, 80, 100],
        "iterations": [300, 500, 700],
        "w": [0.65, 0.72, 0.80],
        "c1": [1.4, 1.49, 1.6],
        "c2": [1.4, 1.49, 1.6],
        "reinit_interval": [30, 50, 80],  # ✅ YENI
    }
```

---

### GOREV 7: GWO ve HHO Memetic Init (K1 — Genisletme)

**Dosya:** `optimizer_api/tests/run_interactive_benchmark_v2_numba.py`  
**Fonksiyonlar:** `_run_gwo()` (satir 577), `_run_hho()` (satir 663)  
**Oncelik:** P2  
**Etki:** %10-15 GAP iyilestirmesi (GWO/HHO icin)

#### Uygulama Adimlari

1. `_run_gwo()` baslangic dongusunde her kurda `_apply_2opt_to_route(route, duration_func, max_iter=10)` uygula
2. `_run_hho()` baslangic dongusunde her sahine `_apply_2opt_to_route(route, duration_func, max_iter=10)` uygula
3. Her iki fonksiyonun sonunda `_refine_route()` cagrisini kontrol et (zaten mevcut, GOREV 4 ile guclendirilecek)

---

### GOREV 8: crossover_rate Master Numba GA'da Aktive Edilme (K4)

**Dosya:** `optimizer_api/tests/run_interactive_benchmark_v2_numba.py`  
**Fonksiyon:** `_run_ga()` (satir 502-508)  
**Oncelik:** P2  
**Etki:** %2-5 GAP iyilestirmesi

#### Mevcut Durum
```python
# SATIR 505-507: crossover_rate parametresi kullanilmiyor
child = _ordered_crossover(parent_a, parent_b, rng)  # Her zaman crossover
if rng.random() < mutation_rate:
    child = _random_swap(child, rng)
```

#### Hedef Durum
```python
crossover_rate = float(params.get("crossover_rate", 0.85))
# ...
if rng.random() < crossover_rate:
    child = _ordered_crossover(parent_a, parent_b, rng)
else:
    child = parent_a[:]  # Crossover olmazsa ebeveyni kopyala
if rng.random() < mutation_rate:
    child = _random_swap(child, rng)
```

---

### GOREV 9: Istatistiksel Saglamlik (ANOVA + Wilcoxon)

**Dosya:** `academic_benchmark/master_numba_engine.py`  
**Fonksiyon:** `_write_summary()` (satir 762)  
**Oncelik:** P2  
**Etki:** Akademik makale gecerliligini artirir

#### Uygulama Adimlari

1. `_write_summary()` fonksiyonuna istatistiksel test sonuclari ekle:
   - Her algoritma cifti icin Wilcoxon signed-rank testi
   - ANOVA p-degeri (tum algoritmalar arasi)
   - %95 guven araligi (CI)
2. Sonuclari `benchmark_summary.csv`'ye ek kolonlar olarak ekle
3. Dashboard'da istatistiksel anlamlilik gostergesi ekle

---

### GOREV 10: Dokumantasyon Guncellemesi

**Dosya:** `academic_benchmark/BILDIRI2026_VS_MASTER_NUMBA_ANALYSIS.md`  
**Oncelik:** P3  
**Etki:** Dokumantasyon

#### Uygulama Adimlari

1. Analiz raporundaki "KOK NEDEN" bolumunu bu planin uygulanma durumunu gorencelle
2. Her gorev tamamlandikca ilgili satiri ✅ ile isaretle
3. Final karsilastirma sonuclarini rapora ekle

---

## 3. UYGULAMA SIRASI

```
FAZ 1 — Memetic Core (P0, en yuksek etki)
├── GOREV 1: GA memetic init             [1-2 saat]
├── GOREV 2: PSO memetic init            [1-2 saat]
├── GOREV 3: PSO diversity re-init       [1-2 saat]
└── GOREV 4: Final polishing guclendirme [30 dk]

FAZ 2 — Parametre Uyumu (P1)
├── GOREV 5: Profile bypass modu         [30 dk]
└── GOREV 6: DoE parametre uzayi         [30 dk]

FAZ 3 — Genisletme (P2)
├── GOREV 7: GWO/HHO memetic init        [1-2 saat]
├── GOREV 8: crossover_rate aktivasyon   [15 dk]
└── GOREV 9: Istatistiksel saglamlik     [2-3 saat]

FAZ 4 — Dokumantasyon (P3)
└── GOREV 10: Dokumantasyon guncelleme   [30 dk]
```

**Toplam tahmini sure:** 8-14 saat

---

## 4. VALIDASYON KRITERLERI

### 4.1 Karsilastirma Testi

Her gorev tamamlandiktan sonra bu testi calistirin:

```bash
# Bildiri2026 parametreleriyle Master Numba'yi calistir
python academic_benchmark/master_numba_engine.py --mode default --algos GA,PSO --runs 10 --size-limit 100

# Bildiri2026'yi calistir
python academic_benchmark/bildiri2026/3_run_benchmark.py --problems berlin52,eil51,kroA100 --runs 10
```

### 4.2 Kabul Kriterleri

| Kriter | Esi | Aciklama |
|--------|-----|----------|
| GA avg_gap farki | ≤ %3 | Master Numba GA, Bildiri2026 GA'dan en fazla %3 daha kotu |
| PSO avg_gap farki | ≤ %3 | Master Numba PSO, Bildiri2026 PSO'dan en fazla %3 daha kotu |
| Final polishing etkisi | ≥ %10 iyilesme | iter=300, iter=5'e gore en az %10 iyilestirme saglamali |
| PSO re-init etkisi | ≥ %5 iyilesme | Re-init, re-init olmamis haline gore en az %5 iyilestirme saglamali |
| Test basarisi | %100 | Mevcut test suiti basarisiz olmamali |

### 4.3 Regresyon Kontrolu

```bash
# Mevcut testleri calistir
cd academic_benchmark
python -m pytest tests/ -v --tb=short

# Gate validation
python gate_validation.py
```

---

## 5. RISK ANALIZI

| Risk | Olasilik | Etki | Onlem |
|------|----------|------|-------|
| 2-opt init runtime'u cok artirir | Orta | Dusuk | `max_iter=10` ile sinirli (milisaniye mertebesi) |
| Re-init yakinsamayi bozabilir | Dusuk | Orta | `%90 best, %10 random` oranini koru |
| Profile bypass DoE'yi etkiler | Dusuk | Dusuk | `bildiri_aligned` ayri profil olarak kalir |
| crossover_rate GA kalitesini dusurur | Dusuk | Dusuk | Varsayilan 0.85 (literatur standardi) |
| Regresyon testleri basarisiz olur | Dusuk | Yuksek | Her gorev sonrasi test calistir |

---

## 6. BEKLENEN SONUCLAR

### Uygulama Oncesi (Mevcut)

```
Problem     | Bildiri2026 GA | Master Numba GA | Delta
berlin52    | 0.12%          | 15.3%           | +15.18%
eil51       | 0.28%          | 12.7%           | +12.42%
kroA100     | 0.45%          | 18.2%           | +17.75%
```

### Uygulama Sonrasi (Hedef)

```
Problem     | Bildiri2026 GA | Master Numba GA | Delta
berlin52    | 0.12%          | ≤ 2.0%          | ≤ 1.88%
eil51       | 0.28%          | ≤ 2.5%          | ≤ 2.22%
kroA100     | 0.45%          | ≤ 3.0%          | ≤ 2.55%
```

---

## 7. REFERANS KOD

### Bildiri2026 GA Implementasyonu (Hedef)
- `academic_benchmark/bildiri2026/core/ga_solver.py` — satir 56-72 (memetic init), 150-156 (final 2-opt)

### Bildiri2026 PSO Implementasyonu (Hedef)
- `academic_benchmark/bildiri2026/core/pso_solver.py` — satir 110-129 (re-init), 142-156 (memetic init), 211-217 (final 2-opt)

### Master Numba Mevcut Implementasyon (Degistirilecek)
- `optimizer_api/tests/run_interactive_benchmark_v2_numba.py` — satir 481-512 (GA), 535-574 (PSO), 156-175 (refine), 94-153 (tune_params)

### Numba Kernel'lar (Referans, degistirilmeyecek)
- `academic_benchmark/bildiri2026/core/numba_accel.py` — `nb_two_opt`, `nb_three_opt`, `nb_or_opt`

---

**Bu plan tamamlandiginda Master Numba motoru, Bildiri2026 ile ayni memetic hybrid yapisina sahip olacak ve akademik karsilastirmalar gecerli hale gelecektir.**
