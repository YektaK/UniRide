# Universal Problem Selector — Unified Plan

**Date:** 2026-05-06
**Status:** READY FOR IMPLEMENTATION
**Scope:** `academic_benchmark/benchmark_utils.py`, `master_sota_engine.py`, `master_numba_engine.py`, tests

---

# PART A — FINAL PLAN (Selected Approach)

---

## A1. Reference Analysis

### A1.1 Three Problem Representations

| Engine | Type | Properties | Loading function |
|--------|------|------------|-----------------|
| bildiri2026 | `dict` | `type`, `name`, `path_relative` (no dimension/optimal) | `data_manager.list_local_problems()` |
| SOTA | `TSPProblem` dataclass | `.name`, `.dimension`, `.category`, `.coordinates`, `.optimal` | `load_problems(size_limit)` |
| Numba | `DOEProblem` dataclass | `.name`, `.dimension`, `.category`, `.coordinates`, `.optimal`, `.is_time_matrix` | `load_problems()` |

### A1.2 Gap Analysis

| Feature | bildiri2026 | SOTA | Numba |
|---------|------------|------|-------|
| Numbered problem list | ✅ | ❌ | ❌ |
| Category aliases only | ❌ | ✅ | ❌ |
| Name-based selection | ❌ | ❌ | ✅ |
| Size-limit filter | ❌ | ✅ | ✅ |
| Comma-separated numbers | ✅ | ❌ | ❌ |
| Range syntax (`1-5`) | ❌ | ❌ | ❌ |
| Dimension/optimal in menu | ❌ | ❌ | ❌ |
| Multi-round refinement | ❌ | ❌ | ❌ |
| CLI `--problems` by name | ❌ | ✅ | ✅ |
| CLI `--size-limit` | ❌ | ✅ | ✅ |

---

## A2. Target UX Design

### A2.1 Interactive Menu

```
════════════════════════════════════════════════════════════════════════
  PROBLEM SEÇİMİ                                Toplam: 47 | Seçili: 0
════════════════════════════════════════════════════════════════════════
  Kategoriler:  small (n≤100) | medium (101-500) | large (500+)
  ────────────────────────────────────────────────────────────────────────
    #    Name                  n    Optimal      Kat
  ────────────────────────────────────────────────────────────────────────
  ▸[ 1] berlin52            n=  52      7542   [small ]
   [ 2] eil51               n=  51       426   [small ]
   [ 3] st70                n=  70       675   [small ]
  ▸[ 4] eil76               n=  76       538   [small ]
   [ 5] eil101              n= 101       629   [medium]
  ────────────────────────────────────────────────────────────────────────
  Syntax:  1,3,5 | 1-7 | berlin52 | small | medium | large | all
  ────────────────────────────────────────────────────────────────────────

  Seçim: small,!eil51
  → 8 problem seçildi.
```

`▸` marks currently selected problems after each refinement round.

### A2.2 Input Grammar

| Token | Example | Meaning |
|-------|---------|---------|
| `all` | `all` | All problems |
| `small` / `medium` / `large` | `small` | Category filter |
| `N` | `5` | 1-based index |
| `N-M` | `3-7` | Range (inclusive), auto-swaps if reversed |
| `name` | `berlin52` | Exact name match (case-insensitive) |
| `!token` | `!eil51` | Exclusion — remove matched set from selection |

Tokens are comma-separated and union-merged. `!` prefix removes instead of adding.

### A2.3 Validation Rules

1. Empty input → select all (least-surprise default)
2. Unknown name → warning, skip
3. Out-of-range index → warning, skip
4. Reversed range (`7-3`) → auto-swap to `3-7`
5. All tokens invalid → re-prompt
6. Deduplication by `.name`
7. Exclusion on empty set → no-op

---

## A3. Implementation Steps

### Step 1: Add `ProblemSelector` class to `benchmark_utils.py`

Insert after `select_mode()` (~line 320), before `# ── Parametre Araçları`.

**Adapter functions** (handle dicts and dataclasses uniformly):

