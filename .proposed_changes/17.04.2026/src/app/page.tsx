"use client";

import React, { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Route,
  Wifi,
  WifiOff,
  Loader2,
  CheckCircle2,
  Clock,
  ArrowRight,
  Star,
  FlaskConical,
  Package,
  Layers,
  Wrench,
  Shield,
  Zap,
  GitBranch,
  Brain,
  Cpu,
  Target,
  TrendingUp,
  BookOpen,
  ExternalLink,
  Sun,
  Moon,
  Boxes,
  Puzzle,
  RefreshCw,
  ChevronRight,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
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
} from "recharts";

// ============================================================
// Types & Constants
// ============================================================

type DnaStatus = "implemented" | "in-progress" | "planned";

interface DnaFactor {
  id: number;
  name: string;
  description: string;
  status: DnaStatus;
  moduleCoverage: string[];
}

interface FazModule {
  id: string;
  nameEn: string;
  nameTr: string;
  purpose: string;
  dnaCoverage: string[];
  status: DnaStatus;
  classDiagram: string;
  keyMethods: string[];
}

interface RoadmapPhase {
  phase: number;
  name: string;
  description: string;
  icon: React.ReactNode;
  status: "current" | "next" | "planned" | "future";
  targetAlgorithms: string;
  dnaFactors: number;
  expectedGapImprovement: string;
  color: string;
}

// ============================================================
// Data
// ============================================================

const DNA_FACTORS: DnaFactor[] = [
  {
    id: 1,
    name: "Problem-Yapili Operatorler",
    description: "Problem tipine ozel tasarlanmis cozum operatörleri (TSP, CVRP, VRPTW)",
    status: "implemented",
    moduleCoverage: ["DestroyOperators", "RepairOperators"],
  },
  {
    id: 2,
    name: "Buyuk Komsuluk Aramasi (LNS)",
    description: "Buyuk komsuluk arama ile kapsamli cozum uzayi kesfi",
    status: "implemented",
    moduleCoverage: ["DestroyOperators", "RepairOperators"],
  },
  {
    id: 3,
    name: "Cok Katmanli Lokal Arama",
    description: "2-opt, Or-opt, 3-opt ve Swap katmanlarindan olusan zincirleme lokal arama",
    status: "implemented",
    moduleCoverage: ["MultiLayerLS"],
  },
  {
    id: 4,
    name: "Adaptif Mekanizmalar",
    description: "Iterasyon boyunca parametrelerin otomatik ayarlanmasi",
    status: "implemented",
    moduleCoverage: ["PenaltyManager", "DiversityController"],
  },
  {
    id: 5,
    name: "Giant Tour + Split Temsil",
    description: "Dev tur ve ayirma tabanli cozum gosterimi",
    status: "implemented",
    moduleCoverage: ["sota_common"],
  },
  {
    id: 6,
    name: "Coklu Baslangic Cozumu",
    description: "NN, CW, Regret ve Random ile cesitlendirilmis baslangic cozumleri",
    status: "implemented",
    moduleCoverage: ["MultiStartInitializer"],
  },
  {
    id: 7,
    name: "Kabul Kriterleri (SA/LAHC)",
    description: "Simulated Annealing ve LAHC tabanli kabul mekanizmalari",
    status: "implemented",
    moduleCoverage: ["AcceptanceCriterion"],
  },
  {
    id: 8,
    name: "Cesitlilik Yonetimi",
    description: "Cozum havuzundaki cesitliligin izlenmesi ve korunmasi",
    status: "implemented",
    moduleCoverage: ["DiversityController"],
  },
  {
    id: 9,
    name: "Penalty-Based Relaxation",
    description: "Kisitlari cezalandirma ile gevsestirip asamali sikilastirma",
    status: "implemented",
    moduleCoverage: ["PenaltyManager"],
  },
  {
    id: 10,
    name: "Neural/ML via Evolutionary Genome",
    description: "P-AOEA ile evrimsel genom tabanli yapay sinir aglari — operator secimi, parametre onerisi ve adaptif ogrenme",
    status: "implemented",
    moduleCoverage: ["P-AOEA"],
  },
];

