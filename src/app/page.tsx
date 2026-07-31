"use client";

import { useTranslations } from 'next-intl';
import React, { useState, useEffect, useCallback, useRef, useMemo, Suspense } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  BarChart3,
  Play,
  Square,
  Download,
  CheckCircle2,
  AlertCircle,
  Clock,
  Zap,
  Target,
  Activity,
  Loader2,
  FlaskConical,
  ScrollText,
  Timer,
  TrendingUp,
  Wifi,
  WifiOff,
  RefreshCw,
  Trophy,
  Cpu,
  Route,
  ArrowDown,
  GitBranch,
  Layers,
  Sparkles,
  Gauge,
  Eye,
  MonitorSmartphone,
  ChevronRight,
  Github,
  Heart,
  FileSpreadsheet,
  History,
  Trash2,
  Medal,
  Grid3X3,
  Crosshair,
  ChevronUp,
  X,
  Sun,
  Moon,
  Bot,
  Info,
  BarChart2,
  PieChart as PieChartIcon,
  ArrowUpRight,
  Lightbulb,
  ChevronDown,
  Send,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  ALGORITHM_OPTIONS_GROUPED,
  ALGORITHM_DISPLAY_NAMES,
  ALGORITHM_DESCRIPTIONS,
  ALGORITHM_COMPLEXITY,
} from "@/lib/algorithm-constants";
import {
  type BenchmarkProblem,
  type BenchmarkAlgorithm,
  type BenchmarkRunSettings,
  type BenchmarkStatus,
  type BenchmarkResult,
  type BenchmarkResultsResponse,
  fetchProblems,
  startBenchmark,
  pollStatus,
  stopBenchmark,
  fetchResults,
} from "@/services/benchmark-service";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ScatterChart,
  Scatter,
  ZAxis,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  PieChart,
  Pie,
  Cell as RechartsCell,
  Legend as RechartsLegend,
} from "recharts";

// ============================================================
// CSS Animation Keyframes (injected via style tag)
// ============================================================
const ANIMATION_STYLES = `
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(24px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes slideUp {
  from { opacity: 0; transform: translateY(40px) scale(0.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes gradientMove {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-12px); }
}
@keyframes floatDelay {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-8px); }
}
@keyframes dotPulse {
  0%, 100% { opacity: 0.15; }
  50% { opacity: 0.35; }
}
@keyframes countUp {
  from { opacity: 0; transform: scale(0.5); }
  to { opacity: 1; transform: scale(1); }
}
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
@keyframes pulseGlow {
  0%, 100% { box-shadow: 0 0 8px rgba(20,184,166,0.3); }
  50% { box-shadow: 0 0 20px rgba(20,184,166,0.6); }
}
@keyframes slideInRight {
  from { opacity: 0; transform: translateX(30px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes breathe {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.02); }
}
.animate-fade-in-up { animation: fadeInUp 0.7s ease-out forwards; }
.animate-fade-in { animation: fadeIn 0.5s ease-out forwards; }
.animate-slide-up { animation: slideUp 0.6s ease-out forwards; }
.animate-gradient-move { animation: gradientMove 8s ease infinite; background-size: 200% 200%; }
.animate-float { animation: float 4s ease-in-out infinite; }
.animate-float-delay { animation: floatDelay 5s ease-in-out 1s infinite; }
.animate-dot-pulse { animation: dotPulse 3s ease-in-out infinite; }
.animate-shimmer { animation: shimmer 3s linear infinite; background-size: 200% 100%; }
.animate-pulse-glow { animation: pulseGlow 2s ease-in-out infinite; }
.animate-slide-in-right { animation: slideInRight 0.5s ease-out forwards; }
.animate-breathe { animation: breathe 4s ease-in-out infinite; }
.glass-card { backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); }
.gradient-text { background: linear-gradient(135deg, #14b8a6, #10b981, #059669); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.hover-lift { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.hover-lift:hover { transform: translateY(-2px); box-shadow: 0 8px 25px -5px rgba(0,0,0,0.1), 0 4px 10px -5px rgba(0,0,0,0.04); }
.delay-100 { animation-delay: 100ms; }
.delay-200 { animation-delay: 200ms; }
.delay-300 { animation-delay: 300ms; }
.delay-400 { animation-delay: 400ms; }
.delay-500 { animation-delay: 500ms; }
`;

// ============================================================
// Constants
// ============================================================

const POLL_INTERVAL_MS = 2000;
const RUN_HISTORY_KEY = "uniride_run_history";

// Wall-clock helpers — kept at module scope so Date.now() is not called
// during render (react-hooks/purity). Recomputed per poll-driven render.
const elapsedSeconds = (startTimeIso: string) => Math.round((Date.now() - new Date(startTimeIso).getTime()) / 1000);
const estimateRemainingSeconds = (startTimeIso: string, progressPercent: number) =>
  Math.round(elapsedSeconds(startTimeIso) * ((100 - progressPercent) / progressPercent));

const CHART_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
  "hsl(160, 60%, 45%)",
  "hsl(30, 80%, 55%)",
  "hsl(280, 60%, 55%)",
  "hsl(0, 70%, 55%)",
  "hsl(190, 70%, 50%)",
  "hsl(60, 70%, 45%)",
  "hsl(330, 60%, 50%)",
  "hsl(120, 50%, 40%)",
  "hsl(210, 60%, 50%)",
];

const CHART_COLOR_VALUES = [
  "#10b981", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4",
  "#22c55e", "#eab308", "#a855f7", "#f97316", "#14b8a6",
  "#84cc16", "#ec4899", "#10b981", "#3b82f6",
];

// ============================================================
// Run History Types
// ============================================================

interface RunHistoryEntry {
  run_id: string;
  date: string;
  algorithmCount: number;
  problemCount: number;
  experimentCount: number;
  bestAlgorithm: string;
  bestGap: number | null;
  results: BenchmarkResultsResponse;
}

