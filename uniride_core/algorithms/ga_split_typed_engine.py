"""Typed GA-Split engine (heterogeneous fleet, WP3).

See ``docs/designs/HETEROGENEOUS_FLEET_DESIGN.md`` sections 3.1 and 3.3.

A GA over giant tours whose fitness comes from ``decode_typed``: the key is
``(infeasible, routes of the minimised type, cost)``.  The loop body duplicates
``ga_split_engine.solve_ga_split`` on purpose (that module must keep a zero
diff, parity gate P1); it reuses the exported GA helpers and the same ``rng``
discipline, so with one type and no quota the RNG stream, the routes and the
generation count equal ``solve_ga_split`` (parity gate P4).

Inner objective (CX-03, decisions O05/H01/H04): the inner split decode is cost-only
(``decode_typed`` without ``minimize_type``, exactly the untyped DP) when there
is one type and no quota (quota_type or quota unset, matching the decoder's
quota tracking, which needs both); that is what makes P4 hold on nonmetric matrices.
With two or more types or a quota the inner decode is count-first (routes of
``minimize_type``, then cost), which is intended for borrowed-vehicle
minimisation.  The two inner objectives differ by design.  The outer GA
ranking key is the same in both cases.

Two differences from ``solve_ga_split`` are deliberate: an infeasible tour is
infeasible (the typed decoder has no singleton fallback) and only the plain
capacity/ride/tour decode exists (no time windows).

Nothing in the academic stack imports this module (parity gate P2).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from uniride_core.algorithms.ga_split_engine import (
    GAIndividual,
    diversify_population,
    educate_individual,
    evolve_population,
    initialize_population,
)
from uniride_core.algorithms.objective_rank import fitness_from_key
from uniride_core.algorithms.typed_split_decoder import (
    TypedSplitResult,
    VehicleType,
    decode_typed,
)

_WORST_KEY: Tuple[int, int, float] = (1, 999, float("inf"))
BASELINE_LABEL = "all_large"


@dataclass
class TypedGASolution:
    """Result of the typed GA-Split search."""

    best_individual: GAIndividual
    final_result: TypedSplitResult
    generations: int


@dataclass
class MenuOption:
    """One entry of the per-wave option menu."""

    label: str  # "q0".."q3" or BASELINE_LABEL
    quota: Optional[int]  # large-route quota; None for the all-large baseline
    solution: Optional[TypedGASolution]
    reason: Optional[str] = None  # set when no feasible solution exists

    @property
    def feasible(self) -> bool:
        return self.solution is not None and self.solution.final_result.feasible


def inner_minimize_type(
    types: Sequence[VehicleType],
    minimize_type: str,
    quota_type: Optional[str],
    quota: Optional[int],
) -> Optional[str]:
    """Inner split objective: ``None`` (cost-only) for one type and no quota.

    "No quota" means ``quota_type`` or ``quota`` unset: ``decode_typed`` only
    tracks a quota when both are set.
    """
    if len(types) == 1 and (quota_type is None or quota is None):
        return None
    return minimize_type


def _key(individual: GAIndividual) -> Tuple[int, int, float]:
    return individual.obj_key or _WORST_KEY


def _evaluate(
    individual: GAIndividual,
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
    demands: Dict[str, Tuple[int, int]],
    types: Sequence[VehicleType],
    minimize_type: str,
    quota_type: Optional[str],
    quota: Optional[int],
    is_asymmetric: bool,
    direction: Any,
) -> GAIndividual:
    result = decode_typed(
        individual.chromosome,
        depot,
        distance_matrix,
        demands,
        types,
        minimize_type=inner_minimize_type(types, minimize_type, quota_type, quota),
        quota_type=quota_type,
        quota=quota,
        is_asymmetric=is_asymmetric,
        direction=direction,
    )
    if not result.feasible or not math.isfinite(result.total_cost):
        return GAIndividual(
            chromosome=individual.chromosome,
            fitness=fitness_from_key(_WORST_KEY),
            total_cost=float("inf"),
            num_vehicles=999,
            obj_key=_WORST_KEY,
        )
    key = (0, int(result.routes_by_type[minimize_type]), float(result.total_cost))
    return GAIndividual(
        chromosome=individual.chromosome,
        fitness=fitness_from_key(key),
        total_cost=float(result.total_cost),
        num_vehicles=result.num_vehicles,
        obj_key=key,
    )


def solve_ga_split_typed(
    waypoints: List[str],
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
    demands: Dict[str, Tuple[int, int]],
    types: Sequence[VehicleType],
    config: Mapping[str, Any],
    rng: random.Random,
    *,
    minimize_type: str,
    quota_type: Optional[str] = None,
    quota: Optional[int] = None,
    direction: Any = "pickup",
    is_asymmetric: bool = False,
) -> TypedGASolution:
    """Run the typed GA-Split and return the final typed decode."""
    types = list(types)
    if minimize_type not in {t.id for t in types}:
        raise ValueError(f"minimize_type {minimize_type!r} is not a declared vehicle type")

    def evaluate(individual: GAIndividual) -> GAIndividual:
        return _evaluate(
            individual, depot, distance_matrix, demands, types,
            minimize_type, quota_type, quota, is_asymmetric, direction,
        )

    def evaluate_all(population: List[GAIndividual]) -> List[GAIndividual]:
        return [evaluate(individual) for individual in population]

    population = initialize_population(waypoints, config, rng, distance_matrix)
    population = evaluate_all(population)

    best = min(population, key=_key)
    no_improvement = 0
    generation = 0

    for generation in range(int(config.get("max_iterations", 100))):
        population = evolve_population(population, config, rng)
        population = evaluate_all(population)

        current_best = min(population, key=_key)
        if generation % int(config.get("local_search_interval", 10)) == 0:
            current_best = educate_individual(
                current_best,
                depot,
                distance_matrix,
                str(config.get("local_search_type", "two_opt")),
            )
            current_best = evaluate(current_best)

        if _key(current_best) < _key(best):
            best = current_best
            no_improvement = 0
        else:
            no_improvement += 1

        if no_improvement >= int(config.get("max_no_improvement", 25)):
            break

        if no_improvement >= int(config.get("diversify_threshold", 30)):
            population = diversify_population(population, rng)
            population = evaluate_all(population)
            no_improvement = 0

    final_result = decode_typed(
        best.chromosome,
        depot,
        distance_matrix,
        demands,
        types,
        minimize_type=inner_minimize_type(types, minimize_type, quota_type, quota),
        quota_type=quota_type,
        quota=quota,
        is_asymmetric=is_asymmetric,
        direction=direction,
    )
    return TypedGASolution(best_individual=best, final_result=final_result, generations=generation)


def solve_typed_menu(
    waypoints: List[str],
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
    demands: Dict[str, Tuple[int, int]],
    types: Sequence[VehicleType],
    config: Mapping[str, Any],
    seed: int,
    *,
    minimize_type: str,
    quota_type: str,
    max_quota: int = 3,
    direction: Any = "pickup",
    is_asymmetric: bool = False,
) -> List[MenuOption]:
    """Per-wave option menu: q = 0..min(max_quota, n) plus the all-large baseline.

    Every option is an independent ``solve_ga_split_typed`` call started from a
    fresh ``random.Random(seed)`` (decision D05: the seed is the caller's).  An
    option without a feasible typed split is kept with ``solution=None`` and a
    reason, so that infeasible quotas are recorded rather than silently absent.
    The baseline solves the quota type alone (scenario-A routes, labelled
    ``all_large``); the day-level master assigns labels later.
    """
    types = list(types)
    by_id = {t.id: t for t in types}
    if quota_type not in by_id or minimize_type not in by_id:
        raise ValueError("quota_type and minimize_type must name a declared type")
    if max_quota < 0:
        raise ValueError("max_quota must be >= 0")
    options: List[MenuOption] = []
    for q in range(0, min(max_quota, len(waypoints)) + 1):
        solution = solve_ga_split_typed(
            waypoints, depot, distance_matrix, demands, types, config,
            random.Random(seed),
            minimize_type=minimize_type, quota_type=quota_type, quota=q,
            direction=direction, is_asymmetric=is_asymmetric,
        )
        feasible = solution.final_result.feasible
        options.append(MenuOption(
            label=f"q{q}", quota=q,
            solution=solution if feasible else None,
            reason=None if feasible else "NO_FEASIBLE_TYPED_SPLIT",
        ))
    large = by_id[quota_type]
    baseline = solve_ga_split_typed(
        waypoints, depot, distance_matrix, demands, [large], config,
        random.Random(seed),
        minimize_type=large.id, direction=direction, is_asymmetric=is_asymmetric,
    )
    feasible = baseline.final_result.feasible
    options.append(MenuOption(
        label=BASELINE_LABEL, quota=None,
        solution=baseline if feasible else None,
        reason=None if feasible else "NO_FEASIBLE_TYPED_SPLIT",
    ))
    return options


__all__ = [
    "BASELINE_LABEL",
    "MenuOption",
    "TypedGASolution",
    "solve_ga_split_typed",
    "solve_typed_menu",
]
