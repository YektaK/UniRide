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
import math
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Optional, Sequence

from academic_benchmark.analysis.environment import require_analysis_environment, statistics_library_identifier
from academic_benchmark.analysis.identity import ComparisonIdentityError, assert_single_comparison_family
from academic_benchmark.contracts.analysis_plan import AnalysisPlanV1, ComparisonFamilyV1, DescriptiveV1
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


# ------------------------------------------------------------------------------------------------ policy
@dataclass(frozen=True)
class NumericalPolicy:
    """Numerical conventions of the tests that the analysis plan does not fix. Every field is required (no defaults):
    the caller states them and every result echoes them. Open owner question in the D-05 hand-over report."""

    alternative: str
    mannwhitney_method: str
    mannwhitney_use_continuity: bool
    wilcoxon_method: str
    wilcoxon_zero_method: str
    wilcoxon_correction: bool

    def validate(self) -> None:
        if self.alternative != "two-sided":
            raise StatisticsRefusal(f"alternative {self.alternative!r} is not implemented; only 'two-sided' (the omnibus tests are non-directional)")
        if self.mannwhitney_method not in ("auto", "exact", "asymptotic"):
            raise StatisticsRefusal(f"mannwhitney_method {self.mannwhitney_method!r} is not implemented (auto, exact, asymptotic)")
        if self.wilcoxon_method not in ("auto", "exact", "asymptotic"):
            raise StatisticsRefusal(f"wilcoxon_method {self.wilcoxon_method!r} is not implemented (auto, exact, asymptotic)")
        if self.wilcoxon_zero_method not in ZERO_METHODS:
            raise StatisticsRefusal(f"wilcoxon_zero_method {self.wilcoxon_zero_method!r} is not implemented {ZERO_METHODS}")
        for name in ("mannwhitney_use_continuity", "wilcoxon_correction"):
            if not isinstance(getattr(self, name), bool):
                raise StatisticsRefusal(f"{name} must be a bool")


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
    p_value: Optional[float]
    effect_size_name: str
    effect_size: Optional[float]
    significant: bool
    n_groups: int
    n_observations: int  # per-instance: replicates in total; across instances: matched units per algorithm


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
    numerical_policy: Mapping[str, Any]
    cells: tuple
    exclusions: tuple
    inference_refused: tuple
    inference: Optional[InferenceResult]
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


# ------------------------------------------------------------------------------------------------ tests
def _holm(p_values: Sequence[float], alpha: float) -> list:
    from statsmodels.stats.multitest import multipletests

    return [float(p) for p in multipletests(list(p_values), alpha=alpha, method="holm")[1]]


def _pairs_independent(samples: Mapping[str, list], alpha: float, policy: NumericalPolicy) -> tuple:
    from scipy import stats as sps

    raw = []
    for a, b in itertools.combinations(sorted(samples), 2):
        result = sps.mannwhitneyu(
            samples[a], samples[b], alternative=policy.alternative, method=policy.mannwhitney_method,
            use_continuity=policy.mannwhitney_use_continuity,
        )
        raw.append((a, b, float(result.statistic), float(result.pvalue)))
    adjusted = _holm([item[3] for item in raw], alpha) if raw else []
    return tuple(
        PairResult(a, b, "mann_whitney_u", STATUS_COMPUTED, u, p, ph, ph < alpha, "vargha_delaney_a12",
                   vargha_delaney_a12(samples[a], samples[b]), len(samples[a]), len(samples[b]))
        for (a, b, u, p), ph in zip(raw, adjusted)
    )


