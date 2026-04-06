"""
Clustering Strategies Module
Time-matrix aware clustering algorithms for CVRP

Available Strategies:
- kmeans: Classic K-Means (coordinate-based, time-matrix unaware) - DEFAULT
- kmedoids: K-Medoids (time-matrix aware, real center points)
- clarke_wright: Clarke-Wright Savings (time-matrix aware, route-oriented)
- agglomerative: Agglomerative Hierarchical (time-matrix aware)
- hybrid: Hybrid approach (CW init + K-Medoids refinement)

Recommended:
- For small problems (N≤30): kmedoids or clarke_wright
- For medium problems (30<N≤100): clarke_wright or hybrid
- For large problems (N>100): kmeans (speed) or hybrid (quality)
"""

import math
import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Import from clustering module
from utils.clustering import Point, Cluster, haversine_distance


class ClusteringStrategy(ABC):
    """Abstract base class for clustering strategies"""
    
    def __init__(self, sw_capacity: int = 4, so_capacity: int = 5):
        self.sw_capacity = sw_capacity
        self.so_capacity = so_capacity
    
    @abstractmethod
    def cluster_students(self, students: List[Point], num_vehicles: int, **kwargs) -> List[Cluster]:
        """Cluster students into groups"""
        pass
    
    def _get_time_matrix(self, kwargs: dict) -> Optional[Dict]:
        """Extract time matrix from kwargs"""
        return kwargs.get("time_matrix")
    
    def _get_depot(self, kwargs: dict) -> str:
        """Extract depot from kwargs"""
        depot = kwargs.get("depot", {})
        return depot.get("id", "D.Kampus") if isinstance(depot, dict) else str(depot)


class KMeansStrategy(ClusteringStrategy):
    """
    Classic K-Means clustering (coordinate-based).
    
    Pros:
    - Fast O(n·k·i)
    - Simple implementation
    
    Cons:
    - Time-matrix UNAWARE (uses haversine distance)
    - May create suboptimal clusters for road networks
    """
    
    def cluster_students(self, students: List[Point], num_vehicles: int, **kwargs) -> List[Cluster]:
        from utils.clustering import kmeans_clustering
        return kmeans_clustering(students, num_vehicles)


