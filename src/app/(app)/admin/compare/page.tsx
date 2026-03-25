"use client";

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Cpu, Play, CheckCircle2, Clock, Truck, Activity, Target, Eye, ChevronRight, Users, MapPin } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { adminApi, getAuthToken } from "@/lib/admin-api";
import { CompareResult, AlgorithmCompareResult } from "@/services/optimizer-service";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import type { User } from "@/types";

const clusteringAlgorithms = [
    { name: "kmeans", label: "K-Means" },
    { name: "fuzzy_cmeans", label: "Fuzzy C-Means" },
    { name: "k_medoids", label: "K-Medoids (Süre Tabanlı)" },
    { name: "sweep", label: "Sweep Algoritması" },
    { name: "clarke_wright", label: "Clarke-Wright" },
];

export default function AlgorithmComparisonPage() {
    const { toast } = useToast();
    const [isLoading, setIsLoading] = useState(false);
    const [isFetchingUsers, setIsFetchingUsers] = useState(true);
    const [students, setStudents] = useState<User[]>([]);
    const [compareResult, setCompareResult] = useState<CompareResult | null>(null);
    const [selectedResult, setSelectedResult] = useState<AlgorithmCompareResult | null>(null);
    const [clusteringAlgorithm, setClusteringAlgorithm] = useState("kmeans");

    useEffect(() => {
        loadStudents();
    }, []);

    const loadStudents = async () => {
        setIsFetchingUsers(true);
        console.log("[Compare UI] Starting loadStudents...");
        try {
            console.log("[Compare UI] Calling adminApi.users.getAll...");
            const response = await adminApi.users.getAll(1, 100);
            console.log("[Compare UI] Received response:", response);
            // Handle both { data: [...] } format and raw array format
            const usersArray = Array.isArray(response) ? response : (response.data || []);
            const studentUsers = usersArray.filter((u: any) => u.role === "student");
            console.log(`[Compare UI] Filtered ${studentUsers.length} students.`);
            setStudents(studentUsers);
        } catch (error) {
            console.error("[Compare UI] Error loading students:", error);
            toast({
                title: "Öğrenciler Yüklenemedi",
                description: "Test verisi için öğrenci listesi alınamadı.",
                variant: "destructive"
            });
        } finally {
            console.log("[Compare UI] loadStudents finally block.");
            setIsFetchingUsers(false);
        }
    };

    const runComparison = async () => {
        if (students.length === 0) {
            toast({
                title: "Öğrenci Bulunamadı",
                description: "Sistemde kayıtlı öğrenci yok. Karşılaştırma yapılamaz.",
                variant: "destructive"
            });
            return;
        }

        setIsLoading(true);
        setCompareResult(null);

        try {
            const token = await getAuthToken();
            const response = await fetch("/api/compare-algorithms", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({
                    students: students,
                    depot: { id: "D.Kampus", lat: 40.8410, lng: 31.1478 },
                    clusteringAlgorithm: clusteringAlgorithm
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || "Karşılaştırma API hatası");
            }

            const data: CompareResult = await response.json();
            setCompareResult(data);
            setSelectedResult(null); // Reset selection on new run
            
            toast({
                title: "Karşılaştırma Tamamlandı",
                description: `${data.results.length} farklı algoritma test edildi.`
            });

        } catch (error: any) {
            console.error("Comparison error:", error);
            toast({
                title: "Optimizasyon Hatası",
                description: error.message || "Algoritma sunucusu yanıt vermedi.",
                variant: "destructive"
            });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <Card className="shadow-lg">
                <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                        <CardTitle className="text-2xl flex items-center gap-2">
                            <Cpu className="text-primary" /> Algoritma Karşılaştırması
                        </CardTitle>
                        <CardDescription>
                            Tüm optimizasyon algoritmalarını (GA, PSO, Greedy, OR-Tools vb.) aynı veri seti üzerinde yarıştırın ve performanslarını karşılaştırın.
                        </CardDescription>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="mb-6 p-4 border rounded-lg bg-muted flex flex-col md:flex-row items-center justify-between gap-4">
                        <div className="flex items-center gap-3 text-sm">
                            <Target className="h-5 w-5 text-muted-foreground" />
                            <div>
                                <p className="font-semibold">Test Verisi</p>
                                <p className="text-muted-foreground">
                                    {isFetchingUsers ? "Sistemdeki öğrenciler yükleniyor..." : `Sistemde kayıtlı ${students.length} adet "Öğrenci" rolündeki kullanıcı kullanılarak test edilecektir.`}
                                </p>
                            </div>
                        </div>
                        <Button 
                            onClick={runComparison} 
                            disabled={isLoading || isFetchingUsers || students.length === 0}
                            size="lg"
                            className="w-full md:w-auto min-w-[200px]"
                        >
                            {isLoading ? (
                                <>
                                    <Activity className="mr-2 h-4 w-4 animate-spin" /> Analiz Ediliyor...
                                </>
                            ) : (
                                <>
                                    <Play className="mr-2 h-4 w-4" /> Tümünü Yarıştır
                                </>
                            )}
                        </Button>
                    </div>
                    
                    <div className="mb-6 w-full md:w-64">
                        <label className="text-sm font-medium mb-2 block text-muted-foreground"><Target className="h-4 w-4 inline mr-1" /> Kümeleme Yöntemi</label>
                        <Select value={clusteringAlgorithm} onValueChange={setClusteringAlgorithm} disabled={isLoading}>
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {clusteringAlgorithms.map((c) => (
                                    <SelectItem key={c.name} value={c.name}>
                                        {c.label}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    {compareResult && (
                        <div className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <Card className="bg-green-50 border-green-200">
                                    <CardContent className="p-4 flex items-center gap-4">
                                        <div className="bg-green-100 p-3 rounded-full">
                                            <CheckCircle2 className="h-6 w-6 text-green-700" />
                                        </div>
                                        <div>
                                            <p className="text-sm font-medium text-green-800">En Verimli Rota</p>
                                            <p className="text-2xl font-bold text-green-900 capitalize">
                                                {compareResult.best_algorithm?.replace('_', ' ') || "-"}
                                            </p>
                                        </div>
                                    </CardContent>
                                </Card>
                                <Card className="bg-blue-50 border-blue-200">
                                    <CardContent className="p-4 flex items-center gap-4">
                                        <div className="bg-blue-100 p-3 rounded-full">
                                            <Activity className="h-6 w-6 text-blue-700" />
                                        </div>
                                        <div>
                                            <p className="text-sm font-medium text-blue-800">En Hızlı Çözümcü</p>
                                            <p className="text-2xl font-bold text-blue-900 capitalize">
                                                {compareResult.fastest_algorithm?.replace('_', ' ') || "-"}
                                            </p>
                                        </div>
                                    </CardContent>
                                </Card>
                            </div>

                            <div className="border rounded-lg overflow-hidden">
                                <Table>
                                    <TableHeader className="bg-muted/50">
                                        <TableRow>
                                            <TableHead className="w-[200px]">Algoritma</TableHead>
                                            <TableHead className="text-center">Durum</TableHead>
                                            <TableHead className="text-center"><div className="flex items-center justify-center gap-1"><Truck className="h-4 w-4"/> Araç</div></TableHead>
                                            <TableHead className="text-center"><div className="flex items-center justify-center gap-1"><Clock className="h-4 w-4"/> Süre (Dk)</div></TableHead>
                                            <TableHead className="text-right">Hız (sn)</TableHead>
                                            <TableHead className="text-center w-[100px]">Detay</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {compareResult.results.sort((a,b) => a.total_duration_minutes - b.total_duration_minutes).map((res) => (
                                            <TableRow 
                                                key={res.algorithm} 
                                                className={`cursor-pointer transition-colors ${res.algorithm === compareResult.best_algorithm ? "bg-green-50/50" : ""} ${selectedResult?.algorithm === res.algorithm ? "bg-slate-100" : ""}`}
                                                onClick={() => res.success && setSelectedResult(res)}
                                            >
                                                <TableCell className="font-medium capitalize flex items-center gap-2">
                                                    {res.algorithm.replace('_', ' ')}
                                                    {res.algorithm === compareResult.best_algorithm && (
                                                        <Badge variant="default" className="bg-green-600 hover:bg-green-700 text-[10px] px-1 h-4">BEST</Badge>
                                                    )}
                                                </TableCell>
                                                <TableCell className="text-center">
                                                    {res.success ? (
                                                        <Badge variant="outline" className="border-green-500 text-green-700">Başarılı</Badge>
                                                    ) : (
                                                        <Badge variant="destructive">Hata Çıktı</Badge>
                                                    )}
                                                </TableCell>
                                                <TableCell className="text-center font-semibold">{res.total_vehicles || "-"}</TableCell>
                                                <TableCell className="text-center font-semibold">{res.total_duration_minutes ? res.total_duration_minutes.toFixed(1) : "-"}</TableCell>
                                                <TableCell className="text-right text-muted-foreground whitespace-nowrap">
                                                    {res.execution_time_seconds ? `${res.execution_time_seconds.toFixed(3)}s` : "-"}
                                                </TableCell>
                                                <TableCell className="text-center">
                                                    {res.success && (
                                                        <Button variant={selectedResult?.algorithm === res.algorithm ? "default" : "ghost"} size="sm" onClick={(e) => { e.stopPropagation(); setSelectedResult(res); }}>
                                                            <Eye className="h-4 w-4" />
                                                        </Button>
                                                    )}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                            
                            {/* Detailed Route View */}
                            {selectedResult && selectedResult.routes && (
                                <Card className="border-t-4 border-t-primary shadow-md mt-8 animate-in fade-in slide-in-from-bottom-4">
                                    <CardHeader className="bg-slate-50/50">
                                        <CardTitle className="text-xl capitalize flex items-center justify-between">
                                            <span>
                                                {selectedResult.algorithm.replace('_', ' ')} - Rota ve Araç Çözüm Detayları
                                            </span>
                                            <Badge variant="outline" className="text-sm">
                                                Toplam Süre: {selectedResult.total_duration_minutes.toFixed(1)} Dk
                                            </Badge>
                                        </CardTitle>
                                        <CardDescription>
                                            Algoritmanın oluşturduğu rotaların araca atanmış öğrenci detayları, sıralamaları ve hesaplanan mesafeler/süreler.
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent className="p-6 space-y-8">
                                        {selectedResult.routes.map((route: any, i: number) => {
                                            const vId = route.vehicle_id || route.vehicle_index || (i + 1);
                                            const details = route.route_details || route.route || route.steps || [];
                                            const students = route.students || route.student_ids || [];
                                            const sw = route.sw_count || 0;
                                            const so = route.so_count || 0;
                                            const duration = route.total_duration_minutes || route.total_duration || 0;
                                            
                                            // Handle case where algorithm failed to build detailed route sequence
                                            const hasValidDetails = details && details.length > 0;
                                            
                                            return (
                                                <div key={vId} className="border rounded-lg overflow-hidden">
                                                    <div className="bg-slate-100 p-3 px-4 flex flex-col md:flex-row md:items-center justify-between gap-2 border-b">
                                                        <div className="flex items-center gap-2">
                                                            <Truck className="h-5 w-5 text-slate-600" />
                                                            <span className="font-semibold text-slate-800">Araç {vId}</span>
                                                            <span className="text-sm text-slate-500 ml-2">({students.length} Öğrenci)</span>
                                                        </div>
                                                        <div className="flex items-center gap-3 text-sm">
                                                            <Badge variant="secondary" className="bg-slate-200">
                                                                <Users className="h-3 w-3 mr-1" /> {sw} Sw, {so} So
                                                            </Badge>
                                                            <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                                                                <Clock className="h-3 w-3 mr-1" /> {duration.toFixed(1)} dk
                                                            </Badge>
                                                        </div>
                                                    </div>
                                                    
                                                    <div className="p-4 bg-white">
                                                        <h4 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
                                                            <MapPin className="h-4 w-4" /> Optimizasyon Rotası
                                                        </h4>
                                                        
                                                        {!hasValidDetails ? (
                                                            <p className="text-sm text-amber-600 italic">Bu algoritma rota adımlarını detaylı döndürmedi. Sadece araç ataması yapıldı.</p>
                                                        ) : (
                                                            <div className="flex flex-wrap items-center gap-y-2 text-sm">
                                                                {details.map((step: any, sIdx: number) => (
                                                                    <React.Fragment key={sIdx}>
                                                                        {/* Start Location Node */}
                                                                        <div className="flex items-center">
                                                                            <span className={`px-2 py-1 rounded-md border ${step.location1.includes('Depo') || step.location1.includes('Kampus') ? 'bg-primary/10 border-primary/30 font-medium' : 'bg-slate-50 border-slate-200'}`}>
                                                                                {step.location1}
                                                                            </span>
                                                                        </div>
                                                                        
                                                                        {/* Arrow with Duration */}
                                                                        <div className="flex flex-col items-center justify-center px-2 text-xs text-muted-foreground w-16">
                                                                            <span className="px-1 bg-white relative z-10">{step.duration ? step.duration.toFixed(0) : '?'} dk</span>
                                                                            <div className="h-px bg-slate-300 w-full -mt-2"></div>
                                                                            <ChevronRight className="h-3 w-3 text-slate-400 absolute ml-16 mt-3" />
                                                                        </div>
                                                                        
                                                                        {/* Final Location Node (only for the last step to close the loop) */}
                                                                        {sIdx === details.length - 1 && (
                                                                            <div className="flex items-center">
                                                                                <span className={`px-2 py-1 rounded-md border ${step.location2.includes('Depo') || step.location2.includes('Kampus') ? 'bg-primary/10 border-primary/30 font-medium' : 'bg-slate-50 border-slate-200'}`}>
                                                                                    {step.location2}
                                                                                </span>
                                                                            </div>
                                                                        )}
                                                                    </React.Fragment>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </CardContent>
                                    <CardFooter className="bg-slate-50 border-t py-3 text-sm text-slate-500">
                                        * Yukarıdaki grafikte her durak arası tahmini seyahat süresi (dk) olarak hesaplanmıştır. Toplam süre, aracın kampüsten çıkıp öğrencileri bırakarak tekrar kampüse döndüğü toplam operasyon süresidir.
                                    </CardFooter>
                                </Card>
                            )}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
