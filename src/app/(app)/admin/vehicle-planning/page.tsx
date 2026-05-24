"use client";

import { useState, useEffect } from "react";
import { useTranslations } from 'next-intl';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
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
import { Truck, Users, Clock, Calculator, ArrowRight, Info, Activity } from "lucide-react";
import { adminApi } from "@/lib/admin-api";
import { ALGORITHM_OPTIONS } from "@/lib/algorithm-constants";
import { formatRoutePlanForSave, saveRoutePlan } from "@/services/route-plans";
import type { User } from "@/types";
import { IEDashboard } from "@/components/admin/ie-dashboard";
import type { IEResponseData } from "@/types/ie-resource";

// Algoritmalar merkezi sabitlerden alinir (algorithm-constants.ts → Python registry)
// Detay: docs/ARCHITECTURE.md#3-algoritma-key-kurali

const clusteringAlgorithms = [
    { name: "sweep", label: "Sweep Algoritması (Önerilen)" },
    { name: "clarke_wright", label: "Clarke-Wright Savings" },
    { name: "k_medoids", label: "K-Medoids (Süre Tabanlı)" },
    { name: "fuzzy_cmeans", label: "Fuzzy C-Means" },
    { name: "fuzzy_cmeans_enhanced", label: "Enhanced Fuzzy C-Means" },
    { name: "hierarchical_fcm", label: "Hierarchical FCM (Büyük Veri)" },
    { name: "kmeans", label: "K-Means (Eski)" },
];

