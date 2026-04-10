import { create } from 'zustand';
import { toast } from 'sonner';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type AlgorithmType = 'local_search' | 'meta_heuristic';
export type ProblemCategory = 'small' | 'medium' | 'large';
export type ActiveView = 'dashboard' | 'experiments' | 'results' | 'algorithms';

export interface AlgorithmParam {
  key: string;
  label: string;
  type: 'number' | 'select';
  default: number | string;
  min?: number;
  max?: number;
  step?: number;
  options?: { value: string; label: string }[];
  description: string;
  unit?: string;
}

export interface Algorithm {
  id: string;
  name: string;
  shortName: string;
  type: AlgorithmType;
  description: string;
  complexity: string;
  parameters: AlgorithmParam[];
  color: string;       // chart color
  gradientFrom: string;
  gradientTo: string;
  ready: boolean;      // implemented in benchmark?
}

export interface Problem {
  name: string;
  dimension: number;
  optimal: number;
  category: ProblemCategory;
}

export interface BenchmarkResult {
  problem: string;
  dimension: number;
  category: ProblemCategory;
  optimal: number;
  strategy: string;
  avgLength: number;
  avgGap: number;
  bestLength: number;
  bestGap: number;
  avgTimeMs: number;
  elapsedMs: number;
  nRuns: number;
  timestamp: string;
  cached?: boolean;
}

