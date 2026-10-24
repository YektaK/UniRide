"""Gate D, D-05: the guarded statistics service (plan 2026-10-23 section 3, D-05; DECISION_LOG A18 OQ-5/6/7/8/9/15).

Every test value below is known independently of the service: either by a hand computation written next to it, or
from a published worked example (cited in the test), or from a direct SciPy / statsmodels call. Fixtures are
synthetic; nothing here runs a solver or reads a result file. No test asserts a ranking or superiority claim.

Sources of the worked examples (offline; no new download was possible in the build environment):

* Friedman statistic 10.68 for k = 4 treatments and b = 5 blocks: J. H. Zar, "Biostatistical Analysis", example 12.6
  (the data are quoted with this citation in the SciPy test ``TestFriedmanChiSquare``, ``x3``). Kendall's W follows from the
  published statistic by its definition W = chi2_F / (b (k - 1)) (Kendall and Babington Smith 1939; Kendall and Gibbons 1990).
* Friedman statistic with ties, 10.2283464566929 for k = 4 and b = 14: Demsar (2006), "Statistical Comparisons of Classifiers
  over Multiple Data Sets" (data as quoted in the same SciPy test, ``x1``; the value is the tie-corrected statistic "verified
  with matlab and R" there; Demsar's own 9.28 is the uncorrected one).
* Epsilon-squared, the matched-pairs rank-biserial correlation and Vargha-Delaney A12: no published worked example with data
  was available offline, so these are tested against independent hand computations given in the docstring of each test
  (formulas: Tomczak and Tomczak 2014, Trends in Sport Sciences 21(1); Kerby 2014, Comprehensive Psychology 3; Vargha and
  Delaney 2000, J. Educational and Behavioral Statistics 25(2)), and A12 additionally against statsmodels
  ``rank_compare_2indep(x, y).prob1`` and ``mannwhitneyu(x, y).statistic / (n1 * n2)`` (A18, D-04a note).
"""
from __future__ import annotations

import ast
import itertools
import math
from pathlib import Path

import numpy as np
import pytest
from scipy import stats as sps
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.nonparametric import rank_compare_2indep

from academic_benchmark.analysis import environment as analysis_environment
from academic_benchmark.analysis import statistics as stats_service
from academic_benchmark.analysis.statistics import (
    StatisticsRefusal,
    analyse_family,
    describe_sample,
    epsilon_squared,
    holm_adjust,
    iman_davenport_f,
    is_significant,
    kendalls_w,
    matched_pairs_rank_biserial,
    smallest_possible_adjusted_p,
    vargha_delaney_a12,
)
from academic_benchmark.analysis.identity import comparison_cell_key
from academic_benchmark.analysis.manifests import make_run_id
from academic_benchmark.contracts import RunManifestV1
from academic_benchmark.contracts.run_index import RunIndexV1
from academic_benchmark.contracts.analysis_plan import AnalysisPlanV1
from academic_benchmark.fairness import normalize_problem
from academic_benchmark.studies.service import load_study_with_plan
from academic_benchmark.studies.smoke import assert_no_ranking_words

REPO = Path(__file__).resolve().parents[2]
FAIR_V2 = "uniride-fair-tsp-v2"
COMMIT = "a" * 40
PER_INSTANCE = "per-instance-independent"
ACROSS = "across-instances-tsp-matched"
_BILDIRI = load_study_with_plan("academic_benchmark/studies/bildiri2026/study.json", repository_root=REPO, mode="smoke").study
STUDY3 = _BILDIRI.model_copy(update={"algorithm_ids": ["Core-GA-TSP", "Core-PSO-TSP", "Core-GWO-TSP-Pure"]})  # the three algorithms of the fixtures
CROSS_INSTANCES = ["berlin52", "eil51", "st70", "kroA100", "rd100", "eil76"]
SEPARATED = {"Core-GA-TSP": [1, 2, 3, 4, 5], "Core-PSO-TSP": [6, 7, 8, 9, 10], "Core-GWO-TSP-Pure": [11, 12, 13, 14, 15]}
INTERLEAVED = {"Core-GA-TSP": [1, 4, 7, 10, 13], "Core-PSO-TSP": [2, 5, 8, 11, 14], "Core-GWO-TSP-Pure": [3, 6, 9, 12, 15]}


# ---------------------------------------------------------------- fixtures
def _dataset(dataset_id, dimension=51):
    return {
        "schema_version": "uniride-dataset/v1", "dataset_id": dataset_id,
        "artifact_path": f"academic_benchmark/tsplib_data/tsp/{dataset_id}.tsp",
        "source": {"authority_url": "https://example.invalid/x", "retrieved_on": "2026-10-19"},
        "checksum": {"algorithm": "sha256", "value": "0" * 64}, "problem_type": "TSP", "dimension": dimension,
        "matrix_semantics": {"directed": False, "edge_weight_type": "EUC_2D", "diagonal_semantics": "zero"},
        "best_known": {"status": "optimal", "value": 426.0, "provenance": "fixture"},
    }


def _levels(problem):
    base = 1000 + 17 * len(problem)
    return (base, base * 5)


def make_item(problem, algorithm, replicate, gap, *, dirty=False, evidence=None, level=0, **row_extra):
    levels = _levels(problem)
    dataset_id = f"tsplib-{normalize_problem(problem)}"
    manifest = RunManifestV1.model_validate({
        "schema_version": "uniride-run/v1", "run_id": make_run_id("bildiri2026", dataset_id, algorithm, level, replicate),
        "study_id": "bildiri2026", "protocol_version": FAIR_V2, "git": {"commit": COMMIT, "dirty": dirty},
        "environment": {"python": "3.13", "operating_system": "test", "cpu": "test", "numpy": "2.4.6",
                        "numba": "0.66.0", "llvmlite": "0.48.0", "statistics_library": "none"},
        "dataset": _dataset(dataset_id),
        "algorithm": {"algorithm_id": algorithm, "capabilities": {}, "backend_policy": "prefer_numba",
                      "backend_profile": {"objective": "numba", "polish": "none"}, "capability_evidence_ids": ["fixture"],
                      "configuration": {"population": 20, "algorithm": algorithm}, "composition_stages": []},
        "seeds": {"base_seed": 2026, "derived": {"run_seed": 1}},
        "budget": {"levels": list(levels), "policy": "atomic_upper_bound_v1", "objective_evaluations": 5, "stage_allocation": {}},
        "termination": {"reason": "evaluation_budget_exhausted", "runtime_seconds": 0.1},
        "validation": {"passed": True, "checks": ["hamiltonian"]}, "outputs": [],
    })
    row = {
        "protocol_version": FAIR_V2, "comparison_regime": "fixed_evaluation_budget", "problem": problem,
        "algorithm_id": algorithm, "variant": "pure", "study_id": "bildiri2026", "evaluation_budget": levels[level],
        "termination_policy": "atomic_upper_bound_v1;max_iterations=1237500;max_no_improvement=1237500",
        "polish_policy": {"enabled": False, "initial": False, "periodic": False, "final": False, "operator": None},
        "objective_cost": 500.0 + gap, "elapsed_ms": 1.0, "replicate": replicate,
        "gap_to_exact_reference": gap, "gap_unit": "percent", "exact_reference_value": 426, "gap_missing_reason": None,
    }
    if evidence is not None:
        row["evidence_class"] = evidence
    row.update(row_extra)
    return row, manifest


def failed_item(problem, algorithm, replicate, **overrides):
    row = {
        "record_kind": "failed_run", "validation_status": "failed", "protocol_version": FAIR_V2, "study_id": "bildiri2026",
        "comparison_regime": "fixed_evaluation_budget", "problem": problem, "algorithm_id": algorithm,
        "replicate": replicate, "evaluation_budget": _levels(problem)[0],
    }
    row.update(overrides)
    return row, None


def index_for(items, mode="paper", *, study_id="bildiri2026", dirty=False, drop=(), digest_of=None, extra_items=()):
    """A ``RunIndexV1`` that lists the manifest of every completed item (the campaign index the caller has verified)."""
    runs = []
    for row, manifest in [*items, *extra_items]:
        if manifest is None or manifest.run_id in drop or any(r["run_id"] == manifest.run_id for r in runs):
            continue
        digest = comparison_cell_key(row, manifest, allow_dirty=True).digest()
        runs.append({"run_id": manifest.run_id, "manifest_path": f"manifests/{manifest.run_id}.json",
                     "manifest_checksum": {"algorithm": "sha256", "value": "b" * 64},
                     "comparison_key_digest": "0" * 64 if digest_of == "wrong" else digest})
    environment = {"python": "3.13", "operating_system": "test", "cpu": "test", "numpy": "2.4.6", "numba": "0.66.0",
                   "llvmlite": "0.48.0", "statistics_library": "none"}
    return RunIndexV1.model_validate({
        "schema_version": "uniride-run-index/v1", "study_id": study_id, "mode": mode, "status": "passed",
        "seed_protocol_version": "sha256-seed-v1", "base_seed": 2026, "git": {"commit": COMMIT, "dirty": dirty},
        "environment": environment, "runs": runs, "outputs": [],
    })


