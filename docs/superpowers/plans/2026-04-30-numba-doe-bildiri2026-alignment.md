# NUMBA DOE — Bildiri2026 Uyumlu Hibrit Geliştirme Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** NUMBA DOE tek-dosya aracını bildiri2026 özellikleriyle zenginleştirmek: time_matrix desteği, düzenlenebilir parametre uzayı, config dosyası, fractional_fallback, CLI, ortam bilgisi, yakınsama geçmişi, anlık paralel ilerleme.

**Architecture:** Tek dosya (`run_smart_benchmark_numba_doe.py`) içinde 11 bölüm. Mevcut yapı korunur, yeni fonksiyonlar eklenir, `_evaluate_param_combo` ve `_run_pool` güncellenir.

**Tech Stack:** Python 3.10+, multiprocessing.Pool, argparse, json, csv, dataclasses

**Spec:** `docs/superpowers/specs/2026-04-30-numba-doe-bildiri2026-alignment-design.md`

---

## Dosya Haritası

| Dosya | İşlem |
|-------|-------|
| `academic_benchmark/run_smart_benchmark_numba_doe.py` | **MODIFY** — tüm değişiklikler burada |
| `academic_benchmark/bildiri2026/data_manager.py` | **READ** — time_matrix yükleme referansı |
| `academic_benchmark/bildiri2026/2_run_tuning.py` | **READ** — evaluate_combination referansı |
| `optimizer_api/tests/run_interactive_benchmark_v2_numba.py` | **READ** — run_single_test, create_duration_func, apply_local_search, _run_meta_heuristic, convert_route_to_indices |

---

### Task 1: Import'lar ve Sabitler

**Files:**
- Modify: `academic_benchmark/run_smart_benchmark_numba_doe.py:1-67`

- [ ] **Step 1: Yeni import'ları ekle**

Dosyanın en üstündeki import bloğuna `argparse`, `random`, `platform` ekle. `run_interactive_benchmark_v2_numba`'dan `create_duration_func`, `apply_local_search`, `_run_meta_heuristic`, `convert_route_to_indices` import et.

```python
import argparse
import platform
import random
```

```python
from optimizer_api.tests.run_interactive_benchmark_v2_numba import (
    BENCHMARK_PROFILE as DEFAULT_PROFILE,
    STRATEGIES,
    VALID_BENCHMARK_PROFILES,
    apply_local_search,
    convert_route_to_indices,
    create_duration_func,
    print_summary_table,
    run_single_test,
    _run_meta_heuristic,
)
```

- [ ] **Step 2: Yeni sabitleri ekle**

`RESULTS_DIR`'dan sonra yeni dizin sabitleri ekle:

```python
CONFIGS_DIR = os.path.join(RESULTS_DIR, "configs")
HISTORIES_DIR = os.path.join(RESULTS_DIR, "histories")
```

- [ ] **Step 3: PARAM_VALIDATORS sözlüğünü ekle**

`ALGORITHMS_TO_CHECK`'tan sonra:

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

- [ ] **Step 4: Syntax kontrolü**

Run: `python -m py_compile academic_benchmark/run_smart_benchmark_numba_doe.py`
Expected: no output (success)

- [ ] **Step 5: Commit**

---

### Task 2: DOEProblem Genişletme

**Files:**
- Modify: `academic_benchmark/run_smart_benchmark_numba_doe.py:70-77`

- [ ] **Step 1: DOEProblem dataclass'ına alan ekle**

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

- [ ] **Step 2: Syntax kontrolü**

Run: `python -m py_compile academic_benchmark/run_smart_benchmark_numba_doe.py`

- [ ] **Step 3: Commit**

---

### Task 3: `_load_problems_unified()` — TSPLIB + time_matrix Yükleme

**Files:**
- Modify: `academic_benchmark/run_smart_benchmark_numba_doe.py` — `_load_problems` fonksiyonundan sonra yeni fonksiyon

- [ ] **Step 1: `_load_problems_unified` fonksiyonunu ekle**

`_load_problems` fonksiyonundan (satır 131-155) sonra ekle:

