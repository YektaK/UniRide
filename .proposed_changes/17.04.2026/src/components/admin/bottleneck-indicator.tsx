"use client";

/**
 * Bottleneck Indicator Component
 * Darboğaz uyarı bileşeni
 * 
 * Konuşma Geçmişi Madde 14: "Verimsiz noktaları görüp yeni koşullarla planlama"
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertCircle, AlertTriangle, Info, Lightbulb, Clock, Users, Truck } from "lucide-react";
import type { BottleneckData, TimeShiftSuggestion } from "@/types/ie-resource";

interface BottleneckIndicatorProps {
    bottlenecks: BottleneckData[];
    shiftSuggestions: TimeShiftSuggestion[];
    onSuggestionClick?: (suggestion: TimeShiftSuggestion) => void;
    onBottleneckClick?: (bottleneck: BottleneckData) => void;
}

// Şiddet renkleri
const SEVERITY_CONFIG = {
    high: {
        icon: AlertCircle,
        badge: "bg-red-100 text-red-700 border-red-300",
        card: "border-red-300",
        label: "Yüksek",
    },
    medium: {
        icon: AlertTriangle,
        badge: "bg-orange-100 text-orange-700 border-orange-300",
        card: "border-orange-300",
        label: "Orta",
    },
    low: {
        icon: Info,
        badge: "bg-yellow-100 text-yellow-700 border-yellow-300",
        card: "border-yellow-300",
        label: "Düşük",
    },
};

// Tip renkleri
const TYPE_LABELS: Record<string, string> = {
    infeasible: "Kapasite Yetersiz",
    low_efficiency: "Düşük Verimlilik",
    resource_conflict: "Kaynak Çakışması",
};

export function BottleneckIndicator({
    bottlenecks,
    shiftSuggestions,
    onSuggestionClick,
    onBottleneckClick,
}: BottleneckIndicatorProps) {
    // Şiddete göre sırala
    const sortedBottlenecks = [...bottlenecks].sort((a, b) => {
        const severityOrder = { high: 0, medium: 1, low: 2 };
        return severityOrder[a.severity] - severityOrder[b.severity];
    });

    const highCount = bottlenecks.filter((b) => b.severity === "high").length;
    const mediumCount = bottlenecks.filter((b) => b.severity === "medium").length;
    const lowCount = bottlenecks.filter((b) => b.severity === "low").length;

    if (bottlenecks.length === 0) {
        return (
            <Card className="border-green-300">
                <CardContent className="pt-6">
                    <div className="flex items-center gap-3 text-green-600">
                        <div className="h-10 w-10 rounded-full bg-green-100 flex items-center justify-center">
                            <Truck className="h-5 w-5" />
                        </div>
                        <div>
                            <p className="font-medium">Darboğaz Yok</p>
                            <p className="text-sm text-muted-foreground">
                                Mevcut kapasite ile tüm saatler feasible
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-4">
            {/* Özet kartı */}
            <Card>
                <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="h-10 w-10 rounded-full bg-red-100 flex items-center justify-center">
                                <AlertCircle className="h-5 w-5 text-red-600" />
                            </div>
                            <div>
                                <p className="font-medium">
                                    {bottlenecks.length} Darboğaz Tespit Edildi
                                </p>
                                <div className="flex gap-2 mt-1">
                                    {highCount > 0 && (
                                        <Badge variant="destructive">{highCount} Yüksek</Badge>
                                    )}
                                    {mediumCount > 0 && (
                                        <Badge className="bg-orange-100 text-orange-700">
                                            {mediumCount} Orta
                                        </Badge>
                                    )}
                                    {lowCount > 0 && (
                                        <Badge className="bg-yellow-100 text-yellow-700">
                                            {lowCount} Düşük
                                        </Badge>
                                    )}
                                </div>
                            </div>
                        </div>
                        {shiftSuggestions.length > 0 && (
                            <div className="text-right">
                                <p className="text-sm text-muted-foreground">
                                    {shiftSuggestions.length} optimizasyon önerisi
                                </p>
                                <p className="text-sm font-medium text-green-600">
                                    Potansiyel tasarruf
                                </p>
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Darboğaz detayları */}
            <div className="grid gap-3">
                {sortedBottlenecks.slice(0, 5).map((bottleneck, idx) => {
                    const config = SEVERITY_CONFIG[bottleneck.severity];
                    const Icon = config.icon;

                    return (
                        <Card
                            key={idx}
                            className={`cursor-pointer hover:shadow-md transition-shadow ${config.card}`}
                            onClick={() => onBottleneckClick?.(bottleneck)}
                        >
                            <CardContent className="p-4">
                                <div className="flex items-start gap-3">
                                    <div className={`p-2 rounded ${config.badge}`}>
                                        <Icon className="h-4 w-4" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <span className="font-medium">{bottleneck.hour}</span>
                                            <Badge variant="outline" className={config.badge}>
                                                {config.label}
                                            </Badge>
                                            <Badge variant="outline">
                                                {TYPE_LABELS[bottleneck.type] || bottleneck.type}
                                            </Badge>
                                        </div>
                                        <p className="text-sm text-muted-foreground mt-1">
                                            {bottleneck.description}
                                        </p>
                                        <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                                            <span className="flex items-center gap-1">
                                                <Users className="h-3 w-3" />
                                                Sw: {bottleneck.swNeeded}/{bottleneck.swAvailable}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Users className="h-3 w-3" />
                                                So: {bottleneck.soNeeded}/{bottleneck.soAvailable}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Truck className="h-3 w-3" />
                                                Araç: {bottleneck.vehiclesNeeded}/{bottleneck.vehiclesAvailable}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    );
                })}
                {bottlenecks.length > 5 && (
                    <p className="text-center text-sm text-muted-foreground">
                        +{bottlenecks.length - 5} darboğaz daha...
                    </p>
                )}
            </div>

            {/* Zaman kaydırma önerileri */}
            {shiftSuggestions.length > 0 && (
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="flex items-center gap-2 text-base">
                            <Lightbulb className="h-4 w-4 text-yellow-500" />
                            Zaman Kaydırma Önerileri
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-0">
                        <div className="space-y-2">
                            {shiftSuggestions.slice(0, 3).map((suggestion, idx) => (
                                <div
                                    key={idx}
                                    className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors cursor-pointer"
                                    onClick={() => onSuggestionClick?.(suggestion)}
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="flex items-center gap-1 text-sm">
                                            <Clock className="h-4 w-4 text-muted-foreground" />
                                            <span>{suggestion.currentTime}</span>
                                            <span className="text-muted-foreground">→</span>
                                            <span className="font-medium">{suggestion.suggestedTime}</span>
                                        </div>
                                        <span className="text-xs text-muted-foreground">
                                            {suggestion.studentName}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {suggestion.savingsVehicles > 0 && (
                                            <Badge className="bg-green-100 text-green-700">
                                                +{suggestion.savingsVehicles} araç tasarrufu
                                            </Badge>
                                        )}
                                        <span
                                            className={`text-xs ${
                                                suggestion.shiftMinutes > 0
                                                    ? "text-blue-600"
                                                    : "text-orange-600"
                                            }`}
                                        >
                                            {suggestion.shiftMinutes > 0 ? "+" : ""}
                                            {suggestion.shiftMinutes} dk
                                        </span>
                                    </div>
                                </div>
                            ))}
                            {shiftSuggestions.length > 3 && (
                                <Button variant="ghost" className="w-full text-sm">
                                    +{shiftSuggestions.length - 3} öneri daha
                                </Button>
                            )}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}

/**
 * Compact bottleneck badge for inline display
 */
interface BottleneckBadgeProps {
    count: number;
    highPriorityCount?: number;
}

export function BottleneckBadge({ count, highPriorityCount = 0 }: BottleneckBadgeProps) {
    if (count === 0) {
        return (
            <Badge className="bg-green-100 text-green-700">
                <Truck className="h-3 w-3 mr-1" />
                Kapasite Yeterli
            </Badge>
        );
    }

    if (highPriorityCount > 0) {
        return (
            <Badge variant="destructive">
                <AlertCircle className="h-3 w-3 mr-1" />
                {highPriorityCount} Darboğaz
            </Badge>
        );
    }

    return (
        <Badge className="bg-orange-100 text-orange-700">
            <AlertTriangle className="h-3 w-3 mr-1" />
            {count} Uyarı
        </Badge>
    );
}