def per_instance_items(samples, problem="eil51"):
    return [make_item(problem, algorithm, r, gap) for algorithm, values in samples.items() for r, gap in enumerate(values)]


ALGORITHMS = ("Core-GA-TSP", "Core-PSO-TSP", "Core-GWO-TSP-Pure")


def cross_items(shift=0.0, problems=CROSS_INSTANCES, algorithms=ALGORITHMS, *, centres=None, skew=None):
    """Every instance orders the algorithms the same way; the per-instance median of A, B, C is i, i + 1, i + 2 unless
    ``centres[(problem, algorithm)]`` overrides it. ``skew[(problem, algorithm)]`` replaces the symmetric replicate offsets
    (-0.1, 0, +0.1) of that cell, so that its mean differs from its median (the median stays the centre)."""
    items = []
    for i, problem in enumerate(problems):
        for a, algorithm in enumerate(algorithms):
            centre = (centres or {}).get((problem, algorithm), float(i + a)) + shift
            offsets = (skew or {}).get((problem, algorithm), (-0.1, 0.0, 0.1))
            for r, offset in enumerate(offsets):
                items.append(make_item(problem, algorithm, r, centre + offset))
    return items


@pytest.fixture(scope="module")
def draft_plans():
    out = {}
    for study in ("bildiri2026", "yaem2026"):
        loaded = load_study_with_plan(f"academic_benchmark/studies/{study}/study.json", repository_root=REPO, mode="smoke")
        out[study] = loaded.analysis_plan.plan
    return out


@pytest.fixture(scope="module")
def draft(draft_plans):
    return draft_plans["bildiri2026"]


def activate(plan, *, minimum_n=3, alpha=None, rule=None, mutate=None):
    data = plan.model_dump(mode="json")
    data.update(status="active", unresolved=[], minimum_n_per_cell=minimum_n)
    if alpha is not None:
        data["alpha"] = alpha
    if rule is not None:
        for family in data["families"]:
            family["post_hoc"]["rule"] = rule
    if mutate is not None:
        mutate(data)
    return AnalysisPlanV1.model_validate(data)


@pytest.fixture(scope="module")
def active(draft):
    return activate(draft)


def study_for(items):
    """The profile of a test: the Bildiri study with exactly the algorithms that occur in the items (completed or failed)."""
    names = {row["algorithm_id"] for row, _ in items}
    return _BILDIRI.model_copy(update={"algorithm_ids": [a for a in (*ALGORITHMS, *sorted(names - set(ALGORITHMS))) if a in names]})


def run(items, plan, family=PER_INSTANCE, *, mode="paper", study=None, **index_options):
    return analyse_family(items, study=study or study_for(items), plan=plan, family_id=family, run_index=index_for(items, mode, **index_options))


# ---------------------------------------------------------------- effect sizes against independent values
def test_epsilon_squared_hand_example():
    """Three groups [1,2,3], [4,5,6], [7,8,9]: rank sums 6, 15, 24, H = 12/(9*10) * (36 + 225 + 576)/3 - 3*10 = 7.2 (hand),
    so epsilon-squared = H / ((n^2 - 1) / (n + 1)) = 7.2 / 8 = 0.9 (Tomczak and Tomczak 2014)."""
    assert epsilon_squared(7.2, 9) == pytest.approx(0.9, abs=1e-12)
    assert sps.kruskal([1, 2, 3], [4, 5, 6], [7, 8, 9]).statistic == pytest.approx(7.2, abs=1e-12)
    # the service's omnibus for five-observation groups: H = 12.5 by hand, epsilon-squared = 12.5 / 14
    assert epsilon_squared(12.5, 15) == pytest.approx(12.5 / 14, abs=1e-12)


def test_epsilon_squared_refuses_impossible_inputs():
    for h, n in ((-1.0, 9), (float("nan"), 9), (3.0, 1), (3.0, True)):
        with pytest.raises(StatisticsRefusal):
            epsilon_squared(h, n)


def test_kendalls_w_published_zar_example_without_ties():
    """Zar example 12.6: chi2_F = 10.68 (published, k = 4, b = 5), so W = 10.68 / (5 * 3) = 0.712."""
    columns = [[7.0, 9.9, 8.5, 5.1, 10.3], [5.3, 5.7, 4.7, 3.5, 7.7], [4.9, 7.6, 5.5, 2.8, 8.4], [8.8, 8.9, 8.1, 3.3, 9.1]]
    blocks = [list(block) for block in zip(*columns)]  # one block = the four treatments of one subject
    assert kendalls_w(blocks) == pytest.approx(10.68 / 15, abs=5e-4)
    assert kendalls_w(blocks) * 5 * 3 == pytest.approx(sps.friedmanchisquare(*columns).statistic, abs=1e-9)


def test_kendalls_w_with_ties_matches_the_tie_corrected_published_statistic():
    """Demsar 2006 data (k = 4, b = 14, ties in one block): tie-corrected chi2_F = 10.2283464566929 (verified with MATLAB and
    R, as recorded in the SciPy test), so W = chi2_F / (b (k - 1))."""
    columns = [
        [0.763, 0.599, 0.954, 0.628, 0.882, 0.936, 0.661, 0.583, 0.775, 1.0, 0.94, 0.619, 0.972, 0.957],
        [0.768, 0.591, 0.971, 0.661, 0.888, 0.931, 0.668, 0.583, 0.838, 1.0, 0.962, 0.666, 0.981, 0.978],
        [0.771, 0.590, 0.968, 0.654, 0.886, 0.916, 0.609, 0.563, 0.866, 1.0, 0.965, 0.614, 0.9751, 0.946],
        [0.798, 0.569, 0.967, 0.657, 0.898, 0.931, 0.685, 0.625, 0.875, 1.0, 0.962, 0.669, 0.975, 0.970],
    ]
    blocks = [list(block) for block in zip(*columns)]
    assert kendalls_w(blocks) == pytest.approx(10.2283464566929 / (14 * 3), abs=1e-12)


def test_kendalls_w_hand_extremes():
    """Perfect agreement of three blocks over three treatments gives W = 1; the cyclic Latin square of ranks (every treatment
    has rank sum 6) gives W = 0 (hand computation from the rank sums)."""
    assert kendalls_w([[1, 2, 3], [10, 20, 30], [0.1, 0.2, 0.3]]) == pytest.approx(1.0, abs=1e-12)
    assert kendalls_w([[1, 2, 3], [2, 3, 1], [3, 1, 2]]) == pytest.approx(0.0, abs=1e-12)


def test_kendalls_w_is_undefined_when_every_block_is_constant():
    assert kendalls_w([[1, 1, 1], [2, 2, 2]]) is None


def test_a12_hand_example_and_library_cross_checks():
    """x = [1,2,3], y = [2,3,4]: of the 9 pairs, x > y in 1 (3 > 2), they tie in 2 (2 = 2, 3 = 3) and x < y in 6, so
    A12 = (1 + 0.5 * 2) / 9 = 2/9 (Vargha and Delaney 2000)."""
    assert vargha_delaney_a12([1, 2, 3], [2, 3, 4]) == pytest.approx(2 / 9, abs=1e-12)
    assert vargha_delaney_a12([1, 2, 3], [2, 3, 4]) + vargha_delaney_a12([2, 3, 4], [1, 2, 3]) == pytest.approx(1.0)
    rng = np.random.default_rng(20261023)
    for n1, n2 in ((7, 9), (12, 5), (30, 30)):
        x = rng.integers(0, 9, n1).astype(float).tolist()  # integer data: many ties
        y = rng.integers(0, 9, n2).astype(float).tolist()
        mine = vargha_delaney_a12(x, y)
        assert mine == pytest.approx(rank_compare_2indep(x, y).prob1, abs=1e-12)
        assert mine == pytest.approx(sps.mannwhitneyu(x, y).statistic / (n1 * n2), abs=1e-12)