```python
def _load_problems_unified(size_mode: str = "all") -> List[DOEProblem]:
    problems = _load_problems(size_mode)
    data_dir = os.path.join(SCRIPT_DIR, "data")
    if os.path.exists(data_dir):
        for f in os.listdir(data_dir):
            if f.endswith(".json") and f != "tuned_parameters_db.json":
                fpath = os.path.join(data_dir, f)
                try:
                    with open(fpath, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    if "time_matrix" not in data:
                        continue
                    matrix = data["time_matrix"]
                    name = data.get("name", f.replace(".json", ""))
                    dim = len(matrix)
                    optimal = data.get("optimal")
                    cat = "small" if dim <= 100 else ("medium" if dim <= 500 else "large")
                    if size_mode != "all" and cat != size_mode:
                        continue
                    problems.append(DOEProblem(
                        name=name, dimension=dim, coordinates=[(0.0, 0.0)] * dim,
                        optimal=optimal, category=cat, source="time_matrix",
                        is_time_matrix=True, time_matrix=matrix,
                    ))
                except Exception:
                    continue
    return problems
```

- [ ] **Step 2: `_ensure_dirs` güncelle**

`_ensure_dirs` fonksiyonuna iki satır ekle:

```python
def _ensure_dirs() -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(CONFIGS_DIR, exist_ok=True)
    os.makedirs(HISTORIES_DIR, exist_ok=True)
```

- [ ] **Step 3: Syntax kontrolü**

- [ ] **Step 4: Commit**

---

### Task 4: `run_single_test_with_matrix()` — time_matrix Test Fonksiyonu

**Files:**
- Modify: `academic_benchmark/run_smart_benchmark_numba_doe.py` — import'lardan sonra, `_normalize_strategy_entry`'den önce

- [ ] **Step 1: Fonksiyonu ekle**

```python
def run_single_test_with_matrix(
    problem: DOEProblem,
    strategy_instance: Union[LocalSearchType, str],
    seed: int,
    params: Union[Dict[str, Any], int, None],
    time_matrix: List[List[float]],
) -> Dict[str, Any]:
    dimension = problem.dimension
    run_params: Dict[str, Any] = {}
    if isinstance(params, dict):
        run_params = params.copy()
    elif isinstance(params, int):
        run_params = {"max_iterations": params}

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

Not: `Union` import'u zaten mevcut (`from typing import ... Union ...`). Eğer yoksa eklenmeli.

- [ ] **Step 2: Syntax kontrolü**

- [ ] **Step 3: Commit**

---

### Task 5: `_evaluate_param_combo` — time_matrix Dallanması

**Files:**
- Modify: `academic_benchmark/run_smart_benchmark_numba_doe.py:592-635`

- [ ] **Step 1: `_evaluate_param_combo` fonksiyonunu güncelle**

Mevcut fonksiyonda `_Problem` sınıfını kaldır, `problem_dict`'ten doğrudan alan oku. `is_time_matrix` dallanması ekle:

```python
def _evaluate_param_combo(task: Tuple[Dict[str, Any], str, Any, Dict[str, Any], int, int]) -> Dict[str, Any]:
    problem_dict, strategy_name, strategy_payload, strategy_params, combo_idx, n_runs = task

    is_time_matrix = problem_dict.get("is_time_matrix", False)
    time_matrix = problem_dict.get("time_matrix")
    optimal = problem_dict.get("optimal")

    class _Problem:
        def __init__(self, data: Dict[str, Any]):
            self.name = data["name"]
            self.dimension = data["dimension"]
            self.optimal = data.get("optimal")
            self.coordinates = data.get("coordinates", [])
            self.category = data.get("category", "small")
            self.source = data.get("source", "tsplib")
            self.is_time_matrix = data.get("is_time_matrix", False)
            self.time_matrix = data.get("time_matrix")

    problem = _Problem(problem_dict)
    effective_problem = problem
    if not getattr(problem, "optimal", None):
        class _ProblemWithSafeOptimal(_Problem):
            def __init__(self, data: Dict[str, Any]):
                super().__init__(data)
                self.optimal = 1
        effective_problem = _ProblemWithSafeOptimal(problem_dict)

    run_results: List[Dict[str, Any]] = []
    t0 = time.perf_counter()
    for run_idx in range(n_runs):
        seed = 1000 + combo_idx * 100 + run_idx
        if is_time_matrix and time_matrix:
            result = run_single_test_with_matrix(
                effective_problem, strategy_payload, seed, strategy_params, time_matrix
            )
        else:
            result = run_single_test(effective_problem, strategy_payload, seed, strategy_params)
        if not optimal:
            result = result.copy()
            result["gap"] = float("nan")
        run_results.append(result)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    avg_length = sum(float(r["tour_length"]) for r in run_results) / max(1, len(run_results))
    valid_gaps = [float(r["gap"]) for r in run_results if not math.isnan(float(r["gap"]))]
    avg_gap = sum(valid_gaps) / len(valid_gaps) if valid_gaps else float("nan")
    convergence_profile = [float(r["tour_length"]) for r in run_results]

    return {
        "problem": problem.name,
        "strategy": strategy_name,
        "combo_idx": combo_idx,
        "params": strategy_params,
        "avg_length": avg_length,
        "avg_gap": avg_gap,
        "avg_time_ms": elapsed_ms / max(1, len(run_results)),
        "n_runs": n_runs,
        "convergence_profile": convergence_profile,
    }
