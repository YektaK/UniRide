/**
 * Genetic Algorithm Strategy for Route Optimization
 *
 * Implementation based on:
 * - Holland, J. H. (1975). Adaptation in Natural and Artificial Systems
 * - Goldberg, D. E. (1989). Genetic Algorithms in Search, Optimization and Machine Learning
 * - Whitley, D. (1994). A Genetic Algorithm Tutorial
 *
 * Specialized for TSP (Traveling Salesman Problem) variant:
 * - Permutation encoding
 * - Order Crossover (OX1) for preserving valid tours
 * - Swap and Inversion mutation operators
 * - Tournament selection with elitism
 *
 * Time Complexity: O(generations * populationSize * n²)
 * Quality: Near-optimal for most instances
 */

import type {
  RouteStrategy,
  StrategyCalculationResult,
  RouteDetail,
  GAConfig,
} from "./types";
import { DEFAULT_GA_CONFIG } from "./types";

/**
 * Individual in the population representing a route permutation
 */
interface Individual {
  chromosome: string[]; // Ordered list of waypoints
  fitness: number; // 1 / totalDuration
  totalDuration: number;
}

/**
 * Seeded random number generator for reproducibility
 */
class SeededRandom {
  private seed: number;

  constructor(seed?: number) {
    this.seed = seed ?? Date.now();
  }

  next(): number {
    // Mulberry32 algorithm
    this.seed |= 0;
    this.seed = (this.seed + 0x6d2b79f5) | 0;
    let t = Math.imul(this.seed ^ (this.seed >>> 15), 1 | this.seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ (t >>> 14);
    return ((t ^ (t >>> 16)) >>> 0) / 4294967296;
  }

  nextInt(max: number): number {
    return Math.floor(this.next() * max);
  }

  shuffle<T>(array: T[]): T[] {
    const result = [...array];
    for (let i = result.length - 1; i > 0; i--) {
      const j = this.nextInt(i + 1);
      [result[i], result[j]] = [result[j], result[i]];
    }
    return result;
  }
}

export class GeneticAlgorithmStrategy implements RouteStrategy {
  name = "genetic-algorithm";
  displayName = "Genetik Algoritma";
  private config: GAConfig;
  private rng: SeededRandom;

  constructor(config?: Partial<GAConfig>) {
    this.config = { ...DEFAULT_GA_CONFIG, ...config };
    this.rng = new SeededRandom(this.config.seed);
  }

  async calculateOptimalRoute(
    start: string,
    end: string,
    waypoints: string[],
    calculateDistanceFunction: (from: string, to: string) => number
  ): Promise<StrategyCalculationResult> {
    // Edge case: no waypoints
    if (waypoints.length === 0) {
      const duration = calculateDistanceFunction(start, end);
      return {
        routeDetails: [{ location1: start, location2: end, duration }],
        totalDuration: duration,
      };
    }

    // Edge case: single waypoint
    if (waypoints.length === 1) {
      const d1 = calculateDistanceFunction(start, waypoints[0]);
      const d2 = calculateDistanceFunction(waypoints[0], end);
      return {
        routeDetails: [
          { location1: start, location2: waypoints[0], duration: d1 },
          { location1: waypoints[0], location2: end, duration: d2 },
        ],
        totalDuration: d1 + d2,
      };
    }

    // Initialize population
    let population = this.initializePopulation(waypoints);

    // Evaluate initial population
    population = this.evaluatePopulation(
      population,
      start,
      end,
      calculateDistanceFunction
    );

    let bestIndividual = this.getBestIndividual(population);
    let iterationsWithoutImprovement = 0;

    // Main evolution loop
    for (
      let generation = 0;
      generation < this.config.maxIterations;
      generation++
    ) {
      // Create new generation
      const newPopulation = this.evolve(population);

      // Evaluate new population
      const evaluatedPopulation = this.evaluatePopulation(
        newPopulation,
        start,
        end,
        calculateDistanceFunction
      );

      population = evaluatedPopulation;

      // Update best solution
      const currentBest = this.getBestIndividual(population);
      if (currentBest.totalDuration < bestIndividual.totalDuration) {
        bestIndividual = currentBest;
        iterationsWithoutImprovement = 0;
      } else {
        iterationsWithoutImprovement++;
      }

      // Early termination check
      if (iterationsWithoutImprovement >= this.config.maxNoImprovement) {
        break;
      }
    }

    // Convert best individual to result
    return this.individualToResult(
      bestIndividual,
      start,
      end,
      calculateDistanceFunction
    );
  }

