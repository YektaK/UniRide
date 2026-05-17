# State-of-the-Art Algorithm Candidates for TSP — Research Findings

> **Date:** 2026-05-15
> **Source:** Dokeroglu et al. (2024) survey of 158 metaheuristics (2019-2024), Toaza & Esztergár-Kiss (2023) review of 120 TSP metaheuristics, plus targeted literature searches.
> **Purpose:** Identify novel metaheuristic algorithms NOT yet applied to TSP in literature, ranked by potential for discrete combinatorial search space.

---

## 1. Methodology

### Selection Criteria
1. **Not yet applied to TSP** — confirmed via literature search (Google Scholar, ScienceDirect, IEEE Xplore, Springer)
2. **High citation impact** — evidence of algorithmic soundness
3. **Novel search mechanism** — fundamentally different from existing 15 algorithms in our framework
4. **Discrete-space adaptability** — operators that naturally map to permutation/tour representation
5. **Low parameter count** — easier DoE tuning, fewer hyperparameters
6. **Source code available** — MATLAB/Python reference implementations exist

### Current Framework Coverage (15 Algorithms)
| Engine | Algorithms |
|--------|-----------|
| Numba | 2-opt, 3-opt-bounded, Or-opt, Swap, Hybrid, GA, PSO, GWO, HHO |
| bildiri2026 | B-PSO, B-GA |
| SOTA | E2BSO-TSP, E2BSO-TSP-CPSO, R2DMA-TSP, P-AOEA-TSP |

---

## 2. Candidate Algorithms — Ranked by Discrete TSP Potential

### Rank 1: RUN (Runge Kutta Optimizer) ⭐⭐⭐⭐⭐

| Property | Value |
|----------|-------|
| **Year** | 2021 |
| **Citations** | ~1,100 |
| **Authors** | Ahmadianfar, Heidari, Gandomi, Mirjalili |
| **Paper** | "RUN: Beyond the Metaphor: An Efficient Optimization Algorithm Based on Runge Kutta Method" |
| **Journal** | Engineering Applications of Artificial Intelligence |
| **TSP in Literature** | ❌ No TSP applications found |
| **Source Code** | ✅ MATLAB (official), Python (community) |

#### Why #1 for Discrete TSP
1. **Metaphor-free** — authors explicitly critique animal-mimic "pseudo-novel" optimizers. Based on RK4 numerical method (mathematical foundation, not biology).
2. **4-stage slope evaluation** — RK4 computes k₁, k₂, k₃, k₄ slopes. In TSP, this maps naturally to evaluating 4 candidate moves per iteration (2-opt, 3-opt, swap, insert).
3. **Enhanced Solution Quality (ESQ)** — built-in mechanism to escape local optima using random perturbation + best-solution guidance. Directly applicable to TSP stagnation.
4. **Only 3 parameters** — population size, max iterations, single control factor β. Minimal DoE complexity.
5. **Strong on CEC benchmarks** — outperforms GWO, WOA, SSA, GSA on 29 CEC-2017 functions.
6. **Adaptive exploration/exploitation** — transition controlled by solution quality ranking, not iteration count.

#### Search Mechanism
```
Exploration:  X_new = X_current + SF × SM × g × (X_best - X_rbc)
Exploitation: X_new = X_best + SF × SM × g × (X_best - X_rbc)
ESQ:          X_new = X_best + rand × (X_best - X_avg) + rand × (X_r1 - X_r2)
```
Where SF = search factor, SM = slope magnitude, g = random gradient, X_rbc = random best-center.

#### Proposed TSP Adaptation
- **Solution encoding:** Permutation (tour)
- **Slope evaluation:** Replace continuous position update with permutation operators
  - k₁ → 2-opt move from current
  - k₂ → 3-opt move from k₁ result
  - k₃ → swap move from k₂ result
  - k₄ → insert move from k₃ result
- **ESQ →** Random k-opt perturbation + best-tour guidance
- **Parameters:** `pop_size: [30, 50, 80]`, `beta: [0.5, 1.0, 2.0]`, `max_iter: [200, 500, 1000]`

#### Paper Angle
"First metaphor-free metaheuristic for TSP: Runge Kutta Optimizer with discrete permutation operators"

---

