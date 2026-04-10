'use client';

import React, { useState, useCallback, useMemo, useRef, useEffect, useSyncExternalStore } from 'react';
import { useTheme } from 'next-themes';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RTooltip,
  ResponsiveContainer, Cell, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  ScatterChart, Scatter, Legend as RLegend,
  LineChart, Line, ReferenceLine, ReferenceArea, ComposedChart, ErrorBar,
} from 'recharts';
import { io, Socket } from 'socket.io-client';
import {
  LayoutDashboard, FlaskConical, Table2, Cpu, Sun, Moon, Upload, Database,
  ChevronDown, ChevronUp, ChevronRight, Check, X, Search, ArrowUpDown,
  Download, FileJson, FileSpreadsheet, Settings2, Play,
  Beaker, Zap, Clock, TrendingDown, Award, BarChart3,
  CircleDot, Layers, Maximize2, Minimize2, Filter,
  ChevronLeft, RefreshCw, Trash2, CheckCircle2,
  Circle, AlertTriangle, Info, SlidersHorizontal, Target,
  Activity, Hash, Timer, Trophy, Radar as RadarIcon,
  GitCompareArrows, Crosshair, Square, Loader2, CheckCircle,
  ListChecks, BookOpen, Grid3X3, Swords, Gauge, Medal,
} from 'lucide-react';

import { useBenchmarkStore, ALGORITHMS, PROBLEMS, type ActiveView, type ProblemCategory, type Algorithm, type BenchmarkResult, type RunProgress } from '@/store/benchmark-store';

// ─── shadcn/ui Components ─────────────────────────────────────────────────
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardAction } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Sheet, SheetTrigger, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS & HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

const CATEGORY_LABELS: Record<ProblemCategory, string> = {
  small: 'Küçük',
  medium: 'Orta',
  large: 'Büyük',
};

const CATEGORY_COLORS: Record<ProblemCategory, string> = {
  small: 'text-emerald-600 dark:text-emerald-400',
  medium: 'text-amber-600 dark:text-amber-400',
  large: 'text-rose-600 dark:text-rose-400',
};

const CATEGORY_BG: Record<ProblemCategory, string> = {
  small: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
  medium: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  large: 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400',
};

function gapColor(gap: number): string {
  if (gap < 2) return 'text-emerald-600 dark:text-emerald-400';
  if (gap < 5) return 'text-amber-600 dark:text-amber-400';
  return 'text-rose-600 dark:text-rose-400';
}

function gapBg(gap: number): string {
  if (gap < 2) return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400';
  if (gap < 5) return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400';
  return 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400';
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K';
  return n.toLocaleString('tr-TR');
}

const fadeIn = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -12 },
};

const staggerContainer = {
  animate: { transition: { staggerChildren: 0.06 } },
};

const ALGO_COLORS: Record<string, string> = {
  '2-opt': '#10b981', '3-opt': '#f59e0b', 'Or-opt': '#6366f1',
  'Swap': '#ef4444', 'Hybrid': '#8b5cf6',
};

const SECTION_NUMBER_STYLE = 'inline-flex items-center justify-center w-6 h-6 rounded-full text-[10px] font-bold bg-gradient-to-br from-emerald-500 to-emerald-600 text-white shadow-sm shrink-0';

// Problem Detail Tooltip Component
function ProblemDetailTooltip({ problemName }: { problemName: string }) {
  const store = useBenchmarkStore();
  const problemSummary = store.getProblemSummary();
  const prob = problemSummary.find(p => p.name === problemName);
  const probDef = PROBLEMS.find(p => p.name === problemName);

  if (!prob && !probDef) {
    return <span className="font-mono text-xs font-medium whitespace-nowrap">{problemName}</span>;
  }

  const p = prob || { name: problemName, dim: probDef?.dimension || 0, optimal: probDef?.optimal || 0, category: probDef?.category || 'small' as ProblemCategory, bestAlgo: '-', bestGap: 0 };

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="font-mono text-xs font-medium whitespace-nowrap cursor-help underline decoration-dotted underline-offset-2 text-foreground hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">
          {problemName}
        </span>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-xs p-0">
        <div className="space-y-2 p-1">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: p.category === 'small' ? '#10b981' : p.category === 'medium' ? '#f59e0b' : '#ef4444' }} />
            <span className="font-semibold text-xs">{p.name}</span>
            <Badge variant="secondary" className={`text-[9px] px-1 py-0 ${CATEGORY_BG[p.category]}`}>
              {CATEGORY_LABELS[p.category]}
            </Badge>
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
            <span className="text-muted-foreground">Düğüm Sayısı:</span>
            <span className="font-mono font-medium tabular-nums">{p.dim}</span>
            <span className="text-muted-foreground">Optimal Tur:</span>
            <span className="font-mono font-medium tabular-nums">{formatNumber(p.optimal)}</span>
            <span className="text-muted-foreground">En İyi Algoritma:</span>
            <span className="font-medium" style={{ color: ALGO_COLORS[p.bestAlgo] || 'var(--foreground)' }}>{p.bestAlgo}</span>
            {prob && (
              <>
                <span className="text-muted-foreground">En İyi GAP:</span>
                <span className={`font-medium tabular-nums ${gapColor(p.bestGap)}`}>{p.bestGap}%</span>
              </>
            )}
          </div>
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

// Algorithm pseudocode for detail sheet
const ALGO_PSEUDOCODE: Record<string, string> = {
  two_opt: `function TwoOpt(tour):
  improved = true
  while improved:
    improved = false
    for i = 0 to n-2:
      for j = i+2 to n-1:
        delta = dist(tour[i], tour[j]) +
                dist(tour[i+1], tour[j+1]) -
                dist(tour[i], tour[i+1]) -
                dist(tour[j], tour[j+1])
        if delta < 0:
          reverse(tour, i+1, j)
          improved = true
          break
      if improved: break
  return tour`,
  three_opt: `function ThreeOpt(tour):
  improved = true
  while improved:
    improved = false
    for i in range(n):
      for j in range(i+2, n):
        for k in range(j+2, n):
          best = reconnect(tour, i, j, k)
          if best.cost < current_cost:
            tour = best.tour
            improved = true
    return tour
  return tour`,
  or_opt: `function OrOpt(tour):
  for length in [3, 2]:
    improved = true
    while improved:
      improved = false
      for i in range(n):
        segment = tour[i : i+length]
        for pos in all positions:
          if pos not in [i-1, i, i+length-1]:
            if insert_better(segment, pos):
              move(segment, pos)
              improved = true
              break
      if improved: break
  return tour`,
  swap: `function Swap(tour):
  improved = true
  while improved:
    improved = false
    for i in 0 to n-2:
      for j in i+1 to n-1:
        if swap(tour[i], tour[j]) improves:
          swap(tour[i], tour[j])
          improved = true
          break
      if improved: break
  return tour`,
  hybrid: `function Hybrid(tour):
  for cycle in 1 to MAX_CYCLES:
    tour = TwoOpt(tour)
    tour = ThreeOpt(tour)
    tour = OrOpt(tour)
    if no_improvement:
      break
  return tour`,
  ga: `function GeneticAlgorithm(pop_size, max_gen):
  population = initialize_random(pop_size)
  for gen in 1 to max_gen:
    evaluate_fitness(population)
    new_pop = select_elites(population)
    while |new_pop| < pop_size:
      p1 = tournament_select(population)
      p2 = tournament_select(population)
      child = crossover(p1, p2)
      if random() < mutation_rate:
        child = mutate(child)
      new_pop.add(child)
    population = new_pop
  return best(population)`,
  pso: `function PSO(swarm_size, max_iter):
  swarm = initialize_particles(swarm_size)
  for iter in 1 to max_iter:
    for particle in swarm:
      update_velocity(particle, gbest, pbest)
      update_position(particle)
      if fitness(particle) > fitness(pbest):
        pbest = particle
      if fitness(particle) > fitness(gbest):
        gbest = particle
  return gbest`,
  gwo: `function GWO(pop_size, max_iter):
  pack = initialize_wolves(pop_size)
  alpha, beta, delta = top_3(pack)
  for iter in 1 to max_iter:
    a = 2 - iter * (2/max_iter)  // linear decay
    for wolf in pack:
      update_position(wolf, alpha, beta, delta, a)
    alpha, beta, delta = top_3(pack)
  return alpha`,
  hho: `function HHO(pop_size, max_iter):
  hawks = initialize_hawks(pop_size)
  rabbit = best(hawks)
  for iter in 1 to max_iter:
    E0 = random(-1, 1)
    E = E0 * (1 - iter/max_iter)  // energy decay
    if |E| >= 1:
      // Exploration phase
      for hawk in hawks:
        random_position(hawk)
    else:
      // Exploitation phase
      if |E| < 0.5: soft_bounce(hawk, rabbit)
      else: hard_bounce(hawk, rabbit)
    rabbit = best(hawks)
  return rabbit`,
};

const ALGO_PERFORMANCE: Record<string, string> = {
  two_opt: 'İyi GAP performansı, düşük çalışma süresi. Küçük-orta problemlerde etkilidir. Basit implementasyonu ile hızlı çözüm üretir. TSP optimizasyon literatüründe en çok kullanılan yerel arama yöntemidir.',
  three_opt: '2-opt\'tan daha iyi GAP performansı sunar ancak çalışma süresi daha yüksektir. Üç kenarlı hareketler sayesinde daha geniş komşuluk araması yapar. Büyük problemlerde yavaş olabilir.',
  or_opt: 'Sıralı kenar hareketleri ile etkili iyileştirme sağlar. 2-opt ile benzer hızda, bazı problemlerde daha iyi sonuç verir. Or-opt hareketleri gerçek dünya TSP instance\'larında özellikle etkilidir.',
  swap: 'En basit yerel arama yöntemi. Hızlı çalışır ancak GAP performansı diğer yöntemlere göre daha zayıftır. Başlangıç çözümü için iyi bir aday olabilir.',
  hybrid: 'En güçlü yerel arama kombinasyonu. 2-opt, 3-opt ve Or-opt\'u sıralı cycle\'lar halinde çalıştırır. Daha düşük GAP ama daha yüksek çalışma süresi sunar.',
  ga: 'Popülasyon tabanlı evrimsel algoritma. Geniş arama uzayında global optimuma yakın çözümler bulur. Çaprazlama ve mutasyon operatörleri ile çeşitliliği sağlar. Çalışma süresi parametrelere bağlıdır.',
  pso: 'Sürü zekası tabanlı optimizasyon. Parçacıklar en iyi çözüme doğru hareket eder. Cognitive ve social ağırlıkları ile keşif-çekme dengesi kurulur. Paralel çalışmaya uygun yapısı vardır.',
  gwo: 'Kurt sürüsü hiyerarşisi tabanlı optimizasyon. Alpha, Beta ve Delta liderliği altında parçacıklar ava doğru hareket eder. a parametresinin lineer azalması ile keşif-oran dengesi sağlanır.',
  hho: 'Harris kartalları av stratejisi. Keşif ve çekme arasında dinamik geçiş yapar. E parametresinin azalması ile exploitation artar. Soft/hard bounce mekanizmaları ile yerel arama yapar.',
};

// ═══════════════════════════════════════════════════════════════════════════════
// PRESETS
// ═══════════════════════════════════════════════════════════════════════════════

