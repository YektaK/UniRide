# Plan: Universal Problem Selector — Best of All Worlds

**Date:** 2026-05-06  
**Author:** GitHub Copilot  
**Goal:** Replace divergent problem-selection UX across `bildiri2026`, `master_sota_engine.py`, and `master_numba_engine.py` with a single, unified `ProblemSelector` class that supports *every* input mode: numbered indices, ranges, names, glob patterns, category aliases, dimension filters, optimal-value filters, exclusions, intersections, multi-round refinement, and saved presets.

---

## 1. Current State Analysis

### 1.1 Three Problem Representations

| Engine | Type | Properties | How loaded |
|--------|------|-----------|------------|
| **bildiri2026** | `dict` | `type`, `name`, `path_relative` | `data_manager.list_local_problems()` |
| **SOTA** | `TSPProblem` (dataclass) | `.name`, `.dimension`, `.category`, `.coordinates`, `.optimal`, `.edge_weight_type` | `load_problems(size_limit)` |
| **Numba** | `DOEProblem` (dataclass) | `.name`, `.dimension`, `.category`, `.coordinates`, `.optimal`, `.is_time_matrix`, `.time_matrix` | `load_problems()` |

**Critical gap**: bildiri2026 dicts have **no dimension** or `optimal` metadata. These must be enriched from the TSPLIB file on disk or from `TSPLIB_OPTIMALS` (already in `benchmark_utils.py`).

### 1.2 Current Selection UX per Engine

| Feature | bildiri2026 | SOTA | Numba |
|---------|:-----------:|:----:|:-----:|
| Numbered list (1..N) | ✅ | ❌ | ❌ |
| Category aliases only | ❌ | ✅ (only) | ❌ |
| Name-based selection | ❌ | ❌ | ✅ (only) |
| Size-limit filter | ❌ | ✅ | ✅ |
| Comma-separated numbers | ✅ | ❌ | ❌ |
| Range syntax (`1-5`) | ❌ | ❌ | ❌ |
| Dimension shown in menu | ❌ | ❌ | ❌ |
| Optimal value shown | ❌ | ❌ | ❌ |
| Multi-round refinement | ❌ | ❌ | ❌ |
| CLI `--problems` by name | ❌ | ✅ | ✅ |
| CLI `--size-limit` | ❌ | ✅ | ✅ |

### 1.3 Shared `benchmark_utils.py` — Already Available

`benchmark_utils.py` already exports (from attached code):

- `multi_select()` — numbered-list multi-select for algorithms
- `select_worker_count()` — worker count prompt
- `select_run_count()` — runs prompt
- `parse_index_or_all()` — simple "1,2,3 or all" parser
- `get_cpu_info()`, `ETATracker`, `TSPLIB_OPTIMALS`
- `generate_combinations()`, `save_config()`, `save_convergence_history()`
- `format_time()`, `clear_screen()`, `log_environment_info()`, etc.

**What's missing**: Any problem-listing or problem-selection functionality. This is where `ProblemSelector` will go.

---

## 2. Target UX Design

### 2.1 Interactive Menu

```
══════════════════════════════════════════════════════════════════════════
  PROBLEM SEÇİMİ                                Toplam: 47 | Seçili: 0
══════════════════════════════════════════════════════════════════════════
  Kategoriler:  small (n≤100) | medium (101-500) | large (500+)
  ────────────────────────────────────────────────────────────────────────
    #    Name                  n    Optimal      Kat
  ────────────────────────────────────────────────────────────────────────
  ▸[ 1] berlin52            n=  52      7542   [small ]
   [ 2] eil51               n=  51       426   [small ]
   [ 3] st70                n=  70       675   [small ]
  ▸[ 4] eil76               n=  76       538   [small ]
   [ 5] eil101              n= 101       629   [medium]
   [ 6] kroA100             n= 100     21282   [small ]
   ...
   [47] pr2392              n=2392    378032   [large ]
  ────────────────────────────────────────────────────────────────────────
  Syntax:  1,3,5 | 1-7 | berlin52 | eil* | >200 | <100
           !exclude | &category | all
  Kısayol:  small | medium | large | all | save:ad | load:ad
  ────────────────────────────────────────────────────────────────────────

  Seçim: small,!eil51,>100,10-15
  → 8 problem seçildi.
```

