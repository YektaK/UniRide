/**
 * Route Strategy Types
 */

export interface RouteDetail {
  location1: string;
  location2: string;
  duration: number;
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