const FAZ_MODULES: FazModule[] = [
  {
    id: "multistart",
    nameEn: "MultiStartInitializer",
    nameTr: "Coklu Baslangic Cozumu Uretici",
    purpose: "NN (En Yakin Komsu), Clarke-Wright Tasarruf, Regret-2 ve Random baslangic stratejileri ile cesitlendirilmis baslangic cozumleri uretir.",
    dnaCoverage: ["DNA-6"],
    status: "implemented",
    classDiagram: `┌─────────────────────────────┐
│   MultiStartInitializer    │
├─────────────────────────────┤
│ + strategies: List[BaseInit]│
│ + count: int                │
├─────────────────────────────┤
│ + generate() → List[Route]  │
│ + _nn_init() → Route        │
│ + _cw_init() → Route        │
│ + _regret_init() → Route    │
│ + _random_init() → Route    │
└─────────────────────────────┘`,
    keyMethods: ["generate()", "_nn_init()", "_cw_init()", "_regret_init()", "_random_init()"],
  },
  {
    id: "multilayerls",
    nameEn: "MultiLayerLS",
    nameTr: "Cok Katmanli Lokal Arama Motoru",
    purpose: "2-opt → Or-opt → 3-opt → Swap katmanlarindan olusan zincirleme lokal arama. Her katman iyilestirme saglamaya devam ettikce bir sonraki katmana gecer.",
    dnaCoverage: ["DNA-3"],
    status: "implemented",
    classDiagram: `┌─────────────────────────────┐
│      MultiLayerLS           │
├─────────────────────────────┤
│ + layers: List[LSOperator]  │
│ + max_iterations: int       │
│ + time_limit: float         │
├─────────────────────────────┤
│ + optimize(route) → Route   │
│ + _run_2opt() → improved    │
│ + _run_or_opt() → improved  │
│ + _run_3opt() → improved    │
│ + _run_swap() → improved    │
└─────────────────────────────┘`,
    keyMethods: ["optimize()", "_run_2opt()", "_run_or_opt()", "_run_3opt()", "_run_swap()"],
  },
  {
    id: "penalty",
    nameEn: "PenaltyManager",
    nameTr: "Adaptif Ceza Yoneticisi",
    purpose: "Zaman penceresi, kapasite ve diger kisit ihlallerini izler, adaptif alpha parametreleri ile ceza agirliklarini otomatik ayarlar.",
    dnaCoverage: ["DNA-4", "DNA-9"],
    status: "implemented",
    classDiagram: `┌─────────────────────────────┐
│     PenaltyManager          │
├─────────────────────────────┤
│ + alpha_tw: float           │
│ + alpha_cap: float          │
│ + history: List[PenaltyRec] │
├─────────────────────────────┤
│ + compute_penalty() → float │
│ + update_weights()           │
│ + reset_penalties()          │
│ + get_violations() → Dict    │
│ + iterated_penalty()         │
└─────────────────────────────┘`,
    keyMethods: ["compute_penalty()", "update_weights()", "reset_penalties()", "get_violations()", "iterated_penalty()"],
  },
  {
    id: "acceptance",
    nameEn: "AcceptanceCriterion",
    nameTr: "Kabul Kriterleri Kutuphanesi",
    purpose: "Simulated Annealing (SA), Late Acceptance Hill Climbing (LAHC) ve Record-to-Record Travel (RTR) kabul stratejileri.",
    dnaCoverage: ["DNA-7"],
    status: "implemented",
    classDiagram: `┌─────────────────────────────┐
│  AcceptanceCriterion        │
├─────────────────────────────┤
│ # temperature: float        │
│ # cooling_rate: float       │
│ # lahc_memory: List[float]  │
├─────────────────────────────┤
│ + accept(delta, iter) → bool│
│ + _sa_accept() → bool       │
│ + _lahc_accept() → bool     │
│ + _rtr_accept() → bool      │
│ + reset()                    │
└─────────────────────────────┘`,
    keyMethods: ["accept()", "_sa_accept()", "_lahc_accept()", "_rtr_accept()", "reset()"],
  },
  {
    id: "destroy",
    nameEn: "DestroyOperators",
    nameTr: "Yikici Operatorler (ALNS)",
    purpose: "ALNS icin 4 yikici operator: Random Removal, Worst Removal, Shaw Removal (Related) ve Historical Removal.",
    dnaCoverage: ["DNA-1", "DNA-2"],
    status: "implemented",
    classDiagram: `┌─────────────────────────────┐
│    DestroyOperators          │
├─────────────────────────────┤
│ + operators: List[Destroy]   │
│ + weights: Dict[str,float]   │
├─────────────────────────────┤
│ + destroy(route, q) → Partial│
│ + random_removal()           │
│ + worst_removal()            │
│ + shaw_removal()             │
│ + historical_removal()       │
│ + select_operator()          │
│ + update_weights()           │
└─────────────────────────────┘`,
    keyMethods: ["destroy()", "random_removal()", "worst_removal()", "shaw_removal()", "historical_removal()"],
  },
  {
    id: "repair",
    nameEn: "RepairOperators",
    nameTr: "Tamir Operatorleri (ALNS)",
    purpose: "ALNS icin 3 tamir operator: Greedy Insertion, Regret-2 Insertion ve Regret-3 Insertion.",
    dnaCoverage: ["DNA-1", "DNA-2"],
    status: "implemented",
    classDiagram: `┌─────────────────────────────┐
│    RepairOperators          │
├─────────────────────────────┤
│ + operators: List[Repair]    │
│ + weights: Dict[str,float]   │
├─────────────────────────────┤
│ + repair(partial) → Route    │
│ + greedy_insertion()         │
│ + regret_2_insertion()       │
│ + regret_3_insertion()       │
│ + select_operator()          │
│ + update_weights()           │
└─────────────────────────────┘`,
    keyMethods: ["repair()", "greedy_insertion()", "regret_2_insertion()", "regret_3_insertion()", "select_operator()"],
  },
  {
    id: "diversity",
    nameEn: "DiversityController",
    nameTr: "Cesitlilik Kontrolcusu",
    purpose: "Cozum havuzundaki cesitliligi olcer, benzerlik ekseninde olcutler kullanir, gerektiginde perturbasyon uygular.",
    dnaCoverage: ["DNA-4", "DNA-8"],
    status: "implemented",
    classDiagram: `┌─────────────────────────────┐
│  DiversityController        │
├─────────────────────────────┤
│ + pool: List[Route]          │
│ + threshold: float           │
│ + diversity_metric: float    │
├─────────────────────────────┤
│ + measure() → float          │
│ + add_solution()             │
│ + is_diverse() → bool        │
│ + perturb() → Route          │
│ + prune_pool()               │
└─────────────────────────────┘`,
    keyMethods: ["measure()", "add_solution()", "is_diverse()", "perturb()", "prune_pool()"],
  },
  {
    id: "sota_common",
    nameEn: "sota_common",
    nameTr: "Package Export Modulu",
    purpose: "Tum FAZ 0 modullerini tek bir paket olarak disa aktarir. E²BSO, R²DMA, P-AOEA algoritmalarinin ortak import noktasi.",
    dnaCoverage: ["DNA-5"],
    status: "implemented",
    classDiagram: `┌─────────────────────────────┐
│      sota_common             │
├─────────────────────────────┤
│ exports:                     │
│  MultiStartInitializer       │
│  MultiLayerLS                │
│  PenaltyManager              │
│  AcceptanceCriterion         │
│  DestroyOperators            │
│  RepairOperators             │
│  DiversityController         │
│  types & interfaces          │
├─────────────────────────────┤
│ + VERSION: str               │
│ + get_module_info()          │
└─────────────────────────────┘`,
    keyMethods: ["get_module_info()", "MultiStartInitializer", "MultiLayerLS", "PenaltyManager", "DiversityController"],
  },
];