```

- [ ] **Step 2: `_make_problem_dict` güncelle**

`_make_problem_dict` fonksiyonuna `is_time_matrix` ve `time_matrix` alanlarını ekle:

```python
def _make_problem_dict(problem: DOEProblem) -> Dict[str, Any]:
    d = {
        "name": problem.name,
        "dimension": problem.dimension,
        "optimal": problem.optimal,
        "coordinates": problem.coordinates,
        "category": problem.category,
        "source": problem.source,
        "is_time_matrix": problem.is_time_matrix,
    }
    if problem.is_time_matrix and problem.time_matrix is not None:
        d["time_matrix"] = problem.time_matrix
    return d
```

- [ ] **Step 3: Syntax kontrolü**

- [ ] **Step 4: Commit**

---

### Task 6: `_run_pool` — Lazy Iteration + on_result Callback

**Files:**
- Modify: `academic_benchmark/run_smart_benchmark_numba_doe.py:638-644`

- [ ] **Step 1: `_run_pool` fonksiyonunu güncelle**

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

- [ ] **Step 2: Syntax kontrolü**

- [ ] **Step 3: Commit**

---

### Task 7: `_generate_combinations` — fractional_fallback

**Files:**
- Modify: `academic_benchmark/run_smart_benchmark_numba_doe.py` — `_param_product`'tan sonra

- [ ] **Step 1: `_generate_combinations` fonksiyonunu ekle**

```python
def _generate_combinations(space: Dict[str, List[Any]], max_combinations: int,
                           strategy: str = "sequential", random_seed: int = 42) -> List[Dict[str, Any]]:
    keys = list(space.keys())
    combos = [dict(zip(keys, v)) for v in itertools.product(*(space[k] for k in keys))]
    if len(combos) > max_combinations and strategy == "fractional_fallback":
        random.seed(random_seed)
        combos = random.sample(combos, max_combinations)
    else:
        combos = combos[:max_combinations]
    return combos
```

- [ ] **Step 2: `_tune_parameters` içinde `_param_product` kullanımını güncelle**

`_tune_parameters` fonksiyonunda (yaklaşık satır 686):
```python
# ESKİ:
combos = list(_param_product(space))[:max_combinations]

# YENİ:
combos = _generate_combinations(space, max_combinations)
```

- [ ] **Step 3: Syntax kontrolü**

- [ ] **Step 4: Commit**

---

### Task 8: `_validate_param_value` + `_edit_param_space` — Parametre Düzenleme

**Files:**
- Modify: `academic_benchmark/run_smart_benchmark_numba_doe.py` — `_select_algorithms_numbered`'den sonra

- [ ] **Step 1: `_validate_param_value` fonksiyonunu ekle**

```python
def _validate_param_value(key: str, raw: str, expected_type: type) -> Optional[Any]:
    validator = PARAM_VALIDATORS.get(key)
    try:
        if expected_type == bool:
            val = raw.lower() in ("true", "1", "t", "evet", "e")
        elif expected_type == float:
            val = float(raw)
        elif expected_type == int:
            val = int(raw)
        else:
            val = raw
        if validator:
            vmin, vmax, _ = validator
            if val < vmin or val > vmax:
                print(f"    [!] {key} aralik disi [{vmin}, {vmax}]: {val}")
                return None
        return val
    except ValueError:
        print(f"    [!] {key} icin gecersiz deger: {raw}")
        return None
