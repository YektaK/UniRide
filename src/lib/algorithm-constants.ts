/**
 * Algorithm Constants
 * Single source of truth for algorithm names across UI and Python API
 * 
 * IMPORTANT: These names MUST match Python STRATEGY_REGISTRY keys
 * See: optimizer_api/strategies/__init__.py
 * 
 * Organized by Pipeline:
 * - Pipeline A: Cluster-First, Route-Second (Sweep/CW + TSP)
 * - Pipeline B: Route-First, Cluster-Second (Giant Tour + Split)
 * - Holistic: Native CVRP solvers
 * - Heuristic: Simple algorithms
 */

// ============================================================
// ALGORITHM KEYS - MUST match Python STRATEGY_REGISTRY exactly
// ============================================================

// Pipeline A: Cluster-First, Route-Second (Sweep/CW based)
export const PIPELINE_A_KEYS = {
  GENETIC_ALGORITHM: "genetic_algorithm",
  GA: "ga", // Alias
  PSO: "pso",
  GWO: "gwo",
  GREY_WOLF: "grey_wolf", // Alias
  HHO: "hho",
  HARRIS_HAWKS: "harris_hawks", // Alias
} as const;

// Pipeline B: Route-First, Cluster-Second (Split based)
export const PIPELINE_B_KEYS = {
  GA_SPLIT: "ga_split",
  GA_SPLIT_ALIAS: "ga-split", // Alias
  PSO_SPLIT: "pso_split",
  PSO_SPLIT_ALIAS: "pso-split", // Alias
  GWO_SPLIT: "gwo_split",
  GWO_SPLIT_ALIAS: "gwo-split", // Alias
  HHO_SPLIT: "hho_split",
  HHO_SPLIT_ALIAS: "hho-split", // Alias
} as const;

// Holistic Solvers (Native CVRP)
export const HOLISTIC_KEYS = {
  ORTOOLS_CVRP: "ortools_cvrp",
  ORTOOLS: "ortools", // Alias
  PYVRP: "pyvrp",
  HGS: "hgs", // PyVRP alias
  PYVRP_ALT: "pyvrp_alt",
  VROOM: "vroom",
  VROOM_FALLBACK: "vroom_fallback",
} as const;

// Heuristic Algorithms
export const HEURISTIC_KEYS = {
  TWO_OPT: "two_opt",
  TWO_OPT_ALIAS: "2opt", // Alias
  GREEDY: "greedy",
  NEAREST_NEIGHBOR: "nearest_neighbor", // Alias
  PERMUTATION_TSP: "permutation_tsp",
  PERMUTATION: "permutation", // Alias
  EXACT: "exact", // Alias for permutation_tsp
} as const;

// Combined algorithm keys
export const ALGORITHM_KEYS = {
  ...PIPELINE_A_KEYS,
  ...PIPELINE_B_KEYS,
  ...HOLISTIC_KEYS,
  ...HEURISTIC_KEYS,
} as const;

// Local Search Type keys - MUST match Python LocalSearchType enum
export const LOCAL_SEARCH_KEYS = {
  NONE: "none",
  TWO_OPT: "two_opt",
  THREE_OPT: "three_opt",
  OR_OPT: "or_opt",
  HYBRID: "hybrid",
} as const;

export type LocalSearchType = typeof LOCAL_SEARCH_KEYS[keyof typeof LOCAL_SEARCH_KEYS];

// ============================================================
// DIRECTION KEYS - CVRPTW Support
// ============================================================

export const DIRECTION_KEYS = {
  PICKUP: "pickup",   // Geliş - öğrencileri okula getirme
  DROPOFF: "dropoff", // Gidiş - öğrencileri okuldan bırakma
} as const;

export type DirectionType = typeof DIRECTION_KEYS[keyof typeof DIRECTION_KEYS];

// Direction display names for UI
export const DIRECTION_DISPLAY_NAMES: Record<DirectionType, string> = {
  [DIRECTION_KEYS.PICKUP]: "Geliş (Okula Getirme)",
  [DIRECTION_KEYS.DROPOFF]: "Gidiş (Okuldan Bırakma)",
};