export interface ExperimentConfig {
  selectedAlgorithms: string[];
  selectedProblems: string[];
  algorithmParams: Record<string, Record<string, number | string>>;
  nRuns: number;
  workers: number;
  seed: number;
  skipCached: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════════
// ALGORITHM DEFINITIONS
// ═══════════════════════════════════════════════════════════════════════════════

export const ALGORITHMS: Algorithm[] = [
  // Local Search
  {
    id: 'two_opt',
    name: '2-opt',
    shortName: '2-opt',
    type: 'local_search',
    description: 'İki kenarı keserek yeni bağlantılar oluşturur. Her iterasyonda en iyi iyileştirmeyi arar.',
    complexity: 'O(n²)',
    parameters: [
      { key: 'max_iterations', label: 'Maksimum İterasyon', type: 'number', default: 2000, min: 100, max: 50000, step: 100, description: 'İyileştirme döngüsü üst limiti', unit: 'iterasyon' },
    ],
    color: '#10b981', gradientFrom: '#059669', gradientTo: '#10b981', ready: true,
  },
  {
    id: 'three_opt',
    name: '3-opt',
    shortName: '3-opt',
    type: 'local_search',
    description: 'Üç kenar simultaneously yeniden bağlayarak turu iyileştirir. 2-opt\'tan daha güçlüdür.',
    complexity: 'O(n³)',
    parameters: [
      { key: 'max_iterations', label: 'Maksimum İterasyon', type: 'number', default: 200, min: 10, max: 5000, step: 10, description: 'İyileştirme döngüsü üst limiti', unit: 'iterasyon' },
    ],
    color: '#f59e0b', gradientFrom: '#d97706', gradientTo: '#f59e0b', ready: true,
  },
  {
    id: 'or_opt',
    name: 'Or-opt',
    shortName: 'Or-opt',
    type: 'local_search',
    description: 'Sıralı kenar setlerini (2 veya 3 ardışık kenar) yeni konumlara taşır.',
    complexity: 'O(n²)',
    parameters: [
      { key: 'max_iterations', label: 'Maksimum İterasyon', type: 'number', default: 1000, min: 100, max: 30000, step: 100, description: 'İyileştirme döngüsü üst limiti', unit: 'iterasyon' },
    ],
    color: '#6366f1', gradientFrom: '#4f46e5', gradientTo: '#6366f1', ready: true,
  },
  {
    id: 'swap',
    name: 'Swap',
    shortName: 'Swap',
    type: 'local_search',
    description: 'İki düğümün pozisyonunu değiştirerek turu iyileştirir. Basit ama etkili.',
    complexity: 'O(n²)',
    parameters: [
      { key: 'max_iterations', label: 'Maksimum İterasyon', type: 'number', default: 5000, min: 100, max: 100000, step: 500, description: 'İyileştirme döngüsü üst limiti', unit: 'iterasyon' },
    ],
    color: '#ef4444', gradientFrom: '#dc2626', gradientTo: '#ef4444', ready: true,
  },
  {
    id: 'hybrid',
    name: 'Hybrid',
    shortName: 'Hybrid',
    type: 'local_search',
    description: '2-opt + 3-opt + Or-opt kombinasyonu. Cycle bazlı sıralı çalışır. En güçlü local search.',
    complexity: 'O(n³)',
    parameters: [
      { key: 'cycles', label: 'Cycle Sayısı', type: 'number', default: 5, min: 1, max: 50, step: 1, description: 'Her bir hybrid döngüsü (2-opt → 3-opt → Or-opt)', unit: 'cycle' },
    ],
    color: '#8b5cf6', gradientFrom: '#7c3aed', gradientTo: '#8b5cf6', ready: true,
  },
  // Meta-Heuristics (planned)
  {
    id: 'ga',
    name: 'Genetic Algorithm (GA)',
    shortName: 'GA',
    type: 'meta_heuristic',
    description: 'Popülasyon tabanlı evrimsel algoritma. Çaprazlama, mutasyon ve seçilim operatörleri kullanır.',
    complexity: 'O(pop × gen × n)',
    parameters: [
      { key: 'population_size', label: 'Popülasyon Boyutu', type: 'number', default: 50, min: 10, max: 500, step: 10, description: 'Her jenerasyondaki birey sayısı', unit: 'birey' },
      { key: 'max_generations', label: 'Maksimum Jenerasyon', type: 'number', default: 100, min: 10, max: 2000, step: 10, description: 'Maksimum evrim jenerasyon sayısı', unit: 'jenerasyon' },
      { key: 'crossover_rate', label: 'Çaprazlama Oranı', type: 'number', default: 0.85, min: 0.1, max: 1.0, step: 0.05, description: 'Ebeveynlerden çaprazlama olasılığı' },
      { key: 'mutation_rate', label: 'Mutasyon Oranı', type: 'number', default: 0.15, min: 0.01, max: 0.5, step: 0.01, description: 'Rastgele mutasyon olasılığı' },
      { key: 'elite_count', label: 'Elit Sayısı', type: 'number', default: 2, min: 1, max: 20, step: 1, description: 'Her jenerasyonda korunan en iyi birey sayısı' },
      { key: 'tournament_size', label: 'Turnuva Boyutu', type: 'number', default: 3, min: 2, max: 10, step: 1, description: 'Turnuva seçiminde karşılaştırılan birey sayısı' },
      { key: 'local_search_type', label: 'Local Search Tipi', type: 'select', default: 'two_opt', description: 'Son jenerasyonda uygulanan local search refinemet', options: [
        { value: 'none', label: 'Yok' },
        { value: 'two_opt', label: '2-opt' },
        { value: 'hybrid', label: 'Hybrid' },
      ]},
    ],
    color: '#06b6d4', gradientFrom: '#0891b2', gradientTo: '#06b6d4', ready: false,
  },
  {
    id: 'pso',
    name: 'Particle Swarm Optimization (PSO)',
    shortName: 'PSO',
    type: 'meta_heuristic',
    description: 'Sürü zekası tabanlı optimizasyon. Parçacıklar en iyi çözüme doğru hareket eder.',
    complexity: 'O(swarm × iter × n)',
    parameters: [
      { key: 'swarm_size', label: 'Sürü Boyutu', type: 'number', default: 30, min: 10, max: 200, step: 5, description: 'Parçacık sayısı', unit: 'parçacık' },
      { key: 'max_iterations', label: 'Maksimum İterasyon', type: 'number', default: 100, min: 10, max: 2000, step: 10, description: 'Maksimum iterasyon sayısı', unit: 'iterasyon' },
      { key: 'inertia_weight', label: 'Eylemsizlik Ağırlığı (w)', type: 'number', default: 0.729, min: 0.1, max: 1.5, step: 0.01, description: 'Clerc constriction faktörü' },
      { key: 'cognitive_weight', label: 'Bilişsel Ağırlık (c1)', type: 'number', default: 1.49445, min: 0.5, max: 3.0, step: 0.1, description: 'Kişisel en iyi çekim gücü' },
      { key: 'social_weight', label: 'Sosyal Ağırlık (c2)', type: 'number', default: 1.49445, min: 0.5, max: 3.0, step: 0.1, description: 'Global en iyi çekim gücü' },
      { key: 'local_search_type', label: 'Local Search Tipi', type: 'select', default: 'hybrid', description: 'Parçacık güncelleme sonrası local search', options: [
        { value: 'none', label: 'Yok' },
        { value: 'two_opt', label: '2-opt' },
        { value: 'hybrid', label: 'Hybrid' },
      ]},
    ],
    color: '#f97316', gradientFrom: '#ea580c', gradientTo: '#f97316', ready: false,
  },
  {
    id: 'gwo',
    name: 'Grey Wolf Optimizer (GWO)',
    shortName: 'GWO',
    type: 'meta_heuristic',
    description: 'Kurt sürüsü hiyerarşisi tabanlı optimizasyon. Alpha, Beta, Delta liderliği.',
    complexity: 'O(pop × iter × n)',
    parameters: [
      { key: 'population_size', label: 'Popülasyon Boyutu', type: 'number', default: 30, min: 10, max: 200, step: 5, description: 'Kurt sayısı', unit: 'kurt' },
      { key: 'max_iterations', label: 'Maksimum İterasyon', type: 'number', default: 100, min: 10, max: 2000, step: 10, description: 'Av takip iterasyon sayısı', unit: 'iterasyon' },
      { key: 'initial_a', label: 'Başlangıç a Parametresi', type: 'number', default: 2.0, min: 1.0, max: 3.0, step: 0.1, description: 'Keşif-oran parametresi (lineer azalır)' },
      { key: 'local_search_type', label: 'Local Search Tipi', type: 'select', default: 'two_opt', description: 'Her iterasyonda local search', options: [
        { value: 'none', label: 'Yok' },
        { value: 'two_opt', label: '2-opt' },
        { value: 'hybrid', label: 'Hybrid' },
      ]},
    ],
    color: '#14b8a6', gradientFrom: '#0d9488', gradientTo: '#14b8a6', ready: false,
  },
  {
    id: 'hho',
    name: 'Harris Hawks Optimization (HHO)',
    shortName: 'HHO',
    type: 'meta_heuristic',
    description: 'Harris kartalları av stratejisi. Keşif-çekme dengesi ile global optimum arar.',
    complexity: 'O(pop × iter × n)',
    parameters: [
      { key: 'population_size', label: 'Popülasyon Boyutu', type: 'number', default: 30, min: 10, max: 200, step: 5, description: 'Kartal sayısı', unit: 'kartal' },
      { key: 'max_iterations', label: 'Maksimum İterasyon', type: 'number', default: 100, min: 10, max: 2000, step: 10, description: 'Av iterasyon sayısı', unit: 'iterasyon' },
      { key: 'jump_probability', label: 'Sıçrama Olasılığı', type: 'number', default: 0.5, min: 0.0, max: 1.0, step: 0.05, description: 'Soft bound → hard bound geçiş olasılığı' },
      { key: 'local_search_type', label: 'Local Search Tipi', type: 'select', default: 'hybrid', description: 'Sonuç refinemet için local search', options: [
        { value: 'none', label: 'Yok' },
        { value: 'two_opt', label: '2-opt' },
        { value: 'hybrid', label: 'Hybrid' },
      ]},
    ],
    color: '#ec4899', gradientFrom: '#db2777', gradientTo: '#ec4899', ready: false,
  },
];

// ═══════════════════════════════════════════════════════════════════════════════
// PROBLEM DEFINITIONS (TSPLIB)
// ═══════════════════════════════════════════════════════════════════════════════

export const PROBLEMS: Problem[] = [
  // Small (dim ≤ 150)
  { name: 'berlin52', dimension: 52, optimal: 7542, category: 'small' },
  { name: 'eil51', dimension: 51, optimal: 426, category: 'small' },
  { name: 'eil76', dimension: 76, optimal: 538, category: 'small' },
  { name: 'st70', dimension: 70, optimal: 675, category: 'small' },
  { name: 'kroA100', dimension: 100, optimal: 21282, category: 'small' },
  { name: 'kroB100', dimension: 100, optimal: 22141, category: 'small' },
  { name: 'kroC100', dimension: 100, optimal: 20749, category: 'small' },
  { name: 'kroD100', dimension: 100, optimal: 21294, category: 'small' },
  { name: 'kroE100', dimension: 100, optimal: 22068, category: 'small' },
  { name: 'rd100', dimension: 100, optimal: 7910, category: 'small' },
  { name: 'eil101', dimension: 101, optimal: 629, category: 'small' },
  { name: 'lin105', dimension: 105, optimal: 14379, category: 'small' },
  { name: 'pr107', dimension: 107, optimal: 44303, category: 'small' },
  { name: 'pr124', dimension: 124, optimal: 59030, category: 'small' },
  { name: 'pr136', dimension: 136, optimal: 96772, category: 'small' },
  { name: 'pr144', dimension: 144, optimal: 58537, category: 'small' },
  { name: 'pr152', dimension: 152, optimal: 73682, category: 'small' },
  // Medium (150 < dim ≤ 500)
  { name: 'kroA150', dimension: 150, optimal: 26524, category: 'medium' },
  { name: 'kroB150', dimension: 150, optimal: 26130, category: 'medium' },
  { name: 'kroA200', dimension: 200, optimal: 29368, category: 'medium' },
  { name: 'kroB200', dimension: 200, optimal: 29437, category: 'medium' },
  { name: 'pr226', dimension: 226, optimal: 80369, category: 'medium' },
  { name: 'pr264', dimension: 264, optimal: 49135, category: 'medium' },
  { name: 'pr299', dimension: 299, optimal: 48191, category: 'medium' },
  { name: 'ts225', dimension: 225, optimal: 126843, category: 'medium' },
  { name: 'gil262', dimension: 262, optimal: 2412, category: 'medium' },
  { name: 'pr439', dimension: 439, optimal: 107217, category: 'medium' },
  { name: 'a280', dimension: 280, optimal: 2579, category: 'medium' },
  { name: 'lin318', dimension: 318, optimal: 42029, category: 'medium' },
  { name: 'rd400', dimension: 400, optimal: 15281, category: 'medium' },
  // Large (dim > 500)
  { name: 'd493', dimension: 493, optimal: 35002, category: 'large' },
  { name: 'u724', dimension: 724, optimal: 41910, category: 'large' },
  { name: 'rat783', dimension: 783, optimal: 8806, category: 'large' },
  { name: 'pr1002', dimension: 1002, optimal: 259045, category: 'large' },
  { name: 'u1060', dimension: 1060, optimal: 224094, category: 'large' },
  { name: 'vm1084', dimension: 1084, optimal: 239297, category: 'large' },
  { name: 'pcb1173', dimension: 1173, optimal: 56892, category: 'large' },
  { name: 'nrw1379', dimension: 1379, optimal: 56638, category: 'large' },
  { name: 'u1432', dimension: 1432, optimal: 152970, category: 'large' },
  { name: 'd1655', dimension: 1655, optimal: 62128, category: 'large' },
  { name: 'vm1748', dimension: 1748, optimal: 336556, category: 'large' },
  { name: 'u1817', dimension: 1817, optimal: 57201, category: 'large' },
  { name: 'd2103', dimension: 2103, optimal: 80450, category: 'large' },
  { name: 'u2152', dimension: 2152, optimal: 64253, category: 'large' },
  { name: 'u2319', dimension: 2319, optimal: 234256, category: 'large' },
  { name: 'pr2392', dimension: 2392, optimal: 378032, category: 'large' },
];

// ═══════════════════════════════════════════════════════════════════════════════
// DEMO DATA (realistic benchmark results)
// ═══════════════════════════════════════════════════════════════════════════════

// Seeded random for reproducibility
function seededRandom(seed: number) {
  let s = seed;
  return () => { s = (s * 16807 + 0) % 2147483647; return (s - 1) / 2147483646; };
}

function generateDemoResults(): BenchmarkResult[] {
  const results: BenchmarkResult[] = [];
  const rng = seededRandom(42);
  const demoProblems = PROBLEMS.filter(p => p.category === 'small').slice(0, 10);
  const strategies = ALGORITHMS.filter(a => a.ready);
  const now = new Date().toISOString();

  // Realistic GAP ranges per algorithm
  const gapRanges: Record<string, [number, number]> = {
    two_opt: [2.0, 5.5],
    three_opt: [0.3, 3.0],
    or_opt: [1.5, 4.5],
    swap: [4.0, 12.0],
    hybrid: [0.2, 2.5],
  };

  // Realistic time ranges per algorithm (ms)
  const timeRanges: Record<string, [number, number]> = {
    two_opt: [8, 45],
    three_opt: [40, 180],
    or_opt: [6, 35],
    swap: [3, 18],
    hybrid: [80, 400],
  };

  for (const problem of demoProblems) {
    for (const strategy of strategies) {
      const [gapMin, gapMax] = gapRanges[strategy.id] || [1, 5];
      const [timeMin, timeMax] = timeRanges[strategy.id] || [10, 100];

      // Dimension factor - larger problems have slightly worse GAP and longer time
      const dimFactor = problem.dimension / 100;
      const avgGap = +(gapMin + rng() * (gapMax - gapMin) * (0.8 + dimFactor * 0.3)).toFixed(2);
      const bestGap = +(avgGap * (0.5 + rng() * 0.4)).toFixed(2);
      const avgTimeMs = +((timeMin + rng() * (timeMax - timeMin)) * dimFactor).toFixed(1);
      const elapsedMs = +(avgTimeMs * 3 * (0.9 + rng() * 0.2)).toFixed(1);
      const avgLength = Math.round(problem.optimal * (1 + avgGap / 100));
      const bestLength = Math.round(problem.optimal * (1 + bestGap / 100));

      results.push({
        problem: problem.name,
        dimension: problem.dimension,
        category: problem.category,
        optimal: problem.optimal,
        strategy: strategy.shortName,
        avgLength,
        avgGap,
        bestLength,
        bestGap,
        avgTimeMs,
        elapsedMs,
        nRuns: 3,
        timestamp: now,
      });
    }
  }
  return results;
}

const DEMO_RESULTS = generateDemoResults();

// ═══════════════════════════════════════════════════════════════════════════════
// STORE
// ═══════════════════════════════════════════════════════════════════════════════

export type SortField = 'problem' | 'strategy' | 'avgGap' | 'bestGap' | 'avgTimeMs' | 'dimension' | 'optimal';
export type SortDir = 'asc' | 'desc';

export interface RunProgress {
  completed: number;
  total: number;
  percentage: number;
  current: { problem: string; algorithm: string; run: number } | null;
  elapsed_ms: number;
  eta_ms: number;
}

interface BenchmarkStore {
  // Data
  results: BenchmarkResult[];
  dataMode: 'demo' | 'loaded';

