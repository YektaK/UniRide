/**
 * Route Strategy Benchmark and Testing Suite
 *
 * Provides comprehensive testing for route optimization strategies:
 * 1. Correctness tests - verify algorithms produce valid routes
 * 2. Optimality tests - compare against known optimal solutions
 * 3. Performance tests - measure execution time
 * 4. Comparative tests - compare strategies against each other
 *
 * Usage:
 * ```typescript
 * import { runBenchmark } from './strategy-benchmark';
 *
 * const results = await runBenchmark();
 * console.log(results);
 * ```
 */

import { GeneticAlgorithmStrategy } from "../ga-strategy";
import { PSOStrategy } from "../pso-strategy";
import type { RouteStrategy, StrategyCalculationResult } from "../types";

/**
 * Test scenario definition
 */
interface TestScenario {
  name: string;
  waypoints: string[];
  optimalKnown?: number; // Known optimal duration (if available)
  category: "trivial" | "small" | "medium" | "large";
}

/**
 * Benchmark result for a single test
 */
interface BenchmarkResult {
  scenario: string;
  strategy: string;
  totalDuration: number;
  executionTimeMs: number;
  isOptimal: boolean | null;
  routeLength: number;
  deviationFromOptimal?: number;
  routeOrder: string[];
}

/**
 * Aggregated benchmark statistics
 */
interface BenchmarkStats {
  strategy: string;
  avgDuration: number;
  avgExecutionTime: number;
  optimalCount: number;
  totalTests: number;
  avgDeviation: number;
}

/**
 * Predefined test scenarios
 * Based on typical UniRide use cases
 */
const TEST_SCENARIOS: TestScenario[] = [
  // Trivial cases (should always find optimal)
  {
    name: "Empty Route",
    waypoints: [],
    optimalKnown: 0,
    category: "trivial",
  },
  {
    name: "Single Waypoint",
    waypoints: ["Sw1"],
    optimalKnown: 0, // Will be calculated based on distance matrix
    category: "trivial",
  },
  {
    name: "Two Waypoints",
    waypoints: ["Sw1", "Sw2"],
    category: "trivial",
  },

  // Small cases (can verify with brute force)
  {
    name: "Small Cluster - 4 waypoints",
    waypoints: ["Sw1", "Sw2", "Sw3", "Sw4"],
    category: "small",
  },
  {
    name: "Mixed Locations - 5 waypoints",
    waypoints: ["Sw1", "Sw2", "So1", "So2", "D.Kampus"],
    category: "small",
  },

  // Medium cases (typical real-world scenarios)
  {
    name: "Morning Route - 8 waypoints",
    waypoints: ["Sw1", "Sw2", "Sw3", "So1", "So2", "So3", "Sw4", "D.Kampus"],
    category: "medium",
  },
  {
    name: "Afternoon Route - 10 waypoints",
    waypoints: [
      "Sw1",
      "Sw2",
      "Sw3",
      "Sw4",
      "So1",
      "So2",
      "So3",
      "So4",
      "So5",
      "D.Kampus",
    ],
    category: "medium",
  },

  // Large cases (stress test)
  {
    name: "Large Route - 15 waypoints",
    waypoints: [
      "Sw1",
      "Sw2",
      "Sw3",
      "Sw4",
      "Sw5",
      "So1",
      "So2",
      "So3",
      "So4",
      "So5",
      "So6",
      "So7",
      "Sw6",
      "Sw7",
      "D.Kampus",
    ],
    category: "large",
  },
];

/**
 * Sample distance matrix (symmetric, based on typical Istanbul distances)
 * In production, this would come from the actual DouBus distance matrix
 */
