"use client";

import { useState } from "react";
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
import { Truck, Users, Clock, Calculator, ArrowRight, Info } from "lucide-react";
import { ALL_LOCATIONS } from "@/services/doubus/route";

// Test students data (based on Excel data)
const testStudents = [
    ...Array.from({ length: 9 }, (_, i) => ({
        id: `sw-${i + 1}`,
        name: `Sw${i + 1} Öğrenci`,
        locationCode: `Sw${i + 1}`,
        disabilityType: "Sw" as const,
    })),
    ...Array.from({ length: 19 }, (_, i) => ({
        id: `so-${i + 1}`,
        name: `So${i + 1} Öğrenci`,
        locationCode: `So${i + 1}`,
        disabilityType: "So" as const,
    })),
];

// Strategies
const strategies = [
    { name: "nearest-neighbor", label: "En Yakın Komşu (Hızlı)" },
    { name: "two-opt", label: "2-opt (Dengeli)" },
    { name: "permutation", label: "Permütasyon (Optimal)" },
];

export default function VehiclePlanningPage() {
    const { toast } = useToast();
    const [loading, setLoading] = useState(false);
    const [selectedStudents, setSelectedStudents] = useState<string[]>([]);
    const [maxTourTime, setMaxTourTime] = useState(120);
    const [swCapacity, setSwCapacity] = useState(4);
    const [soCapacity, setSoCapacity] = useState(5);
    const [strategy, setStrategy] = useState("two-opt");
    const [result, setResult] = useState<any>(null);

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
            setSelectedStudents(testStudents.map(s => s.id));
        } else {
            const ids = testStudents.filter(s => s.disabilityType === type).map(s => s.id);
            setSelectedStudents(prev => [...new Set([...prev, ...ids])]);
        }
    };

    const clearAll = () => setSelectedStudents([]);

    const handleCalculate = async () => {
        try {
            setLoading(true);
            setResult(null);

            const students = testStudents.filter(s => selectedStudents.includes(s.id));

            if (students.length === 0) {
                toast({
                    title: "Hata",
                    description: "En az bir öğrenci seçin",
                    variant: "destructive",
                });
                return;
            }

            const response = await fetch("/api/calculate-vehicles", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    students,
                    maxTourTime,
                    swCapacity,
                    soCapacity,
                    strategy,
                }),
            });

            if (!response.ok) {
                throw new Error("Hesaplama başarısız");
            }

            const data = await response.json();
            setResult(data);

            toast({
                title: "Hesaplama Tamamlandı",
                description: `${data.requiredVehicles} araç gerekli`,
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

    const swStudents = testStudents.filter(s => s.disabilityType === "Sw");
    const soStudents = testStudents.filter(s => s.disabilityType === "So");
    const selectedSwCount = selectedStudents.filter(id => id.startsWith("sw-")).length;
    const selectedSoCount = selectedStudents.filter(id => id.startsWith("so-")).length;

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Truck className="text-primary" />
                        Araç Planlama
                    </CardTitle>
                    <CardDescription>
                        Öğrencileri seçin, kapasite ve kısıtları belirleyin, gerekli araç sayısını hesaplayın
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {/* Parameters */}
                    <div className="grid gap-4 md:grid-cols-5">
                        <div className="space-y-2">
                            <Label>Sw Kapasitesi</Label>
                            <Input
                                type="number"
                                value={swCapacity}
                                onChange={(e) => setSwCapacity(Number(e.target.value))}
                                min={1}
                            />
                            <p className="text-xs text-muted-foreground">Tekerlekli sandalye</p>
                        </div>
                        <div className="space-y-2">
                            <Label>So Kapasitesi</Label>
                            <Input
                                type="number"
                                value={soCapacity}
                                onChange={(e) => setSoCapacity(Number(e.target.value))}
                                min={1}
                            />
                            <p className="text-xs text-muted-foreground">Normal koltuk</p>
                        </div>
                        <div className="space-y-2">
                            <Label>Max Tur Süresi</Label>
                            <Input
                                type="number"
                                value={maxTourTime}
                                onChange={(e) => setMaxTourTime(Number(e.target.value))}
                                min={30}
                            />
                            <p className="text-xs text-muted-foreground">Dakika</p>
                        </div>
                        <div className="space-y-2">
                            <Label>Strateji</Label>
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
                        </div>
                        <div className="space-y-2">
                            <Label>&nbsp;</Label>
                            <Button onClick={handleCalculate} disabled={loading} className="w-full">
                                <Calculator className="h-4 w-4 mr-2" />
                                {loading ? "Hesaplanıyor..." : "Hesapla"}
                            </Button>
                        </div>
                    </div>

                    {/* Student Selection */}
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <Label>
                                Öğrenci Seçimi ({selectedStudents.length} seçili:
                                {selectedSwCount} Sw, {selectedSoCount} So)
                            </Label>
                            <div className="flex gap-2">
                                <Button variant="outline" size="sm" onClick={() => selectAll("Sw")}>
                                    Tüm Sw
                                </Button>
                                <Button variant="outline" size="sm" onClick={() => selectAll("So")}>
                                    Tüm So
                                </Button>
                                <Button variant="outline" size="sm" onClick={() => selectAll("all")}>
                                    Tümü
                                </Button>
                                <Button variant="ghost" size="sm" onClick={clearAll}>
                                    Temizle
                                </Button>
                            </div>
                        </div>
                        <ScrollArea className="h-40 w-full rounded-md border p-4 bg-muted/30">
                            <div className="mb-3">
                                <p className="text-xs font-semibold text-muted-foreground mb-2">
                                    Sw Öğrenciler (Tekerlekli Sandalye)
                                </p>
                                <div className="grid grid-cols-5 sm:grid-cols-6 md:grid-cols-9 gap-2">
                                    {swStudents.map((student) => (
                                        <div key={student.id} className="flex items-center space-x-1">
                                            <Checkbox
                                                id={student.id}
                                                checked={selectedStudents.includes(student.id)}
                                                onCheckedChange={() => handleStudentToggle(student.id)}
                                            />
                                            <Label htmlFor={student.id} className="text-xs cursor-pointer">
                                                {student.locationCode}
                                            </Label>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <Separator className="my-3" />
                            <div>
                                <p className="text-xs font-semibold text-muted-foreground mb-2">
                                    So Öğrenciler (Diğer Engel Tipi)
                                </p>
                                <div className="grid grid-cols-5 sm:grid-cols-6 md:grid-cols-10 gap-2">
                                    {soStudents.map((student) => (
                                        <div key={student.id} className="flex items-center space-x-1">
                                            <Checkbox
                                                id={student.id}
                                                checked={selectedStudents.includes(student.id)}
                                                onCheckedChange={() => handleStudentToggle(student.id)}
                                            />
                                            <Label htmlFor={student.id} className="text-xs cursor-pointer">
                                                {student.locationCode}
                                            </Label>
                                        </div>
                                    ))}
                                </div>
                            </div>
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
                            Sonuç: {result.requiredVehicles} Araç
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {/* Summary */}
                        <div className="grid gap-4 md:grid-cols-4">
                            <div className="p-4 rounded-lg bg-muted">
                                <div className="text-sm text-muted-foreground flex items-center gap-1">
                                    <Truck className="h-3 w-3" /> Araç Sayısı
                                </div>
                                <div className="text-2xl font-bold">{result.requiredVehicles}</div>
                            </div>
                            <div className="p-4 rounded-lg bg-muted">
                                <div className="text-sm text-muted-foreground flex items-center gap-1">
                                    <Users className="h-3 w-3" /> Öğrenci
                                </div>
                                <div className="text-2xl font-bold">{result.meta?.validStudentCount || 0}</div>
                            </div>
                            <div className="p-4 rounded-lg bg-muted">
                                <div className="text-sm text-muted-foreground flex items-center gap-1">
                                    <Clock className="h-3 w-3" /> Toplam Süre
                                </div>
                                <div className="text-2xl font-bold">{result.totalDuration} dk</div>
                            </div>
                            <div className="p-4 rounded-lg bg-muted">
                                <div className="text-sm text-muted-foreground">Hesaplama</div>
                                <div className="text-2xl font-bold">{result.meta?.calculationTimeMs || 0} ms</div>
                            </div>
                        </div>

                        {/* Vehicle Assignments */}
                        {result.assignments && result.assignments.length > 0 && (
                            <div className="space-y-4">
                                <Label>Araç Atamaları</Label>
                                {result.assignments.map((assignment: any) => (
                                    <div key={assignment.vehicleIndex} className="border rounded-lg p-4">
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="font-semibold flex items-center gap-2">
                                                <Truck className="h-4 w-4" />
                                                Araç {assignment.vehicleIndex}
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
                                                <span className="font-medium">Rota:</span>
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
        </div>
    );
}
