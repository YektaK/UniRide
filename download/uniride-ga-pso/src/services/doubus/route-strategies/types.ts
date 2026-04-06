/**
 * Route Strategy Types
 * Common interfaces for all route optimization strategies
 */

export interface RouteDetail {
  location1: string;
  location2: string;
  duration: number; // in minutes
}

export interface StrategyCalculationResult {
  routeDetails: RouteDetail[];
  totalDuration: number;
}

export interface RouteStrategy {
  name: string;
  calculateOptimalRoute: (
    start: string,
    end: string,
    waypoints: string[],
    calculateDistanceFunction: (from: string, to: string) => number
  ) => Promise<StrategyCalculationResult>;
}

/**
 * Configuration for metaheuristic algorithms (GA, PSO)
 */
export interface MetaheuristicConfig {
  maxIterations: number;
  maxNoImprovement: number;
  seed?: number;
}

export interface GAConfig extends MetaheuristicConfig {
  populationSize: number;
  eliteCount: number;
  crossoverRate: number;
  mutationRate: number;
  tournamentSize: number;
}

export interface PSOConfig extends MetaheuristicConfig {
  swarmSize: number;
  inertiaWeight: number;      // w: [0.4, 0.9] typically
  cognitiveWeight: number;    // c1: usually 1.5-2.0
  socialWeight: number;       // c2: usually 1.5-2.0
  velocityClamp: number;      // max velocity magnitude
}

/**
 * Default configurations based on literature
 * References:
 * - Goldberg, D. E. (1989). Genetic Algorithms in Search, Optimization and Machine Learning
 * - Kennedy, J., & Eberhart, R. (1995). Particle Swarm Optimization
 * - Clerc, M., & Kennedy, J. (2002). The particle swarm-explosion, stability, and convergence
 */
export const DEFAULT_GA_CONFIG: GAConfig = {
  populationSize: 100,
  eliteCount: 10,
  crossoverRate: 0.85,
  mutationRate: 0.15,
  tournamentSize: 5,
  maxIterations: 500,
  maxNoImprovement: 100,
};

export const DEFAULT_PSO_CONFIG: PSOConfig = {
  swarmSize: 50,
  inertiaWeight: 0.729,      // Clerc's constriction factor
  cognitiveWeight: 1.49445,   // c1 = c2 = 2.05 / κ where κ = 1
  socialWeight: 1.49445,
  velocityClamp: 6,
  maxIterations: 300,
  maxNoImprovement: 80,
};