const PRESETS = [
  {
    id: 'quick',
    name: 'Hızlı Test',
    desc: '5 algoritma, 3 küçük problem, 1 run',
    config: {
      algorithms: ['two_opt', 'swap', 'or_opt', 'hybrid', 'three_opt'],
      problems: ['berlin52', 'eil51', 'st70'],
      nRuns: 1, workers: 4, seed: 42, skipCached: true,
    },
  },
  {
    id: 'standard',
    name: 'Standart Deney',
    desc: '5 algoritma, 10 küçük problem, 3 run',
    config: {
      algorithms: ['two_opt', 'swap', 'or_opt', 'hybrid', 'three_opt'],
      problems: ['berlin52', 'eil51', 'eil76', 'st70', 'kroA100', 'kroB100', 'kroC100', 'kroD100', 'kroE100', 'rd100'],
      nRuns: 3, workers: 4, seed: 42, skipCached: true,
    },
  },
  {
    id: 'comprehensive',
    name: 'Kapsamlı Deney',
    desc: '5 algoritma, tüm küçük + orta problem, 3 run',
    config: {
      algorithms: ['two_opt', 'swap', 'or_opt', 'hybrid', 'three_opt'],
      problems: PROBLEMS.filter(p => p.category === 'small' || p.category === 'medium').map(p => p.name),
      nRuns: 3, workers: 4, seed: 42, skipCached: true,
    },
  },
  {
    id: 'full',
    name: 'Tam Kapsam',
    desc: '5 algoritma, tüm 45 problem, 3 run',
    config: {
      algorithms: ['two_opt', 'swap', 'or_opt', 'hybrid', 'three_opt'],
      problems: PROBLEMS.map(p => p.name),
      nRuns: 3, workers: 4, seed: 42, skipCached: false,
    },
  },
] as const;

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN PAGE COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export default function TSPBenchmarkPage() {
  const store = useBenchmarkStore();
  const { theme, setTheme } = useTheme();
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>, type: 'csv' | 'json') => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      if (type === 'csv') {
        store.loadCSVData(text);
      } else {
        try {
          store.loadJSONData(JSON.parse(text));
        } catch {
          toast.error('JSON dosyası okunamadı');
        }
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  }, [store]);

  const useDemoData = useCallback(() => {
    const demoResults = (store as unknown as { results: BenchmarkResult[] }).results;
    if (demoResults.length > 0) {
      toast.success('Demo veri yüklendi');
    }
  }, [store]);

  return (
    <TooltipProvider delayDuration={200}>
      <div className="min-h-screen flex flex-col bg-background bg-mesh-gradient">
        {/* ─── ANIMATED GRADIENT BORDER (TOP) ──────────────────── */}
        <div className="top-gradient-line sticky top-0 z-[60]" />

        {/* ─── HEADER ──────────────────────────────────────────────── */}
        <header className="glass-header sticky top-[2px] z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-emerald-500 to-amber-500 flex items-center justify-center text-white font-bold text-sm shadow-lg">
                  TS
                </div>
                <div>
                  <h1 className="text-lg font-bold tracking-tight gradient-text">
                    TSP Benchmark Studio
                  </h1>
                  <p className="text-xs text-muted-foreground hidden sm:block">
                    Akademik Deney Tasarımı ve Sonuç Analizi
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-xs gap-1">
                  <CircleDot className="size-3" />
                  {store.dataMode === 'demo' ? 'Demo Veri' : 'Yüklenen Veri'}
                </Badge>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                    >
                      {!mounted || theme === 'dark' ? (
                        <Sun className="size-4 text-amber-400" />
                      ) : (
                        <Moon className="size-4 text-slate-600" />
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    {!mounted || theme === 'dark' ? 'Açık Tema' : 'Koyu Tema'}
                  </TooltipContent>
                </Tooltip>
              </div>
            </div>
          </div>
        </header>

        {/* ─── DATA SOURCE BAR ─────────────────────────────────────── */}
        <div className="border-b border-border/50 bg-muted/30">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
            <div className="flex items-center gap-3 flex-wrap text-xs">
              <span className="text-muted-foreground font-medium flex items-center gap-1">
                <Database className="size-3" /> Veri Kaynağı:
              </span>

              <label className="cursor-pointer">
                <input
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={(e) => handleFileUpload(e, 'csv')}
                />
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-card border border-border hover:bg-accent transition-colors text-foreground">
                  <FileSpreadsheet className="size-3 text-emerald-500" />
                  CSV Yükle
                </span>
              </label>

              <label className="cursor-pointer">
                <input
                  type="file"
                  accept=".json"
                  className="hidden"
                  onChange={(e) => handleFileUpload(e, 'json')}
                />
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-card border border-border hover:bg-accent transition-colors text-foreground">
                  <FileJson className="size-3 text-amber-500" />
                  JSON Yükle
                </span>
              </label>

              <Separator orientation="vertical" className="h-4" />

              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs gap-1"
                onClick={useDemoData}
              >
                <FlaskConical className="size-3" />
                Demo Veri Kullan
              </Button>
            </div>
          </div>
        </div>

        {/* ─── MAIN CONTENT ────────────────────────────────────────── */}
        <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            {/* ─── TAB NAVIGATION ─────────────────────────────────── */}
            <TabsList className="w-full sm:w-auto mb-6 bg-card border border-border p-1 h-auto">
              {([
                { key: 'dashboard', icon: <LayoutDashboard className="size-4" />, label: 'Dashboard' },
                { key: 'experiments', icon: <FlaskConical className="size-4" />, label: 'Deney Tasarımcısı' },
                { key: 'results', icon: <Table2 className="size-4" />, label: 'Sonuçlar' },
                { key: 'algorithms', icon: <Cpu className="size-4" />, label: 'Algoritmalar' },
              ]).map(tab => {
                const isActive = activeTab === tab.key;
                return (
                  <TabsTrigger
                    key={tab.key}
                    value={tab.key}
                    className={[
                      'flex-1 sm:flex-initial gap-1.5 px-4 py-2.5 text-xs sm:text-sm font-medium transition-all duration-200 rounded-md',
                      isActive ? 'tab-active-indicator bg-primary text-primary-foreground shadow-sm' : 'hover:bg-muted text-muted-foreground hover:text-foreground',
                    ].join(' ')}
                  >
                    {tab.icon}
                    <span className="hidden sm:inline">{tab.label}</span>
                  </TabsTrigger>
                );
              })}
            </TabsList>

            {/* ─── TAB CONTENT ─────────────────────────────────────── */}
            <AnimatePresence mode="wait">
              {activeTab === 'dashboard' && (
                <motion.div key="dashboard" {...fadeIn} transition={{ duration: 0.3 }}>
                  <DashboardView onGoToResults={() => setActiveTab('results')} />
                </motion.div>
              )}
              {activeTab === 'experiments' && (
                <motion.div key="experiments" {...fadeIn} transition={{ duration: 0.3 }}>
                  <ExperimentDesignerView />
                </motion.div>
              )}
              {activeTab === 'results' && (
                <motion.div key="results" {...fadeIn} transition={{ duration: 0.3 }}>
                  <ResultsView />
                </motion.div>
              )}
              {activeTab === 'algorithms' && (
                <motion.div key="algorithms" {...fadeIn} transition={{ duration: 0.3 }}>
                  <AlgorithmsInfoView />
                </motion.div>
              )}
            </AnimatePresence>
          </Tabs>
        </main>

        {/* ─── FOOTER ──────────────────────────────────────────────── */}
        <footer className="footer-gradient-bg border-t border-border/30 mt-auto">
          <div className="footer-gradient-line" />
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <div className="w-5 h-5 rounded bg-gradient-to-br from-emerald-500 to-amber-500 flex items-center justify-center text-white text-[8px] font-bold">TS</div>
                <span>TSP Benchmark Studio <span className="font-mono text-[10px] px-1 py-0.5 rounded bg-muted/60">v1.2.0</span></span>
                <Separator orientation="vertical" className="h-3 hidden sm:block" />
                <span className="hidden sm:flex items-center gap-1">
                  Powered by <span className="font-medium text-foreground hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors cursor-default">Next.js 16</span> · <span className="font-medium text-foreground hover:text-amber-600 dark:hover:text-amber-400 transition-colors cursor-default">React 19</span>
                </span>
              </div>
              <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                <span className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors cursor-default">TSPLIB</span>
                <span>·</span>
                <span className="hover:text-amber-600 dark:hover:text-amber-400 transition-colors cursor-default">Recharts</span>
                <span>·</span>
                <span className="hover:text-violet-600 dark:hover:text-violet-400 transition-colors cursor-default">shadcn/ui</span>
                <Separator orientation="vertical" className="h-3 hidden sm:block" />
                <span className="hidden sm:block">TSPLIB Optimizasyon Algoritmaları Karşılaştırma Platformu</span>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </TooltipProvider>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// DASHBOARD VIEW
// ═══════════════════════════════════════════════════════════════════════════════

function DashboardView({ onGoToResults }: { onGoToResults: () => void }) {
  const store = useBenchmarkStore();
  const stats = store.getStats();
  const algoSummary = store.getAlgorithmSummary();
  const problemSummary = store.getProblemSummary();

  const chartData = useMemo(() => algoSummary.map(a => ({
    name: a.name,
    avgGap: a.avgGap,
    avgTime: a.avgTime,
    color: a.color,
  })), [algoSummary]);

  const timeData = useMemo(() => [...algoSummary]
    .sort((a, b) => a.avgTime - b.avgTime)
    .map(a => ({
      name: a.name,
      avgTime: a.avgTime,
      color: a.color,
    })), [algoSummary]);

  // Normalized radar data: invert GAP/Speed so higher = better, 0-100 scale
  const radarData = useMemo(() => {
    if (algoSummary.length === 0) return [];

    // Compute min/max for normalization
    const maxAvgGap = Math.max(...algoSummary.map(a => a.avgGap), 0.01);
    const minAvgGap = Math.min(...algoSummary.map(a => a.avgGap));
    const maxAvgTime = Math.max(...algoSummary.map(a => a.avgTime), 0.01);
    const minAvgTime = Math.min(...algoSummary.map(a => a.avgTime));
    const gapRange = maxAvgGap - minAvgGap || 1;
    const timeRange = maxAvgTime - minAvgTime || 1;

    const metrics = [
      { key: 'GAP Performansı', label: 'GAP Performansı' },
      { key: 'Hız', label: 'Hız' },
      { key: 'Tutarlılık', label: 'Tutarlılık' },
      { key: 'En İyi Skor', label: 'En İyi Skor' },
    ];

    return metrics.map((m) => {
      const point: Record<string, string | number> = { metric: m.label };
      for (const algo of algoSummary) {
        let score = 0;
        switch (m.key) {
          case 'GAP Performansı':
            // Lower GAP = higher score
            score = ((maxAvgGap - algo.avgGap) / gapRange) * 80 + 20;
            break;
          case 'Hız':
            // Lower time = higher score
            score = ((maxAvgTime - algo.avgTime) / timeRange) * 80 + 20;
            break;
          case 'Tutarlılık':
            // Lower gap range = higher consistency
            score = ((maxAvgGap - (algo.maxGap - algo.minGap)) / gapRange) * 80 + 20;
            break;
          case 'En İyi Skor':
            // Lower best gap = higher score (use minGap)
            score = ((maxAvgGap - algo.minGap) / gapRange) * 80 + 20;
            break;
        }
        point[algo.name] = Math.round(Math.max(0, Math.min(100, score)));
      }
      return point;
    });
  }, [algoSummary]);

  return (
    <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-6">
      {/* ─── DASHBOARD FILTERS ─────────────────────────────────── */}
      <motion.div variants={fadeIn}>
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          {/* Category Filter Pills */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground font-medium mr-1">Kategori:</span>
            {(['all', 'small', 'medium', 'large'] as const).map((cat) => (
              <button
                key={cat}
                onClick={() => store.setDashboardFilter(cat)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 ${
                  store.dashboardFilter === cat
                    ? cat === 'all'
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : cat === 'small'
                        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 shadow-sm'
                        : cat === 'medium'
                          ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 shadow-sm'
                          : 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400 shadow-sm'
                    : 'bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground'
                }`}
              >
                {cat === 'all' ? 'Tümü' : CATEGORY_LABELS[cat]}
              </button>
            ))}
          </div>

          {/* Algorithm Filter Dropdown */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground font-medium mr-1">Algoritma:</span>
            <Select
              value={store.dashboardAlgorithmFilter}
              onValueChange={(v) => store.setDashboardAlgorithmFilter(v)}
            >
              <SelectTrigger className={`h-8 w-40 text-xs${store.dashboardAlgorithmFilter !== 'all' ? ' filter-active' : ''}`}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all" className="text-xs">Tüm Algoritmalar</SelectItem>
                {ALGORITHMS.filter(a => a.ready).map(a => (
                  <SelectItem key={a.id} value={a.shortName} className="text-xs">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: a.color }} />
                      {a.name}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </motion.div>

      {/* ─── STATS CARDS ───────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <motion.div variants={fadeIn}>
          <Card className="card-lift card-shimmer card-glow-hover stat-card-border-emerald stat-card-pattern overflow-hidden border-emerald-500/20">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground font-medium">Toplam Deney</p>
                  <p className="text-2xl font-bold tabular-nums text-emerald-600 dark:text-emerald-400 mt-1 count-up">
                    {stats.totalExperiments}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center stat-icon-glow">
                  <Activity className="size-5 text-emerald-600 dark:text-emerald-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeIn}>
          <Card className="card-lift card-shimmer card-glow-hover stat-card-border-amber stat-card-pattern overflow-hidden border-amber-500/20">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground font-medium">Test Edilen Algoritma</p>
                  <p className="text-2xl font-bold tabular-nums text-amber-600 dark:text-amber-400 mt-1 count-up">
                    {stats.algorithmsTested}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center stat-icon-glow">
                  <Cpu className="size-5 text-amber-600 dark:text-amber-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeIn}>
          <Card className="card-lift card-shimmer card-glow-hover stat-card-border-emerald stat-card-pattern overflow-hidden border-emerald-500/20">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground font-medium">Ortalama GAP</p>
                  <p className="text-2xl font-bold tabular-nums mt-1">
                    <span className={gapColor(stats.avgGap)}>{stats.avgGap}%</span>
                  </p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center stat-icon-glow">
                  <TrendingDown className="size-5 text-emerald-600 dark:text-emerald-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeIn}>
          <Card className="card-lift card-shimmer card-glow-hover stat-card-border-amber stat-card-pattern overflow-hidden border-amber-500/20">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground font-medium">En İyi Algoritma</p>
                  <p className="text-lg font-bold text-amber-600 dark:text-amber-400 mt-1 truncate">
                    {stats.bestAlgorithm}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center stat-icon-glow">
                  <Trophy className="size-5 text-amber-600 dark:text-amber-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* ─── CHARTS ────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Algorithm Performance (GAP) */}
        <motion.div variants={fadeIn}>
          <Card className="overflow-hidden">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <BarChart3 className="size-4 text-emerald-500" />
                Algoritma Performansı (Ort. GAP %)
              </CardTitle>
              <CardDescription>Düşük GAP = daha iyi performans</CardDescription>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border/50" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} className="fill-muted-foreground" />
                    <YAxis tick={{ fontSize: 11 }} className="fill-muted-foreground" unit="%" />
                    <RTooltip
                      contentStyle={{
                        backgroundColor: 'var(--card)',
                        border: '1px solid var(--border)',
                        borderRadius: '8px',
                        fontSize: '12px',
                        color: 'var(--card-foreground)',
                      }}
                      formatter={(value: number) => [`${value}%`, 'Ort. GAP']}
                    />
                    <Bar dataKey="avgGap" radius={[4, 4, 0, 0]}>
                      {chartData.map((entry, idx) => (
                        <Cell key={idx} fill={entry.color} fillOpacity={0.85} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Time Comparison */}
        <motion.div variants={fadeIn}>
          <Card className="overflow-hidden">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Clock className="size-4 text-amber-500" />
                Ortalama Çalışma Süresi (ms)
              </CardTitle>
              <CardDescription>Algoritma bazlı ortalama çalışma süresi</CardDescription>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={timeData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border/50" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} className="fill-muted-foreground" />
                    <YAxis tick={{ fontSize: 11 }} className="fill-muted-foreground" unit=" ms" />
                    <RTooltip
                      contentStyle={{
                        backgroundColor: 'var(--card)',
                        border: '1px solid var(--border)',
                        borderRadius: '8px',
                        fontSize: '12px',
                        color: 'var(--card-foreground)',
                      }}
                      formatter={(value: number) => [`${value} ms`, 'Ort. Süre']}
                    />
                    <Bar dataKey="avgTime" radius={[4, 4, 0, 0]}>
                      {timeData.map((entry, idx) => (
                        <Cell key={idx} fill={entry.color} fillOpacity={0.85} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* ─── RADAR CHART: Algorithm Comparison ────────────────── */}
      <motion.div variants={fadeIn}>
        <Card className="overflow-hidden">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <RadarIcon className="size-4 text-violet-500" />
              Algoritma Karşılaştırma (Radar)
            </CardTitle>
            <CardDescription>Normalleştirilmiş metrikler üzerinden algoritma karşılaştırması (0-100)</CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                  <PolarGrid stroke="var(--border)" />
                  <PolarAngleAxis
                    dataKey="metric"
                    tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }}
                  />
                  <PolarRadiusAxis
                    angle={30}
                    domain={[0, 100]}
                    tick={{ fontSize: 9, fill: 'var(--muted-foreground)' }}
                  />
                  {algoSummary.map((algo) => (
                    <Radar
                      key={algo.name}
                      name={algo.name}
                      dataKey={algo.name}
                      stroke={algo.color}
                      fill={algo.color}
                      fillOpacity={0.12}
                      strokeWidth={2}
                    />
                  ))}
                  <RTooltip
                    contentStyle={{
                      backgroundColor: 'var(--card)',
                      border: '1px solid var(--border)',
                      borderRadius: '8px',
                      fontSize: '12px',
                      color: 'var(--card-foreground)',
                    }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            {/* Legend */}
            <div className="flex flex-wrap items-center justify-center gap-3 mt-2">
              {algoSummary.map((algo) => (
                <div key={algo.name} className="flex items-center gap-1.5 text-xs">
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: algo.color }}
                  />
                  <span className="text-muted-foreground">{algo.name}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* ─── PROBLEM COVERAGE ──────────────────────────────────── */}
      <motion.div variants={fadeIn}>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Target className="size-4 text-emerald-500" />
              Problem Kapsam Özeti
            </CardTitle>
            <CardDescription>
              {problemSummary.length} problem test edildi
            </CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="overflow-x-auto max-h-72 rounded-md border border-border/50">
              <Table className="min-w-[540px]">
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs whitespace-nowrap">Problem</TableHead>
                    <TableHead className="text-xs text-right whitespace-nowrap">Boyut</TableHead>
                    <TableHead className="text-xs text-right whitespace-nowrap">Optimal</TableHead>
                    <TableHead className="text-xs whitespace-nowrap">Kategori</TableHead>
                    <TableHead className="text-xs whitespace-nowrap">En İyi Algoritma</TableHead>
                    <TableHead className="text-xs text-right whitespace-nowrap">En İyi GAP</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {problemSummary.map((p) => (
                    <TableRow key={p.name} className="table-row-hover">
                      <TableCell className="whitespace-nowrap"><ProblemDetailTooltip problemName={p.name} /></TableCell>
                      <TableCell className="text-xs text-right tabular-nums whitespace-nowrap">{p.dim}</TableCell>
                      <TableCell className="text-xs text-right tabular-nums whitespace-nowrap">{formatNumber(p.optimal)}</TableCell>
                      <TableCell className="whitespace-nowrap">
                        <Badge variant="secondary" className={`text-[10px] px-1.5 py-0 ${CATEGORY_BG[p.category]}`}>
                          {CATEGORY_LABELS[p.category]}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs font-medium whitespace-nowrap">{p.bestAlgo}</TableCell>
                      <TableCell className="text-xs text-right whitespace-nowrap">
                        <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ${gapBg(p.bestGap)}`}>
                          {p.bestGap}%
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* ─── QUICK EXPERIMENT SUMMARY (Son Deney Özeti) ─────── */}
      <motion.div variants={fadeIn}>
        <Card className="overflow-hidden">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <FlaskConical className="size-4 text-emerald-500" />
                Son Deney Özeti
              </CardTitle>
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs gap-1"
                onClick={onGoToResults}
              >
                <Table2 className="size-3" />
                Sonuçlara Git
              </Button>
            </div>
            <CardDescription>
              Mevcut deney konfigürasyonu ve performans özeti
            </CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Configuration Summary */}
              <div className="p-3 rounded-lg bg-muted/30 border border-border/50 space-y-3">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                  <Settings2 className="size-3" /> Konfigürasyon
                </h4>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex items-center gap-1.5">
                    <Cpu className="size-3 text-emerald-500" />
                    <span className="text-muted-foreground">Algoritma:</span>
                    <span className="font-semibold">{ALGORITHMS.filter(a => a.ready).length}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Target className="size-3 text-amber-500" />
                    <span className="text-muted-foreground">Problem:</span>
                    <span className="font-semibold">{problemSummary.length}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Hash className="size-3 text-violet-500" />
                    <span className="text-muted-foreground">Deney:</span>
                    <span className="font-semibold">{stats.totalExperiments}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Timer className="size-3 text-rose-500" />
                    <span className="text-muted-foreground">Ort. Süre:</span>
                    <span className="font-semibold">{stats.avgTime}ms</span>
                  </div>
                </div>

                {/* Algorithm × Problem mini matrix */}
                <div>
                  <p className="text-[10px] text-muted-foreground mb-1.5">Algoritma × Problem Matrisi</p>
                  <div className="flex flex-wrap gap-1">
                    {algoSummary.slice(0, 5).map(a => (
                      <span
                        key={a.name}
                        className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium"
                        style={{ backgroundColor: a.color + '15', color: a.color }}
                      >
                        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: a.color }} />
                        {a.name}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Best Performing Algorithm */}
              <div className="p-3 rounded-lg border border-border/50 space-y-3" style={{ background: 'linear-gradient(135deg, oklch(0.7 0.15 165 / 0.05), transparent)' }}>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                  <Trophy className="size-3 text-amber-500" /> En İyi Performans
                </h4>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500 to-amber-500 flex items-center justify-center text-white text-xs font-bold shadow-lg">
                    {stats.bestAlgorithm.slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <p className="text-sm font-bold">{stats.bestAlgorithm}</p>
                    <p className="text-xs text-muted-foreground">
                      Ortalama GAP: <span className={gapColor(stats.avgGap)}>{stats.avgGap}%</span>
                    </p>
                  </div>
                </div>

                {/* Quick stats row */}
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="p-2 rounded-md bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-200/30 dark:border-emerald-800/20">
                    <p className="text-[10px] text-muted-foreground">En İyi GAP</p>
                    <p className="text-sm font-bold text-emerald-600 dark:text-emerald-400">{stats.bestGap}%</p>
                  </div>
                  <div className="p-2 rounded-md bg-amber-50 dark:bg-amber-900/10 border border-amber-200/30 dark:border-amber-800/20">
                    <p className="text-[10px] text-muted-foreground">Algoritma</p>
                    <p className="text-sm font-bold text-amber-600 dark:text-amber-400">{stats.algorithmsTested}</p>
                  </div>
                  <div className="p-2 rounded-md bg-violet-50 dark:bg-violet-900/10 border border-violet-200/30 dark:border-violet-800/20">
                    <p className="text-[10px] text-muted-foreground">Problem</p>
                    <p className="text-sm font-bold text-violet-600 dark:text-violet-400">{stats.problemsCovered}</p>
                  </div>
                </div>

                <Button
                  variant="default"
                  size="sm"
                  className="w-full h-8 text-xs gap-1.5 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white shadow-md shadow-emerald-500/20"
                  onClick={onGoToResults}
                >
                  <BarChart3 className="size-3.5" />
                  Detaylı Sonuçları Görüntüle
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// EXPERIMENT DESIGNER VIEW
// ═══════════════════════════════════════════════════════════════════════════════

function formatElapsed(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)} sn`;
  if (ms < 3600000) return `${Math.floor(ms / 60000)}dk ${Math.floor((ms % 60000) / 1000)}sn`;
  return `${Math.floor(ms / 3600000)}sa ${Math.floor((ms % 3600000) / 60000)}dk`;
}

function ExperimentDesignerView() {
  const store = useBenchmarkStore();
  const { experiment } = store;
  const [expandedAlgo, setExpandedAlgo] = useState<string | null>(null);
  const [problemSearch, setProblemSearch] = useState('');
  const [openCategories, setOpenCategories] = useState<Record<ProblemCategory, boolean>>({
    small: true, medium: true, large: true,
  });
  const [elapsedDisplay, setElapsedDisplay] = useState(0);
  const socketRef = useRef<Socket | null>(null);
  const elapsedIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const problemsByCategory = useMemo(() => {
    const filtered = problemSearch
      ? PROBLEMS.filter(p => p.name.toLowerCase().includes(problemSearch.toLowerCase()))
      : PROBLEMS;
    return {
      small: filtered.filter(p => p.category === 'small'),
      medium: filtered.filter(p => p.category === 'medium'),
      large: filtered.filter(p => p.category === 'large'),
    };
  }, [problemSearch]);

  const localSearchAlgos = ALGORITHMS.filter(a => a.type === 'local_search');
  const metaHeuristicAlgos = ALGORITHMS.filter(a => a.type === 'meta_heuristic');

  const toggleCategory = (cat: ProblemCategory) => {
    setOpenCategories(prev => ({ ...prev, [cat]: !prev[cat] }));
  };

  const matrixCount = store.getExperimentMatrixCount();

  const estimatedTime = useMemo(() => {
    const avgTimePerExperiment = 120; // ms
    const totalTimeMs = matrixCount * experiment.nRuns * avgTimePerExperiment;
    if (totalTimeMs < 1000) return `${totalTimeMs} ms`;
    if (totalTimeMs < 60000) return `~${(totalTimeMs / 1000).toFixed(1)} sn`;
    return `~${(totalTimeMs / 60000).toFixed(1)} dk`;
  }, [matrixCount, experiment.nRuns]);

  const selectedProblemCounts = useMemo(() => ({
    small: experiment.selectedProblems.filter(name => PROBLEMS.find(p => p.name === name && p.category === 'small')).length,
    medium: experiment.selectedProblems.filter(name => PROBLEMS.find(p => p.name === name && p.category === 'medium')).length,
    large: experiment.selectedProblems.filter(name => PROBLEMS.find(p => p.name === name && p.category === 'large')).length,
  }), [experiment.selectedProblems]);

  // ─── Socket.io connection & run handlers ────────────────────────────────
  const cleanupSocket = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
    }
    if (elapsedIntervalRef.current) {
      clearInterval(elapsedIntervalRef.current);
      elapsedIntervalRef.current = null;
    }
  }, []);

  const startRun = useCallback(async () => {
    const selectedAlgos = experiment.selectedAlgorithms;
    const selectedProbs = experiment.selectedProblems;

    if (selectedAlgos.length === 0) {
      toast.error('En az bir algoritma seçin');
      return;
    }
    if (selectedProbs.length === 0) {
      toast.error('En az bir problem seçin');
      return;
    }
    if (store.isRunning) {
      toast.warning('Zaten bir deney çalışıyor');
      return;
    }

    const config = {
      algorithms: selectedAlgos.map(id => {
        const algo = ALGORITHMS.find(a => a.id === id);
        return { id, params: store.experiment.algorithmParams[id] || {} };
      }),
      problems: selectedProbs,
      settings: {
        nRuns: experiment.nRuns,
        workers: experiment.workers,
        seed: experiment.seed,
        skipCached: experiment.skipCached,
      },
    };

    try {
      const res = await fetch('/api/benchmark/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });

      if (!res.ok) {
        const err = await res.json();
        toast.error(err.error || 'Deney başlatılamadı');
        return;
      }

      const data = await res.json();
      store.setIsRunning(true);
      store.setRunId(data.runId);
      store.setRunStartTime(Date.now());
      store.setRunProgress(null);
      store.setRunError(null);
      store.setRunComplete(false);
      // runResults is reset via addRunResults pattern
      setElapsedDisplay(0);

      toast.info(`Deney ${data.totalExperiments} kombinasyonla başlatıldı`);

      // Start elapsed timer
      elapsedIntervalRef.current = setInterval(() => {
        if (store.runStartTime) {
          setElapsedDisplay(Date.now() - store.runStartTime);
        }
      }, 1000);

      // Connect socket.io
      socketRef.current = io('/?XTransformPort=3003', {
        transports: ['websocket', 'polling'],
      });

      socketRef.current.on('benchmark', (msg: { type: string; data: Record<string, unknown> }) => {
        switch (msg.type) {
          case 'progress': {
            const pd = msg.data as unknown as RunProgress;
            store.setRunProgress(pd);
            break;
          }
          case 'result': {
            const rd = msg.data as {
              problem: string; dimension: number; optimal: number; algorithm: string;
              avg_gap: number; best_gap: number; avg_time_ms: number;
              avg_length: number; best_length: number; n_runs: number;
            };
            const prob = PROBLEMS.find(p => p.name === rd.problem);
            store.addRunResult({
              problem: rd.problem,
              dimension: rd.dimension,
              category: prob?.category || 'small',
              optimal: rd.optimal,
              strategy: rd.algorithm,
              avgGap: rd.avg_gap,
              bestGap: rd.best_gap,
              avgTimeMs: rd.avg_time_ms,
              elapsedMs: rd.avg_time_ms * rd.n_runs,
              avgLength: rd.avg_length,
              bestLength: rd.best_length,
              nRuns: rd.n_runs,
              timestamp: new Date().toISOString(),
              cached: false,
            });
            break;
          }
          case 'complete': {
            const cd = msg.data as { results?: unknown[]; total_results?: number; total_time_ms?: number };
            if (cd.results && cd.results.length > 0) {
              const mappedResults: BenchmarkResult[] = (cd.results as Record<string, unknown>[]).map(r => {
                const prob = PROBLEMS.find(p => p.name === r.problem);
                return {
                  problem: r.problem as string,
                  dimension: r.dimension as number,
                  category: prob?.category || 'small',
                  optimal: r.optimal as number,
                  strategy: r.algorithm as string,
                  avgGap: r.avg_gap as number,
                  bestGap: r.best_gap as number,
                  avgTimeMs: r.avg_time_ms as number,
                  elapsedMs: r.avg_time_ms as number * (r.n_runs as number || 1),
                  avgLength: r.avg_length as number,
                  bestLength: r.best_length as number,
                  nRuns: r.n_runs as number,
                  timestamp: new Date().toISOString(),
                  cached: false,
                };
              });
              store.addRunResults(mappedResults);
            }
            store.setIsRunning(false);
            store.setRunComplete(true);
            store.setRunProgress(null);
            store.setRunStartTime(null);
            cleanupSocket();
            // Merge results into main store
            store.mergeRunResults();
            toast.success(`Deney tamamlandı! ${cd.total_results ?? 0} sonuç üretildi.`);
            break;
          }
          case 'stopped': {
            const sd = msg.data as { completed?: number; total?: number; results?: unknown[] };
            if (sd.results && sd.results.length > 0) {
              const mappedResults: BenchmarkResult[] = (sd.results as Record<string, unknown>[]).map(r => {
                const prob = PROBLEMS.find(p => p.name === r.problem);
                return {
                  problem: r.problem as string,
                  dimension: r.dimension as number,
                  category: prob?.category || 'small',
                  optimal: r.optimal as number,
                  strategy: r.algorithm as string,
                  avgGap: r.avg_gap as number,
                  bestGap: r.best_gap as number,
                  avgTimeMs: r.avg_time_ms as number,
                  elapsedMs: r.avg_time_ms as number * (r.n_runs as number || 1),
                  avgLength: r.avg_length as number,
                  bestLength: r.best_length as number,
                  nRuns: r.n_runs as number,
                  timestamp: new Date().toISOString(),
                  cached: false,
                };
              });
              store.addRunResults(mappedResults);
            }
            store.setIsRunning(false);
            store.setRunProgress(null);
            store.setRunStartTime(null);
            cleanupSocket();
            store.mergeRunResults();
            toast.warning(`Deney durduruldu. ${sd.completed ?? 0}/${sd.total ?? 0} deney tamamlandı.`);
            break;
          }
          case 'error': {
            const ed = msg.data as { message?: string };
            store.setRunError(ed.message || 'Bilinmeyen hata');
            store.setIsRunning(false);
            store.setRunStartTime(null);
            cleanupSocket();
            toast.error(ed.message || 'Deney sırasında hata oluştu');
            break;
          }
          case 'status': {
            // Initial status on connect - ignore
            break;
          }
        }
      });

      socketRef.current.on('connect_error', () => {
        // Fallback: poll status if socket fails
        console.warn('[Socket.io] Connection error, falling back to polling');
      });
    } catch {
      toast.error('Deney başlatılamadı');
    }
  }, [experiment, store, cleanupSocket]);

  const stopRun = useCallback(async () => {
    try {
      const res = await fetch('/api/benchmark/run/stop', { method: 'POST' });
      if (res.ok) {
        toast.info('Deney durduruluyor...');
      }
    } catch {
      toast.error('Deney durdurulamadı');
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupSocket();
    };
  }, [cleanupSocket]);

  function getAlgoGlowClass(color: string): string {
    if (color.includes('10b981') || color.includes('059669')) return 'algo-glow-emerald';
    if (color.includes('f59e0b') || color.includes('d97706')) return 'algo-glow-amber';
    if (color.includes('8b5cf6') || color.includes('7c3aed')) return 'algo-glow-violet';
    if (color.includes('ef4444') || color.includes('dc2626')) return 'algo-glow-red';
    if (color.includes('06b6d4') || color.includes('0891b2')) return 'algo-glow-cyan';
    if (color.includes('f97316') || color.includes('ea580c')) return 'algo-glow-orange';
    if (color.includes('14b8a6') || color.includes('0d9488')) return 'algo-glow-teal';
    if (color.includes('ec4899') || color.includes('db2777')) return 'algo-glow-pink';
    return '';
  }

  const renderAlgorithmCard = (algo: Algorithm) => {
    const isSelected = experiment.selectedAlgorithms.includes(algo.id);
    const isExpanded = expandedAlgo === algo.id;
    const currentParams = experiment.algorithmParams[algo.id] || {};

    return (
      <Card
        key={algo.id}
        className={`card-lift overflow-hidden transition-all duration-200 ${
          isSelected
            ? 'border-emerald-500/50 shadow-md'
            : algo.ready
            ? 'border-border/50 opacity-70 hover:opacity-100'
            : 'border-amber-500/30 opacity-60 hover:opacity-90'
        } ${getAlgoGlowClass(algo.color)}`}
      >
        <CardContent className="p-4 relative">
          <div className="absolute top-0 left-0 bottom-0 w-1 rounded-l-sm" style={{ backgroundColor: algo.color }} />
          <div className="flex items-start gap-3 pl-2">
            <Checkbox
              checked={isSelected}
              onCheckedChange={() => store.toggleAlgorithm(algo.id)}
              className="mt-0.5"
            />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-sm">{algo.name}</span>
                {algo.ready ? (
                  <Badge className="text-[10px] px-1.5 py-0 bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800">
                    Hazır
                  </Badge>
                ) : (
                  <Badge className="text-[10px] px-1.5 py-0 bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border-amber-200 dark:border-amber-800">
                    Planlanıyor
                  </Badge>
                )}
                <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                  {algo.type === 'local_search' ? 'Local Search' : 'Meta-Heuristic'}
                </Badge>
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0 font-mono">
                  {algo.complexity}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{algo.description}</p>

              {/* Expand Button */}
              {algo.parameters.length > 0 && isSelected && (
                <button
                  onClick={() => setExpandedAlgo(isExpanded ? null : algo.id)}
                  className="mt-2 flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400 hover:underline"
                >
                  <SlidersHorizontal className="size-3" />
                  Parametreler ({algo.parameters.length})
                  {isExpanded ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
                </button>
              )}
            </div>

            {/* Color dot */}
            <div
              className="w-3 h-3 rounded-full shrink-0 mt-1"
              style={{ backgroundColor: algo.color }}
            />
          </div>

          {/* Parameter Form */}
          {isExpanded && isSelected && algo.parameters.length > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-3 pt-3 border-t border-border"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                  <Settings2 className="size-3" /> Parametre Yapılandırması
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 text-[10px] px-2"
                  onClick={() => store.resetAlgorithmParams(algo.id)}
                >
                  <RefreshCw className="size-2.5 mr-1" />
                  Varsayılana Sıfırla
                </Button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {algo.parameters.map((param) => {
                  const currentValue = currentParams[param.key] ?? param.default;
                  return (
                    <div key={param.key} className="space-y-1">
                      <label className="text-xs font-medium flex items-center gap-1">
                        {param.label}
                        {param.unit && (
                          <span className="text-muted-foreground font-normal">({param.unit})</span>
                        )}
                      </label>
                      {param.type === 'number' ? (
                        <Input
                          type="number"
                          value={currentValue as number}
                          min={param.min}
                          max={param.max}
                          step={param.step}
                          onChange={(e) => store.setAlgorithmParam(algo.id, param.key, parseFloat(e.target.value) || 0)}
                          className="h-8 text-xs"
                        />
                      ) : (
                        <Select
                          value={currentValue as string}
                          onValueChange={(v) => store.setAlgorithmParam(algo.id, param.key, v)}
                        >
                          <SelectTrigger className="h-8 text-xs w-full">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {param.options?.map((opt) => (
                              <SelectItem key={opt.value} value={opt.value} className="text-xs">
                                {opt.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                      <p className="text-[10px] text-muted-foreground">{param.description}</p>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}
        </CardContent>
      </Card>
    );
  };

  const renderProblemGroup = (cat: ProblemCategory, problems: typeof PROBLEMS) => {
    const allSelected = problems.every(p => experiment.selectedProblems.includes(p.name));
    const count = selectedProblemCounts[cat];

    return (
      <Collapsible
        key={cat}
        open={openCategories[cat]}
        onOpenChange={() => toggleCategory(cat)}
      >
        <CollapsibleTrigger asChild>
          <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors cursor-pointer">
            <div className="flex items-center gap-2">
              <motion.div
                animate={{ rotate: openCategories[cat] ? 90 : 0 }}
                transition={{ duration: 0.2 }}
              >
                <ChevronRight className="size-4 text-muted-foreground" />
              </motion.div>
              <Badge className={`text-[10px] px-1.5 py-0 ${CATEGORY_BG[cat]}`}>
                {CATEGORY_LABELS[cat]}
              </Badge>
              <span className="text-sm font-medium">
                {problems.length} Problem
              </span>
              <span className="text-xs text-muted-foreground">
                ({count} seçili)
              </span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-[10px] px-2"
              onClick={(e) => {
                e.stopPropagation();
                if (allSelected) {
                  store.clearProblemSelection();
                } else {
                  store.selectAllProblems(cat);
                }
              }}
            >
              {allSelected ? 'Temizle' : 'Hepsini Seç'}
            </Button>
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="mt-1 ml-4 space-y-0.5 max-h-52 overflow-y-auto rounded-md border border-border/50">
            {problems.map((p) => {
              const checked = experiment.selectedProblems.includes(p.name);
              return (
                <label
                  key={p.name}
                  className={`flex items-center gap-3 px-3 py-2 rounded-md text-xs cursor-pointer transition-colors hover:bg-muted/50 ${
                    checked ? 'bg-emerald-50 dark:bg-emerald-900/10' : ''
                  }`}
                >
                  <Checkbox
                    checked={checked}
                    onCheckedChange={() => store.toggleProblem(p.name)}
                  />
                  <span className="font-mono font-medium min-w-[80px] cursor-help underline decoration-dotted underline-offset-2 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"><ProblemDetailTooltip problemName={p.name} /></span>
                  <span className="text-muted-foreground tabular-nums">n={p.dimension}</span>
                  <span className="text-muted-foreground tabular-nums">opt={formatNumber(p.optimal)}</span>
                </label>
              );
            })}
          </div>
        </CollapsibleContent>
      </Collapsible>
    );
  };

  return (
    <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-6">
      {/* ─── ALGORITHM SELECTION ───────────────────────────────── */}
      <motion.div variants={fadeIn}>
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Cpu className="size-4 text-emerald-500" />
                  Algoritma Seçimi
                </CardTitle>
                <CardDescription>
                  {experiment.selectedAlgorithms.length} algoritma seçili
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => store.selectAllAlgorithms()}
                >
                  Hepsini Seç
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => store.clearAlgorithmSelection()}
                >
                  <Trash2 className="size-3 mr-1" />
                  Temizle
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Local Search */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 text-xs">
                  Local Search (Hazır)
                </Badge>
                <Separator className="flex-1" />
              </div>
              <div className="space-y-2">
                {localSearchAlgos.map(renderAlgorithmCard)}
              </div>
            </div>

            {/* Meta-Heuristics */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 text-xs">
                  Meta-Heuristic (Planlanıyor)
                </Badge>
                <Separator className="flex-1" />
              </div>
              <div className="space-y-2">
                {metaHeuristicAlgos.map(renderAlgorithmCard)}
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* ─── PROBLEM SELECTION ─────────────────────────────────── */}
      <motion.div variants={fadeIn}>
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Target className="size-4 text-amber-500" />
                  Problem Seçimi
                </CardTitle>
                <CardDescription>
                  {experiment.selectedProblems.length} / {PROBLEMS.length} problem seçili
                </CardDescription>
              </div>
              <div className="flex gap-2 items-center">
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3 text-muted-foreground" />
                  <Input
                    placeholder="Problem ara..."
                    value={problemSearch}
                    onChange={(e) => setProblemSearch(e.target.value)}
                    className="h-7 w-40 text-xs pl-8"
                  />
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => store.selectAllProblems()}
                >
                  Hepsini Seç
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => store.clearProblemSelection()}
                >
                  <Trash2 className="size-3 mr-1" />
                  Temizle
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {renderProblemGroup('small', problemsByCategory.small)}
            {renderProblemGroup('medium', problemsByCategory.medium)}
            {renderProblemGroup('large', problemsByCategory.large)}
          </CardContent>
        </Card>
      </motion.div>

      {/* ─── PRESETS ──────────────────────────────────────────── */}
      <motion.div variants={fadeIn}>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex items-center gap-2">
                <ListChecks className="size-4 text-emerald-500" />
                <span className="text-sm font-semibold">Hazır Ayarlar</span>
              </div>
              <Select onValueChange={(v) => {
                const preset = PRESETS.find(p => p.id === v);
                if (preset) {
                  const c = preset.config;
                  store.clearAlgorithmSelection();
                  store.clearProblemSelection();
                  for (const algoId of c.algorithms) store.toggleAlgorithm(algoId);
                  for (const probName of c.problems) store.toggleProblem(probName);
                  store.setExperimentSetting('nRuns', c.nRuns);
                  store.setExperimentSetting('workers', c.workers);
                  store.setExperimentSetting('seed', c.seed);
                  store.setExperimentSetting('skipCached', c.skipCached);
                  toast.success(`"${preset.name}" ayarı uygulandı`);
                }
              }}>
                <SelectTrigger className="h-8 w-48 text-xs">
                  <SelectValue placeholder="Preset seçin..." />
                </SelectTrigger>
                <SelectContent>
                  {PRESETS.map(p => (
                    <SelectItem key={p.id} value={p.id} className="text-xs">
                      <div className="flex flex-col">
                        <span className="font-medium">{p.name}</span>
                        <span className="text-muted-foreground text-[10px]">{p.desc}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* ─── GENERAL SETTINGS ─────────────────────────────────── */}
      <motion.div variants={fadeIn}>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Settings2 className="size-4 text-emerald-500" />
              Genel Ayarlar
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="space-y-1">
                <label className="text-xs font-medium">Tekrar Sayısı (nRuns)</label>
                <Input
                  type="number"
                  value={experiment.nRuns}
                  min={1}
                  max={100}
                  onChange={(e) => store.setExperimentSetting('nRuns', parseInt(e.target.value) || 1)}
                  className="h-8 text-xs"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium">Worker Sayısı</label>
                <Input
                  type="number"
                  value={experiment.workers}
                  min={1}
                  max={32}
                  onChange={(e) => store.setExperimentSetting('workers', parseInt(e.target.value) || 1)}
                  className="h-8 text-xs"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium">Tohum (Seed)</label>
                <Input
                  type="number"
                  value={experiment.seed}
                  min={0}
                  onChange={(e) => store.setExperimentSetting('seed', parseInt(e.target.value) || 0)}
                  className="h-8 text-xs"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium">Önbelleği Atla</label>
                <div className="flex items-center gap-2 mt-1">
                  <Switch
                    checked={experiment.skipCached}
                    onCheckedChange={(v) => store.setExperimentSetting('skipCached', v)}
                  />
                  <span className="text-xs text-muted-foreground">
                    {experiment.skipCached ? 'Evet' : 'Hayır'}
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* ─── EXPERIMENT MATRIX PREVIEW ────────────────────────── */}
      <motion.div variants={fadeIn}>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Layers className="size-4 text-amber-500" />
              Deney Matrisi Önizleme
            </CardTitle>
            <CardDescription>
              {experiment.selectedAlgorithms.length} algoritma × {experiment.selectedProblems.length} problem = {matrixCount} deney kombinasyonu
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Experiment Summary Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 rounded-lg bg-muted/30 border border-border/50">
              <div className="text-center">
                <p className="text-xs text-muted-foreground">Toplam Deney</p>
                <p className="text-lg font-bold tabular-nums text-emerald-600 dark:text-emerald-400">
                  {matrixCount * experiment.nRuns}
                </p>
              </div>
              <div className="text-center">
                <p className="text-xs text-muted-foreground">Tahmini Süre</p>
                <p className="text-lg font-bold tabular-nums text-amber-600 dark:text-amber-400">
                  {estimatedTime}
                </p>
              </div>
              <div className="text-center">
                <p className="text-xs text-muted-foreground">Önbellek Durumu</p>
                <p className="text-lg font-bold tabular-nums">
                  {(() => {
                    const results = store.getFilteredResults();
                    const cachedCount = experiment.selectedAlgorithms.reduce((acc, algoId) => {
                      const algo = ALGORITHMS.find(a => a.id === algoId);
                      return acc + experiment.selectedProblems.filter(p => results.some(r => r.problem === p && r.strategy === (algo?.shortName || algoId))).length;
                    }, 0);
                    return (
                      <span className={cachedCount > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-muted-foreground'}>
                        {cachedCount}/{matrixCount}
                      </span>
                    );
                  })()}
                </p>
              </div>
            </div>

            {/* Stats bar */}
            <div className="flex items-center gap-4 flex-wrap text-xs">
              <div className="flex items-center gap-1 text-muted-foreground">
                <Hash className="size-3" />
                Toplam kombinasyon: <strong className="text-foreground">{matrixCount}</strong>
              </div>
              <div className="flex items-center gap-1 text-muted-foreground">
                <Timer className="size-3" />
                Tahmini süre: <strong className="text-foreground">{estimatedTime}</strong>
              </div>
              <div className="flex items-center gap-1 text-muted-foreground">
                <Activity className="size-3" />
                Tekrar başına: <strong className="text-foreground">{experiment.nRuns} run</strong>
              </div>
            </div>

            {/* Matrix preview table */}
            <div className="overflow-x-auto max-h-60 rounded-md border border-border/50">
              <Table className="min-w-max">
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs sticky left-0 bg-card z-10 whitespace-nowrap min-w-[120px]">Problem</TableHead>
                    {experiment.selectedAlgorithms.map(id => {
                      const algo = ALGORITHMS.find(a => a.id === id);
                      return (
                        <TableHead key={id} className="text-xs text-center min-w-[60px] whitespace-nowrap">
                          <span style={{ color: algo?.color }}>{algo?.shortName || id}</span>
                        </TableHead>
                      );
                    })}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {experiment.selectedProblems.slice(0, 20).map(name => {
                    const prob = PROBLEMS.find(p => p.name === name);
                    return (
                      <TableRow key={name}>
                        <TableCell className="text-xs font-mono sticky left-0 bg-card z-10 whitespace-nowrap">
                          <ProblemDetailTooltip problemName={name} />
                          <span className="text-muted-foreground ml-1">({prob?.dimension})</span>
                        </TableCell>
                        {experiment.selectedAlgorithms.map(algoId => (
                          <TableCell key={algoId} className="text-center p-2">
                            <CheckCircle2 className="size-3.5 text-emerald-500 inline" />
                          </TableCell>
                        ))}
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
            {experiment.selectedProblems.length > 20 && (
              <p className="text-xs text-muted-foreground text-center">
                ...ve {experiment.selectedProblems.length - 20} problem daha
              </p>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* ─── RUN / STOP BUTTON ─────────────────────────────────── */}
      <motion.div variants={fadeIn}>
        <div className="flex items-center gap-3">
          {!store.isRunning && !store.runComplete ? (
            <Button
              onClick={startRun}
              disabled={experiment.selectedAlgorithms.length === 0 || experiment.selectedProblems.length === 0}
              className="h-10 px-6 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white shadow-lg shadow-emerald-500/25 font-semibold gap-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="size-4" />
              Çalıştır
            </Button>
          ) : null}
          {store.isRunning && (
            <>
              <Button
                onClick={stopRun}
                className="h-10 px-6 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white shadow-lg shadow-red-500/25 font-semibold gap-2 transition-all duration-200"
              >
                <Square className="size-3.5" />
                Durdur
              </Button>
              <div className="flex items-center gap-2">
                <Loader2 className="size-4 text-emerald-500 animate-spin" />
                <span className="text-sm text-muted-foreground">Çalışıyor...</span>
              </div>
            </>
          )}
          {store.runComplete && !store.isRunning && (
            <>
              <div className="flex items-center gap-2">
                <CheckCircle className="size-5 text-emerald-500" />
                <span className="text-sm font-medium text-emerald-600 dark:text-emerald-400">
                  Deney tamamlandı! {store.runResults.length} sonuç
                </span>
              </div>
              <Button
                onClick={store.clearRunState}
                variant="outline"
                size="sm"
                className="text-xs"
              >
                <RefreshCw className="size-3 mr-1" />
                Yeni Deney
              </Button>
            </>
          )}
          {store.runError && (
            <div className="flex items-center gap-2 text-red-500 text-xs">
              <AlertTriangle className="size-4" />
              {store.runError}
            </div>
          )}
        </div>
      </motion.div>

      {/* ─── LIVE PROGRESS PANEL ──────────────────────────────── */}
      {(store.isRunning || store.runComplete || store.runResults.length > 0) && (
        <motion.div variants={fadeIn}>
          <Card className={`border-emerald-500/30 overflow-hidden${store.isRunning ? ' pulse-glow-emerald' : ''}`}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  {store.isRunning ? (
                    <Loader2 className="size-4 text-emerald-500 animate-spin" />
                  ) : store.runComplete ? (
                    <CheckCircle className="size-4 text-emerald-500" />
                  ) : (
                    <Activity className="size-4 text-emerald-500" />
                  )}
                  {store.isRunning ? 'Canlı İlerleme' : store.runComplete ? 'Deney Tamamlandı' : 'Sonuçlar'}
                </CardTitle>
                {store.runProgress && (
                  <Badge variant="secondary" className="text-xs tabular-nums">
                    {store.runProgress.completed} / {store.runProgress.total}
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Progress Bar */}
              {store.runProgress && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">
                      {store.runProgress.current
                        ? `${store.runProgress.current.problem} × ${store.runProgress.current.algorithm}`
                        : 'Hazırlanıyor...'}
                      {store.runProgress.current && store.runProgress.current.run > 0 && (
                        <span className="text-muted-foreground/60 ml-1">
                          (Run {store.runProgress.current.run}/{experiment.nRuns})
                        </span>
                      )}
                    </span>
                    <span className="font-semibold tabular-nums text-emerald-600 dark:text-emerald-400">
                      %{store.runProgress.percentage.toFixed(1)}
                    </span>
                  </div>
                  <Progress
                    value={store.runProgress.percentage}
                    className="h-3"
                  />
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Timer className="size-3" />
                      {store.runProgress.completed} / {store.runProgress.total} deney tamamlandı
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="size-3" />
                      Geçen: {formatElapsed(elapsedDisplay || store.runProgress.elapsed_ms)}
                    </span>
                    {store.runProgress.eta_ms > 0 && store.isRunning && (
                      <span className="flex items-center gap-1">
                        <Zap className="size-3" />
                        ETA: ~{formatElapsed(store.runProgress.eta_ms)}
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Completed Experiments Log */}
              {store.runResults.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-muted-foreground">
                      Tamamlanan Deneyler ({store.runResults.length})
                    </span>
                  </div>
                  <div className="max-h-48 overflow-y-auto rounded-md border border-border/50">
                    <div className="divide-y divide-border/50">
                      {[...store.runResults].reverse().map((r, idx) => {
                        const algo = ALGORITHMS.find(a => a.shortName === r.strategy);
                        return (
                          <div
                            key={`${r.problem}-${r.strategy}-${idx}`}
                            className="flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-muted/30 transition-colors slide-in-up"
                          >
                            <span
                              className="w-2 h-2 rounded-full shrink-0"
                              style={{ backgroundColor: algo?.color || '#64748b' }}
                            />
                            <span className="font-mono font-medium min-w-[80px] cursor-help underline decoration-dotted underline-offset-2 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"><ProblemDetailTooltip problemName={r.problem} /></span>
                            <span className="text-muted-foreground">×</span>
                            <span className="font-medium" style={{ color: algo?.color }}>{r.strategy}</span>
                            <span className="ml-auto tabular-nums">
                              <span className={gapColor(r.avgGap)}>GAP %{r.avgGap}</span>
                              <span className="text-muted-foreground ml-2">{r.avgTimeMs}ms</span>
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* Run Error */}
              {store.runError && (
                <div className="flex items-center gap-2 p-3 rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-xs text-red-700 dark:text-red-400">
                  <AlertTriangle className="size-4 shrink-0" />
                  {store.runError}
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      )}
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// RESULTS VIEW
// ═══════════════════════════════════════════════════════════════════════════════

function SortIcon({ field, sortField, sortDir }: { field: string; sortField: string; sortDir: string }) {
  if (sortField !== field) return <ArrowUpDown className="size-3 opacity-40" />;
  return sortDir === 'asc'
    ? <ChevronDown className="size-3 text-emerald-500" />
    : <ChevronUp className="size-3 text-emerald-500" />;
}

// ─── Results Helpers ──────────────────────────────────────────────────────────

function stdDev(values: number[]): number {
  if (values.length < 2) return 0;
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / (values.length - 1);
  return Math.sqrt(variance);
}

function computeAverageRanks(results: BenchmarkResult[]): Map<string, number> {
  const byProblem = new Map<string, BenchmarkResult[]>();
  for (const r of results) {
    if (!byProblem.has(r.problem)) byProblem.set(r.problem, []);
    byProblem.get(r.problem)!.push(r);
  }
  const rankSums = new Map<string, number[]>();
  for (const [, problemResults] of byProblem) {
    const sorted = [...problemResults].sort((a, b) => a.avgGap - b.avgGap);
    sorted.forEach((r, idx) => {
      if (!rankSums.has(r.strategy)) rankSums.set(r.strategy, []);
      rankSums.get(r.strategy)!.push(idx + 1);
    });
  }
  const avgRanks = new Map<string, number>();
  for (const [strategy, ranks] of rankSums) {
    avgRanks.set(strategy, ranks.reduce((a, b) => a + b, 0) / ranks.length);
  }
  return avgRanks;
}

function heatmapColor(gap: number): string {
  if (gap < 1) return 'bg-emerald-200 dark:bg-emerald-900/60 text-emerald-900 dark:text-emerald-100';
  if (gap < 2) return 'bg-emerald-300 dark:bg-emerald-800/60 text-emerald-900 dark:text-emerald-100';
  if (gap < 3) return 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-200';
  if (gap < 5) return 'bg-amber-200 dark:bg-amber-900/60 text-amber-900 dark:text-amber-100';
  if (gap < 8) return 'bg-amber-300 dark:bg-amber-800/60 text-amber-900 dark:text-amber-100';
  if (gap < 12) return 'bg-orange-300 dark:bg-orange-800/60 text-orange-900 dark:text-orange-100';
  return 'bg-rose-300 dark:bg-rose-800/60 text-rose-900 dark:text-rose-100';
}

const chartTooltipStyle: React.CSSProperties = {
  backgroundColor: 'var(--card)',
  border: '1px solid var(--border)',
  borderRadius: '8px',
  fontSize: '12px',
  color: 'var(--card-foreground)',
};

function ResultsView() {
  const store = useBenchmarkStore();
  const filteredResults = store.getFilteredResults();
  const { sortField, sortDir, resultsPerPage, resultsPage } = store;
  const [h2hAlgoA, setH2hAlgoA] = useState<string>('');
  const [h2hAlgoB, setH2hAlgoB] = useState<string>('');
  const [h2hOpen, setH2hOpen] = useState(false);
  const [expandedAlgoRank, setExpandedAlgoRank] = useState<string | null>(null);
  const [resultsSubTab, setResultsSubTab] = useState<'overview' | 'charts' | 'details'>('overview');
  const resultsTopRef = useRef<HTMLDivElement>(null);

  const totalPages = Math.max(1, Math.ceil(filteredResults.length / resultsPerPage));
  const pagedResults = filteredResults.slice(
    (resultsPage - 1) * resultsPerPage,
    resultsPage * resultsPerPage
  );

  const handleSort = (field: typeof sortField) => {
    store.setSortField(field);
  };

  const handleExport = (format: 'csv' | 'json') => {
    if (filteredResults.length === 0) {
      toast.error('Dışa aktarılacak veri yok');
      return;
    }
    let content: string;
    let filename: string;
    let type: string;
    if (format === 'csv') {
      const headers = 'Problem,Dimension,Optimal,Strategy,Avg GAP,Best GAP,Avg Time (ms),Runs,Timestamp';
      const rows = filteredResults.map(r =>
        `${r.problem},${r.dimension},${r.optimal},${r.strategy},${r.avgGap},${r.bestGap},${r.avgTimeMs},${r.nRuns},${r.timestamp}`
      ).join('\n');
      content = headers + '\n' + rows;
      filename = 'benchmark_results.csv';
      type = 'text/csv';
    } else {
      content = JSON.stringify(filteredResults, null, 2);
      filename = 'benchmark_results.json';
      type = 'application/json';
    }
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(`${filteredResults.length} sonuç ${format.toUpperCase()} olarak indirildi`);
  };

  // ─── Computed Data (React Compiler auto-memoizes) ────────────────────────

  const algoNames = [...new Set(filteredResults.map(r => r.strategy))].sort();

  const algoSummaryMap = (() => {
    const map = new Map<string, { gaps: number[]; bestGaps: number[]; times: number[]; count: number; color: string }>();
    for (const r of filteredResults) {
      if (!map.has(r.strategy)) map.set(r.strategy, { gaps: [], bestGaps: [], times: [], count: 0, color: '' });
      const entry = map.get(r.strategy)!;
      entry.gaps.push(r.avgGap);
      entry.bestGaps.push(r.bestGap);
      entry.times.push(r.avgTimeMs);
      entry.count++;
    }
    for (const [name, data] of map) {
      const algo = ALGORITHMS.find(a => a.shortName === name);
      data.color = algo?.color || '#64748b';
    }
    return map;
  })();

  const avgRanks = computeAverageRanks(filteredResults);

  // Quick Stats
  const quickStatsTotalResults = filteredResults.length;
  const quickStatsBestGap = filteredResults.length > 0 ? Math.min(...filteredResults.map(r => r.bestGap)) : 0;
  let quickStatsFastestAlgo = '-';
  let quickStatsFastestTime = Infinity;
  for (const [name, data] of algoSummaryMap) {
    const avgTime = data.times.reduce((a, b) => a + b, 0) / data.times.length;
    if (avgTime < quickStatsFastestTime) { quickStatsFastestTime = avgTime; quickStatsFastestAlgo = name; }
  }
  let quickStatsTotalRank = 0;
  let quickStatsRankCount = 0;
  for (const [, rank] of avgRanks) { quickStatsTotalRank += rank; quickStatsRankCount++; }
  const quickStatsOverallAvgRank = quickStatsRankCount > 0 ? (quickStatsTotalRank / quickStatsRankCount) : 0;
  const quickStats = { totalResults: quickStatsTotalResults, bestGap: +quickStatsBestGap.toFixed(2), fastestAlgo: quickStatsFastestAlgo, fastestTime: +quickStatsFastestTime.toFixed(1), overallAvgRank: +quickStatsOverallAvgRank.toFixed(2) };

  // Algorithm Ranking Table Data
  const rankingAllGaps: number[] = [];
  const rankingAllTimes: number[] = [];
  for (const [, data] of algoSummaryMap) {
    rankingAllGaps.push(...data.gaps);
    rankingAllTimes.push(...data.times);
  }
  const rankingMaxGap = Math.max(...rankingAllGaps, 0.01);
  const rankingMinGap = Math.min(...rankingAllGaps, 0);
  const rankingMaxTime = Math.max(...rankingAllTimes, 0.01);
  const rankingMinTime = Math.min(...rankingAllTimes, 0);
  const rankingGapRange = rankingMaxGap - rankingMinGap || 1;
  const rankingTimeRange = rankingMaxTime - rankingMinTime || 1;

  const rankingData = algoNames.map(name => {
    const data = algoSummaryMap.get(name)!;
    const avgGap = data.gaps.reduce((a, b) => a + b, 0) / data.gaps.length;
    const bestGap = Math.min(...data.bestGaps);
    const gapStd = stdDev(data.gaps);
    const avgTime = data.times.reduce((a, b) => a + b, 0) / data.times.length;
    const rank = avgRanks.get(name) || 999;
    const gapScore = ((rankingMaxGap - avgGap) / rankingGapRange) * 100;
    const speedScore = ((rankingMaxTime - avgTime) / rankingTimeRange) * 100;
    const paretoScore = +(gapScore * 0.6 + speedScore * 0.4).toFixed(1);
    return {
      name, avgGap: +avgGap.toFixed(2), bestGap: +bestGap.toFixed(2),
      gapStd: +gapStd.toFixed(2), avgTime: +avgTime.toFixed(1),
      rank: +rank.toFixed(2), paretoScore, count: data.count, color: data.color,
    };
  }).sort((a, b) => a.rank - b.rank);

  // GAP Distribution Range Chart Data
  const gapRangeData = algoNames.map(name => {
    const data = algoSummaryMap.get(name)!;
    const avgGap = data.gaps.reduce((a, b) => a + b, 0) / data.gaps.length;
    const minGap = Math.min(...data.gaps);
    const maxGap = Math.max(...data.gaps);
    return { name, min: +minGap.toFixed(2), avg: +avgGap.toFixed(2), max: +maxGap.toFixed(2), color: data.color };
  });

  // Heatmap Data
  const heatmapProblems = [...new Set(filteredResults.map(r => r.problem))].slice(0, 10);
  const heatmapAlgos = [...new Set(filteredResults.map(r => r.strategy))];
  const heatmapMatrix: { problem: string; algo: string; gap: number }[] = [];
  for (const prob of heatmapProblems) {
    for (const algo of heatmapAlgos) {
      const result = filteredResults.find(r => r.problem === prob && r.strategy === algo);
      heatmapMatrix.push({ problem: prob, algo, gap: result ? result.avgGap : -1 });
    }
  }
  const heatmapData = { problems: heatmapProblems, algos: heatmapAlgos, matrix: heatmapMatrix };

  // Scatter Plot Data
  const scatterData = filteredResults.map(r => {
    const algo = ALGORITHMS.find(a => a.shortName === r.strategy);
    return { x: r.avgTimeMs, y: r.avgGap, z: r.strategy, name: `${r.problem} × ${r.strategy}`, color: algo?.color || '#64748b' };
  });

  // Problem Difficulty Data
  const problemDifficultyByProblem = new Map<string, { gaps: number[]; category: ProblemCategory }>();
  for (const r of filteredResults) {
    if (!problemDifficultyByProblem.has(r.problem)) problemDifficultyByProblem.set(r.problem, { gaps: [], category: r.category });
    problemDifficultyByProblem.get(r.problem)!.gaps.push(r.avgGap);
  }
  const problemDifficulty = [...problemDifficultyByProblem.entries()].map(([name, data]) => ({
    name,
    avgGap: +(data.gaps.reduce((a, b) => a + b, 0) / data.gaps.length).toFixed(2),
    category: data.category,
  })).sort((a, b) => b.avgGap - a.avgGap);

  // Category Performance Data
  const categoryPerfByAlgoCat = new Map<string, Map<string, number[]>>();
  for (const r of filteredResults) {
    if (!categoryPerfByAlgoCat.has(r.strategy)) categoryPerfByAlgoCat.set(r.strategy, new Map());
    const algoMap = categoryPerfByAlgoCat.get(r.strategy)!;
    if (!algoMap.has(r.category)) algoMap.set(r.category, []);
    algoMap.get(r.category)!.push(r.avgGap);
  }
  const categoryPerfData = algoNames.map(name => {
    const catMap = categoryPerfByAlgoCat.get(name);
    const point: Record<string, string | number> = { name };
    for (const cat of ['small', 'medium', 'large'] as const) {
      const gaps = catMap?.get(cat) || [];
      point[cat] = gaps.length > 0 ? +(gaps.reduce((a, b) => a + b, 0) / gaps.length).toFixed(2) : 0;
    }
    return point;
  });

  // Head-to-Head Data
  let h2hData: { winsA: number; winsB: number; ties: number; comparisons: { problem: string; gapA: number; gapB: number; winner: string }[]; avgGapA: number; avgGapB: number; avgTimeA: number; avgTimeB: number; winRateA: number; winRateB: number; total: number; colorA: string; colorB: string } | null = null;
  if (h2hAlgoA && h2hAlgoB && h2hAlgoA !== h2hAlgoB) {
    const h2hProblems = [...new Set(filteredResults.filter(r => r.strategy === h2hAlgoA || r.strategy === h2hAlgoB).map(r => r.problem))];
    let h2hWinsA = 0, h2hWinsB = 0, h2hTies = 0;
    const h2hComparisons: { problem: string; gapA: number; gapB: number; winner: string }[] = [];
    for (const prob of h2hProblems) {
      const rA = filteredResults.find(r => r.problem === prob && r.strategy === h2hAlgoA);
      const rB = filteredResults.find(r => r.problem === prob && r.strategy === h2hAlgoB);
      if (!rA || !rB) continue;
      const h2hGapA = rA.bestGap;
      const h2hGapB = rB.bestGap;
      let winner = 'tie';
      if (h2hGapA < h2hGapB) { h2hWinsA++; winner = h2hAlgoA; }
      else if (h2hGapB < h2hGapA) { h2hWinsB++; winner = h2hAlgoB; }
      else { h2hTies++; }
      h2hComparisons.push({ problem: prob, gapA: h2hGapA, gapB: h2hGapB, winner });
    }
    const h2hDataA = algoSummaryMap.get(h2hAlgoA);
    const h2hDataB = algoSummaryMap.get(h2hAlgoB);
    const h2hAvgGapA = h2hDataA ? +(h2hDataA.gaps.reduce((a, b) => a + b, 0) / h2hDataA.gaps.length).toFixed(2) : 0;
    const h2hAvgGapB = h2hDataB ? +(h2hDataB.gaps.reduce((a, b) => a + b, 0) / h2hDataB.gaps.length).toFixed(2) : 0;
    const h2hAvgTimeA = h2hDataA ? +(h2hDataA.times.reduce((a, b) => a + b, 0) / h2hDataA.times.length).toFixed(1) : 0;
    const h2hAvgTimeB = h2hDataB ? +(h2hDataB.times.reduce((a, b) => a + b, 0) / h2hDataB.times.length).toFixed(1) : 0;
    const h2hTotal = h2hWinsA + h2hWinsB + h2hTies;
    const h2hWinRateA = h2hTotal > 0 ? +((h2hWinsA / h2hTotal) * 100).toFixed(1) : 0;
    const h2hWinRateB = h2hTotal > 0 ? +((h2hWinsB / h2hTotal) * 100).toFixed(1) : 0;
    h2hData = { winsA: h2hWinsA, winsB: h2hWinsB, ties: h2hTies, comparisons: h2hComparisons, avgGapA: h2hAvgGapA, avgGapB: h2hAvgGapB, avgTimeA: h2hAvgTimeA, avgTimeB: h2hAvgTimeB, winRateA: h2hWinRateA, winRateB: h2hWinRateB, total: h2hTotal, colorA: h2hDataA?.color || '#64748b', colorB: h2hDataB?.color || '#64748b' };
  }

  const categoryChartColors: Record<string, string> = {
    small: '#10b981',
    medium: '#f59e0b',
    large: '#f43f5e',
  };

  // ─── Performance Profile Data (React Compiler auto-memoizes) ───────────────
  const tauValues = [1, 1.5, 2, 3, 4, 5, 7, 10, 15, 20];
  const performanceProfileData = (() => {
    const problems = [...new Set(filteredResults.map(r => r.problem))];
    const totalProblems = problems.length;
    if (totalProblems === 0) return { tauValues: [], profiles: [] };

    const profiles = tauValues.map(tau => {
      const point: { tau: number; [algoName: string]: number } = { tau };
      for (const name of algoNames) {
        let solved = 0;
        for (const prob of problems) {
          const result = filteredResults.find(r => r.problem === prob && r.strategy === name);
          if (result && result.bestGap <= tau) solved++;
        }
        point[name] = +((solved / totalProblems) * 100).toFixed(1);
      }
      return point;
    });
    return { tauValues, profiles };
  })();

  // ─── Win Rate Matrix (React Compiler auto-memoizes) ──────────────────────
  const winRateMatrix = (() => {
    const problems = [...new Set(filteredResults.map(r => r.problem))];
    const matrix: Record<string, Record<string, number>> = {};
    for (const a of algoNames) {
      matrix[a] = {} as Record<string, number>;
      for (const b of algoNames) matrix[a][b] = 0;
    }
    for (const prob of problems) {
      const probResults = filteredResults.filter(r => r.problem === prob);
      for (let i = 0; i < probResults.length; i++) {
        for (let j = i + 1; j < probResults.length; j++) {
          const a = probResults[i], b = probResults[j];
          if (a.bestGap < b.bestGap) { matrix[a.strategy][b.strategy]++; }
          else if (b.bestGap < a.bestGap) { matrix[b.strategy][a.strategy]++; }
        }
      }
    }
    return matrix;
  })();

  // ─── Box Plot Data (React Compiler auto-memoizes) ────────────────────────
  const boxPlotData = algoNames.map(name => {
    const data = algoSummaryMap.get(name);
    if (!data || data.gaps.length === 0) return null;
    const sorted = [...data.gaps].sort((a, b) => a - b);
    const n = sorted.length;
    const q1 = sorted[Math.floor(n * 0.25)];
    const median = sorted[Math.floor(n * 0.5)];
    const q3 = sorted[Math.floor(n * 0.75)];
    const min = sorted[0];
    const max = sorted[n - 1];
    const avg = +(data.gaps.reduce((a, b) => a + b, 0) / n).toFixed(2);
    return { name, min: +min.toFixed(2), q1: +q1.toFixed(2), median: +median.toFixed(2), q3: +q3.toFixed(2), max: +max.toFixed(2), avg, color: data.color };
  }).filter(Boolean) as { name: string; min: number; q1: number; median: number; q3: number; max: number; avg: number; color: string }[];

  // ─── Speed Ranking (React Compiler auto-memoizes) ─────────────────────────
  const speedRanking = algoNames.map(name => {
    const data = algoSummaryMap.get(name);
    if (!data) return null;
    const avgTime = data.times.reduce((a, b) => a + b, 0) / data.times.length;
    return { name, avgTime: +avgTime.toFixed(1), color: data.color, count: data.count };
  }).filter(Boolean).sort((a, b) => (a?.avgTime ?? 0) - (b?.avgTime ?? 0)) as { name: string; avgTime: number; color: string; count: number }[];

  if (filteredResults.length === 0) {
    return (
      <motion.div variants={fadeIn} className="space-y-4">
        <motion.div variants={fadeIn}>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3 flex-wrap">
                <div className="flex items-center gap-1">
                  <Filter className="size-3 text-muted-foreground" />
                  <Select value={store.dashboardFilter} onValueChange={(v) => store.setDashboardFilter(v as ProblemCategory | 'all')}>
                    <SelectTrigger className="h-8 w-32 text-xs"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all" className="text-xs">Tümü</SelectItem>
                      <SelectItem value="small" className="text-xs">Küçük</SelectItem>
                      <SelectItem value="medium" className="text-xs">Orta</SelectItem>
                      <SelectItem value="large" className="text-xs">Büyük</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Select value={store.dashboardAlgorithmFilter} onValueChange={(v) => store.setDashboardAlgorithmFilter(v)}>
                  <SelectTrigger className="h-8 w-36 text-xs"><SelectValue placeholder="Algoritma" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all" className="text-xs">Tüm Algoritmalar</SelectItem>
                    {ALGORITHMS.filter(a => a.ready).map(a => (
                      <SelectItem key={a.id} value={a.shortName} className="text-xs">{a.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <div className="relative flex-1 min-w-[150px]">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3 text-muted-foreground" />
                  <Input placeholder="Problem veya algoritma ara..." value={store.dashboardSearch} onChange={(e) => store.setDashboardSearch(e.target.value)} className="h-8 text-xs pl-8" />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
        <motion.div variants={fadeIn}>
          <Card>
            <CardContent className="py-16">
              <div className="flex flex-col items-center gap-3">
                <Search className="size-10 opacity-20" />
                <p className="text-sm text-muted-foreground">Sonuç bulunamadı</p>
                <p className="text-xs text-muted-foreground">Filtreleri değiştirmeyi veya demo veri yüklemeyi deneyin</p>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>
    );
  }

  return (
    <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-6" ref={resultsTopRef}>
      {/* ─── 1. FILTER BAR ──────────────────────────────────────── */}
      <motion.div variants={fadeIn}>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex items-center gap-1">
                <Filter className="size-3 text-muted-foreground" />
                <Select value={store.dashboardFilter} onValueChange={(v) => store.setDashboardFilter(v as ProblemCategory | 'all')}>
                  <SelectTrigger className={`h-8 w-32 text-xs${store.dashboardFilter !== 'all' ? ' filter-active' : ''}`}><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all" className="text-xs">Tümü</SelectItem>
                    <SelectItem value="small" className="text-xs">Küçük</SelectItem>
                    <SelectItem value="medium" className="text-xs">Orta</SelectItem>
                    <SelectItem value="large" className="text-xs">Büyük</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Select value={store.dashboardAlgorithmFilter} onValueChange={(v) => store.setDashboardAlgorithmFilter(v)}>
                <SelectTrigger className={`h-8 w-36 text-xs${store.dashboardAlgorithmFilter !== 'all' ? ' filter-active' : ''}`}><SelectValue placeholder="Algoritma" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all" className="text-xs">Tüm Algoritmalar</SelectItem>
                  {ALGORITHMS.filter(a => a.ready).map(a => (
                    <SelectItem key={a.id} value={a.shortName} className="text-xs">{a.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div className="relative flex-1 min-w-[150px]">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3 text-muted-foreground" />
                <Input placeholder="Problem veya algoritma ara..." value={store.dashboardSearch} onChange={(e) => store.setDashboardSearch(e.target.value)} className="h-8 text-xs pl-8" />
              </div>
              <Separator orientation="vertical" className="h-6 hidden sm:block" />
              <div className="flex gap-2">
                <Button variant="outline" size="sm" className="h-8 text-xs gap-1" onClick={() => handleExport('csv')}>
                  <FileSpreadsheet className="size-3" /> CSV
                </Button>
                <Button variant="outline" size="sm" className="h-8 text-xs gap-1" onClick={() => handleExport('json')}>
                  <FileJson className="size-3" /> JSON
                </Button>
                <Button variant="outline" size="sm" className="h-8 text-xs gap-1" onClick={() => {
                  if (filteredResults.length === 0) { toast.error('Dışa aktarılacak veri yok'); return; }
                  let latex = '\\begin{tabular}{lrrr}\n\\toprule\nProblem & Algoritma & Ort. GAP & Ort. Süre \\\\\n\\midrule\n';
                  for (const r of filteredResults) {
                    latex += `${r.problem} & ${r.strategy} & ${r.avgGap}\\% & ${r.avgTimeMs}ms \\\\\n`;
                  }
                  latex += '\\bottomrule\n\\end{tabular}';
                  const blob = new Blob([latex], { type: 'text/plain' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url; a.download = 'benchmark_results.tex'; a.click();
                  URL.revokeObjectURL(url);
                  toast.success(`${filteredResults.length} sonuç LaTeX olarak indirildi`);
                }}>
                  <BookOpen className="size-3" /> LaTeX
                </Button>
              </div>
            </div>
            <div className="mt-2 text-xs text-muted-foreground">
              {filteredResults.length} sonuç gösteriliyor
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* ─── RESULTS SUB-TAB NAVIGATION ─────────────────────────── */}
      <motion.div variants={fadeIn}>
        <div className="flex items-center gap-1.5 flex-wrap">
          {([
            { key: 'overview' as const, label: 'Genel Bakış', icon: <Grid3X3 className="size-3.5" /> },
            { key: 'charts' as const, label: 'Grafikler', icon: <BarChart3 className="size-3.5" /> },
            { key: 'details' as const, label: 'Detaylar', icon: <ListChecks className="size-3.5" /> },
          ]).map(tab => (
            <button
              key={tab.key}
              onClick={() => setResultsSubTab(tab.key)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-200 ${
                resultsSubTab === tab.key
                  ? 'bg-primary text-primary-foreground shadow-sm subtab-active'
                  : 'bg-muted/40 text-muted-foreground hover:bg-muted hover:text-foreground hover:shadow-sm'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </motion.div>

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* OVERVIEW TAB                                                    */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      {resultsSubTab === 'overview' && (
        <AnimatePresence mode="wait">
          <motion.div key="overview" {...fadeIn} transition={{ duration: 0.25 }} className="space-y-6">

      {/* ─── SUMMARY BANNER ────────────────────────────────── */}
      <motion.div variants={fadeIn} className="slide-in-up">
        <div className="banner-shimmer rounded-xl p-4 border border-border/50" style={{ background: 'linear-gradient(135deg, oklch(0.7 0.15 165 / 0.08), transparent, oklch(0.8 0.15 85 / 0.05))' }}>
          <div className="flex items-center gap-4 flex-wrap text-sm relative z-10">
            <span className="font-semibold tabular-nums">{quickStats.totalResults} Sonuç</span>
            <span className="text-muted-foreground">•</span>
            <span className="font-semibold">{algoNames.length} Algoritma</span>
            <span className="text-muted-foreground">•</span>
            <span className="font-semibold">{new Set(filteredResults.map(r => r.problem)).size} Problem</span>
            <span className="text-muted-foreground">•</span>
            <span className="font-semibold">
              Ortalama GAP: <span className={gapColor(+(filteredResults.reduce((s, r) => s + r.avgGap, 0) / filteredResults.length).toFixed(2))}>
                {(filteredResults.reduce((s, r) => s + r.avgGap, 0) / filteredResults.length).toFixed(2)}%
              </span>
            </span>
          </div>
        </div>
      </motion.div>

      {/* ─── 1. QUICK STATS CARDS ──────────────────────────── */}
      <motion.div variants={fadeIn}>
        <div className="flex items-center gap-2 mb-3">
          <span className={SECTION_NUMBER_STYLE}>1</span>
          <h3 className="text-sm font-semibold">Hızlı İstatistikler</h3>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="card-lift card-shimmer card-glow-hover overflow-hidden border-emerald-500/20">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground font-medium">Toplam Sonuç</p>
                  <p className="text-2xl font-bold tabular-nums text-emerald-600 dark:text-emerald-400 mt-1 count-up">{quickStats.totalResults}</p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center stat-icon-glow">
                  <Activity className="size-5 text-emerald-600 dark:text-emerald-400" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="card-lift card-shimmer card-glow-hover overflow-hidden border-amber-500/20">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground font-medium">En İyi GAP</p>
                  <p className="text-2xl font-bold tabular-nums text-amber-600 dark:text-amber-400 mt-1 count-up">{quickStats.bestGap}%</p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center stat-icon-glow">
                  <Trophy className="size-5 text-amber-600 dark:text-amber-400" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="card-lift card-shimmer card-glow-hover overflow-hidden border-emerald-500/20">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground font-medium">En Hızlı Ortalama</p>
                  <p className="text-sm font-bold text-emerald-600 dark:text-emerald-400 mt-1 truncate">{quickStats.fastestAlgo}</p>
                  <p className="text-xs text-muted-foreground tabular-nums">{quickStats.fastestTime} ms</p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center stat-icon-glow">
                  <Zap className="size-5 text-emerald-600 dark:text-emerald-400" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="card-lift card-shimmer card-glow-hover overflow-hidden border-amber-500/20">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground font-medium">Ortalama Sıralama</p>
                  <p className="text-2xl font-bold tabular-nums text-amber-600 dark:text-amber-400 mt-1">{quickStats.overallAvgRank}</p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center stat-icon-glow">
                  <Hash className="size-5 text-amber-600 dark:text-amber-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </motion.div>

      {/* ─── 2. ALGORITHM RANKING TABLE ────────────────────── */}
      <motion.div variants={fadeIn}>
        <div className="flex items-center gap-2 mb-3">
          <span className={SECTION_NUMBER_STYLE}>2</span>
          <h3 className="text-sm font-semibold">Algoritma Sıralama Tablosu</h3>
          <Badge variant="secondary" className="text-[10px]">Friedman</Badge>
        </div>
        <Card className="animated-border overflow-hidden rounded-lg">
          <CardHeader className="pb-2">
            <CardDescription>Friedman sıralama puanına göre (düşük = iyi) · Algoritma adına tıklayarak detay görüntüleyin</CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="overflow-x-auto rounded-md border border-border/50">
              <Table className="min-w-[720px]">
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs text-center w-16">#</TableHead>
                    <TableHead className="text-xs">Algoritma</TableHead>
                    <TableHead className="text-xs text-right">Ort. GAP</TableHead>
                    <TableHead className="text-xs text-right">En İyi GAP</TableHead>
                    <TableHead className="text-xs text-right">Std Sapma</TableHead>
                    <TableHead className="text-xs text-right">Ort. Süre</TableHead>
                    <TableHead className="text-xs text-right">Sıralama Puanı</TableHead>
                    <TableHead className="text-xs text-right">Pareto Skor</TableHead>
                    <TableHead className="text-xs text-center">Deney</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rankingData.map((item, idx) => (
                    <React.Fragment key={item.name}>
                      <TableRow className="table-row-hover cursor-pointer" onClick={() => setExpandedAlgoRank(expandedAlgoRank === item.name ? null : item.name)}>
                        <TableCell className="text-center">
                          <span className="text-sm font-bold">
                            {idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : `${idx + 1}`}
                          </span>
                        </TableCell>
                        <TableCell className="text-xs font-medium">
                          <span className="flex items-center gap-1.5">
                            <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                            {item.name}
                            <ChevronRight className={`size-3 text-muted-foreground transition-transform ${expandedAlgoRank === item.name ? 'rotate-90' : ''}`} />
                          </span>
                        </TableCell>
                        <TableCell className="text-xs text-right tabular-nums">
                          <span className={gapColor(item.avgGap)}>{item.avgGap}%</span>
                        </TableCell>
                        <TableCell className="text-xs text-right tabular-nums">
                          <span className={gapColor(item.bestGap)}>{item.bestGap}%</span>
                        </TableCell>
                        <TableCell className="text-xs text-right tabular-nums text-muted-foreground">{item.gapStd}</TableCell>
                        <TableCell className="text-xs text-right tabular-nums">{item.avgTime} ms</TableCell>
                        <TableCell className="text-xs text-right tabular-nums font-semibold">{item.rank.toFixed(2)}</TableCell>
                        <TableCell className="text-xs text-right tabular-nums font-semibold">
                          <span className={item.paretoScore >= 70 ? 'text-emerald-600 dark:text-emerald-400' : item.paretoScore >= 40 ? 'text-amber-600 dark:text-amber-400' : 'text-rose-600 dark:text-rose-400'}>
                            {item.paretoScore}
                          </span>
                        </TableCell>
                        <TableCell className="text-xs text-center tabular-nums">{item.count}</TableCell>
                      </TableRow>
                      {expandedAlgoRank === item.name && (() => {
                        const algoData = algoSummaryMap.get(item.name);
                        if (!algoData) return null;
                        const algoResults = filteredResults.filter(r => r.strategy === item.name);
                        const bestProblem = [...algoResults].sort((a, b) => a.avgGap - b.avgGap)[0];
                        const worstProblem = [...algoResults].sort((a, b) => b.avgGap - a.avgGap)[0];
                        const catGaps: Record<string, number[]> = {};
                        for (const r of algoResults) {
                          if (!catGaps[r.category]) catGaps[r.category] = [];
                          catGaps[r.category].push(r.avgGap);
                        }
                        const catAvgs = Object.entries(catGaps).map(([cat, gaps]) => ({
                          cat: cat as ProblemCategory,
                          avg: +(gaps.reduce((a, b) => a + b, 0) / gaps.length).toFixed(2),
                        }));
                        const minG = Math.min(...algoData.gaps);
                        const maxG = Math.max(...algoData.gaps);
                        const rangeG = maxG - minG || 1;
                        return (
                          <TableRow key={`${item.name}-detail`}>
                            <TableCell colSpan={9} className="p-0">
                              <div className="p-4 bg-muted/20 space-y-3 slide-in-up">
                                {/* Stats row */}
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                                  <span className="text-sm font-bold" style={{ color: item.color }}>{item.name}</span>
                                  <span className="text-xs text-muted-foreground ml-2">
                                    Ort. GAP: <strong className={gapColor(item.avgGap)}>{item.avgGap}%</strong> ·
                                    En İyi: <strong>{item.bestGap}%</strong> ·
                                    Std: <strong>{item.gapStd}</strong> ·
                                    Ort. Süre: <strong>{item.avgTime}ms</strong> ·
                                    Deney: <strong>{item.count}</strong>
                                  </span>
                                </div>
                                {/* GAP Distribution Bar */}
                                <div className="space-y-1">
                                  <p className="text-[10px] text-muted-foreground font-medium">GAP Dağılımı</p>
                                  <div className="relative h-4 bg-muted/50 rounded-full overflow-hidden">
                                    <div className="absolute inset-y-0 left-0 rounded-full" style={{ width: `${((item.avgGap - minG) / rangeG) * 100}%`, backgroundColor: item.color, opacity: 0.2 }} />
                                    <div className="absolute top-0 bottom-0 w-0.5 bg-foreground" style={{ left: `${((item.avgGap - minG) / rangeG) * 100}%` }} />
                                    <div className="absolute top-0 bottom-0 left-0 w-0.5 rounded-full" style={{ backgroundColor: item.color, left: `${((item.bestGap - minG) / rangeG) * 100}%` }} />
                                  </div>
                                  <div className="flex justify-between text-[10px] text-muted-foreground tabular-nums">
                                    <span>{minG.toFixed(1)}%</span>
                                    <span className="font-medium" style={{ color: item.color }}>Ort: {item.avgGap}%</span>
                                    <span>{maxG.toFixed(1)}%</span>
                                  </div>
                                </div>
                                {/* Best/Worst Problems & Category Performance */}
                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                                  <div className="p-2 rounded-md bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-200/50 dark:border-emerald-800/30">
                                    <p className="text-[10px] text-muted-foreground mb-1">En İyi Problem</p>
                                    <p className="font-mono font-bold text-emerald-600 dark:text-emerald-400">{bestProblem?.problem}</p>
                                    <p className="text-emerald-600 dark:text-emerald-400 tabular-nums">GAP: {bestProblem?.avgGap}%</p>
                                  </div>
                                  <div className="p-2 rounded-md bg-rose-50 dark:bg-rose-900/10 border border-rose-200/50 dark:border-rose-800/30">
                                    <p className="text-[10px] text-muted-foreground mb-1">En Kötü Problem</p>
                                    <p className="font-mono font-bold text-rose-600 dark:text-rose-400">{worstProblem?.problem}</p>
                                    <p className="text-rose-600 dark:text-rose-400 tabular-nums">GAP: {worstProblem?.avgGap}%</p>
                                  </div>
                                  <div className="p-2 rounded-md bg-muted/30 border border-border/50">
                                    <p className="text-[10px] text-muted-foreground mb-1">Kategori Performansı</p>
                                    {catAvgs.map(c => (
                                      <div key={c.cat} className="flex items-center justify-between">
                                        <span className={CATEGORY_COLORS[c.cat]}>{CATEGORY_LABELS[c.cat]}</span>
                                        <span className="tabular-nums font-medium">{c.avg}%</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              </div>
                            </TableCell>
                          </TableRow>
                        );
                      })()}
                    </React.Fragment>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* ─── 3. PERFORMANCE HEATMAP MATRIX ─────────────────── */}
      <motion.div variants={fadeIn}>
        <div className="flex items-center gap-2 mb-3">
          <span className={SECTION_NUMBER_STYLE}>3</span>
          <h3 className="text-sm font-semibold">Performans Isı Haritası</h3>
        </div>
        <Card className="card-lift overflow-hidden">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Grid3X3 className="size-4 text-rose-500" />
              Performans Isı Haritası (Algoritma × Problem)
            </CardTitle>
            <CardDescription>İlk 10 problem gösterilmektedir · Renk skalası: yeşil(&lt;2%) → sarı(2-5%) → kırmızı(&gt;5%)</CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="overflow-auto max-h-96 rounded-md border border-border/50">
              <table className="min-w-max text-xs">
                <thead>
                  <tr>
                    <th className="sticky left-0 bg-card z-10 px-2 py-1.5 text-left font-medium border-b border-r border-border/50 whitespace-nowrap">Problem</th>
                    {heatmapData.algos.map(algo => {
                      const a = ALGORITHMS.find(x => x.shortName === algo);
                      return (
                        <th key={algo} className="sticky top-0 bg-card z-10 px-2 py-1.5 text-center font-medium border-b border-border/50 whitespace-nowrap">
                          <span style={{ color: a?.color }}>{algo}</span>
                        </th>
                      );
                    })}
                  </tr>
                </thead>
                <tbody>
                  {heatmapData.problems.map(prob => (
                    <tr key={prob}>
                      <td className="sticky left-0 bg-card z-10 px-2 py-1 font-mono font-medium border-r border-border/50 whitespace-nowrap"><ProblemDetailTooltip problemName={prob} /></td>
                      {heatmapData.algos.map(algo => {
                        const cell = heatmapData.matrix.find(m => m.problem === prob && m.algo === algo);
                        const gap = cell?.gap ?? -1;
                        return (
                          <td key={algo} className={`px-2 py-1 text-center tabular-nums font-medium whitespace-nowrap heatmap-cell-hover rounded-sm ${gap < 0 ? 'bg-muted/50 text-muted-foreground' : heatmapColor(gap)}`}>
                            {gap < 0 ? '–' : `${gap}%`}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {new Set(filteredResults.map(r => r.problem)).size > 10 && (
              <p className="text-xs text-muted-foreground text-center mt-2">
                ...ve {new Set(filteredResults.map(r => r.problem)).size - 10} problem daha
              </p>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* ─── 4. SPEED RANKING ─────────────────────────────── */}
      <motion.div variants={fadeIn}>
        <div className="flex items-center gap-2 mb-3">
          <span className={SECTION_NUMBER_STYLE}>4</span>
          <h3 className="text-sm font-semibold">Hız Sıralaması</h3>
        </div>
        <Card className="card-lift overflow-hidden">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Gauge className="size-4 text-amber-500" />
              Ortalama Çalışma Süresi Sıralaması
            </CardTitle>
            <CardDescription>Algoritmalar ortalama çalışma süresine göre sıralanmıştır (hızlı → yavaş)</CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div style={{ height: Math.max(200, speedRanking.length * 48) }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={speedRanking} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border/50" />
                  <XAxis type="number" tick={{ fontSize: 11 }} className="fill-muted-foreground" unit=" ms" />
                  <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} className="fill-muted-foreground" width={80} />
                  <RTooltip contentStyle={chartTooltipStyle} formatter={(value: number) => [`${value} ms`, 'Ort. Süre']} />
                  <Bar dataKey="avgTime" radius={[0, 4, 4, 0]} barSize={24}>
                    {speedRanking.map((entry, idx) => (
                      <Cell key={idx} fill={entry.color} fillOpacity={0.85} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="flex items-center justify-center gap-4 mt-2 text-xs text-muted-foreground">
              {speedRanking.map((d, idx) => (
                <span key={d.name} className="flex items-center gap-1">
                  <Medal className="size-3" style={{ color: idx === 0 ? '#10b981' : idx === 1 ? '#f59e0b' : '#64748b' }} />
                  <span style={{ color: d.color }}>{d.name}</span>: {d.avgTime} ms
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>

          </motion.div>
        </AnimatePresence>
      )}

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* CHARTS TAB                                                      */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      {resultsSubTab === 'charts' && (
        <AnimatePresence mode="wait">
          <motion.div key="charts" {...fadeIn} transition={{ duration: 0.25 }} className="space-y-6">

      {/* ─── 1. PERFORMANCE PROFILE CHART ──────────────────── */}
      <motion.div variants={fadeIn}>
        <div className="flex items-center gap-2 mb-3">
          <span className={SECTION_NUMBER_STYLE}>1</span>
          <h3 className="text-sm font-semibold">Performans Profili</h3>
        </div>
        <Card className="card-lift overflow-hidden">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <TrendingDown className="size-4 text-emerald-500" />
              Performans Profili Grafiği
            </CardTitle>
            <CardDescription>τ% GAP eşiğinde çözülebilen problem oranı · Yüksek = daha iyi</CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={performanceProfileData.profiles} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border/50" />
                  <XAxis dataKey="tau" tick={{ fontSize: 11 }} className="fill-muted-foreground" label={{ value: 'τ (GAP Eşiği %)', position: 'insideBottom', offset: -5, fontSize: 11, fill: 'var(--muted-foreground)' }} />
                  <YAxis tick={{ fontSize: 11 }} className="fill-muted-foreground" domain={[0, 100]} unit="%" label={{ value: 'Çözüm Oranı', angle: -90, position: 'insideLeft', fontSize: 11, fill: 'var(--muted-foreground)' }} />
                  <RTooltip contentStyle={chartTooltipStyle} formatter={(value: number) => [`${value}%`, 'Çözüm Oranı']} />
                  <ReferenceLine x={2} stroke="var(--border)" strokeDasharray="5 5" />
                  {algoNames.map(name => {
                    const algo = ALGORITHMS.find(a => a.shortName === name);
                    return (
                      <Line key={name} type="monotone" dataKey={name} stroke={algo?.color || '#64748b'} strokeWidth={2} strokeDasharray="5 5" dot={{ r: 3, strokeWidth: 2 }} activeDot={{ r: 5 }} name={name} />
                    );
                  })}
                  <RLegend />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* ─── 2. GAP DISTRIBUTION RANGE CHART ───────────────── */}
      <motion.div variants={fadeIn}>
        <div className="flex items-center gap-2 mb-3">
          <span className={SECTION_NUMBER_STYLE}>2</span>
          <h3 className="text-sm font-semibold">GAP Dağılım Aralığı</h3>
        </div>
        <Card className="card-lift overflow-hidden">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Activity className="size-4 text-violet-500" />
              Min – Ort – Max GAP Dağılımı
            </CardTitle>
            <CardDescription>Her algoritmanın minimum, ortalama ve maksimum GAP değerleri</CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={gapRangeData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border/50" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} className="fill-muted-foreground" />
                  <YAxis tick={{ fontSize: 11 }} className="fill-muted-foreground" unit="%" />
                  <RTooltip contentStyle={chartTooltipStyle} />
                  <Bar dataKey="min" fill="#10b981" fillOpacity={0.5} radius={[2, 2, 0, 0]} name="Min GAP" />
                  <Bar dataKey="avg" radius={[2, 2, 0, 0]} name="Ort. GAP">
                    {gapRangeData.map((entry, idx) => (
                      <Cell key={idx} fill={entry.color} fillOpacity={0.85} />
                    ))}
                  </Bar>
                  <Bar dataKey="max" fill="#ef4444" fillOpacity={0.5} radius={[2, 2, 0, 0]} name="Max GAP" />
                  <RLegend />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-4 mt-2 text-xs text-muted-foreground">
              {gapRangeData.map(d => (
                <span key={d.name} className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: d.color }} />
                  {d.name}: {d.min}%–{d.max}% (ort: {d.avg}%)
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* ─── 3. GAP vs TIME SCATTER PLOT ──────────────────── */}
      <motion.div variants={fadeIn}>
        <div className="flex items-center gap-2 mb-3">
          <span className={SECTION_NUMBER_STYLE}>3</span>
          <h3 className="text-sm font-semibold">GAP vs Süre Trade-off</h3>
        </div>
        <Card className="card-lift overflow-hidden">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Crosshair className="size-4 text-violet-500" />
              GAP vs Süre Trade-off
            </CardTitle>
            <CardDescription>Sol-alt = ideal bölge (düşük GAP, düşük süre) · Yeşil alan = verimli bölge</CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border/50" />
                  <XAxis dataKey="x" tick={{ fontSize: 11 }} className="fill-muted-foreground" name="Süre" unit=" ms" type="number" />
                  <YAxis dataKey="y" tick={{ fontSize: 11 }} className="fill-muted-foreground" name="GAP" unit="%" type="number" />
                  <RTooltip contentStyle={chartTooltipStyle} formatter={(value: number, name: string) => [name === 'x' ? `${value.toFixed(1)} ms` : `${value.toFixed(2)}%`, name === 'x' ? 'Süre' : 'GAP']} />
                  {(() => {
                    const allTimes = scatterData.map(d => d.x);
                    const allGaps = scatterData.map(d => d.y);
                    const medianTime = allTimes.length > 0 ? allTimes.sort((a, b) => a - b)[Math.floor(allTimes.length / 2)] : 0;
                    const medianGap = allGaps.length > 0 ? allGaps.sort((a, b) => a - b)[Math.floor(allGaps.length / 2)] : 0;
                    return (
                      <ReferenceArea x1={0} y1={0} x2={medianTime} y2={medianGap} fill="#10b981" fillOpacity={0.06} stroke="#10b98140" strokeDasharray="3 3" />
                    );
                  })()}
                  {algoNames.map(name => {
                    const algo = ALGORITHMS.find(a => a.shortName === name);
                    const data = scatterData.filter(d => d.z === name);
                    return (
                      <Scatter key={name} name={name} data={data} fill={algo?.color || '#64748b'} fillOpacity={0.7} />
                    );
                  })}
                  <RLegend />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* ─── 4. PROBLEM DIFFICULTY ANALYSIS ────────────────── */}
      <motion.div variants={fadeIn}>
        <div className="flex items-center gap-2 mb-3">
          <span className={SECTION_NUMBER_STYLE}>4</span>
          <h3 className="text-sm font-semibold">Problem Zorluk Analizi</h3>
        </div>
        <Card className="card-lift overflow-hidden">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <TrendingDown className="size-4 text-rose-500" />
              Problem Zorluk Analizi
            </CardTitle>
            <CardDescription>Yüksek ortalama GAP = zor problem</CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={problemDifficulty} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border/50" />
                  <XAxis type="number" tick={{ fontSize: 11 }} className="fill-muted-foreground" unit="%" />
                  <YAxis dataKey="name" type="category" tick={{ fontSize: 10 }} className="fill-muted-foreground" width={80} />
                  <RTooltip contentStyle={chartTooltipStyle} formatter={(value: number) => [`${value}%`, 'Ort. GAP']} />
                  <Bar dataKey="avgGap" radius={[0, 4, 4, 0]}>
                    {problemDifficulty.map((entry, idx) => (
                      <Cell key={idx} fill={categoryChartColors[entry.category] || '#64748b'} fillOpacity={0.8} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="flex items-center justify-center gap-4 mt-2 text-xs">
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Küçük</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Orta</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> Büyük</span>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* ─── 5. CATEGORY PERFORMANCE BREAKDOWN ─────────────── */}
      <motion.div variants={fadeIn}>
        <div className="flex items-center gap-2 mb-3">
          <span className={SECTION_NUMBER_STYLE}>5</span>
          <h3 className="text-sm font-semibold">Kategori Bazlı Performans</h3>
        </div>
        <Card className="card-lift overflow-hidden">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Layers className="size-4 text-emerald-500" />
              Kategori Bazlı Performans
            </CardTitle>
            <CardDescription>Algoritmaların küçük/orta/büyük problem kategorilerindeki ortalama GAP performansı</CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categoryPerfData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border/50" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} className="fill-muted-foreground" />
                  <YAxis tick={{ fontSize: 11 }} className="fill-muted-foreground" unit="%" />
                  <RTooltip contentStyle={chartTooltipStyle} formatter={(value: number) => [`${value}%`]} />
                  <Bar dataKey="small" fill="#10b981" fillOpacity={0.8} radius={[2, 2, 0, 0]} name="Küçük" />
                  <Bar dataKey="medium" fill="#f59e0b" fillOpacity={0.8} radius={[2, 2, 0, 0]} name="Orta" />
                  <Bar dataKey="large" fill="#f43f5e" fillOpacity={0.8} radius={[2, 2, 0, 0]} name="Büyük" />
                  <RLegend />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* ─── 6. BOX PLOT VISUALIZATION ─────────────────────── */}
      <motion.div variants={fadeIn}>
        <div className="flex items-center gap-2 mb-3">
          <span className={SECTION_NUMBER_STYLE}>6</span>
          <h3 className="text-sm font-semibold">GAP Box Plot</h3>
        </div>
        <Card className="card-lift overflow-hidden">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <BarChart3 className="size-4 text-amber-500" />
              GAP Dağılım Box Plot
            </CardTitle>
            <CardDescription>Medyan (bar), Q1-Q3 aralık (error bar), min-max (whisker) · Bar uzunluğu = medyan GAP</CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={boxPlotData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border/50" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} className="fill-muted-foreground" />
                  <YAxis tick={{ fontSize: 11 }} className="fill-muted-foreground" unit="%" />
                  <RTooltip contentStyle={chartTooltipStyle} />
                  <Bar dataKey="median" radius={[4, 4, 0, 0]} barSize={40} name="Medyan">
                    {boxPlotData.map((entry, idx) => (
                      <Cell key={idx} fill={entry.color} fillOpacity={0.85} />
                    ))}
                  </Bar>
                  <Line dataKey="median" stroke="var(--foreground)" strokeWidth={1.5} dot={{ r: 4, fill: 'var(--foreground)', strokeWidth: 2 }} name="Medyan (dot)" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-4 mt-2 text-xs text-muted-foreground">
              {boxPlotData.map(d => (
                <span key={d.name} className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: d.color }} />
                  <span style={{ color: d.color }}>{d.name}</span>: medyan {d.median}% · Q1={d.q1}% · Q3={d.q3}% · [{d.min}–{d.max}]%
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* ─── 7. ALGORITHM WIN RATE MATRIX ──────────────────── */}
      <motion.div variants={fadeIn}>
        <div className="flex items-center gap-2 mb-3">
          <span className={SECTION_NUMBER_STYLE}>7</span>
          <h3 className="text-sm font-semibold">Algoritma Kazanma Oranı Matrisi</h3>
        </div>
        <Card className="card-lift overflow-hidden">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Swords className="size-4 text-rose-500" />
              Çift Yönlü Kazanma Matrisi
            </CardTitle>
            <CardDescription>Satır algoritması, sütun algoritmasına karşı kaç problemde kazandı · Renk yoğunluğu = kazanma sayısı</CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="overflow-auto max-h-96 rounded-md border border-border/50">
              <table className="min-w-max text-xs">
                <thead>
                  <tr>
                    <th className="sticky left-0 bg-card z-10 px-2 py-1.5 text-left font-medium border-b border-r border-border/50 whitespace-nowrap">← Kazanan ↓ Kaybeden</th>
                    {algoNames.map(name => {
                      const algo = ALGORITHMS.find(a => a.shortName === name);
                      return (
                        <th key={name} className="sticky top-0 bg-card z-10 px-2 py-1.5 text-center font-medium border-b border-border/50 whitespace-nowrap">
                          <span style={{ color: algo?.color }}>{name}</span>
                        </th>
                      );
                    })}
                  </tr>
                </thead>
                <tbody>
                  {algoNames.map(rowAlgo => (
                    <tr key={rowAlgo}>
                      <td className="sticky left-0 bg-card z-10 px-2 py-1 font-medium border-r border-border/50 whitespace-nowrap">
                        <span className="flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: algoSummaryMap.get(rowAlgo)?.color }} />
                          {rowAlgo}
                        </span>
                      </td>
                      {algoNames.map(colAlgo => {
                        if (rowAlgo === colAlgo) return <td key={colAlgo} className="px-2 py-1 text-center bg-muted/30 rounded-sm">–</td>;
                        const count = winRateMatrix[rowAlgo]?.[colAlgo] || 0;
                        const maxCount = Math.max(...algoNames.flatMap(r => algoNames.map(c => r === c ? 0 : (winRateMatrix[r]?.[c] || 0))), 1);
                        const opacity = Math.max(0.08, (count / maxCount) * 0.9);
                        const rowColor = algoSummaryMap.get(rowAlgo)?.color || '#64748b';
                        return (
                          <td key={colAlgo} className="px-2 py-1 text-center tabular-nums font-bold rounded-sm" style={{ backgroundColor: count > 0 ? rowColor : 'transparent', opacity: count > 0 ? opacity : 1, color: count > 0 ? (opacity > 0.5 ? '#fff' : 'var(--foreground)') : 'var(--muted-foreground)' }}>
                            {count}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </motion.div>

          </motion.div>
        </AnimatePresence>
      )}

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* DETAILS TAB                                                     */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      {resultsSubTab === 'details' && (
        <AnimatePresence mode="wait">
          <motion.div key="details" {...fadeIn} transition={{ duration: 0.25 }} className="space-y-6">

      {/* ─── 1. HEAD-TO-HEAD ALGORITHM COMPARISON ───────────── */}
      <motion.div variants={fadeIn}>
        <div className="flex items-center gap-2 mb-3">
          <span className={SECTION_NUMBER_STYLE}>1</span>
          <h3 className="text-sm font-semibold">Algoritma Karşılaştırma (Head-to-Head)</h3>
        </div>
        <Collapsible open={h2hOpen} onOpenChange={setH2hOpen}>
          <Card className="animated-border overflow-hidden rounded-lg">
            <CollapsibleTrigger asChild>
              <CardHeader className="pb-2 cursor-pointer hover:bg-muted/30 transition-colors">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-sm font-semibold flex items-center gap-2">
                      <GitCompareArrows className="size-4 text-violet-500" />
                      Algoritma Karşılaştırma (Head-to-Head)
                    </CardTitle>
                    <CardDescription>İki algoritmayı seçin ve detaylı karşılaştırma yapın</CardDescription>
                  </div>
                  <ChevronDown className={`size-4 text-muted-foreground transition-transform ${h2hOpen ? 'rotate-180' : ''}`} />
                </div>
              </CardHeader>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <CardContent className="pt-0 space-y-4">
                <div className="flex items-center gap-3 flex-wrap">
                  <Select value={h2hAlgoA} onValueChange={setH2hAlgoA}>
                    <SelectTrigger className="h-8 w-36 text-xs"><SelectValue placeholder="Algoritma A" /></SelectTrigger>
                    <SelectContent>
                      {algoNames.map(name => (
                        <SelectItem key={name} value={name} className="text-xs">
                          <span className="flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: algoSummaryMap.get(name)?.color }} />
                            {name}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <span className="text-xs font-bold text-muted-foreground">VS</span>
                  <Select value={h2hAlgoB} onValueChange={setH2hAlgoB}>
                    <SelectTrigger className="h-8 w-36 text-xs"><SelectValue placeholder="Algoritma B" /></SelectTrigger>
                    <SelectContent>
                      {algoNames.map(name => (
                        <SelectItem key={name} value={name} className="text-xs">
                          <span className="flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: algoSummaryMap.get(name)?.color }} />
                            {name}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {h2hData && h2hData.total > 0 && (
                  <div className="space-y-4">
                    {/* Win Record */}
                    <div className="grid grid-cols-3 gap-3 text-center">
                      <div className="rounded-lg border border-border/50 p-3" style={{ borderColor: h2hData.colorA + '40' }}>
                        <p className="text-lg font-bold" style={{ color: h2hData.colorA }}>{h2hData.winsA}</p>
                        <p className="text-xs text-muted-foreground">{h2hAlgoA} Kazanç</p>
                      </div>
                      <div className="rounded-lg border border-border/50 p-3 bg-muted/30">
                        <p className="text-lg font-bold text-muted-foreground">{h2hData.ties}</p>
                        <p className="text-xs text-muted-foreground">Berabere</p>
                      </div>
                      <div className="rounded-lg border border-border/50 p-3" style={{ borderColor: h2hData.colorB + '40' }}>
                        <p className="text-lg font-bold" style={{ color: h2hData.colorB }}>{h2hData.winsB}</p>
                        <p className="text-xs text-muted-foreground">{h2hAlgoB} Kazanç</p>
                      </div>
                    </div>

                    {/* Win Rate Bars */}
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs w-20 truncate font-medium" style={{ color: h2hData.colorA }}>{h2hAlgoA}</span>
                        <div className="flex-1 h-5 bg-muted/50 rounded-full overflow-hidden">
                          <div className="h-full rounded-full transition-all" style={{ width: `${h2hData.winRateA}%`, backgroundColor: h2hData.colorA }} />
                        </div>
                        <span className="text-xs tabular-nums font-medium w-10 text-right">{h2hData.winRateA}%</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs w-20 truncate font-medium" style={{ color: h2hData.colorB }}>{h2hAlgoB}</span>
                        <div className="flex-1 h-5 bg-muted/50 rounded-full overflow-hidden">
                          <div className="h-full rounded-full transition-all" style={{ width: `${h2hData.winRateB}%`, backgroundColor: h2hData.colorB }} />
                        </div>
                        <span className="text-xs tabular-nums font-medium w-10 text-right">{h2hData.winRateB}%</span>
                      </div>
                    </div>

                    {/* Average GAP Comparison */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div className="rounded-lg border border-border/50 p-3">
                        <p className="text-xs text-muted-foreground mb-1">Ortalama GAP</p>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold" style={{ color: h2hData.avgGapA <= h2hData.avgGapB ? h2hData.colorA : 'var(--muted-foreground)' }}>{h2hData.avgGapA}%</span>
                          <span className="text-xs text-muted-foreground">{h2hAlgoA}</span>
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-sm font-bold" style={{ color: h2hData.avgGapB <= h2hData.avgGapA ? h2hData.colorB : 'var(--muted-foreground)' }}>{h2hData.avgGapB}%</span>
                          <span className="text-xs text-muted-foreground">{h2hAlgoB}</span>
                        </div>
                      </div>
                      <div className="rounded-lg border border-border/50 p-3">
                        <p className="text-xs text-muted-foreground mb-1">Ortalama Süre</p>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold" style={{ color: h2hData.avgTimeA <= h2hData.avgTimeB ? h2hData.colorA : 'var(--muted-foreground)' }}>{h2hData.avgTimeA} ms</span>
                          <span className="text-xs text-muted-foreground">{h2hAlgoA}</span>
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-sm font-bold" style={{ color: h2hData.avgTimeB <= h2hData.avgTimeA ? h2hData.colorB : 'var(--muted-foreground)' }}>{h2hData.avgTimeB} ms</span>
                          <span className="text-xs text-muted-foreground">{h2hAlgoB}</span>
                        </div>
                      </div>
                    </div>

                    {/* Problem-by-problem */}
                    <div className="overflow-auto max-h-48 rounded-md border border-border/50">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="bg-muted/50">
                            <th className="px-3 py-1.5 text-left font-medium">Problem</th>
                            <th className="px-3 py-1.5 text-right font-medium" style={{ color: h2hData.colorA }}>{h2hAlgoA}</th>
                            <th className="px-3 py-1.5 text-right font-medium" style={{ color: h2hData.colorB }}>{h2hAlgoB}</th>
                            <th className="px-3 py-1.5 text-center font-medium">Kazanan</th>
                          </tr>
                        </thead>
                        <tbody>
                          {h2hData.comparisons.map(c => (
                            <tr key={c.problem} className="border-t border-border/30 hover:bg-muted/20">
                              <td className="px-3 py-1 font-mono"><ProblemDetailTooltip problemName={c.problem} /></td>
                              <td className="px-3 py-1 text-right tabular-nums" style={{ color: c.winner === h2hAlgoA ? h2hData.colorA : 'inherit', fontWeight: c.winner === h2hAlgoA ? 700 : 400 }}>{c.gapA}%</td>
                              <td className="px-3 py-1 text-right tabular-nums" style={{ color: c.winner === h2hAlgoB ? h2hData.colorB : 'inherit', fontWeight: c.winner === h2hAlgoB ? 700 : 400 }}>{c.gapB}%</td>
                              <td className="px-3 py-1 text-center">
                                {c.winner === 'tie' ? <span className="text-muted-foreground">—</span> : (
                                  <span className="font-medium" style={{ color: c.winner === h2hAlgoA ? h2hData.colorA : h2hData.colorB }}>
                                    {c.winner}
                                  </span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {h2hAlgoA && h2hAlgoB && h2hAlgoA !== h2hAlgoB && (!h2hData || h2hData.total === 0) && (
                  <p className="text-xs text-muted-foreground text-center py-4">Bu iki algoritma için ortak problem bulunamadı</p>
                )}

                {(!h2hAlgoA || !h2hAlgoB) && (
                  <p className="text-xs text-muted-foreground text-center py-4">Karşılaştırma için iki algoritma seçin</p>
                )}
              </CardContent>
            </CollapsibleContent>
          </Card>
        </Collapsible>
      </motion.div>

      {/* ─── 2. RESULTS TABLE ─────────────────────────────── */}
      <motion.div variants={fadeIn}>
        <div className="flex items-center gap-2 mb-3">
          <span className={SECTION_NUMBER_STYLE}>2</span>
          <h3 className="text-sm font-semibold">Sonuç Tablosu</h3>
        </div>
        <Card>
          <CardContent className="p-0">
            <div className="overflow-auto max-h-[500px]">
              <Table className="min-w-[800px]">
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs cursor-pointer hover:text-foreground select-none whitespace-nowrap sticky left-0 bg-card z-10" onClick={() => handleSort('problem')}>
                      <div className="flex items-center gap-1">Problem <SortIcon field="problem" sortField={sortField} sortDir={sortDir} /></div>
                    </TableHead>
                    <TableHead className="text-xs cursor-pointer hover:text-foreground text-right select-none whitespace-nowrap" onClick={() => handleSort('dimension')}>
                      <div className="flex items-center justify-end gap-1">Dim <SortIcon field="dimension" sortField={sortField} sortDir={sortDir} /></div>
                    </TableHead>
                    <TableHead className="text-xs cursor-pointer hover:text-foreground text-right select-none whitespace-nowrap" onClick={() => handleSort('optimal')}>
                      <div className="flex items-center justify-end gap-1">Optimal <SortIcon field="optimal" sortField={sortField} sortDir={sortDir} /></div>
                    </TableHead>
                    <TableHead className="text-xs cursor-pointer hover:text-foreground select-none whitespace-nowrap" onClick={() => handleSort('strategy')}>
                      <div className="flex items-center gap-1">Strateji <SortIcon field="strategy" sortField={sortField} sortDir={sortDir} /></div>
                    </TableHead>
                    <TableHead className="text-xs cursor-pointer hover:text-foreground text-right select-none whitespace-nowrap" onClick={() => handleSort('avgGap')}>
                      <div className="flex items-center justify-end gap-1">Ort. GAP <SortIcon field="avgGap" sortField={sortField} sortDir={sortDir} /></div>
                    </TableHead>
                    <TableHead className="text-xs cursor-pointer hover:text-foreground text-right select-none whitespace-nowrap" onClick={() => handleSort('bestGap')}>
                      <div className="flex items-center justify-end gap-1">En İyi GAP <SortIcon field="bestGap" sortField={sortField} sortDir={sortDir} /></div>
                    </TableHead>
                    <TableHead className="text-xs cursor-pointer hover:text-foreground text-right select-none whitespace-nowrap" onClick={() => handleSort('avgTimeMs')}>
                      <div className="flex items-center justify-end gap-1">Ort. Süre <SortIcon field="avgTimeMs" sortField={sortField} sortDir={sortDir} /></div>
                    </TableHead>
                    <TableHead className="text-xs text-center whitespace-nowrap">Runs</TableHead>
                    <TableHead className="text-xs whitespace-nowrap">Kategori</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pagedResults.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center py-12 text-muted-foreground">
                        <div className="flex flex-col items-center gap-2">
                          <Search className="size-8 opacity-30" />
                          <p className="text-sm">Sonuç bulunamadı</p>
                        </div>
                      </TableCell>
                    </TableRow>
                  ) : (
                    pagedResults.map((r, idx) => {
                      const algo = ALGORITHMS.find(a => a.shortName === r.strategy);
                      return (
                        <TableRow key={`${r.problem}-${r.strategy}-${idx}`} className="table-row-hover">
                          <TableCell className="text-xs font-mono font-medium whitespace-nowrap sticky left-0 bg-card z-10"><ProblemDetailTooltip problemName={r.problem} /></TableCell>
                          <TableCell className="text-xs text-right tabular-nums whitespace-nowrap">{r.dimension}</TableCell>
                          <TableCell className="text-xs text-right tabular-nums whitespace-nowrap">{formatNumber(r.optimal)}</TableCell>
                          <TableCell className="text-xs whitespace-nowrap">
                            <span className="flex items-center gap-1">
                              <span className="w-2 h-2 rounded-full inline-block shrink-0" style={{ backgroundColor: algo?.color || '#64748b' }} />
                              {r.strategy}
                            </span>
                          </TableCell>
                          <TableCell className="text-xs text-right whitespace-nowrap">
                            <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ${gapBg(r.avgGap)}`}>{r.avgGap}%</span>
                          </TableCell>
                          <TableCell className="text-xs text-right whitespace-nowrap">
                            <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ${gapBg(r.bestGap)}`}>{r.bestGap}%</span>
                          </TableCell>
                          <TableCell className="text-xs text-right tabular-nums whitespace-nowrap">{r.avgTimeMs.toFixed(1)} ms</TableCell>
                          <TableCell className="text-xs text-center tabular-nums whitespace-nowrap">{r.nRuns}</TableCell>
                          <TableCell className="whitespace-nowrap">
                            <Badge variant="secondary" className={`text-[10px] px-1.5 py-0 ${CATEGORY_BG[r.category]}`}>{CATEGORY_LABELS[r.category]}</Badge>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* ─── 3. PAGINATION ────────────────────────────────── */}
      <motion.div variants={fadeIn}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>Sayfa başına:</span>
            <Select value={String(resultsPerPage)} onValueChange={(v) => store.setResultsPerPage(parseInt(v))}>
              <SelectTrigger className="h-7 w-16 text-xs"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="10" className="text-xs">10</SelectItem>
                <SelectItem value="15" className="text-xs">15</SelectItem>
                <SelectItem value="25" className="text-xs">25</SelectItem>
                <SelectItem value="50" className="text-xs">50</SelectItem>
              </SelectContent>
            </Select>
            <span>{(resultsPage - 1) * resultsPerPage + 1}–{Math.min(resultsPage * resultsPerPage, filteredResults.length)} / {filteredResults.length}</span>
          </div>
          <div className="flex items-center gap-1">
            <Button variant="outline" size="icon" className="h-7 w-7" disabled={resultsPage <= 1} onClick={() => store.setResultsPage(1)}>
              <ChevronLeft className="size-3" /><ChevronLeft className="size-3 -ml-1.5" />
            </Button>
            <Button variant="outline" size="icon" className="h-7 w-7" disabled={resultsPage <= 1} onClick={() => store.setResultsPage(resultsPage - 1)}>
              <ChevronLeft className="size-3" />
            </Button>
            <span className="text-xs font-medium px-2">{resultsPage} / {totalPages}</span>
            <Button variant="outline" size="icon" className="h-7 w-7" disabled={resultsPage >= totalPages} onClick={() => store.setResultsPage(resultsPage + 1)}>
              <ChevronRight className="size-3" />
            </Button>
            <Button variant="outline" size="icon" className="h-7 w-7" disabled={resultsPage >= totalPages} onClick={() => store.setResultsPage(totalPages)}>
              <ChevronRight className="size-3" /><ChevronRight className="size-3 -ml-1.5" />
            </Button>
          </div>
        </div>
      </motion.div>

          </motion.div>
        </AnimatePresence>
      )}

    </motion.div>
  );
}


// ═══════════════════════════════════════════════════════════════════════════════
// ALGORITHMS INFO VIEW
// ═══════════════════════════════════════════════════════════════════════════════

function AlgorithmsInfoView() {
  return (
    <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-6">
      {/* Section Header */}
      <motion.div variants={fadeIn}>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500 to-amber-500 flex items-center justify-center">
            <Cpu className="size-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold">Algoritma Kütüphanesi</h2>
            <p className="text-sm text-muted-foreground">
              {ALGORITHMS.length} algoritma · {ALGORITHMS.filter(a => a.ready).length} hazır · {ALGORITHMS.filter(a => !a.ready).length} planlanıyor
            </p>
          </div>
        </div>
        <div className="gradient-divider mt-4" />
      </motion.div>

      {/* Local Search */}
      <motion.div variants={fadeIn}>
        <div className="flex items-center gap-2 mb-3">
          <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 text-xs border-0">
            Local Search Algoritmaları
          </Badge>
          <span className="text-xs text-muted-foreground">
            Kenar tabanlı yerel arama yöntemleri
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {ALGORITHMS.filter(a => a.type === 'local_search').map(algo => (
            <AlgorithmInfoCard key={algo.id} algo={algo} />
          ))}
        </div>
      </motion.div>

      {/* Meta-Heuristics */}
      <motion.div variants={fadeIn}>
        <div className="flex items-center gap-2 mb-3">
          <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 text-xs border-0">
            Meta-Heuristic Algoritmalar
          </Badge>
          <span className="text-xs text-muted-foreground">
            Popülasyon tabanlı evrimsel optimizasyon
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {ALGORITHMS.filter(a => a.type === 'meta_heuristic').map(algo => (
            <AlgorithmInfoCard key={algo.id} algo={algo} />
          ))}
        </div>
      </motion.div>
    </motion.div>
  );
}

// ─── Algorithm Info Card ─────────────────────────────────────────────────────

function AlgorithmInfoCard({ algo }: { algo: Algorithm }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <motion.div variants={fadeIn}>
        <Card
          className="card-lift overflow-hidden h-full cursor-pointer group"
          onClick={() => setOpen(true)}
        >
          <CardContent className="p-4 flex flex-col gap-3 relative">
            {/* Accent strip */}
            <div className="absolute top-0 left-0 right-0 h-1" style={{ background: `linear-gradient(90deg, ${algo.gradientFrom}, ${algo.gradientTo})` }} />
            {/* Header */}
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-bold"
                  style={{
                    background: `linear-gradient(135deg, ${algo.gradientFrom}, ${algo.gradientTo})`,
                  }}
                >
                  {algo.shortName.slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <h3 className="text-sm font-semibold">{algo.name}</h3>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    {algo.ready ? (
                      <Badge className="text-[9px] px-1 py-0 bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 border-0">
                        <CheckCircle2 className="size-2.5 mr-0.5" /> Hazır
                      </Badge>
                    ) : (
                      <Badge className="text-[9px] px-1 py-0 bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border-0">
                        <Clock className="size-2.5 mr-0.5" /> Planlanıyor
                      </Badge>
                    )}
                    <Badge variant="outline" className="text-[9px] px-1 py-0 font-mono">
                      {algo.complexity}
                    </Badge>
                  </div>
                </div>
              </div>
              <ChevronRight className="size-4 text-muted-foreground group-hover:text-foreground transition-colors mt-1" />
            </div>

            {/* Description */}
            <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">{algo.description}</p>

            {/* Parameters */}
            <div className="mt-auto">
              <div className="text-[10px] font-medium text-muted-foreground mb-1.5 flex items-center gap-1">
                <SlidersHorizontal className="size-2.5" />
                Parametreler ({algo.parameters.length})
              </div>
              <div className="space-y-1">
                {algo.parameters.slice(0, 4).map(param => (
                  <div key={param.key} className="flex items-center justify-between text-[10px]">
                    <span className="text-muted-foreground">{param.label}</span>
                    <span className="font-mono font-medium px-1 py-0.5 rounded bg-muted/80">
                      {param.type === 'select' ? (param.options?.find(o => o.value === param.default)?.label || param.default) : param.default}
                      {param.unit ? ` ${param.unit}` : ''}
                    </span>
                  </div>
                ))}
                {algo.parameters.length > 4 && (
                  <p className="text-[10px] text-muted-foreground text-center">
                    +{algo.parameters.length - 4} parametre daha
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Algorithm Detail Sheet */}
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <div className="flex items-center gap-3">
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center text-white text-sm font-bold shrink-0"
                style={{ background: `linear-gradient(135deg, ${algo.gradientFrom}, ${algo.gradientTo})` }}
              >
                {algo.shortName.slice(0, 2).toUpperCase()}
              </div>
              <div>
                <SheetTitle className="text-base">{algo.name}</SheetTitle>
                <SheetDescription className="flex items-center gap-2 mt-0.5">
                  {algo.ready ? (
                    <Badge className="text-[9px] px-1.5 py-0 bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 border-0">
                      <CheckCircle2 className="size-2.5 mr-0.5" /> Hazır
                    </Badge>
                  ) : (
                    <Badge className="text-[9px] px-1.5 py-0 bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border-0">
                      <Clock className="size-2.5 mr-0.5" /> Planlanıyor
                    </Badge>
                  )}
                  <Badge variant="outline" className="text-[9px] px-1.5 py-0 font-mono">
                    {algo.complexity}
                  </Badge>
                  <Badge variant="secondary" className="text-[9px] px-1.5 py-0">
                    {algo.type === 'local_search' ? 'Local Search' : 'Meta-Heuristic'}
                  </Badge>
                </SheetDescription>
              </div>
            </div>
          </SheetHeader>

          <div className="px-4 pb-6 space-y-6">
            {/* Description */}
            <div>
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Info className="size-3" /> Açıklama
              </h4>
              <p className="text-sm leading-relaxed">{algo.description}</p>
            </div>

            {/* Complexity */}
            <div>
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Activity className="size-3" /> Karmaşıklık
              </h4>
              <div className="p-3 rounded-lg bg-muted/40 border border-border/50">
                <code className="text-sm font-mono font-semibold" style={{ color: algo.color }}>{algo.complexity}</code>
                <p className="text-xs text-muted-foreground mt-1">
                  n = problem boyutu (düğüm sayısı)
                </p>
              </div>
            </div>

            {/* Performance Characteristics */}
            <div>
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <TrendingDown className="size-3" /> Performans Karakteristikleri
              </h4>
              <p className="text-sm leading-relaxed text-muted-foreground">
                {ALGO_PERFORMANCE[algo.id] || 'Performans bilgisi mevcut değil.'}
              </p>
            </div>

            {/* Parameters */}
            <div>
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <SlidersHorizontal className="size-3" /> Parametreler ({algo.parameters.length})
              </h4>
              <div className="space-y-2">
                {algo.parameters.map(param => (
                  <div key={param.key} className="p-3 rounded-lg bg-muted/30 border border-border/50">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">{param.label}</span>
                      <span className="text-xs font-mono px-2 py-0.5 rounded-full" style={{ backgroundColor: algo.color + '15', color: algo.color }}>
                        {param.type === 'select' ? (param.options?.find(o => o.value === param.default)?.label || param.default) : param.default}
                        {param.unit ? ` ${param.unit}` : ''}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">{param.description}</p>
                    {param.type === 'number' && param.min !== undefined && param.max !== undefined && (
                      <p className="text-[10px] text-muted-foreground mt-0.5">
                        Aralık: {param.min} – {param.max} (adım: {param.step})
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Pseudocode */}
            <div>
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <BookOpen className="size-3" /> Sözde Kod (Pseudocode)
              </h4>
              <pre className="p-4 rounded-lg bg-muted/60 border border-border/50 text-xs font-mono leading-relaxed overflow-x-auto whitespace-pre text-foreground">
                {ALGO_PSEUDOCODE[algo.id] || '// Pseudocode mevcut değil'}
              </pre>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