### Rank 2: Chaos Game Optimization (CGO) ⭐⭐⭐⭐⭐

| Property | Value |
|----------|-------|
| **Year** | 2020 |
| **Citations** | ~770 |
| **Authors** | Talatahari, Azizi |
| **Paper** | "Chaos Game Optimization: a novel metaheuristic algorithm" |
| **Journal** | Artificial Intelligence Review (Springer) |
| **TSP in Literature** | ❌ No TSP applications found |
| **Source Code** | ✅ MATLAB (official) |

#### Why #2 for Discrete TSP
1. **Chaos theory + fractals** — based on Sierpinski triangle construction via chaos game. Completely different paradigm from all existing algorithms.
2. **Seed-based construction** — solutions built incrementally from "seeds" (like building a TSP tour city by city). Natural fit for permutation problems.
3. **Self-similarity property** — fractal structure mirrors TSP substructure (optimal subtours are self-similar at different scales).
4. **Built-in diversification** — chaos game rules inherently produce diverse solutions without explicit mutation operators.
5. **Only 2 parameters** — population size and max iterations. Simplest DoE space of any candidate.
6. **Binary variant exists** — authors published binary CGO for feature selection, proving discrete adaptability.

#### Search Mechanism
```
Seed placement:    S_i = random position in search space
Chaos game rule:   S_new = (S_old + S_seed) / 2 + chaos_factor × rand
Self-similarity:   Each seed generates sub-seeds following same rules
```

#### Proposed TSP Adaptation
- **Solution encoding:** Permutation (tour)
- **Seed →** Partial tour (subsequence of cities)
- **Chaos game rule →** Merge two partial tours by interleaving cities
- **Self-similarity →** Apply same merge rule at different tour scales (subtours → full tour)
- **Chaos factor →** Lévy flight or logistic map for controlled randomness
- **Parameters:** `pop_size: [30, 50, 80]`, `chaos_map: [logistic, tent, sine]`, `max_iter: [200, 500, 1000]`

#### Paper Angle
"Fractal-based tour construction: Chaos Game Optimization with self-similar substructure exploitation for TSP"

---

### Rank 3: Slime Mould Algorithm (SMA) ⭐⭐⭐⭐

| Property | Value |
|----------|-------|
| **Year** | 2020 |
| **Citations** | ~5,570 |
| **Authors** | Li, Chen, Liu, Heidari, Mirjalili |
| **Paper** | "Slime mould algorithm: A new method for stochastic optimization" |
| **Journal** | Future Generation Computer Systems |
| **TSP in Literature** | ❌ No TSP applications found |
| **Source Code** | ✅ MATLAB (official), Python (community) |

#### Why #3 for Discrete TSP
1. **Physarum actually solves shortest paths** — real slime mould (Physarum polycephalum) finds optimal paths in maze experiments (Nakagaki et al., Nature 2000). Biological precedent for TSP.
2. **Venation network formation** — creates optimal transport networks, directly analogous to TSP tour construction.
3. **Oscillation mechanism** — positive/negative feedback oscillation naturally balances exploration/exploitation.
4. **Weight-based adaptation** — each agent has a weight based on fitness, creating implicit elitism.
5. **Only 2 parameters** — population size and a single adaptation parameter z.

#### Search Mechanism
```
Weight:        W_i = 1 + rand × log((best_fit - fit_i) / (best_fit - worst_fit) + 1)
Position:      X_new = X_best + vb × (W × X_A - X_B)   (p < threshold)
               X_new = vc × X                           (p ≥ threshold)
Oscillation:   vb ∈ [-a, a] where a decreases over iterations
```

#### Proposed TSP Adaptation
- **Solution encoding:** Permutation (tour)
- **Weight →** Tour quality weight (better tours have higher influence)
- **Position update →** Guided 2-opt: apply 2-opt moves weighted by agent fitness
- **Oscillation →** Alternate between exploration (random k-opt) and exploitation (best-tour guided 2-opt)
- **Venation →** Build edge frequency matrix from population, select high-frequency edges
- **Parameters:** `pop_size: [30, 50, 80]`, `z: [0.03, 0.05, 0.1]`, `max_iter: [200, 500, 1000]`

#### Paper Angle
"Bio-inspired shortest path finding: Slime Mould Algorithm with venation network modeling for TSP"

