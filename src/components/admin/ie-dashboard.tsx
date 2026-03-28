"use client";

/**
 * IE Dashboard Component
 * Endüstri Mühendisliği Kaynak Yönetimi Dashboard
 * 
 * Tüm IE verilerini bir arada gösterir:
 * - Standart araç ihtiyacı
 * - Saatlik talep histogramı
 * - Araç kullanım çizelgesi (Gantt)
 * - Darboğaz göstergeleri
 * - Zaman kaydırma önerileri
 */

import { useState, useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
    BarChart3,
    Truck,
    Clock,
    Users,
    AlertCircle,
    TrendingUp,
    Calendar,
    Download,
    RefreshCw,
} from "lucide-react";

import { ResourceHistogram } from "./resource-histogram";
import { ResourceTracks } from "./resource-tracks";
import { BottleneckIndicator } from "./bottleneck-indicator";

import type {
    IEResponseData,
    HourlyDemandData,
    ResourceBlock,
    VehicleConfig,
} from "@/types/ie-resource";

interface IEDashboardProps {
    ieData: IEResponseData;
    availableVehicles?: VehicleConfig[];
    onRefresh?: () => void;
    onExport?: () => void;
}

export function IEDashboard({
    ieData,
    availableVehicles = [],
    onRefresh,
    onExport,
}: IEDashboardProps) {
    const [activeTab, setActiveTab] = useState("overview");

    // Demo araçları (gerçek veri yoksa)
    const vehicles = useMemo(() => {
        if (availableVehicles.length > 0) return availableVehicles;

        // Varsayılan araçlar
        return Array.from({ length: ieData.summary.availableVehicles }, (_, i) => ({
            vehicleId: `vehicle_${i + 1}`,
            name: `Araç ${i + 1}`,
            swCapacity: 4,
            soCapacity: 5,
        }));
    }, [availableVehicles, ieData.summary.availableVehicles]);

    // Demo bloklar (gerçek rota verisi yoksa)
    const resourceBlocks = useMemo(() => {
        const blocks: ResourceBlock[] = [];
        const pickupHours = [8, 9, 10, 11];
        const dropoffHours = [14, 15, 16, 17];

        vehicles.forEach((vehicle, idx) => {
            // Pickup bloğu
            if (idx < pickupHours.length) {
                blocks.push({
                    vehicleId: vehicle.vehicleId,
                    startTime: pickupHours[idx] * 60,
                    endTime: (pickupHours[idx] + 2) * 60 + 15,
                    direction: "pickup",
                    students: [],
                    swCount: 2,
                    soCount: 3,
                });
            }

            // Dropoff bloğu
            if (idx < dropoffHours.length) {
                blocks.push({
                    vehicleId: vehicle.vehicleId,
                    startTime: dropoffHours[idx] * 60,
                    endTime: (dropoffHours[idx] + 2) * 60 + 15,
                    direction: "dropoff",
                    students: [],
                    swCount: 2,
                    soCount: 3,
                });
            }
        });

        return blocks;
    }, [vehicles]);

    // Yüksek öncelikli darboğaz sayısı
    const highPriorityBottlenecks = ieData.bottlenecks.filter(
        (b) => b.severity === "high"
    ).length;

    return (
        <div className="space-y-6">
            {/* Başlık ve aksiyonlar */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold flex items-center gap-2">
                        <BarChart3 className="h-6 w-6" />
                        IE Kaynak Analizi
                    </h2>
                    <p className="text-muted-foreground">
                        Endüstri Mühendisliği kaynak yönetimi ve optimizasyon önerileri
                    </p>
                </div>
                <div className="flex gap-2">
                    {onRefresh && (
                        <Button variant="outline" size="sm" onClick={onRefresh}>
                            <RefreshCw className="h-4 w-4 mr-2" />
                            Yenile
                        </Button>
                    )}
                    {onExport && (
                        <Button variant="outline" size="sm" onClick={onExport}>
                            <Download className="h-4 w-4 mr-2" />
                            Dışa Aktar
                        </Button>
                    )}
                </div>
            </div>

            {/* Özet kartları */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card>
                    <CardContent className="pt-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-muted-foreground">Toplam Öğrenci</p>
                                <p className="text-2xl font-bold">
                                    {ieData.summary.totalStudents}
                                </p>
                            </div>
                            <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                                <Users className="h-5 w-5 text-blue-600" />
                            </div>
                        </div>
                        <div className="mt-2 text-xs text-muted-foreground">
                            Sw: {ieData.standardNeeds.swCount} | So:{" "}
                            {ieData.standardNeeds.soCount}
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardContent className="pt-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-muted-foreground">
                                    Standart Araç İhtiyacı
                                </p>
                                <p className="text-2xl font-bold">
                                    {ieData.summary.standardVehiclesNeeded}
                                </p>
                            </div>
                            <div className="h-10 w-10 rounded-full bg-green-100 flex items-center justify-center">
                                <Truck className="h-5 w-5 text-green-600" />
                            </div>
                        </div>
                        <div className="mt-2 text-xs text-muted-foreground">
                            4Sw + 5So kapasiteli minibüs
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardContent className="pt-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-muted-foreground">Mevcut Araç</p>
                                <p className="text-2xl font-bold">
                                    {ieData.summary.availableVehicles}
                                </p>
                            </div>
                            <div className="h-10 w-10 rounded-full bg-purple-100 flex items-center justify-center">
                                <Calendar className="h-5 w-5 text-purple-600" />
                            </div>
                        </div>
                        <div className="mt-2 text-xs text-muted-foreground">
                            {ieData.summary.availableVehicles >=
                            ieData.summary.standardVehiclesNeeded
                                ? "✅ Yeterli"
                                : "⚠️ Yetersiz"}
                        </div>
                    </CardContent>
                </Card>

                <Card
                    className={
                        highPriorityBottlenecks > 0
                            ? "border-red-300"
                            : ieData.summary.bottleneckCount > 0
                            ? "border-orange-300"
                            : "border-green-300"
                    }
                >
                    <CardContent className="pt-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-muted-foreground">Darboğaz</p>
                                <p className="text-2xl font-bold">
                                    {ieData.summary.bottleneckCount}
                                </p>
                            </div>
                            <div
                                className={`h-10 w-10 rounded-full flex items-center justify-center ${
                                    highPriorityBottlenecks > 0
                                        ? "bg-red-100"
                                        : ieData.summary.bottleneckCount > 0
                                        ? "bg-orange-100"
                                        : "bg-green-100"
                                }`}
                            >
                                <AlertCircle
                                    className={`h-5 w-5 ${
                                        highPriorityBottlenecks > 0
                                            ? "text-red-600"
                                            : ieData.summary.bottleneckCount > 0
                                            ? "text-orange-600"
                                            : "text-green-600"
                                    }`}
                                />
                            </div>
                        </div>
                        <div className="mt-2 text-xs text-muted-foreground">
                            {highPriorityBottlenecks > 0
                                ? `⚠️ ${highPriorityBottlenecks} yüksek öncelikli`
                                : ieData.summary.bottleneckCount > 0
                                ? "⚡ Optimizasyon önerileri var"
                                : "✅ Darboğaz yok"}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Doluluk oranı */}
            <Card>
                <CardContent className="pt-6">
                    <div className="flex items-center gap-4">
                        <div className="flex-1">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-sm font-medium">Ortalama Doluluk</span>
                                <span className="text-sm text-muted-foreground">
                                    {ieData.standardNeeds.utilizationPercent}%
                                </span>
                            </div>
                            <div className="h-2 bg-muted rounded-full overflow-hidden">
                                <div
                                    className={`h-full rounded-full transition-all ${
                                        ieData.standardNeeds.utilizationPercent > 90
                                            ? "bg-red-500"
                                            : ieData.standardNeeds.utilizationPercent > 75
                                            ? "bg-green-500"
                                            : ieData.standardNeeds.utilizationPercent > 50
                                            ? "bg-yellow-500"
                                            : "bg-blue-500"
                                    }`}
                                    style={{
                                        width: `${Math.min(
                                            ieData.standardNeeds.utilizationPercent,
                                            100
                                        )}%`,
                                    }}
                                />
                            </div>
                            <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                                <span>Sw: {ieData.standardNeeds.utilizationBreakdown.sw}%</span>
                                <span>So: {ieData.standardNeeds.utilizationBreakdown.so}%</span>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Tab navigasyonu */}
            <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="grid w-full grid-cols-3 lg:w-auto">
                    <TabsTrigger value="overview" className="flex items-center gap-2">
                        <TrendingUp className="h-4 w-4" />
                        <span className="hidden sm:inline">Genel Bakış</span>
                        <span className="sm:hidden">Özet</span>
                    </TabsTrigger>
                    <TabsTrigger value="histogram" className="flex items-center gap-2">
                        <BarChart3 className="h-4 w-4" />
                        <span className="hidden sm:inline">Saatlik Talep</span>
                        <span className="sm:hidden">Talep</span>
                    </TabsTrigger>
                    <TabsTrigger value="tracks" className="flex items-center gap-2">
                        <Clock className="h-4 w-4" />
                        <span className="hidden sm:inline">Zaman Çizelgesi</span>
                        <span className="sm:hidden">Gantt</span>
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="overview" className="space-y-6 mt-6">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Darboğaz göstergesi */}
                        <BottleneckIndicator
                            bottlenecks={ieData.bottlenecks}
                            shiftSuggestions={ieData.shiftSuggestions}
                            onSuggestionClick={(suggestion) => {
                                console.log("Suggestion clicked:", suggestion);
                            }}
                        />

                        {/* Saatlik talep (kompakt) */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-base flex items-center gap-2">
                                    <BarChart3 className="h-4 w-4" />
                                    Saatlik Talep Özeti
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-3">
                                    {Object.entries(ieData.hourlyDemand)
                                        .filter(([_, d]) => d.totalPickup > 0 || d.totalDropoff > 0)
                                        .slice(0, 6)
                                        .map(([hour, demand]) => (
                                            <div
                                                key={hour}
                                                className="flex items-center justify-between p-2 bg-muted/50 rounded"
                                            >
                                                <span className="font-medium">{hour}</span>
                                                <div className="flex gap-3 text-sm">
                                                    {demand.totalPickup > 0 && (
                                                        <span className="text-blue-600">
                                                            Pickup: {demand.totalPickup}
                                                        </span>
                                                    )}
                                                    {demand.totalDropoff > 0 && (
                                                        <span className="text-orange-600">
                                                            Dropoff: {demand.totalDropoff}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                <TabsContent value="histogram" className="mt-6">
                    <ResourceHistogram
                        hourlyDemand={ieData.hourlyDemand}
                        availableVehicles={ieData.summary.availableVehicles}
                        onHourClick={(hour) => {
                            console.log("Hour clicked:", hour);
                        }}
                    />
                </TabsContent>

                <TabsContent value="tracks" className="mt-6">
                    <ResourceTracks
                        vehicles={vehicles}
                        blocks={resourceBlocks}
                        onBlockClick={(block) => {
                            console.log("Block clicked:", block);
                        }}
                    />
                </TabsContent>
            </Tabs>

            {/* Alt bilgi */}
            <div className="text-center text-xs text-muted-foreground pt-4 border-t">
                <p>
                    IE Analizi sonucu üretilmiştir. Standart araç: 4 Sw + 5 So kapasiteli
                    minibüs.
                </p>
                <p className="mt-1">
                    Kapasite: Sw (Wheelchair) = Tekerlekli sandalye | So (Other) = Diğer
                    engel grupları
                </p>
            </div>
        </div>
    );
}