**▸** marks currently selected problems after each round.

### 2.2 Complete Input Grammar

| Token | Example | Meaning |
|-------|---------|---------|
| `all` | `all` | All problems |
| `small` / `medium` / `large` | `small` | Category filter by dimension |
| `N` | `5` | 1-based index |
| `N-M` | `3-7` | Range (inclusive), auto-fixes if reversed |
| `name` | `berlin52` | Exact name match (case-insensitive) |
| `pattern*` | `eil*`, `*100*` | Glob (`fnmatch`) against name |
| `>N` | `>200` | Dimension > N |
| `<N` | `<100` | Dimension < N (dim > 0) |
| `>=N` | `>=500` | Dimension >= N |
| `<=N` | `<=100` | Dimension <= N |
| `opt>N` | `opt>10000` | Optimal value > N |
| `opt<N` | `opt<1000` | Optimal value < N |
| `!token` | `!eil51` | Remove matched set from current selection |
| `&token` | `&small` | Intersect current selection with matched set |
| `save:name` | `save:mypaper` | Save current selection as preset |
| `load:name` | `load:mypaper` | Load a saved preset |

**Special commands** (in interactive mode):
| Command | Effect |
|---------|--------|
| `[Enter]` (empty) | Select all |
| `done` | Finish selection |
| `?` | Show help |
| `list` | Re-display the table |

### 2.3 Validation Rules

1. **Empty input** → select all (least-surprise default for benchmarks)
2. **Unknown name** → warning, token skipped
3. **Out-of-range index** → warning, token skipped
4. **Reversed range** (`7-3`) → auto-swap to `3-7`
5. **Glob with no matches** → warning, token skipped
6. **Exclusion on empty set** → no-op, no error
7. **Intersection on empty set** → empty result
8. **All tokens invalid** → empty result, user re-prompted
9. **`done` with empty selection** → confirm before exit
10. **Deduplication** — same problem via multiple tokens → included once

---

## 3. Implementation Plan

### Phase 1: Core — `benchmark_utils.py`

Add after `select_mode()` (around line 324) and before `# ── Parametre Araçları ──`.

#### Step 1.1: Generic Problem Adapter Functions

```python
# ── Problem Selection (Universal Selector) ──────────────────────────────

def _prob_name(p) -> str:
    """Get problem name from dict or dataclass."""
    return p["name"] if isinstance(p, dict) else getattr(p, "name", str(p))

def _prob_dim(p) -> int:
    """Get problem dimension from dict or dataclass."""
    return p.get("dimension", 0) if isinstance(p, dict) else getattr(p, "dimension", 0)

def _prob_optimal(p) -> Optional[int]:
    """Get optimal value. Falls back to TSPLIB_OPTIMALS dict."""
    if isinstance(p, dict):
        return TSPLIB_OPTIMALS.get(_prob_name(p).lower())
    opt = getattr(p, "optimal", None)
    if opt is not None:
        return opt
    opt2 = getattr(p, "optimal_score", None)
    if opt2 is not None:
        return opt2
    return TSPLIB_OPTIMALS.get(_prob_name(p).lower())

def _prob_category(p, dim: Optional[int] = None) -> str:
    """Classify problem by dimension."""
    d = dim if dim is not None else _prob_dim(p)
    if d <= 100:
        return "small"
    elif d <= 500:
        return "medium"
    return "large"
```

#### Step 1.2: `ProblemSelector` Class

