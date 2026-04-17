"use client";

/**
 * Resource Tracks Component (Gantt Chart)
 * Araç kullanım zaman çizelgesi
 * 
 * Konuşma Geçmişi Madde 21: "Araç kullanım blokları da saatlik talep 
 * grafiğinin x ekseni ile hizalı olursa hangi araç hangi saat 
 * diliminde kullanılıyor net görüntülenebilir"
 */

import { useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Truck, Clock, AlertCircle } from "lucide-react";
import type { ResourceBlock, VehicleConfig } from "@/types/ie-resource";

interface ResourceTracksProps {
    vehicles: VehicleConfig[];
    blocks: ResourceBlock[];
    timeRange?: { start: number; end: number }; // hours (6-22 default)
    onBlockClick?: (block: ResourceBlock) => void;
}

// Renk şeması
const DIRECTION_COLORS = {
    pickup: {
        bg: "bg-blue-500",
        bgLight: "bg-blue-100",
        text: "text-blue-700",
        border: "border-blue-300",
    },
    dropoff: {
        bg: "bg-orange-500",
        bgLight: "bg-orange-100",
        text: "text-orange-700",
        border: "border-orange-300",
    },
};

export function ResourceTracks({
    vehicles,
    blocks,
    timeRange = { start: 6, end: 22 },
    onBlockClick,
}: ResourceTracksProps) {
    const totalMinutes = (timeRange.end - timeRange.start) * 60;

    // Saat etiketleri
    const hourLabels = useMemo(() => {
        const labels = [];
        for (let h = timeRange.start; h <= timeRange.end; h++) {
            labels.push(`${h.toString().padStart(2, "0")}:00`);
        }
        return labels;
    }, [timeRange]);

    // Dakikayı piksel pozisyonuna çevir
    const minuteToPosition = (minutes: number) => {
        const relativeMinutes = minutes - timeRange.start * 60;
        return (relativeMinutes / totalMinutes) * 100;
    };

    // Blok genişliğini hesapla
    const blockStyle = (block: ResourceBlock) => {
        const left = minuteToPosition(block.startTime);
        const width = ((block.endTime - block.startTime) / totalMinutes) * 100;
        return { left: `${left}%`, width: `${width}%` };
    };

    // Her araç için blokları grupla
    const vehicleBlocks = useMemo(() => {
        const grouped: Record<string, ResourceBlock[]> = {};
        vehicles.forEach((v) => {
            grouped[v.vehicleId] = blocks.filter((b) => b.vehicleId === v.vehicleId);
        });
        return grouped;
    }, [vehicles, blocks]);

    // Çakışma kontrolü
    const conflicts = useMemo(() => {
        const conflictBlocks: ResourceBlock[] = [];
        
        vehicles.forEach((vehicle) => {
            const vBlocks = vehicleBlocks[vehicle.vehicleId] || [];
            
            for (let i = 0; i < vBlocks.length; i++) {
                for (let j = i + 1; j < vBlocks.length; j++) {
                    const b1 = vBlocks[i];
                    const b2 = vBlocks[j];
                    
                    // Zaman çakışması var mı?
                    if (b1.endTime > b2.startTime && b2.endTime > b1.startTime) {
                        if (!conflictBlocks.includes(b1)) conflictBlocks.push(b1);
                        if (!conflictBlocks.includes(b2)) conflictBlocks.push(b2);
                    }
                }
            }
        });
        
        return conflictBlocks;
    }, [vehicles, vehicleBlocks]);

    return (
        <Card className="w-full">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <Truck className="h-5 w-5" />
                            Araç Kullanım Zaman Çizelgesi
                        </CardTitle>
                        <CardDescription>
                            Pickup ve Dropoff bloklarının zaman içindeki dağılımı
                        </CardDescription>
                    </div>
                    <div className="flex gap-4 text-sm">
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 bg-blue-500 rounded" />
                            <span>Pickup (Okula Geliş)</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 bg-orange-500 rounded" />
                            <span>Dropoff (Okuldan Dönüş)</span>
                        </div>
                        {conflicts.length > 0 && (
                            <div className="flex items-center gap-2 text-red-600">
                                <AlertCircle className="h-4 w-4" />
                                <span>{conflicts.length} çakışma</span>
                            </div>
                        )}
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                {/* Zaman ekseni */}
                <div className="relative mb-2">
                    <div className="flex justify-between text-xs text-muted-foreground px-2">
                        {hourLabels.map((hour) => (
                            <span key={hour}>{hour}</span>
                        ))}
                    </div>
                    {/* Grid çizgileri */}
                    <div className="absolute top-4 left-0 right-0 h-full flex justify-between pointer-events-none">
                        {hourLabels.map((_, i) => (
                            <div
                                key={i}
                                className="h-64 border-l border-dashed border-border"
                                style={{ marginLeft: i === 0 ? 0 : undefined }}
                            />
                        ))}
                    </div>
                </div>

                {/* Araç satırları */}
                <div className="space-y-3 mt-6">
                    {vehicles.map((vehicle) => {
                        const vBlocks = vehicleBlocks[vehicle.vehicleId] || [];
                        const hasConflict = vBlocks.some((b) =>
                            conflicts.some((c) => c.vehicleId === b.vehicleId && c.startTime === b.startTime)
                        );

                        return (
                            <div
                                key={vehicle.vehicleId}
                                className="relative flex items-center gap-3 h-12"
                            >
                                {/* Araç etiketi */}
                                <div className="w-32 shrink-0">
                                    <div className="font-medium text-sm truncate">
                                        {vehicle.name || vehicle.vehicleId}
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                        {vehicle.swCapacity}Sw + {vehicle.soCapacity}So
                                    </div>
                                    {hasConflict && (
                                        <AlertCircle className="h-3 w-3 text-red-500 inline ml-1" />
                                    )}
                                </div>

                                {/* Bloklar */}
                                <div className="flex-1 relative h-full bg-muted/30 rounded overflow-hidden">
                                    {vBlocks.map((block, idx) => {
                                        const colors = DIRECTION_COLORS[block.direction];
                                        const isConflict = conflicts.includes(block);

                                        return (
                                            <div
                                                key={`${block.vehicleId}-${idx}`}
                                                className={`
                                                    absolute top-1 bottom-1 rounded cursor-pointer
                                                    ${colors.bg} hover:opacity-80 transition-opacity
                                                    ${isConflict ? "ring-2 ring-red-500 ring-offset-1" : ""}
                                                `}
                                                style={blockStyle(block)}
                                                onClick={() => onBlockClick?.(block)}
                                                title={`
                                                    ${block.vehicleId}
                                                    ${block.direction === 'pickup' ? 'Pickup' : 'Dropoff'}
                                                    ${Math.floor(block.startTime / 60)}:${(block.startTime % 60).toString().padStart(2, '0')} - 
                                                    ${Math.floor(block.endTime / 60)}:${(block.endTime % 60).toString().padStart(2, '0')}
                                                    ${block.swCount}Sw + ${block.soCount}So
                                                `}
                                            >
                                                {/* Blok içeriği */}
                                                <div className="h-full flex items-center justify-center text-white text-xs font-medium">
                                                    {block.direction === 'pickup' ? 'P' : 'D'}
                                                    <span className="ml-1 hidden sm:inline">
                                                        {block.swCount + block.soCount}
                                                    </span>
                                                </div>
                                            </div>
                                        );
                                    })}

                                    {/* Boş durum */}
                                    {vBlocks.length === 0 && (
                                        <div className="absolute inset-0 flex items-center justify-center text-xs text-muted-foreground">
                                            Kullanılmıyor
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* Cooldown açıklaması */}
                <div className="mt-4 text-xs text-muted-foreground text-center">
                    <Clock className="h-3 w-3 inline mr-1" />
                    Bloklar rotasyon süresini içerir (+15 dk cooldown)
                </div>
            </CardContent>
        </Card>
    );
}

/**
 * Compact Resource Tracks for summary views
 */
export function ResourceTracksCompact({
    vehicles,
    blocks,
    timeRange = { start: 6, end: 22 },
}: ResourceTracksProps) {
    const totalMinutes = (timeRange.end - timeRange.start) * 60;

    const minuteToPosition = (minutes: number) => {
        const relativeMinutes = minutes - timeRange.start * 60;
        return (relativeMinutes / totalMinutes) * 100;
    };

    const vehicleBlocks = useMemo(() => {
        const grouped: Record<string, ResourceBlock[]> = {};
        vehicles.forEach((v) => {
            grouped[v.vehicleId] = blocks.filter((b) => b.vehicleId === v.vehicleId);
        });
        return grouped;
    }, [vehicles, blocks]);

    return (
        <div className="space-y-2">
            {vehicles.slice(0, 3).map((vehicle) => {
                const vBlocks = vehicleBlocks[vehicle.vehicleId] || [];
                
                return (
                    <div key={vehicle.vehicleId} className="flex items-center gap-2">
                        <span className="text-xs w-20 truncate">{vehicle.vehicleId}</span>
                        <div className="flex-1 h-6 bg-muted rounded relative overflow-hidden">
                            {vBlocks.map((block, idx) => {
                                const left = minuteToPosition(block.startTime);
                                const width = ((block.endTime - block.startTime) / totalMinutes) * 100;
                                
                                return (
                                    <div
                                        key={idx}
                                        className={`absolute top-0 bottom-0 ${
                                            block.direction === 'pickup' ? 'bg-blue-500' : 'bg-orange-500'
                                        }`}
                                        style={{ left: `${left}%`, width: `${width}%` }}
                                    />
                                );
                            })}
                        </div>
                    </div>
                );
            })}
            {vehicles.length > 3 && (
                <div className="text-xs text-muted-foreground text-center">
                    +{vehicles.length - 3} araç daha
                </div>
            )}
        </div>
    );
}
