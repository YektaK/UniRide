"""Guarded statistics service (Gate D, D-05; plan 2026-10-23 section 3; DECISION_LOG A18 OQ-5, OQ-6, OQ-7, OQ-8, OQ-9, OQ-15).

``analyse_family`` carries out the predeclared analysis of one comparison family of a study's analysis plan (D-09) over
rows that carry the D-06 column ``gap_to_exact_reference`` (percent) and a run manifest (D-01/D-02):

* per instance (``per_instance`` scope, independent samples): omnibus Kruskal-Wallis with epsilon-squared, then pairwise
  Mann-Whitney U with Vargha-Delaney A12 and Holm over the pairs of that instance, under the plan's post-hoc rule;
* across instances (``across_instances`` scope, matched units = the per-instance median over replicates): omnibus Friedman
  with Kendall's W, then pairwise Wilcoxon signed-rank with the matched-pairs rank-biserial correlation and Holm.

Everything the plan declares is read from the plan (alpha, tests, post-hoc rule, correction, effect sizes, SD convention,
quantile method, minimum n, failure policy, response); a plan value this module does not implement is refused, never
replaced. The numerical conventions that the plan does not fix (alternative, exact or asymptotic p-values, continuity
correction, zero differences in the Wilcoxon test) are a required ``NumericalPolicy`` argument without a default, are echoed
in every result and are listed as an open owner question (A18 has no answer for them).

Guards, in this order: ``require_analysis_environment`` (pinned SciPy and statsmodels), ``assert_rankable`` (exact, union-day
and joint-day rows are references or selections, never data; one pooling group), then
``identity.assert_single_comparison_family`` without ``allow_dirty`` (one comparison cell family, clean tree, verified
manifest per row). ``historical_unverified`` rows are refused. A smoke campaign, a non-active plan, an unresolved
``minimum_n_per_cell`` or a cell below it give descriptive output and a named reason, never a p-value. Failed runs are not
observations: their (algorithm, instance) cell is excluded from inference and reported (OQ-9); a matched design that would
need an excluded or missing cell is refused (no silent choice of what to drop). Equal numeric seeds are never read as pairing
evidence: the matched unit is the instance, and every algorithm must have a unit on every instance.

Epsilon-squared, Kendall's W, the matched-pairs rank-biserial correlation and A12 are local code (SciPy and statsmodels do not
provide them); they are tested against published or hand-computed examples in ``test_analysis_statistics.py``. Holm comes from
statsmodels ``multipletests``; the omnibus and pairwise tests from SciPy. Output text is descriptive only (no ranking wording).
"""
from __future__ import annotations

import itertools
import re
import math
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Sequence

from academic_benchmark.analysis.environment import require_analysis_environment, statistics_library_identifier
from academic_benchmark.analysis.identity import ComparisonIdentityError, assert_single_comparison_family, comparison_cell_key
from academic_benchmark.analysis.manifests import make_run_id
from academic_benchmark.contracts.analysis_plan import AnalysisPlanV1, ComparisonFamilyV1, DescriptiveV1
from academic_benchmark.contracts.run_index import RunIndexV1
from academic_benchmark.contracts.study import StudyManifestV1
from academic_benchmark.fairness import normalize_problem
from academic_benchmark.protocol_registry import assert_rankable

GAP_COLUMN = "gap_to_exact_reference"  # D-06 (analysis/gaps.py); not imported, so this module needs no reference reader
GAP_UNIT_COLUMN = "gap_unit"
GAP_REASON_COLUMN = "gap_missing_reason"
CAMPAIGN_MODES = ("smoke", "paper")
CURRENT_EVIDENCE = (None, "current", "CURRENT")
ZERO_METHODS = ("wilcox", "pratt", "zsplit")
SUPPORTED_RULES = ("only_after_significant_omnibus", "always_over_declared_family")
STATUS_COMPUTED = "computed"
STATUS_UNDEFINED = "undefined_all_values_identical"



class StatisticsRefusal(ValueError):
    """The service refused to analyse the input; the message names the reason."""


# ------------------------------------------------------------------------------------------------ results
@dataclass(frozen=True)
class CellSummary:
    dataset_identity: str
    algorithm_id: str
    n: int
    summary: Mapping[str, Any]


@dataclass(frozen=True)
class Omnibus:
    test: str
    status: str
    statistic: Optional[float]
    statistic_name: str
    p_value: Optional[float]
    p_value_method: str
    effect_size_name: str
    effect_size: Optional[float]
    significant: bool
    n_groups: int
    n_observations: int  # per-instance: replicates in total; across instances: matched units per algorithm
    chi_square_statistic: Optional[float] = None  # Friedman only: reported beside the primary Iman-Davenport F
    chi_square_p_value: Optional[float] = None


@dataclass(frozen=True)
class PairResult:
    algorithm_a: str
    algorithm_b: str
    test: str
    status: str
    statistic: Optional[float]
    p_value: Optional[float]
    p_holm: Optional[float]
    significant: bool
    effect_size_name: str
    effect_size: Optional[float]
    n_a: int
    n_b: int
    method_used: str


@dataclass(frozen=True)
class InferenceResult:
    omnibus: Omnibus
    post_hoc_ran: bool
    post_hoc_reason: str
    pairs: tuple
    correction: str
    alpha: float
    matched_units: Optional[Mapping[tuple, float]] = None


@dataclass(frozen=True)
class FamilyAnalysis:
    family_id: str
    scope: str
    campaign_mode: str
    analysis_plan_id: str
    plan_status: str
    statistics_library: str
    conventions: Mapping[str, Any]
    cells: tuple
    exclusions: tuple
    inference_refused: tuple
    inference: Optional[InferenceResult]
    excluded_pairs: tuple  # per-instance pairs that left the Holm family because a cell was excluded (OQ-9)
    text: str


