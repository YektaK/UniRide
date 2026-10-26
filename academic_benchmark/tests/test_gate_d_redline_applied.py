"""Gate D (D-11 / D-14, OQ-14 a): the owner-approved design redline is applied.

Source of truth: ``docs/superpowers/plans/2026-10-23-design-redline_taslak.md`` with the owner
decisions OD-1..OD-7 recorded in DECISION_LOG A18 (2026-10-23).

Each case names one redline item and asserts that a distinctive phrase of the new text is present
and that the replaced operational phrase is gone. Items kept by OD-1 (design lines :20 and :30)
assert that the original text and the dated "Superseded" note are both present. Items the owner
routed elsewhere (OD-5: new migration rows only in the D-11 master table) assert absence.

These are documentation tests: they read text files only and run no solver.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIFICATION = REPO_ROOT / "ACADEMIC_STUDY_UNIFICATION_DESIGN.md"
FAIRNESS = REPO_ROOT / "ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md"
GATE_C_PLAN = (
    REPO_ROOT
    / "docs"
    / "superpowers"
    / "plans"
    / "2026-10-19-gate-c-catalog-composition-experiment-services.md"
)
REDLINE = REPO_ROOT / "docs" / "superpowers" / "plans" / "2026-10-23-design-redline_taslak.md"

SUPERSEDED_NOTE = "Superseded 2026-10-23 by DECISION_LOG A18 (OQ-13 a)"

# (item, file, phrases that must be present, phrases that must be gone)
CASES = [
    # --- A1: branch and publication model --------------------------------------------------
    (
        "A1.1",
        UNIFICATION,
        [
            # OD-1: the approved line keeps its text ...
            "publish the completed remediation on a branch and draft pull request without modifying `WIP` directly.",
            # ... and gains the dated note with the new text.
            SUPERSEDED_NOTE,
            "pushing `WIP` and opening a draft pull request `WIP -> main` that states that paper-scale verification on the stronger computer is pending",
        ],
        [],
    ),
    (
        "A1.2",
        UNIFICATION,
        [
            "Preserve the current rescue checkout and perform work on `codex/reconcile-native-protocol`.",
            SUPERSEDED_NOTE,
            "Each work item runs in its own worktree and branch from `WIP`. The lead merges reviewed items into `WIP` with `--no-ff`.",
            # OD-7
            "preserved rescue head (`archive/local-rescue-20260721`",
        ],
        [],
    ),
    (
        "A1.3",
        UNIFICATION,
        ["Work is merged into `WIP` package by package and is decomposed into four"],
        ["Work remains on `codex/reconcile-native-protocol`"],
    ),
    (
        "A1.4",
        UNIFICATION,
        [
            "- fetch and inspect divergence of `origin/WIP`;",
            "- with the owner's explicit permission, push `WIP` and open a draft pull request `WIP -> main`.",
        ],
        ["fetch and inspect remote divergence;", "- push the branch and open a draft pull request."],
    ),
    (
        "A1.5",
        UNIFICATION,
        [
            "`git status --short` prints nothing after the suites and the integration worktree is clean, and the draft PR `WIP -> main` explicitly awaits powerful-computer verification.",
        ],
        ["the integration worktree is clean, and the draft PR explicitly awaits"],
    ),
    (
        "A1.6",
        UNIFICATION,
        [
            "reconcile only in the integration worktree. Never pull directly into the preserved rescue head.",
            "If the remote has new commits, the Gate D checks are rerun on the reconciled commit before anything is pushed.",
        ],
        ["Never pull directly into the rescue checkout."],
    ),
    (
        "A1.7",
        UNIFICATION,
        [
            "push `WIP` at the commit the checks ran on and open a draft pull request `WIP -> main`. Its text states that paper-scale runs and full-suite verification on the stronger computer are pending.",
        ],
        ["push the branch and open a draft pull request. The draft remains unmerged"],
    ),
    (
        "A1.8",
        UNIFICATION,
        ["10. `WIP` is pushed and a draft pull request `WIP -> main` is opened for powerful-computer verification."],
        ["10. The branch is pushed and a draft pull request is opened"],
    ),
    # --- A2: catalog and composition kinds ---------------------------------------------------
    (
        "A2.1",
        UNIFICATION,
        [
            "Design addition (DECISION_LOG A17, C-16c): `Core-GA-TSP-Memetic-2opt`, study label `GA-2opt`, a counted memetic GA with initial and final 2-opt.",
            "15 VERIFIED IDs, no candidate or planned ID.",
        ],
        [],
    ),
    (
        "A2.2",
        UNIFICATION,
        [
            "- GA-2opt (memetic GA, the design addition below the capability table).",
            "The catalog uses the kinds `pure`, `memetic_2opt`, `local_search`, `global_then_final_3opt` and `global_then_final_alns`; the enum also declares `population_based`, which no claim uses today.",
            "their labels say '(final polish once)'",
        ],
        ["- HHO-ALNS.\n"],
    ),
    # --- A3: alias compatibility and migration table ----------------------------------------
    (
        "A3.1",
        UNIFICATION,
        [
            "| `Numba-GWO`, `Core-GWO-TSP` | `Core-GWO-TSP-Memetic-2opt` | deprecated input alias with warning (CLI only); a manifest that names it is refused |",
            "| `Numba-HHO`, `Core-HHO-TSP` | `Core-HHO-TSP-Memetic-2opt` | deprecated input alias with warning (CLI only); a manifest that names it is refused |",
            "| `SOTA-ALNS-TSP` | `ALNS-TSP` | deprecated input alias with warning (CLI only); a manifest that names it is refused; manifests emit `ALNS-TSP` |",
        ],
        [
            "backward-compatible alias preserving current semantics",
            "backward-compatible alias; manifests emit",
        ],
    ),
    (
        "A3.2",
        UNIFICATION,
        [
            "These names have no registry entry of their own.",
            "`Numba-GA`/`Numba-PSO` in C-14",
            "routing-refusal follow-up `58f77d66`",
            "`B-GA` and `B-PSO` are refused like `GWO-LKH`/`HHO-LKH` and name `Core-GA-TSP` / `Core-PSO-TSP`.",
        ],
        [],
    ),
    (
        # OD-5: the new rows live only in the D-11 master table; the design gets a pointer.
        "A3.3",
        UNIFICATION,
        ["migration table of `CURRENT_ARCHITECTURE.md` (section 8, Gate D item D-11)"],
        [
            "D-11 master-document migration table",
            "Matrix-TwoOpt/GA/PSO/GWO/HHO-TSP-legacy",
            "run `Matrix-TwoOpt-TSP-legacy`",
        ],
    ),
    # --- A4: routing refusals ----------------------------------------------------------------
    (
        "A4.1",
        UNIFICATION,
        [
            "every `Core-*` catalog ID, `ALNS-TSP`, `Numba-Swap`, `Numba-Hybrid`, `SOTA-E2BSO-TSP`, `SOTA-R2DMA-TSP`, `SOTA-P-AOEA-TSP`, `SOTA-CGO-TSP`, `SOTA-RUN-TSP` and `FCM-GA/PSO/GWO/HHO-TSP` refuse CVRP/CVRPTW on every path",
        ],
        ["- unsupported CVRP/CVRPTW requests fail clearly;\n"],
    ),
    # --- A5: study profile schema and analysis plans -----------------------------------------
    (
        "A5.1",
        UNIFICATION,
        [
            "an analysis-plan ID that resolves to `academic_benchmark/studies/<study>/analysis_plan.json` (schema `uniride-analysis-plan/v1`).",
            "The exact-reference link lives in the analysis plan; `study.json` stays unlinked;",
        ],
        ["- an analysis-plan ID;\n"],
    ),
    (
        "A5.2",
        UNIFICATION,
        [
            "Run manifests use `uniride-run/v1` (one per run) and contain the reproducibility fields defined below. A campaign index uses `uniride-run-index/v1`. Analysis plans use `uniride-analysis-plan/v1`.",
        ],
        ["Run manifests use `uniride-run/v1` and contain"],
    ),
    # --- A6: experimental protocol -----------------------------------------------------------
    (
        "A6.1",
        UNIFICATION,
        [
            "On fixed-budget paths every stopping key is written explicitly: `max_no_improvement` and `max_iterations` for GWO/HHO",
            "so no registry default can end a fixed-budget run early. Native Or-opt also requires `max_iterations`.",
        ],
        [],
    ),
    (
        "A6.2",
        UNIFICATION,
        [
            "Results at different levels remain separate and are not pooled.",
            "`scaled_fixed_budget_levels`; Bildiri 2026: 50x and 250x n(n-1)/2",
            "never by raw budget across instances.",
        ],
        [],
    ),
    (
        "A6.3",
        UNIFICATION,
        [
            "### Comparison identity",
            "`assert_single_pooling_group` keeps fixed-budget, native and exact rows apart and nothing more",
            "A family may vary only the algorithm and/or the dataset.",
        ],
        [],
    ),
    # --- A7, A8, A9 --------------------------------------------------------------------------
    (
        "A7.1",
        UNIFICATION,
        [
            "The implementation uses a proven statistical library under a pinned scientific environment.",
            "SciPy 1.18.1 and statsmodels 0.15.0, with their dependencies, are pinned in `requirements-analysis.txt` for academic analysis only, not as an operational dependency.",
            "NumPy 2.4.6, llvmlite 0.48.0 and Numba 0.66.0 stay pinned by `academic_benchmark/jit-benchmark-constraints.txt`.",
            "are local code in `academic_benchmark/analysis/statistics.py` (Gate D item D-05, merged `d8259753`)",
            "Kendall's W is tested against a published worked example (Zar, example 12.6) and the tie-corrected Friedman statistic quoted by Demšar (2006); epsilon-squared and the matched-pairs rank-biserial correlation are tested against independent hand computations",
        ],
        ["will be local code (Gate D item D-05)", "tested against published examples"],
    ),
    (
        "A8.1",
        UNIFICATION,
        ["Each run (algorithm x dataset x budget level x replicate) writes one `RunManifestV1` that records:"],
        ["Each pilot or experiment records:"],
    ),
    (
        "A8.2",
        UNIFICATION,
        [
            "A detached `<manifest>.sha256` file contains the run manifest's checksum.",
            "A campaign index (`run_index.json`, `uniride-run-index/v1`) lists every run manifest with its checksum",
            "Paper mode of the study run service passes `statistics_library_identifier()` (`scipy==1.18.1+statsmodels==0.15.0`)",
            "(`academic_benchmark/studies/run.py:473`)",
            "Smoke mode and any caller that passes nothing keep the literal `none`.",
        ],
        ["until a caller in the pinned environment passes"],
    ),
    (
        # OD-2: study profiles, analysis plans and dataset manifests ship in the wheel.
        "A9.1",
        UNIFICATION,
        [
            "packaging smoke tests prove that archives, `*_legacy` packages and `tsplib.db` files are excluded, and that both study profiles, their analysis plans and the dataset manifests they reference are included, with nothing else under `studies/` or `datasets/`.",
        ],
        [
            "packaging smoke tests prove archives are excluded and study profiles are included.",
            "study profiles are read from the repository",
        ],
    ),
    # --- B: fairness design ------------------------------------------------------------------
    (
        "B1",
        FAIRNESS,
        [
            "The former GWO/HHO registry names (`Numba-GWO`, `Numba-HHO`, `Core-GWO-TSP`, `Core-HHO-TSP`) are no longer registry entries.",
            "A manifest that names them is refused.",
        ],
        ["Existing GWO/HHO public registry names remain registered."],
    ),
    (
        "B2",
        FAIRNESS,
        ["`algorithm_family`: `GWO`, `HHO`, `GA`, `PSO`, `ALNS`, `2-opt`, `3-opt` or `Or-opt`;"],
        ["`algorithm_family`: `GWO`, `HHO`, `2-opt`, or `3-opt`;"],
    ),
    (
        "B3",
        FAIRNESS,
        [
            "`variant`: `pure`, `memetic_2opt`, `global_then_final_3opt` or `global_then_final_alns`;",
            "local searches, ALNS, PSO and pure GA carry `pure`;",
        ],
        ["`variant`: at minimum `pure` or `memetic_2opt`;"],
    ),
    (
        "B4",
        FAIRNESS,
        [
            "- `Core-HHO-TSP-Memetic-2opt`\n",
            "The full set of canonical identities is the 15 VERIFIED IDs of the capability catalog (`uniride_core/algorithms/capabilities.py`)",
        ],
        [],
    ),
    (
        "B5",
        FAIRNESS,
        [
            "Deprecated GWO/HHO aliases resolve to the memetic 2-opt canonical IDs (CLI only, with a warning). Pure variants disable initial, periodic, and final 2-opt calls",
        ],
        ["Existing GWO/HHO aliases remain backward-compatible and report `variant=memetic_2opt`."],
    ),
    (
        "B6",
        FAIRNESS,
        [
            "8. On fixed-budget paths the secondary stopping keys are written explicitly: `max_no_improvement` and `max_iterations` for GWO/HHO, `max_iterations` for 2-opt, 3-opt and Or-opt. A missing or non-positive key is refused before any evaluation.",
        ],
        [],
    ),
    (
        "B7",
        FAIRNESS,
        [
            "Rows of different protocol versions (`uniride-fair-tsp-v1`, `uniride-fair-tsp-v2`) are never one comparison cell, although the protocol registry puts them in one pooling group.",
        ],
        [],
    ),
    (
        "B8",
        FAIRNESS,
        [
            "It does not claim Numba parity in the ordinary interpreter's NumPy 2.5.1 environment (recorded 2026-07-17). The JIT benchmark environment is separate and pins NumPy 2.4.6, llvmlite 0.48.0 and Numba 0.66.0 (`academic_benchmark/jit-benchmark-constraints.txt`).",
        ],
        ["It does not claim Numba parity in the current NumPy 2.5.1 environment."],
    ),
    # --- C: closed Gate C plan (OD-6: function name instead of line number) -------------------
    (
        "C1",
        GATE_C_PLAN,
        ["Output directory rules of `fair_pilot._prepare_output_dir`;"],
        ["fair_pilot.py:283-300"],
    ),
]


@pytest.mark.parametrize(
    "item, path, present, gone", CASES, ids=[case[0] for case in CASES]
)
def test_redline_item_applied(item, path, present, gone):
    text = path.read_text(encoding="utf-8")
    for phrase in present:
        assert phrase in text, f"{item}: new text missing from {path.name}: {phrase!r}"
    for phrase in gone:
        assert phrase not in text, f"{item}: replaced text still in {path.name}: {phrase!r}"


def test_od1_note_is_dated_and_on_both_approved_lines():
    """OD-1: exactly the two approved lines (:20 and :30) carry the superseded note."""
    text = UNIFICATION.read_text(encoding="utf-8")
    assert text.count(SUPERSEDED_NOTE) == 2


def test_c1_other_citation_site_is_also_function_name():
    text = GATE_C_PLAN.read_text(encoding="utf-8")
    assert "(reuse `fair_pilot._prepare_output_dir` rules)" in text


def test_redline_header_status_is_applied():
    first_lines = REDLINE.read_text(encoding="utf-8").splitlines()[:5]
    status = [line for line in first_lines if line.startswith("Status:")]
    assert len(status) == 1
    assert status[0].startswith("Status: APPLIED on ")
    assert " in " in status[0]