**Constructor + Index Builder:**
```python
class ProblemSelector:
    """Universal interactive problem selector with multi-mode input."""

    def __init__(self, problems: Sequence[Any],
                 title: str = "PROBLEM SEÇİMİ",
                 presets_file: Optional[str] = None):
        self.title = title
        self.all_problems = list(problems)
        self.presets_file = presets_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            ".problem_presets.json"
        )
        self._build_index()

    def _build_index(self) -> None:
        """Sorted list, name→index map, category indices."""
        self.sorted = sorted(self.all_problems,
                             key=lambda p: _prob_name(p).lower())
        self.name_map: Dict[str, int] = {}
        for idx, p in enumerate(self.sorted):
            self.name_map[_prob_name(p).lower()] = idx
        self.cat_indices: Dict[str, List[int]] = {
            "small": [], "medium": [], "large": []
        }
        for idx, p in enumerate(self.sorted):
            cat = _prob_category(p, _prob_dim(p))
            if cat in self.cat_indices:
                self.cat_indices[cat].append(idx)
```

**Display:**
```python
    def display_table(self, selected: Optional[Set[int]] = None) -> None:
        """Print numbered table with name, dimension, optimal, category."""
        total = len(self.sorted)
        sel = len(selected) if selected else 0
        print(f"\n{'═' * 72}")
        print(f"  {self.title:<42} Toplam: {total} | Seçili: {sel}")
        print(f"{'═' * 72}")
        print("  Kategoriler:  small (n≤100) | medium (101-500) | large (500+)")
        print(f"  {'─' * 48}")
        print(f"  {'#':>3}  {'Name':<20} {'n':>5}  {'Optimal':>10}  {'Kat':<8}")
        print(f"  {'─' * 48}")
        for idx, p in enumerate(self.sorted, 1):
            name = _prob_name(p)
            dim = _prob_dim(p)
            opt = _prob_optimal(p)
            cat = _prob_category(p, dim)
            os_ = f"{opt:>10}" if opt is not None else "       N/A"
            mk = "▸" if selected is not None and (idx-1) in selected else " "
            print(f"  {mk}[{idx:>2}] {name:<20} n={dim:>5}  {os_}  [{cat}]")
        print(f"  {'─' * 48}")
        print("  Syntax:  1,3,5 | 1-7 | berlin52 | eil* | >200 | <100")
        print("           !exclude | &category | all")
        print("  Kısayol:  small | medium | large | all | save:ad | load:ad")
        print(f"  {'─' * 48}")
```