```

- [ ] **Step 2: `_edit_param_space` fonksiyonunu ekle**

```python
def _edit_param_space(space: Dict[str, List[Any]], algo_name: str) -> Dict[str, List[Any]]:
    print(f"\n[PARAM] {algo_name} parametre uzayini duzenleyin (Enter = kabul):")
    result: Dict[str, List[Any]] = {}
    for key, vals in space.items():
        print(f"  {key} = {vals}")
        raw = input(f"    Yeni degerler (virgul) [{vals}]: ").strip()
        if not raw:
            result[key] = vals
            continue
        parts = [x.strip() for x in raw.split(",")]
        new_vals: List[Any] = []
        sample_type = type(vals[0]) if vals else str
        valid = True
        for p in parts:
            if not p:
                continue
            v = _validate_param_value(key, p, sample_type)
            if v is None:
                valid = False
                break
            new_vals.append(v)
        if valid and new_vals:
            result[key] = new_vals
        else:
            print(f"    [!] Gecersiz giris, mevcut degerler korunuyor: {vals}")
            result[key] = vals
    return result
```

- [ ] **Step 3: Syntax kontrolü**

- [ ] **Step 4: Commit**

---

### Task 9: `_log_environment_info` — Ortam Bilgisi

**Files:**
- Modify: `academic_benchmark/run_smart_benchmark_numba_doe.py` — `_clear`'den sonra

- [ ] **Step 1: Fonksiyonu ekle**

```python
def _log_environment_info() -> None:
    print(f"[ENV] OS: {platform.system()} {platform.release()}")
    print(f"[ENV] Python: {sys.version.split()[0]}")
    try:
        import numpy
        print(f"[ENV] NumPy: {numpy.__version__}")
    except ImportError:
        print("[ENV] NumPy: N/A")
    try:
        import numba
        print(f"[ENV] Numba: {numba.__version__}")
    except ImportError:
        print("[ENV] Numba: N/A")
    print(f"[ENV] CPU: {cpu_count()} cores")
```

- [ ] **Step 2: Syntax kontrolü**

- [ ] **Step 3: Commit**

---

### Task 10: Config Dosyası Fonksiyonları

**Files:**
- Modify: `academic_benchmark/run_smart_benchmark_numba_doe.py` — `_write_summary`'den sonra

- [ ] **Step 1: `_validate_config` fonksiyonunu ekle**

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

- [ ] **Step 2: `_list_configs` fonksiyonunu ekle**

```python
def _list_configs() -> List[str]:
    if not os.path.exists(CONFIGS_DIR):
        return []
    return sorted([f for f in os.listdir(CONFIGS_DIR) if f.endswith(".json")])
```

- [ ] **Step 3: `_save_config` fonksiyonunu ekle**

```python
def _save_config(
    selected_problems: List[DOEProblem],
    selected_names: List[str],
    settings: Dict[str, Any],
    param_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
) -> str:
    scope_parts = []
    for p in selected_problems[:3]:
        scope_parts.append(p.name)
    if len(selected_problems) > 3:
        scope_parts.append(f"and{len(selected_problems)-3}more")
    scope_str = "_".join(scope_parts) if scope_parts else "custom"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_{scope_str}.json"
    filepath = os.path.join(CONFIGS_DIR, filename)

    problem_indices = []
    all_problems = _load_problems_unified("all")
    for p in selected_problems:
        for idx, ap in enumerate(all_problems):
            if ap.name == p.name:
                problem_indices.append(idx + 1)
                break

    all_specs = _all_strategy_specs()
    algo_indices = []
    for name in selected_names:
        for idx, spec in enumerate(all_specs):
            if spec.name == name:
                algo_indices.append(idx + 1)
                break

    config = {
        "version": 1,
        "created_at": datetime.now().isoformat(),
        "problems": {"mode": "index", "selection": problem_indices},
        "algorithms": {"selection": algo_indices},
        "settings": settings,
    }
    if param_overrides:
        config["param_overrides"] = param_overrides

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return filepath
```

- [ ] **Step 4: `_load_config` fonksiyonunu ekle**

```python
def _load_config(filepath: str, all_problems: List[DOEProblem], all_specs: List[StrategySpec]) -> Optional[Dict[str, Any]]:
    if not os.path.exists(filepath):
        print(f"[HATA] Config dosyasi bulunamadi: {filepath}")
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[HATA] Config JSON hatasi: {e}")
        return None

    ok, msg = _validate_config(config, all_problems, all_specs)
    if not ok:
        print(f"[HATA] Config dogrulama basarisiz: {msg}")
        return None
    return config