```python
def _prob_name(p) -> str:
    return p["name"] if isinstance(p, dict) else getattr(p, "name", str(p))

def _prob_dim(p) -> int:
    return p.get("dimension", 0) if isinstance(p, dict) else getattr(p, "dimension", 0)

def _prob_optimal(p) -> Optional[int]:
    if isinstance(p, dict):
        return TSPLIB_OPTIMALS.get(_prob_name(p).lower())
    opt = getattr(p, "optimal", None)
    if opt is not None:
        return opt
    return TSPLIB_OPTIMALS.get(_prob_name(p).lower())

def _prob_category(p, dim: Optional[int] = None) -> str:
    d = dim if dim is not None else _prob_dim(p)
    if d <= 100:
        return "small"
    elif d <= 500:
        return "medium"
    return "large"
```

**Constructor + index builder:**

```python
class ProblemSelector:
    def __init__(self, problems: Sequence[Any], title: str = "PROBLEM SEÇİMİ"):
        self.title = title
        self.all_problems = list(problems)
        self._build_index()

    def _build_index(self) -> None:
        self.sorted = sorted(self.all_problems, key=lambda p: _prob_name(p).lower())
        self.name_map: Dict[str, int] = {}
        for idx, p in enumerate(self.sorted):
            self.name_map[_prob_name(p).lower()] = idx
        self.cat_indices: Dict[str, List[int]] = {"small": [], "medium": [], "large": []}
        for idx, p in enumerate(self.sorted):
            cat = _prob_category(p)
            if cat in self.cat_indices:
                self.cat_indices[cat].append(idx)
```

**Display table:**

```python
    def display_table(self, selected: Optional[Set[int]] = None) -> None:
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
        print("  Syntax:  1,3,5 | 1-7 | berlin52 | small | medium | large | all")
        print("           !token = exclude")
        print(f"  {'─' * 48}")
```

**Token resolution engine:**

```python
    def _resolve_token(self, token: str, current: Set[int]) -> Tuple[Set[int], List[str]]:
        warnings: List[str] = []
        lower = token.lower()

        # Exclusion
        if lower.startswith("!"):
            inner, w2 = self._resolve_token(lower[1:], set())
            warnings.extend(w2)
            return current - inner, warnings

        # All
        if lower == "all":
            return set(range(len(self.sorted))), warnings

        # Category
        if lower in self.cat_indices:
            return set(self.cat_indices[lower]), warnings

        # Range N-M
        if "-" in lower and not lower.startswith("-"):
            parts = lower.split("-", 1)
            if len(parts) == 2:
                try:
                    a, b = int(parts[0]), int(parts[1])
                    a, b = min(a, b), max(a, b)  # auto-swap
                    return {i for i in range(max(0, a-1), min(b, len(self.sorted)))}, warnings
                except ValueError:
                    pass

        # Single index
        if lower.isdigit():
            idx = int(lower) - 1
            if 0 <= idx < len(self.sorted):
                return {idx}, warnings
            warnings.append(f"⚠️ İndeks {int(lower)} geçersiz (1-{len(self.sorted)}).")
            return set(), warnings

        # Name match
        if lower in self.name_map:
            return {self.name_map[lower]}, warnings

        warnings.append(f"⚠️ Bilinmeyen token: '{token}' — atlandı.")
        return set(), warnings

    def resolve_tokens(self, raw: str, current: Optional[Set[int]] = None) -> Tuple[Set[int], List[str]]:
        if current is None:
            current = set()
        all_warnings: List[str] = []
        for t in [t.strip() for t in raw.split(",") if t.strip()]:
            result, w = self._resolve_token(t, current)
            current = result
            all_warnings.extend(w)
        return current, all_warnings
```

**Interactive selection (multi-round):**

```python
    def interactive_select(self) -> List[Any]:
        current: Set[int] = set()
        while True:
            self.display_table(current)
            raw = input("\n  Seçim [Enter=tümü, done=bitir, ?=yardım]: ").strip()
            if not raw:
                current = set(range(len(self.sorted)))
                break
            if raw.lower() == "done":
                if not current:
                    yn = input("  Hiç seçilmedi, çıkılsın mı? (e/H): ").strip().lower()
                    if yn != "e":
                        continue
                break
            if raw == "?":
                self._show_help()
                continue
            current, warnings = self.resolve_tokens(raw, current)
            for w in warnings:
                print(f"  {w}")
            print(f"  → {len(current)} problem seçildi.")
        return [self.sorted[i] for i in sorted(current)]
```

**Quick select (CLI / non-interactive):**

