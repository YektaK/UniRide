# WP-E8 Exact Reference Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking. Approved by the owner on 2026-10-18; the decisions are recorded in the last section.

**Goal:** Make the committed `exact_reference_v1` results readable, independently validated and discoverable inside `academic_benchmark`, as typed rows that cannot be pooled, ranked or tested together with fixed-budget or native-termination rows, without changing any fixed-budget or native output.

**Architecture:** Everything new lives in `academic_benchmark`. A pure, standard-library Hamiltonian-cycle validator (`academic_benchmark/validation/`) recomputes tour lengths from dataset artifacts under the TSPLIB convention; it shares no code with the solver path (`uniride_core.exact.tsp`) or the WP-E7 runner. A row contract (`exact_reference/rows.py`) and a reader (`exact_reference/reader.py`) turn committed manifests into rows, refusing anything that does not verify. An academic-layer protocol registry (`academic_benchmark/protocol_registry.py`) declares the three protocol kinds and their pooling groups. `uniride_core` and `optimizer_api` are not changed. Gap columns are not built (Package D).

**Tech Stack:** Python 3.14.6 (`.venv-jit`), Pydantic 2.13.4, pytest, standard library only in the validator. No AMPL, no solver, no database write, no network.

## Global Constraints

- Work in your own worktree and branch: `git -C <main> worktree add .claude/worktrees/wp-e8 -b feat/wp-e8-exact-reference WIP`. Never `git checkout`/`git switch` in the main checkout; preserve its dirty tree; do not change git config. Commit every task separately; do not merge or push.
- Python: only `.venv-jit` with `PYTHONPATH=<worktree>` (the editable install points at main). No interactive Python (no bare `python`/`py`, no `python -i`, no `python -` or heredoc); scripts go to a file and run as `python path/script.py`; `python -c` only for one line. Time-limit long commands and cap their output. Never kill processes by image name; PID only. Short-path temp folders only under `C:\wt\`.
- Do not open, copy, write or lock `academic_benchmark/tsplib_data/tsplib.db*`. WP-E8 reads no database at all; only the companion task reads `tsplib.db`, read-only and immutable (`mode=ro&immutable=1`), refusing a non-empty `-wal` file as the WP-E7 runner does.
- Do not change: `uniride_core/**`, `optimizer_api/**`, `src/**`, `scripts/run_exact_*.py`, the fixed-budget and native modules (`fairness.py`, `fair_pilot.py`, `native_protocol.py`, `native_pilot.py`, `matrix_run_summary.py`, `results_reader.py`, `data_export.py`, `core/preflight.py`, `core/execution_gateway.py`, `core/registry_setup.py`), `uniride_core/algorithms/capabilities.py` (`ExecutionProtocol` stays `fixed_budget`/`native_termination`), the existing three files in `academic_benchmark/schemas/`, `academic_benchmark/studies/**`, anything under `archive/` or `docs/paper/results/`.
- No gap column (`gap_to_LB`, `gap_to_reference_optimum`, or any `gap_*` field) is computed or stored by WP-E8 code. No CVRP (E09: WP-E9 deferred). No campaign, no re-solve.
- Never read a path under `archive/`. The reader refuses one at run time; a test scans the new modules statically.
- Exact rows are never ranked, averaged or tested with heuristic rows (design §4, A04). Hamiltonian-cycle validation and multi-route validation stay separate contracts (A04).
- Smoke and verification results support no superiority claim; WP-E7 stage 1 is a verification subset, not a paper instance set (`TSP_REFERENCE_CLAIM`).

## Preconditions (evidence)

| # | Precondition | Evidence | Status |
|---|---|---|---|
| P1 | Unification gates 1-2 passed | Fresh check 2026-10-18 at `65fb0b00`: schema check rc=0; YAEM archive verified 159 entries, Bildiri archive 233 entries; gate test batch 150 passed, no JIT skip (numba 0.66.0); full `academic_benchmark/tests` 1275 passed, 3 skipped (streamlit only) | met |
| P2 | EQ6 decided | DECISION_LOG E09 (2026-10-18): verification set = 16 TSPLIB TSP n <= 100 + ft53; 600 s per instance; CVRP and n > 100 deferred; WP-E8 wiring waits for gates 1-2 | met |
| P3 | WP-E7 stage 1 merged, results committed | `5e52a79b`; `docs/paper/results/tsplib-exact-reference/stage1-verification/` (17 of 17 reproduced, `-text` in `.gitattributes`); polish merged `ebec5a21` | met |
| P4 | Package C context | C1-C3 merged (capability catalog `uniride_core/algorithms/capabilities.py`, preflight, gateway); no hybrids, no study loader, no YAEM profile. WP-E8 is a Package C item (design §9 WP-E8 row) and does not claim Gate C | partial, acceptable |
| P5 | Active dataset location for published tours (companion task, below) | Runner default `OPT_TOUR_DIR` at `scripts/run_exact_tsp_reference.py:61` points into `archive/academic_benchmark/bildiri2026_legacy/bildiri2026/data/tsplib` | **open, prerequisite for Task 5 only** |
| P6 | Dataset artifacts for the 16 TSP instances | `*.tsp` is git-ignored (`.gitignore:51`); stage 1 read 5 instances from local `.tsp` files and 11 from `tsplib.db` coordinates; only `ft53.atsp` and `atsp/*.atsp` are tracked | resolved (owner, 2026-10-18, OQ1): the companion task commits the 16 `.tsp` files; prerequisite for Task 5 |

Known residuals carried, not fixed here: M17 (`archive/` has no `__init__.py`, importable as a namespace package; audit line 1233), H9 (one ID maps to several implementations; audit §H9, line 885), WP-E7 default archive read (P5).

## Companion task (separate, owner step 4; not part of WP-E8)

Branch `fix/opt-tours-active-dataset`, its own small plan, review and merge before WP-E8 Task 5.

- **Copy, never move.** The Bildiri archive stays byte-identical so its manifest (233 entries) still verifies. "Moving files does not rehabilitate results" (unification design `:273`) applies to results; TSPLIB tours are input data, and they get their own provenance record.
- **Target:** `academic_benchmark/tsplib_data/opt_tours/<name>.opt.tour` (lower-case instance name in the manifest; the file keeps the TSPLIB name, e.g. `kroA100.opt.tour`), with `.gitattributes` line `academic_benchmark/tsplib_data/opt_tours/** text eol=lf`.
- **Manifest** `academic_benchmark/tsplib_data/opt_tours/MANIFEST.json`, modelled on `atsp/MANIFEST.json`:

```json
{
  "schema_version": "uniride-opt-tour-collection/v1",
  "collection_id": "tsplib95-opt-tours",
  "tour_convention": {"node_base": 1, "closed": true, "terminator": -1},
  "instances": [
    {"name": "kroa100", "file_name": "kroA100.opt.tour", "dimension": 100, "type": "TOUR",
     "problem_type": "TSP", "artifact_path": "academic_benchmark/tsplib_data/opt_tours/kroA100.opt.tour",
     "size_bytes": 0, "sha256": "<64 hex>",
     "authority_url": "https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/kroA100.opt.tour.gz",
     "provenance": {"kind": "archive_copy", "archive_path": "archive/academic_benchmark/bildiri2026_legacy/bildiri2026/data/tsplib/kroA100.opt.tour",
                    "archive_entry_sha256": "<64 hex, equal to the Bildiri archive manifest entry>"},
     "retrieved_on": "2026-10-xx"}
  ]
}
```

- **Source (owner, 2026-10-18, OQ5):** the tours are copied from the Bildiri archive; nothing is downloaded. `authority_url` names the original TSPLIB95 location for reference only and is not fetched. The copy's sha256 must equal the archive manifest entry's sha256.
- **Coverage:** the archive holds tours for 13 of the 16 TSP verification instances (not burma14, krob100, kroe100); ATSP has no published tours (`atsp/MANIFEST.json` note). Missing tours stay missing (`published_tour_check.source = "none"`), never synthesized from our own runs.
- **Runner:** `OPT_TOUR_DIR` default becomes the new directory; `--opt-tour-dir` refuses a path that resolves under `archive/` (exit 2). A test asserts the default and the refusal. Committed WP-E7 results are not regenerated.
- **TSP instance files (owner, 2026-10-18, OQ1).** The same branch commits the 16 TSP verification instances as `academic_benchmark/tsplib_data/tsp/<name>.tsp` (public TSPLIB research data), with `.gitignore` negation `!academic_benchmark/tsplib_data/tsp/*.tsp` and `.gitattributes` line `academic_benchmark/tsplib_data/tsp/** text eol=lf`. Nothing is downloaded. Source order per instance:
  1. an existing local copy (the untracked `academic_benchmark/tsplib_data/<name>.tsp` in the main checkout; at the stage-1 run 5 instances came from such files), copied byte for byte (`provenance.kind = "local_copy"`);
  2. else an archived copy, if the archive holds one (`"archive_copy"`, with the archive entry sha256); at `65fb0b00` the Bildiri archive directory `bildiri2026/data/tsplib/` holds no `.tsp` file, so this case is expected to be empty;
  3. else a reconstruction from the `tsplib.db` node coordinates, opened read-only and immutable (`"db_reconstruction"`): header `NAME`, `TYPE: TSP`, `COMMENT: reconstructed from tsplib.db coordinates (UniRide, <date>)`, `DIMENSION`, `EDGE_WEIGHT_TYPE` from the database, `NODE_COORD_SECTION` with 1-based ids and `repr()` floats so parsing returns the identical floats, `EOF`.
- **Manifest** `academic_benchmark/tsplib_data/tsp/MANIFEST.json`, schema `uniride-tsp-collection/v1`, one entry per instance: `name`, `dimension`, `problem_type`, `edge_weight_type`, `artifact_path`, `size_bytes`, `sha256` (file bytes), `coordinate_text_sha256` (sha256 of the canonical coordinate text `"{i} {x!r} {y!r}\n"`, ASCII, 0-based, of the parsed coordinates), `provenance` (`kind`; `source_path` repo-relative for `local_copy`/`archive_copy`, `null` for `db_reconstruction`; `source_sha256`; for a reconstruction the database table and query used, the database sha256 and size), `published_optimum` and `retrieved_on`.
- **Blocking checks:** for the 5 instances with `data_source = tsp_file` in the committed stage-1 manifest, the committed file's sha256 equals `instances[].sha256`; for the 11 with `tsplib_db_coordinates`, the `coordinate_text_sha256` of the parsed committed file equals `instances[].sha256`; `dimension` and `edge_weight_type` equal the stage-1 manifest. Any mismatch blocks the companion task.

## File Map

| Path | Change | Responsibility |
|---|---|---|
| `academic_benchmark/validation/__init__.py` | create | Package marker; exports the validator API. |
| `academic_benchmark/validation/hamiltonian_cycle.py` | create | Independent TSP/ATSP tour validator: TSPLIB parsing (NODE_COORD_SECTION, EXPLICIT FULL_MATRIX), distances EUC_2D (nint), ATT, GEO (`math.pi`, E10), closed-cycle length, permutation checks. Standard library only. No route/VRP logic. |
| `academic_benchmark/exact_reference/rows.py` | create | `ExactReferenceRowV1` contract and its invariants. |
| `academic_benchmark/exact_reference/reader.py` | create | Readers for `tsp_reference` manifests (WP-E7) and wave `exact_manifest.json` (WP-E3, WP-E4a); sha256 and schema verification; refusal of other manifest kinds and of archive/absolute paths. |
| `academic_benchmark/exact_reference/results_index.json` | create | Explicit list of committed exact result directories with their manifest sha256 (no glob discovery). |
| `academic_benchmark/exact_reference/__init__.py` | modify | Docstring: WP-E8 contents; public names. |
| `academic_benchmark/protocol_registry.py` | create | Academic-layer protocol kinds, pooling groups, `assert_single_pooling_group`, `assert_rankable`. |
| `academic_benchmark/contracts/export_schemas.py` | modify (one entry) | Adds `exact-reference-row-v1.schema.json`; the three existing schema files stay byte-identical. |
| `academic_benchmark/schemas/exact-reference-row-v1.schema.json` | create (generated) | Rendered row schema. |
| `academic_benchmark/tests/fixtures/fixed_budget_tables_golden_v1.json` | create | Golden fixed-budget and native outputs captured at `65fb0b00` before any production change. |
| `academic_benchmark/tests/test_fixed_budget_tables_unchanged.py` | create | Byte-identity of those outputs. |
| `academic_benchmark/tests/test_hamiltonian_cycle_validator.py` | create | Validator unit, convention and independence tests. |
| `academic_benchmark/tests/test_exact_reference_rows.py` | create | Row contract tests. |
| `academic_benchmark/tests/test_exact_reference_reader.py` | create | Reader over the committed results and over tampered copies (in `tmp_path`). |
| `academic_benchmark/tests/test_protocol_registry_pooling.py` | create | No-pooling and no-ranking tests. |
| `academic_benchmark/tests/test_exact_reference_boundaries.py` | create | Import, archive-path, schema and study-profile boundary tests. |
| `docs/designs/EXACT_SOLVER_AMPL_DESIGN.md` | modify | §9 WP-E8 row and a WP-E8 status paragraph (gap columns moved to Package D). |
| `docs/DECISION_LOG.md` | modify | One dated entry for the owner answers to the open questions below. |

`uniride_core`: no change. Core keeps owning the solver, `EXACT_STATUSES` and `validate_tour`; WP-E8 does not import `uniride_core.exact` except `EXACT_STATUSES` through the existing `protocol.py`. `optimizer_api`/`src`: no change; new guards prove they import none of the new modules and read no `docs/paper/results` artifact (unification design `:89-93`).

## Data Contracts

### Row: `uniride-exact-reference-row/v1` (`ExactReferenceRowV1`, Pydantic `StrictContract`, extra fields forbidden)

| Field | Type | Rule |
|---|---|---|
| `row_schema_version` | `"uniride-exact-reference-row/v1"` | fixed |
| `protocol` | `"exact_reference_v1"` | equals `protocol.PROTOCOL_ID` |
| `solution_kind` | `"hamiltonian_cycle"` or `"vehicle_routes"` | `hamiltonian_cycle` only with `problem_contract` TSP/ATSP |
| `problem_contract` | `"TSP"`, `"ATSP"`, `"uniride_wave"` | `uniride_wave` only with `vehicle_routes` |
| `instance_id` | str | TSPLIB name, or `<date>_R<r>/<wave_id>[/<option>]` for waves |
| `stage` | `null` or `"stage1"`/`"stage2"`/`"free"` | `null` for `hamiltonian_cycle` |
| `solver_role` | `"primary"`, `"verification"` | Gurobi primary, HiGHS verification (design §6) |
| `solver_name`, `solver_version`, `option_string` | str | copied verbatim from the manifest; never a heuristic `algorithm_id` |
| `status` | `protocol.STATUS_LABELS` key | |
| `stop_reason` | `protocol.STOP_REASONS` key or `null` | rules of `protocol.validate_stage_row` |
| `lb`, `ub` | int or `null` | `optimal`: both present and `ub - lb < 1`; `feasible_with_gap`: `lb <= ub`; `bound_only`: `ub` null |
| `reference_optimum` | int or `null` | published value only |
| `reference_optimum_source` | `"tsplib"` or `null` | both null or both set; `best_solutions` impossible (enum) |
| `timing_dependent` | bool | true whenever `stop_reason` is `wall_limit`/`other_limit` |
| `wall_seconds` | float or `null` | informational, never compared |
| `ub_validated` | bool | true only after the independent validator (`hamiltonian_cycle`); wave rows stay false with reason `certified_by_producing_run` (owner, 2026-10-18, OQ3) |
| `source` | object | `results_dir` (repo-relative), `manifest_kind` (`tsp_reference`/`wave_campaign`), `manifest_sha256`, `work_package`, `git_commit` |

No `algorithm_id`, no `evaluation_budget`, no `gap_*` field can exist (extra forbidden; explicit tests). A row is `optimal` only from the solver's status, never because `ub == reference_optimum`.

### Mapping from committed manifests

| Source | Manifest kind and version | Rows produced |
|---|---|---|
| WP-E7 `tsplib-exact-reference/stage1-verification/` | `manifest_kind tsp_reference`, `schema_version 1`; `reference.csv` (31 columns, frozen in the reader as `TSP_REFERENCE_CSV_FIELDS_V1`), `tours.json` (`schema_version 1`, `node_base 1`) | per instance: one `primary` row (gurobi columns) and one `verification` row (`highs_*` columns); MTZ agreement is checked, not emitted. `gap_to_reference`, `verdict`, `reference_in_bracket` are checked for consistency and not carried (OQ2) |
| WP-E3 `wp-e3-goal1-single/exact_manifest.json` | wave campaign, `schema_version 1`, `source_campaign` | one row per (wave, stage, solver role) |
| WP-E4a `wp-e4a-typed-options/exact_manifest.json` | wave campaign, `schema_version 1`, `source_campaigns` | one row per (option, stage, solver role) |
| WP-E4b `union_day_manifest.json` | `union_day_v1` | refused as exact rows (own protocol) |
| WP-E6 `wp-e6-gap-report/manifest.json`, scaling probe | analysis/probe manifests | refused (not `exact_reference_v1`) |

### Versioning and backward compatibility

- The reader dispatches on (`protocol`, `manifest_kind`, `schema_version`); an unknown triple is refused with a message, never guessed.
- Committed manifests are read as they are and never rewritten (tests pin their sha256). The committed stage-1 manifest predates the WP-E7 polish: its `run_history` holds `invocations_at_this_commit` and it has no database size/sha256 and no `published_tour_check`; the reader accepts both this and the later shape (`invocations_in_this_manifest`, `started_utc`, `ended_utc`).
- `outputs` sha256 values in the stage-1 manifest are checked over raw bytes (the tree is `-text`).
- The row schema is versioned independently of the manifests; a later `/v2` adds fields only through a new literal.

### Protocol registry (academic layer)

| Kind | Version label | Pooling group | Rankable | Statistics |
|---|---|---|---|---|
| `fixed_evaluation_budget` | `uniride-fair-tsp-v2` | `fixed_budget` | yes, within group | yes, within group |
| `algorithm_native_termination` | `uniride-native-tsp-v1` | `native` | yes, within group | yes, within group |
| `exact_reference_v1` | `exact_reference_v1` | `exact_reference_v1` | no | no |
| `union_day_v1` | `union_day_v1` | `union_day_v1` | no | no |

`assert_single_pooling_group(rows)` raises when rows from two groups meet; `assert_rankable(rows)` raises for exact and union rows. The existing `protocol.assert_not_pooled` is kept unchanged. `ExecutionProtocol` in core is not extended (owner, 2026-10-18, OQ4).

### Where the gap columns go later (not built)

Package D, after Gate C: an analysis module (proposed `academic_benchmark/analysis/exact_gaps.py`) joins validated heuristic rows (fixed-budget or native, never both in one table) with `ExactReferenceRowV1` rows on (`problem_contract`, `instance_id`, dataset sha256) and emits `gap_to_LB` and `gap_to_reference_optimum` carrying both protocol labels (design §4, §5). It calls `assert_single_pooling_group` on the heuristic side and uses canonical algorithm IDs from the resolver (H9).

---

### Task 1: Freeze the baseline (tests only, green at `65fb0b00`)

**Files:** create `tests/fixtures/fixed_budget_tables_golden_v1.json`, `tests/test_fixed_budget_tables_unchanged.py`.

- [ ] **Step 1: Capture golden outputs.** With a deterministic stub executor and a monkeypatched constant elapsed time (1.0 ms; elapsed fields are time-dependent and are the only fields set this way), run `fair_pilot.run_fair_pilot` and the native pilot on the existing tiny test fixtures, and call `matrix_run_summary.summarize_benchmark_rows` and `results_reader` leaderboard functions on fixed fixture rows. Store sorted-key JSON with a final newline. Capture once, at the base commit, before any production file changes; do not hand-edit.
- [ ] **Step 2: Byte test.** The test re-renders the same outputs and compares bytes with the fixture.
- [ ] **Step 3: Pin committed exact results.** The test also pins sha256 of the four stage-1 files, the WP-E3/WP-E4a `exact_manifest.json`, and `studies/bildiri2026/study.json`.

**Verify:** `PYTHONPATH=<wt> <repo>/.venv-jit/Scripts/python.exe -m pytest academic_benchmark/tests/test_fixed_budget_tables_unchanged.py -q` → all passed at the base commit.
**Accept:** fixture committed in its own commit before any other change; `git diff 65fb0b00 --stat` lists only the two new test files.

### Task 2: Independent Hamiltonian-cycle validator

**Files:** create `validation/__init__.py`, `validation/hamiltonian_cycle.py`, `tests/test_hamiltonian_cycle_validator.py`.

**Interface:** `tsplib_distance(edge_weight_type, a, b) -> int`; `parse_coordinates(text) -> list[tuple[float, float]]`; `parse_full_matrix(text) -> list[list[int]]`; `closed_length(tour0, cost) -> int`; `validate_hamiltonian_cycle(tour, *, n, node_base, cost, claimed_length=None) -> list[str]` (empty when valid; direction respected; no symmetry assumed).

- [ ] **Red tests:** subtour (n-1 nodes), repeated node, node outside range, 0/1-base mismatch, bool node, wrong claimed length, ATSP reversed tour gives a different length on a hand asymmetric matrix; EUC_2D nint at .5; ATT rule (r = sqrt((dx^2+dy^2)/10), t = nint(r), d = t+1 if t < r else t); GEO with `math.pi` on two hand-computed burma14 pairs; unsupported `edge_weight_type` refused.
- [ ] **Independence test (AST):** the module imports only the standard library; not `uniride_core`, `scripts`, `numpy`, `academic_benchmark.core`.
- [ ] **Parity test (E10):** on the tracked `ft53.atsp` and hand coordinate fixtures, the validator's distances equal `uniride_core.algorithms.tsplib_parser`'s (test-only import), and a `3.141592` GEO variant differs where expected.
- [ ] Implement until green.

**Verify:** `... -m pytest academic_benchmark/tests/test_hamiltonian_cycle_validator.py -q` → all passed.
**Accept:** no VRP/route code in the module; validator is pure and deterministic.

### Task 3: Row contract

**Files:** create `exact_reference/rows.py`, `tests/test_exact_reference_rows.py`; modify `contracts/export_schemas.py`; generate `schemas/exact-reference-row-v1.schema.json`.

- [ ] **Red tests:** a `gap_to_LB`/`gap_to_reference_optimum`/`algorithm_id`/`evaluation_budget` key is rejected; `reference_optimum_source = "best_solutions"` rejected; `optimal` with `ub - lb >= 1` rejected; `wall_limit` without `timing_dependent` rejected; `vehicle_routes` with TSP rejected; `hamiltonian_cycle` with a stage rejected; status set equals `STATUS_LABELS` keys; `optimal` cannot be inferred from `ub == reference_optimum` (row with status `feasible_with_gap` and `ub == reference_optimum` stays `feasible_with_gap`).
- [ ] Implement with `protocol.STATUS_LABELS`, `STOP_REASONS`, `TIMING_STOP_REASONS` (no duplicated sets).
- [ ] Add the schema entry; regenerate; the existing three schema files are byte-identical.

**Verify:** `... -m pytest academic_benchmark/tests/test_exact_reference_rows.py -q` and `... -m academic_benchmark.contracts.export_schemas --check` → rc 0.
**Accept:** schema check rc 0; `git diff 65fb0b00 -- academic_benchmark/schemas/study-v1.schema.json academic_benchmark/schemas/dataset-v1.schema.json academic_benchmark/schemas/run-v1.schema.json` empty.

### Task 4: Reader for committed results

**Files:** create `exact_reference/reader.py`, `exact_reference/results_index.json`, `tests/test_exact_reference_reader.py`.

**Interface:** `load_exact_reference(results_dir, *, repo_root) -> ExactReferenceSet` (rows sorted by `instance_id`, `stage`, `solver_role`; plus the manifest and its sha256); `discover_exact_references(repo_root) -> tuple[ExactReferenceSet, ...]` from `results_index.json` only.

- [ ] **Red tests on the committed results:** stage 1 gives 34 rows (17 primary + 17 verification), all `optimal`, `ub == lb == reference_optimum`, `timing_dependent` false, `reference_optimum_source` `tsplib`; WP-E3 and WP-E4a manifests load and every stage row passes `validate_stage_row`.
- [ ] **Red tests on tampered copies in `tmp_path`:** one byte changed in `reference.csv`/`tours.json`/`README.md` (outputs sha mismatch); `reference.csv` header reordered; an instance missing from `tours.json`; `tours.json` length differs from `ub`; `protocol` not `exact_reference_v1` in one row; `gap_to_reference != ub - reference_optimum`; `union_day_v1` and gap-report manifests refused; unknown `schema_version` refused; a `results_dir` under `archive/`, an absolute path, or a `..` escape refused; `private_data_errors` non-empty refused.
- [ ] **Backward compatibility:** both `run_history` shapes accepted (committed old shape; synthetic new shape).
- [ ] **Determinism:** two loads give identical `model_dump_json()` bytes.
- [ ] Implement; the index lists the three exact directories with manifest sha256.

**Verify:** `... -m pytest academic_benchmark/tests/test_exact_reference_reader.py -q` → all passed.
**Accept:** reader never imports `scripts.*`, never opens `tsplib.db`, never writes.

### Task 5: Validate the committed tours (needs the merged companion task)

**Files:** extend `reader.py` (`validate_hamiltonian_rows(set, *, dataset_root)`), tests in `test_exact_reference_reader.py`.

- [ ] **Red tests:** for each stage-1 instance, the tracked artifact (`tsplib_data/tsp/<name>.tsp`, or `ft53.atsp`) matches `instances[].sha256` of the stage-1 manifest: the file sha256 for `tsp_file`/`atsp_file` instances, the canonical coordinate text sha256 (`"{i} {x!r} {y!r}\n"`, ASCII, 0-based, as in the WP-E7 runner) for `tsplib_db_coordinates` instances; the reader also checks the artifact against `tsplib_data/tsp/MANIFEST.json`; the validator's recomputed length of each tour equals `ub`; a swapped pair of nodes in a copied `tours.json` is detected; an artifact with one changed coordinate is refused by the sha check before any length is computed.
- [ ] Rows get `ub_validated = true` only here. The 16 `.tsp` files and `ft53.atsp` are tracked, so a missing artifact is a test failure, never a skip; synthetic fixtures cover the error paths.
- [ ] Optional cross-check: where the companion `opt_tours/` holds a published tour, its recomputed length equals `reference_optimum`.

**Verify:** `... -m pytest academic_benchmark/tests/test_exact_reference_reader.py -q -rs` → all passed, 0 skipped.
**Accept:** 17 of 17 tours validated in CI and locally, 0 skips.

### Task 6: Protocol registry and no-pooling

**Files:** create `protocol_registry.py`, `tests/test_protocol_registry_pooling.py`.

- [ ] **Red tests:** registry has exactly the four kinds above; mixing exact rows with fixed-budget rows, with native rows, or fixed with native, raises in `assert_single_pooling_group`; `assert_rankable` raises for exact and union rows; `assert_not_pooled` behaviour unchanged (existing tests untouched and green); an `ExactReferenceRowV1` is not a `Mapping`, so it cannot be fed to the dict-based fixed-budget aggregators by accident (test that `fair_pilot._aggregate([row])` raises); fixed-budget rows are classified by their existing fields (protocol version / regime fields as written today), documented in the test.
- [ ] **AST tests:** the fixed/native modules listed in Global Constraints import neither `exact_reference` nor `protocol_registry`; `exact_reference` imports none of them.
- [ ] Implement.

**Verify:** `... -m pytest academic_benchmark/tests/test_protocol_registry_pooling.py academic_benchmark/tests/test_exact_reference_protocol.py -q` → all passed.
**Accept:** `uniride_core/algorithms/capabilities.py` unchanged; preflight still rejects any protocol other than the two existing ones.

### Task 7: Boundary tests

**Files:** create `tests/test_exact_reference_boundaries.py`.

- [ ] `optimizer_api/**` and `uniride_core/**` Python files import none of `academic_benchmark.exact_reference`, `academic_benchmark.validation`, `academic_benchmark.protocol_registry`; `src/**` contains no reference to `docs/paper/results` or `exact_reference`.
- [ ] The new modules contain no string path segment `archive` (static scan) and the reader refuses archive paths (run time).
- [ ] `studies/bildiri2026/study.json` and the three existing schemas byte-identical to the base.
- [ ] Archive manifests verify: YAEM 159 entries, Bildiri 233 entries, with the existing `archive_manifest` verify command.

**Verify:** `... -m pytest academic_benchmark/tests/test_exact_reference_boundaries.py uniride_core/tests/test_archive_boundaries.py uniride_core/tests/test_architecture_boundaries.py academic_benchmark/tests/test_bildiri_quarantine_boundary.py academic_benchmark/tests/test_yaem_quarantine_boundary.py -q` → all passed.

### Task 8: Documentation

- [ ] Design §9 WP-E8 row: scope as built; "gap columns" replaced by "gap columns: Package D (analysis layer), after Gate C"; WP-E8 status paragraph with test counts.
- [ ] `exact_reference/__init__.py` docstring.
- [ ] DECISION_LOG entry recording the owner decisions OQ1-OQ6 of 2026-10-18 (last section of this plan).

**Accept:** no results file, archive file or study profile changed (`git diff 65fb0b00 --stat -- archive docs/paper/results academic_benchmark/studies` empty).

## WP-E8 Acceptance Gate

1. Rows validated: every row from `results_index.json` loads; all 17 stage-1 tours recomputed by the independent validator from the tracked artifacts equal `ub`, in CI, with 0 skips.
2. Fixed-budget and native outputs byte-identical: `test_fixed_budget_tables_unchanged.py` green, and `git diff --exit-code 65fb0b00 -- <fixed/native module list>` empty.
3. No pooling, proven by Task 6 tests; `assert_not_pooled` tests unchanged and green.
4. Boundary tests (Task 7) green; schema check rc 0.
5. Archive manifests still verify (159 and 233 entries).
6. Full suite: `academic_benchmark/tests` = 1275 passed + the new tests, 3 skipped (streamlit only), no other skip; `uniride_core/tests` exact and boundary tests green; gate batch 150 passed with no JIT skip.
7. Independent review (denetci) ONAY.

## Risks

| Risk | Test |
|---|---|
| Validator shares a bug with the solver path (not independent) | AST independence test; parity test only in tests; hand-computed distances |
| GEO constant drift (E10) | parity test with `math.pi`; a `3.141592` variant must differ on known pairs |
| H9 identity ambiguity reaches exact rows | row model forbids `algorithm_id`; solver identity verbatim from the manifest; Package D join uses resolver canonical IDs (documented, not built) |
| M17: `archive` importable as a namespace package | not fixed here (audit item); runtime refusal of archive paths, static scan of new modules, existing archive boundary tests in the gate |
| Committed result drift (CRLF, rewrite) | sha256 pins over raw bytes (Task 1, Task 4); `-text` attribute already present |
| Nondeterminism | reader output sorted; two loads byte-identical; `wall_seconds` carried but never compared; `timing_dependent` rows labelled |
| Fixed-budget path changes by accident | golden bytes, `git diff --exit-code` over the module list, AST no-import tests |
| Missing or altered dataset artifacts make validation a silent pass | artifacts tracked (OQ1); a missing file fails the test; sha256 against the stage-1 manifest and the collection manifest before any length is computed |
| Scope creep into gaps or CVRP | row model forbids `gap_*`; no `vehicle_routes` validation code beyond OQ3 |

## Review checklist and mutation targets

The reviewer runs the tests and mutates only source files, in a throw-away worktree (C:\wt\...), never test files. Each mutation must turn at least one test red:

1. `hamiltonian_cycle.py`: drop the closing arc from `closed_length`; use `round` instead of nint; GEO with `3.141592`; accept a repeated node; treat ATSP as symmetric.
2. `rows.py`: allow extra fields; allow `best_solutions`; drop the `ub - lb < 1` rule; drop the timing rule.
3. `reader.py`: skip the outputs sha check; accept an unknown `schema_version`; accept a path under `archive/`; set `ub_validated = true` without validation; accept `union_day_v1`.
4. `protocol_registry.py`: put exact and fixed in one pooling group; make exact rankable.
5. Golden byte test: change one format or rounding in `fair_pilot._aggregate` and confirm `test_fixed_budget_tables_unchanged.py` fails (then revert).

Also check: no change under `uniride_core/`, `optimizer_api/`, `src/`, `archive/`, `docs/paper/results/`, `academic_benchmark/studies/`; commit granularity per task; claims in the design paragraph match test output.

## Effort

WP-E8: about 2.5 days (Task 1 0.25 d, Task 2 0.5 d, Task 3 0.25 d, Task 4 0.75 d, Task 5 0.25 d, Tasks 6-7 0.25 d, Task 8 and review rounds 0.25 d). Companion task: about 0.75 day (tour copies, the 16 `.tsp` files by local copy, archive copy or read-only reconstruction, two manifests, runner default; no download). Medium risk (protocol plumbing); no solver time.

## Owner decisions (resolved 2026-10-18, owner)

1. **OQ1 - instance artifacts: commit them.** The 16 TSP verification instances are committed as `.tsp` files (public TSPLIB research data) in `academic_benchmark/tsplib_data/tsp/` with `MANIFEST.json` recording each file's sha256 and source. Source: a local or archived copy where one exists, otherwise a reconstruction from `tsplib.db` coordinates (read-only, `mode=ro&immutable=1`) with recorded provenance. No download. This is part of the companion task (owner step 4). Effect: Task 5 runs in CI and the gate is no longer partial.
2. **OQ2 - `gap_to_reference`: plan default.** The reader checks the existing exact-vs-published `gap_to_reference` column of `reference.csv` for consistency (`ub - reference_optimum`) and drops it; the row model carries no `gap_*` field.
3. **OQ3 - wave rows: plan default.** For the WP-E3/WP-E4a wave results WP-E8 checks schema and fingerprints (sha256) only and does not re-certify; their rows keep `ub_validated = false` with reason `certified_by_producing_run`.
4. **OQ4 - registration: academic layer.** `exact_reference_v1` is registered in `academic_benchmark/protocol_registry.py`; `uniride_core.algorithms.capabilities.ExecutionProtocol` stays unchanged.
5. **OQ5 - published tours: copy from the archive.** The 13 available `.opt.tour` files are copied (not moved) from the Bildiri archive with `provenance.kind = "archive_copy"` and the archive entry sha256; nothing is downloaded.
6. **OQ6 - study profile: unlinked.** `academic_benchmark/studies/bildiri2026/study.json` is not linked to the exact reference until Package D.
