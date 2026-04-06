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
  pso: new PSOStrategy(),
};

export interface StrategyInfo {
  name: string;
  displayName: string;
  description: string;
  timeComplexity: string;
  recommended: boolean;
}

const strategyInfo: StrategyInfo[] = [
  {
    name: "permutation",
    displayName: "Permütasyon (Brute Force)",
    description: "Tüm olası rotaları dener. Küçük problemler için optimal çözüm garanti edilir.",
    timeComplexity: "O(n!)",
    recommended: false,
  },
  {
    name: "nearest-neighbor",
    displayName: "En Yakın Komşu",
    description: "Her adımda en yakın konumu seçer. Hızlı ancak optimal olmayabilir.",
    timeComplexity: "O(n²)",
    recommended: false,
  },
  {
    name: "two-opt",
    description: "En yakından başlayıp yerel arama ile iyileştirir. Dengeli performans.",
    displayName: "2-Opt Yerel Arama",
    timeComplexity: "O(n³)",
    recommended: true,
  },
  {
    name: "genetic-algorithm",
    displayName: "Genetik Algoritma",
    description: "Popülasyon tabanlı meta-sezgisel algoritma. Büyük problemler için ideal.",
    timeComplexity: "O(generations × population × n²)",
    recommended: true,
  },
  {
    name: "pso",
    displayName: "Parçacık Sürü Optimizasyonu",
    description: "Sürü zekası tabanlı meta-sezgisel algoritma. Hızlı yakınsama.",
    timeComplexity: "O(iterations × swarm × n²)",
    recommended: true,
  },
];

export const getStrategy = (name?: string): RouteStrategy | null => {
  if (!name) return getDefaultStrategy();
  return strategies[name] || null;
};

export const getDefaultStrategy = (): RouteStrategy => {
  // Default to Genetic Algorithm for good balance of speed and quality
  return strategies["genetic-algorithm"];
};

export const getAvailableStrategies = (): StrategyInfo[] => {
  return strategyInfo;
};

export { GeneticAlgorithmStrategy, PSOStrategy };
export type { RouteStrategy, StrategyCalculationResult, RouteDetail, GAConfig, PSOConfig } from "./types";