const SAMPLE_DISTANCE_MATRIX: Record<string, Record<string, number>> = {
  "D.Kampus": {
    "D.Kampus": 0,
    Sw1: 15,
    Sw2: 18,
    Sw3: 22,
    Sw4: 25,
    Sw5: 28,
    Sw6: 30,
    Sw7: 32,
    Sw8: 35,
    Sw9: 38,
    So1: 20,
    So2: 22,
    So3: 25,
    So4: 28,
    So5: 30,
    So6: 32,
    So7: 35,
    So8: 38,
    So9: 40,
    So10: 42,
    So11: 45,
    So12: 48,
    So13: 50,
    So14: 52,
    So15: 55,
    So16: 58,
    So17: 60,
    So18: 62,
    So19: 65,
  },
  Sw1: {
    "D.Kampus": 15,
    Sw1: 0,
    Sw2: 5,
    Sw3: 8,
    Sw4: 12,
    Sw5: 15,
    Sw6: 18,
    Sw7: 20,
    So1: 10,
    So2: 12,
    So3: 15,
  },
  Sw2: {
    "D.Kampus": 18,
    Sw1: 5,
    Sw2: 0,
    Sw3: 4,
    Sw4: 8,
    Sw5: 12,
    So1: 8,
    So2: 10,
  },
  Sw3: {
    "D.Kampus": 22,
    Sw1: 8,
    Sw2: 4,
    Sw3: 0,
    Sw4: 5,
    Sw5: 8,
    So1: 12,
    So2: 14,
  },
  Sw4: {
    "D.Kampus": 25,
    Sw1: 12,
    Sw2: 8,
    Sw3: 5,
    Sw4: 0,
    Sw5: 4,
    So1: 15,
  },
  Sw5: {
    "D.Kampus": 28,
    Sw1: 15,
    Sw2: 12,
    Sw3: 8,
    Sw4: 4,
    Sw5: 0,
    So2: 10,
  },
  Sw6: {
    "D.Kampus": 30,
    Sw4: 10,
    Sw5: 8,
    Sw6: 0,
    Sw7: 5,
  },
  Sw7: {
    "D.Kampus": 32,
    Sw5: 10,
    Sw6: 5,
    Sw7: 0,
    Sw8: 4,
  },
  Sw8: {
    "D.Kampus": 35,
    Sw6: 8,
    Sw7: 4,
    Sw8: 0,
    Sw9: 5,
  },
  Sw9: {
    "D.Kampus": 38,
    Sw7: 10,
    Sw8: 5,
    Sw9: 0,
  },
  So1: {
    "D.Kampus": 20,
    Sw1: 10,
    Sw2: 8,
    Sw3: 12,
    So1: 0,
    So2: 4,
    So3: 8,
    So4: 12,
    So5: 15,
  },
  So2: {
    "D.Kampus": 22,
    Sw1: 12,
    Sw2: 10,
    So1: 4,
    So2: 0,
    So3: 5,
    So4: 8,
    So5: 12,
  },
  So3: {
    "D.Kampus": 25,
    Sw2: 12,
    Sw3: 10,
    So1: 8,
    So2: 5,
    So3: 0,
    So4: 4,
    So5: 8,
  },
  So4: {
    "D.Kampus": 28,
    Sw3: 12,
    So1: 12,
    So2: 8,
    So3: 4,
    So4: 0,
    So5: 5,
    So6: 8,
  },
  So5: {
    "D.Kampus": 30,
    So1: 15,
    So2: 12,
    So3: 8,
    So4: 5,
    So5: 0,
    So6: 4,
    So7: 8,
  },
  So6: {
    "D.Kampus": 32,
    So2: 15,
    So3: 12,
    So4: 8,
    So5: 4,
    So6: 0,
    So7: 5,
    So8: 8,
  },
  So7: {
    "D.Kampus": 35,
    So3: 15,
    So4: 12,
    So5: 8,
    So6: 5,
    So7: 0,
    So8: 4,
    So9: 8,
  },
  So8: {
    "D.Kampus": 38,
    So4: 15,
    So5: 12,
    So6: 8,
    So7: 4,
    So8: 0,
    So9: 5,
    So10: 8,
  },
  So9: {
    "D.Kampus": 40,
    So5: 15,
    So6: 12,
    So7: 8,
    So8: 5,
    So9: 0,
    So10: 4,
  },
  So10: {
    "D.Kampus": 42,
    So6: 15,
    So7: 12,
    So8: 8,
    So9: 4,
    So10: 0,
    So11: 5,
  },
  So11: {
    "D.Kampus": 45,
    So7: 15,
    So8: 12,
    So9: 8,
    So10: 5,
    So11: 0,
    So12: 4,
  },
  So12: {
    "D.Kampus": 48,
    So8: 15,
    So9: 12,
    So10: 8,
    So11: 4,
    So12: 0,
    So13: 5,
  },
  So13: {
    "D.Kampus": 50,
    So9: 15,
    So10: 12,
    So11: 8,
    So12: 5,
    So13: 0,
    So14: 4,
  },
  So14: {
    "D.Kampus": 52,
    So10: 15,
    So11: 12,
    So12: 8,
    So13: 5,
    So14: 0,
    So15: 4,
  },
  So15: {
    "D.Kampus": 55,
    So11: 15,
    So12: 12,
    So13: 8,
    So14: 5,
    So15: 0,
    So16: 4,
  },
  So16: {
    "D.Kampus": 58,
    So12: 15,
    So13: 12,
    So14: 8,
    So15: 4,
    So16: 0,
    So17: 5,
  },
  So17: {
    "D.Kampus": 60,
    So13: 15,
    So14: 12,
    So15: 8,
    So16: 5,
    So17: 0,
    So18: 4,
  },
  So18: {
    "D.Kampus": 62,
    So14: 15,
    So15: 12,
    So16: 8,
    So17: 5,
    So18: 0,
    So19: 4,
  },
  So19: {
    "D.Kampus": 65,
    So15: 15,
    So16: 12,
    So17: 8,
    So18: 5,
    So19: 0,
  },
};