**Token Resolution Engine:**
```python
    def _resolve_token(self, token: str, current: Set[int]
                       ) -> Tuple[Set[int], List[str]]:
        """Resolve one token → set of indices + warning messages."""
        warnings: List[str] = []
        lower = token.lower()

        # Exclusion
        if lower.startswith("!"):
            inner, w2 = self._resolve_token(lower[1:], set())
            warnings.extend(w2)
            return current - inner, warnings

        # Intersection
        if lower.startswith("&"):
            inner, w2 = self._resolve_token(lower[1:], current)
            warnings.extend(w2)
            return current & inner, warnings

        # All
        if lower == "all":
            return set(range(len(self.sorted))), warnings

        # Category
        if lower in self.cat_indices:
            return set(self.cat_indices[lower]), warnings

        # Presets
        if lower.startswith("save:"):
            self._save_preset(lower[5:], sorted(current))
            warnings.append(f"✅ '{lower[5:]}' kaydedildi.")
            return current, warnings
        if lower.startswith("load:"):
            loaded = self._load_preset(lower[5:])
            if loaded is not None:
                warnings.append(f"📂 '{lower[5:]}' yüklendi.")
                return set(loaded), warnings
            warnings.append(f"⚠️ Preset '{lower[5:]}' bulunamadı.")
            return current, warnings

        # Dimension filters
        for prefix in (">=", "<=", ">", "<"):
            if lower.startswith(prefix):
                try:
                    val = int(lower[len(prefix):])
                    op = {"<": lambda d: 0 < d < val,
                          "<=": lambda d: 0 < d <= val,
                          ">": lambda d: d > val,
                          ">=": lambda d: d >= val}[prefix]
                    return {i for i, p in enumerate(self.sorted)
                            if op(_prob_dim(p))}, warnings
                except ValueError:
                    break

        # Optimal filters
        for prefix in ("opt>", "opt<"):
            if lower.startswith(prefix):
                try:
                    val = int(lower[len(prefix):])
                    op = {"opt>": lambda o: o is not None and o > val,
                          "opt<": lambda o: o is not None and o < val}[prefix]
                    return {i for i, p in enumerate(self.sorted)
                            if op(_prob_optimal(p))}, warnings
                except ValueError:
                    break

        # Glob
        import fnmatch
        if "*" in lower or "?" in lower:
            r = {i for i, p in enumerate(self.sorted)
                 if fnmatch.fnmatch(_prob_name(p).lower(), lower)}
            return r, warnings

        # Range N-M
        if "-" in lower:
            parts = lower.split("-")
            if len(parts) == 2:
                try:
                    a, b = int(parts[0]), int(parts[1])
                    a, b = (a, b) if a <= b else (b, a)
                    return {i for i in range(max(0, a-1), min(b, len(self.sorted)))}, warnings
                except ValueError:
                    pass

        # Single index
        try:
            idx = int(lower) - 1
            if 0 <= idx < len(self.sorted):
                return {idx}, warnings
            warnings.append(f"⚠️ İndeks {int(lower)} geçersiz (1-{len(self.sorted)}).")
            return set(), warnings
        except ValueError:
            pass

        # Name match
        if lower in self.name_map:
            return {self.name_map[lower]}, warnings

        warnings.append(f"⚠️ Bilinmeyen token: '{token}' — atlandı.")
        return set(), warnings

    def resolve_tokens(self, raw: str, current: Optional[Set[int]] = None
                       ) -> Tuple[Set[int], List[str]]:
        """Parse comma-separated string → set of indices."""
        if current is None:
            current = set()
        all_warnings: List[str] = []
        for t in [t.strip() for t in raw.split(",") if t.strip()]:
            result, w = self._resolve_token(t, current)
            current = result
            all_warnings.extend(w)
        return current, all_warnings
```

**Interactive Loop:**
```python
    def interactive_select(self) -> List[Any]:
        """Multi-round interactive selection."""
        current: Set[int] = set()
        print("\n  [Enter]=tümü  'done'=bitir  '?'=yardım  'list'=tablo")

        while True:
            self.display_table(current)
            raw = input("\n  Seçim: ").strip()

            if not raw:
                current = set(range(len(self.sorted)))
                break
            lower = raw.lower()
            if lower == "done":
                if not current:
                    yn = input("  Hiç seçilmedi, çıkılsın mı? (e/H): ").strip().lower()
                    if yn != "e":
                        continue
                break
            if lower == "?":
                self._show_help()
                continue
            if lower == "list":
                continue

            current, warnings = self.resolve_tokens(raw, current)
            for w in warnings:
                print(f"  {w}")
            print(f"  → {len(current)} problem seçildi.")
            if not current:
                print("  💡 Geçerli bir seçim yapın veya 'done' ile çıkın.")

        return [self.sorted[i] for i in sorted(current)]
```

**Quick Select (non-interactive / CLI):**
```python
    def quick_select(self, token_str: str) -> List[Any]:
        """Single-shot selection for CLI automation."""
        if not token_str or token_str.strip().lower() == "all":
            return list(self.sorted)
        current, _ = self.resolve_tokens(token_str)
        return [self.sorted[i] for i in sorted(current)]
```

**Presets:**
```python
    def _presets_path(self) -> str:
        return self.presets_file

    def _load_presets(self) -> Dict[str, List[str]]:
        if not os.path.exists(self._presets_path()):
            return {}
        try:
            with open(self._presets_path(), "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_preset(self, name: str, indices: List[int]) -> None:
        presets = self._load_presets()
        presets[name] = [_prob_name(self.sorted[i]) for i in indices]
        os.makedirs(os.path.dirname(self._presets_path()) or ".", exist_ok=True)
        with open(self._presets_path(), "w", encoding="utf-8") as f:
            json.dump(presets, f, indent=2, ensure_ascii=False)

    def _load_preset(self, name: str) -> Optional[List[int]]:
        presets = self._load_presets()
        names = presets.get(name)
        if not names:
            return None
        indices = [self.name_map[n.lower()] for n in names
                   if n.lower() in self.name_map]
        return sorted(set(indices))

    def list_presets(self) -> List[str]:
        return list(self._load_presets().keys())
```

