# NUMBA DOE — Bildiri2026 Uyumlu Hibrit Geliştirme Tasarımı

**Tarih:** 2026-04-30
**Durum:** Güncellenmiş (Review sonrası revizyon)
**Kapsam:** `academic_benchmark/run_smart_benchmark_numba_doe.py`
**Referans:** `academic_benchmark/bildiri2026/` (1_generate_config.py, 2_run_tuning.py, 3_run_benchmark.py)

---

## 1. Hedef

NUMBA DOE tek-dosya aracını bildiri2026'nın güçlü yönleriyle zenginleştirmek:
- time_matrix desteği
- Düzenlenebilir parametre uzayı
- Config dosyası üretme/yükleme (reproducibility)
- fractional_fallback stratejisi
- CLI argüman desteği (otomasyon)
- Ortam bilgisi loglama
- Yakınsama geçmişi kaydetme
- Anlık paralel ilerleme raporu

Tek dosya yapısı korunur (`run_smart_benchmark_numba_doe.py`).

---

## 2. Review Bulguları ve Çözümleri

### 2.1 KRİTİK — time_matrix Desteği

**Sorun:** `run_single_test` sadece koordinat bazlı çalışır. `create_distance_matrix(coordinates)` ile EUC_2D mesafe matrisi üretir, `calculate_tour_length(tour_indices, coordinates)` ile tur uzunluğunu koordinatlardan hesaplar. `strategy_payload` bir solver sınıfı değil (LocalSearchType enum veya string), "doğrudan solver çağrısı" mümkün değil.

**Çözüm:** `run_single_test_with_matrix()` fonksiyonu yazılacak. Bu fonksiyon:
- `run_single_test` ile aynı arayüze sahip olacak
- `create_distance_matrix(coordinates)` yerine `time_matrix`'ten `Dict[str, Dict[str, float]]` formatına dönüştürme yapacak
- `calculate_tour_length` yerine matris üzerinden hesaplama yapacak
- Aynı `apply_local_search` / `_run_meta_heuristic` dispatch mekanizmasını kullanacak

```python
def run_single_test_with_matrix(
    problem: TSPLIBProblem,
    strategy_instance: Union[LocalSearchType, str],
    seed: int,
    params: Union[Dict[str, Any], int, None],
    time_matrix: List[List[float]],
) -> Dict:
    """time_matrix ile çalışan run_single_test alternatifi."""
    dimension = problem.dimension
    run_params: Dict[str, Any] = {}
    if isinstance(params, dict):
        run_params = params.copy()
    elif isinstance(params, int):
        run_params = {"max_iterations": params}

    # time_matrix'i Dict[str, Dict[str, float]] formatına dönüştür
    matrix: Dict[str, Dict[str, float]] = {}
    for i in range(dimension):
        key_i = f"L{i+1}"
        matrix[key_i] = {}
        for j in range(dimension):
            matrix[key_i][f"L{j+1}"] = float(time_matrix[i][j])

    duration_func = create_duration_func(matrix)

    indices = list(range(1, dimension + 1))
    random.seed(seed)
    random.shuffle(indices)
    initial_route = [f"L{i}" for i in indices]

    start_time = time.time()
    if isinstance(strategy_instance, LocalSearchType):
        improved_route, _ = apply_local_search(
            initial_route, duration_func, strategy_instance,
            max_iterations=int(run_params.get("max_iterations", 1000)),
        )
        algorithm_type = "local_search"
    else:
        improved_route = _run_meta_heuristic(
            str(strategy_instance), initial_route, duration_func, run_params, seed,
        )
        algorithm_type = "meta_heuristic"
    elapsed = time.time() - start_time

    # Tur uzunluğunu matristen hesapla
    tour_indices = convert_route_to_indices(improved_route)
    tour_length = 0
    for k in range(len(tour_indices)):
        a = tour_indices[k]
        b = tour_indices[(k + 1) % len(tour_indices)]
        tour_length += time_matrix[a - 1][b - 1]
    tour_length = int(tour_length)

    gap = ((tour_length - problem.optimal) / problem.optimal) * 100 if problem.optimal else float("nan")

    return {
        "tour_length": tour_length,
        "gap": gap,
        "time_ms": elapsed * 1000,
        "algorithm_type": algorithm_type,
    }
```