/**
 * Distance function using the sample matrix
 */
function getDistance(from: string, to: string): number {
  if (SAMPLE_DISTANCE_MATRIX[from]?.[to] !== undefined) {
    return SAMPLE_DISTANCE_MATRIX[from][to];
  }
  if (SAMPLE_DISTANCE_MATRIX[to]?.[from] !== undefined) {
    return SAMPLE_DISTANCE_MATRIX[to][from];
  }
  // Default distance for unknown pairs
  return 50;
}

/**
 * Brute force optimal solution for small instances (n <= 8)
 * Used for verification
 */
function bruteForceOptimal(
  waypoints: string[],
  start: string,
  end: string,
  getDistanceFn: (from: string, to: string) => number
): number {
  if (waypoints.length === 0) return getDistanceFn(start, end);
  if (waypoints.length === 1) {
    return getDistanceFn(start, waypoints[0]) + getDistanceFn(waypoints[0], end);
  }

  function permute(arr: string[]): string[][] {
    if (arr.length <= 1) return [arr];
    const result: string[][] = [];
    for (let i = 0; i < arr.length; i++) {
      const rest = [...arr.slice(0, i), ...arr.slice(i + 1)];
      for (const perm of permute(rest)) {
        result.push([arr[i], ...perm]);
      }
    }
    return result;
  }

  let best = Infinity;
  for (const perm of permute(waypoints)) {
    let duration = getDistanceFn(start, perm[0]);
    for (let i = 0; i < perm.length - 1; i++) {
      duration += getDistanceFn(perm[i], perm[i + 1]);
    }
    duration += getDistanceFn(perm[perm.length - 1], end);
    best = Math.min(best, duration);
  }

  return best;
}

/**
 * Run a single test with a strategy
 */
async function runTest(
  strategy: RouteStrategy,
  scenario: TestScenario,
  start: string,
  end: string
): Promise<BenchmarkResult> {
  const startTime = performance.now();

  const result = await strategy.calculateOptimalRoute(
    start,
    end,
    scenario.waypoints,
    getDistance
  );

  const executionTime = performance.now() - startTime;

  // Calculate optimal for small instances
  let isOptimal: boolean | null = null;
  let deviation = 0;

  if (scenario.waypoints.length <= 8) {
    const optimalDuration = bruteForceOptimal(
      scenario.waypoints,
      start,
      end,
      getDistance
    );
    isOptimal = Math.abs(result.totalDuration - optimalDuration) < 0.001;
    deviation = ((result.totalDuration - optimalDuration) / optimalDuration) * 100;
  }

  return {
    scenario: scenario.name,
    strategy: strategy.name,
    totalDuration: result.totalDuration,
    executionTimeMs: executionTime,
    isOptimal,
    routeLength: scenario.waypoints.length,
    deviationFromOptimal: deviation,
    routeOrder: result.routeDetails.map((r) => r.location1),
  };
}

/**
 * Main benchmark function
 * Tests all strategies across all scenarios
 */
export async function runBenchmark(): Promise<{
  results: BenchmarkResult[];
  stats: BenchmarkStats[];
  summary: string;
}> {
  const strategies: RouteStrategy[] = [
    new GeneticAlgorithmStrategy(),
    new PSOStrategy(),
  ];

  const results: BenchmarkResult[] = [];
  const start = "D.Kampus";
  const end = "D.Kampus"; // Return to campus

  console.log("Starting Route Strategy Benchmark...\n");

  for (const scenario of TEST_SCENARIOS) {
    console.log(`Testing: ${scenario.name} (${scenario.waypoints.length} waypoints)`);

    for (const strategy of strategies) {
      const result = await runTest(strategy, scenario, start, end);
      results.push(result);

      console.log(
        `  ${strategy.name}: ${result.totalDuration.toFixed(1)} min ` +
          `(${result.executionTimeMs.toFixed(2)}ms)` +
          (result.isOptimal !== null
            ? result.isOptimal
              ? " ✓ OPTIMAL"
              : ` ✗ (${result.deviationFromOptimal?.toFixed(1)}% deviation)`
            : "")
      );
    }
  }

  // Calculate statistics
  const stats: BenchmarkStats[] = strategies.map((strategy) => {
    const strategyResults = results.filter((r) => r.strategy === strategy.name);
    const optimalCount = strategyResults.filter((r) => r.isOptimal === true).length;
    const testWithOptimal = strategyResults.filter((r) => r.isOptimal !== null).length;

    return {
      strategy: strategy.name,
      avgDuration:
        strategyResults.reduce((sum, r) => sum + r.totalDuration, 0) /
        strategyResults.length,
      avgExecutionTime:
        strategyResults.reduce((sum, r) => sum + r.executionTimeMs, 0) /
        strategyResults.length,
      optimalCount,
      totalTests: strategyResults.length,
      avgDeviation:
        strategyResults
          .filter((r) => r.deviationFromOptimal !== undefined)
          .reduce((sum, r) => sum + (r.deviationFromOptimal || 0), 0) /
        Math.max(testWithOptimal, 1),
    };
  });

  // Generate summary
  const summary = generateSummary(results, stats);

  return { results, stats, summary };
}