def test_matched_pairs_rank_biserial_hand_examples():
    """Differences x - y = [+1, +2, -3, +4, +5]: ranks of |d| are 1..5, T+ = 1 + 2 + 4 + 5 = 12, T- = 3, so
    r = (T+ - T-) / (T+ + T-) = 9/15 = 0.6 (Kerby 2014, simple difference formula).
    With a zero difference, d = [+1, +2, 0, -3, +4]: wilcox drops it (T+ = 7, T- = 3, r = 0.4); pratt ranks it and then drops
    its rank (ranks 1..5, zero rank 1 removed: T+ = 2 + 3 + 5 = 10, T- = 4, r = 6/14); zsplit splits its rank (T+ = 10.5,
    T- = 4.5, r = 6/15 = 0.4)."""
    assert matched_pairs_rank_biserial([1, 2, 0, 4, 5], [0, 0, 3, 0, 0], "wilcox") == pytest.approx(0.6, abs=1e-12)
    x, y = [1, 2, 5, 0, 4], [0, 0, 5, 3, 0]
    assert matched_pairs_rank_biserial(x, y, "wilcox") == pytest.approx(0.4, abs=1e-12)
    assert matched_pairs_rank_biserial(x, y, "pratt") == pytest.approx(6 / 14, abs=1e-12)
    assert matched_pairs_rank_biserial(x, y, "zsplit") == pytest.approx(0.4, abs=1e-12)
    assert matched_pairs_rank_biserial(y, x, "wilcox") == pytest.approx(-0.4, abs=1e-12)  # swapping the pair flips the sign
    assert matched_pairs_rank_biserial([1, 2], [1, 2], "wilcox") is None  # no non-zero difference: undefined


def test_rank_biserial_equals_one_minus_twice_the_smaller_signed_rank_sum_over_the_total():
    """Wendt (1972): r = +/-(1 - 2 T_min / (n (n + 1) / 2)); T_min is SciPy's two-sided Wilcoxon statistic (no ties, no zeros)."""
    rng = np.random.default_rng(7)
    for _ in range(5):
        x, y = rng.normal(size=9), rng.normal(size=9)
        t_min = sps.wilcoxon(x, y).statistic
        expected = 1 - 2 * t_min / (9 * 10 / 2)
        assert abs(matched_pairs_rank_biserial(x.tolist(), y.tolist(), "wilcox")) == pytest.approx(expected, abs=1e-12)


def test_descriptive_sample_uses_type_7_quantiles_and_the_plan_sd_convention(draft):
    """[1,2,3,4]: Hyndman-Fan type 7 gives Q1 = 1.75 and Q3 = 3.25 (h = (n - 1) p + 1), IQR 1.5; the sample SD is
    sqrt(5/3) (n - 1), the population SD sqrt(5/4)."""
    spec = draft.descriptive
    assert spec.sd_convention == "sample_n_minus_1" and spec.quantile_method == "hyndman_fan_type_7"
    out = describe_sample([1, 2, 3, 4], spec)
    assert out == pytest.approx({"n": 4, "median": 2.5, "iqr": 1.5, "min": 1, "max": 4, "mean": 2.5, "sd": math.sqrt(5 / 3)})
    population = spec.model_copy(update={"sd_convention": "population_n"})
    assert describe_sample([1, 2, 3, 4], population)["sd"] == pytest.approx(math.sqrt(5 / 4))
    assert set(out) == set(spec.columns)
    narrower = spec.model_copy(update={"columns": ["n", "median"]})
    assert set(describe_sample([1, 2, 3, 4], narrower)) == {"n", "median"}


def test_descriptive_sample_of_one_value_has_an_empty_sd_and_an_empty_sample_is_refused(draft):
    out = describe_sample([3.5], draft.descriptive)
    assert out["n"] == 1 and out["sd"] is None and out["mean"] == out["median"] == out["min"] == 3.5 and out["iqr"] == 0
    with pytest.raises(StatisticsRefusal):
        describe_sample([], draft.descriptive)
    with pytest.raises(StatisticsRefusal):
        describe_sample([1.0, float("nan")], draft.descriptive)


# ---------------------------------------------------------------- per-instance family against exact known values
def test_per_instance_family_reproduces_the_hand_computed_values(active):
    """Three separated groups of five ([1..5], [6..10], [11..15]): H = 12/(15*16) * (15^2 + 40^2 + 65^2)/5 - 3*16 = 12.5 (hand),
    p = exp(-H/2) (chi-square with 2 df), epsilon-squared = 12.5/14; each pairwise U is 0 or 25, the exact two-sided
    p = 2 / C(10, 5) = 1/126, Holm over three pairs: 3/126 = 1/42; A12 is 0 or 1."""
    result = run(per_instance_items(SEPARATED), active)
    assert result.inference_refused == () and result.inference is not None
    omnibus = result.inference.omnibus
    assert omnibus.test == "kruskal_wallis" and omnibus.status == "computed"
    assert omnibus.statistic == pytest.approx(12.5, abs=1e-12)
    assert omnibus.p_value == pytest.approx(math.exp(-6.25), rel=1e-12)
    assert omnibus.effect_size_name == "epsilon_squared" and omnibus.effect_size == pytest.approx(12.5 / 14, abs=1e-12)
    assert omnibus.significant is True
    assert result.inference.post_hoc_ran is True and len(result.inference.pairs) == 3
    for pair in result.inference.pairs:
        assert pair.test == "mann_whitney_u" and pair.n_a == pair.n_b == 5
        assert pair.p_value == pytest.approx(1 / 126, abs=1e-12)
        assert pair.p_holm == pytest.approx(1 / 42, abs=1e-12) and pair.significant is True
        assert pair.effect_size_name == "vargha_delaney_a12"
        assert pair.effect_size == (1.0 if SEPARATED[pair.algorithm_a][0] > SEPARATED[pair.algorithm_b][0] else 0.0)
    names = {(p.algorithm_a, p.algorithm_b) for p in result.inference.pairs}
    assert names == set(itertools.combinations(sorted(SEPARATED), 2))
    assert {c.algorithm_id: c.summary["n"] for c in result.cells} == {name: 5 for name in SEPARATED}


def test_holm_adjustment_equals_statsmodels_on_unequal_p_values(active):
    samples = {"Core-GA-TSP": [1, 2, 3, 4, 5, 6], "Core-PSO-TSP": [2.5, 3.5, 7, 8, 9, 10], "Core-GWO-TSP-Pure": [11, 12, 13, 14, 15, 16]}
    result = run(per_instance_items(samples), active)
    pairs = sorted(result.inference.pairs, key=lambda p: (p.algorithm_a, p.algorithm_b))
    direct = [sps.mannwhitneyu(samples[p.algorithm_a], samples[p.algorithm_b], method="exact", alternative="two-sided").pvalue for p in pairs]
    holm = multipletests(direct, alpha=0.05, method="holm")[1]
    assert [p.p_value for p in pairs] == pytest.approx(direct, abs=1e-12)
    assert [p.p_holm for p in pairs] == pytest.approx(list(holm), abs=1e-12)
    assert len({round(p.p_value, 12) for p in pairs}) > 1  # the p-values are not all equal, so Holm is exercised


def test_post_hoc_runs_only_after_a_significant_omnibus_under_the_declared_rule(active, draft):
    items = per_instance_items(INTERLEAVED)
    gated = run(items, active)
    # H = 0.5 by hand (rank sums 35, 40, 45), p = exp(-0.25)
    assert gated.inference.omnibus.statistic == pytest.approx(0.5, abs=1e-12)
    assert gated.inference.omnibus.p_value == pytest.approx(math.exp(-0.25), rel=1e-12)
    assert gated.inference.omnibus.significant is False
    assert gated.inference.post_hoc_ran is False and gated.inference.pairs == ()
    assert "omnibus" in gated.inference.post_hoc_reason
    # the same data under the other rule the plan can declare: the plan, not the code, decides
    always = run(items, activate(draft, rule="always_over_declared_family"))
    assert always.inference.post_hoc_ran is True and len(always.inference.pairs) == 3
    direct = sps.mannwhitneyu(INTERLEAVED["Core-GA-TSP"], INTERLEAVED["Core-PSO-TSP"], method="exact").pvalue
    first = [p for p in always.inference.pairs if (p.algorithm_a, p.algorithm_b) == ("Core-GA-TSP", "Core-PSO-TSP")][0]
    assert first.p_value == pytest.approx(direct, abs=1e-12)


def test_alpha_is_read_from_the_plan_not_from_the_code(draft):
    items = per_instance_items(INTERLEAVED)  # omnibus p = 0.7788
    assert run(items, activate(draft, alpha=0.05)).inference.post_hoc_ran is False
    relaxed = run(items, activate(draft, alpha=0.9))
    assert relaxed.inference.omnibus.significant is True and relaxed.inference.post_hoc_ran is True
    source = Path(stats_service.__file__).read_text(encoding="utf-8")
    for literal in ("0.05", "0.01", "alpha = 0", "holm_alpha"):
        assert literal not in source


# ---------------------------------------------------------------- the conventions are analysis-plan fields (owner decisions, A18)
def _plan_dict(plan):
    return plan.model_dump(mode="json")