---

### Rank 4: Gradient-Based Optimizer (GBO) ⭐⭐⭐⭐

| Property | Value |
|----------|-------|
| **Year** | 2020 |
| **Citations** | ~5,990 |
| **Authors** | Ahmadianfar, Heidari, Gandomi, Mirjalili |
| **Paper** | "Gradient-based optimizer: A new metaheuristic optimization algorithm" |
| **Journal** | Engineering Applications of Artificial Intelligence |
| **TSP in Literature** | ❌ No TSP applications found |
| **Source Code** | ✅ MATLAB (official) |

#### Why #4 for Discrete TSP
1. **Gradient search rule (GSR)** — uses Newton's method-inspired direction finding. In TSP, "gradient" = direction of improving moves.
2. **Local escaping operator (LEO)** — specifically designed to escape local optima. Critical for TSP where 2-opt/3-opt get stuck easily.
3. **Dual search mechanism** — combines gradient-based exploitation with population-based exploration.
4. **Binary variant exists** — Jiang et al. (2021) published 8 binary GBO variants for feature selection.
5. **3 parameters** — population size, max iterations, and one control parameter.

#### Search Mechanism
```
GSR:  X_new = X_current + rand × (X_best - X_random) × gradient_factor
LEO:  X_new = X_best + rand₁ × (X_best - X_r1) + rand₂ × (X_r1 - X_r2)
```

#### Proposed TSP Adaptation
- **Solution encoding:** Permutation (tour)
- **GSR →** Gradient = sequence of improving swap operations (greedy move selection)
- **LEO →** Random k-opt perturbation guided by best tour
- **Dual search →** Alternate between gradient-guided local search and population crossover
- **Parameters:** `pop_size: [30, 50, 80]`, `p_r: [0.3, 0.5, 0.7]` (LEO probability), `max_iter: [200, 500, 1000]`

#### Paper Angle
"Gradient-inspired combinatorial search: GBO with discrete gradient operators and local escaping for TSP"

---

### Rank 5: Artificial Protozoa Optimizer (APO) ⭐⭐⭐

| Property | Value |
|----------|-------|
| **Year** | 2024 |
| **Citations** | ~new (very recent) |
| **Authors** | Wang, Snášel, Mirjalili, Pan, Kong, Shehadeh |
| **Paper** | "Artificial Protozoa Optimizer: A novel bio-inspired metaheuristic algorithm" |
| **Journal** | Knowledge-Based Systems |
| **TSP in Literature** | ❌ No TSP applications found |
| **Source Code** | ✅ MATLAB (official) |

#### Why #5 for Discrete TSP
1. **Very recent (2024)** — zero TSP applications, maximum novelty potential.
2. **4 distinct behaviors** — foraging (autotrophic/heterotrophic), dormancy, reproduction. Each maps to different TSP operators.
3. **Outperforms 32 algorithms** on CEC-2022 benchmarks.
4. **Already tested on discrete problem** — multilevel image segmentation (discrete space with constraints).
5. **3 parameters** — population size and two control factors.

#### Search Mechanism
```
Autotrophic foraging: X_new = X_current + rand × (X_best - X_current)  (exploration)
Heterotrophic foraging: X_new = X_current + rand × (X_r1 - X_r2)       (exploration)
Dormancy:             X_new = random position                           (diversification)
Reproduction:         X_new = (X_best + X_current) / 2                  (exploitation)
```

#### Proposed TSP Adaptation
- **Solution encoding:** Permutation (tour)
- **Autotrophic →** Best-tour guided 2-opt (exploitation)
- **Heterotrophic →** Random swap between two tours (exploration)
- **Dormancy →** Random tour generation + greedy construction (diversification)
- **Reproduction →** OX crossover between best and current tour (exploitation)
- **Parameters:** `pop_size: [30, 50, 80]`, `proportion: [0.3, 0.5, 0.7]` (foraging ratio), `max_iter: [200, 500, 1000]`

#### Paper Angle
"Protozoa survival behaviors as TSP search operators: APO with four-mode optimization for combinatorial routing"

---

### Rank 6: Artificial Gorilla Troops Optimizer (GTO) ⭐⭐⭐