```python
    def quick_select(self, token_str: str) -> List[Any]:
        if not token_str or token_str.strip().lower() == "all":
            return list(self.sorted)
        current, _ = self.resolve_tokens(token_str)
        return [self.sorted[i] for i in sorted(current)]
```

**Help text:**

```python
    @staticmethod
    def _show_help() -> None:
        print("""
  ── SEÇİM YARDIMI ──────────────────────────────────
  all           → Tüm problemler
  small/medium/large → Kategori filtresi
  1,3,5         → 1., 3. ve 5. problem
  1-7           → 1-7 arası (ters yazılırsa düzeltilir)
  berlin52      → İsimle eşleşme (büyük/küçük harf duyarsız)
  !berlin52     → Hariç tut
  Karma: small,!eil51,10-15
  ───────────────────────────────────────────────────
  """)
```

### Step 2: Update `master_sota_engine.py`

1. Add `ProblemSelector` to the `from benchmark_utils import` block
2. Add `--select` CLI argument:
   ```python
   parser.add_argument("--select", type=str, default=None,
       help="Unified problem selection (örn: 'small,berlin52,10-15')")
   ```
3. In the CLI branch, add `--select` as highest priority:
   ```python
   if args.select:
       selector = ProblemSelector(all_problems)
       selected_problems = selector.quick_select(args.select)
   elif args.problems:
       wanted = [x.strip().lower() for x in args.problems.split(",")]
       selected_problems = [p for p in all_problems if p.name.lower() in wanted]
   elif args.size_limit:
       selected_problems = [p for p in all_problems if p.dimension <= args.size_limit]
   ```
4. In the interactive branch, replace `_select_problem_scope()`:
   ```python
   selector = ProblemSelector(all_problems)
   selected_problems = selector.interactive_select()
   if not selected_problems:
       print("[UYARI] Problem seçilmedi.")
       input("Devam etmek icin Enter...")
       continue
   ```
5. Delete `_select_problem_scope()` function definition (~4 lines)

### Step 3: Update `master_numba_engine.py`

1. Add `ProblemSelector` to the `from benchmark_utils import` block
2. Add `--select` CLI argument (same as SOTA)
3. In the CLI branch, add `--select` as highest priority (same pattern)
4. In the interactive branch, replace the two-option block (lines ~828-846):
   ```python
   selector = ProblemSelector(all_problems)
   selected_problems = selector.interactive_select()
   if not selected_problems:
       print("Seçilen kriterlere uygun problem bulunamadı.")
       input("Devam etmek için Enter'a basın...")
       continue
   ```

### Step 4: Write Tests

**New file:** `academic_benchmark/tests/test_problem_selector.py`

Create test data using a simple mock:
```python
from dataclasses import dataclass

@dataclass
class MockProblem:
    name: str
    dimension: int
    category: str
    optimal: int = 0

MOCK_PROBLEMS = [
    MockProblem("berlin52", 52, "small", 7542),
    MockProblem("eil51", 51, "small", 426),
    MockProblem("eil76", 76, "small", 538),
    MockProblem("eil101", 101, "medium", 629),
    MockProblem("kroA100", 100, "small", 21282),
    MockProblem("rd100", 100, "small", 7910),
    MockProblem("a280", 280, "medium", 2579),
    MockProblem("pr1002", 1002, "large", 259045),
]
```

Test cases (16):

| # | Test | Validates |
|---|------|-----------|
| 1 | `test_prob_name_dict` | Adapter on `{"name": "x"}` |
| 2 | `test_prob_name_obj` | Adapter on dataclass |
| 3 | `test_prob_dim_missing` | Returns 0 when absent |
| 4 | `test_prob_category_boundaries` | 100=small, 101=medium, 501=large |
| 5 | `test_sorted_alphabetically` | Index order |
| 6 | `test_token_all` | `"all"` → 8 results |
| 7 | `test_token_single_index` | `"1"` → berlin52 |
| 8 | `test_token_multiple_indices` | `"1,3,5"` → 3 results |
| 9 | `test_token_range` | `"1-4"` → 4 results |
| 10 | `test_token_range_reversed` | `"4-1"` → same as `1-4` |
| 11 | `test_token_category` | `"small"` → all small |
| 12 | `test_token_name_exact` | `"berlin52"` → 1 result |
| 13 | `test_token_name_case` | `"BERLIN52"` → same as above |
| 14 | `test_token_exclude` | `"small,!eil51"` → small minus eil51 |
| 15 | `test_token_unknown_warns` | Unknown name → warning |
| 16 | `test_token_dedup` | `"1,1,2"` → 2 results |