**Help:**
```python
    @staticmethod
    def _show_help() -> None:
        print("""
  ── SEÇİM YARDIMI ──────────────────────────────────
  all           → Tüm problemler
  small/medium/large → Kategori
  1,3,5         → 1., 3. ve 5. problem
  1-7           → 1-7 arası
  berlin52      → İsim
  eil*          → eil ile başlayanlar
  >200          → boyut > 200
  <100          → boyut < 100
  >=500         → boyut ≥ 500
  opt<1000      → optimal < 1000
  !berlin52     → Hariç tut
  &small        → Kesişim
  save:my_set   → Kaydet
  load:my_set   → Yükle
  ───────────────────────────────────────────────────
  Örn: small,!eil51,>100,10-15
  ───────────────────────────────────────────────────
  """)
```

---

### Phase 2: SOTA Engine — `master_sota_engine.py`

#### Step 2.1: Import

Add `ProblemSelector` to the existing `from benchmark_utils import` block.

#### Step 2.2: Add `--select` CLI Argument

```python
parser.add_argument("--select", type=str, default=None,
    help="Unified problem selection (örn: 'small,berlin52,10-15')")
```

#### Step 2.3: Replace `_select_problem_scope()` Call Site

**In `_main_loop()`, replace:**
```python
scope = _select_problem_scope()
selected_problems = [p for p in all_problems if p.category == scope or scope == "all"]
```
**With:**
```python
if args.select:
    selector = ProblemSelector(all_problems)
    selected_problems = selector.quick_select(args.select)
elif args.problems:
    wanted = [x.strip().lower() for x in args.problems.split(",")]
    selected_problems = [p for p in all_problems if p.name.lower() in wanted]
elif args.size_limit:
    selected_problems = [p for p in all_problems if p.dimension <= args.size_limit]
else:
    selector = ProblemSelector(all_problems)
    selected_problems = selector.interactive_select()

if not selected_problems:
    print("[UYARI] Problem seçilmedi.")
    input("Devam etmek icin Enter...")
    continue
```

#### Step 2.4: Remove `_select_problem_scope()` Function

Delete the function definition entirely (~4 lines).

---

### Phase 3: Numba Engine — `master_numba_engine.py`

#### Step 3.1: Import

Add `ProblemSelector` to the existing `from benchmark_utils import` block.

#### Step 3.2: Add `--select` CLI Argument

```python
parser.add_argument("--select", type=str, default=None,
    help="Unified problem selection (örn: 'small,berlin52,10-15')")
```

#### Step 3.3: Replace Two-Option Block

**Replace lines ~828-846 (the `[1] Kapsamlı Seçim / [2] Spesifik Problemler` block):**

```python
from benchmark_utils import ProblemSelector

if args.select:
    selector = ProblemSelector(all_problems)
    selected_problems = selector.quick_select(args.select)
elif args.problems:
    wanted = [x.strip().lower() for x in args.problems.split(",")]
    selected_problems = [p for p in all_problems if p.name.lower() in wanted]
elif args.size_limit:
    selected_problems = [p for p in all_problems if p.dimension <= args.size_limit]
else:
    selector = ProblemSelector(all_problems)
    selected_problems = selector.interactive_select()

if not selected_problems:
    print("[UYARI] Problem seçilmedi.")
    input("Devam etmek icin Enter'a basın...")
    continue
```

---

### Phase 4: bildiri2026 Engine — `3_run_benchmark.py` (Optional)

#### Step 4.1: Enrich Dict Problems