| Property | Value |
|----------|-------|
| **Year** | 2021 |
| **Citations** | ~995 |
| **Authors** | Abdollahzadeh, Gharehchopogh, Mirjalili |
| **Paper** | "Artificial gorilla troops optimizer: A new nature-inspired metaheuristic algorithm" |
| **Journal** | International Journal of Intelligent Systems |
| **TSP in Literature** | ❌ No TSP applications found |
| **Source Code** | ✅ MATLAB (official) |

#### Why #6 for Discrete TSP
1. **3 exploration + 2 exploitation operators** — rich operator set for diverse TSP moves.
2. **Silverback mechanism** — best solution guides population (similar to PSO gbest but with social dynamics).
3. **Migration behavior** — gorillas move to familiar/unfamiliar locations, maps to local/global search.
4. **Strong on high-dimensional problems** — good for large TSP instances (n > 500).
5. **4 parameters** — slightly more complex DoE.

#### Proposed TSP Adaptation
- **Silverback →** Best tour in population
- **Migration to familiar →** 2-opt on current tour
- **Migration to unfamiliar →** Random k-opt perturbation
- **Silverback following →** Guided 2-opt using best tour edges
- **Parameters:** `pop_size: [30, 50, 80]`, `p: [0.03, 0.05, 0.1]` (migration probability), `max_iter: [200, 500, 1000]`

---

### Rank 7: Dung Beetle Optimizer (DBO) ⭐⭐

| Property | Value |
|----------|-------|
| **Year** | 2023 |
| **Citations** | ~966 |
| **Authors** | Xue, Shen |
| **Paper** | "Dung beetle optimizer: a new meta-heuristic algorithm for global optimization" |
| **Journal** | The Journal of Supercomputing |
| **TSP in Literature** | ❌ No TSP applications found |
| **Source Code** | ✅ MATLAB (official) |

#### Why #7 for Discrete TSP
1. **5 distinct behaviors** — ball-rolling, dancing, foraging, stealing, reproduction. Very rich operator set.
2. **Navigation mechanism** — dung beetles use celestial cues for straight-line navigation, maps to directed search.
3. **Theft behavior** — stealing from others = natural information sharing between solutions.
4. **Recent (2023)** — high novelty potential.
5. **4 parameters** — moderate DoE complexity.

#### Concerns
- Navigation mechanism is inherently continuous (direction vectors) — harder to discretize.
- 5 behaviors may create complex parameter interactions.

---

## 3. Implementation Difficulty Analysis

This section assesses how hard each algorithm is to adapt from continuous space to discrete TSP permutation space, based on our existing framework architecture and SOTA engine patterns.

### Difficulty Rating Scale
| Rating | Meaning |
|--------|---------|
| 🟢 Easy | Direct operator mapping, minimal mathematical rework, follows existing SOTA patterns |
| 🟡 Medium | Requires creative discretization of core mechanism, moderate rework |
| 🔴 Hard | Core mechanism fundamentally continuous, requires significant redesign |

---

### 3.1 RUN (Runge Kutta Optimizer) — 🟡 Medium Difficulty — ✅ IMPLEMENTED (2026-05-16)

| Aspect | Assessment |
|--------|-----------|
| **Core Challenge** | RK4 slope computation (`k₁, k₂, k₃, k₄`) is inherently continuous — needs discrete analog |
| **Discretization Strategy** | Map each slope stage to a different TSP move operator (2-opt → 3-opt → swap → insert) |
| **ESQ Mechanism** | Easy to adapt — random k-opt perturbation + best-tour guidance maps directly |
| **Parameter Mapping** | Simple — only `beta` needs discrete interpretation (controls perturbation intensity) |
| **Code Complexity** | ~400-500 lines (actual: `run_tsp.py` 480 lines) |
| **Framework Fit** | Good — follows population-based pattern, integrates with existing LS engine |
| **Risk** | Slope-to-operator mapping quality depends on move operator design |
| **Actual Effort** | ~2 hours (implementation + integration + testing) |
| **Test Results** | ✅ 8-city: cost=14, 20-city: cost=351, all tours valid, 45/45 tests pass |