**Yerleşim:** `run_smart_benchmark_numba_doe.py` dosyasının üst kısmında, import'lardan sonra tanımlanır. `run_single_test` import edildiği yerin yanına.

---

### 2.2 KRİTİK — Yakınsama Geçmişi

**Sorun:** `run_single_test` `history` alanı döndürmez. Solver payload'ları enum/string, `.solve()` metodu yok.

**Çözüm (Minimal):** Her run'ın `tour_length` değerini bir listede toplayarak yakınsama profili oluştur. Bu, `run_single_test`'i değiştirmeden yapılabilir.

```python
# _evaluate_param_combo içinde:
run_results = []
for run_idx in range(n_runs):
    seed = 1000 + combo_idx * 100 + run_idx
    result = run_single_test(...)  # veya run_single_test_with_matrix(...)
    run_results.append(result)

# Yakınsama profili: her run'ın tour_length'i
convergence_profile = [r["tour_length"] for r in run_results]
```

**Kayıt:** `_tune_parameters` tamamlandıktan sonra, en iyi parametre setinin `convergence_profile`'ı `histories/convergence_{timestamp}.json` dosyasına yazılır.

**Gelecek genişletme:** Eğer solver'lar `history` döndürmeye başlarsa, `_evaluate_param_combo` return dict'ine `"history": result.get("history")` eklenir.

---

### 2.3 KRİTİK — `_Problem` Sınıfı Scope

**Sorun:** `_Problem` sınıfı `_evaluate_param_combo` içinde her çağrıda yeniden tanımlanıyor. Multiprocessing'te pickle sorunlarına neden olabilir.

**Çözüm:** `_Problem` modül seviyesine taşınır, `is_time_matrix` ve `time_matrix` alanları eklenir.

```python
@dataclass
class DOEProblem:
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]]
    optimal: Optional[float]
    category: str
    source: str = "tsplib"
    is_time_matrix: bool = False
    time_matrix: Optional[List[List[float]]] = None
```

`_evaluate_param_combo` içinde `_Problem` sınıfı kaldırılır, doğrudan `DOEProblem` dataclass'ı kullanılır. Ancak multiprocessing'te dataclass'lar otomatik picklable olduğundan, `_make_problem_dict` ile dict'e dönüştürülüp worker'da tekrar `DOEProblem`'e çevrilir (mevcut pattern korunur).

---

### 2.4 YÜKSEK — Paralel Çalıştırma

**Sorun:** `Pool.imap_unordered` sonuçları toplu döndürüyor (aslında lazy iterator ama `list()` ile tüketiliyor). Bildiri2026 `ProcessPoolExecutor` + `as_completed` ile anlık ilerleme gösteriyor.

**Risk:** Numba JIT + `ProcessPoolExecutor` uyumluluğu garantilenemez. Windows'ta her iki yöntem de `spawn` kullanır.

**Çözüm:** `Pool` kalsın ama lazy iteration ile anlık ilerleme sağlansın:

```python
def _run_pool(tasks: List[Tuple], workers: int, on_result=None) -> List[Dict[str, Any]]:
    if not tasks:
        return []
    if workers <= 1:
        results = []
        for i, task in enumerate(tasks):
            result = _evaluate_param_combo(task)
            results.append(result)
            if on_result:
                on_result(i, result, len(tasks))
        return results
    results = []
    with Pool(processes=workers) as pool:
        for i, result in enumerate(pool.imap_unordered(_evaluate_param_combo, tasks)):
            results.append(result)
            if on_result:
                on_result(i, result, len(tasks))
    return results
```