class KMedoidsStrategy(ClusteringStrategy):
    """
    K-Medoids clustering (time-matrix aware).
    
    Uses actual time matrix for distances and selects real points as centers.
    
    Pros:
    - Time-matrix AWARE
    - Robust to outliers
    - Real points as centers (not virtual centroids)
    
    Cons:
    - Slower than K-Means O(n²·k·i)
    - Requires time matrix
    
    Reference:
    Kaufman, L., & Rousseeuw, P. J. (1987). Clustering by means of medoids.
    """
    
    def cluster_students(self, students: List[Point], num_vehicles: int, **kwargs) -> List[Cluster]:
        time_matrix = self._get_time_matrix(kwargs)
        
        if time_matrix is None:
            # Fallback to K-Means if no time matrix
            from utils.clustering import kmeans_clustering
            return kmeans_clustering(students, num_vehicles)
        
        # Build location code to index mapping
        location_codes = [s.location_code for s in students]
        n = len(students)
        k = num_vehicles
        
        if n <= k:
            return [Cluster(
                centroid=(s.lat, s.lng),
                points=[s],
                sw_count=1 if s.disability_type == "Sw" else 0,
                so_count=1 if s.disability_type == "So" else 0
            ) for s in students]
        
        # Initialize medoids using K-Medoids++ approach
        medoid_indices = self._initialize_medoids(time_matrix, location_codes, k)
        
        # Iterative assignment and update
        prev_assignments = [-1] * n
        max_iterations = 100
        
        for _ in range(max_iterations):
            # Assign each point to nearest medoid
            assignments = []
            for i, student in enumerate(students):
                min_dist = float('inf')
                min_cluster = 0
                for cluster_idx, medoid_idx in enumerate(medoid_indices):
                    medoid_loc = students[medoid_idx].location_code
                    student_loc = student.location_code
                    dist = time_matrix.get(medoid_loc, {}).get(student_loc, 15.0)
                    if dist < min_dist:
                        min_dist = dist
                        min_cluster = cluster_idx
                assignments.append(min_cluster)
            
            # Check convergence
            if assignments == prev_assignments:
                break
            prev_assignments = assignments
            
            # Update medoids (find best center in each cluster)
            for cluster_idx in range(k):
                cluster_points = [i for i in range(n) if assignments[i] == cluster_idx]
                if not cluster_points:
                    continue
                
                # Find point with minimum total distance to others
                best_medoid = cluster_points[0]
                best_total_dist = float('inf')
                
                for candidate in cluster_points:
                    total_dist = 0
                    cand_loc = students[candidate].location_code
                    for other in cluster_points:
                        other_loc = students[other].location_code
                        total_dist += time_matrix.get(cand_loc, {}).get(other_loc, 15.0)
                    
                    if total_dist < best_total_dist:
                        best_total_dist = total_dist
                        best_medoid = candidate
                
                medoid_indices[cluster_idx] = best_medoid
        
        # Build clusters
        clusters = []
        for cluster_idx in range(k):
            cluster_points = [students[i] for i in range(n) if prev_assignments[i] == cluster_idx]
            if cluster_points:
                medoid_idx = medoid_indices[cluster_idx]
                medoid = students[medoid_idx]
                sw_count = sum(1 for p in cluster_points if p.disability_type == "Sw")
                so_count = sum(1 for p in cluster_points if p.disability_type == "So")
                clusters.append(Cluster(
                    centroid=(medoid.lat, medoid.lng),
                    points=cluster_points,
                    sw_count=sw_count,
                    so_count=so_count
                ))
        
        return clusters
    
    def _initialize_medoids(self, time_matrix: Dict, location_codes: List[str], k: int) -> List[int]:
        """Initialize medoids using K-Medoids++ approach"""
        n = len(location_codes)
        medoids = []
        
        # First medoid: random
        medoids.append(random.randint(0, n - 1))
        
        while len(medoids) < k:
            # Calculate distances to nearest medoid
            distances = []
            for i in range(n):
                min_dist = float('inf')
                for m in medoids:
                    loc_i = location_codes[i]
                    loc_m = location_codes[m]
                    dist = time_matrix.get(loc_i, {}).get(loc_m, 15.0)
                    min_dist = min(min_dist, dist)
                distances.append(min_dist ** 2)
            
            # Select with probability proportional to distance squared
            total = sum(distances)
            if total == 0:
                medoids.append(random.randint(0, n - 1))
            else:
                r = random.random() * total
                cumulative = 0
                for i, d in enumerate(distances):
                    cumulative += d
                    if cumulative >= r and i not in medoids:
                        medoids.append(i)
                        break
                else:
                    # Fallback
                    for i in range(n):
                        if i not in medoids:
                            medoids.append(i)
                            break
        
        return medoids