def test_both_real_plans_carry_the_owner_conventions(draft_plans):
    for plan in draft_plans.values():
        c = plan.conventions
        assert (c.mann_whitney.method, c.mann_whitney.continuity_correction) == ("auto", True)
        assert (c.wilcoxon.method, c.wilcoxon.continuity_correction, c.wilcoxon.zero_method) == ("auto", False, "pratt")
        assert (c.friedman.primary_p_value, list(c.friedman.also_report)) == ("iman_davenport_f", ["chi_square"])
        assert (c.alternative, c.significance, c.holm_scope, c.correction_across_instances) == (
            "two_sided", "p_less_than_or_equal_alpha", "within_comparison_cell", "none")
        assert "Wilcoxon" in plan.power_declaration.statement and plan.power_declaration.pairwise_evidence == "per_instance_mann_whitney"


@pytest.mark.parametrize("field", ["conventions", "power_declaration"])
def test_a_plan_without_the_convention_fields_is_refused(draft, field):
    data = _plan_dict(draft)
    del data[field]
    with pytest.raises(Exception):
        AnalysisPlanV1.model_validate(data)
    for key, value in (("alternative", "greater"), ("significance", "p_less_than_alpha"), ("holm_scope", "across_everything")):
        data = _plan_dict(draft)
        data["conventions"][key] = value
        with pytest.raises(Exception):
            AnalysisPlanV1.model_validate(data)
    data = _plan_dict(draft)
    del data["conventions"]["wilcoxon"]["zero_method"]
    with pytest.raises(Exception):
        AnalysisPlanV1.model_validate(data)


def test_mann_whitney_auto_reports_the_method_actually_used_per_pair(active):
    """scipy 1.18.1 ``method="auto"`` (``_mwu_choose_method``): exact only when at least one sample has at most 8 observations and there
    are no ties; asymptotic otherwise (with the plan's continuity correction). Each reported label is checked against the p-value of an
    explicit call of that method, so a wrong label cannot hide behind equal p-values."""
    untied = {"Core-GA-TSP": [1, 2, 3, 4, 5], "Core-PSO-TSP": [4.5, 6, 7, 8, 9]}
    tied = {"Core-GA-TSP": [1, 2, 3, 4, 5], "Core-PSO-TSP": [4, 6, 7, 8, 9]}
    nine_vs_five = {"Core-GA-TSP": [float(v) for v in range(9)], "Core-PSO-TSP": [v + 3.5 for v in range(5)]}  # one sample <= 8, no ties
    thirty = {"Core-GA-TSP": [float(v) for v in range(30)], "Core-PSO-TSP": [v + 10.5 for v in range(30)]}  # both > 8, no ties
    for samples, label in ((untied, "exact"), (tied, "asymptotic"), (nine_vs_five, "exact"), (thirty, "asymptotic")):
        pair = run(per_instance_items(samples), active).inference.pairs[0]
        x, y = samples["Core-GA-TSP"], samples["Core-PSO-TSP"]
        assert pair.method_used == label
        assert pair.p_value == pytest.approx(sps.mannwhitneyu(x, y, method=label, use_continuity=True).pvalue, abs=1e-12)
    # 30 against 30 without ties: scipy auto is asymptotic and differs from the exact p-value (the former wrong label was "exact")
    x, y = thirty["Core-GA-TSP"], thirty["Core-PSO-TSP"]
    assert sps.mannwhitneyu(x, y, method="exact").pvalue != pytest.approx(sps.mannwhitneyu(x, y, method="asymptotic").pvalue, rel=1e-6)
    assert sps.mannwhitneyu(x, y, method="auto").pvalue == pytest.approx(sps.mannwhitneyu(x, y, method="asymptotic").pvalue, abs=1e-15)
    big = {"Core-GA-TSP": list(range(60)), "Core-PSO-TSP": [v + 0.5 for v in range(30, 90)]}
    assert run(per_instance_items(big), active).inference.pairs[0].method_used == "asymptotic"


def test_the_iman_davenport_p_not_the_chi_square_p_opens_the_omnibus_gate(draft):
    """Rank sums 8, 12, 16 over six blocks (four blocks A < B < C, one C < A < B, one B < A < C): chi2_F = 464/6 - 72 = 16/3, chi-square
    p = exp(-8/3) = 0.0695, Iman-Davenport F = 5 * (16/3) / (12 - 16/3) = 4 with (2, 10) df, p = 1.8^-5 = 0.0529. At alpha 0.06 only
    the F p-value is significant, so the post-hoc tests must run under only_after_significant_omnibus; at alpha 0.05 neither is."""
    orders = [(0, 1, 2)] * 4 + [(1, 2, 0), (1, 0, 2)]
    centres = {(problem, algorithm): 10.0 * i + orders[i][a]
               for i, problem in enumerate(CROSS_INSTANCES) for a, algorithm in enumerate(ALGORITHMS)}
    items = cross_items(centres=centres)
    relaxed = run(items, activate(draft, alpha=0.06), ACROSS)
    omnibus = relaxed.inference.omnibus
    assert omnibus.chi_square_statistic == pytest.approx(16 / 3, abs=1e-9) and omnibus.statistic == pytest.approx(4.0, abs=1e-9)
    assert omnibus.chi_square_p_value == pytest.approx(math.exp(-8 / 3), rel=1e-9) and omnibus.chi_square_p_value > 0.06
    assert omnibus.p_value == pytest.approx(1.8 ** -5, rel=1e-9) and omnibus.p_value <= 0.06
    assert omnibus.significant is True and relaxed.inference.post_hoc_ran is True and len(relaxed.inference.pairs) == 3
    strict = run(items, activate(draft, alpha=0.05), ACROSS).inference
    assert strict.omnibus.significant is False and strict.post_hoc_ran is False


def test_wilcoxon_auto_is_asymptotic_above_fifty_units():
    """scipy ``_wilcoxon_iv``: ``method="auto"`` with more than 50 differences is asymptotic even without ties or zeros."""
    from academic_benchmark.analysis.statistics import wilcoxon_method_used
    x = [float(v) for v in range(51)]
    y = [v * 1.37 + 0.11 for v in x]  # 51 distinct non-zero differences
    assert len({abs(a - b) for a, b in zip(x, y)}) == 51 and all(a != b for a, b in zip(x, y))
    assert wilcoxon_method_used(x, y, "auto") == "asymptotic"
    assert sps.wilcoxon(x, y, zero_method="pratt", method="auto").pvalue == pytest.approx(
        sps.wilcoxon(x, y, zero_method="pratt", method="asymptotic").pvalue, abs=1e-15)
    assert wilcoxon_method_used(x[:50], y[:50], "auto") == "exact"


def test_perfect_agreement_text_states_that_f_is_infinite_and_where_f_comes_from(active):
    text = run(cross_items(), active, ACROSS).text
    assert "F infinite (perfect agreement), p below machine precision" in text
    assert "tie-corrected chi-square" in text and "p 0" not in text.replace("p 0.", "p x.")  # no bare "p 0" for the infinite F
    assert_no_ranking_words(text)
    swapped = run(swapped_cross_items(), active, ACROSS).text
    assert "F infinite" not in swapped and "tie-corrected chi-square" in swapped


def test_the_study_profile_must_match_the_plan_and_the_index(active):
    items = per_instance_items(SEPARATED)
    wrong = _BILDIRI.model_copy(update={"study_id": "yaem2026", "algorithm_ids": list(ALGORITHMS)})
    with pytest.raises(StatisticsRefusal, match="study"):
        run(items, active, study=wrong)
    with pytest.raises(StatisticsRefusal, match="StudyManifestV1"):
        run(items, active, study="bildiri2026")




def test_the_plan_conventions_not_the_code_decide_the_method(draft):
    samples = {"Core-GA-TSP": [1, 2, 3, 4, 5], "Core-PSO-TSP": [4.5, 6, 7, 8, 9]}
    items = per_instance_items(samples)

    def with_method(method, continuity):
        def mutate(data):
            data["conventions"]["mann_whitney"] = {"method": method, "continuity_correction": continuity}
        return run(items, activate(draft, mutate=mutate)).inference.pairs[0]

    exact, asymptotic, no_correction = with_method("exact", True), with_method("asymptotic", True), with_method("asymptotic", False)
    assert exact.method_used == "exact" and asymptotic.method_used == no_correction.method_used == "asymptotic"
    assert asymptotic.p_value == pytest.approx(sps.mannwhitneyu(*samples.values(), method="asymptotic", use_continuity=True).pvalue)
    assert no_correction.p_value == pytest.approx(sps.mannwhitneyu(*samples.values(), method="asymptotic", use_continuity=False).pvalue)
    assert len({exact.p_value, asymptotic.p_value, no_correction.p_value}) == 3


