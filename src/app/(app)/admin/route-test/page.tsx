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
import { adminApi } from "@/lib/admin-api";
import { Route, Clock, MapPin, Zap, ArrowRight, Info } from "lucide-react";
import { ALL_LOCATIONS } from "@/services/doubus/route";

// Lokasyon grupları
const dKampusAndSwLocations = ALL_LOCATIONS.filter(
    (loc) => loc === "D.Kampus" || loc.startsWith("Sw")
);
const soLocations = ALL_LOCATIONS.filter((loc) => loc.startsWith("So"));

// Strateji bilgileri
const strategies = [
    {
        name: "nearest-neighbor",
        label: "En Yakın Komşu (Hızlı)",
        description: "Greedy algoritma, hızlı sonuç",
        complexity: "O(n²)"
    },
    {
        name: "two-opt",
        label: "2-opt İyileştirme (Dengeli)",
        description: "Nearest neighbor + lokal iyileştirme",
        complexity: "O(n³)"
    },
    {
        name: "permutation",
        label: "Permütasyon (Optimal)",
        description: "Tüm kombinasyonları dener, en iyi sonuç",
        complexity: "O(n!)"
    },
];

export default function RouteTestPage() {
    const { toast } = useToast();
    const [loading, setLoading] = useState(false);
    const [strategy, setStrategy] = useState("two-opt");
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
            if (strategy === "permutation" && waypoints.length > 8) {
                toast({
                    title: "Uyarı",
                    description: "Permütasyon stratejisi 8'den fazla nokta için çok yavaş olabilir",
                    variant: "destructive",
                });
                return;
            }

            const response = await adminApi.routes.optimize({
                start,
                end,
                waypoints,
                strategy,
            });

            setResult(response);
            toast({
                title: "Optimizasyon Tamamlandı",
                description: `${response.meta.optimizationTimeMs}ms sürdü`,
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

    const selectedStrategy = strategies.find(s => s.name === strategy);

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Route className="text-primary" />
                        Rota Optimizasyon Testi
                    </CardTitle>
                    <CardDescription>
                        Farklı optimizasyon stratejilerini test edin ve karşılaştırın
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {/* Strategy & Endpoints */}
                    <div className="grid gap-4 md:grid-cols-4">
                        <div className="space-y-2">
                            <Label>Çözüm Yöntemi</Label>
                            <Select value={strategy} onValueChange={setStrategy}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {strategies.map((s) => (
                                        <SelectItem key={s.name} value={s.name}>
                                            {s.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            {selectedStrategy && (
                                <p className="text-xs text-muted-foreground flex items-center gap-1">
                                    <Info className="h-3 w-3" />
                                    {selectedStrategy.description} ({selectedStrategy.complexity})
                                </p>
                            )}
                        </div>

                        <div className="space-y-2">
                            <Label>Başlangıç Konumu</Label>
                            <Select value={start} onValueChange={setStart}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {ALL_LOCATIONS.map((loc) => (
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
                                    {ALL_LOCATIONS.map((loc) => (
                                        <SelectItem key={loc} value={loc}>
                                            {loc}
                                        </SelectItem>
                                    ))}
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
                            Sonuç
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {/* Stats */}
                        <div className="grid gap-4 md:grid-cols-4">
                            <div className="p-4 rounded-lg bg-muted">
                                <div className="text-sm text-muted-foreground">Strateji</div>
                                <div className="text-lg font-bold">{result.strategy}</div>
                            </div>
                            <div className="p-4 rounded-lg bg-muted">
                                <div className="text-sm text-muted-foreground flex items-center gap-1">
                                    <Clock className="h-3 w-3" /> Toplam Süre
                                </div>
                                <div className="text-lg font-bold">{result.route.totalDurationMinutes} dk</div>
                            </div>
                            <div className="p-4 rounded-lg bg-muted">
                                <div className="text-sm text-muted-foreground flex items-center gap-1">
                                    <MapPin className="h-3 w-3" /> Mesafe
                                </div>
                                <div className="text-lg font-bold">{result.route.totalDistanceKm} km</div>
                            </div>
                            <div className="p-4 rounded-lg bg-muted">
                                <div className="text-sm text-muted-foreground">Hesaplama Süresi</div>
                                <div className="text-lg font-bold">{result.meta.optimizationTimeMs} ms</div>
                            </div>
                        </div>

                        {/* Route Path */}
                        <div className="space-y-2">
                            <Label>Optimize Edilmiş Rota:</Label>
                            <div className="flex items-center gap-2 flex-wrap p-4 rounded-lg bg-muted">
                                <Badge variant="default">{result.route.start}</Badge>
                                {result.route.routeDetails.map((detail: any, index: number) => (
                                    <div key={index} className="flex items-center gap-2">
                                        <ArrowRight className="h-4 w-4 text-muted-foreground" />
                                        <Badge variant={detail.location2 === result.route.end ? "default" : "secondary"}>
                                            {detail.location2}
                                        </Badge>
                                        <span className="text-xs text-muted-foreground">({detail.duration} dk)</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Route Steps Table */}
                        <div className="space-y-2">
                            <Label>Rota Adımları:</Label>
                            <div className="border rounded-lg overflow-hidden">
                                <table className="w-full text-sm">
                                    <thead className="bg-muted">
                                        <tr>
                                            <th className="px-3 py-2 text-left">#</th>
                                            <th className="px-3 py-2 text-left">Nereden</th>
                                            <th className="px-3 py-2 text-left">Nereye</th>
                                            <th className="px-3 py-2 text-right">Süre</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {result.route.routeDetails.map((detail: any, index: number) => (
                                            <tr key={index} className="border-t">
                                                <td className="px-3 py-2">{index + 1}</td>
                                                <td className="px-3 py-2 font-medium">{detail.location1}</td>
                                                <td className="px-3 py-2 font-medium">{detail.location2}</td>
                                                <td className="px-3 py-2 text-right">{detail.duration} dk</td>
                                            </tr>
                                        ))}
                                        <tr className="border-t bg-muted font-bold">
                                            <td className="px-3 py-2" colSpan={3}>Toplam</td>
                                            <td className="px-3 py-2 text-right">{result.route.totalDurationMinutes} dk</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>

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