#### Implementation Plan
```python
# Continuous RK4: X_new = X + (k1 + 2*k2 + 2*k3 + k4) / 6
# Discrete TSP analog:
k1 = apply_2opt(current_tour)          # slope 1: simple move
k2 = apply_3opt(k1_result)             # slope 2: deeper move
k3 = apply_swap(k2_result)             # slope 3: different move type
k4 = apply_insert(k3_result)           # slope 4: another move type
# Combine: weighted selection of best k_i result (not arithmetic average)
new_tour = select_best([k1, k2, k3, k4], weights=[1, 2, 2, 1])
```

**Key Insight:** We cannot average permutations arithmetically. Instead, we evaluate all 4 moves and use the RK4 weights `[1, 2, 2, 1]` as selection probabilities or apply them sequentially.

---

### 3.2 CGO (Chaos Game Optimization) — 🟢 Easy Difficulty — ✅ IMPLEMENTED (2026-05-16)

| Aspect | Assessment |
|--------|-----------|
| **Core Challenge** | Seed placement in continuous space → needs discrete tour construction |
| **Discretization Strategy** | Seeds = partial tours (subsequences), chaos game = merge operation |
| **Self-Similarity** | Natural fit — apply same merge rule at different scales (subtours → full tour) |
| **Parameter Mapping** | Minimal — only chaos map type and population size |
| **Code Complexity** | ~350 lines (actual: `cgo_tsp.py` 380 lines) |
| **Framework Fit** | Excellent — construction-based approach similar to our existing constructive heuristics |
| **Risk** | Low — chaos game rules are simple and well-defined |
| **Actual Effort** | ~2 hours (implementation + integration + testing) |
| **Test Results** | ✅ 8-city: cost=14, 20-city: cost=351, all tours valid, 45/45 tests pass |

#### Implementation Plan
```python
# Continuous: S_new = (S_old + S_seed) / 2 + chaos_factor × rand
# Discrete TSP analog:
# 1. Initialize: random partial tours (seeds) of length n/4
# 2. Chaos game step: merge two partial tours by interleaving cities
# 3. Self-similarity: double seed length each iteration until full tour
# 4. Chaos factor: logistic map controls merge randomness

def chaos_merge(tour_a, tour_b, chaos_value):
    """Interleave cities from two partial tours with chaos-controlled randomness"""
    merged = []
    idx_a, idx_b = 0, 0
    while idx_a < len(tour_a) and idx_b < len(tour_b):
        if chaos_value > 0.5:
            merged.append(tour_a[idx_a]); idx_a += 1
        else:
            merged.append(tour_b[idx_b]); idx_b += 1
        chaos_value = logistic_map(chaos_value)  # chaos iteration
    merged.extend(tour_a[idx_a:])
    merged.extend(tour_b[idx_b:])
    return merged
```

**Key Insight:** CGO is the easiest to implement because its construction-based approach naturally builds solutions incrementally — no need to "discretize" continuous operators.

---

### 3.3 SMA (Slime Mould Algorithm) — 🟡 Medium Difficulty

| Aspect | Assessment |
|--------|-----------|
| **Core Challenge** | Position update formula uses vector arithmetic → needs permutation analog |
| **Discretization Strategy** | Weight-based guided 2-opt: better tours influence move selection probability |
| **Oscillation Mechanism** | Easy to adapt — alternate between exploration (random k-opt) and exploitation (guided 2-opt) |
| **Venation Network** | Requires edge frequency matrix tracking across population (additional data structure) |
| **Parameter Mapping** | Simple — only `z` parameter controls oscillation threshold |
| **Code Complexity** | ~400-500 lines |
| **Framework Fit** | Good — population-based, integrates with existing LS engine |
| **Risk** | Medium — weight calculation needs careful normalization for permutation space |
| **Estimated Effort** | 3-4 days |

#### Implementation Plan
```python
# Continuous: X_new = X_best + vb × (W × X_A - X_B)
# Discrete TSP analog:
# 1. Calculate weights: W_i = fitness_rank(i) / sum(fitness_ranks)
# 2. Select guide tours A, B weighted by W
# 3. Apply guided 2-opt: prefer edges from tour A, avoid edges from tour B
# 4. Oscillation: vb alternates between exploration (-a) and exploitation (+a)

def sma_update(current_tour, best_tour, tour_a, tour_b, weight_a, weight_b, vb):
    """SMA position update for TSP"""
    if vb > 0:  # Exploitation
        # Guided 2-opt: prefer edges from best_tour and tour_a
        return guided_2opt(current_tour, best_tour, tour_a, weight_a)
    else:  # Exploration
        # Random k-opt perturbation
        return random_kopt(current_tour, k=random.randint(2, 4))
```