def test_a_convention_value_the_service_does_not_implement_is_refused(draft):
    plan = activate(draft)
    forged_conventions = plan.conventions.model_copy(update={"mann_whitney": plan.conventions.mann_whitney.model_copy(update={"method": "permutation"})})
    with pytest.raises(StatisticsRefusal, match="mann_whitney"):
        run(per_instance_items(SEPARATED), plan.model_copy(update={"conventions": forged_conventions}))
    forged_conventions = plan.conventions.model_copy(update={"alternative": "greater"})
    with pytest.raises(StatisticsRefusal, match="alternative"):
        run(per_instance_items(SEPARATED), plan.model_copy(update={"conventions": forged_conventions}))


def test_significance_is_p_less_than_or_equal_to_alpha_everywhere():
    assert is_significant(0.05, 0.05) is True and is_significant(0.0500001, 0.05) is False and is_significant(0.01, 0.05) is True
    # Holm on [0.025, 0.05]: adjusted 0.05 and 0.05 (hand: 0.025 * 2, then max(0.05, 0.05 * 1)); both are significant at alpha = 0.05
    assert holm_adjust([0.025, 0.05], 0.05) == [(pytest.approx(0.05), True), (pytest.approx(0.05), True)]
    assert holm_adjust([0.05, 0.025], 0.05) == [(pytest.approx(0.05), True), (pytest.approx(0.05), True)]  # input order is kept
    assert [d for _, d in holm_adjust([0.026, 0.05], 0.05)] == [False, False]
    assert holm_adjust([], 0.05) == []


def test_the_omnibus_gate_uses_the_same_comparison(draft):
    """A plan alpha equal to the omnibus p opens the post-hoc tests (p <= alpha)."""
    items = per_instance_items(INTERLEAVED)
    p = run(items, activate(draft)).inference.omnibus.p_value
    at = run(items, activate(draft, alpha=p))
    assert at.inference.omnibus.significant is True and at.inference.post_hoc_ran is True


def test_identical_values_make_the_omnibus_undefined_not_an_error(active):
    samples = {name: [2.0] * 5 for name in SEPARATED}
    result = run(per_instance_items(samples), active)
    omnibus = result.inference.omnibus
    assert omnibus.status == "undefined_all_values_identical"
    assert omnibus.p_value is None and omnibus.statistic is None and omnibus.significant is False
    assert result.inference.post_hoc_ran is False


# ---------------------------------------------------------------- across instances (matched units)
def test_iman_davenport_f_follows_demsar_2006():
    """Demsar (2006), section 3.2.2: F_F = (b - 1) chi2_F / (b (k - 1) - chi2_F), F distributed with k - 1 and (k - 1)(b - 1) degrees
    of freedom. His example has b = 14 data sets, k = 4 algorithms and chi2_F = 9.28, which gives F_F = 13 * 9.28 / (42 - 9.28) =
    3.687 (printed as 3.69) with (3, 39) degrees of freedom, whose 5 % critical value is 2.85."""
    f, df1, df2 = iman_davenport_f(9.28, 14, 4)
    assert (df1, df2) == (3, 39)
    assert f == pytest.approx(13 * 9.28 / (42 - 9.28), abs=1e-12) and round(f, 2) == 3.69
    assert sps.f.ppf(0.95, 3, 39) == pytest.approx(2.85, abs=0.005)
    assert f > sps.f.ppf(0.95, 3, 39)  # Demsar rejects the null hypothesis at 5 %
    assert iman_davenport_f(42.0, 14, 4)[0] == math.inf  # chi2_F at its maximum b (k - 1) (perfect agreement): F is infinite


def swapped_cross_items(**kw):
    """Five instances order the algorithms A < B < C; on the sixth (eil76) A and B swap. Rank sums: A 5*1 + 2 = 7, B 5*2 + 1 = 11,
    C 18."""
    centres = {("eil76", "Core-GA-TSP"): 6.0, ("eil76", "Core-PSO-TSP"): 5.0}
    return cross_items(centres=centres, **kw)


def test_across_instance_family_reproduces_the_hand_computed_values(active):
    """b = 6, k = 3, rank sums 7, 11, 18 (see ``swapped_cross_items``), mean 12: chi2_F = 12/(6*3*4) * (49 + 121 + 324) - 3*6*4 =
    31/3 (hand); W = 12 S / (b^2 k (k^2 - 1)) = 12 * 62 / 864 = 0.861111 (S = 25 + 1 + 36); Iman-Davenport F = 5 * (31/3) /
    (12 - 31/3) = 31 with (2, 10) degrees of freedom; for 2 numerator degrees of freedom the F survival function is closed form,
    (1 + 2 F / d2)^(-d2 / 2) = 7.2^-5; the chi-square p (2 df) is exp(-chi2_F / 2)."""
    result = run(swapped_cross_items(), active, ACROSS)
    omnibus = result.inference.omnibus
    assert omnibus.test == "friedman" and omnibus.status == "computed"
    assert omnibus.statistic_name == "iman_davenport_f" and omnibus.statistic == pytest.approx(31.0, abs=1e-9)
    assert omnibus.p_value == pytest.approx(7.2 ** -5, rel=1e-9) and omnibus.p_value_method == "iman_davenport_f"
    assert omnibus.chi_square_statistic == pytest.approx(31 / 3, abs=1e-9)
    assert omnibus.chi_square_p_value == pytest.approx(math.exp(-31 / 6), rel=1e-9)
    assert omnibus.effect_size_name == "kendalls_w" and omnibus.effect_size == pytest.approx(0.861111111, abs=1e-8)
    assert omnibus.significant is True and result.inference.post_hoc_ran is True and len(result.inference.pairs) == 3
    units = {a: [result.inference.matched_units[(d, a)] for d in sorted({d for d, _ in result.inference.matched_units})] for a in ALGORITHMS}
    by_pair = {(p.algorithm_a, p.algorithm_b): p for p in result.inference.pairs}
    direct = {}
    for (a, b), pair in by_pair.items():
        direct[(a, b)] = sps.wilcoxon(units[a], units[b], zero_method="pratt", correction=False, method="auto").pvalue
        assert pair.p_value == pytest.approx(direct[(a, b)], abs=1e-12)
        assert pair.method_used == "permutation"  # |differences| tie (all equal 1 or 2 apart from one unit): scipy auto
        assert pair.n_a == pair.n_b == 6 and pair.test == "wilcoxon_signed_rank"
    holm = multipletests([direct[k] for k in sorted(direct)], alpha=0.05, method="holm")[1]
    assert [by_pair[k].p_holm for k in sorted(by_pair)] == pytest.approx(list(holm), abs=1e-12)
    # A against B: differences -1 on five units and +1 on one: |d| ranks all 3.5, T+ = 3.5, T- = 17.5, r = -14/21
    assert by_pair[("Core-GA-TSP", "Core-PSO-TSP")].effect_size == pytest.approx(-14 / 21, abs=1e-12)


def test_perfect_agreement_gives_an_infinite_f_and_zero_p_and_the_exact_wilcoxon_label(active):
    """Perfect agreement (W = 1): chi2_F = b (k - 1) = 12 (p exp(-6)), the Iman-Davenport denominator is 0, F is infinite and its
    p-value is exactly 0 (the limit). With pairwise differences that are all distinct and non-zero scipy's Wilcoxon is exact:
    every pair differs in the same direction on all six units, p = 2 / 2^6 = 1/32, Holm over three pairs 3/32 = 0.09375."""
    centres = {(p, a): float(i) + (0, 1 + 0.1 * i, 2 + 0.25 * i * i)[n] for i, p in enumerate(CROSS_INSTANCES) for n, a in enumerate(ALGORITHMS)}
    result = run(cross_items(centres=centres), active, ACROSS)
    omnibus = result.inference.omnibus
    assert omnibus.statistic == math.inf and omnibus.p_value == 0.0 and omnibus.significant is True
    assert omnibus.chi_square_statistic == pytest.approx(12.0, abs=1e-12) and omnibus.chi_square_p_value == pytest.approx(math.exp(-6.0), rel=1e-12)
    assert omnibus.effect_size == pytest.approx(1.0, abs=1e-12)
    for pair in result.inference.pairs:
        assert pair.method_used == "exact"
        assert pair.p_value == pytest.approx(1 / 32, abs=1e-12) and pair.p_holm == pytest.approx(3 / 32, abs=1e-12)
        assert pair.significant is False and abs(pair.effect_size) == pytest.approx(1.0)  # low power, stated not hidden