bildiri2026 problems are flat dicts without dimension. Enrich them by reading TSPLIB files:

```python
# After: problems = data_manager.list_local_problems()
for p in problems:
    if p["type"] == "tsplib":
        tsp_path = os.path.join(SCRIPT_DIR, p["path_relative"])
        try:
            from benchmarks.tsplib_benchmark import parse_tsplib
            tsp = parse_tsplib(tsp_path)
            p["dimension"] = len(tsp["coordinates"])
        except Exception:
            p["dimension"] = 0
    else:
        p["dimension"] = 0
```

#### Step 4.2: Replace Selection Block

**Replace lines ~113-134 with:**
```python
from benchmark_utils import ProblemSelector

if len(sys.argv) > 2:
    selector = ProblemSelector(problems)
    selected_problems = selector.quick_select(sys.argv[2])
else:
    selector = ProblemSelector(problems)
    selected_problems = selector.interactive_select()
```

---

### Phase 5: Tests

New file: `academic_benchmark/tests/test_problem_selector.py` — 36 test cases:

| # | Test Name | What It Validates |
|---|-----------|-------------------|
| 1 | `test_prob_name_dict` | `_prob_name()` on dict |
| 2 | `test_prob_name_obj` | `_prob_name()` on dataclass |
| 3 | `test_prob_dim_dict` | `_prob_dim()` on dict |
| 4 | `test_prob_dim_obj` | `_prob_dim()` on dataclass |
| 5 | `test_prob_dim_missing` | `_prob_dim()` returns 0 when missing |
| 6 | `test_prob_category` | Boundary: 100=small, 101=medium, 500=medium, 501=large |
| 7 | `test_sorted_order` | Problems sorted alphabetically by name |
| 8 | `test_name_map` | Name map contains all problems |
| 9 | `test_category_indices` | Each category has correct indices |
| 10 | `test_category_all_present` | All three categories exist |
| 11 | `test_token_all` | `"all"` → all problems |
| 12 | `test_token_single_index` | `"1"` → one problem |
| 13 | `test_token_multiple_indices` | `"1,3,5"` → three |
| 14 | `test_token_range` | `"1-4"` → four |
| 15 | `test_token_range_reversed` | `"4-1"` → same as `1-4` |
| 16 | `test_token_category_small` | `"small"` → all small |
| 17 | `test_token_category_medium` | `"medium"` → all medium |
| 18 | `test_token_category_large` | `"large"` → all large |
| 19 | `test_token_name_exact` | `"berlin52"` → one |
| 20 | `test_token_name_case_insensitive` | `"BERLIN52"` == `"berlin52"` |
| 21 | `test_token_glob_prefix` | `"eil*"` → eil51, eil76, eil101 |
| 22 | `test_token_dim_gt` | `">500"` → dim > 500 |
| 23 | `test_token_dim_lt` | `"<60"` → 0 < dim < 60 |
| 24 | `test_token_dim_gte` | `">=100"` → dim >= 100 |
| 25 | `test_token_dim_lte` | `"<=70"` → dim <= 70 |
| 26 | `test_token_exclude` | `"small,!eil51"` → small minus eil51 |
| 27 | `test_token_exclude_range` | `"all,!1-3"` → all minus first 3 |
| 28 | `test_token_intersect` | `"small,&1-3"` → small ∩ first 3 |
| 29 | `test_token_mixed_complex` | `"small,!eil51,>55"` → union |
| 30 | `test_token_unknown_warns` | Unknown name → warning |
| 31 | `test_token_out_of_range_warns` | Invalid index → warning |
| 32 | `test_token_dedup` | `"1,1"` === `"1"` |
| 33 | `test_quick_select_all` | `quick_select("all")` |
| 34 | `test_quick_select_mixed` | `quick_select("small,berlin52")` |
| 35 | `test_preset_save_load` | Save then load |
| 36 | `test_preset_not_found` | Missing preset → None |

---

## 4. File Change Summary