**Key Insight:** The weight-based adaptation is the core innovation — it creates implicit elitism without explicit selection operators.

---

### 3.4 GBO (Gradient-Based Optimizer) — 🔴 Hard Difficulty

| Aspect | Assessment |
|--------|-----------|
| **Core Challenge** | "Gradient" has no natural meaning in permutation space — fundamental concept mismatch |
| **Discretization Strategy** | Gradient = sequence of improving moves (greedy move selection), but this is just local search |
| **GSR Mechanism** | Hard to adapt — requires defining "direction" in permutation space |
| **LEO Mechanism** | Easy to adapt — random perturbation + best-tour guidance maps directly |
| **Parameter Mapping** | Moderate — `p_r` (LEO probability) needs calibration for TSP |
| **Code Complexity** | ~500-600 lines (complex dual search mechanism) |
| **Framework Fit** | Moderate — dual search may conflict with existing LS engine integration |
| **Risk** | High — gradient metaphor may not translate meaningfully to discrete space |
| **Estimated Effort** | 5-6 days |

#### Implementation Plan
```python
# Continuous: X_new = X_current + rand × (X_best - X_random) × gradient_factor
# Discrete TSP analog (conceptual stretch):
# 1. "Gradient" = sequence of improving swap operations from current to best
# 2. Compute move sequence: find swaps that transform current_tour → best_tour
# 3. Apply partial sequence (controlled by gradient_factor)
# 4. LEO: random k-opt perturbation with probability p_r

def compute_gradient(current_tour, best_tour):
    """Find sequence of swaps that transforms current to best (expensive!)"""
    # This is essentially solving a sorting problem — O(n²) minimum
    swaps = []
    pos_map = {city: i for i, city in enumerate(best_tour)}
    for i in range(len(current_tour)):
        if current_tour[i] != best_tour[i]:
            target_pos = pos_map[current_tour[i]]
            swaps.append((i, target_pos))
    return swaps
```

**Key Insight:** The gradient computation is essentially finding a transformation between two permutations — this is computationally expensive and may not provide meaningful search direction. LEO mechanism is the more valuable component.

---

### 3.5 APO (Artificial Protozoa Optimizer) — 🟢 Easy Difficulty

| Aspect | Assessment |
|--------|-----------|
| **Core Challenge** | 4 behaviors need distinct TSP operator mappings — but each maps cleanly |
| **Discretization Strategy** | Direct 1:1 mapping: foraging → 2-opt, dormancy → random tour, reproduction → OX crossover |
| **Parameter Mapping** | Simple — `proportion` controls foraging ratio (exploration vs exploitation balance) |
| **Code Complexity** | ~350-450 lines (clean 4-mode structure) |
| **Framework Fit** | Excellent — multi-mode approach similar to our E2BSO-TSP 3-phase design |
| **Risk** | Low — behaviors are well-separated and independently implementable |
| **Estimated Effort** | 2-3 days |

#### Implementation Plan
```python
# APO 4 behaviors → TSP operators:
# Autotrophic foraging (exploration): best-tour guided 2-opt
# Heterotrophic foraging (exploration): random swap between two tours
# Dormancy (diversification): random tour + greedy construction
# Reproduction (exploitation): OX crossover between best and current

def apo_update(current_tour, best_tour, population, mode, proportion):
    if mode == "autotrophic":
        return guided_2opt(current_tour, best_tour)
    elif mode == "heterotrophic":
        other = random.choice(population)
        return random_swap(current_tour, other)
    elif mode == "dormancy":
        return random_tour_greedy(n=len(current_tour))
    else:  # reproduction
        return ox_crossover(current_tour, best_tour)
```

**Key Insight:** APO is the easiest to implement because each behavior maps to an existing TSP operator we already have in our framework.

---

### 3.6 GTO (Artificial Gorilla Troops Optimizer) — 🟡 Medium Difficulty