class ClarkeWrightStrategy(ClusteringStrategy):
    """
    Clarke-Wright Savings Algorithm for CVRP.
    
    Route-oriented clustering that directly uses time matrix.
    Builds routes by merging based on savings.
    
    Pros:
    - Time-matrix AWARE
    - Route-oriented (considers actual routing)
    - Fast O(n²)
    - Good initial solution
    
    Cons:
    - Greedy (may miss optimal)
    - Capacity handling requires care
    
    Reference:
    Clarke, G., & Wright, J. W. (1964). Scheduling of vehicles from a central depot.
    Operations Research, 12(4), 568-581.
    """
    
    def cluster_students(self, students: List[Point], num_vehicles: int, **kwargs) -> List[Cluster]:
        time_matrix = self._get_time_matrix(kwargs)
        depot_id = self._get_depot(kwargs)
        
        if time_matrix is None:
            from utils.clustering import kmeans_clustering
            return kmeans_clustering(students, num_vehicles)
        
        n = len(students)
        
        # Calculate savings: S(i,j) = d(depot,i) + d(depot,j) - d(i,j)
        savings = []
        for i in range(n):
            for j in range(i + 1, n):
                loc_i = students[i].location_code
                loc_j = students[j].location_code
                
                d_di = time_matrix.get(depot_id, {}).get(loc_i, 15.0)
                d_dj = time_matrix.get(depot_id, {}).get(loc_j, 15.0)
                d_ij = time_matrix.get(loc_i, {}).get(loc_j, 15.0)
                
                saving = d_di + d_dj - d_ij
                savings.append((saving, i, j))
        
        # Sort by savings (descending)
        savings.sort(reverse=True, key=lambda x: x[0])
        
        # Initialize: each student in own route
        routes = [[i] for i in range(n)]
        route_of = {i: i for i in range(n)}
        
        # Merge routes based on savings
        for saving, i, j in savings:
            if route_of[i] == route_of[j]:
                continue  # Already in same route
            
            route_i = route_of[i]
            route_j = route_of[j]
            
            # Check if merge is possible (capacity)
            route_i_students = [students[idx] for idx in routes[route_i]]
            route_j_students = [students[idx] for idx in routes[route_j]]
            
            sw_total = sum(1 for s in route_i_students + route_j_students if s.disability_type == "Sw")
            so_total = sum(1 for s in route_i_students + route_j_students if s.disability_type == "So")
            
            if sw_total > self.sw_capacity or so_total > self.so_capacity:
                continue  # Capacity violation
            
            # Check if i and j are at endpoints of their routes
            if routes[route_i][0] != i and routes[route_i][-1] != i:
                continue
            if routes[route_j][0] != j and routes[route_j][-1] != j:
                continue
            
            # Merge routes
            if routes[route_i][-1] == i and routes[route_j][0] == j:
                # i at end, j at start: routes[route_i] + routes[route_j]
                new_route = routes[route_i] + routes[route_j]
            elif routes[route_i][-1] == i and routes[route_j][-1] == j:
                # i at end, j at end: routes[route_i] + reversed(routes[route_j])
                new_route = routes[route_i] + routes[route_j][::-1]
            elif routes[route_i][0] == i and routes[route_j][0] == j:
                # i at start, j at start: reversed(routes[route_i]) + routes[route_j]
                new_route = routes[route_i][::-1] + routes[route_j]
            elif routes[route_i][0] == i and routes[route_j][-1] == j:
                # i at start, j at end: routes[route_j] + routes[route_i]
                new_route = routes[route_j] + routes[route_i]
            else:
                continue
            
            # Update routes
            routes[route_i] = new_route
            routes[route_j] = []
            for idx in new_route:
                route_of[idx] = route_i
        
        # Build clusters from non-empty routes
        clusters = []
        for route in routes:
            if not route:
                continue
            
            route_students = [students[i] for i in route]
            sw_count = sum(1 for s in route_students if s.disability_type == "Sw")
            so_count = sum(1 for s in route_students if s.disability_type == "So")
            
            # Calculate centroid
            avg_lat = sum(s.lat for s in route_students) / len(route_students)
            avg_lng = sum(s.lng for s in route_students) / len(route_students)
            
            clusters.append(Cluster(
                centroid=(avg_lat, avg_lng),
                points=route_students,
                sw_count=sw_count,
                so_count=so_count
            ))
        
        # If we need more clusters (constraint), split largest
        while len(clusters) < num_vehicles:
            # Find largest cluster
            largest = max(clusters, key=lambda c: len(c.points))
            if len(largest.points) <= 1:
                break
            
            # Split using K-Medoids
            clusters.remove(largest)
            kmedoids = KMedoidsStrategy(self.sw_capacity, self.so_capacity)
            sub_clusters = kmedoids.cluster_students(largest.points, 2, **kwargs)
            clusters.extend(sub_clusters)
        
        return clusters


