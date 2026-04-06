import { GeneticAlgorithmStrategy } from './src/services/doubus/route-strategies/ga-strategy';
import { PSOStrategy } from './src/services/doubus/route-strategies/pso-strategy';

const DISTANCES: Record<string, Record<string, number>> = {
  'D.Kampus': { 'D.Kampus': 0, Sw1: 15, Sw2: 18, Sw3: 22, Sw4: 25, Sw5: 28, Sw6: 30, Sw7: 32, So1: 20, So2: 22, So3: 25, So4: 28, So5: 30 },
  'Sw1': { 'D.Kampus': 15, Sw1: 0, Sw2: 5, Sw3: 8, Sw4: 12, Sw5: 15, Sw6: 18, Sw7: 20, So1: 10, So2: 12, So3: 15 },
  'Sw2': { 'D.Kampus': 18, Sw1: 5, Sw2: 0, Sw3: 4, Sw4: 8, Sw5: 12, So1: 8, So2: 10 },
  'Sw3': { 'D.Kampus': 22, Sw1: 8, Sw2: 4, Sw3: 0, Sw4: 5, Sw5: 8, So1: 12, So2: 14 },
  'Sw4': { 'D.Kampus': 25, Sw1: 12, Sw2: 8, Sw3: 5, Sw4: 0, Sw5: 4, So1: 15, So2: 8 },
  'Sw5': { 'D.Kampus': 28, Sw1: 15, Sw2: 12, Sw3: 8, Sw4: 4, Sw5: 0, So2: 10, So3: 8 },
  'Sw6': { 'D.Kampus': 30, Sw4: 10, Sw5: 8, Sw6: 0, Sw7: 5 },
  'Sw7': { 'D.Kampus': 32, Sw5: 10, Sw6: 5, Sw7: 0 },
  'So1': { 'D.Kampus': 20, Sw1: 10, Sw2: 8, Sw3: 12, So1: 0, So2: 4, So3: 8, So4: 12, So5: 15 },
  'So2': { 'D.Kampus': 22, Sw1: 12, Sw2: 10, So1: 4, So2: 0, So3: 5, So4: 8, So5: 12 },
  'So3': { 'D.Kampus': 25, Sw2: 12, Sw3: 10, So1: 8, So2: 5, So3: 0, So4: 4, So5: 8 },
  'So4': { 'D.Kampus': 28, Sw3: 12, So1: 12, So2: 8, So3: 4, So4: 0, So5: 5 },
  'So5': { 'D.Kampus': 30, So1: 15, So2: 12, So3: 8, So4: 5, So5: 0 }
};

function getDistance(from: string, to: string): number {
  return DISTANCES[from]?.[to] ?? DISTANCES[to]?.[from] ?? 50;
}

async function runTests() {
  const ga = new GeneticAlgorithmStrategy({ seed: 42, maxIterations: 500, populationSize: 100 });
  const pso = new PSOStrategy({ seed: 42, maxIterations: 300, swarmSize: 50 });

  console.log('='.repeat(60));
  console.log('GA ve PSO ALGORITMA TESTLERI');
  console.log('='.repeat(60));

  const testCases = [
    { name: 'Empty', waypoints: [] },
    { name: 'Single', waypoints: ['Sw1'] },
    { name: 'Two', waypoints: ['Sw1', 'Sw2'] },
    { name: 'Four', waypoints: ['Sw1', 'Sw2', 'Sw3', 'Sw4'] },
    { name: 'Six', waypoints: ['Sw1', 'Sw2', 'Sw3', 'So1', 'So2', 'Sw4'] },
    { name: 'Medium-8', waypoints: ['Sw1', 'Sw2', 'Sw3', 'Sw4', 'So1', 'So2', 'So3', 'Sw5'] },
    { name: 'Large-10', waypoints: ['Sw1', 'Sw2', 'Sw3', 'Sw4', 'Sw5', 'So1', 'So2', 'So3', 'So4', 'Sw6'] },
    { name: 'XL-12', waypoints: ['Sw1', 'Sw2', 'Sw3', 'Sw4', 'Sw5', 'Sw6', 'So1', 'So2', 'So3', 'So4', 'So5', 'Sw7'] }
  ];

  for (const tc of testCases) {
    console.log(`\n--- ${tc.name} (${tc.waypoints.length} waypoints) ---`);

    const start1 = performance.now();
    const gaResult = await ga.calculateOptimalRoute('D.Kampus', 'D.Kampus', tc.waypoints, getDistance);
    const gaTime = performance.now() - start1;

    const start2 = performance.now();
    const psoResult = await pso.calculateOptimalRoute('D.Kampus', 'D.Kampus', tc.waypoints, getDistance);
    const psoTime = performance.now() - start2;

    console.log(`GA:  ${gaResult.totalDuration.toFixed(1)} min (${gaTime.toFixed(1)}ms)`);
    console.log(`PSO: ${psoResult.totalDuration.toFixed(1)} min (${psoTime.toFixed(1)}ms)`);

    if (tc.waypoints.length > 0 && tc.waypoints.length <= 6) {
      const gaRoute = gaResult.routeDetails.map(r => r.location1).join(' -> ') + ' -> D.Kampus';
      console.log(`Route: ${gaRoute}`);
    }
  }

  console.log('\n' + '='.repeat(60));
  console.log('TUM TESTLER BASARILI!');
  console.log('='.repeat(60));
}

runTests().catch(console.error);