// Direction descriptions for UI
export const DIRECTION_DESCRIPTIONS: Record<DirectionType, string> = {
  [DIRECTION_KEYS.PICKUP]: "Öğrencileri evlerinden alıp okula getirme. Hedef varış saatine göre geriye doğru planlama.",
  [DIRECTION_KEYS.DROPOFF]: "Öğrencileri okuldan alıp evlerine bırakma. Çıkış saatinden itibaren ileriye doğru planlama.",
};

// Direction options for UI dropdowns
export const DIRECTION_OPTIONS = [
  {
    key: DIRECTION_KEYS.PICKUP,
    label: DIRECTION_DISPLAY_NAMES[DIRECTION_KEYS.PICKUP],
    description: DIRECTION_DESCRIPTIONS[DIRECTION_KEYS.PICKUP],
    icon: "🏠➡️🏫",
  },
  {
    key: DIRECTION_KEYS.DROPOFF,
    label: DIRECTION_DISPLAY_NAMES[DIRECTION_KEYS.DROPOFF],
    description: DIRECTION_DESCRIPTIONS[DIRECTION_KEYS.DROPOFF],
    icon: "🏫➡️🏠",
  },
];

// Default time window settings
export const TIME_WINDOW_DEFAULTS = {
  WINDOW_SIZE_MINUTES: 30,      // Default time window size
  OFFSET_MINUTES: 10,           // Buffer for driver notification
  DEFAULT_PICKUP_TIME: "09:00", // Default school arrival time
  DEFAULT_DROPOFF_TIME: "14:00", // Default school departure time
} as const;

// ============================================================
// ALGORITHM DISPLAY NAMES
// ============================================================

// Pipeline A Display Names
export const PIPELINE_A_DISPLAY_NAMES: Record<string, string> = {
  [PIPELINE_A_KEYS.GENETIC_ALGORITHM]: "Genetik Algoritma (Sweep)",
  [PIPELINE_A_KEYS.GA]: "Genetik Algoritma (Sweep)",
  [PIPELINE_A_KEYS.PSO]: "Parçacık Sürü (Sweep)",
  [PIPELINE_A_KEYS.GWO]: "Gri Kurt (Sweep)",
  [PIPELINE_A_KEYS.GREY_WOLF]: "Gri Kurt (Sweep)",
  [PIPELINE_A_KEYS.HHO]: "Harris Hawks (Sweep)",
  [PIPELINE_A_KEYS.HARRIS_HAWKS]: "Harris Hawks (Sweep)",
};

// Pipeline B Display Names (Route-First = Split)
export const PIPELINE_B_DISPLAY_NAMES: Record<string, string> = {
  [PIPELINE_B_KEYS.GA_SPLIT]: "GA-Split (Route-First)",
  [PIPELINE_B_KEYS.GA_SPLIT_ALIAS]: "GA-Split (Route-First)",
  [PIPELINE_B_KEYS.PSO_SPLIT]: "PSO-Split (Route-First)",
  [PIPELINE_B_KEYS.PSO_SPLIT_ALIAS]: "PSO-Split (Route-First)",
  [PIPELINE_B_KEYS.GWO_SPLIT]: "GWO-Split (Route-First)",
  [PIPELINE_B_KEYS.GWO_SPLIT_ALIAS]: "GWO-Split (Route-First)",
  [PIPELINE_B_KEYS.HHO_SPLIT]: "HHO-Split (Route-First)",
  [PIPELINE_B_KEYS.HHO_SPLIT_ALIAS]: "HHO-Split (Route-First)",
};

// Holistic Solvers Display Names
export const HOLISTIC_DISPLAY_NAMES: Record<string, string> = {
  [HOLISTIC_KEYS.ORTOOLS_CVRP]: "OR-Tools CVRP",
  [HOLISTIC_KEYS.ORTOOLS]: "OR-Tools CVRP",
  [HOLISTIC_KEYS.PYVRP]: "PyVRP (HGS - DIMACS Winner)",
  [HOLISTIC_KEYS.HGS]: "PyVRP (HGS - DIMACS Winner)",
  [HOLISTIC_KEYS.PYVRP_ALT]: "PyVRP Alternative",
  [HOLISTIC_KEYS.VROOM]: "VROOM (Ultra-fast)",
  [HOLISTIC_KEYS.VROOM_FALLBACK]: "VROOM (Fallback)",
};

