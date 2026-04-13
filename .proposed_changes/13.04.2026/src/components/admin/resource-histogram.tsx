"use client";

/**
 * Resource Histogram Component
 * Saatlik araç ihtiyacı görselleştirmesi (Stacked bar chart)
 * 
 * Konuşma Geçmişi Madde 21: "Zaman çizelgesi x ekseni saat olacak şekilde 
 * gidiş için ve geliş için gerekli araçlar stack edilmiş"
 */

import { useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, TrendingUp, Users, Clock } from "lucide-react";
import type { HourlyDemandData, BottleneckData } from "@/types/ie-resource";

interface ResourceHistogramProps {
    hourlyDemand: Record<string, HourlyDemandData>;
    availableVehicles?: number;
    showBottlenecks?: boolean;
    onHourClick?: (hour: string) => void;
}

export function ResourceHistogram({
    hourlyDemand,
    availableVehicles = 5,
    showBottlenecks = true,
    onHourClick,
}: ResourceHistogramProps) {
    // Saatleri sırala
    const sortedHours = useMemo(() => {
        return Object.keys(hourlyDemand).sort();
    }, [hourlyDemand]);

    // Maksimum değeri bul (grafik ölçeklendirme için)
    const maxValue = useMemo(() => {
        let max = 0;
        Object.values(hourlyDemand).forEach((d) => {
            const total = Math.max(d.totalPickup, d.totalDropoff);
            max = Math.max(max, total);
        });
        return Math.max(max, availableVehicles);
    }, [hourlyDemand, availableVehicles]);

    // Darboğaz saatlerini bul
    const bottleneckHours = useMemo(() => {
        const hours: Set<string> = new Set();
        Object.entries(hourlyDemand).forEach(([hour, demand]) => {
            if (demand.isInfeasible) {
                hours.add(hour);
            }
        });
        return hours;
    }, [hourlyDemand]);

    // Çubuk genişliği hesapla
    const barWidth = Math.min(60, Math.max(30, 800 / sortedHours.length));

    return (
        <Card className="w-full">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <TrendingUp className="h-5 w-5" />
                            Saatlik Araç İhtiyacı
                        </CardTitle>
                        <CardDescription>
                            Pickup ve Dropoff taleplerinin saatlik dağılımı
                        </CardDescription>
                    </div>
                    <div className="flex gap-4 text-sm">
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 bg-blue-500 rounded" />
                            <span>Pickup Sw</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 bg-blue-300 rounded" />
                            <span>Pickup So</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 bg-orange-500 rounded" />
                            <span>Dropoff Sw</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 bg-orange-300 rounded" />
                            <span>Dropoff So</span>
                        </div>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                {/* Histogram */}
                <div className="relative h-64 mt-4">
                    {/* Y ekseni etiketleri */}
                    <div className="absolute left-0 top-0 bottom-8 w-8 flex flex-col justify-between text-xs text-muted-foreground">
                        <span>{maxValue}</span>
                        <span>{Math.round(maxValue / 2)}</span>
                        <span>0</span>
                    </div>

                    {/* Kapasite çizgisi */}
                    {availableVehicles > 0 && (
                        <div
                            className="absolute left-8 right-0 border-t-2 border-dashed border-red-400 z-10"
                            style={{
                                bottom: `${(availableVehicles / maxValue) * 100}%`,
                            }}
                        >
                            <span className="absolute -top-5 right-0 text-xs text-red-500 bg-red-50 px-2 py-0.5 rounded">
                                Kapasite: {availableVehicles}
                            </span>
                        </div>
                    )}

                    {/* Histogram çubukları */}
                    <div className="absolute left-8 right-0 top-0 bottom-8 flex items-end justify-around">
                        {sortedHours.map((hour) => {
                            const demand = hourlyDemand[hour];
                            const hasData = demand.totalPickup > 0 || demand.totalDropoff > 0;
                            const isInfeasible = demand.isInfeasible || bottleneckHours.has(hour);

                            if (!hasData) return null;

                            const pickupHeight = (demand.totalPickup / maxValue) * 100;
                            const dropoffHeight = (demand.totalDropoff / maxValue) * 100;

                            return (
                                <div
                                    key={hour}
                                    className="flex flex-col items-center cursor-pointer hover:opacity-80 transition-opacity"
                                    style={{ width: barWidth }}
                                    onClick={() => onHourClick?.(hour)}
                                >
                                    {/* Tooltip */}
                                    <div className="opacity-0 hover:opacity-100 absolute -mt-20 bg-popover border rounded-lg p-2 shadow-lg z-20 text-xs whitespace-nowrap">
                                        <div className="font-semibold">{hour}</div>
                                        <div className="text-blue-600">
                                            Pickup: Sw={demand.pickupSw}, So={demand.pickupSo}
                                        </div>
                                        <div className="text-orange-600">
                                            Dropoff: Sw={demand.dropoffSw}, So={demand.dropoffSo}
                                        </div>
                                    </div>

                                    {/* Pickup çubuğu */}
                                    {demand.totalPickup > 0 && (
                                        <div
                                            className="w-full flex flex-col-reverse rounded-t overflow-hidden"
                                            style={{ height: `${pickupHeight}%` }}
                                        >
                                            {/* Sw */}
                                            <div
                                                className="bg-blue-500 w-full"
                                                style={{
                                                    height: `${(demand.pickupSw / Math.max(demand.totalPickup, 1)) * 100}%`,
                                                }}
                                            />
                                            {/* So */}
                                            <div
                                                className="bg-blue-300 w-full"
                                                style={{
                                                    height: `${(demand.pickupSo / Math.max(demand.totalPickup, 1)) * 100}%`,
                                                }}
                                            />
                                        </div>
                                    )}

                                    {/* Dropoff çubuğu */}
                                    {demand.totalDropoff > 0 && (
                                        <div
                                            className="w-full flex flex-col-reverse rounded-t overflow-hidden mt-0.5"
                                            style={{ height: `${dropoffHeight}%` }}
                                        >
                                            {/* Sw */}
                                            <div
                                                className="bg-orange-500 w-full"
                                                style={{
                                                    height: `${(demand.dropoffSw / Math.max(demand.totalDropoff, 1)) * 100}%`,
                                                }}
                                            />
                                            {/* So */}
                                            <div
                                                className="bg-orange-300 w-full"
                                                style={{
                                                    height: `${(demand.dropoffSo / Math.max(demand.totalDropoff, 1)) * 100}%`,
                                                }}
                                            />
                                        </div>
                                    )}

                                    {/* Saat etiketi */}
                                    <span className={`text-xs mt-1 ${isInfeasible ? "text-red-600 font-bold" : "text-muted-foreground"}`}>
                                        {hour}
                                    </span>

                                    {/* Darboğaz göstergesi */}
                                    {isInfeasible && showBottlenecks && (
                                        <AlertCircle className="h-4 w-4 text-red-500 absolute -top-4" />
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Özet istatistikler */}
                <div className="grid grid-cols-4 gap-4 mt-6 pt-4 border-t">
                    <div className="text-center">
                        <div className="text-2xl font-bold text-blue-600">
                            {Object.values(hourlyDemand).reduce((sum, d) => sum + d.pickupSw, 0)}
                        </div>
                        <div className="text-xs text-muted-foreground">Toplam Pickup Sw</div>
                    </div>
                    <div className="text-center">
                        <div className="text-2xl font-bold text-blue-400">
                            {Object.values(hourlyDemand).reduce((sum, d) => sum + d.pickupSo, 0)}
                        </div>
                        <div className="text-xs text-muted-foreground">Toplam Pickup So</div>
                    </div>
                    <div className="text-center">
                        <div className="text-2xl font-bold text-orange-600">
                            {Object.values(hourlyDemand).reduce((sum, d) => sum + d.dropoffSw, 0)}
                        </div>
                        <div className="text-xs text-muted-foreground">Toplam Dropoff Sw</div>
                    </div>
                    <div className="text-center">
                        <div className="text-2xl font-bold text-orange-400">
                            {Object.values(hourlyDemand).reduce((sum, d) => sum + d.dropoffSo, 0)}
                        </div>
                        <div className="text-xs text-muted-foreground">Toplam Dropoff So</div>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

/**
 * Compact Resource Histogram for summary views
 */
export function ResourceHistogramCompact({
    hourlyDemand,
    availableVehicles = 5,
}: ResourceHistogramProps) {
    const sortedHours = useMemo(() => {
        return Object.keys(hourlyDemand).sort();
    }, [hourlyDemand]);

    const maxValue = useMemo(() => {
        let max = 0;
        Object.values(hourlyDemand).forEach((d) => {
            const total = d.totalPickup + d.totalDropoff;
            max = Math.max(max, total);
        });
        return Math.max(max, availableVehicles);
    }, [hourlyDemand, availableVehicles]);

    return (
        <div className="h-16 flex items-end gap-1">
            {sortedHours.map((hour) => {
                const demand = hourlyDemand[hour];
                const hasData = demand.totalPickup > 0 || demand.totalDropoff > 0;
                
                if (!hasData) return null;

                const total = demand.totalPickup + demand.totalDropoff;
                const height = (total / maxValue) * 100;
                const isInfeasible = demand.isInfeasible || total > availableVehicles;

                return (
                    <div
                        key={hour}
                        className="flex-1 flex flex-col items-center"
                        title={`${hour}: ${total} öğrenci`}
                    >
                        <div
                            className={`w-full rounded-t ${isInfeasible ? "bg-red-500" : "bg-primary"}`}
                            style={{ height: `${height}%`, minHeight: "4px" }}
                        />
                    </div>
                );
            })}
        </div>
    );
}