# ------------------------------------------------------------------------------------------------ small helpers
def _finite_values(values: Iterable[Any], what: str) -> list:
    out = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise StatisticsRefusal(f"{what}: values must be finite numbers, got {value!r}")
        out.append(float(value))
    return out


def _average_ranks(values: Sequence[float]) -> list:
    """Ranks 1..n with the average rank for ties."""
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        average = (i + j) / 2 + 1
        for position in range(i, j + 1):
            ranks[order[position]] = average
        i = j + 1
    return ranks


def _quantile_type7(sorted_values: Sequence[float], p: float) -> float:
    """Hyndman-Fan type 7 (linear interpolation between order statistics; the NumPy and R default)."""
    h = (len(sorted_values) - 1) * p
    low = math.floor(h)
    high = min(low + 1, len(sorted_values) - 1)
    return sorted_values[low] + (h - low) * (sorted_values[high] - sorted_values[low])


# ------------------------------------------------------------------------------------------------ effect sizes (local)
def epsilon_squared(h: float, n: int) -> float:
    """Epsilon-squared of a Kruskal-Wallis test: H / ((n^2 - 1) / (n + 1)) = H / (n - 1) for ``n`` observations in total
    (Tomczak and Tomczak 2014, Trends in Sport Sciences 21(1):19-25). ``h`` is the (tie-corrected) H statistic."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise StatisticsRefusal(f"epsilon-squared needs an integer n >= 2, got {n!r}")
    if isinstance(h, bool) or not isinstance(h, (int, float)) or not math.isfinite(float(h)) or h < 0:
        raise StatisticsRefusal(f"epsilon-squared needs a finite H >= 0, got {h!r}")
    return float(h) / (n - 1)


def kendalls_w(blocks: Sequence[Sequence[float]]) -> Optional[float]:
    """Kendall's coefficient of concordance W for ``m`` blocks (rows) of ``k`` treatments, corrected for ties within a block:
    W = 12 S / (m^2 (k^3 - k) - m sum_j T_j), S the sum of squared deviations of the treatment rank sums from their mean,
    T_j = sum (t^3 - t) over the tie groups of block j (Kendall and Gibbons 1990). Equals chi2_F / (m (k - 1)) with the
    tie-corrected Friedman statistic. ``None`` when every block is constant (undefined, 0/0)."""
    rows = [_finite_values(block, "Kendall's W") for block in blocks]
    m = len(rows)
    if m < 1:
        raise StatisticsRefusal("Kendall's W needs at least one block")
    k = len(rows[0])
    if k < 2 or any(len(row) != k for row in rows):
        raise StatisticsRefusal("Kendall's W needs blocks of the same length k >= 2")
    sums = [0.0] * k
    tie_term = 0.0
    for row in rows:
        ranks = _average_ranks(row)
        for i, rank in enumerate(ranks):
            sums[i] += rank
        counts: dict = {}
        for value in row:
            counts[value] = counts.get(value, 0) + 1
        tie_term += sum(t ** 3 - t for t in counts.values())
    mean = m * (k + 1) / 2
    s = sum((total - mean) ** 2 for total in sums)
    denominator = m * m * (k ** 3 - k) - m * tie_term
    if denominator <= 0:
        return None
    return 12 * s / denominator


def vargha_delaney_a12(x: Sequence[float], y: Sequence[float]) -> float:
    """Vargha-Delaney A12 = P(X > Y) + 0.5 P(X = Y) over all pairs (Vargha and Delaney 2000, J. Educ. Behav. Stat. 25(2)).
    It equals the Mann-Whitney U statistic of ``x`` divided by n1 * n2."""
    xs, ys = _finite_values(x, "A12 sample x"), _finite_values(y, "A12 sample y")
    if not xs or not ys:
        raise StatisticsRefusal("A12 needs two non-empty samples")
    score = sum(1.0 if a > b else 0.5 if a == b else 0.0 for a in xs for b in ys)
    return score / (len(xs) * len(ys))


def matched_pairs_rank_biserial(x: Sequence[float], y: Sequence[float], zero_method: str) -> Optional[float]:
    """Matched-pairs rank-biserial correlation r = (T+ - T-) / (T+ + T-) of the differences x - y (Kerby 2014, simple
    difference formula; positive when ``x`` is larger). Zero differences follow the Wilcoxon ``zero_method``: ``wilcox``
    drops them before ranking, ``pratt`` ranks them and drops their ranks, ``zsplit`` ranks them and splits their rank equally.
    ``None`` when no difference is non-zero (0/0)."""
    if zero_method not in ZERO_METHODS:
        raise StatisticsRefusal(f"zero_method {zero_method!r} is not implemented {ZERO_METHODS}")
    xs, ys = _finite_values(x, "rank-biserial sample x"), _finite_values(y, "rank-biserial sample y")
    if len(xs) != len(ys) or not xs:
        raise StatisticsRefusal("the matched-pairs rank-biserial correlation needs two samples of the same positive length")
    diffs = [a - b for a, b in zip(xs, ys)]
    if all(d == 0 for d in diffs):
        return None
    if zero_method == "wilcox":
        diffs = [d for d in diffs if d != 0]
    ranks = _average_ranks([abs(d) for d in diffs])
    t_plus = sum(r for r, d in zip(ranks, diffs) if d > 0)
    t_minus = sum(r for r, d in zip(ranks, diffs) if d < 0)
    if zero_method == "zsplit":
        half = sum(r for r, d in zip(ranks, diffs) if d == 0) / 2
        t_plus, t_minus = t_plus + half, t_minus + half
    return (t_plus - t_minus) / (t_plus + t_minus)


# ------------------------------------------------------------------------------------------------ descriptive
def _check_descriptive_spec(spec: DescriptiveV1) -> None:
    if spec.quantile_method != "hyndman_fan_type_7":
        raise StatisticsRefusal(f"descriptive quantile_method {spec.quantile_method!r} is not implemented (hyndman_fan_type_7)")
    if spec.sd_convention not in ("sample_n_minus_1", "population_n"):
        raise StatisticsRefusal(f"descriptive sd_convention {spec.sd_convention!r} is not implemented")


def describe_sample(values: Sequence[float], spec: DescriptiveV1) -> dict:
    """The descriptive columns the plan lists (n, median, IQR by type-7 quantiles, min, max, mean and the SD of the plan's
    convention; the sample SD is ``None`` for n = 1). No column that the plan does not list is returned."""
    _check_descriptive_spec(spec)
    data = sorted(_finite_values(values, "descriptive sample"))
    if not data:
        raise StatisticsRefusal("a descriptive summary needs at least one value")
    n = len(data)
    mean = math.fsum(data) / n
    squares = math.fsum((v - mean) ** 2 for v in data)
    if spec.sd_convention == "sample_n_minus_1":
        sd = None if n == 1 else math.sqrt(squares / (n - 1))
    else:
        sd = math.sqrt(squares / n)
    available = {
        "n": n, "median": _quantile_type7(data, 0.5), "iqr": _quantile_type7(data, 0.75) - _quantile_type7(data, 0.25),
        "min": data[0], "max": data[-1], "mean": mean, "sd": sd,
    }
    return {column: available[column] for column in spec.columns}


# ------------------------------------------------------------------------------------------------ input handling
def _plan_family(plan: Any, family_id: str) -> ComparisonFamilyV1:
    if not isinstance(plan, AnalysisPlanV1):
        raise StatisticsRefusal(f"the statistics service is defined by an AnalysisPlanV1, not {type(plan).__name__}")
    matches = [family for family in plan.families if family.family_id == family_id]
    if not matches:
        raise StatisticsRefusal(f"analysis plan {plan.analysis_plan_id!r} declares no family {family_id!r}")
    family = matches[0]
    if (plan.response.variable, plan.response.unit) != ("relative_gap_to_exact_reference", "percent"):
        raise StatisticsRefusal("the plan's response is not the relative gap to the exact reference in percent")
    if (plan.matched_unit.per, plan.matched_unit.summary, plan.matched_unit.over) != ("instance", "median", "replicates"):
        raise StatisticsRefusal("the plan's matched unit is not the per-instance median over replicates")
    if family.post_hoc.correction != "holm":
        raise StatisticsRefusal(f"post-hoc correction {family.post_hoc.correction!r} is not implemented (holm)")
    if family.post_hoc.rule not in SUPPORTED_RULES:
        raise StatisticsRefusal(f"post-hoc rule {family.post_hoc.rule!r} is not implemented {SUPPORTED_RULES}")
    expected = {
        "per_instance": ("kruskal_wallis", "epsilon_squared", "mann_whitney_u", "vargha_delaney_a12"),
        "across_instances": ("friedman", "kendalls_w", "wilcoxon_signed_rank", "matched_pairs_rank_biserial"),
    }.get(family.scope)
    actual = (family.omnibus.test, family.omnibus.effect_size, family.post_hoc.test, family.post_hoc.effect_size)
    if expected != actual:
        raise StatisticsRefusal(f"the {family.scope} family's tests and effect sizes {actual} are not the implemented {expected}")
    if plan.failure_policy.inference != "exclude_cell":
        raise StatisticsRefusal(f"failure policy {plan.failure_policy.inference!r} is not implemented (exclude_cell)")
    if not (0 < plan.alpha < 1):
        raise StatisticsRefusal(f"alpha {plan.alpha!r} must lie in (0, 1)")
    _check_descriptive_spec(plan.descriptive)
    return family


def _is_failed(row: Mapping[str, Any]) -> bool:
    return row.get("record_kind") == "failed_run" or row.get("validation_status") == "failed"


def _gap_of(row: Mapping[str, Any], unit: str) -> float:
    if GAP_COLUMN not in row:
        raise StatisticsRefusal(f"a row has no {GAP_COLUMN} column: rows must come through the gap columns of D-06 (analysis.gaps)")
    gap = row[GAP_COLUMN]
    if gap is None:
        raise StatisticsRefusal(
            f"{row.get('algorithm_id')!r} on {row.get('problem')!r}: no gap to the exact reference "
            f"({row.get(GAP_REASON_COLUMN) or 'no reason given'}); the instance cannot be analysed"
        )
    if row.get(GAP_UNIT_COLUMN) != unit:
        raise StatisticsRefusal(f"a row's gap unit {row.get(GAP_UNIT_COLUMN)!r} differs from the plan's unit {unit!r}")
    if isinstance(gap, bool) or not isinstance(gap, (int, float)) or not math.isfinite(float(gap)):
        raise StatisticsRefusal(f"a row's gap must be a finite number, got {gap!r}")
    return float(gap)


def _median(values: Sequence[float]) -> float:
    return _quantile_type7(sorted(values), 0.5)




# ------------------------------------------------------------------------------------------------ numerical helpers
def is_significant(p_value: float, alpha: float) -> bool:
    """The one significance comparison of the service (owner decision, A18): ``p <= alpha``. The omnibus gate and the Holm-adjusted
    pairwise p-values both use it."""
    return p_value <= alpha


def holm_adjust(p_values: Sequence[float], alpha: float) -> list:
    """Holm-adjusted p-values in input order, each with its decision (``is_significant``). statsmodels ``multipletests``."""
    values = [float(p) for p in p_values]
    if not values:
        return []
    from statsmodels.stats.multitest import multipletests

    adjusted = [float(p) for p in multipletests(values, alpha=alpha, method="holm")[1]]
    return [(p, is_significant(p, alpha)) for p in adjusted]


def iman_davenport_f(chi_square: float, n_blocks: int, n_treatments: int) -> tuple:
    """Iman-Davenport F of a Friedman test (Demsar 2006, section 3.2.2): F = (b - 1) chi2_F / (b (k - 1) - chi2_F) with k - 1 and
    (k - 1)(b - 1) degrees of freedom; ``(F, df1, df2)``. At the maximum chi2_F = b (k - 1) (perfect agreement) F is infinite."""
    for value, name in ((n_blocks, "blocks"), (n_treatments, "treatments")):
        if isinstance(value, bool) or not isinstance(value, int) or value < 2:
            raise StatisticsRefusal(f"the Iman-Davenport F needs an integer number of {name} >= 2, got {value!r}")
    if isinstance(chi_square, bool) or not isinstance(chi_square, (int, float)) or not math.isfinite(float(chi_square)) or chi_square < 0:
        raise StatisticsRefusal(f"the Iman-Davenport F needs a finite chi-square >= 0, got {chi_square!r}")
    df1, df2 = n_treatments - 1, (n_treatments - 1) * (n_blocks - 1)
    denominator = n_blocks * (n_treatments - 1) - float(chi_square)
    if denominator <= 0:
        return math.inf, df1, df2
    return (n_blocks - 1) * float(chi_square) / denominator, df1, df2


def smallest_possible_adjusted_p(n_units: int, n_pairs: int) -> float:
    """Smallest Holm-adjusted p-value that ``n_pairs`` exact two-sided Wilcoxon signed-rank tests over ``n_units`` matched units can
    reach: one pair with all units differing in one direction has p = 2 / 2^n, and Holm multiplies the smallest p by the family size."""
    if n_units < 1 or n_pairs < 1:
        raise StatisticsRefusal("the power limit needs at least one unit and one pair")
    return min(1.0, n_pairs * 2.0 ** (1 - n_units))


def mannwhitney_method_used(x: Sequence[float], y: Sequence[float], method: str) -> str:
    """The method SciPy applies: ``auto`` is exact for at most 55 observations per sample and no ties in the combined data, else
    asymptotic (SciPy ``mannwhitneyu`` documentation); an explicit method is used as given."""
    if method != "auto":
        return method
    tied = len(set(x) | set(y)) < len(x) + len(y)
    return "exact" if max(len(x), len(y)) <= 55 and not tied else "asymptotic"


def wilcoxon_method_used(x: Sequence[float], y: Sequence[float], method: str) -> str:
    """The method SciPy applies (``_wilcoxon_nd``): ``auto`` is exact without zero differences and without tied absolute differences;
    otherwise a deterministic permutation test for at most 13 units and the asymptotic test above that."""
    if method != "auto":
        return method
    diffs = [a - b for a, b in zip(x, y)]
    magnitudes = [abs(d) for d in diffs if d != 0]
    if len(magnitudes) == len(diffs) and len(set(magnitudes)) == len(magnitudes):
        return "exact"
    return "permutation" if len(diffs) <= 13 else "asymptotic"


# ------------------------------------------------------------------------------------------------ tests
def _pairs_independent(samples: Mapping[str, list], alpha: float, conventions) -> tuple:
    from scipy import stats as sps

    conv = conventions.mann_whitney
    raw = []
    for a, b in itertools.combinations(sorted(samples), 2):
        result = sps.mannwhitneyu(
            samples[a], samples[b], alternative="two-sided", method=conv.method, use_continuity=conv.continuity_correction
        )
        raw.append((a, b, float(result.statistic), float(result.pvalue)))
    adjusted = holm_adjust([item[3] for item in raw], alpha)
    return tuple(
        PairResult(a, b, "mann_whitney_u", STATUS_COMPUTED, u, p, ph, sig, "vargha_delaney_a12",
                   vargha_delaney_a12(samples[a], samples[b]), len(samples[a]), len(samples[b]),
                   mannwhitney_method_used(samples[a], samples[b], conv.method))
        for (a, b, u, p), (ph, sig) in zip(raw, adjusted)
    )


def _pairs_matched(units: Mapping[str, list], alpha: float, conventions) -> tuple:
    from scipy import stats as sps

    conv = conventions.wilcoxon
    raw = []
    for a, b in itertools.combinations(sorted(units), 2):
        x, y = units[a], units[b]
        r = matched_pairs_rank_biserial(x, y, conv.zero_method)
        if r is None:  # every difference is zero: SciPy cannot compute it; reported with p = 1 and kept in the Holm family (A18)
            raw.append((a, b, "all_differences_zero", 0.0, 1.0, None, "none (all differences are zero)"))
            continue
        result = sps.wilcoxon(
            x, y, zero_method=conv.zero_method, correction=conv.continuity_correction, alternative="two-sided", method=conv.method
        )
        raw.append((a, b, STATUS_COMPUTED, float(result.statistic), float(result.pvalue), r, wilcoxon_method_used(x, y, conv.method)))
    adjusted = holm_adjust([item[4] for item in raw], alpha)
    return tuple(
        PairResult(a, b, "wilcoxon_signed_rank", status, stat, p, ph, sig, "matched_pairs_rank_biserial", r,
                   len(units[a]), len(units[b]), used)
        for (a, b, status, stat, p, r, used), (ph, sig) in zip(raw, adjusted)
    )


def _omnibus_independent(samples: Mapping[str, list], alpha: float) -> Omnibus:
    from scipy import stats as sps

    groups = [samples[name] for name in sorted(samples)]
    n_total = sum(len(g) for g in groups)
    if len({v for g in groups for v in g}) == 1:
        return Omnibus("kruskal_wallis", STATUS_UNDEFINED, None, "kruskal_wallis_h", None, "chi_square", "epsilon_squared", None,
                       False, len(groups), n_total)
    result = sps.kruskal(*groups)
    p = float(result.pvalue)
    return Omnibus("kruskal_wallis", STATUS_COMPUTED, float(result.statistic), "kruskal_wallis_h", p, "chi_square",
                   "epsilon_squared", epsilon_squared(float(result.statistic), n_total), is_significant(p, alpha), len(groups), n_total)


def _omnibus_matched(columns: Mapping[str, list], alpha: float) -> Omnibus:
    from scipy import stats as sps

    names = sorted(columns)
    blocks = [list(row) for row in zip(*[columns[name] for name in names])]
    b, k = len(blocks), len(names)
    w = kendalls_w(blocks)
    if w is None:
        return Omnibus("friedman", STATUS_UNDEFINED, None, "iman_davenport_f", None, "iman_davenport_f", "kendalls_w", None, False, k, b)
    chi = sps.friedmanchisquare(*[columns[name] for name in names])
    # the tie-corrected chi2_F equals W * b * (k - 1); the F statistic is computed from W so that perfect agreement is exactly infinite
    f, df1, df2 = iman_davenport_f(w * b * (k - 1), b, k)
    p = 0.0 if f == math.inf else float(sps.f.sf(f, df1, df2))
    return Omnibus("friedman", STATUS_COMPUTED, f, "iman_davenport_f", p, "iman_davenport_f", "kendalls_w", w,
                   is_significant(p, alpha), k, b, float(chi.statistic), float(chi.pvalue))


# ------------------------------------------------------------------------------------------------ the service
def _fmt(value: Optional[float]) -> str:
    return "undefined" if value is None else f"{value:.6g}"


def _render(values: dict, plan: AnalysisPlanV1, family: ComparisonFamilyV1) -> str:
    cells, exclusions = values["cells"], values["exclusions"]
    refused, inference = values["inference_refused"], values["inference"]
    conv = plan.conventions
    lines = [
        f"Family {family.family_id} ({family.scope}); campaign mode {values['campaign_mode']}; "
        f"analysis plan {plan.analysis_plan_id} (status {plan.status}); statistics library {values['statistics_library']}.",
        f"Cells (descriptive statistics of the {plan.response.variable}, {plan.response.unit}; "
        f"SD convention {plan.descriptive.sd_convention}, quantiles {plan.descriptive.quantile_method}):",
    ]
    for cell in cells:
        columns = ", ".join(f"{k}={_fmt(v)}" for k, v in cell.summary.items())
        lines.append(f"  {cell.dataset_identity} / {cell.algorithm_id}: {columns}")
    for item in exclusions:
        who = f"{item['algorithm_id']} on {item['dataset_identity']}" if item.get("algorithm_id") else f"instance {item['dataset_identity']}"
        lines.append(f"  excluded from inference: {who} ({item['reason']})")
    for item in values["excluded_pairs"]:
        lines.append(f"  pair excluded from the Holm family: {item['algorithm_a']} vs {item['algorithm_b']} ({item['reason']})")
    if inference is None:
        lines.append("Inference not performed (descriptive output only): " + "; ".join(refused))
    else:
        o = inference.omnibus
        lines.append(
            f"Omnibus {o.test}: status {o.status}, {o.statistic_name} {_fmt(o.statistic)}, p {_fmt(o.p_value)} ({o.p_value_method}), "
            f"{o.effect_size_name} {_fmt(o.effect_size)}, alpha {inference.alpha}, groups {o.n_groups}, n {o.n_observations}."
        )
        if o.chi_square_statistic is not None:
            lines.append(f"  chi-square beside it: statistic {_fmt(o.chi_square_statistic)}, p {_fmt(o.chi_square_p_value)}.")
        lines.append(f"Post-hoc ({inference.correction}): {inference.post_hoc_reason}")
        for pair in inference.pairs:
            lines.append(
                f"  {pair.algorithm_a} vs {pair.algorithm_b} ({pair.test}, method used {pair.method_used}): status {pair.status}, "
                f"statistic {_fmt(pair.statistic)}, p {_fmt(pair.p_value)}, p after {inference.correction} {_fmt(pair.p_holm)}, "
                f"{pair.effect_size_name} {_fmt(pair.effect_size)}, n {pair.n_a}/{pair.n_b}"
            )
    if family.scope == "per_instance":
        lines.append(
            "Effect-size direction: A12 is P(gap of algorithm a > gap of algorithm b) + 0.5 P(equal) for the pair (a, b) as listed."
        )
    else:
        lines.append(
            "Effect-size direction: the matched-pairs rank-biserial r is positive when algorithm a has larger gaps than algorithm b "
            "for the pair (a, b) as listed."
        )
        datasets, algorithms = {c.dataset_identity for c in cells}, {c.algorithm_id for c in cells}
        if len(datasets) >= 2 and len(algorithms) >= 2:
            pairs = len(algorithms) * (len(algorithms) - 1) // 2
            smallest = smallest_possible_adjusted_p(len(datasets), pairs)
            if not is_significant(smallest, plan.alpha):
                lines.append(plan.power_declaration.statement)
                lines.append(
                    f"With {len(datasets)} matched units the smallest possible exact two-sided Wilcoxon p is {_fmt(2.0 ** (1 - len(datasets)))}; "
                    f"after Holm over {pairs} pairs the smallest possible adjusted p is {_fmt(smallest)}, above alpha {plan.alpha}: "
                    "the pairwise cross-instance tests cannot reach significance here."
                )
    lines.append(
        f"Conventions (from the analysis plan): Mann-Whitney method {conv.mann_whitney.method}, continuity correction "
        f"{conv.mann_whitney.continuity_correction}; Wilcoxon method {conv.wilcoxon.method}, continuity correction "
        f"{conv.wilcoxon.continuity_correction}, zero differences {conv.wilcoxon.zero_method}; significance p <= alpha; "
        f"Holm {conv.holm_scope.replace('_', ' ')}, no correction across instances."
    )
    lines.append("Statistical results describe these runs only; the report states no ordering of the algorithms.")
    return "\n".join(lines)


def _algorithm_token(algorithm: str, level_index: Optional[int]) -> str:
    """The algorithm part of a run id (``manifests.make_run_id`` lower-cases and sanitises it)."""
    run_id = make_run_id("s", "d", algorithm, level_index, 0)
    protocol = "native" if level_index is None else f"fixed-l{level_index}"
    return run_id[len(f"s.d.{protocol}."):-len(".r0")]


def _campaign_algorithm_tokens(run_index: RunIndexV1, study_id: str, level_index: Optional[int]) -> set:
    """The algorithms that the verified campaign ran for this study and budget level (native: no level), read from the run ids of the
    index: ``<study>.<dataset>.<protocol>.<algorithm>.r<replicate>``. A fully failed cell has no manifest, but its algorithm has runs
    on other instances of the campaign, so the family's algorithm set does not depend on which cells completed (OQ-9)."""
    protocol = "native" if level_index is None else f"fixed-l{level_index}"
    study = make_run_id(study_id, "d", "a", level_index, 0).split(".d.", 1)[0]
    pattern = re.compile(rf"^{re.escape(study)}\..+?\.{re.escape(protocol)}\.(?P<algorithm>.+)\.r\d+$")
    tokens = set()
    for entry in run_index.runs:
        match = pattern.match(entry.run_id)
        if match:
            tokens.add(match.group("algorithm"))
    return tokens


