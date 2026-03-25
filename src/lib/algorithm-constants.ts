/**
 * Algorithm Constants
 * Single source of truth for algorithm names across UI and Python API
 * 
 * IMPORTANT: These names MUST match Python STRATEGY_REGISTRY keys
 * See: optimizer_api/strategies/__init__.py
 */

// Algorithm keys - MUST match Python exactly
export const ALGORITHM_KEYS = {
  GENETIC_ALGORITHM: "genetic_algorithm",
  GA: "ga", // Alias for genetic_algorithm
  PSO: "pso",
  GWO: "gwo",
  GREY_WOLF: "grey_wolf", // Alias for gwo
  HHO: "hho",
  HARRIS_HAWKS: "harris_hawks", // Alias for hho
  TWO_OPT: "two_opt", // Standalone 2-opt local search
  GREEDY: "greedy",
  NEAREST_NEIGHBOR: "nearest_neighbor", // Alias for greedy
  PERMUTATION_TSP: "permutation_tsp",
  PERMUTATION: "permutation", // Alias for permutation_tsp
  ORTOOLS_CVRP: "ortools_cvrp",
  ORTOOLS: "ortools", // Alias for ortools_cvrp
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

// Algorithm display names for UI
export const ALGORITHM_DISPLAY_NAMES: Record<string, string> = {
  [ALGORITHM_KEYS.GENETIC_ALGORITHM]: "Genetik Algoritma",
  [ALGORITHM_KEYS.GA]: "Genetik Algoritma",
  [ALGORITHM_KEYS.PSO]: "Parçacık Sürü Optimizasyonu",
  [ALGORITHM_KEYS.GWO]: "Gri Kurt Optimizasyonu",
  [ALGORITHM_KEYS.GREY_WOLF]: "Gri Kurt Optimizasyonu",
  [ALGORITHM_KEYS.HHO]: "Harris Hawks Optimizasyonu",
  [ALGORITHM_KEYS.HARRIS_HAWKS]: "Harris Hawks Optimizasyonu",
  [ALGORITHM_KEYS.TWO_OPT]: "Two-Opt Local Search",
  [ALGORITHM_KEYS.GREEDY]: "Greedy (En Yakın Komşu)",
  [ALGORITHM_KEYS.NEAREST_NEIGHBOR]: "Greedy (En Yakın Komşu)",
  [ALGORITHM_KEYS.PERMUTATION_TSP]: "Permütasyon (Optimal)",
  [ALGORITHM_KEYS.PERMUTATION]: "Permütasyon (Optimal)",
  [ALGORITHM_KEYS.ORTOOLS_CVRP]: "OR-Tools CVRP",
  [ALGORITHM_KEYS.ORTOOLS]: "OR-Tools CVRP",
};

// Local Search display names for UI
export const LOCAL_SEARCH_DISPLAY_NAMES: Record<LocalSearchType, string> = {
  [LOCAL_SEARCH_KEYS.NONE]: "Yok",
  [LOCAL_SEARCH_KEYS.TWO_OPT]: "2-Opt (Klasik)",
  [LOCAL_SEARCH_KEYS.THREE_OPT]: "3-Opt (Yüksek Kalite)",
  [LOCAL_SEARCH_KEYS.OR_OPT]: "Or-Opt (Kümeleme)",
  [LOCAL_SEARCH_KEYS.HYBRID]: "Hibrit (Kombine)",
};

// Algorithm descriptions
export const ALGORITHM_DESCRIPTIONS: Record<string, string> = {
  [ALGORITHM_KEYS.GENETIC_ALGORITHM]: "Popülasyon tabanlı meta-sezgisel optimizasyon. Büyük problemler için ideal.",
  [ALGORITHM_KEYS.PSO]: "Sürü zekası tabanlı meta-sezgisel. Hızlı yakınsama özelliği.",
  [ALGORITHM_KEYS.GWO]: "Sosyal hiyerarşi tabanlı meta-sezgisel. Keşif-sömürü dengesi güçlü.",
  [ALGORITHM_KEYS.HHO]: "Şahin avlanma davranışı tabanlı meta-sezgisel. Kaçış enerjisi ile adaptif arama.",
  [ALGORITHM_KEYS.TWO_OPT]: "Klasik 2-opt yerel arama algoritması. Küçük-orta ölçekli problemler için ideal.",
  [ALGORITHM_KEYS.GREEDY]: "Hızlı sezgisel algoritma. En yakın öğrenciyi her adımda seçer.",
  [ALGORITHM_KEYS.PERMUTATION_TSP]: "Tüm kombinasyonları dener, en iyi sonucu garanti eder. n ≤ 10 için kullanılabilir.",
  [ALGORITHM_KEYS.ORTOOLS_CVRP]: "Google OR-Tools kütüphanesi ile endüstri standardı VRP çözümü.",
};

// Local Search descriptions
export const LOCAL_SEARCH_DESCRIPTIONS: Record<LocalSearchType, string> = {
  [LOCAL_SEARCH_KEYS.NONE]: "Yerel arama uygulanmaz.",
  [LOCAL_SEARCH_KEYS.TWO_OPT]: "Kenar değiştirme ile iyileştirme. Hızlı ve etkili.",
  [LOCAL_SEARCH_KEYS.THREE_OPT]: "3 kenar değiştirme ile daha güçlü iyileştirme. Daha yavaş ama daha kaliteli.",
  [LOCAL_SEARCH_KEYS.OR_OPT]: "Alt tur yeniden konumlandırma. Kümeleme için etkili.",
  [LOCAL_SEARCH_KEYS.HYBRID]: "2-opt + 3-opt + Or-opt kombine. En iyi kalite, en yavaş.",
};

// Algorithm complexity
export const ALGORITHM_COMPLEXITY: Record<string, string> = {
  [ALGORITHM_KEYS.GENETIC_ALGORITHM]: "O(g × p × n²)",
  [ALGORITHM_KEYS.PSO]: "O(i × s × n²)",
  [ALGORITHM_KEYS.GWO]: "O(i × p × n²)",
  [ALGORITHM_KEYS.HHO]: "O(i × h × n²)",
  [ALGORITHM_KEYS.TWO_OPT]: "O(n²)",
  [ALGORITHM_KEYS.GREEDY]: "O(n²)",
  [ALGORITHM_KEYS.PERMUTATION_TSP]: "O(n!)",
  [ALGORITHM_KEYS.ORTOOLS_CVRP]: "O(n³)",
};

// Algorithm select options for UI dropdowns
export const ALGORITHM_OPTIONS = [
  {
    key: ALGORITHM_KEYS.GENETIC_ALGORITHM,
    label: ALGORITHM_DISPLAY_NAMES[ALGORITHM_KEYS.GENETIC_ALGORITHM],
    description: ALGORITHM_DESCRIPTIONS[ALGORITHM_KEYS.GENETIC_ALGORITHM],
    complexity: ALGORITHM_COMPLEXITY[ALGORITHM_KEYS.GENETIC_ALGORITHM],
    recommended: true,
  },
  {
    key: ALGORITHM_KEYS.PSO,
    label: ALGORITHM_DISPLAY_NAMES[ALGORITHM_KEYS.PSO],
    description: ALGORITHM_DESCRIPTIONS[ALGORITHM_KEYS.PSO],
    complexity: ALGORITHM_COMPLEXITY[ALGORITHM_KEYS.PSO],
    recommended: true,
  },
  {
    key: ALGORITHM_KEYS.GWO,
    label: ALGORITHM_DISPLAY_NAMES[ALGORITHM_KEYS.GWO],
    description: ALGORITHM_DESCRIPTIONS[ALGORITHM_KEYS.GWO],
    complexity: ALGORITHM_COMPLEXITY[ALGORITHM_KEYS.GWO],
    recommended: true,
  },
  {
    key: ALGORITHM_KEYS.HHO,
    label: ALGORITHM_DISPLAY_NAMES[ALGORITHM_KEYS.HHO],
    description: ALGORITHM_DESCRIPTIONS[ALGORITHM_KEYS.HHO],
    complexity: ALGORITHM_COMPLEXITY[ALGORITHM_KEYS.HHO],
    recommended: true,
  },
  {
    key: ALGORITHM_KEYS.TWO_OPT,
    label: ALGORITHM_DISPLAY_NAMES[ALGORITHM_KEYS.TWO_OPT],
    description: ALGORITHM_DESCRIPTIONS[ALGORITHM_KEYS.TWO_OPT],
    complexity: ALGORITHM_COMPLEXITY[ALGORITHM_KEYS.TWO_OPT],
    recommended: false,
  },
  {
    key: ALGORITHM_KEYS.GREEDY,
    label: ALGORITHM_DISPLAY_NAMES[ALGORITHM_KEYS.GREEDY],
    description: ALGORITHM_DESCRIPTIONS[ALGORITHM_KEYS.GREEDY],
    complexity: ALGORITHM_COMPLEXITY[ALGORITHM_KEYS.GREEDY],
    recommended: false,
  },
  {
    key: ALGORITHM_KEYS.PERMUTATION_TSP,
    label: ALGORITHM_DISPLAY_NAMES[ALGORITHM_KEYS.PERMUTATION_TSP],
    description: ALGORITHM_DESCRIPTIONS[ALGORITHM_KEYS.PERMUTATION_TSP],
    complexity: ALGORITHM_COMPLEXITY[ALGORITHM_KEYS.PERMUTATION_TSP],
    recommended: false,
  },
  {
    key: ALGORITHM_KEYS.ORTOOLS_CVRP,
    label: ALGORITHM_DISPLAY_NAMES[ALGORITHM_KEYS.ORTOOLS_CVRP],
    description: ALGORITHM_DESCRIPTIONS[ALGORITHM_KEYS.ORTOOLS_CVRP],
    complexity: ALGORITHM_COMPLEXITY[ALGORITHM_KEYS.ORTOOLS_CVRP],
    recommended: false,
  },
];

// Local Search options for UI dropdowns (used with meta-heuristics)
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

// Legacy mapping for backward compatibility
// Maps old UI names to correct Python keys
export const LEGACY_ALGORITHM_MAP: Record<string, string> = {
  "nearest-neighbor": ALGORITHM_KEYS.GREEDY,
  "two-opt": ALGORITHM_KEYS.TWO_OPT, // Now maps to standalone two_opt strategy
  "permutation": ALGORITHM_KEYS.PERMUTATION_TSP,
};

/**
 * Normalize algorithm name to canonical Python key
 */
export function normalizeAlgorithmName(name: string): string {
  // Check legacy mapping first
  if (LEGACY_ALGORITHM_MAP[name]) {
    return LEGACY_ALGORITHM_MAP[name];
  }
  // Return as-is if no mapping needed
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
 * Check if algorithm supports local search configuration
 * Meta-heuristics (GA, PSO, GWO, HHO) support local search, others don't
 */
export function algorithmSupportsLocalSearch(algorithm: string): boolean {
  const normalized = normalizeAlgorithmName(algorithm);
  const algorithms: string[] = [
    ALGORITHM_KEYS.GENETIC_ALGORITHM,
    ALGORITHM_KEYS.GA,
    ALGORITHM_KEYS.PSO,
    ALGORITHM_KEYS.GWO,
    ALGORITHM_KEYS.GREY_WOLF,
    ALGORITHM_KEYS.HHO,
    ALGORITHM_KEYS.HARRIS_HAWKS,
  ];
  return algorithms.includes(normalized);
}