**`on_result` callback:** `_tune_parameters` ve `_run_benchmark_with_best` içinde `_print_progress_line` callback olarak geçirilir. Ana process'te çalışır, thread-safe.

---

### 2.5 YÜKSEK — Config Doğrulama

**Çözüm:** `_validate_config(config, all_problems, all_specs)` fonksiyonu:

```python
def _validate_config(config: Dict, all_problems: List[DOEProblem], all_specs: List[StrategySpec]) -> Tuple[bool, str]:
    if not isinstance(config, dict):
        return False, "Config bir dict olmali"
    if "version" not in config:
        return False, "version alani eksik"
    if config.get("version", 0) != 1:
        return False, f"Desteklenmeyen config versiyonu: {config.get('version')}"
    if "problems" not in config:
        return False, "problems alani eksik"
    if "algorithms" not in config:
        return False, "algorithms alani eksik"
    if "settings" not in config:
        return False, "settings alani eksik"
    return True, "OK"
```

---

### 2.6 ORTA — `fractional_fallback` Seed

**Çözüm:** Config'de `"random_seed": 42` alsın, `_generate_combinations` içinde kullanılsın:

```python
def _generate_combinations(space, max_combinations, strategy="sequential", random_seed=42):
    keys = list(space.keys())
    combos = [dict(zip(keys, v)) for v in itertools.product(*(space[k] for k in keys))]
    if len(combos) > max_combinations and strategy == "fractional_fallback":
        random.seed(random_seed)
        combos = random.sample(combos, max_combinations)
    else:
        combos = combos[:max_combinations]
    return combos
```

---

### 2.7 ORTA — Parametre Doğrulama

**Çözüm:** Her algoritma için min/max/type kuralları:

```python
PARAM_VALIDATORS = {
    "pop_size": (1, 10000, int),
    "swarm_size": (1, 10000, int),
    "hawks": (1, 10000, int),
    "pack_size": (1, 10000, int),
    "generations": (1, 100000, int),
    "iterations": (1, 100000, int),
    "max_iterations": (1, 100000, int),
    "mutation_rate": (0.0, 1.0, float),
    "elite_size": (1, 100, int),
    "w": (0.0, 2.0, float),
    "c1": (0.0, 5.0, float),
    "c2": (0.0, 5.0, float),
}
```

`_edit_param_space` fonksiyonu her değer girişinden sonra doğrulama yapar, geçersizse uyarı + yeniden ister.

---

### 2.8 DÜŞÜK — Dosya Organizasyonu

Tek dosya içinde bölüm ayırıcılar:

```python
# ============================================================
# BÖLÜM 1: Veri Modelleri (dataclass'lar)
# ============================================================

# ============================================================
# BÖLÜM 2: Konfigürasyon ve Metadata
# ============================================================

# ============================================================
# BÖLÜM 3: Problem Yükleme (TSPLIB + time_matrix)
# ============================================================

# ============================================================
# BÖLÜM 4: Parametre Uzayı ve Düzenleme
# ============================================================

# ============================================================
# BÖLÜM 5: Paralel Çalıştırma
# ============================================================

# ============================================================
# BÖLÜM 6: DOE Tuning
# ============================================================

# ============================================================
# BÖLÜM 7: Benchmark
# ============================================================

# ============================================================
# BÖLÜM 8: Config Dosyası (Kaydet/Yükle)
# ============================================================

# ============================================================
# BÖLÜM 9: CLI Arayüzü
# ============================================================

# ============================================================
# BÖLÜM 10: UI Fonksiyonları (Menü, Seçim, Özet)
# ============================================================

# ============================================================
# BÖLÜM 11: main()
# ============================================================
```

---

### 2.9 DÜŞÜK — CLI Öncelik Kuralları