function loadRunHistory(): RunHistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(RUN_HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveRunHistory(entry: RunHistoryEntry) {
  try {
    const history = loadRunHistory();
    history.unshift(entry);
    if (history.length > 20) history.pop();
    localStorage.setItem(RUN_HISTORY_KEY, JSON.stringify(history));
  } catch {
    // localStorage might be full
  }
}

function clearRunHistory() {
  try {
    localStorage.removeItem(RUN_HISTORY_KEY);
  } catch {
    // ignore
  }
}

// ============================================================
// Mock Data
// ============================================================

const MOCK_PROBLEMS: BenchmarkProblem[] = [
  { name: "eil51", dimension: 51, optimal: 426, category: "small", problem_type: "TSP", edge_weight_type: "EUC_2D", available: true },
  { name: "berlin52", dimension: 52, optimal: 7542, category: "small", problem_type: "TSP", edge_weight_type: "EUC_2D", available: true },
  { name: "st70", dimension: 70, optimal: 675, category: "small", problem_type: "TSP", edge_weight_type: "EUC_2D", available: true },
  { name: "eil76", dimension: 76, optimal: 538, category: "small", problem_type: "TSP", edge_weight_type: "EUC_2D", available: true },
  { name: "pr107", dimension: 107, optimal: 44303, category: "small", problem_type: "TSP", edge_weight_type: "EUC_2D", available: true },
  { name: "pr124", dimension: 124, optimal: 59030, category: "medium", problem_type: "TSP", edge_weight_type: "EUC_2D", available: true },
  { name: "pr144", dimension: 144, optimal: 58537, category: "medium", problem_type: "TSP", edge_weight_type: "EUC_2D", available: true },
  { name: "pr152", dimension: 152, optimal: 73682, category: "medium", problem_type: "TSP", edge_weight_type: "EUC_2D", available: true },
  { name: "kroA150", dimension: 150, optimal: 26524, category: "medium", problem_type: "TSP", edge_weight_type: "EUC_2D", available: true },
  { name: "kroB150", dimension: 150, optimal: 26130, category: "medium", problem_type: "TSP", edge_weight_type: "EUC_2D", available: true },
  { name: "pr226", dimension: 226, optimal: 80369, category: "medium", problem_type: "TSP", edge_weight_type: "EUC_2D", available: true },
  { name: "pr299", dimension: 299, optimal: 48191, category: "large", problem_type: "TSP", edge_weight_type: "EUC_2D", available: true },
  { name: "lin318", dimension: 318, optimal: 42029, category: "large", problem_type: "TSP", edge_weight_type: "EUC_2D", available: true },
  { name: "rd400", dimension: 400, optimal: 15281, category: "large", problem_type: "TSP", edge_weight_type: "EUC_2D", available: true },
  { name: "pr439", dimension: 439, optimal: 107217, category: "large", problem_type: "TSP", edge_weight_type: "EUC_2D", available: true },
];

const ALGORITHM_PROFILES: Record<string, { gapRange: [number, number]; timeRange: [number, number] }> = {
  pyvrp: { gapRange: [0.5, 2.0], timeRange: [200, 800] },
  vroom: { gapRange: [1.0, 3.0], timeRange: [50, 200] },
  ortools_cvrp: { gapRange: [0.8, 2.5], timeRange: [300, 1200] },
  ga_split: { gapRange: [1.5, 5.0], timeRange: [500, 2000] },
  pso_split: { gapRange: [2.0, 6.0], timeRange: [300, 1500] },
  gwo_split: { gapRange: [2.5, 7.0], timeRange: [400, 1800] },
  hho_split: { gapRange: [2.0, 6.5], timeRange: [350, 1600] },
  genetic_algorithm: { gapRange: [5.0, 12.0], timeRange: [800, 3000] },
  pso: { gapRange: [6.0, 14.0], timeRange: [600, 2500] },
  gwo: { gapRange: [7.0, 15.0], timeRange: [700, 2800] },
  hho: { gapRange: [6.0, 13.0], timeRange: [650, 2600] },
  two_opt: { gapRange: [3.0, 8.0], timeRange: [100, 500] },
  greedy: { gapRange: [8.0, 18.0], timeRange: [10, 50] },
  permutation_tsp: { gapRange: [0, 0.5], timeRange: [5, 2000] },
};

function generateDemoResult(algorithm: string, problem: BenchmarkProblem, runNumber: number): BenchmarkResult {
  const profile = ALGORITHM_PROFILES[algorithm] || { gapRange: [5, 15], timeRange: [100, 1000] };
  const [minGap, maxGap] = profile.gapRange;
  const [minTime, maxTime] = profile.timeRange;
  const seed = algorithm.length * 100 + problem.dimension * 10 + runNumber;
  const rand = (min: number, max: number) => {
    const x = Math.sin(seed + min) * 10000;
    return min + (x - Math.floor(x)) * (max - min);
  };
  const gapPercent = rand(minGap, maxGap);
  const elapsedMs = Math.round(rand(minTime, maxTime));
  const tourLength = problem.optimal
    ? Math.round(problem.optimal * (1 + gapPercent / 100))
    : Math.round(rand(5000, 50000));
  return {
    algorithm,
    problem: problem.name,
    run_number: runNumber,
    tour_length: tourLength,
    elapsed_ms: elapsedMs,
    gap_percent: problem.optimal ? Number(gapPercent.toFixed(2)) : null,
    timestamp: new Date().toISOString(),
    metadata: {},
  };
}

// ============================================================
// Helpers
// ============================================================

function getCategoryLabel(cat: string, t: (key: string) => string): string {
  switch (cat) {
    case "small": return t('sizeLabels.small');
    case "medium": return t('sizeLabels.medium');
    case "large": return t('sizeLabels.large');
    default: return cat;
  }
}

function getCategoryBadgeVariant(cat: string): "default" | "secondary" | "outline" | "destructive" {
  switch (cat) {
    case "small": return "secondary";
    case "medium": return "default";
    case "large": return "destructive";
    default: return "outline";
  }
}

function getStatusBadge(status: string, tc: (key: string) => string) {
  switch (status) {
    case "running":
      return <Badge className="bg-sky-600 hover:bg-sky-700 text-white"><Activity className="h-3 w-3 mr-1 animate-pulse" /> {tc('status.running')}</Badge>;
    case "completed":
      return <Badge className="bg-emerald-600 hover:bg-emerald-700 text-white"><CheckCircle2 className="h-3 w-3 mr-1" /> {tc('status.completed')}</Badge>;
    case "failed":
      return <Badge variant="destructive"><AlertCircle className="h-3 w-3 mr-1" /> {tc('status.failed')}</Badge>;
    case "stopped":
      return <Badge variant="outline" className="border-amber-500 text-amber-700"><Square className="h-3 w-3 mr-1" /> {tc('status.stopped')}</Badge>;
    case "queued":
      return <Badge variant="secondary"><Clock className="h-3 w-3 mr-1" /> {tc('status.queued')}</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

function getPipelineIcon(pipeline: string) {
  switch (pipeline) {
    case "A": return <GitBranch className="h-5 w-5" />;
    case "B": return <Layers className="h-5 w-5" />;
    case "holistic": return <Sparkles className="h-5 w-5" />;
    case "heuristic": return <Gauge className="h-5 w-5" />;
    default: return <Cpu className="h-5 w-5" />;
  }
}

function getPipelineBorder(pipeline: string): string {
  switch (pipeline) {
    case "A": return "border-teal-500/30 hover:border-teal-500/60";
    case "B": return "border-amber-500/30 hover:border-amber-500/60";
    case "holistic": return "border-purple-500/30 hover:border-purple-500/60";
    case "heuristic": return "border-slate-400/30 hover:border-slate-400/60";
    default: return "border-primary/30 hover:border-primary/60";
  }
}

function escapeCSV(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "";
  const str = String(value);
  if (str.includes(",") || str.includes('"') || str.includes("\n")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

function getRankBadge(rank: number) {
  if (rank === 0) return <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-gradient-to-br from-yellow-400 to-amber-500 text-white text-[10px] font-bold shadow-md">1</span>;
  if (rank === 1) return <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-gradient-to-br from-gray-300 to-gray-400 text-white text-[10px] font-bold shadow-md">2</span>;
  if (rank === 2) return <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-gradient-to-br from-amber-600 to-amber-700 text-white text-[10px] font-bold shadow-md">3</span>;
  return <span className="font-mono text-[10px] text-muted-foreground">{rank + 1}</span>;
}

// ============================================================
// Animated Counter Component
// ============================================================

function AnimatedCounter({ target, duration = 1200, suffix = "", prefix = "", decimals = 0 }: {
  target: number; duration?: number; suffix?: string; prefix?: string; decimals?: number;
}) {
  const [current, setCurrent] = useState(0);
  const startRef = useRef<number | null>(null);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    startRef.current = null;
    const animate = (timestamp: number) => {
      if (startRef.current === null) startRef.current = timestamp;
      const elapsed = timestamp - startRef.current;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCurrent(eased * target);
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      }
    };
    rafRef.current = requestAnimationFrame(animate);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [target, duration]);

  return (
    <span className="tabular-nums">
      {prefix}{decimals > 0 ? current.toFixed(decimals) : Math.round(current)}{suffix}
    </span>
  );
}

// ============================================================
// Main Page Component
// ============================================================

export default function BenchmarkSuitePage() {
  const t = useTranslations('page.benchmark');
  const tc = useTranslations('common');
  const { toast } = useToast();

  // ---- State ----
  const [activeTab, setActiveTab] = useState("config");
  const [resultsSubTab, setResultsSubTab] = useState("tables");
  const [isApiOnline, setIsApiOnline] = useState<boolean | null>(null);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [showHero, setShowHero] = useState(true);

  // Problems
  const [problems, setProblems] = useState<BenchmarkProblem[]>([]);
  const [problemsLoading, setProblemsLoading] = useState(true);
  const [problemCategoryFilter, setProblemCategoryFilter] = useState<string>("all");
  const [problemSearch, setProblemSearch] = useState<string>("");
  const [selectedProblems, setSelectedProblems] = useState<Set<string>>(new Set());

  // Algorithms
  const [selectedAlgorithms, setSelectedAlgorithms] = useState<Set<string>>(new Set());
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(["Route-First, Cluster-Second (Optimal Split)", "Holistik Çözücüler (Native CVRP)"]));

  // Settings
  const [nRuns, setNRuns] = useState(3);
  const [seed, setSeed] = useState(42);

  // Run
  const [runId, setRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<BenchmarkStatus | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);

  // Results
  const [results, setResults] = useState<BenchmarkResultsResponse | null>(null);
  const [resultsLoading, setResultsLoading] = useState(false);

  // Run History
  const [runHistory, setRunHistory] = useState<RunHistoryEntry[]>(() => loadRunHistory());
  const [showHistory, setShowHistory] = useState(false);

  // Animation trigger for counters
  const [animateResults, setAnimateResults] = useState(false);

  // Dark mode
  const [isDark, setIsDark] = useState(() => {
    try { return document.documentElement.classList.contains("dark"); } catch { return false; }
  });

  // AI Advisor
  const [showAdvisor, setShowAdvisor] = useState(false);
  const [advisorLoading, setAdvisorLoading] = useState(false);
  const [advisorAdvice, setAdvisorAdvice] = useState<string | null>(null);
  const [advisorGoal, setAdvisorGoal] = useState<string>("balanced");

  // Algorithm Info Dialog
  const [selectedAlgoInfo, setSelectedAlgoInfo] = useState<string | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const demoTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const benchmarkRef = useRef<HTMLDivElement>(null);

  // Dark mode toggle
  const toggleDarkMode = useCallback(() => {
    setIsDark((prev) => {
      const next = !prev;
      document.documentElement.classList.toggle("dark", next);
      return next;
    });
  }, []);

  // AI Advisor handler
  const handleGetAdvice = useCallback(async () => {
    if (selectedProblems.size === 0 || selectedAlgorithms.size === 0) {
      toast({ title: tc('warning'), description: t('toast.selectWarningDesc'), variant: "destructive" });
      return;
    }
    setAdvisorLoading(true);
    setAdvisorAdvice(null);
    setShowAdvisor(true);
    try {
      const problemsArr = problems.filter((p) => selectedProblems.has(p.name));
      const res = await fetch("/api/ai-advisor", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          problems: problemsArr,
          selectedAlgorithms: Array.from(selectedAlgorithms),
          goal: advisorGoal,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setAdvisorAdvice(data.advice);
      } else {
        setAdvisorAdvice(t('advisor.unavailable'));
      }
    } catch {
      setAdvisorAdvice(t('advisor.connectionError'));
    } finally {
      setAdvisorLoading(false);
    }
  }, [selectedProblems, selectedAlgorithms, problems, advisorGoal, toast]);

  // ---- Check API availability ----
  useEffect(() => {
    const checkApi = async () => {
      try {
        const res = await fetch("/api/benchmark/health", {
          method: "GET",
          signal: AbortSignal.timeout(5000),
        });
        const online = res.ok;
        setIsApiOnline(online);
        if (online) setIsDemoMode(false);
      } catch {
        setIsApiOnline(false);
      }
    };
    checkApi();
    const interval = setInterval(checkApi, 15000);
    return () => clearInterval(interval);
  }, []);

  // ---- Fetch problems ----
  useEffect(() => {
    const load = async () => {
      setProblemsLoading(true);
      try {
        if (isApiOnline === false) {
          setProblems(MOCK_PROBLEMS);
          setIsDemoMode(true);
          const eil51 = MOCK_PROBLEMS.find((p) => p.name === "eil51");
          if (eil51) {
            setSelectedProblems(new Set([eil51.name]));
          }
          setSelectedAlgorithms(new Set(["ga_split", "greedy"]));
        } else {
          const data = await fetchProblems();
          setProblems(data);
          const eil51 = data.find((p) => p.name === "eil51");
          if (eil51) {
            setSelectedProblems(new Set([eil51.name]));
          }
          setSelectedAlgorithms(new Set(["greedy"]));
        }
      } catch {
        setProblems(MOCK_PROBLEMS);
        setIsDemoMode(true);
        setSelectedProblems(new Set(["eil51"]));
        setSelectedAlgorithms(new Set(["ga_split", "greedy"]));
      } finally {
        setProblemsLoading(false);
      }
    };
    if (isApiOnline !== null) {
      load();
    }
  }, [isApiOnline]);

  // ---- Cleanup ----
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (demoTimerRef.current) clearInterval(demoTimerRef.current);
    };
  }, []);

  // ---- Save run to history ----
  const saveRunToHistory = (res: BenchmarkResultsResponse) => {
    const byAlgorithm = new Map<string, BenchmarkResult[]>();
    for (const r of res.results) {
      if (!byAlgorithm.has(r.algorithm)) byAlgorithm.set(r.algorithm, []);
      byAlgorithm.get(r.algorithm)!.push(r);
    }
    let bestAlgo = "";
    let bestGap: number | null = null;
    for (const [algo, results_list] of byAlgorithm) {
      const gaps = results_list.filter((r) => r.gap_percent !== null).map((r) => r.gap_percent!);
      const avgGap = gaps.length > 0 ? gaps.reduce((s, g) => s + g, 0) / gaps.length : null;
      if (avgGap !== null && (bestGap === null || avgGap < bestGap)) {
        bestGap = avgGap;
        bestAlgo = ALGORITHM_DISPLAY_NAMES[algo] || algo;
      }
    }
    const entry: RunHistoryEntry = {
      run_id: res.run_id,
      date: new Date().toISOString(),
      algorithmCount: byAlgorithm.size,
      problemCount: new Set(res.results.map((r) => r.problem)).size,
      experimentCount: res.results.length,
      bestAlgorithm: bestAlgo,
      bestGap: bestGap !== null ? Number(bestGap.toFixed(2)) : null,
      results: res,
    };
    saveRunHistory(entry);
    setRunHistory(loadRunHistory());
  };

  // ---- Real API Polling ----
  const startPolling = useCallback((rid: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const status = await pollStatus(rid);
        setRunStatus(status);
        if (status.status === "completed" || status.status === "failed" || status.status === "stopped") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
          if (status.status === "completed") {
            setActiveTab("results");
            try {
              setResultsLoading(true);
              const res = await fetchResults(rid);
              setResults(res);
              setAnimateResults(true);
              saveRunToHistory(res);
              toast({ title: t('toast.benchmarkCompleteTitle'), description: t('toast.benchmarkCompleteDesc', { n: res.results.length }) });
            } catch {
              toast({ title: t('toast.resultsNotFetchedTitle'), description: t('toast.resultsNotFetchedDesc'), variant: "destructive" });
            } finally {
              setResultsLoading(false);
            }
          }
        }
      } catch {
        // Continue polling on transient errors
      }
    }, POLL_INTERVAL_MS);
  }, [toast]);

  // ---- Demo Benchmark Simulation ----
  const startDemoBenchmark = useCallback(() => {
    const demoRunId = `demo_${Date.now()}`;
    setRunId(demoRunId);
    setRunStatus(null);
    setResults(null);
    setAnimateResults(false);
    setActiveTab("execution");

    const totalExp = selectedAlgorithms.size * selectedProblems.size * nRuns;
    const startTime = new Date().toISOString();
    let completed = 0;
    const demoResults: BenchmarkResult[] = [];

    const problemList = problems.filter((p) => selectedProblems.has(p.name));
    for (const algo of selectedAlgorithms) {
      for (const prob of problemList) {
        for (let run = 1; run <= nRuns; run++) {
          demoResults.push(generateDemoResult(algo, prob, run));
        }
      }
    }

    setRunStatus({
      run_id: demoRunId,
      status: "running",
      total_experiments: totalExp,
      completed_experiments: 0,
      results_count: 0,
      message: t('runPanel.demoRunning'),
      progress_percent: 0,
      start_time: startTime,
      end_time: null,
    });

    if (demoTimerRef.current) clearInterval(demoTimerRef.current);
    const stepSize = Math.max(1, Math.ceil(totalExp / 40));
    const stepInterval = 200;

    demoTimerRef.current = setInterval(() => {
      completed = Math.min(completed + stepSize, totalExp);
      const progress = (completed / totalExp) * 100;

      setRunStatus({
        run_id: demoRunId,
        status: progress >= 100 ? "completed" : "running",
        total_experiments: totalExp,
        completed_experiments: completed,
        results_count: Math.min(completed, demoResults.length),
        message: progress >= 100 ? t('runPanel.demoCompleted') : t('runPanel.processing', { completed, total: totalExp }),
        progress_percent: progress,
        start_time: startTime,
        end_time: progress >= 100 ? new Date().toISOString() : null,
      });

      if (progress >= 100) {
        if (demoTimerRef.current) clearInterval(demoTimerRef.current);
        demoTimerRef.current = null;

        const resultsResponse: BenchmarkResultsResponse = {
          run_id: demoRunId,
          status: "completed",
          total_experiments: totalExp,
          results: demoResults,
        };
        setResults(resultsResponse);
        setAnimateResults(true);
        setActiveTab("results");
        saveRunToHistory(resultsResponse);
        toast({ title: t('toast.demoCompleteTitle'), description: t('toast.demoCompleteDesc', { n: demoResults.length }) });
      }
    }, stepInterval);
  }, [selectedAlgorithms, selectedProblems, nRuns, problems, toast, saveRunToHistory]);

  // ---- Handlers ----
  const handleStartBenchmark = async () => {
    if (selectedProblems.size === 0 || selectedAlgorithms.size === 0) return;

    if (isDemoMode) {
      setIsStarting(true);
      setTimeout(() => {
        startDemoBenchmark();
        setIsStarting(false);
      }, 500);
      return;
    }

    setIsStarting(true);
    try {
      const algorithms: BenchmarkAlgorithm[] = Array.from(selectedAlgorithms).map((id) => ({ id }));
      const problemsArr = Array.from(selectedProblems);
      const settings: BenchmarkRunSettings = { n_runs: nRuns, seed };

      const response = await startBenchmark(algorithms, problemsArr, settings);
      setRunId(response.run_id);
      setRunStatus(null);
      setResults(null);
      setAnimateResults(false);
      setActiveTab("execution");

      toast({ title: t('toast.benchmarkStartedTitle'), description: t('toast.benchmarkStartedDesc', { n: response.total_experiments }) });
      startPolling(response.run_id);
    } catch {
      toast({ title: t('toast.benchmarkStartFailedTitle'), description: t('toast.serverError'), variant: "destructive" });
    } finally {
      setIsStarting(false);
    }
  };

  const handleStopBenchmark = async () => {
    if (!runId) return;
    setIsStopping(true);
    try {
      if (isDemoMode) {
        if (demoTimerRef.current) clearInterval(demoTimerRef.current);
        demoTimerRef.current = null;
        setRunStatus((prev) => prev ? { ...prev, status: "stopped", end_time: new Date().toISOString() } : null);
        toast({ title: t('toast.benchmarkStoppedTitle'), description: t('toast.benchmarkStoppedDesc') });
      } else {
        await stopBenchmark(runId);
        toast({ title: t('toast.benchmarkStoppedTitle'), description: t('toast.benchmarkStoppingDesc') });
      }
    } catch {
      toast({ title: t('toast.stopFailedTitle'), description: t('toast.serverError'), variant: "destructive" });
    } finally {
      setIsStopping(false);
    }
  };

  const handleExportJSON = () => {
    if (!results) return;
    const blob = new Blob([JSON.stringify(results, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `benchmark-${runId || "results"}-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast({ title: t('toast.exportedTitle'), description: t('toast.exportedJSONDesc') });
  };

  const handleExportCSV = () => {
    if (!results) return;
    const headers = ["algorithm", "problem", "run_number", "tour_length", "elapsed_ms", "gap_percent", "timestamp"];
    const rows = results.results.map((r) =>
      [escapeCSV(r.algorithm), escapeCSV(r.problem), escapeCSV(r.run_number), escapeCSV(r.tour_length), escapeCSV(r.elapsed_ms), escapeCSV(r.gap_percent), escapeCSV(r.timestamp)].join(",")
    );
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `benchmark-${runId || "results"}-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast({ title: t('toast.csvDownloadedTitle'), description: t('toast.csvDownloadedDesc') });
  };

  const handleManualFetchResults = async () => {
    if (!runId) return;
    if (isDemoMode && results) {
      setActiveTab("results");
      return;
    }
    setResultsLoading(true);
    try {
      const res = await fetchResults(runId);
      setResults(res);
      setAnimateResults(true);
      setActiveTab("results");
      toast({ title: t('toast.resultsLoadedTitle'), description: t('toast.resultsLoadedDesc', { n: res.results.length }) });
    } catch {
      toast({ title: t('toast.resultsNotFetchedTitle'), description: t('toast.serverError'), variant: "destructive" });
    } finally {
      setResultsLoading(false);
    }
  };

  const handleLoadHistoryEntry = (entry: RunHistoryEntry) => {
    setResults(entry.results);
    setRunId(entry.run_id);
    setAnimateResults(true);
    setActiveTab("results");
    toast({ title: t('toast.historyLoadedTitle'), description: t('toast.historyLoadedDesc', { id: entry.run_id }) });
  };

  const handleClearHistory = () => {
    clearRunHistory();
    setRunHistory([]);
    toast({ title: t('toast.historyClearedTitle'), description: t('toast.historyClearedDesc') });
  };

  // ---- Selection helpers ----
  const filteredProblems = problems.filter((p) => {
    const catMatch = problemCategoryFilter === "all" || p.category === problemCategoryFilter;
    const searchMatch = !problemSearch || p.name.toLowerCase().includes(problemSearch.toLowerCase());
    return catMatch && searchMatch;
  });

  const toggleProblem = (name: string) => {
    setSelectedProblems((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name); else next.add(name);
      return next;
    });
  };

  const selectAllProblems = () => setSelectedProblems(new Set(filteredProblems.map((p) => p.name)));
  const deselectAllProblems = () => setSelectedProblems(new Set());

  const toggleAlgorithm = (key: string) => {
    setSelectedAlgorithms((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const selectAllAlgorithms = () => {
    const keys: string[] = ALGORITHM_OPTIONS_GROUPED.flatMap((g) => g.algorithms.map((a) => String(a.key)));
    setSelectedAlgorithms(new Set(keys));
  };

  const selectRecommendedAlgorithms = () => {
    const keys: string[] = ALGORITHM_OPTIONS_GROUPED.flatMap((g) =>
      g.algorithms.filter((a) => a.recommended).map((a) => String(a.key))
    );
    setSelectedAlgorithms(new Set(keys));
  };

  const toggleGroup = (category: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(category)) next.delete(category); else next.add(category);
      return next;
    });
  };

  // ---- Result analytics ----
  const getAnalytics = useCallback(() => {
    if (!results || !results.results.length) return null;
    const allResults = results.results;
    const totalExperiments = allResults.length;
    const totalTimeMs = allResults.reduce((s, r) => s + r.elapsed_ms, 0);
    const successfulResults = allResults.filter((r) => r.gap_percent !== null);
    const successRate = totalExperiments > 0 ? (successfulResults.length / totalExperiments) * 100 : 0;

    const byAlgorithm = new Map<string, BenchmarkResult[]>();
    for (const r of allResults) {
      if (!byAlgorithm.has(r.algorithm)) byAlgorithm.set(r.algorithm, []);
      byAlgorithm.get(r.algorithm)!.push(r);
    }

    const algorithmStats = Array.from(byAlgorithm.entries()).map(([algo, res]) => {
      const gaps = res.filter((r) => r.gap_percent !== null).map((r) => r.gap_percent!);
      const times = res.map((r) => r.elapsed_ms);
      const tours = res.map((r) => r.tour_length);
      const gapVariance = gaps.length > 1
        ? gaps.reduce((s, g) => s + Math.pow(g - (gaps.reduce((a, b) => a + b, 0) / gaps.length), 2), 0) / gaps.length
        : 0;
      return {
        algorithm: algo,
        displayName: ALGORITHM_DISPLAY_NAMES[algo] || algo,
        count: res.length,
        avgGap: gaps.length > 0 ? gaps.reduce((s, g) => s + g, 0) / gaps.length : null,
        minGap: gaps.length > 0 ? Math.min(...gaps) : null,
        maxGap: gaps.length > 0 ? Math.max(...gaps) : null,
        gapStdDev: Math.sqrt(gapVariance),
        avgTime: times.reduce((s, t) => s + t, 0) / times.length,
        minTour: Math.min(...tours),
        maxTour: Math.max(...tours),
        avgTour: tours.reduce((s, t) => s + t, 0) / tours.length,
      };
    }).sort((a, b) => (a.avgGap ?? Infinity) - (b.avgGap ?? Infinity));

    const byProblem = new Map<string, BenchmarkResult[]>();
    for (const r of allResults) {
      if (!byProblem.has(r.problem)) byProblem.set(r.problem, []);
      byProblem.get(r.problem)!.push(r);
    }

    const problemStats = Array.from(byProblem.entries()).map(([prob, res]) => {
      const tours = res.map((r) => r.tour_length);
      const optimal = problems.find((p) => p.name === prob)?.optimal;
      const bestTour = Math.min(...tours);
      const bestResult = res.find((r) => r.tour_length === bestTour);
      const algoGaps: { algo: string; gap: number | null }[] = [];
      for (const [algo, algoRes] of byAlgorithm.entries()) {
        const probRes = algoRes.filter((r) => r.problem === prob);
        const gaps = probRes.filter((r) => r.gap_percent !== null).map((r) => r.gap_percent!);
        algoGaps.push({ algo, gap: gaps.length > 0 ? gaps.reduce((s, g) => s + g, 0) / gaps.length : null });
      }
      return {
        problem: prob,
        optimal,
        bestTour,
        bestAlgorithm: bestResult?.algorithm || "",
        bestAlgorithmName: ALGORITHM_DISPLAY_NAMES[bestResult?.algorithm || ""] || bestResult?.algorithm || "",
        gapFromOptimal: optimal ? ((bestTour - optimal) / optimal) * 100 : null,
        algorithmsTested: new Set(res.map((r) => r.algorithm)).size,
        algoGaps,
      };
    }).sort((a, b) => a.problem.localeCompare(b.problem));

    return { totalExperiments, totalTimeMs, successRate, algorithmStats, problemStats, byAlgorithm, byProblem };
  }, [results, problems]);

  // ---- Chart Data ----
  const gapChartData = getAnalytics()?.algorithmStats
    .filter((s) => s.avgGap !== null)
    .map((s, i) => ({
      algorithm: s.displayName.length > 20 ? s.displayName.substring(0, 20) + "..." : s.displayName,
      gap: Number(s.avgGap!.toFixed(2)),
      fill: CHART_COLORS[i % CHART_COLORS.length],
    }));

  const timeChartData = getAnalytics()?.algorithmStats
    .map((s, i) => ({
      algorithm: s.displayName.length > 20 ? s.displayName.substring(0, 20) + "..." : s.displayName,
      time: Number(s.avgTime.toFixed(1)),
      fill: CHART_COLORS[i % CHART_COLORS.length],
    }));

  // Radar chart data: compare algorithms on multiple dimensions
  const radarData = useMemo(() => {
    const analytics = getAnalytics();
    if (!analytics || analytics.algorithmStats.length < 2) return null;

    const stats = analytics.algorithmStats;
    const maxGap = Math.max(...stats.map((s) => s.avgGap ?? 0));
    const maxTime = Math.max(...stats.map((s) => s.avgTime));
    const maxStdDev = Math.max(...stats.map((s) => s.gapStdDev));

    // Dimensions: Quality (inverted gap), Speed (inverted time), Consistency (inverted stddev), Coverage
    const dimensions = [t('radarChart.quality'), t('radarChart.speed'), t('radarChart.consistency'), t('radarChart.coverage')];

    return {
      dimensions,
      algorithms: stats.slice(0, 6).map((s, i) => ({
        name: s.displayName.length > 15 ? s.displayName.substring(0, 15) + "..." : s.displayName,
        color: CHART_COLOR_VALUES[i % CHART_COLOR_VALUES.length],
        data: dimensions.map((_, di) => {
          switch (di) {
            case 0: return maxGap > 0 ? Number(((1 - (s.avgGap ?? maxGap) / maxGap) * 100).toFixed(1)) : 50;
            case 1: return maxTime > 0 ? Number(((1 - s.avgTime / maxTime) * 100).toFixed(1)) : 50;
            case 2: return maxStdDev > 0 ? Number(((1 - s.gapStdDev / maxStdDev) * 100).toFixed(1)) : 50;
            case 3: return Number(((s.count / (analytics.totalExperiments / stats.length)) * 100).toFixed(1));
            default: return 0;
          }
        }),
      })),
    };
  }, [results, getAnalytics]);

  const radarChartData = useMemo(() => {
    if (!radarData) return [];
    return radarData.dimensions.map((dim, i) => {
      const point: Record<string, string | number> = { dimension: dim };
      radarData.algorithms.forEach((algo) => {
        point[algo.name] = algo.data[i];
      });
      return point;
    });
  }, [radarData]);

  // Scatter chart data
  const scatterData = useMemo(() => {
    const analytics = getAnalytics();
    if (!analytics) return [];
    return analytics.algorithmStats.map((s, i) => ({
      x: Number(s.avgTime.toFixed(1)),
      y: s.avgGap !== null ? Number(s.avgGap.toFixed(2)) : 0,
      z: s.count,
      name: s.displayName.length > 20 ? s.displayName.substring(0, 20) + "..." : s.displayName,
      fill: CHART_COLOR_VALUES[i % CHART_COLOR_VALUES.length],
    }));
  }, [results, getAnalytics]);

  // Heatmap data
  const heatmapData = useMemo(() => {
    const analytics = getAnalytics();
    if (!analytics) return null;
    const algos = analytics.algorithmStats.map((s) => s.algorithm);
    const probs = analytics.problemStats.map((p) => p.problem);
    const matrix: { algo: string; prob: string; gap: number | null; displayName: string }[] = [];
    for (const algo of algos) {
      for (const prob of probs) {
        const resList = analytics.byAlgorithm.get(algo) || [];
        const probRes = resList.filter((r) => r.problem === prob);
        const gaps = probRes.filter((r) => r.gap_percent !== null).map((r) => r.gap_percent!);
        const avgGap = gaps.length > 0 ? gaps.reduce((s, g) => s + g, 0) / gaps.length : null;
        matrix.push({ algo, prob, gap: avgGap, displayName: ALGORITHM_DISPLAY_NAMES[algo] || algo });
      }
    }
    return { algos, probs, matrix };
  }, [results, getAnalytics]);

  const totalExperiments = selectedAlgorithms.size * selectedProblems.size * nRuns;

  const scrollToBenchmark = () => {
    benchmarkRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // ============================================================
  // Render
  // ============================================================

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Inject animation styles */}
      <style dangerouslySetInnerHTML={{ __html: ANIMATION_STYLES }} />

      {/* ============ HEADER ============ */}
      <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-2.5">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-teal-500 to-emerald-600 flex items-center justify-center shadow-md shadow-teal-500/20 transition-transform duration-300 hover:scale-110 active:scale-95">
                <Route className="h-4 w-4 text-white" />
              </div>
              <div className="flex flex-col">
                <span className="text-base font-bold leading-tight tracking-tight">UniRide</span>
                <span className="text-[9px] uppercase tracking-[0.15em] text-muted-foreground font-semibold leading-tight">Benchmark Suite</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* AI Advisor Button */}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleGetAdvice}
                      disabled={selectedProblems.size === 0 || selectedAlgorithms.size === 0}
                      className="h-7 px-2.5 text-[11px] gap-1.5 transition-all duration-300 hover:bg-teal-500/10 hover:text-teal-600"
                    >
                      <Bot className="h-3.5 w-3.5" />
                      <span className="hidden sm:inline">{t('advisor.buttonLabel')}</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom">
                    <p className="text-xs">{t('advisor.tooltip')}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              {isDemoMode && (
                <Badge variant="outline" className="bg-amber-500/10 text-amber-700 border-amber-500/30 text-[10px] px-2 transition-all duration-300 hover:bg-amber-500/20">
                  <FlaskConical className="h-3 w-3 mr-1" />
                  {t('hero.demoMode')}
                </Badge>
              )}
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border bg-muted/50 transition-all duration-300">
                {isApiOnline === null ? (
                  <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                ) : isApiOnline ? (
                  <Wifi className="h-3 w-3 text-emerald-500" />
                ) : (
                  <WifiOff className="h-3 w-3 text-red-500" />
                )}
                <span className={`text-[10px] font-medium ${isApiOnline === null ? "text-muted-foreground" : isApiOnline ? "text-emerald-600" : "text-red-600"}`}>
                  {isApiOnline === null ? tc('loading') : isApiOnline ? t('hero.apiOnline') : t('hero.apiOffline')}
                </span>
              </div>
              {/* Dark Mode Toggle */}
              <button
                onClick={toggleDarkMode}
                className="h-7 w-7 rounded-lg border bg-muted/50 flex items-center justify-center transition-all duration-300 hover:bg-muted hover:scale-110 active:scale-95"
                aria-label={isDark ? t('hero.lightMode') : t('hero.darkMode')}
              >
                {isDark ? <Sun className="h-3.5 w-3.5 text-amber-500" /> : <Moon className="h-3.5 w-3.5 text-slate-600" />}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* ============ AI ADVISOR PANEL ============ */}
      {showAdvisor && (
        <div className="fixed right-4 top-16 z-50 w-[380px] max-w-[calc(100vw-2rem)] animate-slide-in-right">
          <Card className="shadow-xl border-l-4 border-l-teal-500 bg-background/95 backdrop-blur-md">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-teal-500 to-emerald-600 flex items-center justify-center animate-pulse-glow">
                    <Bot className="h-3.5 w-3.5 text-white" />
                  </div>
                  <div>
                    <CardTitle className="text-xs">{t('advisor.title')}</CardTitle>
                    <CardDescription className="text-[9px]">{t('advisor.description')}</CardDescription>
                  </div>
                </div>
                <button onClick={() => setShowAdvisor(false)} className="h-6 w-6 rounded-md hover:bg-muted flex items-center justify-center transition-colors">
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Goal Selector */}
              <div className="flex gap-1.5">
                {[
                  { key: "quality", label: t('advisor.goalQuality'), icon: Trophy, color: "data-[state=active]:bg-emerald-500/10 data-[state=active]:text-emerald-700" },
                  { key: "balanced", label: t('advisor.goalBalanced'), icon: Gauge, color: "data-[state=active]:bg-teal-500/10 data-[state=active]:text-teal-700" },
                  { key: "speed", label: t('advisor.goalSpeed'), icon: Zap, color: "data-[state=active]:bg-amber-500/10 data-[state=active]:text-amber-700" },
                ].map((g) => (
                  <button
                    key={g.key}
                    onClick={() => setAdvisorGoal(g.key)}
                    className={`flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-md text-[10px] font-medium border transition-all duration-200 ${
                      advisorGoal === g.key
                        ? g.color + " border-current/30"
                        : "border-transparent hover:bg-muted/50"
                    }`}
                  >
                    <g.icon className="h-3 w-3" />
                    {g.label}
                  </button>
                ))}
              </div>

              {/* Advice Display */}
              {advisorLoading ? (
                <div className="flex items-center gap-2 py-6 justify-center">
                  <Loader2 className="h-4 w-4 animate-spin text-teal-500" />
                  <span className="text-xs text-muted-foreground">{t('advisor.analyzing')}</span>
                </div>
              ) : advisorAdvice ? (
                <ScrollArea className="max-h-[300px]">
                  <div className="text-xs leading-relaxed whitespace-pre-wrap text-muted-foreground prose prose-xs prose-teal dark:prose-invert max-w-none">
                    {advisorAdvice}
                  </div>
                </ScrollArea>
              ) : (
                <div className="text-center py-4">
                  <Lightbulb className="h-6 w-6 mx-auto text-amber-500 mb-2" />
                  <p className="text-[11px] text-muted-foreground">{t('advisor.emptyState')}</p>
                </div>
              )}

              {/* Action Button */}
              <Button
                size="sm"
                onClick={handleGetAdvice}
                disabled={advisorLoading || selectedProblems.size === 0 || selectedAlgorithms.size === 0}
                className="w-full h-8 text-[11px] bg-gradient-to-r from-teal-500 to-emerald-500 hover:from-teal-600 hover:to-emerald-600 text-white shadow-md transition-all duration-300 hover:shadow-lg"
              >
                {advisorLoading ? (
                  <><Loader2 className="mr-1.5 h-3 w-3 animate-spin" /> {t('advisor.analyzing')}</>
                ) : (
                  <><Send className="mr-1.5 h-3 w-3" /> {t('advisor.getAdvice', { count: selectedAlgorithms.size })}</>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ============ HERO SECTION ============ */}
      {showHero && (
        <section className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-teal-900 animate-gradient-move">
          {/* Animated dot pattern overlay */}
          <div className="absolute inset-0 animate-dot-pulse" style={{
            backgroundImage: `radial-gradient(circle, rgba(255,255,255,0.15) 1px, transparent 1px)`,
            backgroundSize: "32px 32px",
          }} />

          {/* Gradient overlay */}
          <div className="absolute inset-0 bg-gradient-to-r from-teal-600/10 to-emerald-600/5" />

          {/* Animated gradient orbs */}
          <div className="absolute top-1/4 left-1/4 w-64 h-64 rounded-full bg-teal-500/10 blur-3xl animate-breathe" />
          <div className="absolute bottom-1/4 right-1/4 w-48 h-48 rounded-full bg-emerald-500/10 blur-3xl animate-breathe" style={{ animationDelay: "2s" }} />
          <div className="absolute top-1/2 left-1/2 w-32 h-32 rounded-full bg-amber-500/5 blur-2xl animate-float" />

          {/* Floating elements */}
          <div className="absolute top-10 left-[10%] animate-float opacity-20">
            <Route className="h-8 w-8 text-teal-300" />
          </div>
          <div className="absolute top-20 right-[15%] animate-float-delay opacity-15">
            <Cpu className="h-6 w-6 text-emerald-300" />
          </div>
          <div className="absolute bottom-16 left-[25%] animate-float opacity-10">
            <Trophy className="h-10 w-10 text-amber-300" />
          </div>
          <div className="absolute bottom-10 right-[20%] animate-float-delay opacity-15">
            <GitBranch className="h-7 w-7 text-purple-300" />
          </div>

          <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
            <div className="text-center mb-10 animate-fade-in-up">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 border border-white/10 mb-6 backdrop-blur-sm">
                <Sparkles className="h-3.5 w-3.5 text-teal-300" />
                <span className="text-xs text-teal-200 font-medium">{t('hero.badge')}</span>
              </div>
              <h1 className="text-3xl sm:text-5xl font-bold text-white tracking-tight mb-4">
                UniRide{" "}
                <span className="bg-gradient-to-r from-teal-300 via-emerald-300 to-teal-200 bg-clip-text text-transparent">
                  TSPLIB Benchmark
                </span>{" "}
                Suite
              </h1>
              <p className="text-slate-300 text-sm sm:text-base max-w-2xl mx-auto leading-relaxed">
                {t('hero.description')}
              </p>
            </div>

            {/* Stat Cards - Glassmorphism */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-10">
              {[
                { icon: Cpu, label: t('hero.statAlgorithms'), value: "14+", color: "from-teal-500/20 to-teal-600/10", iconColor: "text-teal-400", delay: "delay-100" },
                { icon: ScrollText, label: t('hero.statProblems'), value: "50+", color: "from-emerald-500/20 to-emerald-600/10", iconColor: "text-emerald-400", delay: "delay-200" },
                { icon: GitBranch, label: t('hero.statPipelines'), value: "3", color: "from-amber-500/20 to-amber-600/10", iconColor: "text-amber-400", delay: "delay-300" },
                { icon: Trophy, label: t('hero.statDimacsWinner'), value: "PyVRP", color: "from-purple-500/20 to-purple-600/10", iconColor: "text-purple-400", delay: "delay-400" },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className={`relative group p-4 sm:p-5 rounded-xl bg-gradient-to-br ${stat.color} backdrop-blur-lg bg-white/10 border-white/20 border border-white/10 hover:border-white/25 transition-all duration-300 hover:scale-[1.03] active:scale-[0.98] animate-slide-up ${stat.delay} cursor-default`}
                >
                  <stat.icon className={`h-5 w-5 ${stat.iconColor} mb-2 transition-transform duration-300 group-hover:scale-110`} />
                  <p className="text-xl sm:text-2xl font-bold text-white bg-gradient-to-r from-white to-white/90 bg-clip-text">{stat.value}</p>
                  <p className="text-[10px] sm:text-xs text-slate-400 font-medium">{stat.label}</p>
                </div>
              ))}
            </div>

            {/* Pipeline Cards - Glassmorphism */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
              {[
                {
                  pipeline: "A", title: "Cluster-First, Route-Second",
                  subtitle: t('hero.pipelineASubtitle'),
                  description: t('hero.pipelineADesc'),
                  algorithms: ["GA", "PSO", "GWO", "HHO"],
                  gradient: "from-teal-500/15 to-emerald-500/10",
                  border: "border-teal-500/20 hover:border-teal-400/40",
                  textColor: "text-teal-300",
                },
                {
                  pipeline: "B", title: "Route-First, Cluster-Second",
                  subtitle: "Giant Tour + Optimal Split",
                  description: t('hero.pipelineBDesc'),
                  algorithms: ["GA-Split ★", "PSO-Split", "GWO-Split", "HHO-Split"],
                  gradient: "from-amber-500/15 to-orange-500/10",
                  border: "border-amber-500/20 hover:border-amber-400/40",
                  textColor: "text-amber-300",
                  recommended: true,
                },
                {
                  pipeline: "H", title: t('hero.pipelineHTitle'),
                  subtitle: t('hero.pipelineHSubtitle'),
                  description: t('hero.pipelineHDesc'),
                  algorithms: ["OR-Tools", "PyVRP 🏆", "VROOM ⚡"],
                  gradient: "from-purple-500/15 to-pink-500/10",
                  border: "border-purple-500/20 hover:border-purple-400/40",
                  textColor: "text-purple-300",
                },
              ].map((card) => (
                <div
                  key={card.pipeline}
                  className={`relative p-5 rounded-xl bg-gradient-to-br ${card.gradient} backdrop-blur-lg bg-white/10 border-white/20 border ${card.border} transition-all duration-300 hover:scale-[1.03] active:scale-[0.98] animate-fade-in-up`}
                >
                  {card.recommended && (
                    <Badge className="absolute -top-2 right-4 bg-emerald-600 text-white text-[9px] px-2 shadow-lg">
                      {tc('recommended')}
                    </Badge>
                  )}
                  <div className="flex items-center gap-2 mb-3">
                    <div className="h-7 w-7 rounded-lg bg-white/10 flex items-center justify-center">
                      <span className="text-xs font-bold text-white">{card.pipeline}</span>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-white">{card.title}</p>
                      <p className="text-[10px] text-slate-400">{card.subtitle}</p>
                    </div>
                  </div>
                  <p className="text-xs text-slate-300 mb-3">{card.description}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {card.algorithms.map((alg) => (
                      <span key={alg} className={`text-[10px] px-2 py-0.5 rounded-full bg-white/10 ${card.textColor} font-medium transition-all duration-200 hover:bg-white/20`}>
                        {alg}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* CTA */}
            <div className="text-center animate-fade-in-up delay-500">
              <Button
                size="lg"
                onClick={scrollToBenchmark}
                className="bg-gradient-to-r from-teal-500 to-emerald-500 hover:from-teal-600 hover:to-emerald-600 text-white shadow-lg shadow-teal-500/25 h-12 px-8 text-base font-semibold transition-all duration-300 hover:scale-[1.03] active:scale-[0.98] hover:shadow-xl hover:shadow-teal-500/30"
              >
                <Play className="mr-2 h-5 w-5" />
                {t('hero.cta')}
                <ArrowDown className="ml-2 h-4 w-4" />
              </Button>
              <button
                onClick={() => setShowHero(false)}
                className="block mx-auto mt-4 text-[11px] text-slate-400 hover:text-slate-300 transition-colors duration-200 underline underline-offset-2"
              >
                {t('hero.hide')}
              </button>
            </div>
          </div>
        </section>
      )}

      {/* Show hero restore button */}
      {!showHero && (
        <button
          onClick={() => setShowHero(true)}
          className="w-full py-1.5 text-[10px] text-muted-foreground hover:text-foreground bg-muted/30 hover:bg-muted/50 transition-all duration-200 flex items-center justify-center gap-1"
        >
          <ChevronUp className="h-3 w-3" /> {t('hero.show')}
        </button>
      )}

      {/* ============ API OFFLINE BANNER ============ */}
      {isApiOnline === false && !isDemoMode && (
        <div className="bg-amber-500/10 border-b border-amber-500/20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2.5">
            <Alert className="border-0 bg-transparent p-0 shadow-none">
              <AlertCircle className="h-4 w-4 text-amber-600" />
              <AlertTitle className="text-sm text-amber-800">{t('hero.demoBannerTitle')}</AlertTitle>
              <AlertDescription className="text-xs text-amber-700">
                {t('hero.demoBannerDesc')}
              </AlertDescription>
            </Alert>
          </div>
        </div>
      )}

      {/* ============ MAIN CONTENT ============ */}
      <main ref={benchmarkRef} className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Section Header with decorative element */}
        <div className="mb-6 relative">
          <div className="absolute -left-4 top-0 bottom-0 w-1 rounded-full bg-gradient-to-b from-teal-500 to-emerald-500" />
          <div className="flex items-center justify-between pl-4">
            <div>
              <h2 className="text-xl sm:text-2xl font-bold tracking-tight flex items-center gap-2.5">
                <FlaskConical className="h-6 w-6 text-primary" />
                {t('problemPanel.title')}
              </h2>
              <p className="text-muted-foreground text-sm mt-1">
                {t('problemPanel.description')}
              </p>
            </div>
            {/* Quick Stats Chips */}
            <div className="hidden lg:flex items-center gap-2">
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-teal-500/10 border border-teal-500/20 text-teal-700 dark:text-teal-400">
                <Cpu className="h-3.5 w-3.5" />
                <span className="text-xs font-semibold">{selectedAlgorithms.size}</span>
                <span className="text-[10px]">{t('problemPanel.algorithmChip')}</span>
              </div>
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-400">
                <ScrollText className="h-3.5 w-3.5" />
                <span className="text-xs font-semibold">{selectedProblems.size}</span>
                <span className="text-[10px]">{t('problemPanel.problemChip')}</span>
              </div>
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-700 dark:text-amber-400">
                <Zap className="h-3.5 w-3.5" />
                <span className="text-xs font-semibold">{totalExperiments}</span>
                <span className="text-[10px]">{t('problemPanel.experimentChip')}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Algorithm Info Dialog */}
        <Dialog open={selectedAlgoInfo !== null} onOpenChange={(open) => !open && setSelectedAlgoInfo(null)}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Info className="h-4 w-4 text-primary" />
                {selectedAlgoInfo ? ALGORITHM_DISPLAY_NAMES[selectedAlgoInfo] || selectedAlgoInfo : ""}
              </DialogTitle>
              <DialogDescription className="text-xs">
                {t('algorithmPanel.infoDialogDesc')}
              </DialogDescription>
            </DialogHeader>
            {selectedAlgoInfo && (
              <div className="space-y-3">
                <div className="p-3 rounded-lg bg-muted/50 border">
                  <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">{t('algorithmPanel.description')}</p>
                  <p className="text-xs">{ALGORITHM_DESCRIPTIONS[selectedAlgoInfo] || t('algorithmPanel.noDescription')}</p>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-2.5 rounded-lg bg-muted/50 border">
                    <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">{t('algorithmPanel.complexity')}</p>
                    <p className="text-xs font-mono">{ALGORITHM_COMPLEXITY[selectedAlgoInfo] || "N/A"}</p>
                  </div>
                  <div className="p-2.5 rounded-lg bg-muted/50 border">
                    <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">{t('algorithmPanel.pipeline')}</p>
                    <p className="text-xs">{(() => {
                      const algo = ALGORITHM_OPTIONS_GROUPED.flatMap((g: any) => g.algorithms).find((a: any) => a.key === selectedAlgoInfo);
                      return algo?.pipeline === "A" ? "Cluster-First, Route-Second" : algo?.pipeline === "B" ? "Route-First, Cluster-Second" : algo?.pipeline === "holistic" ? t('algorithmPanel.holisticSolver') : t('algorithmPanel.heuristic');
                    })()}</p>
                  </div>
                </div>
                {ALGORITHM_OPTIONS_GROUPED.flatMap((g: any) => g.algorithms).find((a: any) => a.key === selectedAlgoInfo)?.recommended && (
                  <div className="flex items-center gap-2 p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                    <Trophy className="h-4 w-4 text-emerald-600" />
                    <p className="text-xs text-emerald-700 dark:text-emerald-400 font-medium">{t('algorithmPanel.recommendedText')}</p>
                  </div>
                )}
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Main Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3 mb-6 h-10">
            <TabsTrigger value="config" className="gap-1.5 text-xs sm:text-sm transition-all duration-200">
              <Target className="h-3.5 w-3.5 hidden sm:block" />
              {t('problemPanel.tabConfig')}
            </TabsTrigger>
            <TabsTrigger value="execution" className="gap-1.5 text-xs sm:text-sm transition-all duration-200 data-[disabled]:opacity-40" data-disabled={!runId}>
              <Activity className="h-3.5 w-3.5 hidden sm:block" />
              {t('runPanel.tabExecution')}
              {runStatus?.status === "running" && (
                <span className="h-2 w-2 rounded-full bg-sky-500 animate-pulse" />
              )}
            </TabsTrigger>
            <TabsTrigger value="results" className="gap-1.5 text-xs sm:text-sm transition-all duration-200 data-[disabled]:opacity-40" data-disabled={!results}>
              <BarChart3 className="h-3.5 w-3.5 hidden sm:block" />
              {t('results.tabResults')}
            </TabsTrigger>
          </TabsList>

          {/* ============================================ */}
          {/* TAB 1: CONFIGURATION */}
          {/* ============================================ */}
          <TabsContent value="config" className="mt-0">
            {/* Run History Section */}
            <div className="mb-5">
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="flex items-center gap-2 text-sm font-semibold hover:text-primary transition-colors duration-200 group"
              >
                <History className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
                {t('runPanel.runHistory')}
                <Badge variant="secondary" className="text-[9px] h-4 px-1.5">{runHistory.length}</Badge>
                <ChevronRight className={`h-3.5 w-3.5 text-muted-foreground transition-transform duration-200 ${showHistory ? "rotate-90" : ""}`} />
              </button>
              {showHistory && (
                <div className="mt-3 animate-fade-in">
                  {runHistory.length === 0 ? (
                    <p className="text-xs text-muted-foreground py-3 text-center">{t('runPanel.noHistory')}</p>
                  ) : (
                    <div className="space-y-2 max-h-64 overflow-y-auto pr-1" style={{ scrollbarWidth: "thin" }}>
                      {runHistory.map((entry, i) => (
                        <div
                          key={entry.run_id}
                          className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-accent/50 transition-all duration-200 cursor-pointer hover:scale-[1.01] active:scale-[0.99] group"
                          onClick={() => handleLoadHistoryEntry(entry)}
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-mono text-[10px] text-muted-foreground">{entry.run_id.slice(0, 20)}</span>
                              <span className="text-[9px] text-muted-foreground">{new Date(entry.date).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}</span>
                            </div>
                            <div className="flex items-center gap-3 text-[10px]">
                              <span className="text-teal-600">{t('runPanel.historyAlgoCount', { count: entry.algorithmCount })}</span>
                              <span className="text-emerald-600">{t('runPanel.historyProblemCount', { count: entry.problemCount })}</span>
                              <span className="text-amber-600">{t('runPanel.historyExperimentCount', { count: entry.experimentCount })}</span>
                              {entry.bestGap !== null && (
                                <span className="text-primary font-medium">{t('runPanel.historyBestGap', { gap: entry.bestGap })}</span>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] text-muted-foreground group-hover:text-primary transition-colors truncate max-w-[120px]">
                              {entry.bestAlgorithm}
                            </span>
                            <ChevronRight className="h-3 w-3 text-muted-foreground group-hover:text-primary transition-all group-hover:translate-x-0.5" />
                          </div>
                        </div>
                      ))}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleClearHistory}
                        className="w-full h-7 text-[10px] text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-3 w-3 mr-1" /> {t('runPanel.clearHistory')}
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Problem Selection */}
              <Card className="lg:col-span-2 border shadow-sm transition-all duration-300 hover:shadow-md">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="bg-gradient-to-br from-teal-500/15 to-emerald-500/10 p-2 rounded-lg transition-transform duration-300 hover:scale-110">
                        <ScrollText className="h-4 w-4 text-teal-600" />
                      </div>
                      <div>
                        <CardTitle className="text-sm">{t('problemPanel.selectProblems')}</CardTitle>
                        <CardDescription className="text-[11px] mt-0.5">
                          {t('problemPanel.selectProblemsDesc')}
                        </CardDescription>
                      </div>
                    </div>
                    <Badge variant="outline" className="font-mono text-[10px]">{t('problemPanel.nSelected', { n: selectedProblems.size })}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {["all", "small", "medium", "large"].map((cat) => (
                        <Button
                          key={cat}
                          size="sm"
                          variant={problemCategoryFilter === cat ? "default" : "outline"}
                          onClick={() => setProblemCategoryFilter(cat)}
                          className="h-7 text-[11px] px-2.5 transition-all duration-200 hover:scale-[1.03] active:scale-[0.98]"
                        >
                          {cat === "all" ? tc('all') : getCategoryLabel(cat, t)}
                        </Button>
                      ))}
                    </div>
                    <div className="flex items-center gap-2 ml-auto w-full sm:w-auto">
                      <Input
                        placeholder={t('problemPanel.searchPlaceholder')}
                        value={problemSearch}
                        onChange={(e) => setProblemSearch(e.target.value)}
                        className="h-7 text-[11px] w-full sm:w-36 transition-all duration-200 focus:ring-2 focus:ring-teal-500/30"
                      />
                      <Button size="sm" variant="ghost" onClick={selectAllProblems} className="h-7 text-[10px] px-2 transition-all duration-200 hover:scale-[1.03]">{tc('selectAll')}</Button>
                      <Button size="sm" variant="ghost" onClick={deselectAllProblems} className="h-7 text-[10px] px-2 transition-all duration-200 hover:scale-[1.03]">{tc('deselectAll')}</Button>
                    </div>
                  </div>

                  {/* Problems table / Skeleton loading */}
                  {problemsLoading ? (
                    <div className="space-y-2">
                      {Array.from({ length: 6 }).map((_, i) => (
                        <div key={i} className="flex items-center gap-3 p-2">
                          <Skeleton className="h-4 w-4 rounded" />
                          <Skeleton className="h-4 w-24" />
                          <Skeleton className="h-4 w-12" />
                          <Skeleton className="h-4 w-16" />
                          <Skeleton className="h-5 w-12 rounded-full" />
                        </div>
                      ))}
                    </div>
                  ) : filteredProblems.length === 0 ? (
                    <Alert>
                      <AlertCircle className="h-4 w-4" />
                      <AlertTitle>{t('problemPanel.notFound')}</AlertTitle>
                      <AlertDescription>{t('problemPanel.notFoundDesc')}</AlertDescription>
                    </Alert>
                  ) : (
                    <div className="max-h-[400px] overflow-y-auto rounded-lg border" style={{ scrollbarWidth: "thin" }}>
                      <Table>
                        <TableHeader>
                          <TableRow className="bg-muted/50 hover:bg-muted/50 sticky top-0">
                            <TableHead className="w-10" />
                            <TableHead className="text-[11px]">{t('problemPanel.tableProblem')}</TableHead>
                            <TableHead className="text-[11px] text-center">{t('problemPanel.tableDimension')}</TableHead>
                            <TableHead className="text-[11px] text-center hidden sm:table-cell">{t('problemPanel.tableOptimal')}</TableHead>
                            <TableHead className="text-[11px] text-center">{t('problemPanel.tableCategory')}</TableHead>
                            <TableHead className="text-[11px] text-center hidden md:table-cell">{t('problemPanel.tableType')}</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {filteredProblems.map((p, i) => (
                            <TableRow
                              key={p.name}
                              className={`cursor-pointer transition-all duration-200 ${selectedProblems.has(p.name) ? "bg-teal-500/5 hover:bg-teal-500/10" : i % 2 === 0 ? "" : "bg-muted/20"} hover:scale-[1.003] active:scale-[0.998]`}
                              onClick={() => toggleProblem(p.name)}
                            >
                              <TableCell>
                                <Checkbox checked={selectedProblems.has(p.name)} onCheckedChange={() => toggleProblem(p.name)} className="transition-all duration-200" />
                              </TableCell>
                              <TableCell className="font-mono font-medium text-xs">{p.name}</TableCell>
                              <TableCell className="text-center font-mono text-xs tabular-nums">{p.dimension}</TableCell>
                              <TableCell className="text-center font-mono text-[11px] tabular-nums hidden sm:table-cell">
                                {p.optimal !== null ? p.optimal.toLocaleString() : "-"}
                              </TableCell>
                              <TableCell className="text-center">
                                <Badge variant={getCategoryBadgeVariant(p.category)} className="text-[9px] px-1.5 py-0 font-medium">
                                  {getCategoryLabel(p.category, t)}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-center text-[10px] text-muted-foreground font-mono hidden md:table-cell">
                                {p.problem_type || p.edge_weight_type || "TSP"}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}

                  {problems.length > 0 && (
                    <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
                      <span>{t('problemPanel.totalProblems', { count: problems.length })}</span>
                      <span>{t('problemPanel.smallCount', { count: problems.filter(p => p.category === "small").length })}</span>
                      <span>{t('problemPanel.mediumCount', { count: problems.filter(p => p.category === "medium").length })}</span>
                      <span>{t('problemPanel.largeCount', { count: problems.filter(p => p.category === "large").length })}</span>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Right Column */}
              <div className="space-y-5">
                {/* Algorithm Selection */}
                <Card className="border shadow-sm transition-all duration-300 hover:shadow-md">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="bg-gradient-to-br from-amber-500/15 to-orange-500/10 p-2 rounded-lg transition-transform duration-300 hover:scale-110">
                          <Cpu className="h-4 w-4 text-amber-600" />
                        </div>
                        <div>
                          <CardTitle className="text-sm">{t('algorithmPanel.selectAlgorithms')}</CardTitle>
                          <CardDescription className="text-[11px] mt-0.5">{t('algorithmPanel.selectAlgorithmsDesc')}</CardDescription>
                        </div>
                      </div>
                      <Badge variant="outline" className="font-mono text-[10px]">{t('algorithmPanel.nSelected', { n: selectedAlgorithms.size })}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex gap-1 flex-wrap">
                      <Button size="sm" variant="ghost" onClick={selectAllAlgorithms} className="h-6 text-[10px] px-2 transition-all duration-200 hover:scale-[1.03]">{tc('selectAll')}</Button>
                      <Button size="sm" variant="ghost" onClick={selectRecommendedAlgorithms} className="h-6 text-[10px] px-2 transition-all duration-200 hover:scale-[1.03]">{t('algorithmPanel.selectRecommended')}</Button>
                      <Button size="sm" variant="ghost" onClick={() => setSelectedAlgorithms(new Set())} className="h-6 text-[10px] px-2 transition-all duration-200 hover:scale-[1.03]">{tc('deselectAll')}</Button>
                    </div>

                    {problemsLoading ? (
                      <div className="space-y-2">
                        {Array.from({ length: 4 }).map((_, i) => (
                          <Skeleton key={i} className="h-10 w-full rounded-lg" />
                        ))}
                      </div>
                    ) : (
                      <div className="max-h-[340px] overflow-y-auto space-y-2 pr-1" style={{ scrollbarWidth: "thin" }}>
                        {ALGORITHM_OPTIONS_GROUPED.map((group) => {
                          const isExpanded = expandedGroups.has(group.category);
                          const pipelineType = group.algorithms[0]?.pipeline || "heuristic";
                          return (
                            <div key={group.category} className={`rounded-lg border ${getPipelineBorder(pipelineType)} transition-all duration-200 overflow-hidden hover:shadow-sm`}>
                              <button
                                onClick={() => toggleGroup(group.category)}
                                className="w-full flex items-center gap-2 px-3 py-2 hover:bg-muted/30 transition-colors duration-200"
                              >
                                {getPipelineIcon(pipelineType)}
                                <div className="flex-1 text-left min-w-0">
                                  <p className="text-[10px] font-semibold text-muted-foreground truncate">{group.category}</p>
                                </div>
                                <ChevronRight className={`h-3 w-3 text-muted-foreground transition-transform duration-200 ${isExpanded ? "rotate-90" : ""}`} />
                              </button>
                              {isExpanded && (
                                <div className="px-2 pb-2 space-y-0.5 animate-fade-in">
                                  {group.algorithms.map((alg) => (
                                    <label
                                      key={alg.key}
                                      className={`flex items-center gap-2 px-2.5 py-1.5 rounded-md cursor-pointer transition-all duration-200 hover:bg-muted/50 hover:scale-[1.01] active:scale-[0.99] ${selectedAlgorithms.has(alg.key) ? "bg-primary/5 ring-1 ring-primary/20" : ""}`}
                                    >
                                      <Checkbox
                                        checked={selectedAlgorithms.has(alg.key)}
                                        onCheckedChange={() => toggleAlgorithm(alg.key)}
                                        className="h-3.5 w-3.5"
                                      />
                                      <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-1.5 flex-wrap">
                                          <span className="text-[11px] font-medium truncate">{alg.label}</span>
                                          {alg.recommended && (
                                            <Badge className="text-[7px] px-1 py-0 h-3 bg-emerald-600 hover:bg-emerald-700 text-white">{tc('recommended')}</Badge>
                                          )}
                                          {"badge" in alg && alg.badge && (
                                            <Badge variant="secondary" className="text-[7px] px-1 py-0 h-3">{String(alg.badge)}</Badge>
                                          )}
                                        </div>
                                        <p className="text-[9px] text-muted-foreground truncate mt-0.5">
                                          {ALGORITHM_DESCRIPTIONS[alg.key] || alg.description}
                                        </p>
                                      </div>
                                      <button
                                        onClick={(e) => { e.stopPropagation(); setSelectedAlgoInfo(alg.key); }}
                                        className="shrink-0 h-5 w-5 rounded flex items-center justify-center hover:bg-muted/80 transition-all duration-200 hover:scale-110"
                                        title={t('algorithmPanel.details')}
                                      >
                                        <Info className="h-3 w-3 text-muted-foreground" />
                                      </button>
                                    </label>
                                  ))}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Settings */}
                <Card className="border shadow-sm transition-all duration-300 hover:shadow-md">
                  <CardHeader className="pb-3">
                    <div className="flex items-center gap-2.5">
                      <div className="bg-gradient-to-br from-slate-500/15 to-gray-500/10 p-2 rounded-lg transition-transform duration-300 hover:scale-110">
                        <Timer className="h-4 w-4 text-slate-600" />
                      </div>
                      <CardTitle className="text-sm">{t('settingsPanel.title')}</CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <Label htmlFor="n_runs" className="text-[11px]">{t('settingsPanel.runsLabel')}</Label>
                        <Input
                          id="n_runs"
                          type="number"
                          min={1}
                          max={100}
                          value={nRuns}
                          onChange={(e) => setNRuns(Math.max(1, parseInt(e.target.value) || 1))}
                          className="h-8 text-xs transition-all duration-200 focus:ring-2 focus:ring-teal-500/30"
                        />
                      </div>
                      <div className="space-y-1">
                        <Label htmlFor="seed" className="text-[11px]">{t('settingsPanel.seedLabel')}</Label>
                        <Input
                          id="seed"
                          type="number"
                          value={seed}
                          onChange={(e) => setSeed(parseInt(e.target.value) || 0)}
                          className="h-8 text-xs transition-all duration-200 focus:ring-2 focus:ring-teal-500/30"
                        />
                      </div>
                    </div>

                    <Separator />

                    {/* Experiment Summary */}
                    <div className="p-3 rounded-lg bg-gradient-to-br from-muted/60 to-muted/30 border space-y-2">
                      <p className="text-[11px] font-semibold flex items-center gap-1.5">
                        <Zap className="h-3 w-3 text-amber-500" />
                        {t('settingsPanel.experimentSummary')}
                      </p>
                      <div className="grid grid-cols-3 gap-2 text-center">
                        <div className="p-1.5 rounded-md bg-background/60 transition-all duration-200 hover:scale-[1.03]">
                          <p className="text-base font-bold bg-gradient-to-r from-teal-600 to-emerald-600 bg-clip-text text-transparent tabular-nums">{selectedAlgorithms.size}</p>
                          <p className="text-[9px] text-muted-foreground">{t('settingsPanel.summaryAlgorithms')}</p>
                        </div>
                        <div className="p-1.5 rounded-md bg-background/60 transition-all duration-200 hover:scale-[1.03]">
                          <p className="text-base font-bold bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent tabular-nums">{selectedProblems.size}</p>
                          <p className="text-[9px] text-muted-foreground">{t('settingsPanel.summaryProblems')}</p>
                        </div>
                        <div className="p-1.5 rounded-md bg-background/60 transition-all duration-200 hover:scale-[1.03]">
                          <p className="text-base font-bold bg-gradient-to-r from-amber-500 to-orange-500 bg-clip-text text-transparent tabular-nums">{nRuns}</p>
                          <p className="text-[9px] text-muted-foreground">{t('settingsPanel.summaryRuns')}</p>
                        </div>
                      </div>
                      <div className="text-center pt-1.5 border-t">
                        <p className="text-[11px] text-muted-foreground">
                          {t('settingsPanel.summaryTotal', { count: totalExperiments })}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Start Button */}
                <Button
                  size="lg"
                  className={`w-full h-11 text-sm font-semibold shadow-lg transition-all duration-300 hover:scale-[1.03] active:scale-[0.98] hover:shadow-xl ${
                    isDemoMode
                      ? "bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 shadow-amber-500/20 hover:shadow-amber-500/30"
                      : "bg-gradient-to-r from-teal-500 to-emerald-500 hover:from-teal-600 hover:to-emerald-600 shadow-teal-500/20 hover:shadow-teal-500/30"
                  } text-white`}
                  disabled={
                    isStarting ||
                    selectedProblems.size === 0 ||
                    selectedAlgorithms.size === 0 ||
                    (!isDemoMode && isApiOnline === false)
                  }
                  onClick={handleStartBenchmark}
                >
                  {isStarting ? (
                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> {t('runPanel.starting')}</>
                  ) : isDemoMode ? (
                    <><FlaskConical className="mr-2 h-4 w-4" /> {t('runPanel.demoStart', { count: totalExperiments })}</>
                  ) : (
                    <><Play className="mr-2 h-4 w-4" /> {t('runPanel.start')}</>
                  )}
                </Button>

                {isDemoMode && (
                  <p className="text-[10px] text-center text-muted-foreground">
                    {t('runPanel.demoNote')}
                  </p>
                )}
              </div>
            </div>
          </TabsContent>

          {/* ============================================ */}
          {/* TAB 2: EXECUTION */}
          {/* ============================================ */}
          <TabsContent value="execution" className="mt-0">
            {!runId && !runStatus ? (
              <Card className="border shadow-sm">
                <CardContent className="py-16 text-center">
                  <div className="mx-auto h-16 w-16 rounded-full bg-muted/50 flex items-center justify-center mb-4">
                    <FlaskConical className="h-8 w-8 text-muted-foreground" />
                  </div>
                  <h3 className="text-lg font-semibold mb-2">{t('runPanel.noRun')}</h3>
                  <p className="text-muted-foreground text-sm max-w-md mx-auto">
                    {t('runPanel.noRunDesc')}
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-5">
                <Card className="border shadow-sm border-l-4 border-l-sky-500">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="bg-gradient-to-br from-sky-500/15 to-blue-500/10 p-2 rounded-lg">
                          <Activity className="h-4 w-4 text-sky-600" />
                        </div>
                        <div>
                          <CardTitle className="text-sm">{t('runPanel.title')}</CardTitle>
                          <CardDescription className="text-[10px] font-mono mt-0.5">Run ID: {runId}</CardDescription>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {isDemoMode && (
                          <Badge variant="outline" className="bg-amber-500/10 text-amber-700 border-amber-500/30 text-[9px]">
                            Demo
                          </Badge>
                        )}
                        {runStatus && getStatusBadge(runStatus.status, tc)}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-5">
                    {runStatus ? (
                      <>
                        {/* Progress */}
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-muted-foreground">{t('runPanel.progress')}</span>
                            <span className="text-xl font-bold tabular-nums bg-gradient-to-r from-sky-600 to-blue-600 bg-clip-text text-transparent">{runStatus.progress_percent.toFixed(1)}%</span>
                          </div>
                          <Progress value={runStatus.progress_percent} className="h-2.5" />
                        </div>

                        {/* Stats Grid */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                          {[
                            { label: t('runPanel.statTotalExperiments'), value: runStatus.total_experiments, color: "border-l-teal-500", iconBg: "bg-teal-500/10", icon: Target },
                            { label: t('runPanel.statCompleted'), value: runStatus.completed_experiments, color: "border-l-emerald-500", iconBg: "bg-emerald-500/10", icon: CheckCircle2 },
                            { label: t('runPanel.statResultsCount'), value: runStatus.results_count, color: "border-l-amber-500", iconBg: "bg-amber-500/10", icon: BarChart3 },
                            { label: t('runPanel.statStartTime'), value: new Date(runStatus.start_time).toLocaleTimeString("tr-TR"), color: "border-l-sky-500", iconBg: "bg-sky-500/10", icon: Clock, isSmall: true },
                          ].map((stat) => (
                            <div key={stat.label} className={`p-3 rounded-lg bg-muted/40 border-l-4 ${stat.color} transition-all duration-200 hover:scale-[1.02]`}>
                              <div className="flex items-center gap-2 mb-1">
                                <div className={`${stat.iconBg} p-1 rounded`}>
                                  <stat.icon className="h-3 w-3" />
                                </div>
                                <p className="text-[9px] text-muted-foreground uppercase tracking-wider">{stat.label}</p>
                              </div>
                              <p className={`font-bold tabular-nums ${stat.isSmall ? "text-sm" : "text-lg"}`}>
                                {stat.value}
                              </p>
                            </div>
                          ))}
                        </div>

                        {/* Status Message */}
                        {runStatus.message && (
                          <div className="p-2.5 rounded-lg bg-muted/40 border">
                            <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-0.5">{t('runPanel.status')}</p>
                            <p className="font-mono text-[11px]">{runStatus.message}</p>
                          </div>
                        )}

                        {/* ETA */}
                        {runStatus.status === "running" && runStatus.progress_percent > 0 && runStatus.progress_percent < 100 && runStatus.start_time && (
                          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                            <Clock className="h-3.5 w-3.5" />
                            <span>
                              {t('runPanel.elapsedTime', { seconds: elapsedSeconds(runStatus.start_time) })}
                              {runStatus.progress_percent > 5 && (
                                <> &middot; {t('runPanel.estimatedTime', { seconds: estimateRemainingSeconds(runStatus.start_time, runStatus.progress_percent) })}</>
                              )}
                            </span>
                          </div>
                        )}

                        {/* Actions */}
                        <div className="flex gap-3 pt-1">
                          {runStatus.status === "running" && (
                            <Button variant="destructive" onClick={handleStopBenchmark} disabled={isStopping} size="sm" className="transition-all duration-200 hover:scale-[1.03] active:scale-[0.98]">
                              {isStopping ? <><Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> {t('runPanel.stopping')}</> : <><Square className="mr-1.5 h-3.5 w-3.5" /> {t('runPanel.stop')}</>}
                            </Button>
                          )}
                          {["completed", "stopped", "failed"].includes(runStatus.status) && (
                            <>
                              <Button onClick={handleManualFetchResults} disabled={resultsLoading} size="sm" className="transition-all duration-200 hover:scale-[1.03] active:scale-[0.98]">
                                {resultsLoading ? <><Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> {tc('loading')}</> : <><BarChart3 className="mr-1.5 h-3.5 w-3.5" /> {t('runPanel.viewResults')}</>}
                              </Button>
                              <Button variant="outline" onClick={() => setActiveTab("config")} size="sm" className="transition-all duration-200 hover:scale-[1.03] active:scale-[0.98]">
                                <RefreshCw className="mr-1.5 h-3.5 w-3.5" /> {t('runPanel.newRun')}
                              </Button>
                            </>
                          )}
                        </div>
                      </>
                    ) : (
                      <div className="flex items-center justify-center py-10">
                        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                        <span className="ml-2 text-sm text-muted-foreground">{t('runPanel.statusLoading')}</span>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            )}
          </TabsContent>

          {/* ============================================ */}
          {/* TAB 3: RESULTS */}
          {/* ============================================ */}
          <TabsContent value="results" className="mt-0">
            {resultsLoading ? (
              <Card className="border shadow-sm">
                <CardContent className="py-16 text-center">
                  <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary mb-4" />
                  <p className="text-sm text-muted-foreground">{t('results.loading')}</p>
                </CardContent>
              </Card>
            ) : results && results.results.length > 0 ? (() => {
              const analytics = getAnalytics();
              if (!analytics) return null;
              return (
                <div className="space-y-5">
                  {/* Summary Cards with Animated Counters */}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    {[
                      { icon: Activity, label: t('results.totalExperiments'), value: analytics.totalExperiments, color: "border-l-teal-500", iconBg: "bg-teal-500/10", iconColor: "text-teal-600", isCounter: true },
                      { icon: Clock, label: t('results.totalTime'), value: (analytics.totalTimeMs / 1000), color: "border-l-sky-500", iconBg: "bg-sky-500/10", iconColor: "text-sky-600", suffix: "s", decimals: 1, isCounter: true },
                      { icon: CheckCircle2, label: t('results.successRate'), value: analytics.successRate, color: "border-l-emerald-500", iconBg: "bg-emerald-500/10", iconColor: "text-emerald-600", suffix: "%", decimals: 1, isCounter: true },
                      { icon: Trophy, label: t('results.bestAlgorithm'), value: analytics.algorithmStats[0]?.displayName || "-", color: "border-l-amber-500", iconBg: "bg-amber-500/10", iconColor: "text-amber-600", isText: true },
                    ].map((stat) => (
                      <Card key={stat.label} className={`border-l-4 ${stat.color} shadow-sm transition-all duration-300 hover:shadow-md hover:scale-[1.02]`}>
                        <CardContent className="p-3.5">
                          <div className="flex items-center gap-2.5">
                            <div className={`${stat.iconBg} p-1.5 rounded-lg shrink-0 transition-transform duration-300 hover:scale-110`}>
                              <stat.icon className={`h-3.5 w-3.5 ${stat.iconColor}`} />
                            </div>
                            <div className="min-w-0">
                              <p className="text-[9px] text-muted-foreground uppercase tracking-wider">{stat.label}</p>
                              {stat.isText ? (
                                <p className="text-xs truncate font-semibold">{String(stat.value)}</p>
                              ) : stat.isCounter && animateResults ? (
                                <p className="text-lg font-bold tabular-nums">
                                  <AnimatedCounter
                                    target={stat.value as number}
                                    suffix={stat.suffix || ""}
                                    decimals={stat.decimals || 0}
                                    duration={1200}
                                  />
                                </p>
                              ) : (
                                <p className="text-lg font-bold tabular-nums">
                                  {stat.decimals ? (stat.value as number).toFixed(stat.decimals) : stat.value}{stat.suffix || ""}
                                </p>
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>

                  {/* Results Sub-tabs */}
                  <Tabs value={resultsSubTab} onValueChange={setResultsSubTab}>
                    <TabsList className="grid w-full grid-cols-4 h-9 mb-4">
                      <TabsTrigger value="tables" className="text-[11px] gap-1 transition-all duration-200">
                        <ScrollText className="h-3 w-3" /> {t('results.subTabTables')}
                      </TabsTrigger>
                      <TabsTrigger value="charts" className="text-[11px] gap-1 transition-all duration-200">
                        <BarChart3 className="h-3 w-3" /> {t('results.subTabCharts')}
                      </TabsTrigger>
                      <TabsTrigger value="comparison" className="text-[11px] gap-1 transition-all duration-200">
                        <Crosshair className="h-3 w-3" /> {t('results.subTabComparison')}
                      </TabsTrigger>
                      <TabsTrigger value="dashboard" className="text-[11px] gap-1 transition-all duration-200">
                        <PieChartIcon className="h-3 w-3" /> {t('results.subTabDashboard')}
                      </TabsTrigger>
                    </TabsList>

                    {/* ========= TABLES SUB-TAB ========= */}
                    <TabsContent value="tables" className="mt-0">
                      <div className="space-y-5">
                        {/* Algorithm Performance Table */}
                        <Card className="border shadow-sm border-l-4 border-l-primary/30">
                          <CardHeader className="pb-2">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <Cpu className="h-4 w-4 text-primary" />
                                <CardTitle className="text-xs">{t('results.algoPerformanceTitle')}</CardTitle>
                              </div>
                              <div className="flex gap-2">
                                <Button variant="outline" size="sm" onClick={handleExportCSV} className="h-7 text-[10px] transition-all duration-200 hover:scale-[1.03] active:scale-[0.98]">
                                  <FileSpreadsheet className="mr-1.5 h-3 w-3" /> {t('results.exportCSV')}
                                </Button>
                                <Button variant="outline" size="sm" onClick={handleExportJSON} className="h-7 text-[10px] transition-all duration-200 hover:scale-[1.03] active:scale-[0.98]">
                                  <Download className="mr-1.5 h-3 w-3" /> {t('results.exportJSON')}
                                </Button>
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent>
                            <div className="max-h-[350px] overflow-y-auto rounded-lg border" style={{ scrollbarWidth: "thin" }}>
                              <Table>
                                <TableHeader>
                                  <TableRow className="bg-muted/50 hover:bg-muted/50 sticky top-0">
                                    <TableHead className="text-[10px] w-10">#</TableHead>
                                    <TableHead className="text-[10px]">{t('results.tableAlgorithm')}</TableHead>
                                    <TableHead className="text-[10px] text-center">{t('results.tableAvgGap')}</TableHead>
                                    <TableHead className="text-[10px] text-center">{t('results.tableMinGap')}</TableHead>
                                    <TableHead className="text-[10px] text-center">{t('results.tableMaxGap')}</TableHead>
                                    <TableHead className="text-[10px] text-center">{t('results.tableAvgTime')}</TableHead>
                                    <TableHead className="text-[10px] text-center hidden sm:table-cell">{t('results.tableQuality')}</TableHead>
                                  </TableRow>
                                </TableHeader>
                                <TableBody>
                                  {analytics.algorithmStats.map((stat, i) => (
                                    <TableRow key={stat.algorithm} className={`transition-all duration-200 ${i === 0 ? "bg-emerald-500/5" : ""} hover:scale-[1.003]`}>
                                      <TableCell>{getRankBadge(i)}</TableCell>
                                      <TableCell className="font-medium text-xs">{stat.displayName}</TableCell>
                                      <TableCell className="text-center font-mono text-[11px] tabular-nums">
                                        <span className={stat.avgGap !== null && stat.avgGap < 3 ? "text-emerald-600 font-semibold" : ""}>
                                          {stat.avgGap !== null ? `%${stat.avgGap.toFixed(2)}` : "-"}
                                        </span>
                                      </TableCell>
                                      <TableCell className="text-center font-mono text-[11px] tabular-nums">
                                        {stat.minGap !== null ? `%${stat.minGap.toFixed(2)}` : "-"}
                                      </TableCell>
                                      <TableCell className="text-center font-mono text-[11px] tabular-nums">
                                        {stat.maxGap !== null ? `%${stat.maxGap.toFixed(2)}` : "-"}
                                      </TableCell>
                                      <TableCell className="text-center font-mono text-[11px] tabular-nums">
                                        {stat.avgTime.toFixed(0)}ms
                                      </TableCell>
                                      <TableCell className="text-center hidden sm:table-cell">
                                        {/* Mini quality bar */}
                                        <div className="flex items-center gap-1.5">
                                          <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                                            <div
                                              className="h-full rounded-full transition-all duration-700"
                                              style={{
                                                width: stat.avgGap !== null ? `${Math.max(5, Math.min(100, (1 - stat.avgGap / 20) * 100))}%` : "0%",
                                                background: stat.avgGap !== null && stat.avgGap < 3
                                                  ? "linear-gradient(90deg, #10b981, #22c55e)"
                                                  : stat.avgGap !== null && stat.avgGap < 7
                                                    ? "linear-gradient(90deg, #f59e0b, #eab308)"
                                                    : "linear-gradient(90deg, #ef4444, #f97316)",
                                              }}
                                            />
                                          </div>
                                          <span className="text-[8px] text-muted-foreground tabular-nums">
                                            {stat.avgGap !== null ? `${Math.round((1 - stat.avgGap / 20) * 100)}%` : "-"}
                                          </span>
                                        </div>
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </div>
                          </CardContent>
                        </Card>

                        {/* Problem Results Table with sparkline bars */}
                        <Card className="border shadow-sm border-l-4 border-l-teal-500/30">
                          <CardHeader className="pb-2">
                            <div className="flex items-center gap-2">
                              <ScrollText className="h-4 w-4 text-primary" />
                              <CardTitle className="text-xs">{t('results.problemResultsTitle')}</CardTitle>
                            </div>
                          </CardHeader>
                          <CardContent>
                            <div className="max-h-[350px] overflow-y-auto rounded-lg border" style={{ scrollbarWidth: "thin" }}>
                              <Table>
                                <TableHeader>
                                  <TableRow className="bg-muted/50 hover:bg-muted/50 sticky top-0">
                                    <TableHead className="text-[10px]">{t('results.tableProblem')}</TableHead>
                                    <TableHead className="text-[10px] text-center">{t('results.tableOptimal')}</TableHead>
                                    <TableHead className="text-[10px] text-center">{t('results.tableBestTour')}</TableHead>
                                    <TableHead className="text-[10px]">{t('results.tableBestAlgo')}</TableHead>
                                    <TableHead className="text-[10px] text-center">{t('results.tableOptGap')}</TableHead>
                                    <TableHead className="text-[10px] text-center hidden sm:table-cell">{t('results.tableAlgoDist')}</TableHead>
                                    <TableHead className="text-[10px] text-center hidden md:table-cell">#</TableHead>
                                  </TableRow>
                                </TableHeader>
                                <TableBody>
                                  {analytics.problemStats.map((stat) => (
                                    <TableRow key={stat.problem} className="transition-all duration-200 hover:scale-[1.003]">
                                      <TableCell className="font-mono font-medium text-xs">{stat.problem}</TableCell>
                                      <TableCell className="text-center font-mono text-[11px] tabular-nums">
                                        {stat.optimal != null ? stat.optimal.toLocaleString() : "-"}
                                      </TableCell>
                                      <TableCell className="text-center font-mono text-[11px] tabular-nums">
                                        {stat.bestTour.toLocaleString()}
                                      </TableCell>
                                      <TableCell className="text-xs">{stat.bestAlgorithmName}</TableCell>
                                      <TableCell className="text-center font-mono text-[11px] tabular-nums">
                                        {stat.gapFromOptimal != null ? (
                                          <span className={stat.gapFromOptimal < 3 ? "text-emerald-600 font-semibold" : ""}>
                                            %{stat.gapFromOptimal.toFixed(2)}
                                          </span>
                                        ) : "-"}
                                      </TableCell>
                                      <TableCell className="hidden sm:table-cell">
                                        {/* Sparkline mini bars for algorithm comparison */}
                                        <div className="flex items-end gap-[2px] h-5">
                                          {stat.algoGaps
                                            .filter((ag) => ag.gap !== null)
                                            .sort((a, b) => (a.gap ?? 0) - (b.gap ?? 0))
                                            .slice(0, 8)
                                            .map((ag, j) => {
                                              const maxGap = Math.max(...stat.algoGaps.filter(x => x.gap !== null).map(x => x.gap!), 1);
                                              const height = ag.gap !== null ? Math.max(10, (1 - ag.gap / maxGap) * 100) : 10;
                                              const isBest = ag.algo === stat.bestAlgorithm;
                                              return (
                                                <div
                                                  key={j}
                                                  className="w-1.5 rounded-sm transition-all duration-300 hover:w-2.5"
                                                  style={{
                                                    height: `${height}%`,
                                                    backgroundColor: isBest ? "#10b981" : CHART_COLOR_VALUES[j % CHART_COLOR_VALUES.length],
                                                    opacity: isBest ? 1 : 0.6,
                                                  }}
                                                  title={`${ALGORITHM_DISPLAY_NAMES[ag.algo] || ag.algo}: ${ag.gap !== null ? `%${ag.gap.toFixed(2)}` : "-"}`}
                                                />
                                              );
                                            })}
                                        </div>
                                      </TableCell>
                                      <TableCell className="text-center text-[11px] tabular-nums hidden md:table-cell">
                                        {stat.algorithmsTested}
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </div>
                          </CardContent>
                        </Card>

                        {/* Heatmap Matrix */}
                        {heatmapData && heatmapData.algos.length > 1 && heatmapData.probs.length > 1 && (
                          <Card className="border shadow-sm border-l-4 border-l-amber-500/30">
                            <CardHeader className="pb-2">
                              <div className="flex items-center gap-2">
                                <Grid3X3 className="h-4 w-4 text-primary" />
                                <CardTitle className="text-xs">{t('results.heatmapTitle')}</CardTitle>
                              </div>
                              <CardDescription className="text-[10px]">
                                {t('results.heatmapDesc')}
                              </CardDescription>
                            </CardHeader>
                            <CardContent>
                              <div className="overflow-x-auto max-h-[300px]" style={{ scrollbarWidth: "thin" }}>
                                <table className="text-[9px] border-collapse">
                                  <thead>
                                    <tr>
                                      <th className="p-1.5 text-left font-semibold sticky left-0 bg-background z-10">{t('results.heatmapHeader')}</th>
                                      {heatmapData.probs.map((prob) => (
                                        <th key={prob} className="p-1.5 text-center font-mono font-semibold min-w-[48px]">{prob}</th>
                                      ))}
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {heatmapData.algos.map((algo) => {
                                      const algoName = ALGORITHM_DISPLAY_NAMES[algo] || algo;
                                      return (
                                        <tr key={algo}>
                                          <td className="p-1.5 font-medium sticky left-0 bg-background z-10 max-w-[120px] truncate" title={algoName}>{algoName}</td>
                                          {heatmapData.probs.map((prob) => {
                                            const cell = heatmapData.matrix.find((m) => m.algo === algo && m.prob === prob);
                                            const gap = cell?.gap;
                                            const bg = gap == null
                                              ? "bg-muted"
                                              : gap < 2
                                                ? "bg-emerald-500/40"
                                                : gap < 5
                                                  ? "bg-emerald-500/20"
                                                  : gap < 8
                                                    ? "bg-amber-500/30"
                                                    : gap < 12
                                                      ? "bg-orange-500/30"
                                                      : "bg-red-500/30";
                                            return (
                                              <td
                                                key={`${algo}-${prob}`}
                                                className={`p-1.5 text-center font-mono tabular-nums rounded-sm transition-all duration-200 hover:scale-110 hover:z-10 hover:shadow-md cursor-default ${bg}`}
                                                title={`${algoName} × ${prob}: ${gap != null ? `%${gap.toFixed(2)}` : "-"}`}
                                              >
                                                {gap != null ? gap.toFixed(1) : "-"}
                                              </td>
                                            );
                                          })}
                                        </tr>
                                      );
                                    })}
                                  </tbody>
                                </table>
                              </div>
                            </CardContent>
                          </Card>
                        )}
                      </div>
                    </TabsContent>

                    {/* ========= CHARTS SUB-TAB ========= */}
                    <TabsContent value="charts" className="mt-0">
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                        {gapChartData && gapChartData.length > 0 && (
                          <Card className="border shadow-sm border-l-4 border-l-teal-500/30">
                            <CardHeader className="pb-2">
                              <CardTitle className="text-xs flex items-center gap-1.5">
                                <TrendingUp className="h-3.5 w-3.5 text-teal-600" />
                                {t('results.chartAvgGapTitle')}
                              </CardTitle>
                              <CardDescription className="text-[10px]">
                                {t('results.chartAvgGapDesc')}
                              </CardDescription>
                            </CardHeader>
                            <CardContent>
                              <ChartContainer
                                config={Object.fromEntries(
                                  gapChartData.map((d, i) => [d.algorithm, { label: d.algorithm, color: CHART_COLORS[i % CHART_COLORS.length] }])
                                ) as ChartConfig}
                                className="h-[280px] w-full"
                              >
                                <BarChart data={gapChartData} layout="vertical" margin={{ left: 10, right: 20 }}>
                                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                                  <XAxis type="number" tick={{ fontSize: 10 }} />
                                  <YAxis type="category" dataKey="algorithm" width={120} tick={{ fontSize: 10 }} />
                                  <ChartTooltip content={<ChartTooltipContent />} />
                                  <Bar dataKey="gap" radius={[0, 4, 4, 0]}>
                                    {gapChartData.map((_entry, index) => (
                                      <Cell key={`cell-gap-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                                    ))}
                                  </Bar>
                                </BarChart>
                              </ChartContainer>
                            </CardContent>
                          </Card>
                        )}

                        {timeChartData && timeChartData.length > 0 && (
                          <Card className="border shadow-sm border-l-4 border-l-amber-500/30">
                            <CardHeader className="pb-2">
                              <CardTitle className="text-xs flex items-center gap-1.5">
                                <Timer className="h-3.5 w-3.5 text-amber-600" />
                                {t('results.chartAvgTimeTitle')}
                              </CardTitle>
                              <CardDescription className="text-[10px]">
                                {t('results.chartAvgTimeDesc')}
                              </CardDescription>
                            </CardHeader>
                            <CardContent>
                              <ChartContainer
                                config={Object.fromEntries(
                                  timeChartData.map((d, i) => [d.algorithm, { label: d.algorithm, color: CHART_COLORS[i % CHART_COLORS.length] }])
                                ) as ChartConfig}
                                className="h-[280px] w-full"
                              >
                                <BarChart data={timeChartData} margin={{ bottom: 5, right: 10, left: 10 }}>
                                  <CartesianGrid strokeDasharray="3 3" />
                                  <XAxis type="category" dataKey="algorithm" tick={{ fontSize: 9 }} angle={-20} textAnchor="end" height={50} />
                                  <YAxis type="number" tick={{ fontSize: 10 }} />
                                  <ChartTooltip content={<ChartTooltipContent />} />
                                  <Bar dataKey="time" radius={[4, 4, 0, 0]}>
                                    {timeChartData.map((_entry, index) => (
                                      <Cell key={`cell-time-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                                    ))}
                                  </Bar>
                                </BarChart>
                              </ChartContainer>
                            </CardContent>
                          </Card>
                        )}
                      </div>
                    </TabsContent>

                    {/* ========= COMPARISON SUB-TAB ========= */}
                    <TabsContent value="comparison" className="mt-0">
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                        {/* Radar Chart */}
                        {radarData && radarChartData.length > 0 && (
                          <Card className="border shadow-sm border-l-4 border-l-purple-500/30">
                            <CardHeader className="pb-2">
                              <CardTitle className="text-xs flex items-center gap-1.5">
                                <Crosshair className="h-3.5 w-3.5 text-purple-600" />
                                {t('results.radarTitle')}
                              </CardTitle>
                              <CardDescription className="text-[10px]">
                                {t('results.radarDesc')}
                              </CardDescription>
                            </CardHeader>
                            <CardContent>
                              <ChartContainer
                                config={Object.fromEntries(
                                  radarData.algorithms.map((a) => [a.name, { label: a.name, color: a.color }])
                                ) as ChartConfig}
                                className="h-[320px] w-full"
                              >
                                <RadarChart data={radarChartData} cx="50%" cy="50%" outerRadius="70%">
                                  <PolarGrid />
                                  <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 10 }} />
                                  <PolarRadiusAxis tick={{ fontSize: 8 }} domain={[0, 100]} />
                                  {radarData.algorithms.slice(0, 4).map((algo, i) => (
                                    <Radar
                                      key={algo.name}
                                      name={algo.name}
                                      dataKey={algo.name}
                                      stroke={algo.color}
                                      fill={algo.color}
                                      fillOpacity={0.15}
                                      strokeWidth={2}
                                    />
                                  ))}
                                  <ChartTooltip content={<ChartTooltipContent />} />
                                </RadarChart>
                              </ChartContainer>
                              {/* Legend */}
                              <div className="flex flex-wrap gap-3 mt-2 justify-center">
                                {radarData.algorithms.slice(0, 4).map((algo) => (
                                  <div key={algo.name} className="flex items-center gap-1.5 text-[10px]">
                                    <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: algo.color }} />
                                    <span className="text-muted-foreground truncate max-w-[100px]">{algo.name}</span>
                                  </div>
                                ))}
                              </div>
                            </CardContent>
                          </Card>
                        )}

                        {/* Quality vs Speed Scatter Plot */}
                        {scatterData.length > 0 && (
                          <Card className="border shadow-sm border-l-4 border-l-emerald-500/30">
                            <CardHeader className="pb-2">
                              <CardTitle className="text-xs flex items-center gap-1.5">
                                <Zap className="h-3.5 w-3.5 text-emerald-600" />
                                {t('results.scatterTitle')}
                              </CardTitle>
                              <CardDescription className="text-[10px]">
                                {t('results.scatterDesc')}
                              </CardDescription>
                            </CardHeader>
                            <CardContent>
                              <div className="h-[320px] w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                  <ScatterChart margin={{ bottom: 10, right: 10, left: 10, top: 10 }}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis type="number" dataKey="x" name="time" tick={{ fontSize: 9 }} label={{ value: t('results.scatterTimeName'), position: "insideBottom", offset: -5, fontSize: 9 }} />
                                    <YAxis type="number" dataKey="y" name="gap" tick={{ fontSize: 9 }} label={{ value: t('results.scatterGapName'), angle: -90, position: "insideLeft", offset: 10, fontSize: 9 }} />
                                    <ZAxis type="number" dataKey="z" range={[60, 400]} name="experiment" />
                                    <RechartsTooltip
                                      formatter={(value: number, name: string) => {
                                        if (name === "time") return [`${value.toFixed(0)}ms`, t('results.scatterTimeName')];
                                        if (name === "gap") return [`%${value.toFixed(2)}`, t('results.scatterGapName')];
                                        if (name === "experiment") return [value, t('results.scatterExperimentName')];
                                        return [value, name];
                                      }}
                                      labelFormatter={(_label: string, payload: Array<{ payload?: { name?: string } }>) => {
                                        if (payload?.[0]?.payload?.name) return payload[0].payload.name;
                                        return "";
                                      }}
                                    />
                                    <Scatter data={scatterData} fill="#10b981">
                                      {scatterData.map((entry, index) => (
                                        <Cell key={`cell-scatter-${index}`} fill={entry.fill} fillOpacity={0.7} stroke={entry.fill} strokeWidth={1.5} />
                                      ))}
                                    </Scatter>
                                  </ScatterChart>
                                </ResponsiveContainer>
                              </div>
                              {/* Legend for scatter */}
                              <div className="flex flex-wrap gap-2 mt-2 justify-center">
                                {scatterData.map((entry, i) => (
                                  <div key={i} className="flex items-center gap-1 text-[9px]">
                                    <div className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.fill }} />
                                    <span className="text-muted-foreground truncate max-w-[90px]">{entry.name}</span>
                                  </div>
                                ))}
                              </div>
                            </CardContent>
                          </Card>
                        )}
                      </div>
                    </TabsContent>

                    {/* ========= DASHBOARD SUB-TAB ========= */}
                    <TabsContent value="dashboard" className="mt-0">
                      <div className="space-y-5">
                        {/* Algorithm Distribution Pie Chart */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                          <Card className="border shadow-sm border-l-4 border-l-teal-500/30">
                            <CardHeader className="pb-2">
                              <CardTitle className="text-xs flex items-center gap-1.5">
                                <PieChartIcon className="h-3.5 w-3.5 text-teal-600" />
                                {t('results.pieTitle')}
                              </CardTitle>
                              <CardDescription className="text-[10px]">
                                {t('results.pieDesc')}
                              </CardDescription>
                            </CardHeader>
                            <CardContent>
                              <div className="h-[260px] w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                  <PieChart>
                                    <Pie
                                      data={analytics.algorithmStats.map((s, i) => ({
                                        name: s.displayName.length > 18 ? s.displayName.substring(0, 18) + "..." : s.displayName,
                                        value: s.count,
                                        fill: CHART_COLOR_VALUES[i % CHART_COLOR_VALUES.length],
                                      }))}
                                      cx="50%"
                                      cy="50%"
                                      innerRadius={55}
                                      outerRadius={90}
                                      paddingAngle={3}
                                      dataKey="value"
                                      strokeWidth={2}
                                      stroke="var(--background)"
                                    >
                                      {analytics.algorithmStats.map((_, i) => (
                                        <RechartsCell key={`cell-pie-${i}`} fill={CHART_COLOR_VALUES[i % CHART_COLOR_VALUES.length]} />
                                      ))}
                                    </Pie>
                                    <RechartsTooltip
                                      formatter={(value: number, name: string) => [t('results.pieTooltip', { count: value }), name]}
                                    />
                                    <RechartsLegend
                                      layout="vertical"
                                      align="right"
                                      verticalAlign="middle"
                                      iconSize={8}
                                      iconType="circle"
                                      formatter={(value: string) => <span className="text-[9px] text-muted-foreground">{value}</span>}
                                    />
                                  </PieChart>
                                </ResponsiveContainer>
                              </div>
                            </CardContent>
                          </Card>

                          {/* Performance Ranking Card */}
                          <Card className="border shadow-sm border-l-4 border-l-amber-500/30">
                            <CardHeader className="pb-2">
                              <CardTitle className="text-xs flex items-center gap-1.5">
                                <Medal className="h-3.5 w-3.5 text-amber-600" />
                                {t('results.rankingTitle')}
                              </CardTitle>
                              <CardDescription className="text-[10px]">
                                {t('results.rankingDesc')}
                              </CardDescription>
                            </CardHeader>
                            <CardContent>
                              <div className="space-y-2.5">
                                {analytics.algorithmStats.slice(0, 6).map((stat, i) => {
                                  const maxGap = Math.max(...analytics.algorithmStats.map(s => s.avgGap ?? 0), 1);
                                  const qualityScore = stat.avgGap !== null ? Math.max(0, (1 - stat.avgGap / maxGap) * 100) : 0;
                                  return (
                                    <div key={stat.algorithm} className="flex items-center gap-3 group">
                                      <div className="shrink-0">
                                        {getRankBadge(i)}
                                      </div>
                                      <div className="flex-1 min-w-0">
                                        <div className="flex items-center justify-between mb-1">
                                          <span className="text-[11px] font-medium truncate">{stat.displayName}</span>
                                          <span className="text-[10px] font-mono tabular-nums ml-2">
                                            {stat.avgGap !== null ? `%${stat.avgGap.toFixed(2)}` : "-"}
                                          </span>
                                        </div>
                                        <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                                          <div
                                            className="h-full rounded-full transition-all duration-700 group-hover:opacity-90"
                                            style={{
                                              width: `${qualityScore}%`,
                                              background: i === 0
                                                ? "linear-gradient(90deg, #10b981, #22c55e)"
                                                : i === 1
                                                  ? "linear-gradient(90deg, #06b6d4, #14b8a6)"
                                                  : i === 2
                                                    ? "linear-gradient(90deg, #f59e0b, #eab308)"
                                                    : "linear-gradient(90deg, #94a3b8, #cbd5e1)",
                                            }}
                                          />
                                        </div>
                                      </div>
                                      <div className="shrink-0 text-[9px] text-muted-foreground tabular-nums w-14 text-right">
                                        {stat.avgTime.toFixed(0)}ms
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            </CardContent>
                          </Card>
                        </div>

                        {/* Key Insights Card */}
                        <Card className="border shadow-sm border-l-4 border-l-purple-500/30">
                          <CardHeader className="pb-2">
                            <CardTitle className="text-xs flex items-center gap-1.5">
                              <Lightbulb className="h-3.5 w-3.5 text-purple-600" />
                              {t('results.insightsTitle')}
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                              {analytics.algorithmStats.length > 0 && (
                                <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/15">
                                  <p className="text-[9px] font-semibold text-emerald-600 uppercase tracking-wider mb-1">{t('results.insightBestQuality')}</p>
                                  <p className="text-xs font-semibold">{analytics.algorithmStats[0].displayName}</p>
                                  <p className="text-[10px] text-muted-foreground">
                                    {t('results.insightAvgGap', { gap: analytics.algorithmStats[0].avgGap !== null ? analytics.algorithmStats[0].avgGap.toFixed(2) : "N/A" })}
                                  </p>
                                </div>
                              )}
                              {analytics.algorithmStats.length > 0 && (
                                <div className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/15">
                                  <p className="text-[9px] font-semibold text-amber-600 uppercase tracking-wider mb-1">{t('results.insightFastest')}</p>
                                  <p className="text-xs font-semibold">
                                    {analytics.algorithmStats.reduce((fastest, s) => s.avgTime < fastest.avgTime ? s : fastest).displayName}
                                  </p>
                                  <p className="text-[10px] text-muted-foreground">
                                    {t('results.insightAvgTime', { time: analytics.algorithmStats.reduce((fastest, s) => s.avgTime < fastest.avgTime ? s : fastest).avgTime.toFixed(0) })}
                                  </p>
                                </div>
                              )}
                              {analytics.algorithmStats.length > 0 && (
                                <div className="p-3 rounded-lg bg-sky-500/5 border border-sky-500/15">
                                  <p className="text-[9px] font-semibold text-sky-600 uppercase tracking-wider mb-1">{t('results.insightMostConsistent')}</p>
                                  <p className="text-xs font-semibold">
                                    {analytics.algorithmStats.reduce((best, s) => s.gapStdDev < best.gapStdDev ? s : best).displayName}
                                  </p>
                                  <p className="text-[10px] text-muted-foreground">
                                    {t('results.insightStdDev', { stddev: analytics.algorithmStats.reduce((best, s) => s.gapStdDev < best.gapStdDev ? s : best).gapStdDev.toFixed(3) })}
                                  </p>
                                </div>
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    </TabsContent>
                  </Tabs>
                </div>
              );
            })() : (
              <Card className="border shadow-sm">
                <CardContent className="py-16 text-center">
                  <BarChart3 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="text-lg font-semibold mb-2">{t('results.noResults')}</h3>
                  <p className="text-muted-foreground text-sm">{t('results.noResultsDesc')}</p>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </main>

      {/* ============ FOOTER ============ */}
      <footer className="border-t bg-muted/30 mt-auto">
        {/* Gradient separator */}
        <div className="h-[2px] bg-gradient-to-r from-transparent via-teal-500/40 to-transparent" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-teal-500 to-emerald-600 flex items-center justify-center shadow-md shadow-teal-500/20 transition-transform duration-300 hover:scale-110">
                <Route className="h-4 w-4 text-white" />
              </div>
              <div>
                <p className="text-sm font-bold tracking-tight">UniRide Benchmark Suite</p>
                <p className="text-[10px] text-muted-foreground">{t('hero.footerSubtitle')}</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-muted/60 text-[10px] text-muted-foreground transition-colors duration-200 hover:text-teal-600 cursor-default">
                <Eye className="h-3 w-3" /> 3 Pipeline
              </span>
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-muted/60 text-[10px] text-muted-foreground transition-colors duration-200 hover:text-amber-600 cursor-default">
                <Cpu className="h-3 w-3" /> 14+ Algoritma
              </span>
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-muted/60 text-[10px] text-muted-foreground transition-colors duration-200 hover:text-emerald-600 cursor-default">
                <MonitorSmartphone className="h-3 w-3" /> Responsive
              </span>
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-muted/60 text-[10px] text-muted-foreground transition-colors duration-200 hover:text-purple-600 cursor-default">
                <Bot className="h-3 w-3" /> {t('advisor.buttonLabel')}
              </span>
            </div>
            <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
              <span className="flex items-center gap-1">
                {t('hero.madeBy')}
                <Heart className="h-3 w-3 text-red-400 animate-pulse" />
                {t('hero.madeBySuffix')}
              </span>
              <a href="#" className="flex items-center gap-1.5 px-2 py-1 rounded-md hover:bg-muted transition-all duration-200 hover:text-foreground">
                <Github className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">GitHub</span>
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