def test_wilcoxon_auto_method_labels_follow_scipy():
    """scipy ``wilcoxon(method="auto")``: exact without zero differences and tied |d|; a deterministic permutation test for at most 13
    units with ties or zeros; asymptotic above that. Each label is checked against the explicit method's p-value."""
    from academic_benchmark.analysis.statistics import wilcoxon_method_used
    x14 = [float(v) for v in range(14)]
    y14 = [v + 1.0 for v in x14]  # 14 units, all |d| equal: ties, more than 13 units
    assert wilcoxon_method_used(x14, y14, "auto") == "asymptotic"
    assert sps.wilcoxon(x14, y14, zero_method="pratt", method="auto").pvalue == pytest.approx(
        sps.wilcoxon(x14, y14, zero_method="pratt", method="asymptotic").pvalue, abs=1e-15)
    x6, y6 = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0], [1.5, 2.0, 3.2, 4.9, 5.1, 6.0]  # zeros present
    assert wilcoxon_method_used(x6, y6, "auto") == "permutation"
    assert sps.wilcoxon(x6, y6, zero_method="pratt", method="auto").pvalue == pytest.approx(
        sps.wilcoxon(x6, y6, zero_method="pratt", method=sps.PermutationMethod()).pvalue, abs=1e-15)
    x5, y5 = [1.0, 2.0, 3.0, 4.0, 5.0], [1.5, 3.0, 3.2, 8.0, 5.9]
    assert wilcoxon_method_used(x5, y5, "auto") == "exact"
    assert sps.wilcoxon(x5, y5, zero_method="pratt", method="auto").pvalue == pytest.approx(
        sps.wilcoxon(x5, y5, zero_method="pratt", method="exact").pvalue, abs=1e-15)
    assert wilcoxon_method_used(x5, y5, "asymptotic") == "asymptotic"


def test_an_all_zero_wilcoxon_pair_is_reported_with_p_one_and_stays_in_the_holm_family(active):
    centres = {(p, a): float(i) + (0, 0, 2)[n] for i, p in enumerate(CROSS_INSTANCES) for n, a in enumerate(ALGORITHMS)}
    result = run(cross_items(centres=centres), active, ACROSS)
    by_pair = {(p.algorithm_a, p.algorithm_b): p for p in result.inference.pairs}
    equal = by_pair[("Core-GA-TSP", "Core-PSO-TSP")]
    assert equal.status == "all_differences_zero" and equal.p_value == 1.0 and equal.p_holm == 1.0
    assert equal.effect_size is None and equal.significant is False
    others = [p for k, p in by_pair.items() if k != ("Core-GA-TSP", "Core-PSO-TSP")]
    assert all(p.status == "computed" for p in others)
    # Holm over all three pairs (the all-zero pair keeps its place): sorted p = [1/32, 1/32, 1]: 3/32, max(3/32, 2/32), 1
    assert [p.p_holm for p in others] == pytest.approx([3 / 32, 3 / 32], abs=1e-12)


def test_the_matched_unit_is_the_median_not_the_mean_of_the_replicates(active):
    """One skewed cell: Core-GA-TSP on eil51 has replicate gaps 1, 1, 10 (median 1, mean 4). The unit must be 1; with the mean 4 it
    would exceed Core-PSO-TSP's 2 and change the Friedman and Wilcoxon inputs."""
    skew = {("eil51", "Core-GA-TSP"): (0.0, 0.0, 9.0)}
    plain = run(cross_items(), active, ACROSS).inference
    skewed = run(cross_items(skew=skew), active, ACROSS).inference
    assert skewed.matched_units[("eil51", "Core-GA-TSP")] == pytest.approx(1.0, abs=1e-12)  # centre 1, replicates 1, 1, 10
    assert skewed.matched_units == pytest.approx(plain.matched_units)
    assert skewed.omnibus.chi_square_statistic == pytest.approx(plain.omnibus.chi_square_statistic)
    assert [v for p in skewed.pairs for v in (p.p_value, p.effect_size)] == pytest.approx([v for p in plain.pairs for v in (p.p_value, p.effect_size)])
    cell = [c for c in run(cross_items(skew=skew), active, ACROSS).cells if (c.dataset_identity, c.algorithm_id) == ("eil51", "Core-GA-TSP")][0]
    assert cell.summary["mean"] == pytest.approx(4.0) and cell.summary["median"] == pytest.approx(1.0)  # the descriptive columns differ


def test_across_instances_refuses_a_declared_instance_with_no_rows(active):
    """5 of 6 declared instances: Friedman and Wilcoxon would still compute (p = 0.006738); the plan declares six, so it is refused."""
    with pytest.raises(StatisticsRefusal, match="eil76"):
        run(cross_items(problems=CROSS_INSTANCES[:5]), active, ACROSS)
    with pytest.raises(StatisticsRefusal, match="st70"):
        run(cross_items(problems=CROSS_INSTANCES[:2]), active, ACROSS)
    # a descriptive (smoke) view of a partial design is still offered, with the absent instance listed
    smoke = run(cross_items(problems=CROSS_INSTANCES[:5]), active, ACROSS, mode="smoke")
    assert smoke.inference is None and any(e["dataset_identity"] == "eil76" and e["algorithm_id"] is None for e in smoke.exclusions)


def test_the_power_limit_is_declared_in_the_plan_and_stated_when_it_applies(active):
    assert smallest_possible_adjusted_p(6, 3) == pytest.approx(3 / 32, abs=1e-15)
    assert smallest_possible_adjusted_p(4, 3) == pytest.approx(3 / 8, abs=1e-15)
    assert smallest_possible_adjusted_p(4, 1) == pytest.approx(0.125, abs=1e-15)
    assert smallest_possible_adjusted_p(10, 3) == pytest.approx(3 / 512, abs=1e-15)
    text = run(cross_items(), active, ACROSS).text
    assert active.power_declaration.statement in text
    assert "0.09375" in text and "cannot reach" in text
    assert "cannot reach" not in run(per_instance_items(SEPARATED), active).text
    assert_no_ranking_words(text)


def test_the_effect_size_directions_are_stated_neutrally(active):
    a12 = "A12 is P(gap of algorithm a > gap of algorithm b) + 0.5 P(equal)"
    biserial = "the matched-pairs rank-biserial r is positive when algorithm a has larger gaps than algorithm b"
    for family, items, present, absent in ((PER_INSTANCE, per_instance_items(SEPARATED), a12, biserial), (ACROSS, cross_items(), biserial, a12)):
        text = run(items, active, family).text
        assert "Effect-size direction" in text and present in text and absent not in text
        assert_no_ranking_words(text)


def test_across_instance_pair_directions_follow_the_units(active):
    result = run(cross_items(), active, ACROSS)
    pair = [p for p in result.inference.pairs if (p.algorithm_a, p.algorithm_b) == ("Core-GA-TSP", "Core-PSO-TSP")][0]
    assert pair.effect_size == pytest.approx(-1.0)  # the first algorithm's gap is smaller on every instance


def test_across_instance_matched_unit_is_the_median_over_replicates_and_replicate_seeds_are_not_pairing(active):
    items = cross_items()
    one = [item for item in items if item[0]["problem"] == "eil51" and item[0]["algorithm_id"] == "Core-GA-TSP"]
    assert sorted(item[0]["replicate"] for item in one) == [0, 1, 2]
    result = run(items, active, ACROSS)
    assert result.inference.matched_units[("eil51", "Core-GA-TSP")] == pytest.approx(1.0)


def test_across_instances_refuses_a_false_pairing_one_instance_missing_an_algorithm(active):
    items = [item for item in cross_items() if not (item[0]["problem"] == "st70" and item[0]["algorithm_id"] == "Core-PSO-TSP")]
    with pytest.raises(StatisticsRefusal, match="unit"):
        run(items, active, ACROSS)


def test_across_instances_refuses_a_failed_cell_and_names_the_exclusion(active):
    items = [item for item in cross_items() if not (item[0]["problem"] == "st70" and item[0]["algorithm_id"] == "Core-PSO-TSP" and item[0]["replicate"] == 2)]
    items.append(failed_item("st70", "Core-PSO-TSP", 2))
    with pytest.raises(StatisticsRefusal, match="excluded"):
        run(items, active, ACROSS)


def test_across_instances_refuses_an_instance_outside_the_declared_family(active):
    items = cross_items(problems=CROSS_INSTANCES[:5] + ["ft53"])
    with pytest.raises(StatisticsRefusal, match="family"):
        run(items, active, ACROSS)


def test_across_instances_needs_at_least_two_instances(active):
    result = run(cross_items(problems=["eil51"]), active, ACROSS)
    assert result.inference is None
    assert any("insufficient" in reason and "instance" in reason for reason in result.inference_refused)