  // UI
  activeView: ActiveView;
  sidebarOpen: boolean;

  // Dashboard filters
  dashboardFilter: ProblemCategory | 'all';
  dashboardAlgorithmFilter: string | 'all';
  dashboardSearch: string;

  // Results table
  sortField: SortField;
  sortDir: SortDir;
  resultsPerPage: number;
  resultsPage: number;

  // Experiment config
  experiment: ExperimentConfig;

  // Run execution state
  isRunning: boolean;
  runId: string | null;
  runProgress: RunProgress | null;
  runResults: BenchmarkResult[];
  runError: string | null;
  runComplete: boolean;
  runStartTime: number | null;

  // Actions
  setActiveView: (view: ActiveView) => void;
  setSidebarOpen: (open: boolean) => void;
  setDashboardFilter: (cat: ProblemCategory | 'all') => void;
  setDashboardAlgorithmFilter: (algo: string | 'all') => void;
  setDashboardSearch: (query: string) => void;
  setSortField: (field: SortField) => void;
  setSortDir: (dir: SortDir) => void;
  setResultsPerPage: (n: number) => void;
  setResultsPage: (n: number) => void;

  // Experiment actions
  toggleAlgorithm: (id: string) => void;
  selectAllAlgorithms: (type?: AlgorithmType | 'all') => void;
  clearAlgorithmSelection: () => void;
  toggleProblem: (name: string) => void;
  selectAllProblems: (category?: ProblemCategory | 'all') => void;
  clearProblemSelection: () => void;
  setAlgorithmParam: (algoId: string, paramKey: string, value: number | string) => void;
  resetAlgorithmParams: (algoId: string) => void;
  setExperimentSetting: <K extends keyof ExperimentConfig>(key: K, value: ExperimentConfig[K]) => void;