// Heuristic Display Names
export const HEURISTIC_DISPLAY_NAMES: Record<string, string> = {
  [HEURISTIC_KEYS.TWO_OPT]: "Two-Opt Local Search",
  [HEURISTIC_KEYS.TWO_OPT_ALIAS]: "Two-Opt Local Search",
  [HEURISTIC_KEYS.GREEDY]: "Greedy (En Yakın Komşu)",
  [HEURISTIC_KEYS.NEAREST_NEIGHBOR]: "Greedy (En Yakın Komşu)",
  [HEURISTIC_KEYS.PERMUTATION_TSP]: "Permütasyon (Optimal n≤10)",
  [HEURISTIC_KEYS.PERMUTATION]: "Permütasyon (Optimal n≤10)",
  [HEURISTIC_KEYS.EXACT]: "Permütasyon (Optimal n≤10)",
};

// Combined display names
export const ALGORITHM_DISPLAY_NAMES: Record<string, string> = {
  ...PIPELINE_A_DISPLAY_NAMES,
  ...PIPELINE_B_DISPLAY_NAMES,
  ...HOLISTIC_DISPLAY_NAMES,
  ...HEURISTIC_DISPLAY_NAMES,
};

// Local Search display names for UI
export const LOCAL_SEARCH_DISPLAY_NAMES: Record<LocalSearchType, string> = {
  [LOCAL_SEARCH_KEYS.NONE]: "Yok",
  [LOCAL_SEARCH_KEYS.TWO_OPT]: "2-Opt (Klasik)",
  [LOCAL_SEARCH_KEYS.THREE_OPT]: "3-Opt (Yüksek Kalite)",
  [LOCAL_SEARCH_KEYS.OR_OPT]: "Or-Opt (Kümeleme)",
  [LOCAL_SEARCH_KEYS.HYBRID]: "Hibrit (Kombine)",
};

// ============================================================
// ALGORITHM DESCRIPTIONS
// ============================================================

export const ALGORITHM_DESCRIPTIONS: Record<string, string> = {
  // Pipeline A
  [PIPELINE_A_KEYS.GENETIC_ALGORITHM]: "Sweep/CW kümeleme + GA rotalama. Kümeleme öncesi, rota sonrası.",
  [PIPELINE_A_KEYS.PSO]: "Sweep/CW kümeleme + PSO rotalama. Hızlı yakınsama.",
  [PIPELINE_A_KEYS.GWO]: "Sweep/CW kümeleme + GWO rotalama. Sosyal hiyerarşi.",
  [PIPELINE_A_KEYS.HHO]: "Sweep/CW kümeleme + HHO rotalama. Adaptif avlanma.",
  
  // Pipeline B
  [PIPELINE_B_KEYS.GA_SPLIT]: "GA Giant Tour + Optimal Split. %100 feasible, optimal bölme.",
  [PIPELINE_B_KEYS.PSO_SPLIT]: "PSO Giant Tour + Optimal Split. Hızlı ve kaliteli.",
  [PIPELINE_B_KEYS.GWO_SPLIT]: "GWO Giant Tour + Optimal Split. Güçlü keşif-sömürü.",
  [PIPELINE_B_KEYS.HHO_SPLIT]: "HHO Giant Tour + Optimal Split. Adaptif, kaçış enerjisi.",
  
  // Holistic
  [HOLISTIC_KEYS.ORTOOLS_CVRP]: "Google OR-Tools endüstri standardı CVRP çözücüsü.",
  [HOLISTIC_KEYS.PYVRP]: "PyVRP HGS - DIMACS 2021 birincisi. En yüksek kalite.",
  [HOLISTIC_KEYS.PYVRP_ALT]: "PyVRP alternatif implementasyon.",
  [HOLISTIC_KEYS.VROOM]: "VROOM C++ motor - 1000+ nokta < 5 saniye.",
  [HOLISTIC_KEYS.VROOM_FALLBACK]: "VROOM yedek çözücü.",
  
  // Heuristics
  [HEURISTIC_KEYS.TWO_OPT]: "Klasik 2-opt yerel arama. Küçük-orta ölçekli.",
  [HEURISTIC_KEYS.GREEDY]: "Hızlı sezgisel. En yakın komşu stratejisi.",
  [HEURISTIC_KEYS.PERMUTATION_TSP]: "Tüm kombinasyonları dener. n ≤ 10 için optimal.",
};

