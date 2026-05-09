# Universal Problem Selector — Implementation Plan

**Date:** 2026-05-07  
**Scope:** `academic_benchmark/benchmark_utils.py`, `academic_benchmark/master_sota_engine.py`, `academic_benchmark/master_numba_engine.py`, `academic_benchmark/tests/`  
**Explicitly excluded:** `bildiri2026`  
**Goal:** Replace the current split problem-selection UX in the two master engines with a shared `ProblemSelector` that supports both CLI and interactive selection, while preserving the existing `--problems` and `--size-limit` behavior.

**Status:** Core implementation completed and locally verified for the shared selector slice.

**Completed slice:** Shared selector core, SOTA and Numba wiring, focused selector tests, and import-safe engine test setup.

---

## 1. Implementation Objective

Build one shared selection path for SOTA and Numba so users can select problems by:

- `all`
- `small`, `medium`, `large`
- 1-based index, e.g. `1`
- inclusive ranges, e.g. `3-7`
- exact name, e.g. `berlin52`
- exclusion, e.g. `!eil51`

The selector must work in both interactive mode and CLI mode, and it must accept both problem dataclasses used by the master engines.

This iteration does **not** touch `bildiri2026`, preset persistence, glob patterns, dimension operators, or optimal-value filters.

### Completed Work

- Shared `ProblemSelector` is implemented in `benchmark_utils.py` with dict/dataclass adapters, category reuse, left-to-right token evaluation, and interactive selection support.
- Both engines now resolve problem selection through a shared helper and accept the `--select` syntax alongside `--problems` and `--size-limit`.
- Focused tests were added for selector parsing, edge cases, and precedence behavior.
- The selector test file passes locally, and a focused SOTA/Numba precedence sanity check returns the same selection result in both engines.

---

## 2. Execution Workflow

### Phase 0 — Confirm the contract

Purpose: lock the behavior before editing code.

Checklist:
- [x] Confirm the new selector is only for SOTA and Numba.
- [x] Confirm the accepted token grammar is limited to `all`, category aliases, 1-based indices, ranges, exact names, and exclusion.
- [x] Confirm selection evaluation is left-to-right.
- [x] Confirm empty interactive input means select all.
- [x] Confirm unknown tokens produce warnings and are skipped.
- [x] Confirm the existing CLI fallback order remains `--select` > `--problems` > `--size-limit` > interactive.

Exit criteria:
- The selector grammar and priority chain are unambiguous.

### Phase 1 — Build the shared selector core

Purpose: add one reusable selection engine in `benchmark_utils.py`.

Checklist:
- [x] Add adapter helpers that read `name`, `dimension`, and `optimal` from dict-like or dataclass-like problems.
- [x] Reuse `categorize_dimension()` instead of duplicating threshold logic.
- [x] Implement `ProblemSelector.__init__()` with a stable sorted problem list.
- [x] Build name lookup and category lookup indexes once during initialization.
- [x] Implement `display_table()` with name, dimension, optimal, category, and selection marker output.
- [x] Implement `_resolve_token()` for:
  - [x] `all`
  - [x] `small`, `medium`, `large`
  - [x] numeric indices
  - [x] inclusive ranges
  - [x] exact name lookup
  - [x] exclusion with `!token`
- [x] Implement `resolve_tokens()` for comma-separated input.
- [x] Implement `quick_select()` for CLI use.
- [x] Implement `interactive_select()` for multi-round refinement.
- [x] Add `_show_help()` so the syntax is visible in the UI.
- [x] Define interactive command semantics:
  - [x] `?` prints help and keeps prompting.
  - [x] Empty input means select all on first prompt, otherwise keeps prompting.
  - [x] Unknown tokens produce warnings and are skipped.
- [x] `done` confirmation: if the current selection is empty, warn and require explicit confirmation to exit.
- [x] Empty-selection guard: when token evaluation yields an empty set, show `Seçim boş!` and re-prompt.

Exit criteria:
- A single selector instance can parse inputs, warn on invalid tokens, and return the correct problem list.

### Phase 2 — Wire SOTA

Purpose: replace the category-only selection flow in `master_sota_engine.py`.

Checklist:
- [x] Import `ProblemSelector` from `benchmark_utils`.
- [x] Add a `--select` CLI argument.
- [x] Apply CLI priority order:
  - [x] `--select`
  - [x] `--problems`
  - [x] `--size-limit`
  - [x] interactive selector
- [x] Replace `_select_problem_scope()` usage with the shared selector.
- [x] Remove `_select_problem_scope()` after `ProblemSelector` integration; it is fully superseded.
- [x] Keep default and tuning execution paths unchanged after selection.
- [x] Keep existing result writing and metadata behavior unchanged.

Exit criteria:
- SOTA can run with the new selector without breaking the old CLI flags.

### Phase 3 — Wire Numba

Purpose: replace the current two-option problem chooser in `master_numba_engine.py`.