const ROADMAP_PHASES: RoadmapPhase[] = [
  {
    phase: 0,
    name: "FAZ 0: Ortak Altyapi",
    description: "8 ortak modul ile altyapi temeli. Tum SOTA algoritmalar icin paylasilan temel bilesenler.",
    icon: <CheckCircle2 className="h-5 w-5 text-emerald-500" />,
    status: "current",
    targetAlgorithms: "Tumu",
    dnaFactors: 10,
    expectedGapImprovement: "Baseline olusturma",
    color: "emerald",
  },
  {
    phase: 1,
    name: "FAZ 1: E²BSO",
    description: "Evolutionary & Entropy-Based Swarm Optimization. Genetik algoritma + Entropi cesitlilik + Balina optimizasyonu.",
    icon: <CheckCircle2 className="h-5 w-5 text-emerald-500" />,
    status: "current",
    targetAlgorithms: "TSP, CVRP, VRPTW",
    dnaFactors: 7,
    expectedGapImprovement: "%20 → %10",
    color: "amber",
  },
  {
    phase: 2,
    name: "FAZ 2: R²DMA",
    description: "Resonance-Driven Multi-Algorithm. 6-boyutlu rezonans metriği + ALNS destructive.",
    icon: <CheckCircle2 className="h-5 w-5 text-emerald-500" />,
    status: "current",
    targetAlgorithms: "CVRP, VRPTW",
    dnaFactors: 8,
    expectedGapImprovement: "%10 → %5",
    color: "slate",
  },
  {
    phase: 3,
    name: "FAZ 3: P-AOEA",
    description: "Physics-Augmented Operator Evolutionary Algorithm. 20+ atomic operasyon + Neural/ML Boosting.",
    icon: <CheckCircle2 className="h-5 w-5 text-emerald-500" />,
    status: "current",
    targetAlgorithms: "TSP, CVRP, VRPTW",
    dnaFactors: 10,
    expectedGapImprovement: "%5 → <3%",
    color: "purple",
  },
];

const CHART_CONFIG = {
  coverage: {
    label: "Kapsam (%)",
    color: "hsl(142, 76%, 36%)",
  },
} satisfies ChartConfig;

// ============================================================
// Helpers
// ============================================================

function getStatusConfig(status: DnaStatus) {
  switch (status) {
    case "implemented":
      return {
        label: "Uygulandı",
        bgClass: "bg-emerald-100 dark:bg-emerald-950/40",
        borderClass: "border-emerald-300 dark:border-emerald-700",
        textClass: "text-emerald-700 dark:text-emerald-400",
        badgeClass: "bg-emerald-600 hover:bg-emerald-700 text-white",
        icon: <CheckCircle2 className="h-4 w-4" />,
      };
    case "in-progress":
      return {
        label: "Devam Ediyor",
        bgClass: "bg-amber-100 dark:bg-amber-950/40",
        borderClass: "border-amber-300 dark:border-amber-700",
        textClass: "text-amber-700 dark:text-amber-400",
        badgeClass: "bg-amber-600 hover:bg-amber-700 text-white",
        icon: <RefreshCw className="h-4 w-4" />,
      };
    case "planned":
      return {
        label: "Planlandı",
        bgClass: "bg-slate-100 dark:bg-slate-800/40",
        borderClass: "border-slate-300 dark:border-slate-600",
        textClass: "text-slate-500 dark:text-slate-400",
        badgeClass: "bg-slate-500 hover:bg-slate-600 text-white",
        icon: <Clock className="h-4 w-4" />,
      };
  }
}

function getPhaseCardStyles(phase: RoadmapPhase) {
  switch (phase.status) {
    case "current":
      return "border-emerald-300 dark:border-emerald-700 bg-emerald-50/50 dark:bg-emerald-950/20";
    case "next":
      return "border-amber-300 dark:border-amber-700 bg-amber-50/50 dark:bg-amber-950/20";
    case "planned":
      return "border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/20";
    case "future":
      return "border-purple-200 dark:border-purple-700 bg-purple-50/50 dark:bg-purple-950/20";
  }
}

// ============================================================
// Main Page Component
// ============================================================

