"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Route, Clock, MapPin, Zap, ArrowRight, Info, AlertTriangle } from "lucide-react";
import { ALL_LOCATIONS } from "@/services/doubus/route";
import { 
    ALGORITHM_OPTIONS, 
    LOCAL_SEARCH_OPTIONS,
    normalizeAlgorithmName, 
    getAlgorithmDisplayName,
    getLocalSearchDisplayName,
    ALGORITHM_KEYS,
    LOCAL_SEARCH_KEYS,
    algorithmSupportsLocalSearch,
    type LocalSearchType
} from "@/lib/algorithm-constants";
import { optimizeRoutes, type StudentForOptimization, type Depot } from "@/services/optimizer-service";

// Lokasyon grupları
const dKampusAndSwLocations = ALL_LOCATIONS.filter(
    (loc) => loc === "D.Kampus" || loc.startsWith("Sw")
);
const soLocations = ALL_LOCATIONS.filter((loc) => loc.startsWith("So"));

// Default depot
const DEFAULT_DEPOT: Depot = {
    id: "D.Kampus",
    lat: 37.0667,
    lng: 37.3833,
};

export default function RouteTestPage() {
    const { toast } = useToast();
    const [loading, setLoading] = useState(false);
    const [algorithm, setAlgorithm] = useState(ALGORITHM_KEYS.GENETIC_ALGORITHM);
    const [localSearchType, setLocalSearchType] = useState<LocalSearchType>(LOCAL_SEARCH_KEYS.TWO_OPT);
    const [start, setStart] = useState("D.Kampus");
    const [end, setEnd] = useState("D.Kampus");
    const [waypoints, setWaypoints] = useState<string[]>([]);
    const [result, setResult] = useState<any>(null);

    const handleWaypointToggle = (location: string) => {
        setWaypoints((prev) => {
            if (prev.includes(location)) {
                return prev.filter((wp) => wp !== location);
            } else {
                return [...prev, location];
            }
        });
    };

    const selectAll = (region: "sw" | "so" | "all") => {
        if (region === "sw") {
            const swLocs = dKampusAndSwLocations.filter(l => l !== start && l !== end && l !== "D.Kampus");
            setWaypoints(prev => [...new Set([...prev, ...swLocs])]);
        } else if (region === "so") {
            const soLocs = soLocations.filter(l => l !== start && l !== end);
            setWaypoints(prev => [...new Set([...prev, ...soLocs])]);
        } else {
            const allLocs = ALL_LOCATIONS.filter(l => l !== start && l !== end && l !== "D.Kampus");
            setWaypoints([...allLocs]);
        }
    };

    const clearAll = () => {
        setWaypoints([]);
    };

    const handleOptimize = async () => {
        try {
            setLoading(true);
            setResult(null);

            if (waypoints.length === 0) {
                toast({
                    title: "Hata",
                    description: "En az bir ara nokta seçin",
                    variant: "destructive",
                });
                return;
            }

            // Uyarı: Permütasyon için çok fazla nokta
            if (algorithm === ALGORITHM_KEYS.PERMUTATION_TSP && waypoints.length > 8) {
                toast({
                    title: "Uyarı",
                    description: "Permütasyon stratejisi 8'den fazla nokta için çok yavaş olabilir",
                    variant: "destructive",
                });
                return;
            }

            // Convert waypoints to students format for Python API
            const students: StudentForOptimization[] = waypoints.map((loc, index) => ({
                id: `test-${index}`,
                name: loc,
                location_code: loc,
                coordinates: undefined, // Will use time matrix
                disability_type: loc.startsWith("Sw") ? "Sw" : "So" as const,
            }));

            // Use start as depot
            const depot: Depot = {
                id: start,
                lat: DEFAULT_DEPOT.lat,
                lng: DEFAULT_DEPOT.lng,
            };

            // Call Python API with correct payload
            const response = await optimizeRoutes(students, depot, {
                algorithm: normalizeAlgorithmName(algorithm) as any,
                local_search_type: algorithmSupportsLocalSearch(algorithm) ? localSearchType : undefined,
                max_travel_time: 180,
            });

            if (!response.success) {
                throw new Error(response.error_message || "Optimizasyon başarısız");
            }

            // Transform response for display
            const transformedResult = {
                success: response.success,
                algorithm: response.algorithm_used,
                algorithm_display_name: getAlgorithmDisplayName(response.algorithm_used),
                total_vehicles: response.total_vehicles,
                total_duration_minutes: response.total_duration_minutes,
                execution_time_seconds: response.execution_time_seconds,
                routes: response.routes,
                meta: {
                    waypointCount: waypoints.length,
                    optimizationTimeMs: Math.round(response.execution_time_seconds * 1000),
                },
            };

            setResult(transformedResult);
            toast({
                title: "Optimizasyon Tamamlandı",
                description: `${response.execution_time_seconds.toFixed(3)}s sürdü, ${response.total_vehicles} araç`,
            });
        } catch (error: any) {
            toast({
                title: "Hata",
                description: error.message,
                variant: "destructive",
            });
        } finally {
            setLoading(false);
        }
    };

    const selectedAlgorithm = ALGORITHM_OPTIONS.find(a => a.key === algorithm);

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Route className="text-primary" />
                        Rota Optimizasyon Testi
                    </CardTitle>
                    <CardDescription>
                        Farklı optimizasyon algoritmalarını test edin ve karşılaştırın
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {/* Algorithm Selection */}
                    <div className="grid gap-4 md:grid-cols-4">
                        <div className="space-y-2">
                            <Label>Algoritma</Label>
                            <Select value={algorithm} onValueChange={setAlgorithm}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {ALGORITHM_OPTIONS.map((alg) => (
                                        <SelectItem key={alg.key} value={alg.key}>
                                            <div className="flex items-center gap-2">
                                                {alg.label}
                                                {alg.recommended && (
                                                    <Badge variant="secondary" className="text-xs">Önerilen</Badge>
                                                )}
                                            </div>
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            {selectedAlgorithm && (
                                <p className="text-xs text-muted-foreground flex items-center gap-1">
                                    <Info className="h-3 w-3" />
                                    {selectedAlgorithm.description} ({selectedAlgorithm.complexity})
                                </p>
                            )}
                        </div>

                        {/* Local Search Type - Only shown for meta-heuristics */}
                        <div className="space-y-2">
                            <Label>Yerel Arama</Label>
                            <Select 
                                value={localSearchType} 
                                onValueChange={(v) => setLocalSearchType(v as LocalSearchType)}
                                disabled={!algorithmSupportsLocalSearch(algorithm)}
                            >
                                <SelectTrigger className={!algorithmSupportsLocalSearch(algorithm) ? "opacity-50" : ""}>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {LOCAL_SEARCH_OPTIONS.map((ls) => (
                                        <SelectItem key={ls.key} value={ls.key}>
                                            {ls.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            {!algorithmSupportsLocalSearch(algorithm) ? (
                                <p className="text-xs text-muted-foreground">
                                    Bu algoritma yerel arama desteklemiyor
                                </p>
                            ) : (
                                <p className="text-xs text-muted-foreground flex items-center gap-1">
                                    <Info className="h-3 w-3" />
                                    {LOCAL_SEARCH_OPTIONS.find(ls => ls.key === localSearchType)?.description}
                                </p>
                            )}
                        </div>

                        <div className="space-y-2">
                            <Label>Başlangıç Konumu (Depot)</Label>
                            <Select value={start} onValueChange={setStart}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {ALL_LOCATIONS.filter(l => l === "D.Kampus").map((loc) => (
                                        <SelectItem key={loc} value={loc}>
                                            {loc}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label>Varış Konumu</Label>
                            <Select value={end} onValueChange={setEnd}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="D.Kampus">D.Kampus (Depot'a dönüş)</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label>&nbsp;</Label>
                            <Button onClick={handleOptimize} disabled={loading} className="w-full">
                                {loading ? "Hesaplanıyor..." : "Optimize Et"}
                            </Button>
                        </div>
                    </div>

                    {/* Waypoint Selection */}
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <Label>Ara Noktalar ({waypoints.length} seçili)</Label>
                            <div className="flex gap-2">
                                <Button variant="outline" size="sm" onClick={() => selectAll("sw")}>
                                    Sw Tümü
                                </Button>
                                <Button variant="outline" size="sm" onClick={() => selectAll("so")}>
                                    So Tümü
                                </Button>
                                <Button variant="ghost" size="sm" onClick={clearAll}>
                                    Temizle
                                </Button>
                            </div>
                        </div>
                        <ScrollArea className="h-48 w-full rounded-md border p-4 bg-muted/30">
                            {/* D.Kampus & Sw Group */}
                            <div className="mb-3">
                                <p className="text-xs font-semibold text-muted-foreground mb-2">D.Kampus & Batı Bölgesi (Sw)</p>
                                <div className="grid grid-cols-5 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10 gap-2">
                                    {dKampusAndSwLocations.map((location) => (
                                        <div key={location} className="flex items-center space-x-1">
                                            <Checkbox
                                                id={`wp-${location}`}
                                                checked={waypoints.includes(location)}
                                                onCheckedChange={() => handleWaypointToggle(location)}
                                                disabled={location === start || location === end || location === "D.Kampus"}
                                            />
                                            <Label
                                                htmlFor={`wp-${location}`}
                                                className={`text-xs font-normal cursor-pointer ${location === start || location === end ? "text-muted-foreground" : ""
                                                    }`}
                                            >
                                                {location}
                                            </Label>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <Separator className="my-3" />
                            {/* So Group */}
                            <div>
                                <p className="text-xs font-semibold text-muted-foreground mb-2">Doğu Bölgesi (So)</p>
                                <div className="grid grid-cols-5 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10 gap-2">
                                    {soLocations.map((location) => (
                                        <div key={location} className="flex items-center space-x-1">
                                            <Checkbox
                                                id={`wp-${location}`}
                                                checked={waypoints.includes(location)}
                                                onCheckedChange={() => handleWaypointToggle(location)}
                                                disabled={location === start || location === end}
                                            />
                                            <Label
                                                htmlFor={`wp-${location}`}
                                                className={`text-xs font-normal cursor-pointer ${location === start || location === end ? "text-muted-foreground" : ""
                                                    }`}
                                            >
                                                {location}
                                            </Label>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </ScrollArea>
                    </div>

                    {/* Quick Presets */}
                    <div className="flex gap-2 flex-wrap">
                        <span className="text-sm text-muted-foreground self-center">Hazır Setler:</span>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setWaypoints(["Sw1", "Sw3", "Sw5"])}
                        >
                            3 Nokta (Batı)
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setWaypoints(["So1", "So3", "So5", "So7"])}
                        >
                            4 Nokta (Doğu)
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setWaypoints(["Sw1", "Sw3", "So2", "So4", "Sw5", "So6"])}
                        >
                            6 Nokta (Karışık)
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setWaypoints(["Sw1", "Sw2", "Sw3", "Sw4", "Sw5", "Sw6", "Sw7", "Sw8"])}
                        >
                            8 Nokta (Stres Testi)
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Results */}
            {result && (
                <Card className="border-l-4 border-l-green-500">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Zap className="text-green-500" />
                            Sonuç: {result.algorithm_display_name}
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {/* Stats */}
                        <div className="grid gap-4 md:grid-cols-4">
                            <div className="p-4 rounded-lg bg-muted">
                                <div className="text-sm text-muted-foreground">Algoritma</div>
                                <div className="text-lg font-bold">{result.algorithm_display_name}</div>
                            </div>
                            <div className="p-4 rounded-lg bg-muted">
                                <div className="text-sm text-muted-foreground flex items-center gap-1">
                                    <Clock className="h-3 w-3" /> Toplam Süre
                                </div>
                                <div className="text-lg font-bold">{result.total_duration_minutes.toFixed(1)} dk</div>
                            </div>
                            <div className="p-4 rounded-lg bg-muted">
                                <div className="text-sm text-muted-foreground flex items-center gap-1">
                                    <Route className="h-3 w-3" /> Araç Sayısı
                                </div>
                                <div className="text-lg font-bold">{result.total_vehicles}</div>
                            </div>
                            <div className="p-4 rounded-lg bg-muted">
                                <div className="text-sm text-muted-foreground">Hesaplama Süresi</div>
                                <div className="text-lg font-bold">{result.execution_time_seconds.toFixed(3)} s</div>
                            </div>
                        </div>

                        {/* Vehicle Routes */}
                        {result.routes && result.routes.length > 0 && (
                            <div className="space-y-4">
                                <Label>Araç Rotaları</Label>
                                {result.routes.map((route: any, index: number) => (
                                    <div key={index} className="border rounded-lg p-4">
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="font-semibold flex items-center gap-2">
                                                <Route className="h-4 w-4" />
                                                {route.vehicle_id}
                                            </div>
                                            <div className="flex gap-2">
                                                <Badge variant="outline">Sw: {route.sw_count}</Badge>
                                                <Badge variant="outline">So: {route.so_count}</Badge>
                                                <Badge>{route.total_duration_minutes.toFixed(1)} dk</Badge>
                                            </div>
                                        </div>
                                        <div className="flex flex-wrap items-center gap-1 text-sm">
                                            {route.route_details.map((detail: any, i: number) => (
                                                <span key={i} className="flex items-center gap-1">
                                                    {i === 0 && <Badge variant="default">{detail.location1}</Badge>}
                                                    <ArrowRight className="h-3 w-3 text-muted-foreground" />
                                                    <Badge variant={i === route.route_details.length - 1 ? "default" : "secondary"}>
                                                        {detail.location2}
                                                    </Badge>
                                                    <span className="text-xs text-muted-foreground">({detail.duration.toFixed(1)} dk)</span>
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Raw JSON */}
                        <details className="mt-4">
                            <summary className="cursor-pointer text-sm text-muted-foreground">
                                Ham JSON Yanıtı
                            </summary>
                            <pre className="mt-2 p-4 rounded-lg bg-muted text-xs overflow-auto max-h-64">
                                {JSON.stringify(result, null, 2)}
                            </pre>
                        </details>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