  // Data actions
  loadCSVData: (csvText: string) => void;
  loadJSONData: (json: Record<string, Record<string, unknown>>) => void;

  // Run execution actions
  setIsRunning: (running: boolean) => void;
  setRunId: (runId: string | null) => void;
  setRunProgress: (progress: RunProgress | null) => void;
  addRunResult: (result: BenchmarkResult) => void;
  addRunResults: (results: BenchmarkResult[]) => void;
  setRunError: (error: string | null) => void;
  setRunComplete: (complete: boolean) => void;
  setRunStartTime: (time: number | null) => void;
  clearRunState: () => void;
  mergeRunResults: () => void;

  // Computed
  getFilteredResults: () => BenchmarkResult[];
  getStats: () => {
    totalExperiments: number;
    algorithmsTested: number;
    problemsCovered: number;
    avgGap: number;
    bestGap: number;
    bestAlgorithm: string;
    avgTime: number;
  };
  getAlgorithmSummary: () => { name: string; avgGap: number; minGap: number; maxGap: number; avgTime: number; experiments: number; color: string }[];
  getProblemSummary: () => { name: string; dim: number; optimal: number; category: ProblemCategory; bestAlgo: string; bestGap: number }[];
  getExperimentMatrixCount: () => number;
}

export const useBenchmarkStore = create<BenchmarkStore>((set, get) => ({
  results: DEMO_RESULTS,
  dataMode: 'demo' as const,
  activeView: 'dashboard' as ActiveView,
  sidebarOpen: false,
  dashboardFilter: 'all' as const,
  dashboardAlgorithmFilter: 'all' as const,
  dashboardSearch: '',
  sortField: 'avgGap' as SortField,
  sortDir: 'asc' as SortDir,
  resultsPerPage: 15,
  resultsPage: 1,
  experiment: {
    selectedAlgorithms: ['two_opt', 'three_opt', 'or_opt', 'swap', 'hybrid'],
    selectedProblems: PROBLEMS.filter(p => p.category === 'small').map(p => p.name),
    algorithmParams: {},
    nRuns: 3,
    workers: 4,
    seed: 42,
    skipCached: true,
  },

  // Run execution state
  isRunning: false,
  runId: null,
  runProgress: null,
  runResults: [],
  runError: null,
  runComplete: false,
  runStartTime: null,

  setActiveView: (view) => set({ activeView: view, sidebarOpen: false }),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setDashboardFilter: (cat) => set({ dashboardFilter: cat, resultsPage: 1 }),
  setDashboardAlgorithmFilter: (algo) => set({ dashboardAlgorithmFilter: algo, resultsPage: 1 }),
  setDashboardSearch: (query) => set({ dashboardSearch: query, resultsPage: 1 }),
  setSortField: (field) => set((s) => ({ sortField: field, sortDir: s.sortField === field ? (s.sortDir === 'asc' ? 'desc' : 'asc') : s.sortDir })),
  setSortDir: (dir) => set({ sortDir: dir }),
  setResultsPerPage: (n) => set({ resultsPerPage: n, resultsPage: 1 }),
  setResultsPage: (n) => set({ resultsPage: n }),

  // ─── Experiment Actions ─────────────────────────────────────────────────

  toggleAlgorithm: (id) => set((s) => {
    const sel = s.experiment.selectedAlgorithms.includes(id)
      ? s.experiment.selectedAlgorithms.filter((a) => a !== id)
      : [...s.experiment.selectedAlgorithms, id];
    return { experiment: { ...s.experiment, selectedAlgorithms: sel } };
  }),

  selectAllAlgorithms: (type) => set((s) => {
    const algos = type === 'all' || type === undefined
      ? ALGORITHMS.map(a => a.id)
      : ALGORITHMS.filter(a => a.type === type).map(a => a.id);
    return { experiment: { ...s.experiment, selectedAlgorithms: algos } };
  }),

  clearAlgorithmSelection: () => set((s) => ({
    experiment: { ...s.experiment, selectedAlgorithms: [] },
  })),

  toggleProblem: (name) => set((s) => {
    const sel = s.experiment.selectedProblems.includes(name)
      ? s.experiment.selectedProblems.filter((p) => p !== name)
      : [...s.experiment.selectedProblems, name];
    return { experiment: { ...s.experiment, selectedProblems: sel } };
  }),

  selectAllProblems: (category) => set((s) => {
    const probs = category === 'all' || category === undefined
      ? PROBLEMS.map(p => p.name)
      : PROBLEMS.filter(p => p.category === category).map(p => p.name);
    return { experiment: { ...s.experiment, selectedProblems: probs } };
  }),

  clearProblemSelection: () => set((s) => ({
    experiment: { ...s.experiment, selectedProblems: [] },
  })),

  setAlgorithmParam: (algoId, paramKey, value) => set((s) => {
    const current = s.experiment.algorithmParams[algoId] || {};
    return { experiment: { ...s.experiment, algorithmParams: { ...s.experiment.algorithmParams, [algoId]: { ...current, [paramKey]: value } } } };
  }),

  resetAlgorithmParams: (algoId) => set((s) => {
    const newParams = { ...s.experiment.algorithmParams };
    delete newParams[algoId];
    return { experiment: { ...s.experiment, algorithmParams: newParams } };
  }),

  setExperimentSetting: (key, value) => set((s) => ({
    experiment: { ...s.experiment, [key]: value },
  })),

  // ─── Run Execution Actions ──────────────────────────────────────────

  setIsRunning: (running) => set({ isRunning: running }),
  setRunId: (runId) => set({ runId }),
  setRunProgress: (progress) => set({ runProgress: progress }),
  addRunResult: (result) => set((s) => ({ runResults: [...s.runResults, result] })),
  addRunResults: (results) => set((s) => ({ runResults: [...s.runResults, ...results] })),
  setRunError: (error) => set({ runError: error }),
  setRunComplete: (complete) => set({ runComplete: complete }),
  setRunStartTime: (time) => set({ runStartTime: time }),
  clearRunState: () => set({
    isRunning: false,
    runId: null,
    runProgress: null,
    runResults: [],
    runError: null,
    runComplete: false,
    runStartTime: null,
  }),
  mergeRunResults: () => set((s) => {
    if (s.runResults.length === 0) return {};
    // Merge run results into main results (avoid duplicates by problem+strategy)
    const existingKeys = new Set(s.results.map(r => `${r.problem}::${r.strategy}`));
    const newResults = s.runResults.filter(r => !existingKeys.has(`${r.problem}::${r.strategy}`));
    if (newResults.length === 0) return {};
    return {
      results: [...s.results, ...newResults],
      dataMode: 'loaded' as const,
    };
  }),

  // ─── Data Actions ──────────────────────────────────────────────────────

  loadCSVData: (csvText) => {
    try {
      const lines = csvText.trim().split('\n');
      if (lines.length < 2) { toast.error('CSV dosyası boş veya geçersiz'); return; }
      const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
      const results: BenchmarkResult[] = [];

      for (let i = 1; i < lines.length; i++) {
        const vals = lines[i].split(',').map(v => v.trim());
        if (vals.length < headers.length) continue;

        const row: Record<string, string> = {};
        headers.forEach((h, idx) => { row[h] = vals[idx]; });

        const prob = PROBLEMS.find(p => p.name === row['problem']);
        results.push({
          problem: row['problem'] || '',
          dimension: parseInt(row['dimension']) || prob?.dimension || 0,
          category: (row['category'] as ProblemCategory) || prob?.category || 'small',
          optimal: parseInt(row['optimal']) || prob?.optimal || 0,
          strategy: row['strategy'] || '',
          avgLength: parseFloat(row['avg_length'] || row['avglength'] || '0'),
          avgGap: parseFloat(row['avg_gap'] || row['avggap'] || '0'),
          bestLength: parseFloat(row['best_length'] || row['bestlength'] || '0'),
          bestGap: parseFloat(row['best_gap'] || row['bestgap'] || '0'),
          avgTimeMs: parseFloat(row['avg_time_ms'] || row['avgtimems'] || '0'),
          elapsedMs: parseFloat(row['elapsed_ms'] || row['elapsedms'] || '0'),
          nRuns: parseInt(row['n_runs'] || row['nruns'] || '3'),
          timestamp: row['timestamp'] || new Date().toISOString(),
          cached: row['cached'] === 'True',
        });
      }

      set({ results, dataMode: 'loaded' });
      toast.success(`${results.length} sonuç yüklendi`);
    } catch {
      toast.error('CSV dosyası okunamadı');
    }
  },

  loadJSONData: (json) => {
    try {
      const results: BenchmarkResult[] = [];
      for (const [probName, strategies] of Object.entries(json)) {
        for (const [stratName, data] of Object.entries(strategies as Record<string, Record<string, unknown>>)) {
          const prob = PROBLEMS.find(p => p.name === probName);
          results.push({
            problem: probName,
            dimension: prob?.dimension || 0,
            category: prob?.category || 'small',
            optimal: prob?.optimal || 0,
            strategy: stratName,
            avgLength: (data.avg_length as number) || 0,
            avgGap: (data.avg_gap as number) || 0,
            bestLength: (data.best_length as number) || (data.avg_length as number) || 0,
            bestGap: (data.best_gap as number) || 0,
            avgTimeMs: (data.avg_time_ms as number) || 0,
            elapsedMs: (data.elapsed_ms as number) || 0,
            nRuns: (data.n_runs as number) || 3,
            timestamp: (data.timestamp as string) || new Date().toISOString(),
            cached: true,
          });
        }
      }
      if (results.length > 0) {
        set({ results, dataMode: 'loaded' });
        toast.success(`${results.length} sonuç yüklendi`);
      } else {
        toast.error('JSON dosyasında sonuç bulunamadı');
      }
    } catch {
      toast.error('JSON dosyası okunamadı');
    }
  },

  // ─── Computed ──────────────────────────────────────────────────────────

  getFilteredResults: () => {
    const { results, dashboardFilter, dashboardAlgorithmFilter, dashboardSearch } = get();
    let filtered = [...results];

    if (dashboardFilter !== 'all') filtered = filtered.filter(r => r.category === dashboardFilter);
    if (dashboardAlgorithmFilter !== 'all') filtered = filtered.filter(r => r.strategy === dashboardAlgorithmFilter);
    if (dashboardSearch) {
      const q = dashboardSearch.toLowerCase();
      filtered = filtered.filter(r => r.problem.toLowerCase().includes(q) || r.strategy.toLowerCase().includes(q));
    }

    // Sort
    const { sortField, sortDir } = get();
    filtered.sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];
      const cmp = typeof aVal === 'string' ? (aVal as string).localeCompare(bVal as string) : (aVal as number) - (bVal as number);
      return sortDir === 'asc' ? cmp : -cmp;
    });

    return filtered;
  },