class AgglomerativeStrategy(ClusteringStrategy):
    """
    Agglomerative Hierarchical Clustering (time-matrix aware).
    
    Bottom-up clustering that merges closest clusters iteratively.
    
    Pros:
    - Time-matrix AWARE
    - Produces dendrogram (can cut at any level)
    - No need to specify k exactly
    
    Cons:
    - Slower O(n³) or O(n² log n)
    - May create unbalanced clusters
    
    Reference:
    Müllner, D. (2011). Modern hierarchical, agglomerative clustering algorithms.
    """
    
    def cluster_students(self, students: List[Point], num_vehicles: int, **kwargs) -> List[Cluster]:
        time_matrix = self._get_time_matrix(kwargs)
        
        if time_matrix is None:
            from utils.clustering import kmeans_clustering
            return kmeans_clustering(students, num_vehicles)
        
        n = len(students)
        
        # Initialize: each point is its own cluster
        clusters = [{i} for i in range(n)]
        
        # Calculate initial distance matrix
        def cluster_distance(c1: set, c2: set) -> float:
            # Average linkage
            total = 0
            count = 0
            for i in c1:
                for j in c2:
                    loc_i = students[i].location_code
                    loc_j = students[j].location_code
                    total += time_matrix.get(loc_i, {}).get(loc_j, 15.0)
                    count += 1
            return total / count if count > 0 else float('inf')
        
        # Merge until we have num_vehicles clusters
        while len(clusters) > num_vehicles:
            # Find closest pair
            min_dist = float('inf')
            merge_i, merge_j = 0, 1
            
            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    dist = cluster_distance(clusters[i], clusters[j])
                    if dist < min_dist:
                        min_dist = dist
                        merge_i, merge_j = i, j
            
            # Check capacity constraint before merging
            merged = clusters[merge_i] | clusters[merge_j]
            merged_students = [students[idx] for idx in merged]
            sw_total = sum(1 for s in merged_students if s.disability_type == "Sw")
            so_total = sum(1 for s in merged_students if s.disability_type == "So")
            
            if sw_total > self.sw_capacity or so_total > self.so_capacity:
                # Cannot merge, mark for removal
                # Instead of merging, we keep the smaller cluster separate
                break
            
            # Merge
            clusters[merge_i] = merged
            clusters.pop(merge_j)
        
        # Build final clusters
        result = []
        for cluster_set in clusters:
            if not cluster_set:
                continue
            
            cluster_students = [students[i] for i in cluster_set]
            sw_count = sum(1 for s in cluster_students if s.disability_type == "Sw")
            so_count = sum(1 for s in cluster_students if s.disability_type == "So")
            
            avg_lat = sum(s.lat for s in cluster_students) / len(cluster_students)
            avg_lng = sum(s.lng for s in cluster_students) / len(cluster_students)
            
            result.append(Cluster(
                centroid=(avg_lat, avg_lng),
                points=cluster_students,
                sw_count=sw_count,
                so_count=so_count
            ))
        
        return result


class HybridClusteringStrategy(ClusteringStrategy):
    """
    Hybrid Clustering: Clarke-Wright initialization + K-Medoids refinement.
    
    Combines the route-oriented nature of CW with the robustness of K-Medoids.
    
    Process:
    1. Use Clarke-Wright to get initial route-oriented clusters
    2. Refine with K-Medoids iterations
    
    Pros:
    - Time-matrix AWARE
    - Combines strengths of both methods
    - Good balance of quality and speed
    """
    
    def cluster_students(self, students: List[Point], num_vehicles: int, **kwargs) -> List[Cluster]:
        # Step 1: Initialize with Clarke-Wright
        cw = ClarkeWrightStrategy(self.sw_capacity, self.so_capacity)
        initial_clusters = cw.cluster_students(students, num_vehicles, **kwargs)
        
        # Step 2: Refine with K-Medoids (limited iterations)
        time_matrix = self._get_time_matrix(kwargs)
        if time_matrix is None:
            return initial_clusters
        
        # Re-assign points based on time-matrix distances to cluster centers
        for _ in range(5):  # Limited refinement iterations
            # Calculate cluster centers (medoids)
            medoids = []
            for cluster in initial_clusters:
                if not cluster.points:
                    continue
                # Find medoid
                best_medoid = cluster.points[0]
                best_total = float('inf')
                for candidate in cluster.points:
                    total = 0
                    for other in cluster.points:
                        total += time_matrix.get(candidate.location_code, {}).get(
                            other.location_code, 15.0
                        )
                    if total < best_total:
                        best_total = total
                        best_medoid = candidate
                medoids.append(best_medoid)
            
            # Re-assign all points to nearest medoid
            new_clusters = {i: [] for i in range(len(medoids))}
            for student in students:
                min_dist = float('inf')
                min_cluster = 0
                for i, medoid in enumerate(medoids):
                    dist = time_matrix.get(student.location_code, {}).get(
                        medoid.location_code, 15.0
                    )
                    if dist < min_dist:
                        min_dist = dist
                        min_cluster = i
                new_clusters[min_cluster].append(student)
            
            # Update clusters
            initial_clusters = []
            for i, points in new_clusters.items():
                if not points:
                    continue
                sw_count = sum(1 for p in points if p.disability_type == "Sw")
                so_count = sum(1 for p in points if p.disability_type == "So")
                avg_lat = sum(p.lat for p in points) / len(points)
                avg_lng = sum(p.lng for p in points) / len(points)
                initial_clusters.append(Cluster(
                    centroid=(avg_lat, avg_lng),
                    points=points,
                    sw_count=sw_count,
                    so_count=so_count
                ))
        
        return initial_clusters


