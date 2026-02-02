/**
 * Permutation Strategy
 * Tries all possible permutations of waypoints to find the shortest route
 */

import type { RouteStrategy, StrategyCalculationResult } from "./types";

/**
 * Generate all permutations of an array
 */
function permute<T>(array: T[]): T[][] {
  if (array.length <= 1) return [array];
  
  const result: T[][] = [];
  for (let i = 0; i < array.length; i++) {
    const rest = [...array.slice(0, i), ...array.slice(i + 1)];
    const perms = permute(rest);
    for (const perm of perms) {
      result.push([array[i], ...perm]);
    }
  }
  return result;
}

export class PermutationStrategy implements RouteStrategy {
  name = "permutation";
  
  async calculateOptimalRoute(
    start: string,
    end: string,
    waypoints: string[],
    calculateDistanceFunction: (from: string, to: string) => number
  ): Promise<StrategyCalculationResult> {
    if (waypoints.length === 0) {
      const duration = calculateDistanceFunction(start, end);
      return {
        routeDetails: [
          {
            location1: start,
            location2: end,
            duration,
          },
        ],
        totalDuration: duration,
      };
    }
    
    // Generate all permutations of waypoints
    const permutations = permute(waypoints);
    
    let bestRoute: StrategyCalculationResult | null = null;
    let bestDuration = Infinity;
    
    for (const perm of permutations) {
      const path = [start, ...perm, end];
      let totalDuration = 0;
      const routeDetails: StrategyCalculationResult["routeDetails"] = [];
      
      for (let i = 0; i < path.length - 1; i++) {
        const duration = calculateDistanceFunction(path[i], path[i + 1]);
        if (duration === Infinity) {
          totalDuration = Infinity;
          break;
        }
        totalDuration += duration;
        routeDetails.push({
          location1: path[i],
          location2: path[i + 1],
          duration,
        });
      }
      
      if (totalDuration < bestDuration) {
        bestDuration = totalDuration;
        bestRoute = {
          routeDetails,
          totalDuration,
        };
      }
    }
    
    if (!bestRoute) {
      throw new Error("No valid route found");
    }
    
    return bestRoute;
  }
}