```

- [ ] **Step 5: Syntax kontrolü**

- [ ] **Step 6: Commit**

---

### Task 11: `_save_convergence_history` — Yakınsama Geçmişi

**Files:**
- Modify: `academic_benchmark/run_smart_benchmark_numba_doe.py`

- [ ] **Step 1: Fonksiyonu ekle**

```python
def _save_convergence_history(best_params: Dict[str, Dict[str, Any]], metadata: Dict[str, Any]) -> None:
    histories: Dict[str, Any] = {}
    for key, entry in best_params.items():
        profile = entry.get("convergence_profile")
        if profile:
            histories[key] = {
                "problem": entry.get("problem"),
                "strategy": entry.get("strategy"),
                "avg_length": entry.get("avg_length"),
                "avg_gap": entry.get("avg_gap"),
                "convergence_profile": profile,
            }
    if histories:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h_path = os.path.join(HISTORIES_DIR, f"convergence_{ts}.json")
        with open(h_path, "w", encoding="utf-8") as f:
            json.dump(histories, f, indent=2, ensure_ascii=False)
        print(f"[SAVED] Yakinsama gecmisi: {h_path}")
```

- [ ] **Step 2: `_tune_parameters` içinde convergence_profile kaydetme**

`_tune_parameters` fonksiyonunda `best_params[best_key]` atamasına `"convergence_profile"` ekle:

```python
best_params[best_key] = {
    "problem": problem_name,
    "strategy": strategy_name,
    "avg_length": result["avg_length"],
    "avg_gap": result["avg_gap"],
    "avg_time_ms": result["avg_time_ms"],
    "params": params,
    "convergence_profile": result.get("convergence_profile", []),
}
```

- [ ] **Step 3: Syntax kontrolü**

- [ ] **Step 4: Commit**

---

### Task 12: `_parse_cli_args` — CLI Desteği

**Files:**
- Modify: `academic_benchmark/run_smart_benchmark_numba_doe.py` — `main()`'dan önce

- [ ] **Step 1: Fonksiyonu ekle**

```python
def _parse_cli_args() -> Optional[Dict[str, Any]]:
    parser = argparse.ArgumentParser(
        description="UniRide NUMBA DOE Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", help="Config dosyası yolu")
    parser.add_argument("--problem", help="Problem secimi (isim: berlin52,eil51 veya class: small)")
    parser.add_argument("--algo", help="Algoritma secimi (isim: GA,PSO veya all)")
    parser.add_argument("--tune-runs", type=int, help="DOE tuning tekrar sayisi")
    parser.add_argument("--benchmark-runs", type=int, help="Benchmark tekrar sayisi")
    parser.add_argument("--workers", type=int, help="Worker sayisi")
    parser.add_argument("--mode", choices=["S", "P"], help="S=Sirali, P=Paralel")
    parser.add_argument("--profile", choices=["quality_first", "baseline"], help="Benchmark profili")
    parser.add_argument("--save-config", help="Secimleri config olarak kaydet")
    parser.add_argument("--fractional-fallback", action="store_true", help="Fractional fallback stratejisi")
    parser.add_argument("--random-seed", type=int, default=42, help="Fractional fallback seed")

    args, _ = parser.parse_known_args()
    d = vars(args)
    if not any(d.values()):
        return None
    return d
```

- [ ] **Step 2: Syntax kontrolü**

- [ ] **Step 3: Commit**

---

### Task 13: `main()` Akışı — G Menüsü + CLI + Parametre Düzenleme + Ortam Bilgisi

**Files:**
- Modify: `academic_benchmark/run_smart_benchmark_numba_doe.py:798-1055`

Bu task en büyük değişiklik. Adımlara bölünmüş:

- [ ] **Step 1: `main()` girişinde CLI kontrolü ekle**

`main()` fonksiyonunun başında, `_ensure_dirs()`'tan sonra:

```python
cli_args = _parse_cli_args()
if cli_args:
    _log_environment_info()
    # CLI modu — config veya manuel seçim
    # ... (Task 14'te detaylandırılacak)