  /**
   * Initialize population with random permutations
   */
  private initializePopulation(waypoints: string[]): Individual[] {
    const population: Individual[] = [];

    for (let i = 0; i < this.config.populationSize; i++) {
      population.push({
        chromosome: this.rng.shuffle([...waypoints]),
        fitness: 0,
        totalDuration: Infinity,
      });
    }

    return population;
  }

  /**
   * Evaluate fitness for all individuals in population
   */
  private evaluatePopulation(
    population: Individual[],
    start: string,
    end: string,
    calculateDistance: (from: string, to: string) => number
  ): Individual[] {
    return population.map((individual) => {
      const totalDuration = this.calculateRouteDuration(
        individual.chromosome,
        start,
        end,
        calculateDistance
      );

      return {
        ...individual,
        totalDuration,
        fitness: totalDuration === Infinity ? 0 : 1 / totalDuration,
      };
    });
  }

  /**
   * Calculate total route duration for a chromosome
   */
  private calculateRouteDuration(
    chromosome: string[],
    start: string,
    end: string,
    calculateDistance: (from: string, to: string) => number
  ): number {
    let total = 0;

    // Start to first waypoint
    total += calculateDistance(start, chromosome[0]);

    // Between waypoints
    for (let i = 0; i < chromosome.length - 1; i++) {
      total += calculateDistance(chromosome[i], chromosome[i + 1]);
    }

    // Last waypoint to end
    total += calculateDistance(chromosome[chromosome.length - 1], end);

    return total;
  }

  /**
   * Evolve population to create next generation
   */
  private evolve(population: Individual[]): Individual[] {
    const newPopulation: Individual[] = [];

    // Sort by fitness (descending)
    const sorted = [...population].sort((a, b) => b.fitness - a.fitness);

    // Elitism: preserve best individuals
    for (let i = 0; i < this.config.eliteCount; i++) {
      newPopulation.push({ ...sorted[i] });
    }

    // Generate offspring
    while (newPopulation.length < this.config.populationSize) {
      // Selection
      const parent1 = this.tournamentSelection(sorted);
      const parent2 = this.tournamentSelection(sorted);

      // Crossover
      if (this.rng.next() < this.config.crossoverRate) {
        const [child1, child2] = this.orderCrossover(
          parent1.chromosome,
          parent2.chromosome
        );

        // Mutation
        const mutatedChild1 =
          this.rng.next() < this.config.mutationRate
            ? this.mutate(child1)
            : child1;
        const mutatedChild2 =
          this.rng.next() < this.config.mutationRate
            ? this.mutate(child2)
            : child2;

        newPopulation.push(
          { chromosome: mutatedChild1, fitness: 0, totalDuration: Infinity },
          { chromosome: mutatedChild2, fitness: 0, totalDuration: Infinity }
        );
      } else {
        // No crossover, just copy parents with potential mutation
        const child1 =
          this.rng.next() < this.config.mutationRate
            ? this.mutate(parent1.chromosome)
            : [...parent1.chromosome];
        const child2 =
          this.rng.next() < this.config.mutationRate
            ? this.mutate(parent2.chromosome)
            : [...parent2.chromosome];

        newPopulation.push(
          { chromosome: child1, fitness: 0, totalDuration: Infinity },
          { chromosome: child2, fitness: 0, totalDuration: Infinity }
        );
      }
    }

    // Trim excess if population size exceeded
    return newPopulation.slice(0, this.config.populationSize);
  }