| Aspect | Assessment |
|--------|-----------|
| **Core Challenge** | 5 operators (3 exploration + 2 exploitation) need distinct mappings — some overlap with existing algorithms |
| **Discretization Strategy** | Migration → k-opt, silverback following → guided 2-opt, competition → crossover |
| **Parameter Mapping** | Moderate — `p` (migration probability) and `C` (competition factor) need calibration |
| **Code Complexity** | ~450-550 lines |
| **Framework Fit** | Moderate — social dynamics similar to GWO/HHO, may feel redundant |
| **Risk** | Medium — operators may overlap significantly with existing GWO/HHO implementations |
| **Estimated Effort** | 3-4 days |

#### Implementation Plan
```python
# GTO operators → TSP mappings:
# Migration to unfamiliar: random k-opt (exploration)
# Migration to familiar: 2-opt on current tour (exploitation)
# Silverback following: guided 2-opt using best tour edges (exploitation)
# Competition: OX crossover between two random tours (exploration)
# Migration to known location: guided swap using historical best edges (exploitation)
```

**Key Insight:** GTO's operators are conceptually similar to GWO and HHO — the main value is the social dynamics (silverback leadership), which may not provide significantly different search behavior.

---

### 3.7 DBO (Dung Beetle Optimizer) — 🔴 Hard Difficulty

| Aspect | Assessment |
|--------|-----------|
| **Core Challenge** | Navigation mechanism uses celestial direction vectors — fundamentally continuous |
| **Discretization Strategy** | Direction → preferred edge selection, but this is weak mapping |
| **Dance Behavior** | Hard to interpret in TSP context — what does "dancing" mean for a tour? |
| **Theft Behavior** | Easy to adapt — copy edges from better solutions |
| **Parameter Mapping** | Complex — 4+ parameters with unclear discrete interpretation |
| **Code Complexity** | ~500-650 lines (complex 5-behavior system) |
| **Framework Fit** | Poor — navigation metaphor doesn't translate well to permutation space |
| **Risk** | High — core mechanism (celestial navigation) has no meaningful discrete analog |
| **Estimated Effort** | 5-7 days |

#### Implementation Plan
```python
# DBO behaviors → TSP mappings (weak):
# Ball-rolling: guided 2-opt using "direction" (preferred edges) — direction is artificial
# Dance: ??? — no clear TSP analog
# Foraging: random k-opt
# Theft: copy edges from better solutions
# Reproduction: OX crossover
```

**Key Insight:** DBO is the hardest to implement because its core innovation (celestial navigation) is fundamentally continuous. The other behaviors (theft, reproduction) are generic and already covered by existing algorithms.

---

### 3.8 Summary: Implementation Difficulty Matrix

| Algorithm | Discretization Difficulty | Code Complexity | Framework Fit | Total Effort | Overall Difficulty |
|-----------|--------------------------|-----------------|---------------|--------------|-------------------|
| **CGO** | 🟢 Easy (construction-based) | ~350 lines | Excellent | 2-3 days | 🟢 Easy |
| **APO** | 🟢 Easy (direct operator mapping) | ~400 lines | Excellent | 2-3 days | 🟢 Easy |
| **RUN** | 🟡 Medium (slope → operator) | ~450 lines | Good | 3-4 days | 🟡 Medium |
| **SMA** | 🟡 Medium (weight adaptation) | ~450 lines | Good | 3-4 days | 🟡 Medium |
| **GTO** | 🟡 Medium (social dynamics) | ~500 lines | Moderate | 3-4 days | 🟡 Medium |
| **GBO** | 🔴 Hard (gradient concept mismatch) | ~550 lines | Moderate | 5-6 days | 🔴 Hard |
| **DBO** | 🔴 Hard (navigation fundamentally continuous) | ~600 lines | Poor | 5-7 days | 🔴 Hard |

---

## 4. Algorithms Excluded from Consideration