```

- [ ] **Step 2: `_load_problems("all")` → `_load_problems_unified("all")` değişimi**

`main()` içinde `all_problems = _load_problems("all")` satırını `all_problems = _load_problems_unified("all")` olarak değiştir.

- [ ] **Step 3: Ana menüye `[G]` ekle**

Mevcut menüye ekle:

```python
print("\n--- CONFIG ---")
print("  [G] Config Yükle: Kayitli config dosyasindan calistir")
```

Valid choices'e `"G"` ekle.

- [ ] **Step 4: `_log_environment_info()` çağrısı ekle**

While loop'un başına, `_clear()`'dan sonra:

```python
_log_environment_info()
```

- [ ] **Step 5: A-E akışında `_edit_param_space` çağrısı ekle**

Her A-E choice bloğunda, `selected_names` belirlendikten sonra ve `specs` oluşturulmadan önce:

```python
specs = [spec for spec in all_specs if spec.name in selected_names]
# Parametre uzayı düzenleme
edited_spaces: Dict[str, Dict[str, List[Any]]] = {}
for spec in specs:
    space = _build_numba_parameter_space(spec)
    edited = _edit_param_space(space, spec.name)
    edited_spaces[spec.name] = edited
```

`_tune_parameters` fonksiyonuna `edited_spaces` parametresi eklenir, `_build_numba_parameter_space` yerine kullanılır.

- [ ] **Step 6: A-E akışında `_save_convergence_history` çağrısı ekle**

Tuning tamamlandıktan sonra:

```python
_save_convergence_history(best_params, metadata)
```

- [ ] **Step 7: A-E akışında `_save_config` istemi ekle**

Benchmark sorusundan sonra:

```python
save_choice = input("\nAyarlari config olarak kaydetmek ister misiniz? [E/H]: ").strip().upper()
if save_choice == "E":
    cfg_path = _save_config(selected_problems, selected_names, {
        "profile": BENCHMARK_PROFILE,
        "mode": "S" if mode_sequential else "P",
        "tuning_runs": tuning_runs,
        "max_combinations": max_combinations,
        "workers": NUM_WORKERS,
    }, edited_spaces if edited_spaces else None)
    print(f"[SAVED] Config: {cfg_path}")
```

- [ ] **Step 8: G menüsü akışını ekle**

`choice == "F"` bloğundan sonra:

```python
elif choice == "G":
    configs = _list_configs()
    if not configs:
        print("[HATA] Kayitli config dosyasi bulunamadi.")
        input("Devam etmek icin Enter'a basin...")
        continue
    print("\n--- Mevcut Config Dosyalari ---")
    for idx, c in enumerate(configs, 1):
        print(f"  [{idx}] {c}")
    raw = input("\nSeciminiz: ").strip()
    if not raw.isdigit() or int(raw) < 1 or int(raw) > len(configs):
        print("[HATA] Gecersiz secim.")
        input("Devam etmek icin Enter'a basin...")
        continue
    cfg_path = os.path.join(CONFIGS_DIR, configs[int(raw) - 1])
    cfg = _load_config(cfg_path, all_problems, all_specs)
    if not cfg:
        input("Devam etmek icin Enter'a basin...")
        continue
    # Config'den seçimleri yükle
    prob_sel = cfg["problems"]
    algo_sel = cfg["algorithms"]
    settings = cfg.get("settings", {})
    # ... (seçimleri uygula, A-E veya F akışına yönlendir)
```

- [ ] **Step 9: `_tune_parameters` fonksiyonuna `edited_spaces` parametresi ekle**

Fonksiyon imzasını güncelle:

```python
def _tune_parameters(
    problems: List[DOEProblem],
    specs: List[StrategySpec],
    n_runs: int,
    max_combinations: int,
    workers: int,
    metadata: Dict[str, Any],
    skip_cached: bool,
    edited_spaces: Optional[Dict[str, Dict[str, List[Any]]]] = None,
) -> Dict[str, Dict[str, Any]]:
```

İçindeki `_build_numba_parameter_space(spec)` çağrısını:

```python
if edited_spaces and spec.name in edited_spaces:
    space = edited_spaces[spec.name]