  /**
   * Tournament selection
   * Selects the best individual from a random subset
   */
  private tournamentSelection(population: Individual[]): Individual {
    let best: Individual | null = null;

    for (let i = 0; i < this.config.tournamentSize; i++) {
      const idx = this.rng.nextInt(population.length);
      const contestant = population[idx];

      if (!best || contestant.fitness > best.fitness) {
        best = contestant;
      }
    }

    return best!;
  }

  /**
   * Order Crossover (OX1)
   * Preserves relative order of elements from both parents
   *
   * Reference: Davis, L. (1985). Applying Adaptive Algorithms to Epistatic Domains
   */
  private orderCrossover(
    parent1: string[],
    parent2: string[]
  ): [string[], string[]] {
    const n = parent1.length;
    const child1: (string | null)[] = new Array(n).fill(null);
    const child2: (string | null)[] = new Array(n).fill(null);

    // Select random segment
    const startIdx = this.rng.nextInt(n);
    const endIdx = startIdx + this.rng.nextInt(n - startIdx);

    // Copy segment from parent1 to child1, parent2 to child2
    for (let i = startIdx; i <= endIdx; i++) {
      child1[i] = parent1[i];
      child2[i] = parent2[i];
    }

    // Fill remaining positions maintaining order from other parent
    this.fillRemaining(child1, parent2, startIdx, endIdx);
    this.fillRemaining(child2, parent1, startIdx, endIdx);

    return [child1 as string[], child2 as string[]];
  }

  /**
   * Fill remaining positions in crossover offspring
   */
  private fillRemaining(
    child: (string | null)[],
    parent: string[],
    startIdx: number,
    endIdx: number
  ): void {
    const n = child.length;
    const segment = new Set(child.slice(startIdx, endIdx + 1).filter(Boolean));

    // Find elements not in segment, in order they appear in parent
    const remaining: string[] = [];
    for (const gene of parent) {
      if (!segment.has(gene)) {
        remaining.push(gene);
      }
    }

    // Fill from position after segment, wrapping around
    let remainingIdx = 0;
    let childIdx = (endIdx + 1) % n;

    while (remainingIdx < remaining.length) {
      if (child[childIdx] === null) {
        child[childIdx] = remaining[remainingIdx];
        remainingIdx++;
      }
      childIdx = (childIdx + 1) % n;
    }
  }

  /**
   * Mutation operator: combination of swap and inversion
   */
  private mutate(chromosome: string[]): string[] {
    const mutated = [...chromosome];

    // 50% chance for each mutation type
    if (this.rng.next() < 0.5) {
      // Swap mutation: exchange two random positions
      const i = this.rng.nextInt(mutated.length);
      const j = this.rng.nextInt(mutated.length);
      [mutated[i], mutated[j]] = [mutated[j], mutated[i]];
    } else {
      // Inversion mutation: reverse a random segment
      const i = this.rng.nextInt(mutated.length);
      const j = this.rng.nextInt(mutated.length);
      let start = Math.min(i, j);
      let end = Math.max(i, j);

      while (start < end) {
        [mutated[start], mutated[end]] = [mutated[end], mutated[start]];
        start++;
        end--;
      }
    }

    return mutated;
  }

  /**
   * Get the best individual from population
   */
  private getBestIndividual(population: Individual[]): Individual {
    return population.reduce((best, current) =>
      current.fitness > best.fitness ? current : best
    );
  }

  /**
   * Convert individual to StrategyCalculationResult
   */
  private individualToResult(
    individual: Individual,
    start: string,
    end: string,
    calculateDistance: (from: string, to: string) => number
  ): StrategyCalculationResult {
    const routeDetails: RouteDetail[] = [];
    let totalDuration = 0;

    const path = [start, ...individual.chromosome, end];

    for (let i = 0; i < path.length - 1; i++) {
      const duration = calculateDistance(path[i], path[i + 1]);
      routeDetails.push({
        location1: path[i],
        location2: path[i + 1],
        duration,
      });
      totalDuration += duration;
    }

    return {
      routeDetails,
      totalDuration,
    };
  }
}
