# Sprint 2: Discovered Issues & Technical Debt

This document lists bugs and technical debt discovered during the final verification of Sprint 2 (IE Resource Engine). These issues should be addressed in Sprint 3 or a dedicated stabilization turn.

## 1. Logic Bugs

### [ga_split_strategy.py](file:///c:/Users/yekta/Masa%C3%BCst%C3%BC/AiCode/FirebaseUniRide/UniRide/optimizer_api/strategies/ga_split_strategy.py) - `_crossover_cx2`
> [!WARNING]
> The Cycle Crossover (CX2) implementation (lines 645-686) has a logic error in position mapping.
- **Problem**: It uses `child[cycle_start + j] = val`, which assumes sequential placement of cycle elements. In a true Cycle Crossover, elements should maintain their indices from the parent.
- **Impact**: Potential invalid permutations or index out of bounds if the cycle length exceeds the remaining space from `cycle_start`.

### [resource_profiler.py](file:///c:/Users/yekta/Masa%C3%BCst%C3%BC/AiCode/FirebaseUniRide/UniRide/optimizer_api/utils/resource_profiler.py) - `suggest_time_shifts`
- **Problem**: The suggestion logic (lines 444-511) is relatively static. It only checks ±60 minutes for "excess" demand.
- **Impact**: It doesn't account for individual student constraints (e.g., student A can shift 30 min, student B cannot shift at all).

## 2. Technical Debt

### [main.py](file:///c:/Users/yekta/Masa%C3%BCst%C3%BC/AiCode/FirebaseUniRide/UniRide/optimizer_api/main.py) - `calculate_vehicles` vs `optimize_route`
- **Problem**: `calculate_vehicles` is currently a direct alias for `optimize_route`.
- **Debt**: It should eventually be decoupled if the "Vehicle Calculator" (Sandbox) requires specialized constraints different from standard optimization.

### Frontend: IE Dashboard Data Mapping
- **Problem**: Some metrics in `src/app/api/calculate-vehicles/route.ts` are re-calculated (e.g., `swCapacityNeeded`) instead of being taken directly from the Python IE Engine output.
- **Debt**: Logic duplication between Python and TypeScript.

## 3. Performance

### Holistic Solvers Fallback
- **Problem**: `vroom` and `pyvrp` fall back to `ortools` on import error.
- **Impact**: On Windows machines without C++ build tools, OR-Tools will always be the fallback, which is fine but should be communicated better in the UI.