// Local Search descriptions
export const LOCAL_SEARCH_DESCRIPTIONS: Record<LocalSearchType, string> = {
  [LOCAL_SEARCH_KEYS.NONE]: "Yerel arama uygulanmaz.",
  [LOCAL_SEARCH_KEYS.TWO_OPT]: "Kenar değiştirme ile iyileştirme. Hızlı ve etkili.",
  [LOCAL_SEARCH_KEYS.THREE_OPT]: "3 kenar değiştirme ile daha güçlü iyileştirme.",
  [LOCAL_SEARCH_KEYS.OR_OPT]: "Alt tur yeniden konumlandırma.",
  [LOCAL_SEARCH_KEYS.HYBRID]: "2-opt + 3-opt + Or-opt kombine.",
};

// ============================================================
// ALGORITHM COMPLEXITY
// ============================================================

export const ALGORITHM_COMPLEXITY: Record<string, string> = {
  // Pipeline A
  [PIPELINE_A_KEYS.GENETIC_ALGORITHM]: "O(g × p × n²) + Sweep",
  [PIPELINE_A_KEYS.PSO]: "O(i × s × n²) + Sweep",
  [PIPELINE_A_KEYS.GWO]: "O(i × p × n²) + Sweep",
  [PIPELINE_A_KEYS.HHO]: "O(i × h × n²) + Sweep",
  
  // Pipeline B
  [PIPELINE_B_KEYS.GA_SPLIT]: "O(g × p × n²) + O(n²) Split",
  [PIPELINE_B_KEYS.PSO_SPLIT]: "O(i × s × n²) + O(n²) Split",
  [PIPELINE_B_KEYS.GWO_SPLIT]: "O(i × p × n²) + O(n²) Split",
  [PIPELINE_B_KEYS.HHO_SPLIT]: "O(i × h × n²) + O(n²) Split",
  
  // Holistic
  [HOLISTIC_KEYS.ORTOOLS_CVRP]: "O(n³)"
  [HOLISTIC_KEYS.PYVRP]: "O(n² log n)",
  [HOLISTIC_KEYS.VROOM]: "O(n²)",
  
  // Heuristics
  [HEURISTIC_KEYS.TWO_OPT]: "O(n²)",
  [HEURISTIC_KEYS.GREEDY]: "O(n²)",
  [HEURISTIC_KEYS.PERMUTATION_TSP]: "O(n!)",
};

// ============================================================
// ALGORITHM OPTIONS FOR UI DROPDOWNS (Grouped by Pipeline)
// ============================================================