export default function Faz0Dashboard() {
  const { toast } = useToast();
  const [isDark, setIsDark] = useState(false);
  const [apiStatus, setApiStatus] = useState<{
    online: boolean | null;
    loading: boolean;
  }>({ online: null, loading: true });

  // ---- Theme toggle ----
  useEffect(() => {
    const root = document.documentElement;
    const isDarkMode = root.classList.contains("dark");
    setIsDark(isDarkMode);

    const observer = new MutationObserver(() => {
      setIsDark(root.classList.contains("dark"));
    });
    observer.observe(root, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  const toggleTheme = () => {
    const root = document.documentElement;
    if (root.classList.contains("dark")) {
      root.classList.remove("dark");
      setIsDark(false);
    } else {
      root.classList.add("dark");
      setIsDark(true);
    }
  };

  // ---- Check API status ----
  useEffect(() => {
    const checkApi = async () => {
      setApiStatus({ online: null, loading: true });
      try {
        const [res0, res3] = await Promise.allSettled([
          fetch("/api/faz0/status", {
            method: "GET",
            signal: AbortSignal.timeout(5000),
          }),
          fetch("/api/faz3/status", {
            method: "GET",
            signal: AbortSignal.timeout(5000),
          }),
        ]);
        const data0 = res0.status === "fulfilled" ? await res0.value.json().catch(() => null) : null;
        const data3 = res3.status === "fulfilled" ? await res3.value.json().catch(() => null) : null;
        setApiStatus({
          online: (data0?.api_online ?? false) || (data3?.api_online ?? false),
          loading: false,
        });
      } catch {
        setApiStatus({ online: false, loading: false });
      }
    };
    checkApi();
    const interval = setInterval(checkApi, 15000);
    return () => clearInterval(interval);
  }, []);

  // ---- DNA Coverage chart data ----
  const dnaChartData = DNA_FACTORS.map((f) => {
    const moduleCount = f.moduleCoverage.length;
    const totalModules = 8;
    const coverage = f.status === "planned" ? 0 : Math.round((moduleCount / totalModules) * 100);
    return {
      name: `DNA-${f.id}`,
      coverage: Math.max(coverage, f.status === "planned" ? 0 : 12),
      status: f.status,
      fullName: f.name,
    };
  });

  // ---- Stats ----
  const implementedCount = DNA_FACTORS.filter((f) => f.status === "implemented").length;
  const inProgressCount = DNA_FACTORS.filter((f) => f.status === "in-progress").length;
  const plannedCount = DNA_FACTORS.filter((f) => f.status === "planned").length;
  const overallProgress = Math.round(((implementedCount + inProgressCount * 0.5) / DNA_FACTORS.length) * 100);

  // ============================================================
  // Render
  // ============================================================

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-muted/30 to-background">
      {/* ============ HEADER ============ */}
      <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Brand */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-sm">
                  <Route className="h-5 w-5 text-white" />
                </div>
                <div className="flex flex-col">
                  <span className="text-lg font-bold leading-tight tracking-tight">UniRide</span>
                  <span className="text-[10px] uppercase tracking-widest text-muted-foreground font-medium leading-tight">
                    FAZ 0–3 Tamamlandi
                  </span>
                </div>
              </div>
            </div>

            {/* Right side */}
            <div className="flex items-center gap-3">
              {/* API Status Indicator */}
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border bg-muted/50 text-sm">
                {apiStatus.loading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                ) : apiStatus.online ? (
                  <Wifi className="h-3.5 w-3.5 text-emerald-500" />
                ) : (
                  <WifiOff className="h-3.5 w-3.5 text-red-500" />
                )}
                <span
                  className={`text-xs font-medium ${
                    apiStatus.loading
                      ? "text-muted-foreground"
                      : apiStatus.online
                        ? "text-emerald-600 dark:text-emerald-400"
                        : "text-red-600 dark:text-red-400"
                  }`}
                >
                  {apiStatus.loading
                    ? "Baglaniyor..."
                    : apiStatus.online
                      ? "Optimizer Aktif"
                      : "Optimizer Kapali"}
                </span>
              </div>

              {/* Theme Toggle */}
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleTheme}
                className="h-9 w-9 rounded-full"
                aria-label="Tema Degistir"
              >
                {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* ============ MAIN CONTENT ============ */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* ============ HERO SECTION ============ */}
        <section className="relative overflow-hidden rounded-2xl mb-10">
          {/* Animated gradient background */}
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 via-teal-500/5 to-amber-500/10 dark:from-emerald-500/20 dark:via-teal-500/10 dark:to-amber-500/15" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-emerald-400/20 via-transparent to-transparent dark:from-emerald-400/10" />

          <div className="relative px-6 sm:px-10 py-10 sm:py-14">
            <div className="max-w-3xl">
              <div className="flex items-center gap-2 mb-4">
                <Badge className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs">
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  FAZ 0–3 Tamamlandi
                </Badge>
                <Badge variant="outline" className="text-xs">
                  v3.0.0
                </Badge>
              </div>
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight mb-4">
                Algoritma Gelistirme{" "}
                <span className="bg-gradient-to-r from-emerald-600 to-teal-600 dark:from-emerald-400 dark:to-teal-400 bg-clip-text text-transparent">
                  Framework
                </span>
              </h1>
              <p className="text-base sm:text-lg text-muted-foreground max-w-2xl mb-8">
                SOTA optimizasyon algoritmaları icin tamamlanmis framework. E²BSO, R²DMA ve
                P-AOEA algoritmalarinin tamamı uygulanmistir. 10/10 DNA kapsami.
              </p>

              {/* Stat Cards */}
              <div className="grid grid-cols-3 gap-3 sm:gap-4 max-w-lg">
                <div className="bg-white/70 dark:bg-slate-800/70 backdrop-blur-sm rounded-xl p-3 sm:p-4 border shadow-sm text-center">
                  <div className="flex items-center justify-center mb-1">
                    <Boxes className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <p className="text-2xl sm:text-3xl font-extrabold text-foreground">8</p>
                  <p className="text-[10px] sm:text-xs text-muted-foreground font-medium">Modul</p>
                </div>
                <div className="bg-white/70 dark:bg-slate-800/70 backdrop-blur-sm rounded-xl p-3 sm:p-4 border shadow-sm text-center">
                  <div className="flex items-center justify-center mb-1">
                    <GitBranch className="h-5 w-5 text-teal-600 dark:text-teal-400" />
                  </div>
                  <p className="text-2xl sm:text-3xl font-extrabold text-foreground">10</p>
                  <p className="text-[10px] sm:text-xs text-muted-foreground font-medium">DNA Faktoru</p>
                </div>
                <div className="bg-white/70 dark:bg-slate-800/70 backdrop-blur-sm rounded-xl p-3 sm:p-4 border shadow-sm text-center">
                  <div className="flex items-center justify-center mb-1">
                    <Brain className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                  </div>
                  <p className="text-2xl sm:text-3xl font-extrabold text-foreground">3</p>
                  <p className="text-[10px] sm:text-xs text-muted-foreground font-medium">Algoritma ✅</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ============ TABS: DNA / MODULES / ARCHITECTURE ============ */}
        <Tabs defaultValue="dna" className="mb-10">
          <TabsList className="grid w-full grid-cols-3 mb-6">
            <TabsTrigger value="dna" className="gap-1.5">
              <GitBranch className="h-4 w-4 hidden sm:block" />
              DNA Matrisi
            </TabsTrigger>
            <TabsTrigger value="modules" className="gap-1.5">
              <Package className="h-4 w-4 hidden sm:block" />
              Moduller
            </TabsTrigger>
            <TabsTrigger value="architecture" className="gap-1.5">
              <Layers className="h-4 w-4 hidden sm:block" />
              Mimari
            </TabsTrigger>
          </TabsList>

          {/* ========== DNA COVERAGE MATRIX ========== */}
          <TabsContent value="dna" className="mt-0 space-y-6">
            {/* Summary Stats */}
            <div className="grid grid-cols-3 gap-3 sm:gap-4">
              <Card className="p-4 text-center">
                <div className="flex items-center justify-center mb-1">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                </div>
                <p className="text-xl sm:text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                  {implementedCount}
                </p>
                <p className="text-[10px] sm:text-xs text-muted-foreground">Uygulandı</p>
              </Card>
              <Card className="p-4 text-center">
                <div className="flex items-center justify-center mb-1">
                  <RefreshCw className="h-4 w-4 text-amber-500" />
                </div>
                <p className="text-xl sm:text-2xl font-bold text-amber-600 dark:text-amber-400">
                  {inProgressCount}
                </p>
                <p className="text-[10px] sm:text-xs text-muted-foreground">Devam Ediyor</p>
              </Card>
              <Card className="p-4 text-center">
                <div className="flex items-center justify-center mb-1">
                  <Clock className="h-4 w-4 text-slate-400" />
                </div>
                <p className="text-xl sm:text-2xl font-bold text-slate-500 dark:text-slate-400">
                  {plannedCount}
                </p>
                <p className="text-[10px] sm:text-xs text-muted-foreground">Planlandı</p>
              </Card>
            </div>

            {/* DNA Factor Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {DNA_FACTORS.map((factor) => {
                const cfg = getStatusConfig(factor.status);
                return (
                  <Card
                    key={factor.id}
                    className={`${cfg.bgClass} ${cfg.borderClass} border transition-all hover:shadow-md`}
                  >
                    <CardHeader className="pb-2 pt-4 px-4">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="flex-shrink-0 inline-flex items-center justify-center h-7 w-7 rounded-lg bg-background/80 text-xs font-bold text-muted-foreground">
                            {factor.id}
                          </span>
                          <div className="min-w-0">
                            <CardTitle className="text-sm font-semibold leading-tight truncate">
                              {factor.name}
                            </CardTitle>
                          </div>
                        </div>
                        <Badge className={`flex-shrink-0 text-[10px] ${cfg.badgeClass}`}>
                          {cfg.icon}
                          <span className="ml-1 hidden sm:inline">{cfg.label}</span>
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="px-4 pb-4 pt-0">
                      <p className="text-xs text-muted-foreground mb-3 line-clamp-2">
                        {factor.description}
                      </p>
                      {factor.moduleCoverage.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {factor.moduleCoverage.map((mod) => (
                            <Badge
                              key={mod}
                              variant="outline"
                              className="text-[9px] px-1.5 py-0 bg-background/50"
                            >
                              {mod}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>

            {/* DNA Coverage Chart */}
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  <div className="bg-emerald-100 dark:bg-emerald-950/40 p-2 rounded-lg">
                    <Target className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div>
                    <CardTitle className="text-base">Modul Kapsam Orani</CardTitle>
                    <CardDescription className="text-xs mt-0.5">
                      Her DNA faktorunun kac modul tarafindan kapsandigi
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <ChartContainer config={CHART_CONFIG} className="h-[260px] w-full">
                  <BarChart data={dnaChartData} layout="vertical" margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
                    <YAxis type="category" dataKey="name" width={55} tick={{ fontSize: 11 }} />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Bar dataKey="coverage" radius={[0, 4, 4, 0]} maxBarSize={24}>
                      {dnaChartData.map((entry, index) => (
                        <Cell
                          key={index}
                          fill={
                            entry.status === "implemented"
                              ? "hsl(142, 76%, 36%)"
                              : entry.status === "in-progress"
                                ? "hsl(38, 92%, 50%)"
                                : "hsl(215, 16%, 47%)"
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ChartContainer>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ========== MODULES SECTION ========== */}
          <TabsContent value="modules" className="mt-0">
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-2">
                <Package className="h-5 w-5 text-primary" />
                <h2 className="text-xl font-bold">FAZ 0 Modulleri</h2>
                <Badge variant="outline" className="ml-1">8 modul</Badge>
              </div>

              <Accordion type="single" collapsible className="space-y-3">
                {FAZ_MODULES.map((mod) => {
                  const cfg = getStatusConfig(mod.status);
                  return (
                    <AccordionItem
                      key={mod.id}
                      value={mod.id}
                      className={`${cfg.bgClass} ${cfg.borderClass} border rounded-xl px-1 overflow-hidden`}
                    >
                      <AccordionTrigger className="hover:no-underline py-4 px-3">
                        <div className="flex items-center gap-3 flex-1 min-w-0 text-left">
                          <div className="flex-shrink-0 h-10 w-10 rounded-lg bg-background/80 flex items-center justify-center">
                            {mod.id === "multistart" && <FlaskConical className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />}
                            {mod.id === "multilayerls" && <Layers className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />}
                            {mod.id === "penalty" && <Shield className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />}
                            {mod.id === "acceptance" && <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />}
                            {mod.id === "destroy" && <Wrench className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />}
                            {mod.id === "repair" && <Wrench className="h-5 w-5 text-teal-600 dark:text-teal-400" />}
                            {mod.id === "diversity" && <GitBranch className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />}
                            {mod.id === "sota_common" && <Package className="h-5 w-5 text-amber-600 dark:text-amber-400" />}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-semibold text-sm">{mod.nameEn}</span>
                              <Badge className={`text-[9px] ${cfg.badgeClass}`}>
                                {cfg.label}
                              </Badge>
                            </div>
                            <p className="text-xs text-muted-foreground mt-0.5 truncate">{mod.nameTr}</p>
                          </div>
                        </div>
                      </AccordionTrigger>
                      <AccordionContent className="px-4 pb-4">
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                          {/* Left: Description + DNA + Methods */}
                          <div className="space-y-4">
                            <div>
                              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                                Amac
                              </h4>
                              <p className="text-sm leading-relaxed">{mod.purpose}</p>
                            </div>

                            <div>
                              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                                DNA Kapsami
                              </h4>
                              <div className="flex flex-wrap gap-1.5">
                                {mod.dnaCoverage.length > 0 ? (
                                  mod.dnaCoverage.map((dna) => (
                                    <Badge key={dna} variant="outline" className="text-xs">
                                      <GitBranch className="h-3 w-3 mr-1" />
                                      {dna}
                                    </Badge>
                                  ))
                                ) : (
                                  <span className="text-xs text-muted-foreground italic">Genel modul</span>
                                )}
                              </div>
                            </div>

                            <div>
                              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                                Temel Metotlar
                              </h4>
                              <div className="flex flex-wrap gap-1.5">
                                {mod.keyMethods.map((method) => (
                                  <Badge
                                    key={method}
                                    className="text-[10px] bg-muted/80 hover:bg-muted text-foreground"
                                  >
                                    <code className="text-[10px]">{method}</code>
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          </div>

                          {/* Right: Class Diagram */}
                          <div>
                            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                              Sinif Diyagrami
                            </h4>
                            <Card className="bg-slate-950 text-emerald-400 p-4 shadow-inner">
                              <pre className="text-[11px] leading-relaxed font-mono whitespace-pre overflow-x-auto">
                                {mod.classDiagram}
                              </pre>
                            </Card>
                          </div>
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  );
                })}
              </Accordion>
            </div>
          </TabsContent>

          {/* ========== ARCHITECTURE DIAGRAM ========== */}
          <TabsContent value="architecture" className="mt-0 space-y-6">
            {/* Architecture Overview */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <div className="bg-teal-100 dark:bg-teal-950/40 p-2 rounded-lg">
                    <Layers className="h-4 w-4 text-teal-600 dark:text-teal-400" />
                  </div>
                  <div>
                    <CardTitle className="text-base">SOTA Mimari Diyagrami</CardTitle>
                    <CardDescription className="text-xs mt-0.5">
                      Modullerin birbirleriyle ve algoritmalarla iliskisi
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="bg-slate-950 dark:bg-slate-950 rounded-xl p-4 sm:p-6 shadow-inner overflow-x-auto">
                  <pre className="text-[10px] sm:text-xs leading-relaxed font-mono text-slate-300 whitespace-pre">
{`
 ┌─────────────────────────────────────────────────────────────────────┐
 │                    UST KATMAN (Algoritma) ✅                       │
 │                                                                     │
 │  ┌──────────┐     ┌──────────┐     ┌──────────┐                    │
 │  │  E²BSO ✅│     │  R²DMA ✅│     │ P-AOEA ✅│   (FAZ 1-3)       │
 │  │ (FAZ 1)  │     │ (FAZ 2)  │     │ (FAZ 3)  │                    │
 │  └────┬─────┘     └────┬─────┘     └────┬─────┘                    │
 │       │                │                │                           │
 └───────┼────────────────┼────────────────┼───────────────────────────┘
         │                │                │
         ▼                ▼                ▼
 ┌─────────────────────────────────────────────────────────────────────┐
 │                      FAZ 0 — ORTAK ALTYAPI ✅                       │
 │                                                                     │
 │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
 │  │ MultiStart       │  │ MultiLayerLS    │  │ PenaltyManager  │     │
 │  │ Initializer      │  │                 │  │                 │     │
 │  │ (DNA-6)          │  │ (DNA-3)         │  │ (DNA-4, DNA-9)  │     │
 │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘     │
 │           │                    │                    │               │
 │           ▼                    ▼                    ▼               │
 │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
 │  │ Acceptance       │  │ Destroy          │  │ Repair           │     │
 │  │ Criterion        │  │ Operators        │  │ Operators        │     │
 │  │ (DNA-7)          │  │ (DNA-1, DNA-2)   │  │ (DNA-1, DNA-2)   │     │
 │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘     │
 │           │                    │                    │               │
 │           ▼                    ▼                    ▼               │
 │  ┌─────────────────────────────────────────────────────────┐       │
 │  │              DiversityController (DNA-4, DNA-8)         │       │
 │  └────────────────────────┬────────────────────────────────┘       │
 │                           │                                         │
 │  ┌────────────────────────┴────────────────────────────────┐       │
 │  │              sota_common (Export Modulu, DNA-5)          │       │
 │  └─────────────────────────────────────────────────────────┘       │
 └─────────────────────────────────────────────────────────────────────┘
         │                │                │
         ▼                ▼                ▼
 ┌─────────────────────────────────────────────────────────────────────┐
 │                         ALT KATMAN (Veri)                           │
 │                                                                     │
 │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
 │  │  TSPLIB      │  │  Solomon     │  │  Gercek      │              │
 │  │  Veri Seti   │  │  Veri Seti   │  │  Dunya Data  │              │
 │  └──────────────┘  └──────────────┘  └──────────────┘              │
 └─────────────────────────────────────────────────────────────────────┘
`}
                  </pre>
                </div>
              </CardContent>
            </Card>

            {/* Data Flow Diagram */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <div className="bg-emerald-100 dark:bg-emerald-950/40 p-2 rounded-lg">
                    <ArrowRight className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div>
                    <CardTitle className="text-base">Veri Akisi</CardTitle>
                    <CardDescription className="text-xs mt-0.5">
                      Problem → FAZ 0 → Algoritma → Cozum akisi
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="bg-slate-950 dark:bg-slate-950 rounded-xl p-4 sm:p-6 shadow-inner overflow-x-auto">
                  <pre className="text-[10px] sm:text-xs leading-relaxed font-mono text-slate-300 whitespace-pre">
{`
  Veri Akisi: FAZ 0 Optimizasyon Pipeline

  ┌───────────┐     ┌───────────────┐     ┌───────────────┐     ┌───────────┐
  │  Problem   │────▶│ MultiStart    │────▶│ ALNS Döngüsü  │────▶│ Lokal     │
  │  Tanımı    │     │ Initializer   │     │               │     │ Arama     │
  │            │     │ (cesitli      │     │ Destroy →     │     │           │
  │ TSP/CVRP   │     │  baslangic)   │     │ Repair →      │     │ 2-opt     │
  │ VRPTW      │     └───────┬───────┘     │ Acceptance    │     │ Or-opt    │
  └───────────┘             │             └───────┬───────┘     │ 3-opt     │
                            │                     │             │ Swap      │
                            ▼                     ▼             └─────┬─────┘
                     ┌─────────────────────────────────┐             │
                     │        PenaltyManager           │             │
                     │   (kisit ihlalleri cezalandirma) │             │
                     └───────────────┬─────────────────┘             │
                                     │                               │
                                     ▼                               ▼
                              ┌───────────────┐              ┌───────────┐
                              │   En Iyi      │◀─────────────│ Gelistir- │
                              │   Cozum       │              │ miş Cozum │
                              └───────────────┘              └───────────┘
`}
                  </pre>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* ============ IMPROVEMENT ROADMAP ============ */}
        <section className="mb-10">
          <div className="flex items-center gap-2 mb-5">
            <TrendingUp className="h-5 w-5 text-primary" />
            <h2 className="text-xl font-bold">Gelistirme Yol Haritasi</h2>
          </div>

          {/* Overall Progress */}
          <Card className="mb-6">
            <CardContent className="py-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Genel Framework Ilerlemesi</span>
                <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400">{overallProgress}%</span>
              </div>
              <Progress value={overallProgress} className="h-3" />
              <p className="text-[10px] text-muted-foreground mt-1.5">
                4/4 FAZ tamamlandi — DNA kapsami: 10/10
              </p>
            </CardContent>
          </Card>

          {/* Phase Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {ROADMAP_PHASES.map((phase) => (
              <Card
                key={phase.phase}
                className={`border-2 ${getPhaseCardStyles(phase)} transition-all hover:shadow-md`}
              >
                <CardHeader className="pb-2 pt-4 px-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="flex-shrink-0 mt-0.5">{phase.icon}</div>
                      <div>
                        <CardTitle className="text-sm font-bold">{phase.name}</CardTitle>
                        <p className="text-xs text-muted-foreground mt-0.5">{phase.description}</p>
                      </div>
                    </div>
                    {phase.status === "current" && (
                      <Badge className="bg-emerald-600 hover:bg-emerald-700 text-white text-[10px] flex-shrink-0">
                        Tamamlandi
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="px-4 pb-4 pt-0">
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="bg-background/60 rounded-lg p-2">
                      <p className="text-[10px] text-muted-foreground">Hedef</p>
                      <p className="text-xs font-semibold mt-0.5">{phase.targetAlgorithms}</p>
                    </div>
                    <div className="bg-background/60 rounded-lg p-2">
                      <p className="text-[10px] text-muted-foreground">DNA</p>
                      <p className="text-xs font-semibold mt-0.5">{phase.dnaFactors} faktor</p>
                    </div>
                    <div className="bg-background/60 rounded-lg p-2">
                      <p className="text-[10px] text-muted-foreground">Gap</p>
                      <p className="text-xs font-semibold mt-0.5">{phase.expectedGapImprovement}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* ============ PERFORMANCE TARGETS ============ */}
        <section className="mb-10">
          <div className="flex items-center gap-2 mb-5">
            <Target className="h-5 w-5 text-primary" />
            <h2 className="text-xl font-bold">Performans Hedefleri</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* TSPLIB Gap */}
            <Card className="relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-500 to-teal-500" />
              <CardContent className="pt-6 pb-4 px-4 text-center">
                <div className="flex items-center justify-center mb-2">
                  <div className="h-12 w-12 rounded-full bg-emerald-100 dark:bg-emerald-950/40 flex items-center justify-center">
                    <Cpu className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                  </div>
                </div>
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                  TSPLIB Gap
                </p>
                <div className="mb-2">
                  <span className="text-3xl font-extrabold text-emerald-600 dark:text-emerald-400">
                    &lt;3%
                  </span>
                </div>
                <p className="text-[10px] text-muted-foreground mb-3">
                  Optimizasyon sonrasi hedef gap
                </p>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="text-muted-foreground">Mevcut</span>
                    <span className="font-semibold text-red-500">~20%</span>
                  </div>
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="text-muted-foreground">Hedef</span>
                    <span className="font-semibold text-emerald-600 dark:text-emerald-400">&lt;3%</span>
                  </div>
                  <Progress value={15} className="h-1.5 mt-1" />
                </div>
              </CardContent>
            </Card>

            {/* CVRPTW Gap */}
            <Card className="relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-amber-500 to-orange-500" />
              <CardContent className="pt-6 pb-4 px-4 text-center">
                <div className="flex items-center justify-center mb-2">
                  <div className="h-12 w-12 rounded-full bg-amber-100 dark:bg-amber-950/40 flex items-center justify-center">
                    <FlaskConical className="h-6 w-6 text-amber-600 dark:text-amber-400" />
                  </div>
                </div>
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                  CVRPTW Gap
                </p>
                <div className="mb-2">
                  <span className="text-3xl font-extrabold text-amber-600 dark:text-amber-400">
                    &lt;5%
                  </span>
                </div>
                <p className="text-[10px] text-muted-foreground mb-3">
                  Solomon veri seti hedef
                </p>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="text-muted-foreground">Mevcut</span>
                    <span className="font-semibold text-red-500">~25%</span>
                  </div>
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="text-muted-foreground">Hedef</span>
                    <span className="font-semibold text-amber-600 dark:text-amber-400">&lt;5%</span>
                  </div>
                  <Progress value={12} className="h-1.5 mt-1" />
                </div>
              </CardContent>
            </Card>

            {/* Academic Plan */}
            <Card className="relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 to-pink-500" />
              <CardContent className="pt-6 pb-4 px-4 text-center">
                <div className="flex items-center justify-center mb-2">
                  <div className="h-12 w-12 rounded-full bg-purple-100 dark:bg-purple-950/40 flex items-center justify-center">
                    <BookOpen className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                  </div>
                </div>
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                  Akademik
                </p>
                <div className="mb-2">
                  <span className="text-3xl font-extrabold text-purple-600 dark:text-purple-400">
                    3
                  </span>
                  <span className="text-sm font-medium text-muted-foreground ml-1">Makale</span>
                </div>
                <p className="text-[10px] text-muted-foreground mb-3">
                  GECCO, AAAI, IEEE TEVC hedef
                </p>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="text-muted-foreground">E²BSO (GECCO)</span>
                    <Badge className="text-[8px] h-3 bg-amber-600 text-white px-1">Plan</Badge>
                  </div>
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="text-muted-foreground">R²DMA (AAAI)</span>
                    <Badge className="text-[8px] h-3 bg-slate-500 text-white px-1">Plan</Badge>
                  </div>
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="text-muted-foreground">P-AOEA (TEVC)</span>
                    <Badge className="text-[8px] h-3 bg-slate-500 text-white px-1">Plan</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* ============ QUICK ACTIONS ============ */}
        <section className="mb-10">
          <div className="flex items-center gap-2 mb-5">
            <Zap className="h-5 w-5 text-primary" />
            <h2 className="text-xl font-bold">Hizli Erisim</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Benchmark Suite */}
            <Button
              asChild
              className="h-auto p-0 bg-background border border-border hover:bg-muted/50 transition-all group"
            >
              <a href="/admin/benchmark" className="block p-4">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-emerald-100 dark:bg-emerald-950/40 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                    <FlaskConical className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div className="text-left min-w-0 flex-1">
                    <p className="text-sm font-semibold text-foreground flex items-center gap-1">
                      Benchmark Suite
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      TSPLIB benchmark calistirmalari ve sonuclari
                    </p>
                  </div>
                </div>
              </a>
            </Button>

            {/* Optimizer API Status */}
            <Card className="hover:shadow-md transition-all cursor-default">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div
                    className={`h-10 w-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      apiStatus.online
                        ? "bg-emerald-100 dark:bg-emerald-950/40"
                        : "bg-red-100 dark:bg-red-950/40"
                    }`}
                  >
                    {apiStatus.loading ? (
                      <Loader2 className="h-5 w-5 text-muted-foreground animate-spin" />
                    ) : apiStatus.online ? (
                      <Wifi className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                    ) : (
                      <WifiOff className="h-5 w-5 text-red-500" />
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-foreground">Optimizer API Durumu</p>
                    <p
                      className={`text-xs mt-0.5 ${
                        apiStatus.online
                          ? "text-emerald-600 dark:text-emerald-400"
                          : "text-red-600 dark:text-red-400"
                      }`}
                    >
                      {apiStatus.loading
                        ? "Kontrol ediliyor..."
                        : apiStatus.online
                          ? "Online — 16 algoritma hazir"
                          : "Offline — Servis baslatilmadi"}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Documentation */}
            <Button
              asChild
              className="h-auto p-0 bg-background border border-border hover:bg-muted/50 transition-all group"
            >
              <a href="/admin/benchmark" className="block p-4">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-purple-100 dark:bg-purple-950/40 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                    <BookOpen className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div className="text-left min-w-0 flex-1">
                    <p className="text-sm font-semibold text-foreground flex items-center gap-1">
                      Dokumantasyon
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Mimari, yol haritasi ve gelistirme kilavuzu
                    </p>
                  </div>
                </div>
              </a>
            </Button>
          </div>
        </section>
      </main>

      {/* ============ FOOTER ============ */}
      <footer className="border-t bg-background/80 backdrop-blur-md mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded-md bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
                <Route className="h-3.5 w-3.5 text-white" />
              </div>
              <span className="text-sm font-semibold">UniRide SOTA Framework</span>
              <Separator orientation="vertical" className="h-4 mx-1" />
              <span className="text-xs text-muted-foreground">FAZ 0–3 Tamamlandi</span>
            </div>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <Badge variant="outline" className="text-[10px]">
                v3.0.0
              </Badge>
              <span>&copy; {new Date().getFullYear()} UniRide</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
