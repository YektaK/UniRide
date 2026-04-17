"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
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
  ChevronDown,
  ChevronUp,
  ScrollText,
  Timer,
  TrendingUp,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import {
  ALGORITHM_OPTIONS_GROUPED,
  ALGORITHM_DISPLAY_NAMES,
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
} from "recharts";

// ============================================================
// Constants
// ============================================================

const POLL_INTERVAL_MS = 2000;

const CHART_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
  "hsl(210, 70%, 50%)",
  "hsl(150, 60%, 45%)",
  "hsl(30, 80%, 55%)",
  "hsl(280, 60%, 55%)",
  "hsl(0, 70%, 55%)",
  "hsl(190, 70%, 50%)",
  "hsl(60, 70%, 45%)",
  "hsl(330, 60%, 50%)",
  "hsl(120, 50%, 40%)",
];

// ============================================================
// Category label helpers
// ============================================================

function getCategoryLabel(cat: string): string {
  switch (cat) {
    case "small": return "Küçük";
    case "medium": return "Orta";
    case "large": return "Büyük";
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

function getStatusBadge(status: string) {
  switch (status) {
    case "running":
      return <Badge className="bg-blue-600 hover:bg-blue-700"><Activity className="h-3 w-3 mr-1 animate-pulse" /> Çalışıyor</Badge>;
    case "completed":
      return <Badge className="bg-green-600 hover:bg-green-700"><CheckCircle2 className="h-3 w-3 mr-1" /> Tamamlandı</Badge>;
    case "failed":
      return <Badge variant="destructive"><AlertCircle className="h-3 w-3 mr-1" /> Başarısız</Badge>;
    case "stopped":
      return <Badge variant="outline" className="border-amber-500 text-amber-700"><Square className="h-3 w-3 mr-1" /> Durduruldu</Badge>;
    case "queued":
      return <Badge variant="secondary"><Clock className="h-3 w-3 mr-1" /> Sıraya Alındı</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

// ============================================================
// Main Page Component
// ============================================================

export default function BenchmarkPage() {
  const { toast } = useToast();

  // ---- State ----
  const [activeTab, setActiveTab] = useState("config");
  const [isApiOnline, setIsApiOnline] = useState<boolean | null>(null);

  // Problems
  const [problems, setProblems] = useState<BenchmarkProblem[]>([]);
  const [problemsLoading, setProblemsLoading] = useState(true);
  const [problemCategoryFilter, setProblemCategoryFilter] = useState<string>("all");
  const [selectedProblems, setSelectedProblems] = useState<Set<string>>(new Set());

  // Algorithms
  const [selectedAlgorithms, setSelectedAlgorithms] = useState<Set<string>>(new Set());

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

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ---- Check API availability ----
  useEffect(() => {
    const checkApi = async () => {
      try {
        const res = await fetch("/api/v1/strategies?XTransformPort=8099", {
          method: "GET",
          signal: AbortSignal.timeout(5000),
        });
        setIsApiOnline(res.ok);
      } catch {
        setIsApiOnline(false);
      }
    };
    checkApi();
  }, []);

  // ---- Fetch problems ----
  useEffect(() => {
    const load = async () => {
      setProblemsLoading(true);
      try {
        const data = await fetchProblems();
        setProblems(data);
      } catch (err) {
        console.error("Failed to load problems:", err);
        toast({
          title: "Problemler Yüklenemedi",
          description: err instanceof Error ? err.message : "Sunucuya ulaşılamadı",
          variant: "destructive",
        });
      } finally {
        setProblemsLoading(false);
      }
    };
    load();
  }, [toast]);

  // ---- Cleanup polling ----
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  // ---- Polling logic ----
  const startPolling = useCallback((rid: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const status = await pollStatus(rid);
        setRunStatus(status);

        if (status.status === "completed" || status.status === "failed" || status.status === "stopped") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;

          // Auto-switch to results tab
          if (status.status === "completed") {
            setActiveTab("results");
            // Auto-fetch results
            try {
              setResultsLoading(true);
              const res = await fetchResults(rid);
              setResults(res);
            } catch {
              toast({
                title: "Sonuçlar Alınamadı",
                description: "Benchmark tamamlandı ancak sonuçlar yüklenemedi.",
                variant: "destructive",
              });
            } finally {
              setResultsLoading(false);
            }
          }
        }
      } catch {
        // Silently continue polling on transient errors
      }
    }, POLL_INTERVAL_MS);
  }, [toast]);

  // ---- Handlers ----
  const handleStartBenchmark = async () => {
    if (selectedProblems.size === 0 || selectedAlgorithms.size === 0) return;

    setIsStarting(true);
    try {
      const algorithms: BenchmarkAlgorithm[] = Array.from(selectedAlgorithms).map((id) => ({ id }));
      const problemsArr = Array.from(selectedProblems);
      const settings: BenchmarkRunSettings = { n_runs: nRuns, seed };

      const response = await startBenchmark(algorithms, problemsArr, settings);
      setRunId(response.run_id);
      setActiveTab("execution");

      toast({
        title: "Benchmark Başlatıldı",
        description: `Çalışma ID: ${response.run_id} — ${response.total_experiments} deney kuyruğa alındı.`,
      });

      // Start polling
      startPolling(response.run_id);
    } catch (err) {
      toast({
        title: "Benchmark Başlatılamadı",
        description: err instanceof Error ? err.message : "Sunucu hatası",
        variant: "destructive",
      });
    } finally {
      setIsStarting(false);
    }
  };

  const handleStopBenchmark = async () => {
    if (!runId) return;
    setIsStopping(true);
    try {
      await stopBenchmark(runId);
      toast({
        title: "Benchmark Durduruldu",
        description: "Çalışma sonlandırılıyor...",
      });
    } catch (err) {
      toast({
        title: "Durdurma Başarısız",
        description: err instanceof Error ? err.message : "Sunucu hatası",
        variant: "destructive",
      });
    } finally {
      setIsStopping(false);
    }
  };

  const handleExportResults = () => {
    if (!results) return;
    const blob = new Blob([JSON.stringify(results, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `benchmark-${runId || "results"}-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast({ title: "Dışa Aktarıldı", description: "Sonuçlar JSON olarak indirildi." });
  };

  const handleManualFetchResults = async () => {
    if (!runId) return;
    setResultsLoading(true);
    try {
      const res = await fetchResults(runId);
      setResults(res);
      toast({ title: "Sonuçlar Yüklendi", description: `${res.results.length} sonuç getirildi.` });
    } catch (err) {
      toast({
        title: "Sonuçlar Alınamadı",
        description: err instanceof Error ? err.message : "Sunucu hatası",
        variant: "destructive",
      });
    } finally {
      setResultsLoading(false);
    }
  };

  // ---- Problem selection helpers ----
  const filteredProblems = problems.filter(
    (p) => problemCategoryFilter === "all" || p.category === problemCategoryFilter
  );

  const toggleProblem = (name: string) => {
    setSelectedProblems((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const selectAllProblems = () => {
    setSelectedProblems(new Set(filteredProblems.map((p) => p.name)));
  };

  const deselectAllProblems = () => {
    setSelectedProblems(new Set());
  };

  // ---- Algorithm selection helpers ----
  const toggleAlgorithm = (key: string) => {
    setSelectedAlgorithms((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const selectAllAlgorithms = () => {
    const keys: string[] = ALGORITHM_OPTIONS_GROUPED.flatMap((g) => g.algorithms.map((a: any) => String(a.key)));
    setSelectedAlgorithms(new Set(keys));
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const selectRecommendedAlgorithms = () => {
    const allAlgos: any[] = [];
    for (const g of ALGORITHM_OPTIONS_GROUPED) {
      for (const a of g.algorithms) {
        allAlgos.push(a);
      }
    }
    const keys: string[] = allAlgos.filter((a) => a.recommended).map((a) => String(a.key));
    setSelectedAlgorithms(new Set(keys));
  };

  // ---- Result analytics ----
  const getAnalytics = useCallback(() => {
    if (!results || !results.results.length) return null;

    const allResults = results.results;
    const totalExperiments = allResults.length;
    const totalTimeMs = allResults.reduce((s, r) => s + r.elapsed_ms, 0);
    const successfulResults = allResults.filter((r) => r.gap_percent !== null);
    const successRate = totalExperiments > 0 ? (successfulResults.length / totalExperiments) * 100 : 0;

    // Group by algorithm
    const byAlgorithm = new Map<string, BenchmarkResult[]>();
    for (const r of allResults) {
      if (!byAlgorithm.has(r.algorithm)) byAlgorithm.set(r.algorithm, []);
      byAlgorithm.get(r.algorithm)!.push(r);
    }

    const algorithmStats = Array.from(byAlgorithm.entries()).map(([algo, res]) => {
      const gaps = res.filter((r) => r.gap_percent !== null).map((r) => r.gap_percent!);
      const times = res.map((r) => r.elapsed_ms);
      const tours = res.map((r) => r.tour_length);
      return {
        algorithm: algo,
        displayName: ALGORITHM_DISPLAY_NAMES[algo] || algo,
        count: res.length,
        avgGap: gaps.length > 0 ? gaps.reduce((s, g) => s + g, 0) / gaps.length : null,
        minGap: gaps.length > 0 ? Math.min(...gaps) : null,
        maxGap: gaps.length > 0 ? Math.max(...gaps) : null,
        avgTime: times.reduce((s, t) => s + t, 0) / times.length,
        minTour: Math.min(...tours),
        maxTour: Math.max(...tours),
        avgTour: tours.reduce((s, t) => s + t, 0) / tours.length,
      };
    }).sort((a, b) => (a.avgGap ?? Infinity) - (b.avgGap ?? Infinity));

    // Group by problem
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
      return {
        problem: prob,
        optimal,
        bestTour,
        bestAlgorithm: bestResult?.algorithm || "",
        bestAlgorithmName: ALGORITHM_DISPLAY_NAMES[bestResult?.algorithm || ""] || bestResult?.algorithm || "",
        gapFromOptimal: optimal ? ((bestTour - optimal) / optimal) * 100 : null,
        algorithmsTested: new Set(res.map((r) => r.algorithm)).size,
      };
    }).sort((a, b) => a.problem.localeCompare(b.problem));

    return {
      totalExperiments,
      totalTimeMs,
      successRate,
      algorithmStats,
      problemStats,
    };
  }, [results, problems]);

  // ---- Chart data ----
  const gapChartData = getAnalytics()?.algorithmStats
    .filter((s) => s.avgGap !== null)
    .map((s) => ({ algorithm: s.displayName, gap: Number(s.avgGap!.toFixed(2)), fill: CHART_COLORS[0] }));

  const timeChartData = getAnalytics()?.algorithmStats
    .map((s) => ({ algorithm: s.displayName, time: Number(s.avgTime.toFixed(1)), fill: CHART_COLORS[1] }));

  // ============================================================
  // Render
  // ============================================================

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2">
            <FlaskConical className="text-primary" /> Benchmark Suite
          </CardTitle>
          <CardDescription>
            TSPLIB standart veri setleri üzerinde algoritma karşılaştırma testleri çalıştırın.
            Sistematik benchmark ile algoritmaların kalite ve performansını ölçün.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            <div className={`h-2 w-2 rounded-full ${isApiOnline === null ? "bg-gray-400" : isApiOnline ? "bg-green-500" : "bg-red-500"}`} />
            <span className="text-sm text-muted-foreground">
              {isApiOnline === null ? "Bağlantı kontrol ediliyor..." : isApiOnline ? "Python Optimizer API çevrimiçi" : "Python Optimizer API çevrimdışı"}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="config">
            <Target className="h-4 w-4 mr-1.5 hidden sm:inline" />
            Yapılandırma
          </TabsTrigger>
          <TabsTrigger value="execution" disabled={!runId}>
            <Activity className="h-4 w-4 mr-1.5 hidden sm:inline" />
            Çalışma
            {runStatus?.status === "running" && (
              <span className="ml-1.5 h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
            )}
          </TabsTrigger>
          <TabsTrigger value="results" disabled={!results}>
            <BarChart3 className="h-4 w-4 mr-1.5 hidden sm:inline" />
            Sonuçlar
          </TabsTrigger>
        </TabsList>

        {/* ============================================ */}
        {/* TAB 1: CONFIGURATION */}
        {/* ============================================ */}
        <TabsContent value="config" className="space-y-6 mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Problem Selection */}
            <Card className="lg:col-span-2 shadow-md">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <ScrollText className="h-5 w-5 text-primary" /> Problem Seçimi
                    </CardTitle>
                    <CardDescription className="mt-1">
                      TSPLIB test problemlerinden benchmark için seçim yapın
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{selectedProblems.size} seçili</Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Category filter */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-muted-foreground mr-1">Kategori:</span>
                  {["all", "small", "medium", "large"].map((cat) => (
                    <Button
                      key={cat}
                      size="sm"
                      variant={problemCategoryFilter === cat ? "default" : "outline"}
                      onClick={() => setProblemCategoryFilter(cat)}
                    >
                      {cat === "all" ? "Tümü" : getCategoryLabel(cat)}
                    </Button>
                  ))}
                  <div className="ml-auto flex gap-2">
                    <Button size="sm" variant="ghost" onClick={selectAllProblems}>
                      Tümünü Seç
                    </Button>
                    <Button size="sm" variant="ghost" onClick={deselectAllProblems}>
                      Seçimi Kaldır
                    </Button>
                  </div>
                </div>

                {/* Problems list */}
                {problemsLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    <span className="ml-2 text-muted-foreground">Problemler yükleniyor...</span>
                  </div>
                ) : filteredProblems.length === 0 ? (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>Problem Bulunamadı</AlertTitle>
                    <AlertDescription>
                      Bu kategoride uyumlu problem bulunamadı.
                    </AlertDescription>
                  </Alert>
                ) : (
                  <div className="max-h-96 overflow-y-auto rounded-md border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-10">✓</TableHead>
                          <TableHead>Problem</TableHead>
                          <TableHead className="text-center">Boyut</TableHead>
                          <TableHead className="text-center">Optimal</TableHead>
                          <TableHead className="text-center">Kategori</TableHead>
                          <TableHead className="text-center">Tip</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {filteredProblems.map((p) => (
                          <TableRow
                            key={p.name}
                            className={`cursor-pointer ${selectedProblems.has(p.name) ? "bg-primary/5" : ""}`}
                            onClick={() => toggleProblem(p.name)}
                          >
                            <TableCell>
                              <Checkbox
                                checked={selectedProblems.has(p.name)}
                                onCheckedChange={() => toggleProblem(p.name)}
                              />
                            </TableCell>
                            <TableCell className="font-mono font-medium">{p.name}</TableCell>
                            <TableCell className="text-center">{p.dimension}</TableCell>
                            <TableCell className="text-center font-mono text-sm">
                              {p.optimal !== null ? p.optimal.toLocaleString() : "-"}
                            </TableCell>
                            <TableCell className="text-center">
                              <Badge variant={getCategoryBadgeVariant(p.category)}>
                                {getCategoryLabel(p.category)}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-center text-xs text-muted-foreground">
                              {p.problem_type || p.edge_weight_type || "TSP"}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Algorithm Selection + Settings */}
            <div className="space-y-6">
              {/* Algorithm Selection */}
              <Card className="shadow-md">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Zap className="h-5 w-5 text-primary" /> Algoritma Seçimi
                      </CardTitle>
                      <CardDescription className="mt-1">
                        Test edilecek algoritmaları seçin
                      </CardDescription>
                    </div>
                    <Badge variant="outline">{selectedAlgorithms.size} seçili</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex gap-2 flex-wrap">
                    <Button size="sm" variant="ghost" onClick={selectAllAlgorithms}>
                      Hepsini Seç
                    </Button>
                    <Button size="sm" variant="ghost" onClick={selectRecommendedAlgorithms}>
                      Önerilenler
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setSelectedAlgorithms(new Set())}>
                      Seçimi Kaldır
                    </Button>
                  </div>

                  <div className="max-h-80 overflow-y-auto space-y-3">
                    {ALGORITHM_OPTIONS_GROUPED.map((group) => (
                      <div key={group.category}>
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5 px-1">
                          {group.category}
                        </p>
                        <div className="space-y-1">
                          {group.algorithms.map((alg) => (
                            <label
                              key={alg.key}
                              className={`flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer transition-colors hover:bg-muted/50 ${selectedAlgorithms.has(alg.key) ? "bg-primary/5" : ""}`}
                            >
                              <Checkbox
                                checked={selectedAlgorithms.has(alg.key)}
                                onCheckedChange={() => toggleAlgorithm(alg.key)}
                              />
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-1.5">
                                  <span className="text-sm font-medium truncate">{alg.label}</span>
                                  {alg.recommended && (
                                    <Badge variant="default" className="text-[9px] px-1 py-0 h-3.5 bg-emerald-600 hover:bg-emerald-700">
                                      Önerilen
                                    </Badge>
                                  )}
                                  {"badge" in alg && alg.badge && (
                                    <Badge variant="secondary" className="text-[9px] px-1 py-0 h-3.5">
                                      {String(alg.badge)}
                                    </Badge>
                                  )}
                                </div>
                              </div>
                            </label>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Settings */}
              <Card className="shadow-md">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Timer className="h-5 w-5 text-primary" /> Ayarlar
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="n_runs">Tekrar Sayısı (n_runs)</Label>
                    <Input
                      id="n_runs"
                      type="number"
                      min={1}
                      max={100}
                      value={nRuns}
                      onChange={(e) => setNRuns(Math.max(1, parseInt(e.target.value) || 1))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Her algoritma-problem çifti için kaç kez çalıştırılacak
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="seed">Rastgele Tohum (seed)</Label>
                    <Input
                      id="seed"
                      type="number"
                      value={seed}
                      onChange={(e) => setSeed(parseInt(e.target.value) || 0)}
                    />
                    <p className="text-xs text-muted-foreground">
                      Tekrarlanabilir sonuçlar için sabit tohum
                    </p>
                  </div>

                  {/* Summary */}
                  <div className="p-3 rounded-md bg-muted text-sm space-y-1">
                    <p className="font-semibold">Özet</p>
                    <p className="text-muted-foreground">
                      <span className="font-medium text-foreground">{selectedAlgorithms.size}</span> algoritma ×{" "}
                      <span className="font-medium text-foreground">{selectedProblems.size}</span> problem ×{" "}
                      <span className="font-medium text-foreground">{nRuns}</span> çalışma ={" "}
                      <span className="font-bold text-foreground">
                        {selectedAlgorithms.size * selectedProblems.size * nRuns}
                      </span>{" "}
                      deney
                    </p>
                  </div>
                </CardContent>
              </Card>

              {/* Start Button */}
              <Button
                size="lg"
                className="w-full"
                disabled={
                  isStarting ||
                  selectedProblems.size === 0 ||
                  selectedAlgorithms.size === 0 ||
                  isApiOnline === false
                }
                onClick={handleStartBenchmark}
              >
                {isStarting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Başlatılıyor...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Benchmark Başlat
                  </>
                )}
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* ============================================ */}
        {/* TAB 2: EXECUTION */}
        {/* ============================================ */}
        <TabsContent value="execution" className="space-y-6 mt-6">
          {!runId && !runStatus ? (
            <Card className="shadow-md">
              <CardContent className="py-16 text-center">
                <FlaskConical className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">Henüz Çalışma Yok</h3>
                <p className="text-muted-foreground">
                  Benchmark başlatmak için &quot;Yapılandırma&quot; sekmesine gidin ve algoritmaları problemleri seçip çalıştırın.
                </p>
              </CardContent>
            </Card>
          ) : (
            <>
              {/* Run Info */}
              <Card className="shadow-md">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Activity className="h-5 w-5 text-primary" /> Benchmark Çalışması
                  </CardTitle>
                  <CardDescription>
                    Çalışma ID: <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">{runId}</span>
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {runStatus && (
                    <>
                      {/* Status & Progress */}
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            {getStatusBadge(runStatus.status)}
                          </div>
                          <span className="text-2xl font-bold tabular-nums">
                            {runStatus.progress_percent.toFixed(1)}%
                          </span>
                        </div>

                        <Progress value={runStatus.progress_percent} className="h-4" />

                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                          <div className="p-3 rounded-md bg-muted">
                            <p className="text-muted-foreground text-xs">Toplam Deney</p>
                            <p className="font-semibold text-lg">{runStatus.total_experiments}</p>
                          </div>
                          <div className="p-3 rounded-md bg-muted">
                            <p className="text-muted-foreground text-xs">Tamamlanan</p>
                            <p className="font-semibold text-lg">{runStatus.completed_experiments}</p>
                          </div>
                          <div className="p-3 rounded-md bg-muted">
                            <p className="text-muted-foreground text-xs">Sonuç Sayısı</p>
                            <p className="font-semibold text-lg">{runStatus.results_count}</p>
                          </div>
                          <div className="p-3 rounded-md bg-muted">
                            <p className="text-muted-foreground text-xs">Başlangıç</p>
                            <p className="font-semibold text-xs">{new Date(runStatus.start_time).toLocaleTimeString("tr-TR")}</p>
                          </div>
                        </div>

                        {/* Message */}
                        {runStatus.message && (
                          <Alert>
                            <Activity className="h-4 w-4" />
                            <AlertTitle>Durum</AlertTitle>
                            <AlertDescription className="font-mono text-xs">{runStatus.message}</AlertDescription>
                          </Alert>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex gap-3">
                        {runStatus.status === "running" && (
                          <Button
                            variant="destructive"
                            onClick={handleStopBenchmark}
                            disabled={isStopping}
                          >
                            {isStopping ? (
                              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Durduruluyor...</>
                            ) : (
                              <><Square className="mr-2 h-4 w-4" /> Benchmark Durdur</>
                            )}
                          </Button>
                        )}
                        {(runStatus.status === "completed" || runStatus.status === "stopped" || runStatus.status === "failed") && (
                          <Button onClick={handleManualFetchResults} disabled={resultsLoading}>
                            {resultsLoading ? (
                              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Yükleniyor...</>
                            ) : (
                              <><BarChart3 className="mr-2 h-4 w-4" /> Sonuçları Görüntüle</>
                            )}
                          </Button>
                        )}
                      </div>
                    </>
                  )}

                  {!runStatus && (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                      <span className="ml-2 text-muted-foreground">Durum yükleniyor...</span>
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>

        {/* ============================================ */}
        {/* TAB 3: RESULTS */}
        {/* ============================================ */}
        <TabsContent value="results" className="space-y-6 mt-6">
          {resultsLoading ? (
            <Card className="shadow-md">
              <CardContent className="py-16 text-center">
                <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary mb-4" />
                <p className="text-muted-foreground">Sonuçlar yükleniyor...</p>
              </CardContent>
            </Card>
          ) : results && results.results.length > 0 ? (() => {
            const analytics = getAnalytics();
            if (!analytics) return null;
            return (
              <>
                {/* Summary Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <Card className="shadow-md">
                    <CardContent className="p-4">
                      <div className="flex items-center gap-3">
                        <div className="bg-primary/10 p-2.5 rounded-lg">
                          <Activity className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Toplam Deney</p>
                          <p className="text-2xl font-bold">{analytics.totalExperiments}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="shadow-md">
                    <CardContent className="p-4">
                      <div className="flex items-center gap-3">
                        <div className="bg-blue-500/10 p-2.5 rounded-lg">
                          <Clock className="h-5 w-5 text-blue-600" />
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Toplam Süre</p>
                          <p className="text-2xl font-bold">{(analytics.totalTimeMs / 1000).toFixed(1)}s</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="shadow-md">
                    <CardContent className="p-4">
                      <div className="flex items-center gap-3">
                        <div className="bg-green-500/10 p-2.5 rounded-lg">
                          <CheckCircle2 className="h-5 w-5 text-green-600" />
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Başarı Oranı</p>
                          <p className="text-2xl font-bold">{analytics.successRate.toFixed(1)}%</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="shadow-md">
                    <CardContent className="p-4">
                      <div className="flex items-center gap-3">
                        <div className="bg-amber-500/10 p-2.5 rounded-lg">
                          <TrendingUp className="h-5 w-5 text-amber-600" />
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Test Edilen</p>
                          <p className="text-2xl font-bold">{analytics.algorithmStats.length} Algo</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Charts */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Gap Chart */}
                  {gapChartData && gapChartData.length > 0 && (
                    <Card className="shadow-md">
                      <CardHeader>
                        <CardTitle className="text-base">Ortalama Sapma (%) — Algoritma Bazlı</CardTitle>
                        <CardDescription>Optimal çözüme olan ortalama yüzde sapma</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <ChartContainer
                          config={Object.fromEntries(gapChartData.map((d, i) => [d.algorithm, { label: d.algorithm, color: CHART_COLORS[i % CHART_COLORS.length] }])) as ChartConfig}
                          className="h-[300px] w-full"
                        >
                          <BarChart data={gapChartData} layout="vertical" margin={{ left: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                            <XAxis type="number" tick={{ fontSize: 12 }} />
                            <YAxis type="category" dataKey="algorithm" width={150} tick={{ fontSize: 11 }} />
                            <ChartTooltip content={<ChartTooltipContent />} />
                            <Bar dataKey="gap" fill="var(--color-groove-purple)" radius={[0, 4, 4, 0]} />
                          </BarChart>
                        </ChartContainer>
                      </CardContent>
                    </Card>
                  )}

                  {/* Time Chart */}
                  {timeChartData && timeChartData.length > 0 && (
                    <Card className="shadow-md">
                      <CardHeader>
                        <CardTitle className="text-base">Ortalama Çalışma Süresi (ms) — Algoritma Bazlı</CardTitle>
                        <CardDescription>Algoritmaların ortalama çalışma süreleri</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <ChartContainer
                          config={Object.fromEntries(timeChartData.map((d, i) => [d.algorithm, { label: d.algorithm, color: CHART_COLORS[i % CHART_COLORS.length] }])) as ChartConfig}
                          className="h-[300px] w-full"
                        >
                          <BarChart data={timeChartData} layout="vertical" margin={{ left: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                            <XAxis type="number" tick={{ fontSize: 12 }} />
                            <YAxis type="category" dataKey="algorithm" width={150} tick={{ fontSize: 11 }} />
                            <ChartTooltip content={<ChartTooltipContent />} />
                            <Bar dataKey="time" fill="var(--color-chart-2)" radius={[0, 4, 4, 0]} />
                          </BarChart>
                        </ChartContainer>
                      </CardContent>
                    </Card>
                  )}
                </div>

                {/* Algorithm Stats Table */}
                <Card className="shadow-md">
                  <CardHeader>
                    <CardTitle className="text-lg">Algoritma Karşılaştırma Tablosu</CardTitle>
                    <CardDescription>
                      Her algoritmanın ortalama, minimum ve maksimum sapma/süre değerleri
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="max-h-96 overflow-y-auto rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Algoritma</TableHead>
                            <TableHead className="text-center">Test Sayısı</TableHead>
                            <TableHead className="text-center">Ort. Sapma %</TableHead>
                            <TableHead className="text-center">Min Sapma %</TableHead>
                            <TableHead className="text-center">Max Sapma %</TableHead>
                            <TableHead className="text-center">Ort. Süre (ms)</TableHead>
                            <TableHead className="text-center">En İyi Tur</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {analytics.algorithmStats.map((s, i) => (
                            <TableRow key={s.algorithm}>
                              <TableCell className="font-medium">
                                <div className="flex items-center gap-2">
                                  {i === 0 && <Badge className="bg-green-600 text-[10px] px-1 h-4">1.</Badge>}
                                  {s.displayName}
                                </div>
                              </TableCell>
                              <TableCell className="text-center">{s.count}</TableCell>
                              <TableCell className="text-center font-mono">
                                {s.avgGap !== null ? s.avgGap.toFixed(2) + "%" : "-"}
                              </TableCell>
                              <TableCell className="text-center font-mono text-green-600">
                                {s.minGap !== null ? s.minGap.toFixed(2) + "%" : "-"}
                              </TableCell>
                              <TableCell className="text-center font-mono text-red-500">
                                {s.maxGap !== null ? s.maxGap.toFixed(2) + "%" : "-"}
                              </TableCell>
                              <TableCell className="text-center font-mono">
                                {s.avgTime.toFixed(1)}
                              </TableCell>
                              <TableCell className="text-center font-mono">{s.minTour.toLocaleString()}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </CardContent>
                </Card>

                {/* Problem Comparison Table */}
                <Card className="shadow-md">
                  <CardHeader>
                    <CardTitle className="text-lg">Problem Bazlı Karşılaştırma</CardTitle>
                    <CardDescription>
                      Her problem için en iyi algoritma ve optimal sapma
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="max-h-96 overflow-y-auto rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Problem</TableHead>
                            <TableHead className="text-center">Optimal</TableHead>
                            <TableHead className="text-center">En İyi Tur</TableHead>
                            <TableHead className="text-center">Sapma %</TableHead>
                            <TableHead className="text-center">En İyi Algoritma</TableHead>
                            <TableHead className="text-center">Test Edilen Algo.</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {analytics.problemStats.map((p) => (
                            <TableRow key={p.problem}>
                              <TableCell className="font-mono font-medium">{p.problem}</TableCell>
                              <TableCell className="text-center font-mono text-muted-foreground">
                                {p.optimal !== null && p.optimal !== undefined ? p.optimal.toLocaleString() : "-"}
                              </TableCell>
                              <TableCell className="text-center font-mono font-semibold">
                                {p.bestTour.toLocaleString()}
                              </TableCell>
                              <TableCell className="text-center font-mono">
                                {p.gapFromOptimal !== null ? (
                                  <span className={p.gapFromOptimal < 5 ? "text-green-600" : p.gapFromOptimal < 15 ? "text-amber-600" : "text-red-600"}>
                                    {p.gapFromOptimal.toFixed(2)}%
                                  </span>
                                ) : (
                                  "-"
                                )}
                              </TableCell>
                              <TableCell className="text-center text-sm">
                                {p.bestAlgorithmName}
                              </TableCell>
                              <TableCell className="text-center">{p.algorithmsTested}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </CardContent>
                </Card>

                {/* Raw Results */}
                <details className="group">
                  <summary className="flex items-center gap-2 cursor-pointer text-sm font-medium text-muted-foreground hover:text-foreground transition-colors py-2">
                    <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
                    Ham Sonuçlar ({results.results.length} kayıt)
                  </summary>
                  <Card className="shadow-md mt-2">
                    <CardContent className="p-0">
                      <div className="max-h-96 overflow-y-auto">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Algoritma</TableHead>
                              <TableHead>Problem</TableHead>
                              <TableHead className="text-center">Çalışma #</TableHead>
                              <TableHead className="text-center">Tur Uzunluğu</TableHead>
                              <TableHead className="text-center">Sapma %</TableHead>
                              <TableHead className="text-right">Süre (ms)</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {results.results.map((r, i) => (
                              <TableRow key={`${r.algorithm}-${r.problem}-${r.run_number}-${i}`}>
                                <TableCell className="text-sm">{ALGORITHM_DISPLAY_NAMES[r.algorithm] || r.algorithm}</TableCell>
                                <TableCell className="font-mono text-sm">{r.problem}</TableCell>
                                <TableCell className="text-center text-sm">{r.run_number}</TableCell>
                                <TableCell className="text-center font-mono text-sm">{r.tour_length.toLocaleString()}</TableCell>
                                <TableCell className="text-center font-mono text-sm">
                                  {r.gap_percent !== null ? (
                                    <span className={r.gap_percent < 5 ? "text-green-600" : r.gap_percent < 15 ? "text-amber-600" : "text-red-600"}>
                                      {r.gap_percent.toFixed(2)}%
                                    </span>
                                  ) : (
                                    "-"
                                  )}
                                </TableCell>
                                <TableCell className="text-right font-mono text-sm">{r.elapsed_ms.toFixed(1)}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    </CardContent>
                  </Card>
                </details>

                {/* Export */}
                <div className="flex justify-end">
                  <Button variant="outline" onClick={handleExportResults}>
                    <Download className="mr-2 h-4 w-4" />
                    JSON Olarak İndir
                  </Button>
                </div>
              </>
            );
          })() : (
            <Card className="shadow-md">
              <CardContent className="py-16 text-center">
                <BarChart3 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">Henüz Sonuç Yok</h3>
                <p className="text-muted-foreground">
                  Benchmark tamamlandığında sonuçlar burada görüntülenecek.
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