  getStats: () => {
    const { results } = get();
    if (results.length === 0) return { totalExperiments: 0, algorithmsTested: 0, problemsCovered: 0, avgGap: 0, bestGap: 0, bestAlgorithm: '-', avgTime: 0 };

    const algorithms = new Set(results.map(r => r.strategy));
    const problems = new Set(results.map(r => r.problem));
    const avgGap = results.reduce((s, r) => s + r.avgGap, 0) / results.length;
    const bestResult = results.reduce((best, r) => r.bestGap < best.bestGap ? r : best, results[0]);

    // Find best algorithm (lowest avg gap)
    const algoGaps: Record<string, number[]> = {};
    for (const r of results) {
      if (!algoGaps[r.strategy]) algoGaps[r.strategy] = [];
      algoGaps[r.strategy].push(r.avgGap);
    }
    let bestAlgo = '-';
    let bestAlgoGap = Infinity;
    for (const [algo, gaps] of Object.entries(algoGaps)) {
      const avg = gaps.reduce((a, b) => a + b, 0) / gaps.length;
      if (avg < bestAlgoGap) { bestAlgoGap = avg; bestAlgo = algo; }
    }

    return {
      totalExperiments: results.length,
      algorithmsTested: algorithms.size,
      problemsCovered: problems.size,
      avgGap: +avgGap.toFixed(2),
      bestGap: +bestResult.bestGap.toFixed(2),
      bestAlgorithm: bestAlgo,
      avgTime: +(results.reduce((s, r) => s + r.avgTimeMs, 0) / results.length).toFixed(1),
    };
  },