def _pairs_matched(units: Mapping[str, list], alpha: float, policy: NumericalPolicy) -> tuple:
    from scipy import stats as sps

    raw = []
    for a, b in itertools.combinations(sorted(units), 2):
        x, y = units[a], units[b]
        r = matched_pairs_rank_biserial(x, y, policy.wilcoxon_zero_method)
        if r is None:  # every difference is zero: SciPy cannot compute it; the observed data sit exactly at the null centre
            raw.append((a, b, "all_differences_zero", 0.0, 1.0, None))
            continue
        result = sps.wilcoxon(
            x, y, zero_method=policy.wilcoxon_zero_method, correction=policy.wilcoxon_correction,
            alternative=policy.alternative, method=policy.wilcoxon_method,
        )
        raw.append((a, b, STATUS_COMPUTED, float(result.statistic), float(result.pvalue), r))
    adjusted = _holm([item[4] for item in raw], alpha) if raw else []
    return tuple(
        PairResult(a, b, "wilcoxon_signed_rank", status, stat, p, ph, ph < alpha, "matched_pairs_rank_biserial", r,
                   len(units[a]), len(units[b]))
        for (a, b, status, stat, p, r), ph in zip(raw, adjusted)
    )


def _omnibus_independent(samples: Mapping[str, list], alpha: float) -> Omnibus:
    from scipy import stats as sps

    groups = [samples[name] for name in sorted(samples)]
    n_total = sum(len(g) for g in groups)
    if len({v for g in groups for v in g}) == 1:
        return Omnibus("kruskal_wallis", STATUS_UNDEFINED, None, None, "epsilon_squared", None, False, len(groups), n_total)
    result = sps.kruskal(*groups)
    p = float(result.pvalue)
    return Omnibus("kruskal_wallis", STATUS_COMPUTED, float(result.statistic), p, "epsilon_squared",
                   epsilon_squared(float(result.statistic), n_total), p < alpha, len(groups), n_total)


def _omnibus_matched(columns: Mapping[str, list], alpha: float) -> Omnibus:
    from scipy import stats as sps

    names = sorted(columns)
    blocks = [list(row) for row in zip(*[columns[name] for name in names])]
    w = kendalls_w(blocks)
    if w is None:
        return Omnibus("friedman", STATUS_UNDEFINED, None, None, "kendalls_w", None, False, len(names), len(blocks))
    result = sps.friedmanchisquare(*[columns[name] for name in names])
    p = float(result.pvalue)
    return Omnibus("friedman", STATUS_COMPUTED, float(result.statistic), p, "kendalls_w", w, p < alpha, len(names), len(blocks))


# ------------------------------------------------------------------------------------------------ the service
def _fmt(value: Optional[float]) -> str:
    return "undefined" if value is None else f"{value:.6g}"


def _render(analysis_kwargs: dict, plan: AnalysisPlanV1, family: ComparisonFamilyV1) -> str:
    cells, exclusions = analysis_kwargs["cells"], analysis_kwargs["exclusions"]
    refused, inference = analysis_kwargs["inference_refused"], analysis_kwargs["inference"]
    lines = [
        f"Family {family.family_id} ({family.scope}); campaign mode {analysis_kwargs['campaign_mode']}; "
        f"analysis plan {plan.analysis_plan_id} (status {plan.status}); statistics library {analysis_kwargs['statistics_library']}.",
        f"Cells (descriptive statistics of the {plan.response.variable}, {plan.response.unit}; "
        f"SD convention {plan.descriptive.sd_convention}, quantiles {plan.descriptive.quantile_method}):",
    ]
    for cell in cells:
        columns = ", ".join(f"{k}={_fmt(v)}" for k, v in cell.summary.items())
        lines.append(f"  {cell.dataset_identity} / {cell.algorithm_id}: {columns}")
    for item in exclusions:
        who = f"{item['algorithm_id']} on {item['dataset_identity']}" if item.get("algorithm_id") else f"instance {item['dataset_identity']}"
        lines.append(f"  excluded from inference: {who} ({item['reason']})")
    if inference is None:
        lines.append("Inference not performed (descriptive output only): " + "; ".join(refused))
    else:
        o = inference.omnibus
        lines.append(
            f"Omnibus {o.test}: status {o.status}, statistic {_fmt(o.statistic)}, p {_fmt(o.p_value)}, "
            f"{o.effect_size_name} {_fmt(o.effect_size)}, alpha {inference.alpha}, groups {o.n_groups}, n {o.n_observations}."
        )
        lines.append(f"Post-hoc ({inference.correction}): {inference.post_hoc_reason}")
        for pair in inference.pairs:
            lines.append(
                f"  {pair.algorithm_a} vs {pair.algorithm_b} ({pair.test}): status {pair.status}, statistic {_fmt(pair.statistic)}, "
                f"p {_fmt(pair.p_value)}, p after {inference.correction} {_fmt(pair.p_holm)}, "
                f"{pair.effect_size_name} {_fmt(pair.effect_size)}, n {pair.n_a}/{pair.n_b}"
            )
    policy = ", ".join(f"{k}={v}" for k, v in analysis_kwargs["numerical_policy"].items())
    lines.append(f"Numerical policy: {policy}.")
    lines.append("Statistical results describe these runs only; the report states no ordering of the algorithms.")
    return "\n".join(lines)


