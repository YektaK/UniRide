/**
 * DouBus Route Optimization Service
 * Adapted from DouBus project for UniRide integration
 */

export interface Route {
  start: string;
  end: string;
  distanceKm: number;
  durationMinutes: number;
  routeDetails: RouteDetail[];
}

export interface RouteDetail {
  location1: string;
  location2: string;
  duration: number; // in minutes
}

/**
 * All available locations (from DouBus)
 */
export const ALL_LOCATIONS = [
  "D.Kampus",
  "Sw1", "Sw2", "Sw3", "Sw4", "Sw5", "Sw6", "Sw7", "Sw8", "Sw9",
  "So1", "So2", "So3", "So4", "So5", "So6", "So7", "So8", "So9",
  "So10", "So11", "So12", "So13", "So14", "So15", "So16", "So17", "So18", "So19"
] as const;

export type LocationCode = typeof ALL_LOCATIONS[number];

/**
 * Travel time matrix (non-symmetric) in minutes
 * Complete 29x29 matrix from DouBus project - represents actual travel times between all locations
 */
const travelTimes: Record<string, Record<string, number>> = {
  "D.Kampus": { "D.Kampus": 0, "Sw1": 40, "Sw2": 24, "Sw3": 9, "Sw4": 30, "Sw5": 35, "Sw6": 28, "Sw7": 26, "Sw8": 14, "Sw9": 28, "So1": 7, "So2": 18, "So3": 30, "So4": 30, "So5": 24, "So6": 50, "So7": 10, "So8": 22, "So9": 10, "So10": 10, "So11": 14, "So12": 20, "So13": 22, "So14": 18, "So15": 26, "So16": 28, "So17": 45, "So18": 30, "So19": 18 },
  "Sw1": { "D.Kampus": 37, "Sw1": 0, "Sw2": 34, "Sw3": 36, "Sw4": 47, "Sw5": 13, "Sw6": 41, "Sw7": 34, "Sw8": 36, "Sw9": 43, "So1": 37, "So2": 35, "So3": 46, "So4": 33, "So5": 35, "So6": 57, "So7": 41, "So8": 43, "So9": 39, "So10": 40, "So11": 41, "So12": 44, "So13": 38, "So14": 40, "So15": 25, "So16": 25, "So17": 54, "So18": 41, "So19": 34 },
  "Sw2": { "D.Kampus": 22, "Sw1": 36, "Sw2": 0, "Sw3": 21, "Sw4": 25, "Sw5": 29, "Sw6": 18, "Sw7": 4, "Sw8": 27, "Sw9": 21, "So1": 25, "So2": 9, "So3": 25, "So4": 7, "So5": 8, "So6": 40, "So7": 21, "So8": 20, "So9": 23, "So10": 22, "So11": 20, "So12": 20, "So13": 14, "So14": 15, "So15": 20, "So16": 17, "So17": 38, "So18": 18, "So19": 10 },
  "Sw3": { "D.Kampus": 7, "Sw1": 36, "Sw2": 21, "Sw3": 0, "Sw4": 32, "Sw5": 29, "Sw6": 22, "Sw7": 21, "Sw8": 17, "Sw9": 22, "So1": 9, "So2": 18, "So3": 26, "So4": 21, "So5": 21, "So6": 44, "So7": 17, "So8": 21, "So9": 14, "So10": 16, "So11": 18, "So12": 20, "So13": 19, "So14": 18, "So15": 20, "So16": 22, "So17": 41, "So18": 24, "So19": 17 },
  "Sw4": { "D.Kampus": 25, "Sw1": 47, "Sw2": 22, "Sw3": 25, "Sw4": 0, "Sw5": 39, "Sw6": 12, "Sw7": 20, "Sw8": 28, "Sw9": 16, "So1": 25, "So2": 20, "So3": 17, "So4": 21, "So5": 19, "So6": 40, "So7": 19, "So8": 14, "So9": 22, "So10": 21, "So11": 18, "So12": 19, "So13": 16, "So14": 15, "So15": 32, "So16": 31, "So17": 39, "So18": 8, "So19": 20 },
  "Sw5": { "D.Kampus": 31, "Sw1": 13, "Sw2": 28, "Sw3": 29, "Sw4": 40, "Sw5": 0, "Sw6": 37, "Sw7": 25, "Sw8": 30, "Sw9": 38, "So1": 31, "So2": 28, "So3": 43, "So4": 25, "So5": 28, "So6": 54, "So7": 35, "So8": 36, "So9": 34, "So10": 35, "So11": 35, "So12": 36, "So13": 31, "So14": 33, "So15": 18, "So16": 19, "So17": 49, "So18": 35, "So19": 28 },
  "Sw6": { "D.Kampus": 22, "Sw1": 41, "Sw2": 14, "Sw3": 21, "Sw4": 18, "Sw5": 33, "Sw6": 0, "Sw7": 13, "Sw8": 28, "Sw9": 18, "So1": 24, "So2": 13, "So3": 19, "So4": 14, "So5": 13, "So6": 40, "So7": 18, "So8": 15, "So9": 21, "So10": 21, "So11": 18, "So12": 15, "So13": 9, "So14": 11, "So15": 25, "So16": 24, "So17": 38, "So18": 10, "So19": 14 },
  "Sw7": { "D.Kampus": 22, "Sw1": 36, "Sw2": 3, "Sw3": 20, "Sw4": 26, "Sw5": 27, "Sw6": 19, "Sw7": 0, "Sw8": 25, "Sw9": 22, "So1": 25, "So2": 10, "So3": 25, "So4": 3, "So5": 9, "So6": 42, "So7": 21, "So8": 21, "So9": 23, "So10": 23, "So11": 21, "So12": 21, "So13": 14, "So14": 16, "So15": 19, "So16": 16, "So17": 40, "So18": 19, "So19": 11 },
  "Sw8": { "D.Kampus": 16, "Sw1": 35, "Sw2": 30, "Sw3": 18, "Sw4": 32, "Sw5": 27, "Sw6": 29, "Sw7": 27, "Sw8": 0, "Sw9": 24, "So1": 13, "So2": 27, "So3": 28, "So4": 26, "So5": 29, "So6": 38, "So7": 17, "So8": 22, "So9": 13, "So10": 18, "So11": 21, "So12": 24, "So13": 27, "So14": 25, "So15": 23, "So16": 26, "So17": 33, "So18": 32, "So19": 27 },
  "Sw9": { "D.Kampus": 19, "Sw1": 45, "Sw2": 18, "Sw3": 20, "Sw4": 19, "Sw5": 36, "Sw6": 17, "Sw7": 17, "Sw8": 21, "Sw9": 0, "So1": 18, "So2": 17, "So3": 8, "So4": 18, "So5": 17, "So6": 33, "So7": 11, "So8": 5, "So9": 14, "So10": 13, "So11": 11, "So12": 12, "So13": 14, "So14": 13, "So15": 28, "So16": 28, "So17": 33, "So18": 19, "So19": 17 },
  "So1": { "D.Kampus": 6, "Sw1": 39, "Sw2": 27, "Sw3": 10, "Sw4": 32, "Sw5": 32, "Sw6": 25, "Sw7": 25, "Sw8": 12, "Sw9": 22, "So1": 0, "So2": 22, "So3": 26, "So4": 26, "So5": 25, "So6": 37, "So7": 15, "So8": 20, "So9": 11, "So10": 15, "So11": 19, "So12": 23, "So13": 22, "So14": 21, "So15": 23, "So16": 26, "So17": 36, "So18": 26, "So19": 21 },
  "So2": { "D.Kampus": 16, "Sw1": 37, "Sw2": 9, "Sw3": 14, "Sw4": 22, "Sw5": 29, "Sw6": 14, "Sw7": 9, "Sw8": 26, "Sw9": 17, "So1": 19, "So2": 0, "So3": 22, "So4": 10, "So5": 8, "So6": 38, "So7": 17, "So8": 16, "So9": 19, "So10": 19, "So11": 16, "So12": 16, "So13": 10, "So14": 10, "So15": 21, "So16": 21, "So17": 37, "So18": 15, "So19": 1 },
  "So3": { "D.Kampus": 22, "Sw1": 44, "Sw2": 21, "Sw3": 23, "Sw4": 18, "Sw5": 38, "Sw6": 15, "Sw7": 20, "Sw8": 24, "Sw9": 7, "So1": 22, "So2": 20, "So3": 0, "So4": 21, "So5": 20, "So6": 31, "So7": 14, "So8": 9, "So9": 17, "So10": 16, "So11": 14, "So12": 16, "So13": 17, "So14": 16, "So15": 32, "So16": 32, "So17": 30, "So18": 17, "So19": 19 },
  "So4": { "D.Kampus": 21, "Sw1": 33, "Sw2": 5, "Sw3": 19, "Sw4": 25, "Sw5": 25, "Sw6": 18, "Sw7": 3, "Sw8": 24, "Sw9": 22, "So1": 26, "So2": 10, "So3": 25, "So4": 0, "So5": 12, "So6": 41, "So7": 21, "So8": 20, "So9": 24, "So10": 23, "So11": 21, "So12": 20, "So13": 14, "So14": 16, "So15": 17, "So16": 15, "So17": 39, "So18": 18, "So19": 11 },
  "So5": { "D.Kampus": 22, "Sw1": 36, "Sw2": 5, "Sw3": 20, "Sw4": 24, "Sw5": 29, "Sw6": 16, "Sw7": 6, "Sw8": 28, "Sw9": 19, "So1": 25, "So2": 7, "So3": 24, "So4": 8, "So5": 0, "So6": 40, "So7": 19, "So8": 18, "So9": 21, "So10": 21, "So11": 18, "So12": 18, "So13": 12, "So14": 14, "So15": 20, "So16": 17, "So17": 39, "So18": 16, "So19": 8 },
  "So6": { "D.Kampus": 37, "Sw1": 57, "Sw2": 37, "Sw3": 38, "Sw4": 39, "Sw5": 50, "Sw6": 35, "Sw7": 35, "Sw8": 38, "Sw9": 29, "So1": 38, "So2": 36, "So3": 31, "So4": 37, "So5": 35, "So6": 0, "So7": 30, "So8": 27, "So9": 33, "So10": 32, "So11": 30, "So12": 33, "So13": 33, "So14": 31, "So15": 43, "So16": 46, "So17": 10, "So18": 36, "So19": 35 },
  "So7": { "D.Kampus": 11, "Sw1": 42, "Sw2": 22, "Sw3": 16, "Sw4": 24, "Sw5": 36, "Sw6": 22, "Sw7": 21, "Sw8": 15, "Sw9": 14, "So1": 13, "So2": 21, "So3": 18, "So4": 22, "So5": 21, "So6": 35, "So7": 0, "So8": 13, "So9": 7, "So10": 4, "So11": 10, "So12": 14, "So13": 18, "So14": 17, "So15": 27, "So16": 30, "So17": 34, "So18": 23, "So19": 21 },
  "So8": { "D.Kampus": 17, "Sw1": 41, "Sw2": 16, "Sw3": 17, "Sw4": 17, "Sw5": 33, "Sw6": 15, "Sw7": 15, "Sw8": 19, "Sw9": 5, "So1": 16, "So2": 15, "So3": 10, "So4": 16, "So5": 14, "So6": 31, "So7": 8, "So8": 0, "So9": 11, "So10": 11, "So11": 8, "So12": 7, "So13": 12, "So14": 11, "So15": 26, "So16": 27, "So17": 30, "So18": 17, "So19": 14 },
  "So9": { "D.Kampus": 10, "Sw1": 39, "Sw2": 24, "Sw3": 15, "Sw4": 25, "Sw5": 32, "Sw6": 24, "Sw7": 23, "Sw8": 12, "Sw9": 15, "So1": 9, "So2": 22, "So3": 20, "So4": 23, "So5": 22, "So6": 34, "So7": 8, "So8": 14, "So9": 0, "So10": 8, "So11": 12, "So12": 14, "So13": 20, "So14": 18, "So15": 28, "So16": 31, "So17": 36, "So18": 24, "So19": 22 },
  "So10": { "D.Kampus": 11, "Sw1": 41, "Sw2": 24, "Sw3": 15, "Sw4": 25, "Sw5": 35, "Sw6": 24, "Sw7": 24, "Sw8": 17, "Sw9": 16, "So1": 13, "So2": 21, "So3": 20, "So4": 24, "So5": 22, "So6": 36, "So7": 4, "So8": 15, "So9": 9, "So10": 0, "So11": 8, "So12": 13, "So13": 19, "So14": 17, "So15": 26, "So16": 30, "So17": 35, "So18": 26, "So19": 21 },
  "So11": { "D.Kampus": 15, "Sw1": 41, "Sw2": 19, "Sw3": 19, "Sw4": 23, "Sw5": 35, "Sw6": 19, "Sw7": 18, "Sw8": 20, "Sw9": 13, "So1": 18, "So2": 18, "So3": 17, "So4": 19, "So5": 17, "So6": 34, "So7": 11, "So8": 11, "So9": 14, "So10": 7, "So11": 0, "So12": 7, "So13": 15, "So14": 13, "So15": 27, "So16": 30, "So17": 33, "So18": 20, "So19": 18 },
  "So12": { "D.Kampus": 17, "Sw1": 43, "Sw2": 16, "Sw3": 18, "Sw4": 23, "Sw5": 34, "Sw6": 14, "Sw7": 15, "Sw8": 21, "Sw9": 11, "So1": 18, "So2": 15, "So3": 16, "So4": 16, "So5": 14, "So6": 35, "So7": 11, "So8": 6, "So9": 13, "So10": 13, "So11": 6, "So12": 0, "So13": 12, "So14": 8, "So15": 26, "So16": 26, "So17": 34, "So18": 16, "So19": 14 },
  "So13": { "D.Kampus": 18, "Sw1": 39, "Sw2": 12, "Sw3": 18, "Sw4": 19, "Sw5": 32, "Sw6": 10, "Sw7": 11, "Sw8": 25, "Sw9": 16, "So1": 21, "So2": 12, "So3": 20, "So4": 12, "So5": 13, "So6": 39, "So7": 15, "So8": 15, "So9": 18, "So10": 17, "So11": 15, "So12": 14, "So13": 0, "So14": 9, "So15": 24, "So16": 24, "So17": 36, "So18": 12, "So19": 11 },
  "So14": { "D.Kampus": 17, "Sw1": 40, "Sw2": 13, "Sw3": 17, "Sw4": 19, "Sw5": 32, "Sw6": 12, "Sw7": 12, "Sw8": 24, "Sw9": 15, "So1": 20, "So2": 9, "So3": 19, "So4": 13, "So5": 11, "So6": 35, "So7": 14, "So8": 12, "So9": 17, "So10": 16, "So11": 13, "So12": 8, "So13": 7, "So14": 0, "So15": 25, "So16": 24, "So17": 35, "So18": 12, "So19": 8 },
  "So15": { "D.Kampus": 24, "Sw1": 23, "Sw2": 21, "Sw3": 23, "Sw4": 34, "Sw5": 19, "Sw6": 28, "Sw7": 18, "Sw8": 24, "Sw9": 31, "So1": 25, "So2": 21, "So3": 35, "So4": 18, "So5": 22, "So6": 48, "So7": 29, "So8": 30, "So9": 29, "So10": 28, "So11": 30, "So12": 29, "So13": 24, "So14": 25, "So15": 0, "So16": 4, "So17": 46, "So18": 29, "So19": 21 },
  "So16": { "D.Kampus": 26, "Sw1": 25, "Sw2": 18, "Sw3": 25, "Sw4": 34, "Sw5": 20, "Sw6": 28, "Sw7": 16, "Sw8": 25, "Sw9": 31, "So1": 26, "So2": 21, "So3": 34, "So4": 16, "So5": 20, "So6": 47, "So7": 30, "So8": 29, "So9": 30, "So10": 30, "So11": 30, "So12": 29, "So13": 24, "So14": 25, "So15": 4, "So16": 0, "So17": 46, "So18": 28, "So19": 21 },
  "So17": { "D.Kampus": 36, "Sw1": 53, "Sw2": 35, "Sw3": 36, "Sw4": 38, "Sw5": 45, "Sw6": 34, "Sw7": 34, "Sw8": 36, "Sw9": 27, "So1": 36, "So2": 34, "So3": 29, "So4": 35, "So5": 33, "So6": 10, "So7": 28, "So8": 26, "So9": 31, "So10": 30, "So11": 28, "So12": 30, "So13": 31, "So14": 30, "So15": 43, "So16": 44, "So17": 0, "So18": 35, "So19": 34 },
  "So18": { "D.Kampus": 24, "Sw1": 43, "Sw2": 16, "Sw3": 24, "Sw4": 13, "Sw5": 37, "Sw6": 11, "Sw7": 16, "Sw8": 30, "Sw9": 23, "So1": 27, "So2": 15, "So3": 23, "So4": 17, "So5": 15, "So6": 43, "So7": 21, "So8": 20, "So9": 23, "So10": 23, "So11": 21, "So12": 18, "So13": 11, "So14": 14, "So15": 28, "So16": 27, "So17": 40, "So18": 0, "So19": 16 },
  "So19": { "D.Kampus": 16, "Sw1": 37, "Sw2": 8, "Sw3": 14, "Sw4": 22, "Sw5": 29, "Sw6": 15, "Sw7": 9, "Sw8": 25, "Sw9": 17, "So1": 19, "So2": 1, "So3": 22, "So4": 11, "So5": 8, "So6": 38, "So7": 17, "So8": 16, "So9": 20, "So10": 20, "So11": 16, "So12": 17, "So13": 10, "So14": 11, "So15": 21, "So16": 22, "So17": 37, "So18": 15, "So19": 0 }
};

/**
 * Calculate travel time between two locations
 * Uses direct matrix lookup - complete 29x29 matrix
 */
export const calculateDistance = (from: string, to: string): number => {
  if (from === to) return 0;

  const duration = travelTimes[from]?.[to];

  if (duration === undefined) {
    return Infinity;
  }
  return duration;
};

/**
 * Get optimal route using permutation strategy
 * This is a simplified version - can be extended with other strategies
 */
export const getOptimalRoute = async (
  start: string,
  end: string,
  waypoints: string[],
  strategyName: string = "permutation"
): Promise<Route> => {
  // Legacy function - real optimization is handled by python API
  // This just returns a linear route through waypoints
  
  const routeDetails: RouteDetail[] = [];
  let totalDuration = 0;

  const path = [start, ...waypoints, end];

  for (let i = 0; i < path.length - 1; i++) {
    const duration = calculateDistance(path[i], path[i + 1]);
    totalDuration += duration;
    routeDetails.push({
      location1: path[i],
      location2: path[i + 1],
      duration,
    });
  }

  const totalDistance = (totalDuration / 60) * 40;

  return {
    start,
    end,
    distanceKm: totalDistance,
    durationMinutes: totalDuration,
    routeDetails,
  };
};