# ---------------------------------------------------------------- guards
def test_both_real_plans_are_draft_and_inference_is_refused_with_descriptive_output(draft_plans):
    for study, plan in draft_plans.items():
        assert plan.status == "draft" and plan.minimum_n_per_cell is None
        result = run(per_instance_items(SEPARATED), plan)
        assert result.inference is None
        assert any("draft" in reason for reason in result.inference_refused)
        assert any("minimum_n_per_cell" in reason for reason in result.inference_refused)
        assert {c.algorithm_id for c in result.cells} == set(SEPARATED)
        assert all(set(c.summary) == set(plan.descriptive.columns) for c in result.cells)
        assert "p-value" not in result.text and "descriptive" in result.text




def test_the_campaign_mode_comes_from_the_verified_run_index(active):
    items = per_instance_items(SEPARATED)
    smoke = run(items, active, mode="smoke")  # the index of a smoke campaign
    assert smoke.campaign_mode == "smoke" and smoke.inference is None and any("smoke" in r for r in smoke.inference_refused)
    assert len(smoke.cells) == 3
    assert run(items, active, mode="paper").campaign_mode == "paper"
    # a caller can no longer name the mode: a bare string is not an index, and the old keyword does not exist
    with pytest.raises(StatisticsRefusal, match="RunIndexV1"):
        analyse_family(items, study=STUDY3, plan=active, family_id=PER_INSTANCE, run_index="paper")
    with pytest.raises(TypeError):
        analyse_family(items, study=STUDY3, plan=active, family_id=PER_INSTANCE, campaign_mode="paper")


def test_manifests_that_the_index_does_not_list_are_refused(active):
    items = per_instance_items(SEPARATED)
    unlisted = items[0][1].run_id
    with pytest.raises(StatisticsRefusal, match="not listed in the run index"):
        analyse_family(items, study=STUDY3, plan=active, family_id=PER_INSTANCE, run_index=index_for(items, drop=(unlisted,)))
    with pytest.raises(StatisticsRefusal, match="comparison key digest"):
        analyse_family(items, study=STUDY3, plan=active, family_id=PER_INSTANCE, run_index=index_for(items, digest_of="wrong"))
    with pytest.raises(StatisticsRefusal, match="study"):
        analyse_family(items, study=STUDY3, plan=active, family_id=PER_INSTANCE, run_index=index_for(items, study_id="yaem2026"))
    with pytest.raises(StatisticsRefusal, match="dirty"):
        analyse_family(items, study=STUDY3, plan=active, family_id=PER_INSTANCE, run_index=index_for(items, dirty=True))
    other_commit = [(row, manifest.model_copy(update={"git": manifest.git.model_copy(update={"commit": "c" * 40})})) for row, manifest in items]
    with pytest.raises(StatisticsRefusal, match="commit"):
        analyse_family(other_commit, study=STUDY3, plan=active, family_id=PER_INSTANCE, run_index=index_for(items))


def test_a_sample_below_the_plan_minimum_gives_insufficient_sample_and_no_p_value(draft):
    plan = activate(draft, minimum_n=6)
    result = run(per_instance_items(SEPARATED), plan)  # n = 5 per cell
    assert result.inference is None
    assert any("insufficient sample" in reason for reason in result.inference_refused)
    assert "insufficient sample" in result.text and "p_value" not in result.text


def test_the_environment_guard_runs_first(monkeypatch, active):
    def refuse():
        raise analysis_environment.AnalysisEnvironmentError("fixture: environment is not the pinned one")
    monkeypatch.setattr(stats_service, "require_analysis_environment", refuse)
    with pytest.raises(analysis_environment.AnalysisEnvironmentError):
        run(per_instance_items(SEPARATED), active)
    with pytest.raises(analysis_environment.AnalysisEnvironmentError):
        run([], active)