```python
def _parse_cli_args() -> Optional[Dict]:
    """CLI argümanlarını parse eder. Dönerse config modunda çalışır, None ise interaktif."""
    parser = argparse.ArgumentParser(...)
    parser.add_argument("--config", help="Config dosyası yolu")
    parser.add_argument("--problem", help="Problem seçimi (isim veya class)")
    parser.add_argument("--algo", help="Algoritma seçimi")
    parser.add_argument("--tune-runs", type=int)
    parser.add_argument("--benchmark-runs", type=int)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--mode", choices=["S", "P"])
    parser.add_argument("--profile", choices=["quality_first", "baseline"])
    parser.add_argument("--save-config", help="Seçimleri config olarak kaydet")
    args = parser.parse_args()
    if not any(vars(args).values()):
        return None  # interaktif mod
    return vars(args)
```

**Öncelik:** `--config` > `--problem`/`--algo` > interaktif. `--config` varsa yüklenir, diğer argümanlar override eder.

---

### 2.10 DÜŞÜK — Config Dosya Adlandırma

Format: `{YYYYMMDD}_{HHMMSS}_{scope}.json`
Örnek: `20260430_223934_index_1,3_all.json`

`_save_config` fonksiyonu otomatik timestamp ekler, kullanıcıya dosya adı gösterir.

---

## 3. Veri Modeli

```python
@dataclass
class DOEProblem:
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]]
    optimal: Optional[float]
    category: str
    source: str = "tsplib"
    is_time_matrix: bool = False
    time_matrix: Optional[List[List[float]]] = None

@dataclass
class StrategySpec:
    name: str
    payload: Any
    default_params: Dict[str, Any]
    algorithm_type: str
```

---

## 4. Yeni Fonksiyonlar

| Fonksiyon | Amaç |
|-----------|------|
| `run_single_test_with_matrix()` | time_matrix ile test çalıştırma |
| `_load_problems_unified()` | TSPLIB + time_matrix problem yükleme |
| `_edit_param_space()` | Parametre uzayı düzenleme |
| `_validate_param_value()` | Tek parametre doğrulama |
| `_generate_combinations()` | fractional_fallback destekli kombinasyon üretimi |
| `_save_config()` | Interaktif seçimleri JSON'a kaydetme |
| `_load_config()` | JSON'dan config yükleme |
| `_validate_config()` | Config doğrulama |
| `_list_configs()` | Mevcut config dosyalarını listeleme |
| `_log_environment_info()` | Ortam bilgisi yazdırma |
| `_save_convergence_history()` | Yakınsama geçmişi kaydetme |
| `_parse_cli_args()` | CLI argüman ayrıştırma |

---

## 5. Güncellenmiş Menü

```
--- TUNING (DOE) ---
  [A] Tam DOE Tune: Tum secili pairleri bastan tune et
  [B] Eksikleri Tamamla: Sadece hic tune edilmemis pairleri calistir
  [C] Hizli Mod: Kucuk problem seti ile tum algoritmalar
  [D] Kapsamli: Secili scope icin her seyi yeniden calistir
  [E] Ozel Secim: Istediginiz problem ve algoritmalari numara ile secin

--- BENCHMARK ---
  [F] Direkt Benchmark: DOE tuning yapmadan kayitli/varsayilan parametrelerle calistir

--- CONFIG ---
  [G] Config Yükle: Kayitli config dosyasindan calistir

--- DIGER ---
  [S] Detay Modu: Bir problem icin DOE kayitlarini gor
  [Q] Cikis
```

---

## 6. Akış Diyagramları

### 6.1 Ana Akış

```
CLI argüman?
├─ Evet → _parse_cli_args() → config/yükle → otomatik çalıştır
└─ Hayır → _log_environment_info() → ana menü loop
```

### 6.2 A-E (Tuning) Akışı

