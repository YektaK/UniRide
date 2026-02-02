/**
 * K-means Clustering Service
 * Groups students by geographic proximity for vehicle assignment
 * Based on MATLAB VRP code logic
 */

import type { Coordinates } from "@/lib/coordinates";
import { haversineDistance } from "@/lib/coordinates";

export interface ClusterablePoint {
    id: string;
    coordinates: Coordinates;
    disabilityType: "Sw" | "So";
}

export interface Cluster {
    centroid: Coordinates;
    points: ClusterablePoint[];
    swCount: number;
    soCount: number;
}

/**
 * K-means clustering implementation
 * Groups points into k clusters based on geographic distance
 */
export function kMeansClustering(
    points: ClusterablePoint[],
    k: number,
    maxIterations: number = 100
): Cluster[] {
    if (points.length === 0) return [];
    if (k <= 0) return [];
    if (k >= points.length) {
        // Each point is its own cluster
        return points.map(p => ({
            centroid: p.coordinates,
            points: [p],
            swCount: p.disabilityType === "Sw" ? 1 : 0,
            soCount: p.disabilityType === "So" ? 1 : 0,
        }));
    }

    // Initialize centroids using k-means++ for better initial placement
    const centroids = initializeCentroids(points, k);

    let clusters: Cluster[] = [];
    let prevAssignments: number[] = [];

    for (let iteration = 0; iteration < maxIterations; iteration++) {
        // Assign points to nearest centroid
        const assignments = points.map(point =>
            findNearestCentroid(point.coordinates, centroids)
        );

        // Check for convergence
        if (arraysEqual(assignments, prevAssignments)) {
            break;
        }
        prevAssignments = assignments;

        // Create clusters from assignments
        clusters = centroids.map((centroid, i) => ({
            centroid,
            points: points.filter((_, idx) => assignments[idx] === i),
            swCount: 0,
            soCount: 0,
        }));

        // Update centroids
        clusters.forEach((cluster, i) => {
            if (cluster.points.length > 0) {
                centroids[i] = calculateCentroid(cluster.points);
                cluster.swCount = cluster.points.filter(p => p.disabilityType === "Sw").length;
                cluster.soCount = cluster.points.filter(p => p.disabilityType === "So").length;
            }
        });
    }

    // Final cluster creation
    const finalClusters = centroids.map((centroid, i) => {
        const clusterPoints = points.filter((_, idx) => prevAssignments[idx] === i);
        return {
            centroid,
            points: clusterPoints,
            swCount: clusterPoints.filter(p => p.disabilityType === "Sw").length,
            soCount: clusterPoints.filter(p => p.disabilityType === "So").length,
        };
    });

    // Remove empty clusters
    return finalClusters.filter(c => c.points.length > 0);
}

/**
 * Initialize centroids using k-means++ algorithm
 */
function initializeCentroids(points: ClusterablePoint[], k: number): Coordinates[] {
    const centroids: Coordinates[] = [];

    // Pick first centroid randomly
    const firstIdx = Math.floor(Math.random() * points.length);
    centroids.push({ ...points[firstIdx].coordinates });

    // Pick remaining centroids with probability proportional to distance
    while (centroids.length < k) {
        const distances = points.map(point => {
            const minDist = Math.min(...centroids.map(c =>
                haversineDistance(point.coordinates, c)
            ));
            return minDist * minDist; // Squared distance for probability weighting
        });

        const totalDist = distances.reduce((a, b) => a + b, 0);
        let random = Math.random() * totalDist;

        for (let i = 0; i < points.length; i++) {
            random -= distances[i];
            if (random <= 0) {
                centroids.push({ ...points[i].coordinates });
                break;
            }
        }
    }

    return centroids;
}

/**
 * Find the index of the nearest centroid to a point
 */
function findNearestCentroid(point: Coordinates, centroids: Coordinates[]): number {
    let minDist = Infinity;
    let minIdx = 0;

    centroids.forEach((centroid, i) => {
        const dist = haversineDistance(point, centroid);
        if (dist < minDist) {
            minDist = dist;
            minIdx = i;
        }
    });

    return minIdx;
}

/**
 * Calculate the centroid of a set of points
 */
function calculateCentroid(points: ClusterablePoint[]): Coordinates {
    const sum = points.reduce(
        (acc, p) => ({
            lat: acc.lat + p.coordinates.lat,
            lng: acc.lng + p.coordinates.lng,
        }),
        { lat: 0, lng: 0 }
    );

    return {
        lat: sum.lat / points.length,
        lng: sum.lng / points.length,
    };
}

/**
 * Check if two arrays are equal
 */
function arraysEqual(a: number[], b: number[]): boolean {
    if (a.length !== b.length) return false;
    return a.every((v, i) => v === b[i]);
}

/**
 * Re-cluster if capacity constraints are violated
 * Returns true if valid, false if needs more vehicles
 */
export function validateClusterCapacity(
    cluster: Cluster,
    swCapacity: number,
    soCapacity: number
): boolean {
    return cluster.swCount <= swCapacity && cluster.soCount <= soCapacity;
}

/**
 * Split an over-capacity cluster into two
 */
export function splitCluster(cluster: Cluster): Cluster[] {
    if (cluster.points.length <= 1) {
        return [cluster];
    }

    return kMeansClustering(cluster.points, 2);
}