export const ALGORITHM_OPTIONS_GROUPED = [
  {
    category: "Cluster-First, Route-Second (Sweep/CW)",
    description: "Önce coğrafi kümeleme, sonra her küme içinde rota optimizasyonu",
    algorithms: [
      {
        key: PIPELINE_A_KEYS.GENETIC_ALGORITHM,
        label: PIPELINE_A_DISPLAY_NAMES[PIPELINE_A_KEYS.GENETIC_ALGORITHM],
        description: ALGORITHM_DESCRIPTIONS[PIPELINE_A_KEYS.GENETIC_ALGORITHM],
        complexity: ALGORITHM_COMPLEXITY[PIPELINE_A_KEYS.GENETIC_ALGORITHM],
        recommended: false,
        pipeline: "A",
      },
      {
        key: PIPELINE_A_KEYS.PSO,
        label: PIPELINE_A_DISPLAY_NAMES[PIPELINE_A_KEYS.PSO],
        description: ALGORITHM_DESCRIPTIONS[PIPELINE_A_KEYS.PSO],
        complexity: ALGORITHM_COMPLEXITY[PIPELINE_A_KEYS.PSO],
        recommended: false,
        pipeline: "A",
      },
      {
        key: PIPELINE_A_KEYS.GWO,
        label: PIPELINE_A_DISPLAY_NAMES[PIPELINE_A_KEYS.GWO],
        description: ALGORITHM_DESCRIPTIONS[PIPELINE_A_KEYS.GWO],
        complexity: ALGORITHM_COMPLEXITY[PIPELINE_A_KEYS.GWO],
        recommended: false,
        pipeline: "A",
      },
      {
        key: PIPELINE_A_KEYS.HHO,
        label: PIPELINE_A_DISPLAY_NAMES[PIPELINE_A_KEYS.HHO],
        description: ALGORITHM_DESCRIPTIONS[PIPELINE_A_KEYS.HHO],
        complexity: ALGORITHM_COMPLEXITY[PIPELINE_A_KEYS.HHO],
        recommended: false,
        pipeline: "A",
      },
    ],
  },
  {
    category: "Route-First, Cluster-Second (Optimal Split)",
    description: "Önce tüm öğrenciler için Giant Tour, sonra optimal araç bölme",
    algorithms: [
      {
        key: PIPELINE_B_KEYS.GA_SPLIT,
        label: PIPELINE_B_DISPLAY_NAMES[PIPELINE_B_KEYS.GA_SPLIT],
        description: ALGORITHM_DESCRIPTIONS[PIPELINE_B_KEYS.GA_SPLIT],
        complexity: ALGORITHM_COMPLEXITY[PIPELINE_B_KEYS.GA_SPLIT],
        recommended: true,
        pipeline: "B",
        badge: "En İyi Kalite",
      },
      {
        key: PIPELINE_B_KEYS.PSO_SPLIT,
        label: PIPELINE_B_DISPLAY_NAMES[PIPELINE_B_KEYS.PSO_SPLIT],
        description: ALGORITHM_DESCRIPTIONS[PIPELINE_B_KEYS.PSO_SPLIT],
        complexity: ALGORITHM_COMPLEXITY[PIPELINE_B_KEYS.PSO_SPLIT],
        recommended: true,
        pipeline: "B",
        badge: "Hızlı",
      },
      {
        key: PIPELINE_B_KEYS.GWO_SPLIT,
        label: PIPELINE_B_DISPLAY_NAMES[PIPELINE_B_KEYS.GWO_SPLIT],
        description: ALGORITHM_DESCRIPTIONS[PIPELINE_B_KEYS.GWO_SPLIT],
        complexity: ALGORITHM_COMPLEXITY[PIPELINE_B_KEYS.GWO_SPLIT],
        recommended: true,
        pipeline: "B",
      },
      {
        key: PIPELINE_B_KEYS.HHO_SPLIT,
        label: PIPELINE_B_DISPLAY_NAMES[PIPELINE_B_KEYS.HHO_SPLIT],
        description: ALGORITHM_DESCRIPTIONS[PIPELINE_B_KEYS.HHO_SPLIT],
        complexity: ALGORITHM_COMPLEXITY[PIPELINE_B_KEYS.HHO_SPLIT],
        recommended: true,
        pipeline: "B",
      },
    ],
  },
  {
    category: "Holistik Çözücüler (Native CVRP)",
    description: "Endüstri standardı kütüphaneler ile doğal CVRP çözümü",
    algorithms: [
      {
        key: HOLISTIC_KEYS.ORTOOLS_CVRP,
        label: HOLISTIC_DISPLAY_NAMES[HOLISTIC_KEYS.ORTOOLS_CVRP],
        description: ALGORITHM_DESCRIPTIONS[HOLISTIC_KEYS.ORTOOLS_CVRP],
        complexity: ALGORITHM_COMPLEXITY[HOLISTIC_KEYS.ORTOOLS_CVRP],
        recommended: false,
        pipeline: "holistic",
      },
      {
        key: HOLISTIC_KEYS.PYVRP,
        label: HOLISTIC_DISPLAY_NAMES[HOLISTIC_KEYS.PYVRP],
        description: ALGORITHM_DESCRIPTIONS[HOLISTIC_KEYS.PYVRP],
        complexity: ALGORITHM_COMPLEXITY[HOLISTIC_KEYS.PYVRP],
        recommended: false,
        pipeline: "holistic",
        badge: "DIMACS 2021 🏆",
      },
      {
        key: HOLISTIC_KEYS.VROOM,
        label: HOLISTIC_DISPLAY_NAMES[HOLISTIC_KEYS.VROOM],
        description: ALGORITHM_DESCRIPTIONS[HOLISTIC_KEYS.VROOM],
        complexity: ALGORITHM_COMPLEXITY[HOLISTIC_KEYS.VROOM],
        recommended: false,
        pipeline: "holistic",
        badge: "Ultra Hızlı ⚡",
      },
    ],
  },
  {
    category: "Sezgisel Algoritmalar",
    description: "Basit ve hızlı çözümler",
    algorithms: [
      {
        key: HEURISTIC_KEYS.TWO_OPT,
        label: HEURISTIC_DISPLAY_NAMES[HEURISTIC_KEYS.TWO_OPT],
        description: ALGORITHM_DESCRIPTIONS[HEURISTIC_KEYS.TWO_OPT],
        complexity: ALGORITHM_COMPLEXITY[HEURISTIC_KEYS.TWO_OPT],
        recommended: false,
        pipeline: "heuristic",
      },
      {
        key: HEURISTIC_KEYS.GREEDY,
        label: HEURISTIC_DISPLAY_NAMES[HEURISTIC_KEYS.GREEDY],
        description: ALGORITHM_DESCRIPTIONS[HEURISTIC_KEYS.GREEDY],
        complexity: ALGORITHM_COMPLEXITY[HEURISTIC_KEYS.GREEDY],
        recommended: false,
        pipeline: "heuristic",
      },
      {
        key: HEURISTIC_KEYS.PERMUTATION_TSP,
        label: HEURISTIC_DISPLAY_NAMES[HEURISTIC_KEYS.PERMUTATION_TSP],
        description: ALGORITHM_DESCRIPTIONS[HEURISTIC_KEYS.PERMUTATION_TSP],
        complexity: ALGORITHM_COMPLEXITY[HEURISTIC_KEYS.PERMUTATION_TSP],
        recommended: false,
        pipeline: "heuristic",
      },
    ],
  },
];

