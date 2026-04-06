/**
 * Particle Swarm Optimization Strategy for Route Optimization
 *
 * Implementation based on:
 * - Kennedy, J., & Eberhart, R. (1995). Particle Swarm Optimization
 * - Clerc, M., & Kennedy, J. (2002). The particle swarm-explosion, stability, and convergence
 * - Wang, K. P., et al. (2003). Particle Swarm Optimization for Traveling Salesman Problem
 *
 * Adapted for discrete combinatorial optimization (TSP):
 * - Position represented as permutation
 * - Velocity represented as sequence of swap operations
 * - Position update applies swap operations probabilistically
 *
 * Time Complexity: O(iterations * swarmSize * n²)
 * Quality: Near-optimal for most instances, good convergence properties
 */

import type {
  RouteStrategy,
  StrategyCalculationResult,
  RouteDetail,
  PSOConfig,
} from "./types";
import { DEFAULT_PSO_CONFIG } from "./types";

/**
 * Represents a swap operation for velocity
 */
interface SwapOperation {
  i: number;
  j: number;
  probability: number; // How strongly to apply this swap [0, 1]
}

/**
 * Velocity as a sequence of swap operations with probabilities
 */
type Velocity = SwapOperation[];

/**
 * Position as a permutation of waypoints
 */
type Position = string[];

/**
 * Particle in the swarm
 */
interface Particle {
  position: Position;
  velocity: Velocity;
  personalBest: Position;
  personalBestDuration: number;
  currentDuration: number;
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

export class PSOStrategy implements RouteStrategy {
  name = "pso";
  displayName = "Parçacık Sürü Optimizasyonu";
  private config: PSOConfig;
  private rng: SeededRandom;

  constructor(config?: Partial<PSOConfig>) {
    this.config = { ...DEFAULT_PSO_CONFIG, ...config };
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

    // Edge case: two waypoints - only 2 permutations possible
    if (waypoints.length === 2) {
      const perm1Duration = this.calculateRouteDuration(
        waypoints,
        start,
        end,
        calculateDistanceFunction
      );
      const perm2Duration = this.calculateRouteDuration(
        [waypoints[1], waypoints[0]],
        start,
        end,
        calculateDistanceFunction
      );

      const bestPermutation =
        perm1Duration <= perm2Duration ? waypoints : [waypoints[1], waypoints[0]];

      return this.positionToResult(
        bestPermutation,
        start,
        end,
        calculateDistanceFunction
      );
    }

    // Initialize swarm
    let swarm = this.initializeSwarm(waypoints);
    let globalBest: Position = [...swarm[0].position];
    let globalBestDuration = Infinity;

    // Evaluate initial swarm
    swarm = this.evaluateSwarm(swarm, start, end, calculateDistanceFunction);

    // Find initial global best
    for (const particle of swarm) {
      if (particle.personalBestDuration < globalBestDuration) {
        globalBest = [...particle.personalBest];
        globalBestDuration = particle.personalBestDuration;
      }
    }

    let iterationsWithoutImprovement = 0;

    // Main PSO loop
    for (let iter = 0; iter < this.config.maxIterations; iter++) {
      // Update velocities and positions
      swarm = this.updateSwarm(swarm, globalBest);

      // Evaluate new positions
      swarm = this.evaluateSwarm(swarm, start, end, calculateDistanceFunction);

      // Update personal and global bests
      let improved = false;
      for (const particle of swarm) {
        if (particle.currentDuration < particle.personalBestDuration) {
          particle.personalBest = [...particle.position];
          particle.personalBestDuration = particle.currentDuration;

          if (particle.personalBestDuration < globalBestDuration) {
            globalBest = [...particle.personalBest];
            globalBestDuration = particle.personalBestDuration;
            improved = true;
          }
        }
      }

      // Early termination check
      if (improved) {
        iterationsWithoutImprovement = 0;
      } else {
        iterationsWithoutImprovement++;
        if (iterationsWithoutImprovement >= this.config.maxNoImprovement) {
          break;
        }
      }
    }

    return this.positionToResult(
      globalBest,
      start,
      end,
      calculateDistanceFunction
    );
  }

  /**
   * Initialize swarm with random positions and velocities
   */
  private initializeSwarm(waypoints: string[]): Particle[] {
    const swarm: Particle[] = [];

    for (let i = 0; i < this.config.swarmSize; i++) {
      const position = this.rng.shuffle([...waypoints]);
      const velocity = this.generateRandomVelocity(waypoints.length);

      swarm.push({
        position,
        velocity,
        personalBest: [...position],
        personalBestDuration: Infinity,
        currentDuration: Infinity,
      });
    }

    return swarm;
  }

  /**
   * Generate random velocity (sequence of swaps with probabilities)
   */
  private generateRandomVelocity(n: number): Velocity {
    const velocity: Velocity = [];
    const numSwaps = Math.min(this.rng.nextInt(Math.floor(n / 2)) + 1, 5);

    for (let s = 0; s < numSwaps; s++) {
      velocity.push({
        i: this.rng.nextInt(n),
        j: this.rng.nextInt(n),
        probability: this.rng.next() * 0.5, // Low initial probability
      });
    }

    return velocity;
  }