---

## A4. File Change Summary

| File | Action | Est. Lines |
|------|--------|-----------|
| `benchmark_utils.py` | Add adapter fns + `ProblemSelector` class | **+200** |
| `master_sota_engine.py` | Import, replace `_select_problem_scope()`, add `--select` | **~20 changed** |
| `master_numba_engine.py` | Import, replace two-option block, add `--select` | **~20 changed** |
| `tests/test_problem_selector.py` | New file — 16 tests | **+130** |

**Total: ~370 lines across 4 files.**

---

## A5. Backward Compatibility

| Existing Feature | Status |
|-----------------|--------|
| SOTA `--problems berlin52,eil51` | ✅ Still works (second priority) |
| SOTA `--size-limit 200` | ✅ Still works (third priority) |
| SOTA `--mode default/tuning` | ✅ Unchanged |
| Numba `--problems`, `--size-limit` | ✅ Still works |
| `select_worker_count()`, `select_run_count()`, `multi_select()` | ✅ Unchanged |
| All benchmark execution logic | ✅ Unchanged — selector returns same object types |

CLI priority chain: `--select` > `--problems` > `--size-limit` > interactive

---

## A6. Compatibility & Constraints

| Constraint | Status |
|-----------|--------|
| Windows 11 | ✅ No platform-specific code |
| Python 3.14.3 | ✅ `Sequence`, `Optional`, `set`, `dict` — all compatible |
| NumPy 2.4.4 | ✅ Not used in selection logic |
| Numba 0.65.0 | ✅ Not used in selection logic |

---

## A7. Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `getattr` fails on unexpected type | Low | Adapter functions handle dicts and dataclasses |
| Large problem list overflows terminal | Low | Current max ~80; add pagination if >200 later |
| User enters negative index | Low | `max(0, a-1)` in range, `0 <= idx` check |
| Reversed range `7-3` | Low | Auto-swap via `min/max` |
| Category name collides with problem name | Very Low | Categories checked first |

---

## A8. Verification Checklist

- [ ] `pytest academic_benchmark/tests/test_problem_selector.py -v` — all 16 pass
- [ ] SOTA interactive: test each token type
- [ ] SOTA CLI: `--problems berlin52,eil51` — backward compatible
- [ ] SOTA CLI: `--size-limit 100` — backward compatible
- [ ] SOTA CLI: `--select "small,berlin52,10-15"` — works
- [ ] Numba interactive: same verification
- [ ] Numba CLI: `--problems`, `--size-limit` — backward compat
- [ ] Numba CLI: `--select` — works
- [ ] No existing benchmark execution logic broken

---

---

# PART B — REFERENCE ALTERNATIVE (Not Selected)

The following is the full original alternative plan considered during the design phase. It is preserved here for context and future reference.

---

## B1. Original Plan Overview

**Title:** Universal Problem Selector — Best of All Worlds
**Author:** GitHub Copilot
**Approach:** Full-featured `ProblemSelector` class with 17 token types, presets, glob patterns, dimension/optimal filters, exclusion, intersection, and multi-round refinement.

## B2. Input Grammar (Full)

| Token | Example | Meaning |
|-------|---------|---------|
| `all` | `all` | All problems |
| `small` / `medium` / `large` | `small` | Category filter |
| `N` | `5` | 1-based index |
| `N-M` | `3-7` | Range (inclusive) |
| `name` | `berlin52` | Exact name match |
| `pattern*` | `eil*`, `*100*` | Glob (`fnmatch`) |
| `>N` / `<N` / `>=N` / `<=N` | `>200`, `<=100` | Dimension filters |
| `opt>N` / `opt<N` | `opt>10000` | Optimal value filters |
| `!token` | `!eil51` | Exclusion |
| `&token` | `&small` | Intersection |
| `save:name` | `save:mypaper` | Save selection as preset |
| `load:name` | `load:mypaper` | Load saved preset |

## B3. Additional Commands

| Command | Effect |
|---------|--------|
| `[Enter]` (empty) | Select all |
| `done` | Finish selection |
| `?` | Show help |
| `list` | Re-display table |

## B4. Preset System

