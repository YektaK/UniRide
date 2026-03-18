/**
 * Route Strategy Registry
 * Manages different route optimization strategies
 */

import { PermutationStrategy } from "./permutation-strategy";
import { NearestNeighborStrategy } from "./nearest-neighbor-strategy";
import { TwoOptStrategy } from "./two-opt-strategy";
import { GeneticAlgorithmStrategy } from "./ga-strategy";
import { PSOStrategy } from "./pso-strategy";
import type { RouteStrategy } from "./types";

const strategies: Record<string, RouteStrategy> = {
  permutation: new PermutationStrategy(),
  "nearest-neighbor": new NearestNeighborStrategy(),
  "two-opt": new TwoOptStrategy(),
  "genetic-algorithm": new GeneticAlgorithmStrategy(),
  "pso": new PSOStrategy(),
};

// Strategy metadata for UI
export interface StrategyInfo {
  name: string;
  label: string;
  description: string;
  complexity: string;
  recommended?: boolean;
}

const strategyInfo: StrategyInfo[] = [
  {
    name: "nearest-neighbor",
    label: "En Yakın Komşu (Hızlı)",
    description: "Greedy algoritma, hızlı sonuç verir ama optimal olmayabilir",
    complexity: "O(n²)",
    recommended: false,
  },
  {
    name: "two-opt",
    label: "2-opt İyileştirme (Dengeli)",
    description: "Nearest neighbor başlangıcı + lokal iyileştirme",
    complexity: "O(n³)",
    recommended: true,
  },
  {
    name: "genetic-algorithm",
    label: "Genetik Algoritma",
    description: "Popülasyon tabanlı meta-sezgisel. Büyük problemler için ideal.",
    complexity: "O(g × p × n²)",
    recommended: true,
  },
  {
    name: "pso",
    label: "Parçacık Sürü Optimizasyonu",
    description: "Sürü zekası tabanlı meta-sezgisel. Hızlı yakınsama.",
    complexity: "O(i × s × n²)",
    recommended: true,
  },
  {
    name: "permutation",
    label: "Permütasyon (Optimal)",
    description: "Tüm kombinasyonları dener, en iyi sonucu garanti eder (n ≤ 10)",
    complexity: "O(n!)",
    recommended: false,
  },
];

// Default strategy - can be overridden via environment variable
const DEFAULT_STRATEGY = process.env.ROUTE_OPTIMIZATION_STRATEGY || "genetic-algorithm";

/**
 * Get a route strategy by name
 */
export const getStrategy = (name?: string): RouteStrategy | null => {
  const strategyName = name || DEFAULT_STRATEGY;
  return strategies[strategyName] || null;
};

/**
 * Get the default strategy
 */
export const getDefaultStrategy = (): RouteStrategy => {
  return strategies[DEFAULT_STRATEGY] || strategies["genetic-algorithm"];
};

/**
 * Get all available strategies (just names)
 */
export const getAvailableStrategies = (): string[] => {
  return Object.keys(strategies);
};

/**
 * Get strategy info for UI
 */
export const getStrategyInfo = (): StrategyInfo[] => {
  return strategyInfo;
};

/**
 * Get info for a specific strategy
 */
export const getStrategyInfoByName = (name: string): StrategyInfo | undefined => {
  return strategyInfo.find(s => s.name === name);
};

// Export strategy classes for direct use
export { GeneticAlgorithmStrategy, PSOStrategy };
// Export types
export type { RouteStrategy, StrategyCalculationResult, RouteDetail, GAConfig, PSOConfig } from "./types";
