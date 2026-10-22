"""C-16c: counted memetic GA ``Core-GA-TSP-Memetic-2opt`` (accounting contract).

Population initialization is the atomic phase of C-16a (population_size evaluations);
then a budgeted 2-opt runs on every chromosome with its known cost, the generations run
as in C-16a, and a final budgeted 2-opt runs once on the best chromosome with its known
cost. Every candidate tour of every phase goes through the shared counter; a polish stops
without overshoot when the budget ends. There is no periodic polish.

These tests run before the catalog promotion: they build the executor through
``registry_setup._make_canonical_ga_executor`` and do not use the capability claims.

Numbers used below (7 nodes, one 2-opt iteration scans 21 candidate tours):
    initialization 6, initial polish 6 x 21 = 126, generation 4 (offspring), final polish 21
    -> two generations complete at 6 + 126 + 8 = 140 and the final polish at 161.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from academic_benchmark.core import registry_setup
from academic_benchmark.engine_core import AlgorithmRegistry, ProblemInstance
from academic_benchmark.fairness import FairComparisonManifest, FairnessValidationError
from academic_benchmark.native_protocol import NativeComparisonManifest

MEMETIC_ID = "Core-GA-TSP-Memetic-2opt"
POP = 6
ELITE = 2
OFFSPRING = POP - ELITE
PAIRS = 21  # 2-opt candidate tours of one iteration on 7 nodes
INIT_POLISH = POP * PAIRS  # one iteration per chromosome
GENERATIONS = 2
BEFORE_FINAL = POP + INIT_POLISH + GENERATIONS * OFFSPRING  # 140
COMPLETE = BEFORE_FINAL + PAIRS  # 161
BASE_SEED = 411

SYMMETRIC_7 = [
    [0.0, 4.0, 8.0, 7.0, 3.0, 6.0, 5.0],
    [4.0, 0.0, 5.0, 9.0, 6.0, 4.0, 7.0],
    [8.0, 5.0, 0.0, 2.0, 7.0, 3.0, 6.0],
    [7.0, 9.0, 2.0, 0.0, 4.0, 5.0, 8.0],
    [3.0, 6.0, 7.0, 4.0, 0.0, 8.0, 2.0],
    [6.0, 4.0, 3.0, 5.0, 8.0, 0.0, 9.0],
    [5.0, 7.0, 6.0, 8.0, 2.0, 9.0, 0.0],
]
ASYMMETRIC_7 = [
    [0.0, 2.0, 9.0, 7.0, 6.0, 5.0, 8.0],
    [8.0, 0.0, 3.0, 9.0, 2.0, 7.0, 4.0],
    [5.0, 6.0, 0.0, 2.0, 8.0, 4.0, 9.0],
    [4.0, 7.0, 6.0, 0.0, 2.0, 9.0, 3.0],
    [9.0, 3.0, 7.0, 8.0, 0.0, 2.0, 6.0],
    [3.0, 8.0, 5.0, 4.0, 6.0, 0.0, 7.0],
    [6.0, 5.0, 4.0, 3.0, 9.0, 8.0, 0.0],
]
MATRICES = {"symmetric": SYMMETRIC_7, "asymmetric": ASYMMETRIC_7}


@dataclass
class _Problem:
    name: str
    problem_type: str
    dist_matrix: list[list[float]]
    optimal: float | None = None
    is_time_matrix: bool = False

    @property
    def dimension(self) -> int:
        return len(self.dist_matrix)


SYMMETRIC_TSP = _Problem("c16c-ga-memetic-symmetric-tsp-7", "tsp", SYMMETRIC_7)
DIRECTED_ATSP = _Problem("c16c-ga-memetic-directed-atsp-7", "atsp", ASYMMETRIC_7)
PROBLEMS = {"symmetric": SYMMETRIC_TSP, "asymmetric": DIRECTED_ATSP}

MEMETIC_PARAMS = {
    "population_size": POP,
    "max_iterations": GENERATIONS,
    "max_no_improvement": 3,
    "crossover_rate": 0.85,
    "mutation_rate": 0.15,
    "elite_count": ELITE,
    "tournament_size": 3,
    "initial_polish_iters": 1,
    "final_polish_iters": 1,
}
POLISH_KEYS = ("initial_polish_iters", "final_polish_iters")
EXPECTED_POLICY_FLAGS = {
    "enabled": True, "initial": True, "periodic": False, "final": True, "operator": "2-opt",
}


def _directed_cost(route, matrix):
    return sum(matrix[node][route[(i + 1) % len(route)]] for i, node in enumerate(route))


def _executor():
    return registry_setup._make_canonical_ga_executor(MEMETIC_ID, memetic=True)


def _fixed_params(budget, **overrides):
    return {
        **MEMETIC_PARAMS, **overrides,
        "fair_comparison": {
            "evaluation_budget": budget, "base_seed": BASE_SEED,
            "protocol_version": "uniride-fair-tsp-v2",
            "comparison_regime": "fixed_evaluation_budget",
        },
    }


def _native_params(**overrides):
    return {
        **MEMETIC_PARAMS, **overrides,
        "native_comparison": {
            "base_seed": BASE_SEED, "protocol_version": "uniride-native-tsp-v1",
            "comparison_regime": "algorithm_native_termination",
        },
    }


@pytest.fixture
def counted(monkeypatch):
    """Independent count of complete-tour objective evaluations.

    Counts every call of the solver's own tour-length function and every call of the
    budgeted search's cost function, without reading any budget counter.
    """
    from uniride_core.algorithms import objective_budget
    from uniride_core.algorithms.tsp_matrix_metaheuristics import GAOptimizer

    calls = {"n": 0}
    real_cost = objective_budget.closed_tour_cost
    real_fast = GAOptimizer._tour_length_fast

    def cost(route, matrix):
        calls["n"] += 1
        return real_cost(route, matrix)

    def fast(self, tour):
        calls["n"] += 1
        return real_fast(self, tour)

    monkeypatch.setattr(objective_budget, "closed_tour_cost", cost)
    monkeypatch.setattr(GAOptimizer, "_tour_length_fast", fast)
    return calls


def _solve(matrix, **overrides):
    from uniride_core.algorithms.tsp_matrix_metaheuristics import GAOptimizer

    values = dict(
        population_size=POP, max_iterations=GENERATIONS, max_no_improvement=1000,
        crossover_rate=0.85, mutation_rate=0.15, elite_count=ELITE, tournament_size=3,
        random_seed=17, polish_enabled=True, initial_polish_iters=1, final_polish_iters=1,
    )
    values.update(overrides)
    return GAOptimizer(**values).solve_with_matrix(
        matrix, recalculate=False, closed_tsp=True
    )


# ----- solver level: independent count, budget never exceeded, boundary triplets -----

@pytest.mark.parametrize("kind", sorted(MATRICES))
def test_objective_evaluations_equal_independent_count_and_never_exceed_budget(kind, counted):
    matrix = MATRICES[kind]
    for budget in (POP + 1, 20, 26, 27, 28, 100, 139, 140, 150, 160, 161, 162, 400):
        counted["n"] = 0
        result = _solve(matrix, evaluation_budget=budget)
        stats = result.extra_stats
        assert stats["objective_evaluations"] == counted["n"], budget
        assert stats["objective_evaluations"] <= budget, budget
        phases = stats["polish_evaluations"]
        assert phases["periodic"] == 0
        assert stats["objective_evaluations"] == (
            POP + sum(phases.values()) + result.iterations * OFFSPRING
        ), budget
    counted["n"] = 0
    result = _solve(matrix, evaluation_budget=None)
    assert result.extra_stats["objective_evaluations"] == counted["n"] == COMPLETE


@pytest.mark.parametrize("kind", sorted(MATRICES))
@pytest.mark.parametrize("budget", [POP + PAIRS - 1, POP + PAIRS, POP + PAIRS + 1])
def test_boundary_triplet_inside_the_initial_polish(kind, budget, counted):
    """One below, exactly at and one above the 22nd candidate of the initial polish."""
    result = _solve(MATRICES[kind], evaluation_budget=budget)
    stats = result.extra_stats
    assert stats["objective_evaluations"] == counted["n"] == budget
    assert stats["budget_terminated"] is True
    assert stats["termination_reason"] == "evaluation_budget_exhausted"
    assert result.iterations == 0
    assert stats["polish_evaluations"] == {"initial": budget - POP, "periodic": 0, "final": 0}
    assert stats["polish_executed"]["final"] == 0


@pytest.mark.parametrize("kind", sorted(MATRICES))
@pytest.mark.parametrize(
    ("budget", "evaluations", "terminated"),
    [
        (COMPLETE - 1, COMPLETE - 1, True),   # final polish stops one candidate short
        (COMPLETE, COMPLETE, False),          # exactly what the final polish needs
        (COMPLETE + 1, COMPLETE, False),      # one unit left over, never used
    ],
)
def test_boundary_triplet_inside_the_final_polish(kind, budget, evaluations, terminated, counted):
    result = _solve(MATRICES[kind], evaluation_budget=budget)
    stats = result.extra_stats
    assert stats["objective_evaluations"] == counted["n"] == evaluations
    assert stats["budget_terminated"] is terminated
    assert result.iterations == GENERATIONS
    # the known cost of the best chromosome is not re-counted: 20 or 21 candidates only
    assert stats["polish_evaluations"]["final"] == evaluations - BEFORE_FINAL
    assert stats["polish_evaluations"]["initial"] == INIT_POLISH
    assert stats["termination_reason"] == (
        "evaluation_budget_exhausted" if terminated else "max_iterations"
    )


@pytest.mark.parametrize("kind", sorted(MATRICES))
def test_memetic_fixed_budget_equal_to_the_population_is_refused_before_any_evaluation(
    kind, counted
):
    """B == population_size cannot start the initial polish: refused, nothing evaluated."""
    with pytest.raises(ValueError, match="population initialization"):
        _solve(MATRICES[kind], evaluation_budget=POP)
    assert counted["n"] == 0
    with pytest.raises(ValueError, match="population initialization"):
        _executor()(PROBLEMS[kind], _fixed_params(POP), seed=1, run_idx=0)
    assert counted["n"] == 0


@pytest.mark.parametrize("kind", sorted(MATRICES))
def test_memetic_fixed_budget_of_population_plus_one_gives_a_valid_row(kind, counted):
    problem = PROBLEMS[kind]
    manifest = FairComparisonManifest.from_value(_fixed_params(POP + 1)["fair_comparison"])
    row = _executor()(problem, _fixed_params(POP + 1), seed=1, run_idx=0)
    manifest.validate_result(row)
    assert row.evaluations == row.objective_evaluations == counted["n"] == POP + 1
    assert row.iterations == 0
    assert row.budget_terminated is True
    assert row.termination_reason == "evaluation_budget_exhausted"
    assert row.polish_policy["initial"] is True and row.polish_policy["final"] is False
    assert row.polish_policy["evaluations"] == {"initial": 1, "periodic": 0, "final": 0}


def test_pure_ga_still_accepts_a_budget_equal_to_the_population():
    from uniride_core.algorithms.tsp_matrix_metaheuristics import GAOptimizer

    result = GAOptimizer(
        population_size=POP, elite_count=ELITE, random_seed=3, evaluation_budget=POP
    ).solve_with_matrix(SYMMETRIC_7, recalculate=False, closed_tsp=True)
    assert result.extra_stats["objective_evaluations"] == POP
    assert result.extra_stats["termination_reason"] == "evaluation_budget_exhausted"


@pytest.mark.parametrize("protocol", ["fixed", "native"])
def test_initialization_policy_follows_the_executed_initial_polish(protocol, monkeypatch):
    """The label is derived from polish_policy.initial, not from the memetic flag.

    With the initial polish switched off inside the solver, the row must report
    initial False and the plain initialization policy (the native validator enforces the
    same pairing).
    """
    from uniride_core.algorithms.tsp_matrix_metaheuristics import GAOptimizer

    monkeypatch.setattr(GAOptimizer, "polish_initial_population", lambda self, population: False)
    params = _fixed_params(COMPLETE) if protocol == "fixed" else _native_params()
    row = _executor()(SYMMETRIC_TSP, params, seed=1, run_idx=0)
    assert row.polish_policy["initial"] is False
    assert row.polish_policy["final"] is True
    assert row.initialization_policy == "paired_seed_random_population_all_nodes"


def test_solver_rejects_memetic_without_any_polish_and_pure_default_is_unchanged():
    from uniride_core.algorithms.tsp_matrix_metaheuristics import GAOptimizer

    with pytest.raises(ValueError, match="polish"):
        GAOptimizer(population_size=POP, polish_enabled=True)
    pure = GAOptimizer(population_size=POP, elite_count=ELITE, max_iterations=2, random_seed=3)
    assert pure.polish_enabled is False
    result = pure.solve_with_matrix(SYMMETRIC_7, recalculate=False, closed_tsp=True)
    assert result.extra_stats["variant"] == "pure"
    assert result.extra_stats["polish_executed"] == {"initial": 0, "periodic": 0, "final": 0}
    assert result.extra_stats["objective_evaluations"] == POP + 2 * OFFSPRING
    assert result.params["memetic"] is False


# ----- executor level: strict parameters, rows, replay, directed cost -----

@pytest.mark.parametrize("protocol", ["fixed", "native"])
@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: {**p, "initial_polish_iters": 0},
        lambda p: {**p, "final_polish_iters": 0},
        lambda p: {**p, "initial_polish_iters": -1},
        lambda p: {**p, "final_polish_iters": True},
        lambda p: {**p, "initial_polish_iters": 1.0},
        lambda p: {k: v for k, v in p.items() if k != "initial_polish_iters"},
        lambda p: {k: v for k, v in p.items() if k != "final_polish_iters"},
        lambda p: {k: v for k, v in p.items() if k not in POLISH_KEYS},
        lambda p: {**p, "polish_interval": 5},
        lambda p: {**p, "polish_iters": 5},
    ],
    ids=["init0", "final0", "neg", "bool", "float", "no-init", "no-final", "no-polish",
         "periodic-key", "foreign-key"],
)
def test_zero_missing_or_unknown_polish_parameters_are_rejected_before_any_evaluation(
    protocol, mutate, counted
):
    params = _fixed_params(COMPLETE) if protocol == "fixed" else _native_params()
    protocol_key = "fair_comparison" if protocol == "fixed" else "native_comparison"
    bad = mutate({k: v for k, v in params.items() if k != protocol_key})
    bad[protocol_key] = params[protocol_key]
    with pytest.raises(ValueError):
        _executor()(SYMMETRIC_TSP, bad, seed=1, run_idx=0)
    assert counted["n"] == 0


@pytest.mark.parametrize("kind", sorted(PROBLEMS))
def test_fixed_row_is_memetic_with_derived_polish_policy_and_replays(kind, counted):
    problem = PROBLEMS[kind]
    manifest = FairComparisonManifest.from_value(_fixed_params(COMPLETE)["fair_comparison"])
    first = _executor()(problem, _fixed_params(COMPLETE), seed=987_654, run_idx=0)
    replay = _executor()(problem, _fixed_params(COMPLETE), seed=123_456, run_idx=0)
    manifest.validate_result(first)

    assert first.algorithm == first.algorithm_id == MEMETIC_ID
    assert first.algorithm_family == "GA"
    assert first.variant == "memetic_2opt"
    assert first.seed == manifest.paired_seed(problem.name, 0)
    assert first.initialization_policy == (
        "paired_seed_random_population_all_nodes_with_initial_2opt"
    )
    assert first.evaluations == first.objective_evaluations == COMPLETE
    assert first.budget_terminated is False
    assert first.termination_reason == "max_iterations"
    assert "polish=python" in first.execution_backend
    flags = {key: first.polish_policy[key] for key in EXPECTED_POLICY_FLAGS}
    assert flags == EXPECTED_POLICY_FLAGS
    assert first.polish_policy["executed"] == {"initial": POP, "periodic": 0, "final": 1}
    assert first.polish_policy["evaluations"] == {
        "initial": INIT_POLISH, "periodic": 0, "final": PAIRS,
    }
    # independent count over both runs
    assert counted["n"] == 2 * COMPLETE

    route = [node - 1 for node in first.tour]
    assert sorted(route) == list(range(len(problem.dist_matrix)))
    assert first.tour_cost == pytest.approx(_directed_cost(route, problem.dist_matrix))
    assert first.objective_cost == pytest.approx(_directed_cost(route, problem.dist_matrix))

    for field in ("tour", "tour_cost", "objective_evaluations", "iterations",
                  "termination_reason", "polish_policy", "execution_backend", "seed"):
        assert getattr(replay, field) == getattr(first, field), field


@pytest.mark.parametrize("kind", sorted(PROBLEMS))
def test_a_ga_memetic_row_never_reports_periodic_polish(kind):
    problem = PROBLEMS[kind]
    for budget in (POP + 1, 26, 27, 100, 139, 140, 141, 160, COMPLETE, 300):
        row = _executor()(problem, _fixed_params(budget), seed=1, run_idx=0)
        assert row.polish_policy["periodic"] is False, budget
        assert row.polish_policy["executed"]["periodic"] == 0, budget
        assert row.polish_policy["evaluations"]["periodic"] == 0, budget
        assert row.evaluations <= budget


def test_gwo_hho_memetic_keep_their_own_schedule():
    """The policy builder derives each flag from the executed counts of that solver."""
    stats = {
        "polish_executed": {"initial": 3, "periodic": 2, "final": 1},
        "polish_evaluations": {"initial": 30, "periodic": 20, "final": 10},
    }
    policy = registry_setup._executed_polish_policy(stats, True)
    assert (policy["initial"], policy["periodic"], policy["final"]) == (True, True, True)
    ga_stats = {
        "polish_executed": {"initial": 3, "periodic": 0, "final": 1},
        "polish_evaluations": {"initial": 30, "periodic": 0, "final": 10},
    }
    policy = registry_setup._executed_polish_policy(ga_stats, True)
    assert (policy["initial"], policy["periodic"], policy["final"]) == (True, False, True)


@pytest.mark.parametrize("kind", sorted(PROBLEMS))
def test_native_path_counts_every_polish_evaluation(kind, counted):
    problem = PROBLEMS[kind]
    manifest = NativeComparisonManifest.from_value(_native_params()["native_comparison"])
    row = _executor()(problem, _native_params(), seed=5, run_idx=0)
    manifest.validate_result(row)
    assert row.variant == "memetic_2opt"
    assert row.evaluation_budget is None and row.budget_terminated is False
    assert row.evaluations == counted["n"]
    assert row.evaluations == POP + INIT_POLISH + row.iterations * OFFSPRING + PAIRS
    assert {key: row.polish_policy[key] for key in EXPECTED_POLICY_FLAGS} == EXPECTED_POLICY_FLAGS
    assert row.polish_policy["evaluations"] == {
        "initial": INIT_POLISH, "periodic": 0, "final": PAIRS,
    }
    assert "polish=python" in row.execution_backend
    route = [node - 1 for node in row.tour]
    assert row.tour_cost == pytest.approx(_directed_cost(route, problem.dist_matrix))


def test_validators_reject_a_ga_memetic_row_that_misreports_itself():
    fixed = _executor()(SYMMETRIC_TSP, _fixed_params(COMPLETE), seed=1, run_idx=0)
    fair_manifest = FairComparisonManifest.from_value(_fixed_params(COMPLETE)["fair_comparison"])
    fair_manifest.validate_result(fixed)
    fixed.variant = "pure"
    with pytest.raises(FairnessValidationError):
        fair_manifest.validate_result(fixed)

    native = _executor()(SYMMETRIC_TSP, _native_params(), seed=1, run_idx=0)
    native_manifest = NativeComparisonManifest.from_value(_native_params()["native_comparison"])
    native.initialization_policy = "paired_seed_random_population_all_nodes"
    with pytest.raises(FairnessValidationError, match="initialization_policy"):
        native_manifest.validate_result(native)


# ----- the pure GA is unchanged and stays the target of Numba-GA -----

def test_pure_core_ga_rejects_polish_keys_and_keeps_the_no_polish_policy():
    from academic_benchmark.engine_core import AlgorithmRegistry

    pure = AlgorithmRegistry.get_executor("Core-GA-TSP")
    pure_params = {k: v for k, v in _fixed_params(POP + OFFSPRING).items()
                   if k not in POLISH_KEYS}
    row = pure(SYMMETRIC_TSP, pure_params, seed=1, run_idx=0)
    assert row.variant == "pure"
    assert row.polish_policy == {
        "enabled": False, "initial": False, "periodic": False, "final": False,
        "operator": None,
    }
    assert row.evaluations == POP + OFFSPRING
    with pytest.raises(ValueError, match="schema mismatch"):
        pure(SYMMETRIC_TSP, _fixed_params(COMPLETE), seed=1, run_idx=0)


def test_numba_ga_alias_stays_on_the_pure_ga_and_no_alias_targets_the_memetic_id():
    from academic_benchmark.core.algorithm_resolution import CLI_ALIAS_TARGETS

    assert CLI_ALIAS_TARGETS["Numba-GA"] == "Core-GA-TSP"
    assert MEMETIC_ID not in CLI_ALIAS_TARGETS.values()


# ----- routing identity (the C-16a routing bug must not repeat) -----

TINY_CVRP = ProblemInstance(
    name="c16c-tiny-cvrp",
    dimension=4,
    coordinates=[],
    problem_type="cvrp",
    dist_matrix=[[0, 10, 10, 10], [10, 0, 1, 1], [10, 1, 0, 1], [10, 1, 1, 0]],
    demands=[0, 1, 1, 1],
    capacities=[2],
    capacity=2,
)


def test_memetic_routing_call_is_refused_before_any_engine_is_built(monkeypatch):
    # Gate C follow-up (owner 2026-10-21): the memetic ID is TSP/ATSP only. It used to build
    # the Matrix-GA-TSP-legacy engine here and label the routing row with the memetic ID.
    built: list[str] = []
    monkeypatch.setattr(registry_setup, "create_matrix_engine", lambda name: built.append(name))
    executor = AlgorithmRegistry.get_executor(MEMETIC_ID)
    with pytest.raises(registry_setup.CoreRoutingRefusedError, match="CVRP-Core-GA-TSP"):
        executor(TINY_CVRP, {}, 42, 0)
    assert built == []


def test_cvrp_alias_of_the_ga_builds_the_ga_engine_under_its_own_name(monkeypatch):
    real_create = registry_setup.create_matrix_engine
    built: list[tuple[str, str]] = []

    def recording_create(name):
        engine = real_create(name)
        built.append((name, type(engine).__name__))
        return engine

    monkeypatch.setattr(registry_setup, "create_matrix_engine", recording_create)
    result = AlgorithmRegistry.get_executor("CVRP-Core-GA-TSP")(TINY_CVRP, {}, 42, 0)
    assert built == [("Matrix-GA-TSP-legacy", "TSPMetaMatrixEngine")]
    assert result.algorithm == "CVRP-Core-GA-TSP"
    assert result.routes


# ----- pilot allowlists: an optional, strictly validated member -----

def _pilot_blocks():
    alns = {
        "max_iterations": 8, "max_no_improvement": 3, "remove_ratio": 0.34,
        "min_remove": 2, "segment_length": 2, "weight_update_factor": 0.8,
        "use_sa": True, "sa_start_temp": 5.0, "sa_cooling_rate": 0.9,
    }
    return {
        "Core-GWO-TSP-Pure": {"pack_size": 4, "max_iterations": 2, "max_no_improvement": 10},
        "Core-HHO-TSP-Pure": {"hawks": 4, "max_iterations": 2, "dive_count": 0,
                              "max_no_improvement": 10},
        "Core-TwoOpt-TSP": {"max_iterations": 20, "first_improvement": False},
        "Core-ThreeOpt-TSP": {"max_iterations": 20, "first_improvement": False, "window": 4},
        "Core-OrOpt-TSP": {"max_iterations": 3, "first_improvement": False, "window": 3},
        "ALNS-TSP": alns,
    }


def _write(tmp_path, name, value):
    import json

    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_fair_pilot_accepts_the_memetic_block_only_with_nonzero_polish(tmp_path):
    from academic_benchmark.fair_pilot import FairPilotError, load_fair_pilot_config

    def config(block):
        return {
            "protocol_version": "uniride-fair-tsp-v2",
            "comparison_regime": "fixed_evaluation_budget",
            "problems": ["tiny-tsp", "tiny-atsp"],
            "algorithms": {k: v for k, v in {**_pilot_blocks(), MEMETIC_ID: block}.items() if k != "Core-OrOpt-TSP"},
            "runs": 1, "evaluation_budget": 400, "base_seed": 17,
            "budget_policy": "atomic_upper_bound_v1", "workers": 1,
            "replay_replicates": [], "allow_repository_output": False, "overwrite": False,
        }

    loaded = load_fair_pilot_config(_write(tmp_path, "ok.json", config(dict(MEMETIC_PARAMS))))
    assert loaded.algorithms[MEMETIC_ID] == MEMETIC_PARAMS
    for bad in (
        {**MEMETIC_PARAMS, "initial_polish_iters": 0},
        {**MEMETIC_PARAMS, "final_polish_iters": 0},
        {k: v for k, v in MEMETIC_PARAMS.items() if k != "final_polish_iters"},
        {**MEMETIC_PARAMS, "polish_interval": 5},
    ):
        with pytest.raises(FairPilotError, match=MEMETIC_ID):
            load_fair_pilot_config(_write(tmp_path, "bad.json", config(bad)))


def test_native_pilot_accepts_the_memetic_block_only_with_nonzero_polish(tmp_path):
    from academic_benchmark.native_pilot import NativePilotError, load_native_pilot_config

    def config(block):
        return {
            "protocol_version": "uniride-native-tsp-v1",
            "comparison_regime": "algorithm_native_termination",
            "problems": ["tiny-tsp", "tiny-atsp"],
            "algorithms": {**_pilot_blocks(), MEMETIC_ID: block},
            "runs": 1, "base_seed": 71, "workers": 1, "replay_replicates": [0],
            "allow_repository_output": False, "overwrite": False,
        }

    loaded = load_native_pilot_config(_write(tmp_path, "ok.json", config(dict(MEMETIC_PARAMS))))
    assert loaded.algorithms[MEMETIC_ID] == MEMETIC_PARAMS
    for bad in (
        {**MEMETIC_PARAMS, "initial_polish_iters": 0},
        {**MEMETIC_PARAMS, "final_polish_iters": 0},
        {k: v for k, v in MEMETIC_PARAMS.items() if k != "initial_polish_iters"},
        {**MEMETIC_PARAMS, "polish_interval": 5},
    ):
        with pytest.raises(NativePilotError, match=MEMETIC_ID):
            load_native_pilot_config(_write(tmp_path, "bad.json", config(bad)))