Stored in `.problem_presets.json` next to `benchmark_utils.py`. Each preset maps a name to a list of problem names.

## B5. bildiri2026 Enrichment (Phase 4)

Parse TSPLIB files to add `dimension` metadata to flat dicts:
```python
for p in problems:
    if p["type"] == "tsplib":
        tsp = parse_tsplib(os.path.join(SCRIPT_DIR, p["path_relative"]))
        p["dimension"] = len(tsp["coordinates"])
```

## B6. Test Plan

36 test cases covering all 17 token types, edge cases, presets, and quick_select.

## B7. File Change Summary (Original)

| File | Action | Est. Lines |
|------|--------|-----------|
| `benchmark_utils.py` | Add adapter fns + full `ProblemSelector` | **+280** |
| `master_sota_engine.py` | Import, replace, add `--select` | **~15 changed** |
| `master_numba_engine.py` | Import, replace, add `--select` | **~15 changed** |
| `bildiri2026/3_run_benchmark.py` | (Optional) Enrich dicts, replace selection | **~12 changed** |
| `tests/test_problem_selector.py` | **New file** — 36 tests | **+230** |

**Total: ~540 lines across 5 files.**

---

---

# PART C — COMPARATIVE COMMENTARY

For each distinct feature or design decision in Plan B, the following explains why it was deprioritized or rejected in favor of Plan A.

---

### C1. Glob Patterns (`fnmatch`: `eil*`, `*100*`)

**Plan B:** Adds `import fnmatch` and pattern matching inside `_resolve_token`.
**Decision:** Rejected.
**Rationale:** The TSPLIB problem set is small (~47 files). Users know exact problem names. Glob adds a dependency (`fnmatch`), implementation complexity (~8 lines in the resolver), and a test case for a feature that provides marginal value over exact name matching. If a user wants all `eil` problems, they can type `eil51,eil76,eil101` — three tokens. The cost-benefit ratio is unfavorable for the current problem set size.

---

### C2. Dimension Filters (`>N`, `<N`, `>=N`, `<=N`)

**Plan B:** Adds four prefix-comparison operators in the resolver.
**Decision:** Rejected.
**Rationale:** Category aliases (`small`, `medium`, `large`) already provide dimension-based filtering with the standard thresholds (100/500). Custom dimension thresholds (`>200`) duplicate what `--size-limit` already does on the CLI. Adding four comparison operators increases the resolver's cyclomatic complexity and requires four additional test cases for a feature that overlaps with existing functionality. If a user needs `dimension > 200`, they can use `medium,large` or `--size-limit 500 --select "medium,large"`.

---

### C3. Optimal Value Filters (`opt>N`, `opt<N`)

**Plan B:** Adds prefix-comparison on optimal tour length.
**Decision:** Rejected.
**Rationale:** Optimal values are not meaningful for problem selection in a benchmark context. Users select problems by size category or name, not by how close the optimal solution is. This feature has no use case in any of the three engines' existing workflows. It adds ~12 lines of resolver code and two test cases for zero demonstrated demand.

---

### C4. Intersection Operator (`&token`)

**Plan B:** `&small` intersects current selection with the small category.
**Decision:** Rejected.
**Rationale:** Intersection is a set operation that is rarely needed when the base operation is union. The typical workflow is: select a broad set, then exclude specifics (`small,!eil51`). Intersection (`small,&1-3`) is an edge case that would be used by <1% of users. It adds ~4 lines of resolver logic and a dedicated test case. Can be added in a future iteration if demand emerges.

---

### C5. Preset System (`save:name`, `load:name`)

**Plan B:** Saves/loads problem selection presets to `.problem_presets.json`.
**Decision:** Rejected.
**Rationale:** Three concerns: (1) Writing runtime state files into the source directory (`academic_benchmark/`) is a code smell — should be in `benchmark_db/` or a temp directory. (2) Presets create a maintenance burden — if problems are renamed or added, stale presets silently produce wrong selections. (3) The use case (repeated benchmark runs with the same problem set) is already served by CLI scripts or shell history. The ~40 lines of preset code (save, load, list, file I/O, JSON schema) are not justified by the marginal convenience.

---

### C6. bildiri2026 Dict Enrichment (Phase 4)

