/**
 * Nearest Neighbor Strategy
 * Greedy algorithm that always picks the closest unvisited location
 * Time complexity: O(n²)
 * Quality: Good for quick results, may not be optimal
 */

import type { RouteStrategy, StrategyCalculationResult, RouteDetail } from "./types";

export class NearestNeighborStrategy implements RouteStrategy {
    name = "nearest-neighbor";

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

        const routeDetails: RouteDetail[] = [];
        const unvisited = new Set(waypoints);
        let currentLocation = start;
        let totalDuration = 0;

        // Greedily visit the nearest unvisited location
        while (unvisited.size > 0) {
            let nearestLocation: string | null = null;
            let nearestDistance = Infinity;

            for (const location of unvisited) {
                const distance = calculateDistanceFunction(currentLocation, location);
                if (distance < nearestDistance) {
                    nearestDistance = distance;
                    nearestLocation = location;
                }
            }

            if (nearestLocation === null || nearestDistance === Infinity) {
                // No reachable location found, break
                break;
            }

            routeDetails.push({
                location1: currentLocation,
                location2: nearestLocation,
                duration: nearestDistance,
            });

            totalDuration += nearestDistance;
            unvisited.delete(nearestLocation);
            currentLocation = nearestLocation;
        }

        // Add final leg to destination
        const finalDistance = calculateDistanceFunction(currentLocation, end);
        if (finalDistance !== Infinity) {
            routeDetails.push({
                location1: currentLocation,
                location2: end,
                duration: finalDistance,
            });
            totalDuration += finalDistance;
        }

        return {
            routeDetails,
            totalDuration,
        };
    }
}