  getAlgorithmSummary: () => {
    const { results } = get();
    const summary: Record<string, { gaps: number[]; times: number[]; count: number; color: string }> = {};

    for (const r of results) {
      if (!summary[r.strategy]) summary[r.strategy] = { gaps: [], times: [], count: 0, color: '' };
      summary[r.strategy].gaps.push(r.avgGap);
      summary[r.strategy].times.push(r.avgTimeMs);
      summary[r.strategy].count++;
    }

    return Object.entries(summary).map(([name, data]) => {
      const algo = ALGORITHMS.find(a => a.shortName === name);
      return {
        name,
        avgGap: +(data.gaps.reduce((a, b) => a + b, 0) / data.gaps.length).toFixed(2),
        minGap: +Math.min(...data.gaps).toFixed(2),
        maxGap: +Math.max(...data.gaps).toFixed(2),
        avgTime: +(data.times.reduce((a, b) => a + b, 0) / data.times.length).toFixed(1),
        experiments: data.count,
        color: algo?.color || '#64748b',
      };
    }).sort((a, b) => a.avgGap - b.avgGap);
  },

  getProblemSummary: () => {
    const { results } = get();
    const summary: Record<string, { bestAlgo: string; bestGap: number; dim: number; optimal: number; category: ProblemCategory }> = {};

    for (const r of results) {
      if (!summary[r.problem] || r.bestGap < summary[r.problem].bestGap) {
        summary[r.problem] = { bestAlgo: r.strategy, bestGap: r.bestGap, dim: r.dimension, optimal: r.optimal, category: r.category };
      }
    }

    return Object.entries(summary).map(([name, data]) => ({
      name, dim: data.dim, optimal: data.optimal, category: data.category,
      bestAlgo: data.bestAlgo, bestGap: +data.bestGap.toFixed(2),
    }));
  },

  getExperimentMatrixCount: () => {
    const { experiment } = get();
    return experiment.selectedAlgorithms.length * experiment.selectedProblems.length;
  },
}));