**Plan B:** Parse TSPLIB files at startup to add `dimension` to flat dicts.
**Decision:** Deferred (not rejected).
**Rationale:** This is a valid improvement but is a separate concern from the selector itself. It requires reading ~47 `.tsp` files from disk at startup, which adds latency. The bildiri2026 engines are research scripts, not production interactive tools — their existing flat-list UX is adequate for their use case. If bildiri2026 is unified later, the enrichment can be added as a preprocessing step in `data_manager.list_local_problems()` without changing the selector.

---

### C7. `done` Confirmation Prompt with `isatty()` Check

**Plan B:** Confirms before exiting with 0 selected; checks `sys.stdin.isatty()`.
**Decision:** Partially adopted.
**Rationale:** The confirmation prompt is good UX (prevents accidental empty selection). Plan A includes the `done` command and confirmation. However, the `isatty()` check is unnecessary overhead — if stdin is not a TTY (CI/automation), the user should use `--select` CLI instead of interactive mode. The interactive loop is inherently a TTY feature.

---

### C8. 36 vs 16 Test Cases

**Plan B:** 36 test cases covering all token types including glob, dimension filters, optimal filters, exclusion, intersection, and presets.
**Decision:** 16 test cases in Plan A.
**Rationale:** Each rejected feature (glob, dim filters, opt filters, intersection, presets) eliminates 2-4 test cases. The remaining 16 cases cover all Plan A token types plus edge cases (reversed range, case sensitivity, deduplication, unknown tokens). Test count should match feature count — over-testing rejected features wastes CI time and creates false maintenance burden.

---

### C9. Class vs Function Architecture

**Plan B:** `ProblemSelector` class with state.
**Decision:** Adopted (Plan A also uses a class).
**Rationale:** The class is the right choice here because the selector maintains index structures (`sorted`, `name_map`, `cat_indices`) that are reused across multiple token resolutions. A stateless function would need to rebuild these on every call. The class also cleanly encapsulates the display, resolution, and help logic. Plan A adopts this from Plan B.

---

### C10. Multi-Round Refinement with `▸` Markers

**Plan B:** Shows `▸` on selected items, allows iterative refinement.
**Decision:** Adopted (Plan A includes this).
**Rationale:** This is a genuine UX improvement over single-shot selection. Being able to type `small`, see the result, then type `!eil51` to refine is materially better than composing the full expression upfront. The `▸` markers provide immediate visual feedback. Plan A adopts this from Plan B at minimal code cost (~5 lines in `display_table`).

---

### C11. `--select` CLI Argument (vs `--problem-scope`)

**Plan B:** `--select "small,berlin52,10-15"` (full token syntax).
**Plan A (original):** `--problem-scope small` (category only).
**Decision:** Adopted `--select` from Plan B.
**Rationale:** `--select` is strictly more powerful — it accepts the same syntax as interactive mode, so automation scripts get full token support. `--problem-scope` would require a second argument for name-based selection, creating two parallel code paths. One argument with one syntax is simpler and more maintainable.

---

### C12. Adapter Functions vs Raw `getattr`

**Plan B:** `_prob_name()`, `_prob_dim()`, `_prob_optimal()`, `_prob_category()` with dict/dataclass dispatch.
**Plan A (original):** Inline `getattr(p, 'name', str(p))`.
**Decision:** Adopted adapter functions from Plan B.
**Rationale:** Adapter functions are cleaner — they handle dicts, dataclasses, and `TSPLIB_OPTIMALS` fallback in one place. Inline `getattr` is fragile (doesn't handle dicts) and repeats the fallback logic in every call site. The four adapter functions add ~20 lines but eliminate repeated `isinstance`/`getattr` patterns throughout the codebase.

---

### C13. `fnmatch` Import Location

**Plan B:** `import fnmatch` inside `_resolve_token` method body.
**Decision:** N/A (glob rejected).
**Rationale:** Even if glob were adopted, the import should be at module level, not inside a method called repeatedly. Plan B's approach would re-import on every glob token evaluation. This is a minor but real inefficiency.

---

### C14. Preset File Location

**Plan B:** `.problem_presets.json` next to `benchmark_utils.py` (source directory).
**Decision:** N/A (presets rejected).
**Rationale:** Writing runtime state to a source directory pollutes the package. If presets were adopted, the file should go in `benchmark_db/` (the existing state directory) or `~/.config/academic_benchmark/`. The `benchmark_db/` directory is already used for metadata, configs, and convergence histories.
