/**
 * IE Resource Engine Type Definitions
 * Endüstri Mühendisliği Kaynak Yönetimi için tip tanımları
 */

export interface HourlyDemandData {
    hour: string;  // "08:00"
    pickupSw: number;
    pickupSo: number;
    dropoffSw: number;
    dropoffSo: number;
    totalPickup: number;
    totalDropoff: number;
    totalSw: number;
    totalSo: number;
    isInfeasible?: boolean;
}

export interface BottleneckData {
    hour: string;
    type: "infeasible" | "low_efficiency" | "resource_conflict";
    severity: "high" | "medium" | "low";
    description: string;
    swNeeded: number;
    soNeeded: number;
    swAvailable: number;
    soAvailable: number;
    vehiclesNeeded: number;
    vehiclesAvailable: number;
}

export interface TimeShiftSuggestion {
    studentId: string;
    studentName: string;
    currentTime: string;
    suggestedTime: string;
    shiftMinutes: number;
    reason: string;
    savingsVehicles: number;
}

export interface StandardVehicleNeeds {
    totalStudents: number;
    swCount: number;
    soCount: number;
    standardVehiclesNeeded: number;
    byCapacity: {
        bySw: number;
        bySo: number;
        maxNeeded: number;
    };
    utilizationPercent: number;
    utilizationBreakdown: {
        sw: number;
        so: number;
    };
}

export interface ResourceBlock {
    vehicleId: string;
    startTime: number;  // minutes from midnight
    endTime: number;
    direction: "pickup" | "dropoff";
    students: string[];
    swCount: number;
    soCount: number;
}

export interface IEResponseData {
    summary: {
        totalStudents: number;
        availableVehicles: number;
        standardVehiclesNeeded: number;
        bottleneckCount: number;
        shiftSuggestionsCount: number;
    };
    standardNeeds: StandardVehicleNeeds;
    hourlyDemand: Record<string, HourlyDemandData>;
    bottlenecks: BottleneckData[];
    shiftSuggestions: TimeShiftSuggestion[];
}

export interface VehicleConfig {
    vehicleId: string;
    name?: string;
    swCapacity: number;
    soCapacity: number;
    cooldownMinutes?: number;
}

export interface IEChartData {
    labels: string[];
    pickupSw: number[];
    pickupSo: number[];
    dropoffSw: number[];
    dropoffSo: number[];
    totalVehicles: number[];
    capacity: number[];
}