/**
 * Generate a human-readable summary
 */
function generateSummary(
  results: BenchmarkResult[],
  stats: BenchmarkStats[]
): string {
  const lines: string[] = [];
  lines.push("=".repeat(60));
  lines.push("BENCHMARK SUMMARY");
  lines.push("=".repeat(60));
  lines.push("");

  for (const stat of stats) {
    lines.push(`${stat.strategy.toUpperCase()}`);
    lines.push("-".repeat(40));
    lines.push(`  Average Duration: ${stat.avgDuration.toFixed(2)} min`);
    lines.push(`  Average Execution Time: ${stat.avgExecutionTime.toFixed(2)} ms`);
    lines.push(
      `  Optimal Solutions: ${stat.optimalCount}/${stat.totalTests} ` +
        `(where verifiable)`
    );
    lines.push(`  Average Deviation from Optimal: ${stat.avgDeviation.toFixed(2)}%`);
    lines.push("");
  }

  lines.push("CONCLUSIONS");
  lines.push("-".repeat(40));

  // Compare strategies
  const gaStat = stats.find((s) => s.strategy === "genetic-algorithm");
  const psoStat = stats.find((s) => s.strategy === "pso");

  if (gaStat && psoStat) {
    if (gaStat.avgDuration < psoStat.avgDuration) {
      lines.push(
        `  GA produces shorter routes on average ` +
          `(${((1 - gaStat.avgDuration / psoStat.avgDuration) * 100).toFixed(1)}% better)`
      );
    } else {
      lines.push(
        `  PSO produces shorter routes on average ` +
          `(${((1 - psoStat.avgDuration / gaStat.avgDuration) * 100).toFixed(1)}% better)`
      );
    }

    if (gaStat.avgExecutionTime < psoStat.avgExecutionTime) {
      lines.push(
        `  GA is faster ` +
          `(${((1 - gaStat.avgExecutionTime / psoStat.avgExecutionTime) * 100).toFixed(1)}% quicker)`
      );
    } else {
      lines.push(
        `  PSO is faster ` +
          `(${((1 - psoStat.avgExecutionTime / gaStat.avgExecutionTime) * 100).toFixed(1)}% quicker)`
      );
    }
  }

  lines.push("");
  lines.push("=".repeat(60));

  return lines.join("\n");
}

/**
 * Quick validation test
 * Run to verify algorithms work correctly
 */
export async function quickValidation(): Promise<boolean> {
  console.log("Running Quick Validation...\n");

  const ga = new GeneticAlgorithmStrategy();
  const pso = new PSOStrategy();

  const testCases = [
    { waypoints: [], expected: 0 },
    { waypoints: ["Sw1"], expected: getDistance("D.Kampus", "Sw1") * 2 },
    { waypoints: ["Sw1", "Sw2"] },
    { waypoints: ["Sw1", "Sw2", "Sw3", "Sw4"] },
  ];

  let allPassed = true;

  for (const testCase of testCases) {
    const gaResult = await ga.calculateOptimalRoute(
      "D.Kampus",
      "D.Kampus",
      testCase.waypoints,
      getDistance
    );

    const psoResult = await pso.calculateOptimalRoute(
      "D.Kampus",
      "D.Kampus",
      testCase.waypoints,
      getDistance
    );

    // Basic validation
    const gaValid =
      gaResult.totalDuration >= 0 &&
      gaResult.routeDetails.length === testCase.waypoints.length + 1;
    const psoValid =
      psoResult.totalDuration >= 0 &&
      psoResult.routeDetails.length === testCase.waypoints.length + 1;

    console.log(`Test (${testCase.waypoints.length} waypoints):`);
    console.log(`  GA: ${gaResult.totalDuration.toFixed(1)} min ${gaValid ? "✓" : "✗"}`);
    console.log(`  PSO: ${psoResult.totalDuration.toFixed(1)} min ${psoValid ? "✓" : "✗"}`);

    if (!gaValid || !psoValid) {
      allPassed = false;
    }
  }

  console.log(`\nValidation ${allPassed ? "PASSED ✓" : "FAILED ✗"}`);
  return allPassed;
}

// Export test utilities
export {
  TEST_SCENARIOS,
  SAMPLE_DISTANCE_MATRIX,
  getDistance,
  bruteForceOptimal,
};