| Algorithm | Reason for Exclusion |
|-----------|---------------------|
| Butterfly Optimization (BOA) | Already widely applied to TSP variants |
| Harris Hawks (HHO) | Already in our framework (Numba-HHO) |
| Marine Predators (MPA) | Applied to VRP/TSP variants in literature |
| Equilibrium Optimizer (EO) | Continuous-only, no discrete variant |
| Aquila Optimizer (AO) | Applied to routing problems |
| Seagull Optimization (SOA) | Applied to TSP in multiple papers |
| Manta Ray Foraging (MRFO) | Applied to VRP variants |
| Chimp Optimization (ChOA) | Applied to scheduling/TSP variants |
| Squirrel Search (SSA) | Applied to routing problems |
| Henry Gas Solubility (HGSO) | Physics-based, continuous-only |
| Archimedes Optimization (AOA) | Physics-based, continuous-only |
| Tunicate Swarm (TSA) | Applied to scheduling problems |
| Honey Badger (HBA) | Applied to routing problems |
| Mayfly Optimization (MA) | Applied to TSP variants |
| African Vultures (AVOA) | Applied to scheduling problems |
| Golden Jackal (GJO) | Applied to routing problems |
| Coati Optimization (COA) | Applied to scheduling problems |
| Beluga Whale (BWO) | Applied to routing problems |
| Gazelle Optimization (GOA) | Applied to scheduling problems |
| Snake Optimizer (SO) | Applied to routing problems |
| Flower Pollination (FPA) | Already applied to TSP-based supply chain |
| Cuckoo Search (CS) | Already widely applied to TSP |

---

## 4. Implementation Priority Recommendation

### Phase 1: High Impact (Implement First) — ✅ COMPLETE
| Algorithm | Effort | Expected Gap Improvement | Paper Novelty | Status |
|-----------|--------|-------------------------|---------------|--------|
| **RUN** | 3-4 days | High (strong local optima escape) | Very High (first metaphor-free for TSP) | ✅ Done (2026-05-16) |
| **CGO** | 3-4 days | Medium-High (chaos-based diversity) | Very High (first chaos-fractal for TSP) | ✅ Done (2026-05-16) |

### Phase 2: Medium Impact (Implement Second)
| Algorithm | Effort | Expected Gap Improvement | Paper Novelty |
|-----------|--------|-------------------------|---------------|
| **SMA** | 3-4 days | Medium (biological shortest-path precedent) | High (first slime mould for TSP) |
| **GBO** | 3-4 days | Medium (gradient-inspired moves) | High (first gradient-based for TSP) |

### Phase 3: Lower Impact (Implement if Time Permits)
| Algorithm | Effort | Expected Gap Improvement | Paper Novelty |
|-----------|--------|-------------------------|---------------|
| **APO** | 3-4 days | Medium (4-mode behavior) | High (very recent, zero TSP) |
| **GTO** | 3-4 days | Low-Medium (similar to existing GWO/HHO) | Medium |

---

## 5. Expected Framework Impact

After implementing RUN + CGO (Phase 1 complete):

| Metric | Current | After Phase 1 |
|--------|---------|---------------|
| Total algorithms | 15 | 17 |
| Unique search paradigms | 8 | 10 |
| Metaphor-free algorithms | 0 | 1 (RUN) |
| Chaos-theory algorithms | 0 | 1 (CGO) |
| 3rd paper novelty | — | "First metaphor-free + chaos-fractal TSP benchmark" |

---

## 6. Key References

1. Dokeroglu, T., Canturk, D., & Kucukyilmaz, T. (2024). "A survey on pioneering metaheuristic algorithms between 2019 and 2024." *arXiv:2501.14769*.
2. Toaza, B., & Esztergár-Kiss, D. (2023). "A review of metaheuristic algorithms for solving TSP-based scheduling optimization problems." *Applied Soft Computing*, 148, 110908.
3. Ahmadianfar et al. (2021). "RUN: Beyond the Metaphor: An Efficient Optimization Algorithm Based on Runge Kutta Method." *Engineering Applications of AI*.
4. Talatahari & Azizi (2021). "Chaos Game Optimization: a novel metaheuristic algorithm." *Artificial Intelligence Review*, 54, 917-1004.
5. Li et al. (2020). "Slime mould algorithm: A new method for stochastic optimization." *Future Generation Computer Systems*.
6. Wang et al. (2024). "Artificial Protozoa Optimizer: A novel bio-inspired metaheuristic algorithm." *Knowledge-Based Systems*, 295, 111737.
7. Rajwar et al. (2023). "An exhaustive review of the metaheuristic algorithms for search and optimization." *Artificial Intelligence Review*.

---

*This document was generated on 2026-05-15 based on comprehensive literature review of 158+ metaheuristic algorithms.*