// Flattened options for backward compatibility
export const ALGORITHM_OPTIONS = ALGORITHM_OPTIONS_GROUPED.flatMap(group => 
  group.algorithms.map(alg => ({
    ...alg,
    category: group.category,
    categoryDescription: group.description,
  }))
);

// Local Search options for UI dropdowns
export const LOCAL_SEARCH_OPTIONS = [
  {
    key: LOCAL_SEARCH_KEYS.NONE,
    label: LOCAL_SEARCH_DISPLAY_NAMES[LOCAL_SEARCH_KEYS.NONE],
    description: LOCAL_SEARCH_DESCRIPTIONS[LOCAL_SEARCH_KEYS.NONE],
  },
  {
    key: LOCAL_SEARCH_KEYS.TWO_OPT,
    label: LOCAL_SEARCH_DISPLAY_NAMES[LOCAL_SEARCH_KEYS.TWO_OPT],
    description: LOCAL_SEARCH_DESCRIPTIONS[LOCAL_SEARCH_KEYS.TWO_OPT],
  },
  {
    key: LOCAL_SEARCH_KEYS.THREE_OPT,
    label: LOCAL_SEARCH_DISPLAY_NAMES[LOCAL_SEARCH_KEYS.THREE_OPT],
    description: LOCAL_SEARCH_DESCRIPTIONS[LOCAL_SEARCH_KEYS.THREE_OPT],
  },
  {
    key: LOCAL_SEARCH_KEYS.OR_OPT,
    label: LOCAL_SEARCH_DISPLAY_NAMES[LOCAL_SEARCH_KEYS.OR_OPT],
    description: LOCAL_SEARCH_DESCRIPTIONS[LOCAL_SEARCH_KEYS.OR_OPT],
  },
  {
    key: LOCAL_SEARCH_KEYS.HYBRID,
    label: LOCAL_SEARCH_DISPLAY_NAMES[LOCAL_SEARCH_KEYS.HYBRID],
    description: LOCAL_SEARCH_DESCRIPTIONS[LOCAL_SEARCH_KEYS.HYBRID],
  },
];

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