def _check_conventions(plan: AnalysisPlanV1) -> None:
    c = plan.conventions
    if c.alternative != "two_sided":
        raise StatisticsRefusal(f"alternative {c.alternative!r} is not implemented (two_sided)")
    if c.significance != "p_less_than_or_equal_alpha":
        raise StatisticsRefusal(f"significance rule {c.significance!r} is not implemented (p_less_than_or_equal_alpha)")
    if (c.holm_scope, c.correction_across_instances) != ("within_comparison_cell", "none"):
        raise StatisticsRefusal("only Holm within each comparison cell without a correction across instances is implemented")
    if c.mann_whitney.method not in ("auto", "exact", "asymptotic"):
        raise StatisticsRefusal(f"mann_whitney method {c.mann_whitney.method!r} is not implemented (auto, exact, asymptotic)")
    if c.wilcoxon.method not in ("auto", "exact", "asymptotic") or c.wilcoxon.zero_method not in ZERO_METHODS:
        raise StatisticsRefusal(f"wilcoxon method {c.wilcoxon.method!r} / zero_method {c.wilcoxon.zero_method!r} is not implemented")
    if c.friedman.primary_p_value != "iman_davenport_f" or list(c.friedman.also_report) != ["chi_square"]:
        raise StatisticsRefusal("only the Iman-Davenport F as primary Friedman p-value with the chi-square beside it is implemented")
    if (c.all_zero_wilcoxon_pair, c.identical_value_omnibus) != (
        "all_differences_zero_p_one_in_holm_family", "undefined_not_significant"
    ):
        raise StatisticsRefusal("the plan's degenerate-case conventions are not the implemented ones")