def analyse_family(
    items: Iterable[tuple], *, plan: AnalysisPlanV1, family_id: str, campaign_mode: str, policy: NumericalPolicy
) -> FamilyAnalysis:
    """Analyse one declared comparison family. ``items`` are ``(row, manifest)`` pairs: rows with the D-06 gap column and their
    ``RunManifestV1``; failed runs are ``(row, None)``. ``campaign_mode`` is the mode of the verified campaign index
    (``"smoke"`` or ``"paper"``). Raises ``StatisticsRefusal`` (or ``AnalysisEnvironmentError``) for input that must not be
    analysed; otherwise returns descriptive cells plus either the inference or the named reasons why it was not performed."""
    require_analysis_environment()
    family = _plan_family(plan, family_id)
    if campaign_mode not in CAMPAIGN_MODES:
        raise StatisticsRefusal(f"campaign_mode must be one of {CAMPAIGN_MODES}, got {campaign_mode!r}")
    if not isinstance(policy, NumericalPolicy):
        raise StatisticsRefusal("policy must be a NumericalPolicy")
    policy.validate()
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
    failed_counts: dict = {}
    for row in failed:
        problem, algorithm = row.get("problem"), row.get("algorithm_id")
        if not isinstance(problem, str) or not isinstance(algorithm, str):
            raise StatisticsRefusal("a failed run needs its algorithm_id and problem name to be reported")
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
    for key in failed_counts:
        samples.pop(key, None)
    if family.scope == "across_instances":
        present = {dataset for dataset, _ in samples} | {dataset for dataset, _ in failed_counts}
        for dataset_id in family.dataset_ids:
            name = dataset_id.removeprefix("tsplib-")
            if name not in present:
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
            run_pairs = lambda: _pairs_independent(data, plan.alpha, policy)  # noqa: E731
            matched = None
        else:
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
            run_pairs = lambda: _pairs_matched(data, plan.alpha, policy)  # noqa: E731
        rule = family.post_hoc.rule
        if rule == "only_after_significant_omnibus" and not omnibus.significant:
            ran, why, pairs = False, "not run: the omnibus test is not significant (rule only_after_significant_omnibus)", ()
        else:
            ran, why, pairs = True, f"run under the rule {rule}", run_pairs()
        inference = InferenceResult(omnibus, ran, why, pairs, family.post_hoc.correction, plan.alpha, matched)

    values = {
        "family_id": family.family_id, "scope": family.scope, "campaign_mode": campaign_mode,
        "analysis_plan_id": plan.analysis_plan_id, "plan_status": plan.status,
        "statistics_library": statistics_library_identifier(), "numerical_policy": asdict(policy),
        "cells": cells, "exclusions": tuple(exclusions), "inference_refused": tuple(reasons), "inference": inference,
    }
    return FamilyAnalysis(**values, text=_render(values, plan, family))


__all__ = [
    "CellSummary", "FamilyAnalysis", "InferenceResult", "NumericalPolicy", "Omnibus", "PairResult", "StatisticsRefusal",
    "analyse_family", "describe_sample", "epsilon_squared", "kendalls_w", "matched_pairs_rank_biserial", "vargha_delaney_a12",
]
