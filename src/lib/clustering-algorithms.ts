/**
 * Clustering algorithm names accepted by the optimizer.
 *
 * MUST match SUPPORTED_CLUSTERING_ALGORITHMS in
 * uniride_core/algorithms/clustering_strategies/__init__.py (the keys of its
 * _CLUSTERING_STRATEGIES dict); clustering-algorithms.test.ts enforces the match.
 */
export const CLUSTERING_ALGORITHM_NAMES = [
  "kmeans",
  "fuzzy_cmeans",
  "fuzzy_cmeans_enhanced",
  "hierarchical_fcm",
  "k_medoids",
  "sweep",
  "clarke_wright",
] as const;

export type ClusteringAlgorithmName = (typeof CLUSTERING_ALGORITHM_NAMES)[number];

/** Option list for the admin selectors (display order, not registry order). */
export const CLUSTERING_ALGORITHM_OPTIONS: ReadonlyArray<{ name: ClusteringAlgorithmName; label: string }> = [
  { name: "sweep", label: "Sweep Algoritması (Önerilen)" },
  { name: "clarke_wright", label: "Clarke-Wright Savings" },
  { name: "k_medoids", label: "K-Medoids (Süre Tabanlı)" },
  { name: "fuzzy_cmeans", label: "Fuzzy C-Means" },
  { name: "fuzzy_cmeans_enhanced", label: "Enhanced Fuzzy C-Means" },
  { name: "hierarchical_fcm", label: "Hierarchical FCM (Büyük Veri)" },
  { name: "kmeans", label: "K-Means (Eski)" },
];