```
Menü seçimi → kapsam (problem + algoritma)
→ _edit_param_space() [her algo için]
→ ayarlar (profile, mode, tuning_runs, max_combinations, workers)
→ _show_test_summary() → onay
→ _tune_parameters() [anlık ilerleme ile]
→ [E/H] benchmark?
├─ E → _run_benchmark_with_best() → sonuçlar
└─ H → sadece tuning sonucu
→ _save_convergence_history()
→ [İsteğe bağlı] _save_config()
```

### 6.3 F (Direkt Benchmark) Akışı

```
Menü seçimi → kapsam (problem + algoritma)
→ ayarlar (profile, mode, benchmark_runs, workers)
→ _collect_benchmark_params() [her pair için parametre girişi]
→ _show_test_summary() → onay
→ _run_benchmark_direct() → sonuçlar
```

### 6.4 G (Config Yükle) Akışı

```
Menü seçimi → _list_configs() → config seç
→ _load_config() → _validate_config()
→ [override varsa uygula]
→ çalıştır (A-E veya F akışına yönlendir)
```

---

## 7. Config JSON Şeması

```json
{
  "version": 1,
  "created_at": "2026-04-30T22:53:45",
  "problems": {
    "mode": "index",
    "selection": [1, 3, 5]
  },
  "algorithms": {
    "selection": [1, 4]
  },
  "settings": {
    "profile": "quality_first",
    "mode": "S",
    "tuning_runs": 3,
    "benchmark_runs": 5,
    "max_combinations": 12,
    "workers": 1,
    "fractional_fallback": true,
    "random_seed": 42
  },
  "param_overrides": {
    "GA": {"pop_size": [80, 120], "generations": [200, 300]},
    "2-opt": {"max_iterations": [1000, 2000]}
  }
}
```

---

## 8. Dosya Yapısı

```
academic_benchmark/
  run_smart_benchmark_numba_doe.py       ← tek dosya (tüm değişiklikler)
  benchmark_db/doe_numba/
    best_params.json
    tuning_progress.csv
    benchmark_progress.csv
    benchmark_summary.csv
    latest_metadata_numba_doe.json
    configs/                             ← YENİ: config dosyaları
    histories/                           ← YENİ: yakınsama geçmişi
```

---

## 9. Uygulama Sırası

1. `DOEProblem` genişletme (is_time_matrix, time_matrix)
2. `_load_problems_unified()` — TSPLIB + time_matrix yükleme
3. `run_single_test_with_matrix()` — time_matrix test fonksiyonu
4. `_Problem` sınıfını modül seviyesine taşıma
5. `_evaluate_param_combo` güncelleme (time_matrix dallanması)
6. `_generate_combinations()` — fractional_fallback
7. `_edit_param_space()` + `_validate_param_value()` — parametre düzenleme
8. `_run_pool()` güncelleme — lazy iteration + on_result callback
9. `_log_environment_info()` — ortam bilgisi
10. `_save_config()` / `_load_config()` / `_validate_config()` / `_list_configs()`
11. `_save_convergence_history()`
12. `_parse_cli_args()` — CLI desteği
13. Menüye `[G]` ekleme
14. `main()` akışını güncelleme
15. Test ve doğrulama

---

## 10. Riskler ve Mitigasyonlar

| Risk | Mitigasyon |
|------|------------|
| Numba + ProcessPoolExecutor uyumsuzluğu | Pool + imap_unordered korundu |
| time_matrix büyük boyut (1000x1000) | Dict dönüşümü worker'da yapılır, serileştirme maliyeti yönetilebilir |
| Config eski versiyon uyumsuzluğu | Versiyon kontrolü + uyarı |
| Parametre doğrulama eksikliği | PARAM_VALIDATORS sözlüğü |
| Dosya boyutu artışı | Bölüm ayırıcılar + net organizasyon |
| run_single_test_with_matrix kod tekrarı | Minimal tekrar, sadece matrix oluşturma ve tur hesaplama farkı |
