/**
 * 2-opt Strategy
 * Local search algorithm that improves an existing route by reversing segments
 * Time complexity: O(n²) per iteration, typically O(n³) total
 * Quality: Good improvement over greedy solutions
 * 
 * The algorithm:
 * 1. Start with an initial route (using nearest neighbor)
 * 2. Try all possible 2-edge swaps
 * 3. If a swap improves the route, apply it
 * 4. Repeat until no improvement is found
 */

import type { RouteStrategy, StrategyCalculationResult, RouteDetail } from "./types";
import { NearestNeighborStrategy } from "./nearest-neighbor-strategy";

export class TwoOptStrategy implements RouteStrategy {
    name = "two-opt";

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

        if (waypoints.length === 1) {
            // For single waypoint, no optimization needed
            const nnStrategy = new NearestNeighborStrategy();
            return nnStrategy.calculateOptimalRoute(start, end, waypoints, calculateDistanceFunction);
        }

        // Start with nearest neighbor solution
        const nnStrategy = new NearestNeighborStrategy();
        const initialSolution = await nnStrategy.calculateOptimalRoute(
            start,
            end,
            waypoints,
            calculateDistanceFunction
        );

        // Extract the path from route details
        let path = [start];
        for (const detail of initialSolution.routeDetails) {
            if (detail.location2 !== path[path.length - 1]) {
                path.push(detail.location2);
            }
        }

        // Apply 2-opt improvement
        let improved = true;
        let iterations = 0;
        const maxIterations = 100; // Prevent infinite loops

        while (improved && iterations < maxIterations) {
            improved = false;
            iterations++;

            for (let i = 1; i < path.length - 2; i++) {
                for (let j = i + 1; j < path.length - 1; j++) {
                    const delta = this.calculate2OptDelta(
                        path,
                        i,
                        j,
                        calculateDistanceFunction
                    );

                    if (delta < -0.0001) { // Small epsilon to avoid floating point issues
                        // Reverse the segment between i and j
                        const newPath = [
                            ...path.slice(0, i),
                            ...path.slice(i, j + 1).reverse(),
                            ...path.slice(j + 1),
                        ];
                        path = newPath;
                        improved = true;
                    }
                }
            }
        }

        // Build route details from optimized path
        const routeDetails: RouteDetail[] = [];
        let totalDuration = 0;

        for (let i = 0; i < path.length - 1; i++) {
            const duration = calculateDistanceFunction(path[i], path[i + 1]);
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

    /**
     * Calculate the change in distance if we reverse the segment between i and j
     */
    private calculate2OptDelta(
        path: string[],
        i: number,
        j: number,
        calculateDistanceFunction: (from: string, to: string) => number
    ): number {
        const a = path[i - 1];
        const b = path[i];
        const c = path[j];
        const d = path[j + 1];

        // Current distance: a-b + c-d
        // New distance: a-c + b-d (after reversing b...c)
        const currentDistance =
            calculateDistanceFunction(a, b) + calculateDistanceFunction(c, d);
        const newDistance =
            calculateDistanceFunction(a, c) + calculateDistanceFunction(b, d);

        return newDistance - currentDistance;
    }
}