// Legacy mapping for backward compatibility
export const LEGACY_ALGORITHM_MAP: Record<string, string> = {
  "nearest-neighbor": HEURISTIC_KEYS.GREEDY,
  "two-opt": HEURISTIC_KEYS.TWO_OPT,
  "permutation": HEURISTIC_KEYS.PERMUTATION_TSP,
  "ga": PIPELINE_A_KEYS.GENETIC_ALGORITHM,
  "grey_wolf": PIPELINE_A_KEYS.GWO,
  "harris_hawks": PIPELINE_A_KEYS.HHO,
  "ga-split": PIPELINE_B_KEYS.GA_SPLIT,
  "pso-split": PIPELINE_B_KEYS.PSO_SPLIT,
  "gwo-split": PIPELINE_B_KEYS.GWO_SPLIT,
  "hho-split": PIPELINE_B_KEYS.HHO_SPLIT,
  "ortools": HOLISTIC_KEYS.ORTOOLS_CVRP,
  "hgs": HOLISTIC_KEYS.PYVRP,
  "2opt": HEURISTIC_KEYS.TWO_OPT,
  "exact": HEURISTIC_KEYS.PERMUTATION_TSP,
};

/**
 * Normalize algorithm name to canonical Python key
 */
export function normalizeAlgorithmName(name: string): string {
  if (LEGACY_ALGORITHM_MAP[name]) {
    return LEGACY_ALGORITHM_MAP[name];
  }
  return name;
}

/**
 * Get display name for algorithm
 */
export function getAlgorithmDisplayName(algorithm: string): string {
  const normalized = normalizeAlgorithmName(algorithm);
  return ALGORITHM_DISPLAY_NAMES[normalized] || algorithm;
}

/**
 * Check if algorithm is recommended for production use
 */
export function isAlgorithmRecommended(algorithm: string): boolean {
  const normalized = normalizeAlgorithmName(algorithm);
  const option = ALGORITHM_OPTIONS.find(opt => opt.key === normalized);
  return option?.recommended ?? false;
}

/**
 * Get algorithm pipeline type
 */
export function getAlgorithmPipeline(algorithm: string): string {
  const normalized = normalizeAlgorithmName(algorithm);
  const option = ALGORITHM_OPTIONS.find(opt => opt.key === normalized);
  return option?.pipeline || "unknown";
}

/**
 * Check if algorithm supports local search configuration
 * Pipeline A algorithms support local search, Pipeline B has built-in local search
 */
export function algorithmSupportsLocalSearch(algorithm: string): boolean {
  const normalized = normalizeAlgorithmName(algorithm);
  const pipelineAAlgorithms: string[] = [
    PIPELINE_A_KEYS.GENETIC_ALGORITHM,
    PIPELINE_A_KEYS.GA,
    PIPELINE_A_KEYS.PSO,
    PIPELINE_A_KEYS.GWO,
    PIPELINE_A_KEYS.GREY_WOLF,
    PIPELINE_A_KEYS.HHO,
    PIPELINE_A_KEYS.HARRIS_HAWKS,
  ];
  return pipelineAAlgorithms.includes(normalized);
}

/**
 * Check if algorithm is a Split-based algorithm (Pipeline B)
 */
export function isSplitAlgorithm(algorithm: string): boolean {
  const normalized = normalizeAlgorithmName(algorithm);
  const splitAlgorithms: string[] = [
    PIPELINE_B_KEYS.GA_SPLIT,
    PIPELINE_B_KEYS.GA_SPLIT_ALIAS,
    PIPELINE_B_KEYS.PSO_SPLIT,
    PIPELINE_B_KEYS.PSO_SPLIT_ALIAS,
    PIPELINE_B_KEYS.GWO_SPLIT,
    PIPELINE_B_KEYS.GWO_SPLIT_ALIAS,
    PIPELINE_B_KEYS.HHO_SPLIT,
    PIPELINE_B_KEYS.HHO_SPLIT_ALIAS,
  ];
  return splitAlgorithms.includes(normalized);
}

/**
 * Get recommended algorithm based on problem size
 */
export function getRecommendedAlgorithm(nStudents: number): string {
  if (nStudents <= 30) {
    return PIPELINE_B_KEYS.GA_SPLIT; // Best quality for small instances
  } else if (nStudents <= 100) {
    return PIPELINE_B_KEYS.PSO_SPLIT; // Good balance
  } else {
    return HOLISTIC_KEYS.ORTOOLS_CVRP; // Reliable for large instances
  }
}
