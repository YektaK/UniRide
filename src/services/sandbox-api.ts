/**
 * Sandbox API Service
 * Handles sandbox mode API calls from frontend
 */
import { getAuthToken } from "@/lib/admin-api";

export interface VehicleConfig {
    id?: string;
    name: string;
    swCapacity: number;
    soCapacity: number;
    cooldownMinutes?: number;
}

export interface ReoptimizeRequest {
    students: any[];
    vehicles: VehicleConfig[];
    maxTourTime?: number;
    allowTimeShift?: boolean;
    strategy?: string;
    clusteringAlgorithm?: string;
}

export interface SandboxScenario {
    id: string;
    name: string;
    vehicles: VehicleConfig[];
    studentIds: string[];
    timeWindowMinutes: number;
    createdAt: string;
}

export async function reoptimize(request: ReoptimizeRequest): Promise<any> {
    const token = await getAuthToken();
    if (!token) throw new Error("Not authenticated");

    const response = await fetch('/api/sandbox', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(request),
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || 'Re-optimization failed');
    }

    return data.data;
}

export async function saveSandboxScenario(scenario: Omit<SandboxScenario, 'id' | 'createdAt'>): Promise<SandboxScenario> {
    const token = await getAuthToken();
    if (!token) throw new Error("Not authenticated");

    const response = await fetch('/api/sandbox?action=save', {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(scenario),
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || 'Failed to save scenario');
    }

    return data.data;
}

export async function getSandboxScenarios(): Promise<SandboxScenario[]> {
    const token = await getAuthToken();
    if (!token) throw new Error("Not authenticated");

    const response = await fetch('/api/sandbox?action=list', {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
        },
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || 'Failed to fetch scenarios');
    }

    return data.data;
}

export async function deleteSandboxScenario(id: string): Promise<void> {
    const token = await getAuthToken();
    if (!token) throw new Error("Not authenticated");

    const response = await fetch(`/api/sandbox?action=delete&id=${id}`, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${token}`,
        },
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || 'Failed to delete scenario');
    }
}