# Strategy Registry
CLUSTERING_STRATEGIES = {
    "kmeans": KMeansStrategy,
    "kmedoids": KMedoidsStrategy,
    "k-medoids": KMedoidsStrategy,  # Alias
    "clarke_wright": ClarkeWrightStrategy,
    "cw": ClarkeWrightStrategy,  # Alias
    "savings": ClarkeWrightStrategy,  # Alias
    "agglomerative": AgglomerativeStrategy,
    "hierarchical": AgglomerativeStrategy,  # Alias
    "hybrid": HybridClusteringStrategy,
}


def get_clustering_strategy(name: str, sw_capacity: int = 4, so_capacity: int = 5) -> ClusteringStrategy:
    """
    Get clustering strategy by name.
    
    Args:
        name: Strategy name (kmeans, kmedoids, clarke_wright, agglomerative, hybrid)
        sw_capacity: Wheelchair capacity per vehicle
        so_capacity: Other disability capacity per vehicle
    
    Returns:
        ClusteringStrategy instance
    """
    name_lower = name.lower()
    strategy_class = CLUSTERING_STRATEGIES.get(name_lower)
    
    if strategy_class is None:
        # Default to K-Means if unknown
        print(f"Warning: Unknown clustering strategy '{name}', using K-Means")
        strategy_class = KMeansStrategy
    
    return strategy_class(sw_capacity, so_capacity)


def get_available_strategies() -> List[str]:
    """Get list of available clustering strategies"""
    return list(set(CLUSTERING_STRATEGIES.keys()))


# Convenience functions
def cluster_with_kmedoids(students: List[Point], num_vehicles: int, 
                          time_matrix: Dict, **kwargs) -> List[Cluster]:
    """Convenience function for K-Medoids clustering"""
    strategy = KMedoidsStrategy(
        sw_capacity=kwargs.get("sw_capacity", 4),
        so_capacity=kwargs.get("so_capacity", 5)
    )
    return strategy.cluster_students(students, num_vehicles, time_matrix=time_matrix, **kwargs)


def cluster_with_clarke_wright(students: List[Point], num_vehicles: int,
                                time_matrix: Dict, depot_id: str, **kwargs) -> List[Cluster]:
    """Convenience function for Clarke-Wright clustering"""
    strategy = ClarkeWrightStrategy(
        sw_capacity=kwargs.get("sw_capacity", 4),
        so_capacity=kwargs.get("so_capacity", 5)
    )
    return strategy.cluster_students(students, num_vehicles, 
                                     time_matrix=time_matrix, depot={"id": depot_id}, **kwargs)


if __name__ == "__main__":
    # Quick test
    print("Clustering Strategies Available:")
    for name in get_available_strategies():
        print(f"  - {name}")