else:
    space = _build_numba_parameter_space(spec)
```

olarak değiştir.

- [ ] **Step 10: Syntax kontrolü**

- [ ] **Step 11: Commit**

---

### Task 14: CLI Modu Uygulaması

**Files:**
- Modify: `academic_benchmark/run_smart_benchmark_numba_doe.py` — `main()` içindeki CLI bloğu

- [ ] **Step 1: CLI modu akışını uygula**

`cli_args` None değilse çalışacak akış:

```python
if cli_args:
    _log_environment_info()
    all_specs = _all_strategy_specs()
    all_problems = _load_problems_unified("all")

    if cli_args.get("config"):
        cfg = _load_config(cli_args["config"], all_problems, all_specs)
        if not cfg:
            return 1
        # Config'den seçimleri uygula
        # ... (Task 13 Step 8 ile aynı mantık)
    else:
        # Manuel CLI seçimleri
        if cli_args.get("problem"):
            # problem parsing
            pass
        if cli_args.get("algo"):
            # algo parsing
            pass
        # ... settings uygula

    # Çalıştır
    # ...
    return 0
```

- [ ] **Step 2: Syntax kontrolü**

- [ ] **Step 3: Commit**

---

### Task 15: Bölüm Ayırıcılar ve Final Organizasyon

**Files:**
- Modify: `academic_benchmark/run_smart_benchmark_numba_doe.py` — tüm dosya

- [ ] **Step 1: Bölüm ayırıcıları ekle**

Dosya içinde ilgili yerlere bölüm ayırıcı yorumlar ekle (tasarım dokümanı Bölüm 2.8'deki gibi).

- [ ] **Step 2: `_multi_select` fonksiyonunu kaldır (artık kullanılmıyor)**

Eğer hiçbir yerde çağrılmıyorsa kaldır.

- [ ] **Step 3: Final syntax kontrolü**

Run: `python -m py_compile academic_benchmark/run_smart_benchmark_numba_doe.py`

- [ ] **Step 4: Smoke test — time_matrix olmayan problem**

Run: `echo "E\n2\n1\n1\n\nS\n1\n1\nS\nY\nH\nQ\n" | python academic_benchmark/run_smart_benchmark_numba_doe.py`
Expected: DOE tuning completes, no crash

- [ ] **Step 5: Smoke test — F menüsü**

Run: `echo "F\n2\n1\n1\n\nS\n1\n\nY\nQ\n" | python academic_benchmark/run_smart_benchmark_numba_doe.py`
Expected: Direct benchmark completes

- [ ] **Step 6: Smoke test — parametre düzenleme**

Run: `echo "E\n2\n1\n1\n\n\n\n\n\n\nS\n1\n1\nS\nY\nH\nQ\n" | python academic_benchmark/run_smart_benchmark_numba_doe.py`
Expected: Parametre düzenleme ekranı görünür, Enter ile kabul çalışır

- [ ] **Step 7: Commit**

---

## Uygulama Sırası Özeti

| Sıra | Task | Tahmini Süre |
|------|------|-------------|
| 1 | Import'lar ve Sabitler | 5 dk |
| 2 | DOEProblem Genişletme | 3 dk |
| 3 | `_load_problems_unified` | 10 dk |
| 4 | `run_single_test_with_matrix` | 15 dk |
| 5 | `_evaluate_param_combo` Güncelleme | 10 dk |
| 6 | `_run_pool` Güncelleme | 5 dk |
| 7 | `_generate_combinations` | 5 dk |
| 8 | `_validate_param_value` + `_edit_param_space` | 15 dk |
| 9 | `_log_environment_info` | 3 dk |
| 10 | Config Fonksiyonları | 20 dk |
| 11 | `_save_convergence_history` | 10 dk |
| 12 | `_parse_cli_args` | 10 dk |
| 13 | `main()` Akışı | 30 dk |
| 14 | CLI Modu | 15 dk |
| 15 | Final Organizasyon + Test | 15 dk |
| | **TOPLAM** | **~170 dk** |