def test_a_dirty_tree_is_refused_and_allow_dirty_is_never_passed(monkeypatch, active):
    items = per_instance_items(SEPARATED)
    dirty = [make_item("eil51", "Core-GA-TSP", 5, 6.0, dirty=True)]
    with pytest.raises(StatisticsRefusal, match="dirty"):
        run(items + dirty, active)
    tree = ast.parse(Path(stats_service.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "allow_dirty":
            assert isinstance(node.value, ast.Constant) and node.value.value is False

    class Family:
        contains_dirty = True
        pooling_group = "fixed_budget"
        shared, varied, size = {}, {}, 1
    monkeypatch.setattr(stats_service, "assert_single_comparison_family", lambda *a, **k: Family())
    with pytest.raises(StatisticsRefusal, match="dirty"):
        run(items, active)


def test_historical_unverified_rows_are_refused(active):
    items = per_instance_items(SEPARATED)
    items[0] = make_item("eil51", "Core-GA-TSP", 0, 1.0, evidence="historical_unverified")
    with pytest.raises(StatisticsRefusal, match="historical"):
        run(items, active)


def test_exact_union_and_joint_rows_are_refused(active):
    for protocol in ("exact_reference_v1", "union_day_v1", "exact_day_joint_v1"):
        items = per_instance_items(SEPARATED) + [({"protocol": protocol, "problem": "eil51", "algorithm_id": "x"}, None)]
        with pytest.raises(StatisticsRefusal, match="never ranked|pooling group|references"):
            run(items, active)


def test_fixed_and_native_rows_never_meet(active):
    native = ({"protocol_version": "uniride-native-tsp-v1", "comparison_regime": "algorithm_native_termination", "problem": "eil51",
               "algorithm_id": "Core-GA-TSP", "replicate": 9}, None)
    with pytest.raises(StatisticsRefusal, match="pooling"):
        run(per_instance_items(SEPARATED) + [native], active)


def test_mixed_comparison_cells_are_refused(active):
    items = per_instance_items(SEPARATED)
    items.append(make_item("eil76", "Core-GA-TSP", 9, 3.0))  # a second instance inside a per-instance family
    with pytest.raises(StatisticsRefusal, match="dataset"):
        run(items, active)
    other_level = per_instance_items(SEPARATED)
    row, manifest = other_level[0]
    other_level[0] = ({**row, "evaluation_budget": _levels("eil51")[1]}, manifest)
    with pytest.raises(StatisticsRefusal, match="budget_level_index"):
        run(other_level, active)


def test_unequal_replicate_sets_are_refused_per_instance(active):
    items = per_instance_items(SEPARATED)
    items = [item for item in items if not (item[0]["algorithm_id"] == "Core-PSO-TSP" and item[0]["replicate"] == 4)]
    with pytest.raises(StatisticsRefusal, match="replicate"):
        run(items, active)
    duplicate = per_instance_items(SEPARATED) + [make_item("eil51", "Core-GA-TSP", 0, 9.0)]
    with pytest.raises(StatisticsRefusal, match="replicate"):
        run(duplicate, active)


def test_a_failed_run_excludes_its_cell_from_inference_and_is_reported(active):
    items = per_instance_items(SEPARATED)
    items = [item for item in items if not (item[0]["algorithm_id"] == "Core-PSO-TSP" and item[0]["replicate"] == 4)]
    items.append(failed_item("eil51", "Core-PSO-TSP", 4))
    result = run(items, active)
    assert [(e["algorithm_id"], e["dataset_identity"], e["failed_runs"]) for e in result.exclusions] == [("Core-PSO-TSP", "eil51", 1)]
    assert {c.algorithm_id for c in result.cells} == {"Core-GA-TSP", "Core-GWO-TSP-Pure"}
    assert {(p.algorithm_a, p.algorithm_b) for p in result.inference.pairs} == {("Core-GA-TSP", "Core-GWO-TSP-Pure")}
    assert "excluded" in result.text and "Core-PSO-TSP" in result.text


def test_a_failed_row_must_belong_to_the_family(active):
    good = per_instance_items(SEPARATED)
    cases = {
        "algorithm": failed_item("eil51", "Core-ALIEN-TSP", 0),
        "study_id": failed_item("eil51", "Core-PSO-TSP", 0, study_id="yaem2026"),
        "protocol_version": failed_item("eil51", "Core-PSO-TSP", 0, protocol_version="uniride-fair-tsp-v1"),
    }
    for field, item in cases.items():
        with pytest.raises(StatisticsRefusal, match=field):
            run(good + [item], active, study=STUDY3)
    row, _ = failed_item("eil51", "Core-PSO-TSP", 0)
    del row["study_id"]
    with pytest.raises(StatisticsRefusal, match="study_id"):
        run(good + [(row, None)], active, study=STUDY3)


def test_the_expected_algorithm_set_comes_from_the_study_profile(active):
    """Lead decision (OQ-9 a): the algorithms of a family are the profile's algorithm IDs, not the ones that happen to have rows. A failed
    row of a profile algorithm is excluded and reported even when the index lists no run of it; an algorithm outside the profile is
    refused, as is an index run of such an algorithm."""
    good = per_instance_items({name: SEPARATED[name] for name in ("Core-GA-TSP", "Core-GWO-TSP-Pure")})
    failed = [failed_item("eil51", "Core-PSO-TSP", r) for r in range(5)]
    result = run(good + failed, active, study=STUDY3)  # PSO is in the profile; the index lists none of its runs
    assert result.inference is not None and [e["algorithm_id"] for e in result.exclusions] == ["Core-PSO-TSP"]
    with pytest.raises(StatisticsRefusal, match="profile"):
        run(good + [failed_item("eil51", "Core-ALIEN-TSP", 0)], active, study=STUDY3)
    alien_run = [make_item("eil76", "Core-ALIEN-TSP", r, 1.0) for r in range(3)]
    with pytest.raises(StatisticsRefusal, match="run index"):
        run(good + failed, active, study=STUDY3, extra_items=alien_run)


def test_an_expected_algorithm_without_completed_or_failed_rows_refuses_the_per_instance_analysis(active):
    """The profile names three algorithms; the input has rows for two. Kruskal-Wallis over two groups would silently answer a different
    question, so it is refused (the plan has no way to declare that an algorithm does not apply to an instance)."""
    two = per_instance_items({name: SEPARATED[name] for name in ("Core-GA-TSP", "Core-GWO-TSP-Pure")})
    with pytest.raises(StatisticsRefusal, match="Core-PSO-TSP"):
        run(two, active, study=STUDY3)
    with pytest.raises(StatisticsRefusal, match="no mechanism"):
        run(two, active, study=STUDY3)
    # a descriptive (smoke) view is still offered, with the missing algorithm listed
    smoke = run(two, active, mode="smoke", study=STUDY3)
    assert smoke.inference is None and any(e["algorithm_id"] == "Core-PSO-TSP" and e["dataset_identity"] is None for e in smoke.exclusions)
    # the real profile lists ten algorithms: three of them are not a family
    with pytest.raises(StatisticsRefusal, match="Core-TwoOpt-TSP"):
        run(per_instance_items(SEPARATED), active, study=_BILDIRI)


def test_an_expected_algorithm_without_rows_on_any_instance_refuses_the_cross_instance_analysis(active):
    four = STUDY3.model_copy(update={"algorithm_ids": [*STUDY3.algorithm_ids, "Core-HHO-TSP-Pure"]})
    with pytest.raises(StatisticsRefusal, match="Core-HHO-TSP-Pure"):
        run(cross_items(), active, ACROSS, study=four)  # the profile says four algorithms, the rows hold three
    # with a failed row on every instance the algorithm has rows; the cross-instance design still refuses the failed cells
    failed = [failed_item(problem, "Core-HHO-TSP-Pure", 0) for problem in CROSS_INSTANCES]
    with pytest.raises(StatisticsRefusal, match="excluded after a failed run"):
        run(cross_items() + failed, active, ACROSS, study=four)
    assert run(cross_items(), active, ACROSS).inference is not None  # the matching three-algorithm profile is fine


def test_a_fully_failed_per_instance_cell_is_excluded_reported_and_the_rest_is_analysed(active):
    """Two algorithms complete, the third failed on every replicate: its cell is excluded, the Holm family is the single remaining pair
    (adjusted p equals p), and the report lists the pairs that dropped out and why."""
    good = per_instance_items({name: SEPARATED[name] for name in ("Core-GA-TSP", "Core-GWO-TSP-Pure")})
    failed = [failed_item("eil51", "Core-PSO-TSP", r) for r in range(5)]

    result = run(good + failed, active)
    assert [(e["algorithm_id"], e["dataset_identity"], e["failed_runs"]) for e in result.exclusions] == [("Core-PSO-TSP", "eil51", 5)]
    assert {c.algorithm_id for c in result.cells} == {"Core-GA-TSP", "Core-GWO-TSP-Pure"}
    assert result.inference_refused == ()
    (pair,) = result.inference.pairs
    assert (pair.algorithm_a, pair.algorithm_b) == ("Core-GA-TSP", "Core-GWO-TSP-Pure")
    assert pair.p_holm == pytest.approx(pair.p_value, abs=1e-15)  # Holm over one pair
    assert [(p["algorithm_a"], p["algorithm_b"]) for p in result.excluded_pairs] == [("Core-GA-TSP", "Core-PSO-TSP"), ("Core-GWO-TSP-Pure", "Core-PSO-TSP")]
    assert all("Core-PSO-TSP" in p["reason"] and "failed" in p["reason"] for p in result.excluded_pairs)
    assert "pair excluded from the Holm family: Core-GA-TSP vs Core-PSO-TSP" in result.text
    assert_no_ranking_words(result.text)
    # nothing is excluded when nothing failed
    assert run(per_instance_items(SEPARATED), active).excluded_pairs == ()


def test_a_fully_failed_cross_instance_cell_still_refuses_the_analysis(active):
    items = [item for item in cross_items() if not (item[0]["problem"] == "st70" and item[0]["algorithm_id"] == "Core-PSO-TSP")]
    items += [failed_item("st70", "Core-PSO-TSP", r) for r in range(3)]
    with pytest.raises(StatisticsRefusal, match="excluded after a failed run"):
        run(items, active, ACROSS)


def test_rows_without_a_usable_gap_are_refused(active):
    items = per_instance_items(SEPARATED)
    row, manifest = items[0]
    broken = {key: value for key, value in row.items() if key != "gap_to_exact_reference"}
    with pytest.raises(StatisticsRefusal, match="gap_to_exact_reference"):
        run([(broken, manifest)] + items[1:], active)
    with pytest.raises(StatisticsRefusal, match="gap"):
        run([({**row, "gap_to_exact_reference": None, "gap_missing_reason": "no proven exact reference"}, manifest)] + items[1:], active)
    with pytest.raises(StatisticsRefusal, match="unit"):
        run([({**row, "gap_unit": "fraction"}, manifest)] + items[1:], active)
    with pytest.raises(StatisticsRefusal, match="gap"):
        run([({**row, "gap_to_exact_reference": float("nan")}, manifest)] + items[1:], active)


def test_a_plan_value_the_service_does_not_implement_is_refused(draft):
    def swap(data):
        data["families"][0]["post_hoc"]["rule"] = "something_new"
    with pytest.raises(Exception):  # the contract itself refuses the value
        activate(draft, mutate=swap)
    plan = activate(draft)
    forged = plan.model_copy(update={"descriptive": plan.descriptive.model_copy(update={"quantile_method": "hyndman_fan_type_6"})})
    with pytest.raises(StatisticsRefusal, match="quantile_method"):
        run(per_instance_items(SEPARATED), forged)
    odd_post_hoc = plan.families[0].post_hoc.model_copy(update={"correction": "bonferroni"})
    odd_family = plan.families[0].model_copy(update={"post_hoc": odd_post_hoc})
    forged = plan.model_copy(update={"families": [odd_family, plan.families[1]]})
    with pytest.raises(StatisticsRefusal, match="correction"):
        run(per_instance_items(SEPARATED), forged)


def test_unknown_family_and_wrong_plan_type_are_refused(active):
    with pytest.raises(StatisticsRefusal, match="family"):
        run(per_instance_items(SEPARATED), active, "no-such-family")
    with pytest.raises(StatisticsRefusal, match="AnalysisPlanV1"):
        run(per_instance_items(SEPARATED), {"alpha": 0.05})


def test_atsp_instance_is_analysed_per_instance_and_never_in_the_cross_instance_family(active):
    # ft53 is in the per-instance family (problem types TSP and ATSP) but not in the across-instance one (OQ-8 a)
    result = run(per_instance_items(SEPARATED, problem="ft53"), active)
    assert result.inference is not None
    with pytest.raises(StatisticsRefusal, match="family"):
        run(cross_items(problems=["ft53", "eil51", "st70", "kroA100", "rd100", "eil76"]), active, ACROSS)


def test_report_text_uses_descriptive_wording_only(active, draft):
    for plan, mode in ((active, "paper"), (active, "smoke"), (draft, "paper")):
        for family, items in ((PER_INSTANCE, per_instance_items(SEPARATED)), (ACROSS, cross_items())):
            text = run(items, plan, family, mode=mode).text
            assert text.strip()
            assert_no_ranking_words(text)
    text = run(per_instance_items(SEPARATED), active).text
    assert "scipy==1.18.1" in text and "kruskal_wallis" in text and "holm" in text


def test_the_service_calls_the_identity_guards_in_order():
    tree = ast.parse(Path(stats_service.__file__).read_text(encoding="utf-8"))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "analyse_family")
    calls = sorted((n.lineno, n.col_offset, n.func.id) for n in ast.walk(func) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name))
    order = [name for _, _, name in calls if name in ("require_analysis_environment", "assert_rankable", "assert_single_comparison_family")]
    assert order[:3] == ["require_analysis_environment", "assert_rankable", "assert_single_comparison_family"]