Checklist:
- [x] Import `ProblemSelector` from `benchmark_utils`.
- [x] Add a `--select` CLI argument.
- [x] Apply the same CLI priority order as SOTA.
- [x] Replace the current interactive problem-selection block with the shared selector.
- [x] Keep the algorithm-selection and run-count prompts unchanged.
- [x] Keep direct benchmark and tuning paths unchanged after selection.

Exit criteria:
- Numba uses the same problem-selection semantics as SOTA.

### Phase 4 — Add tests

Purpose: lock behavior down before changing anything else.

Checklist:
- [x] Create `academic_benchmark/tests/test_problem_selector.py`.
- [x] Add adapter tests for dict and dataclass inputs.
- [x] Add category boundary tests for 100, 101, and 501.
- [x] Add sorting and index map tests.
- [x] Add token parsing tests for:
  - [x] `all`
  - [x] `small` / `medium` / `large`
  - [x] single indices
  - [x] multiple indices
  - [x] ranges
  - [x] reversed ranges
  - [x] exact names
  - [x] exclusions
  - [x] deduplication
  - [x] unknown-token warnings
- [x] Add SOTA wiring tests for `--select`, `--problems`, and `--size-limit` precedence.
- [x] Add Numba wiring tests for the same precedence.
- [x] Add one interactive test path that monkeypatches `input()` and verifies the loop returns the expected problems.

Exit criteria:
- The selector tests cover the parsing contract and the engine priority chain.

### Phase 5 — Validate and stabilize

Purpose: confirm the implementation works without regressing existing behavior.

Checklist:
- [x] Run the selector test file first.
- [x] Run focused helper sanity checks for SOTA and Numba selection precedence.
- [x] Fix any syntax, import, or ordering issues introduced by the new shared selector.
- [ ] Run focused tests for SOTA CLI and interactive selection.
- [ ] Run focused tests for Numba CLI and interactive selection.
- [ ] Confirm `--problems` still works exactly as before.
- [ ] Confirm `--size-limit` still works exactly as before.
- [ ] Confirm the selector returns the same object types the engines already expect.

Exit criteria:
- All touched paths are validated and the old behavior is still intact.

---

## 3. Detailed Task List

### Shared utilities

- [x] Add `_prob_name(p)`.
- [x] Add `_prob_dim(p)`.
- [x] Add `_prob_optimal(p)`.
- [x] Add `_prob_category(p, dim=None)` or reuse `categorize_dimension()` directly where possible.
- [x] Add `ProblemSelector`.
- [x] Ensure all helpers work for both SOTA and Numba problem objects.

### SOTA integration

- [x] Add `--select` to argparse.
- [x] Replace category-only scope selection.
- [x] Keep the `--problems` branch intact.
- [x] Keep the `--size-limit` branch intact.
- [x] Ensure the no-selection interactive branch uses the selector.

### Numba integration

- [x] Add `--select` to argparse.
- [x] Replace the two-option menu with the selector.
- [x] Keep tuning and default execution logic unchanged.
- [x] Keep problem loading for time matrices unchanged.

### Tests

- [x] Add selector unit tests.
- [x] Add engine integration tests.
- [x] Confirm interactive flow with monkeypatched input.
- [x] Confirm warnings and deduplication behavior.

### Validation

- [x] Run unit tests for the selector.
- [x] Review diff for accidental behavior changes.
- [x] Confirm no `bildiri2026` files were touched.
- [ ] Run narrow engine tests.

---

## 4. Dependency Order

1. Shared selector helpers in `benchmark_utils.py`
2. `ProblemSelector` class in `benchmark_utils.py`
3. SOTA wiring
4. Numba wiring
5. Tests
6. Validation

Do not start the engine wiring until the selector class is stable enough to be imported and tested in isolation.

---

## 5. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Duplicate category logic | Medium | Reuse `categorize_dimension()` instead of adding a second threshold helper |
| Token precedence confusion | Medium | Keep token evaluation left-to-right and document it in the selector help text |
| CLI regression | High | Preserve the old flags and make `--select` only the first-priority override |
| Interactive loop mismatch | Medium | Add a monkeypatched input test before touching more code |
| Overexpanding scope into bildiri2026 | High | Exclude it from this iteration entirely |

---

## 6. Definition of Done

The implementation is complete when all of the following are true:

- [ ] SOTA and Numba both use the same problem-selection semantics.
- [ ] `--select` works in both engines.
- [ ] `--problems` still works.
- [ ] `--size-limit` still works.
- [ ] Interactive selection supports the agreed grammar.
- [ ] `done` does not silently exit with an empty selection unless explicitly confirmed.
- [ ] Empty-selection results re-prompt instead of running with an empty list.
- [ ] Unit tests and engine wiring tests pass.
- [ ] No `bildiri2026` code was modified.
- [ ] The plan remains documented in `docs/` for future implementation work.

---

## 7. Execution Notes

- Keep edits small and local.
- Validate the selector before widening to engine wiring.
- Prefer tests that prove the CLI priority chain over broad end-to-end runs.
- If a token feature is not listed above, do not add it in this iteration.
- As of 2026-05-07, the shared selector implementation is in place and the focused selector tests pass locally.