export default function VehiclePlanningPage() {
    const t = useTranslations('page.admin.vehiclePlanning');
    const tc = useTranslations('common');
    const { toast } = useToast();
    const [loading, setLoading] = useState(false);
    const [isLoadingStudents, setIsLoadingStudents] = useState(true);
    const [students, setStudents] = useState<User[]>([]);
    const [selectedStudents, setSelectedStudents] = useState<string[]>([]);
    const [maxTourTime, setMaxTourTime] = useState(120);
    const [swCapacity, setSwCapacity] = useState(4);
    const [soCapacity, setSoCapacity] = useState(5);
    const [strategy, setStrategy] = useState("genetic_algorithm");
    const [clusteringAlgorithm, setClusteringAlgorithm] = useState("sweep");
    const [planDate, setPlanDate] = useState<string>(new Date().toISOString().split('T')[0]);
    const [direction, setDirection] = useState<"pickup" | "dropoff">("pickup");
    const [isSaving, setIsSaving] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [ieData, setIeData] = useState<IEResponseData | null>(null);

    useEffect(() => {
        loadStudents();
    }, []);

    const loadStudents = async () => {
        setIsLoadingStudents(true);
        try {
            const response = await adminApi.users.getAll(1, 100);
            const usersArray = Array.isArray(response) ? response : (response.data || []);
            const studentUsers = usersArray.filter((u: User) => u.role === "student");
            setStudents(studentUsers);
        } catch (error) {
            console.error("Error loading students:", error);
            toast({
                title: t('studentLoadError'),
                description: t('studentLoadError'),
                variant: "destructive"
            });
        } finally {
            setIsLoadingStudents(false);
        }
    };

    const handleStudentToggle = (studentId: string) => {
        setSelectedStudents((prev) => {
            if (prev.includes(studentId)) {
                return prev.filter((id) => id !== studentId);
            } else {
                return [...prev, studentId];
            }
        });
    };

    const selectAll = (type: "Sw" | "So" | "all") => {
        if (type === "all") {
            setSelectedStudents(students.map(s => s.id));
        } else {
            const ids = students.filter((s: User) => s.disabilityType === type).map(s => s.id);
            setSelectedStudents(prev => [...new Set([...prev, ...ids])]);
        }
    };

    const clearAll = () => setSelectedStudents([]);

    const handleCalculate = async () => {
        try {
            setLoading(true);
            setResult(null);

            const activeStudents = students.filter(s => selectedStudents.includes(s.id));

            if (activeStudents.length === 0) {
                toast({
                    title: tc('error'),
                    description: t('studentLoadError'),
                    variant: "destructive",
                });
                return;
            }

            const response = await fetch("/api/calculate-vehicles", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    students: activeStudents,
                    maxTourTime,
                    swCapacity,
                    soCapacity,
                    strategy,
                    clusteringAlgorithm,
                }),
            });

            if (!response.ok) {
                throw new Error(tc('error'));
            }

            const data = await response.json();
            setResult(data);
            setIeData(data.ieData);

            toast({
                title: tc('success'),
                description: `${data.requiredVehicles} ${tc('sidebar.vehicleManagement')}`,
            });
        } catch (error: unknown) {
            toast({
                title: tc('error'),
                description: error instanceof Error ? error.message : tc('error'),
                variant: "destructive",
            });
        } finally {
            setLoading(false);
        }
    };

    const handleSavePlan = async () => {
        if (!result || !result.success) {
            toast({
                title: tc('error'),
                description: t('saveError'),
                variant: "destructive",
            });
            return;
        }

        try {
            setIsSaving(true);

            const planData = formatRoutePlanForSave(result, planDate, direction, strategy, clusteringAlgorithm);
            await saveRoutePlan(planData);

            toast({
                title: tc('success'),
                description: `${planDate} ${tc('success')}`,
            });
        } catch (error: unknown) {
            toast({
                title: t('saveError'),
                description: error instanceof Error ? error.message : t('saveError'),
                variant: "destructive",
            });
        } finally {
            setIsSaving(false);
        }
    };

    const swStudents = students.filter((s: User) => s.disabilityType === "Sw");
    const soStudents = students.filter((s: User) => s.disabilityType === "So" || !s.disabilityType);
    const selectedSwCount = swStudents.filter(s => selectedStudents.includes(s.id)).length;
    const selectedSoCount = soStudents.filter(s => selectedStudents.includes(s.id)).length;

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Truck className="text-primary" />
                        {tc('sidebar.vehiclePlanning')}
                    </CardTitle>
                    <CardDescription>
                        {tc('sidebar.vehiclePlanning')}
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {/* Parameters */}
                    <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
                        <div className="space-y-2">
                            <Label>{tc('configuration')}</Label>
                            <Input
                                type="number"
                                value={swCapacity}
                                onChange={(e) => setSwCapacity(Number(e.target.value))}
                                min={1}
                            />
                            <p className="text-xs text-muted-foreground">{tc('details')}</p>
                        </div>
                        <div className="space-y-2">
                            <Label>{tc('configuration')}</Label>
                            <Input
                                type="number"
                                value={soCapacity}
                                onChange={(e) => setSoCapacity(Number(e.target.value))}
                                min={1}
                            />
                            <p className="text-xs text-muted-foreground">{tc('details')}</p>
                        </div>
                        <div className="space-y-2">
                            <Label>{tc('selectAll')}</Label>
                            <Input
                                type="number"
                                value={maxTourTime}
                                onChange={(e) => setMaxTourTime(Number(e.target.value))}
                                min={30}
                            />
                            <p className="text-xs text-muted-foreground">{tc('details')}</p>
                        </div>
                        <div className="space-y-2">
                            <Label>{tc('selectAll')}</Label>
                            <Select value={strategy} onValueChange={setStrategy}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {ALGORITHM_OPTIONS.map((s) => (
                                        <SelectItem key={s.key} value={s.key}>
                                            {s.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label>{tc('configuration')}</Label>
                            <Select value={clusteringAlgorithm} onValueChange={setClusteringAlgorithm}>
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
                        <div className="space-y-2">
                            <Label>{tc('filter')}</Label>
                            <Input
                                type="date"
                                value={planDate}
                                onChange={(e) => setPlanDate(e.target.value)}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>{tc('details')}</Label>
                            <Select value={direction} onValueChange={(v) => setDirection(v as "pickup" | "dropoff")}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="pickup">{tc('details')}</SelectItem>
                                    <SelectItem value="dropoff">{tc('details')}</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label>&nbsp;</Label>
                            <Button onClick={handleCalculate} disabled={loading} className="w-full">
                                <Calculator className="h-4 w-4 mr-2" />
                                {loading ? tc('loading') : tc('selectAll')}
                            </Button>
                        </div>
                        <div className="space-y-2">
                            <Label>&nbsp;</Label>
                            <Button onClick={handleSavePlan} disabled={isSaving || !result} variant="outline" className="w-full">
                                {isSaving ? tc('loading') : tc('save')}
                            </Button>
                        </div>
                    </div>

                    {/* Student Selection */}
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <Label>
                                {tc('select')} ({selectedStudents.length} {tc('select')}:
                                {selectedSwCount} Sw, {selectedSoCount} So)
                            </Label>
                            <div className="flex gap-2">
                                <Button variant="outline" size="sm" onClick={() => selectAll("Sw")}>
                                    Sw
                                </Button>
                                <Button variant="outline" size="sm" onClick={() => selectAll("So")}>
                                    So
                                </Button>
                                <Button variant="outline" size="sm" onClick={() => selectAll("all")}>
                                    {tc('all')}
                                </Button>
                                <Button variant="ghost" size="sm" onClick={clearAll}>
                                    {tc('clear')}
                                </Button>
                            </div>
                        </div>
                        <ScrollArea className="h-40 w-full rounded-md border p-4 bg-muted/30 relative">
                            {isLoadingStudents ? (
                                <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/50 z-10">
                                    <Activity className="h-6 w-6 text-primary animate-spin mb-2" />
                                    <p className="text-sm text-muted-foreground">{tc('loading')}</p>
                                </div>
                            ) : students.length === 0 ? (
                                <div className="text-center py-8 text-muted-foreground text-sm">
                                    {tc('noResults')}
                                </div>
                            ) : (
                                <>
                                    <div className="mb-3">
                                        <p className="text-xs font-semibold text-muted-foreground mb-2 flex items-center justify-between">
                                            <span>{tc('details')}</span>
                                            <Badge variant="outline">{swStudents.length}</Badge>
                                        </p>
                                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
                                            {swStudents.map((student) => (
                                                <div key={student.id} className="flex items-center space-x-1 border rounded p-1 bg-white hover:bg-slate-50 transition-colors">
                                                    <Checkbox
                                                        id={student.id}
                                                        checked={selectedStudents.includes(student.id)}
                                                        onCheckedChange={() => handleStudentToggle(student.id)}
                                                    />
                                                    <Label htmlFor={student.id} className="text-xs cursor-pointer truncate" title={student.name || tc('select')}>
                                                        {(student as User & { location_code?: string }).location_code || student.locationCode || tc('details')}
                                                    </Label>
                                                </div>
                                            ))}
                                            {swStudents.length === 0 && <span className="text-xs italic text-muted-foreground">{tc('noResults')}</span>}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ))}
                    </div>
                    {/* SO Students */}
                    {soStudents.length > 0 && (
                        <div>
                            <h4 className="font-semibold text-sm mb-2">{tc('wheelchairStudents')} ({soStudents.length})</h4>
                            <div className="flex flex-wrap gap-2 p-2 border rounded-md min-h-[80px]">
                                {soStudents.filter(student => driverStudentMap[driverIndex]?.includes(student.id)).map((student) => (
                                    <div key={student.id} className="flex items-center gap-1.5 bg-muted p-1 rounded">
                                        <Checkbox
                                            id={student.id}
                                            checked={selectedStudents.has(student.id)}
                                            onCheckedChange={() => handleStudentToggle(student.id)}
                                        />
                                        <Label htmlFor={student.id} className="text-xs cursor-pointer truncate" title={student.name || tc('select')}>
                                                        {(student as User & { location_code?: string }).location_code || student.locationCode || tc('details')}
                                                    </Label>
                                                </div>
                                            ))}
                                            {soStudents.length === 0 && <span className="text-xs italic text-muted-foreground">{tc('noResults')}</span>}
                                        </div>
                                    </div>
                                </>
                            )}
                        </ScrollArea>
                    </div>
                </CardContent>
            </Card>

            {/* Results */}
            {result && (
                <Card className={`border-l-4 ${result.success ? "border-l-green-500" : "border-l-red-500"}`}>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Truck className={result.success ? "text-green-500" : "text-red-500"} />
                            {tc('details')}: {result.requiredVehicles} {tc('sidebar.vehicleManagement')}
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {/* Summary */}
                        <div className="grid gap-4 md:grid-cols-4">
                            <div className="p-4 rounded-lg bg-muted">
                                <div className="text-sm text-muted-foreground flex items-center gap-1">
                                    <Truck className="h-3 w-3" /> {tc('sidebar.vehicleManagement')}
                                </div>
                                <div className="text-2xl font-bold">{result.requiredVehicles}</div>
                            </div>
                            <div className="p-4 rounded-lg bg-muted">
                                <div className="text-sm text-muted-foreground flex items-center gap-1">
                                    <Users className="h-3 w-3" /> {tc('select')}
                                </div>
                                <div className="text-2xl font-bold">{result.meta?.validStudentCount || 0}</div>
                            </div>
                            <div className="p-4 rounded-lg bg-muted">
                                <div className="text-sm text-muted-foreground flex items-center gap-1">
                                    <Clock className="h-3 w-3" /> {tc('details')}
                                </div>
                                <div className="text-2xl font-bold">{result.totalDuration} dk</div>
                            </div>
                            <div className="p-4 rounded-lg bg-muted">
                                <div className="text-sm text-muted-foreground">{tc('edit')}</div>
                                <div className="text-2xl font-bold">{result.meta?.calculationTimeMs || 0} ms</div>
                            </div>
                        </div>

                        {/* Vehicle Assignments */}
                        {result.assignments && result.assignments.length > 0 && (
                            <div className="space-y-4">
                                <Label>{tc('sidebar.vehicleManagement')}</Label>
                                {result.assignments.map((assignment: any) => (
                                    <div key={assignment.vehicleIndex} className="border rounded-lg p-4">
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="font-semibold flex items-center gap-2">
                                                <Truck className="h-4 w-4" />
                                                {tc('sidebar.vehicleManagement')} {assignment.vehicleIndex}
                                            </div>
                                            <div className="flex gap-2">
                                                <Badge variant="outline">Sw: {assignment.swCount}</Badge>
                                                <Badge variant="outline">So: {assignment.soCount}</Badge>
                                                <Badge>{assignment.totalDuration} dk</Badge>
                                            </div>
                                        </div>
                                        <div className="flex flex-wrap gap-1 mb-2">
                                            {assignment.students.map((s: any) => (
                                                <Badge
                                                    key={s.id}
                                                    variant={s.disabilityType === "Sw" ? "default" : "secondary"}
                                                >
                                                    {s.locationCode}
                                                </Badge>
                                            ))}
                                        </div>
                                        {assignment.route && assignment.route.length > 0 && (
                                            <div className="text-xs text-muted-foreground flex flex-wrap items-center gap-1">
                                                <span className="font-medium">{tc('details')}:</span>
                                                {assignment.route.map((r: any, i: number) => (
                                                    <span key={i} className="flex items-center gap-1">
                                                        {i === 0 && <span>{r.location1}</span>}
                                                        <ArrowRight className="h-3 w-3" />
                                                        <span>{r.location2}</span>
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Message */}
                        <div className="p-3 rounded-lg bg-muted flex items-start gap-2">
                            <Info className="h-4 w-4 mt-0.5 text-muted-foreground" />
                            <span className="text-sm">{result.message}</span>
                        </div>
                    </CardContent>
                </Card>
            )}

            {ieData && (
                <IEDashboard
                    ieData={ieData}
                    onRefresh={() => handleCalculate()}
                    onExport={() => console.log("Export IE report")}
                />
            )}
        </div>
    );
}