def analyse_family(
    items: Iterable[tuple], *, study: StudyManifestV1, plan: AnalysisPlanV1, family_id: str, run_index: RunIndexV1
) -> FamilyAnalysis:
    """Analyse one declared comparison family. ``items`` are ``(row, manifest)`` pairs: rows with the D-06 gap column and their
    ``RunManifestV1``; failed runs are ``(row, None)``. ``run_index`` is the ``RunIndexV1`` of the campaign that the caller has verified
    (``manifests.verify_campaign``): its ``mode`` is the campaign mode ("smoke" or "paper"), and every manifest must be listed in it
    with the comparison key digest of its row. Raises ``StatisticsRefusal`` (or ``AnalysisEnvironmentError``) for input that must
    not be analysed; otherwise returns descriptive cells plus either the inference or the named reasons why it was not performed."""
    require_analysis_environment()
    family = _plan_family(plan, family_id)
    _check_conventions(plan)
    if not isinstance(study, StudyManifestV1):
        raise StatisticsRefusal(f"study must be the StudyManifestV1 profile that declares the algorithms, not {type(study).__name__}")
    if study.study_id != plan.study_id:
        raise StatisticsRefusal(f"the study profile {study.study_id!r} and the analysis plan of study {plan.study_id!r} do not belong together")
    if not isinstance(run_index, RunIndexV1):
        raise StatisticsRefusal(f"run_index must be the verified RunIndexV1 of the campaign, not {type(run_index).__name__}")
    campaign_mode = run_index.mode
    conventions = plan.conventions
    pairs_in = list(items)
    if not pairs_in or any(not isinstance(pair, tuple) or len(pair) != 2 for pair in pairs_in):
        raise StatisticsRefusal("items must be a non-empty list of (row, manifest) pairs")
    rows = [row for row, _ in pairs_in]
    for row in rows:
        if isinstance(row, Mapping) and row.get("evidence_class") not in CURRENT_EVIDENCE:
            raise StatisticsRefusal(
                f"evidence_class {row.get('evidence_class')!r}: historical_unverified and invalid rows are never analysed (A13)"
            )
    try:
        assert_rankable(rows)
    except (ValueError, TypeError) as exc:
        raise StatisticsRefusal(str(exc)) from exc
    good = [(row, manifest) for row, manifest in pairs_in if not _is_failed(row)]
    failed = [row for row, _ in pairs_in if _is_failed(row)]
    if not good:
        raise StatisticsRefusal("no completed run in the input: nothing to analyse")
    vary = ("algorithm",) if family.scope == "per_instance" else ("algorithm", "dataset")
    try:
        identity_family = assert_single_comparison_family(good, vary=vary, allow_dirty=False)
    except ComparisonIdentityError as exc:
        raise StatisticsRefusal(f"not one comparison family: {exc}") from exc
    if identity_family is None or identity_family.contains_dirty:
        raise StatisticsRefusal("the rows come from a dirty working tree (contains_dirty): no code identity, no statistics")

    # the verified campaign index binds the manifests: mode, study, commit and the comparison key of every run
    if run_index.git.dirty:
        raise StatisticsRefusal("the run index records a dirty working tree: no code identity, no statistics")
    study_id = identity_family.shared["study_id"]
    if run_index.study_id != study_id:
        raise StatisticsRefusal(f"the run index belongs to study {run_index.study_id!r}, the rows to study {study_id!r}")
    listed = {entry.run_id: entry for entry in run_index.runs}
    for row, manifest in good:
        entry = listed.get(manifest.run_id)
        if entry is None:
            raise StatisticsRefusal(f"manifest {manifest.run_id!r} is not listed in the run index: rows must come from the verified campaign")
        if manifest.git.commit != run_index.git.commit:
            raise StatisticsRefusal(f"manifest {manifest.run_id!r} was written at commit {manifest.git.commit}, the run index at {run_index.git.commit}")
        if comparison_cell_key(row, manifest).digest() != entry.comparison_key_digest:
            raise StatisticsRefusal(f"the comparison key digest of {manifest.run_id!r} differs from the run index entry")

    unit = plan.response.unit
    samples: dict = {}
    for row, manifest in good:
        dataset_id = manifest.dataset.dataset_id
        if dataset_id not in family.dataset_ids:
            raise StatisticsRefusal(f"dataset {dataset_id!r} is outside the declared family {family.family_id!r} {family.dataset_ids}")
        if manifest.dataset.problem_type not in family.problem_types:
            raise StatisticsRefusal(f"problem type {manifest.dataset.problem_type!r} is outside the declared family {family.family_id!r}")
        replicate = row.get("replicate")
        if isinstance(replicate, bool) or not isinstance(replicate, int):
            raise StatisticsRefusal("every row needs an integer replicate")
        cell = samples.setdefault((normalize_problem(row["problem"]), row["algorithm_id"]), {})
        if replicate in cell:
            raise StatisticsRefusal(f"duplicate replicate {replicate} for {row['algorithm_id']!r} on {row['problem']!r}")
        cell[replicate] = _gap_of(row, unit)

    budgets: dict = {}
    for row, _ in good:
        budgets.setdefault(normalize_problem(row["problem"]), set()).add(row.get("evaluation_budget"))
    level_index = identity_family.shared["budget_level_index"]
    campaign_algorithms = _campaign_algorithm_tokens(run_index, study_id, level_index)
    protocol_version = identity_family.shared["protocol_version"]
    failed_counts: dict = {}
    for row in failed:
        problem, algorithm = row.get("problem"), row.get("algorithm_id")
        if not isinstance(problem, str) or not isinstance(algorithm, str):
            raise StatisticsRefusal("a failed run needs its algorithm_id and problem name to be reported")
        if _algorithm_token(algorithm, level_index) not in campaign_algorithms:
            raise StatisticsRefusal(
                f"a failed run names algorithm_id {algorithm!r}, which the run index does not list for study {study_id!r} at this budget level"
            )
        if row.get("study_id") != study_id:
            raise StatisticsRefusal(f"a failed run of {algorithm!r} has study_id {row.get('study_id')!r}, the family's is {study_id!r}")
        if row.get("protocol_version") != protocol_version:
            raise StatisticsRefusal(
                f"a failed run of {algorithm!r} has protocol_version {row.get('protocol_version')!r}, the family's is {protocol_version!r}"
            )
        identity = normalize_problem(problem)
        known = budgets.get(identity)
        if known and row.get("evaluation_budget") not in known:
            raise StatisticsRefusal(f"a failed run of {algorithm!r} on {problem!r} belongs to another budget level than the analysed rows")
        failed_counts[(identity, algorithm)] = failed_counts.get((identity, algorithm), 0) + 1
    exclusions = [
        {"algorithm_id": algorithm, "dataset_identity": dataset, "failed_runs": count,
         "reason": "failed run(s): the cell is excluded from inference and reported (plan failure policy)"}
        for (dataset, algorithm), count in sorted(failed_counts.items())
    ]
    seen_algorithms = sorted({a for _, a in samples} | {a for _, a in failed_counts})
    for key in failed_counts:
        samples.pop(key, None)
    excluded_pairs: list = []
    if family.scope == "per_instance":
        out = {a for _, a in failed_counts}
        for a, b in itertools.combinations(seen_algorithms, 2):
            if a in out or b in out:
                who = " and ".join(sorted({a, b} & out))
                excluded_pairs.append({
                    "algorithm_a": a, "algorithm_b": b,
                    "reason": f"the cell of {who} is excluded after failed run(s); the pair is not in the Holm family",
                })
    absent: list = []
    if family.scope == "across_instances":
        present = {dataset for dataset, _ in samples} | {dataset for dataset, _ in failed_counts}
        absent = [d.removeprefix("tsplib-") for d in family.dataset_ids if d.removeprefix("tsplib-") not in present]
        for name in absent:
            exclusions.append({"algorithm_id": None, "dataset_identity": name, "failed_runs": 0,
                               "reason": "instance of the declared family has no rows in the analysed input"})

    cells = tuple(
        CellSummary(dataset, algorithm, len(values), describe_sample([values[r] for r in sorted(values)], plan.descriptive))
        for (dataset, algorithm), values in sorted(samples.items())
    )

    reasons = []
    if campaign_mode != "paper":
        reasons.append(f"campaign mode is {campaign_mode!r}: smoke runs give descriptive output only and no inferential claim")
    if plan.status != "active":
        reasons.append(f"analysis plan {plan.analysis_plan_id!r} has status {plan.status!r}; inference needs an active plan")
    if plan.minimum_n_per_cell is None:
        reasons.append("minimum_n_per_cell is unresolved in the analysis plan; no inference without it")
    else:
        small = sorted(f"{a} on {d} (n={len(v)})" for (d, a), v in samples.items() if len(v) < plan.minimum_n_per_cell)
        if small:
            reasons.append(f"insufficient sample: fewer than minimum_n_per_cell={plan.minimum_n_per_cell} replicates for " + ", ".join(small))
    algorithms = sorted({algorithm for _, algorithm in samples})
    datasets = sorted({dataset for dataset, _ in samples})
    if family.scope == "per_instance" and len(algorithms) < 2:
        reasons.append("insufficient sample: fewer than two algorithms with a complete cell remain")
    if family.scope == "across_instances":
        if len(datasets) < 2:
            reasons.append("insufficient sample: the matched omnibus needs at least two instances")
        if len(algorithms) < 3:
            reasons.append("insufficient sample: the Friedman omnibus needs at least three algorithms")

    inference = None
    if not reasons:
        if family.scope == "per_instance":
            lengths = {algorithm: sorted(samples[(datasets[0], algorithm)]) for algorithm in algorithms}
            if len({tuple(v) for v in lengths.values()}) != 1:
                raise StatisticsRefusal(
                    f"the replicate sets of the algorithms differ on {datasets[0]!r}: {lengths}; a balanced replicate design is required"
                )
            data = {a: [samples[(datasets[0], a)][r] for r in lengths[a]] for a in algorithms}
            omnibus = _omnibus_independent(data, plan.alpha)
            run_pairs = lambda: _pairs_independent(data, plan.alpha, conventions)  # noqa: E731
            matched = None
        else:
            if absent:
                raise StatisticsRefusal(
                    f"declared instance(s) {absent} of family {family.family_id!r} have no completed and no failed rows; the matched "
                    "design must cover every declared instance (no instance is dropped or added after results are seen)"
                )
            missing = [(d, a) for d in datasets for a in algorithms if (d, a) not in samples]
            if missing:
                excluded = {(e["dataset_identity"], e["algorithm_id"]) for e in exclusions}
                detail = ", ".join(f"{a} on {d} ({'excluded after a failed run' if (d, a) in excluded else 'missing'})" for d, a in missing)
                raise StatisticsRefusal(
                    f"the matched design has no unit for: {detail}. Unit sets must be equal across instances (no silent drop of an "
                    "instance or an algorithm); this cell is excluded or missing"
                )
            replicate_sets = {d: {tuple(sorted(samples[(d, a)])) for a in algorithms} for d in datasets}
            unbalanced = sorted(d for d, sets in replicate_sets.items() if len(sets) > 1)
            if unbalanced:
                raise StatisticsRefusal(f"the replicate sets of the algorithms differ on {unbalanced}; a balanced replicate design is required")
            matched = {(d, a): _median(list(samples[(d, a)].values())) for d in datasets for a in algorithms}
            data = {a: [matched[(d, a)] for d in datasets] for a in algorithms}
            omnibus = _omnibus_matched(data, plan.alpha)
            run_pairs = lambda: _pairs_matched(data, plan.alpha, conventions)  # noqa: E731
        rule = family.post_hoc.rule
        if rule == "only_after_significant_omnibus" and not omnibus.significant:
            ran, why, pairs = False, "not run: the omnibus test is not significant (rule only_after_significant_omnibus)", ()
        else:
            ran, why, pairs = True, f"run under the rule {rule}", run_pairs()
        inference = InferenceResult(omnibus, ran, why, pairs, family.post_hoc.correction, plan.alpha, matched)

    values = {
        "family_id": family.family_id, "scope": family.scope, "campaign_mode": campaign_mode,
        "analysis_plan_id": plan.analysis_plan_id, "plan_status": plan.status,
        "statistics_library": statistics_library_identifier(), "conventions": conventions.model_dump(mode="json"),
        "cells": cells, "exclusions": tuple(exclusions), "inference_refused": tuple(reasons), "inference": inference,
        "excluded_pairs": tuple(excluded_pairs),
    }
    return FamilyAnalysis(**values, text=_render(values, plan, family))


__all__ = [
    "CellSummary", "FamilyAnalysis", "InferenceResult", "Omnibus", "PairResult", "StatisticsRefusal", "analyse_family",
    "describe_sample", "epsilon_squared", "holm_adjust", "iman_davenport_f", "is_significant", "kendalls_w",
    "mannwhitney_method_used", "matched_pairs_rank_biserial", "smallest_possible_adjusted_p", "vargha_delaney_a12",
    "wilcoxon_method_used",
]