  /**
   * Evaluate all particles in swarm
   */
  private evaluateSwarm(
    swarm: Particle[],
    start: string,
    end: string,
    calculateDistance: (from: string, to: string) => number
  ): Particle[] {
    return swarm.map((particle) => {
      const currentDuration = this.calculateRouteDuration(
        particle.position,
        start,
        end,
        calculateDistance
      );

      const personalBestDuration =
        particle.personalBestDuration === Infinity
          ? currentDuration
          : particle.personalBestDuration;

      return {
        ...particle,
        currentDuration,
        personalBestDuration,
      };
    });
  }

  /**
   * Calculate total route duration for a position
   */
  private calculateRouteDuration(
    position: Position,
    start: string,
    end: string,
    calculateDistance: (from: string, to: string) => number
  ): number {
    let total = 0;

    // Start to first waypoint
    total += calculateDistance(start, position[0]);

    // Between waypoints
    for (let i = 0; i < position.length - 1; i++) {
      total += calculateDistance(position[i], position[i + 1]);
    }

    // Last waypoint to end
    total += calculateDistance(position[position.length - 1], end);

    return total;
  }

  /**
   * Update velocities and positions for all particles
   *
   * Based on the canonical PSO equation:
   * v(t+1) = w * v(t) + c1 * r1 * (pbest - x(t)) + c2 * r2 * (gbest - x(t))
   *
   * For discrete PSO, we interpret this as:
   * - w * v(t): retain some of the previous velocity
   * - c1 * r1 * (pbest - x): swaps to move toward personal best
   * - c2 * r2 * (gbest - x): swaps to move toward global best
   */
  private updateSwarm(swarm: Particle[], globalBest: Position): Particle[] {
    return swarm.map((particle) => {
      // Calculate new velocity
      const newVelocity = this.calculateNewVelocity(
        particle.velocity,
        particle.position,
        particle.personalBest,
        globalBest
      );

      // Apply velocity to get new position
      const newPosition = this.applyVelocity(particle.position, newVelocity);

      return {
        ...particle,
        position: newPosition,
        velocity: newVelocity,
      };
    });
  }

  /**
   * Calculate new velocity using PSO equation
   */
  private calculateNewVelocity(
    currentVelocity: Velocity,
    currentPosition: Position,
    personalBest: Position,
    globalBest: Position
  ): Velocity {
    const n = currentPosition.length;
    const newVelocity: Velocity = [];

    // Inertia component: retain part of old velocity
    for (const swap of currentVelocity) {
      const adjustedProbability = swap.probability * this.config.inertiaWeight;
      if (adjustedProbability > 0.1) {
        // Threshold to prevent vanishing velocities
        newVelocity.push({
          ...swap,
          probability: Math.min(adjustedProbability, this.config.velocityClamp),
        });
      }
    }

    // Cognitive component: swaps toward personal best
    const pbestSwaps = this.getDifferenceSwaps(
      currentPosition,
      personalBest,
      this.config.cognitiveWeight
    );
    newVelocity.push(...pbestSwaps);

    // Social component: swaps toward global best
    const gbestSwaps = this.getDifferenceSwaps(
      currentPosition,
      globalBest,
      this.config.socialWeight
    );
    newVelocity.push(...gbestSwaps);

    // Limit velocity size
    return newVelocity.slice(0, this.config.velocityClamp * n);
  }

  /**
   * Get swaps needed to transform current into target
   * Returns a set of swaps with associated probabilities
   */
  private getDifferenceSwaps(
    current: Position,
    target: Position,
    weight: number
  ): Velocity {
    const swaps: Velocity = [];
    const n = current.length;

    // Find positions where current differs from target
    for (let i = 0; i < n; i++) {
      if (current[i] !== target[i]) {
        // Find where the target element is in current
        const j = current.indexOf(target[i]);
        if (j !== -1 && j !== i) {
          swaps.push({
            i,
            j,
            probability: weight * this.rng.next(),
          });
        }
      }
    }

    return swaps;
  }

  /**
   * Apply velocity (swaps) to position probabilistically
   */
  private applyVelocity(position: Position, velocity: Velocity): Position {
    const newPosition = [...position];

    for (const swap of velocity) {
      // Apply swap with probability
      if (this.rng.next() < swap.probability) {
        if (
          swap.i >= 0 &&
          swap.i < newPosition.length &&
          swap.j >= 0 &&
          swap.j < newPosition.length
        ) {
          [newPosition[swap.i], newPosition[swap.j]] = [
            newPosition[swap.j],
            newPosition[swap.i],
          ];
        }
      }
    }

    return newPosition;
  }

  /**
   * Convert position to StrategyCalculationResult
   */
  private positionToResult(
    position: Position,
    start: string,
    end: string,
    calculateDistance: (from: string, to: string) => number
  ): StrategyCalculationResult {
    const routeDetails: RouteDetail[] = [];
    let totalDuration = 0;

    const path = [start, ...position, end];

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