| File | Action | Est. Lines |
|------|--------|-----------|
| `benchmark_utils.py` | Add adapter fns + `ProblemSelector` class | **+280** |
| `master_sota_engine.py` | Import, replace `_select_problem_scope()`, add `--select` | **~15 changed** |
| `master_numba_engine.py` | Import, replace two-option block, add `--select` | **~15 changed** |
| `bildiri2026/3_run_benchmark.py` | (Optional) Enrich dicts, replace selection block | **~12 changed** |
| `tests/test_problem_selector.py` | **New file** — 36 tests | **+230** |

**Total**: ~540 lines across 5 files.

---

## 5. Backward Compatibility

| Existing Feature | Status | Notes |
|-----------------|--------|-------|
| SOTA `--problems berlin52,eil51` | ✅ Still works | Checked first in priority chain |
| SOTA `--size-limit 200` | ✅ Still works | Checked second |
| SOTA `--mode default/tuning` | ✅ Unchanged | |
| Numba `--problems berlin52,eil51` | ✅ Still works | |
| Numba `--size-limit 200` | ✅ Still works | |
| Numba `[1] Kapsamlı Seçim` / `[2] Spesifik` | ✅ Replaced, not broken | New UX supersedes both |
| bildiri2026 `sys.argv[2]` numbers | ✅ If unified, `--select` syntax also accepted | |
| `select_worker_count()` / `select_run_count()` | ✅ Unchanged | |
| `multi_select()` for algorithms | ✅ Unchanged | |
| ALL existing benchmark execution code | ✅ Unchanged | `select_problems` returns same object types |

---

## 6. Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| bildiri2026 dicts lack dimension | **Certain** | Enrich from TSPLIB file parse or `TSPLIB_OPTIMALS` |
| Large problem list overflows terminal | Low | Current max ~80; if >200, add pagination (`page:N`) |
| `fnmatch` not imported | Very Low | Standard library — just add import |
| `json` not imported in `benchmark_utils.py` | Low | Check existing imports; add if missing |
| User enters negative index | Low | Clamped: `max(0, a-1)` in range, `0 <= idx` check |
| Glob with `*` matches too broadly | Low | Intentional — user chose glob |
| `done` confirmed exit with 0 selected | Low | Confirm prompt added |

---

## 7. Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Class vs functions | `ProblemSelector` class | Stateful — index, current selection, presets |
| Dict vs dataclass handling | Adapter functions (`_prob_name`, etc.) | Cleaner than `getattr`/`isinstance` everywhere |
| Exclusion syntax | `!token` | Matches grep/search conventions |
| Intersection syntax | `&token` | Useful for power users; rare but valuable |
| Range reversal | Auto-fix swap | User-friendly, no error for `7-3` |
| Empty input default | All problems | Least-surprise for benchmark runs |
| Default to `all` on unknown token | Show warning, skip | Resilient — partial selections still work |
| Preset storage | `.problem_presets.json` | Simple, no deps, git-shareable |
| Priority chain | `--select` > `--problems` > `--size-limit` > interactive | Most explicit wins |
| bildiri2026 enrichment | Parse TSPLIB for dimension | Only way to get category/dimension metadata for dicts |

---

## 8. Verification Checklist

- [ ] `pytest academic_benchmark/tests/test_problem_selector.py -v` — all 36 pass
- [ ] SOTA interactive: test each token type, refinement rounds
- [ ] SOTA CLI: `--problems berlin52,eil51` — backward compatible
- [ ] SOTA CLI: `--size-limit 100` — backward compatible
- [ ] SOTA CLI: `--select "small,berlin52,10-15"` — new syntax works
- [ ] Numba interactive: same verification as SOTA
- [ ] Numba CLI: `--problems`, `--size-limit` — backward compat
- [ ] Numba CLI: `--select` — new syntax works
- [ ] bildiri2026 (if unified): dict enrichment works, all token types available
- [ ] No existing benchmark execution logic broken
- [ ] `select_worker_count()`, `select_run_count()`, `multi_select()` unchanged