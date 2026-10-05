from typing import List, Dict, Tuple
from uniride_core.algorithms.clustering import Point, Cluster, calculate_centroid, matrix_travel_time, validate_cluster_capacity
from uniride_core.algorithms.clustering_strategies.base import BaseClusteringStrategy

def get_duration(p1: Point, p2: Point, time_matrix: Dict) -> float:
    """Directed matrix time; raises ``MissingTravelTimeError`` (no haversine stand-in)."""
    return matrix_travel_time(p1, p2, time_matrix)

class ClarkeWrightClusteringStrategy(BaseClusteringStrategy):
    """Directed Clarke-Wright savings adapted for clustering.

    Routes are closed tours ``D -> s1 -> ... -> sk -> D`` costed on the
    directed ``time_matrix`` (``c(a, b) != c(b, a)`` in general). Joining the
    tail ``i`` of one route to the head ``j`` of another removes the arcs
    ``i -> D`` and ``D -> j`` and adds ``i -> j``::

        S(i -> j) = c(i, D) + c(D, j) - c(i, j)

    The two orientations of a pair differ (``S(i -> j) != S(j -> i)``), so every
    ordered pair is a separate candidate: the better orientation of a pair is
    tried first and the other only if the first no longer applies. On a
    symmetric matrix both orientations equal the classic
    ``c(D, i) + c(D, j) - c(i, j)``. Savings are processed in descending
    order; a merge needs ``i`` to be the last stop of one route and ``j`` the
    first stop of another, and respects the Sw/So capacities.
    """

    def cluster_students(self, students: List[Point], num_vehicles: int, **kwargs) -> List[Cluster]:
        if not students or num_vehicles <= 0: return []

        time_matrix = kwargs.get("time_matrix", {})
        depot = kwargs.get("depot", {"id": "D.Kampus", "lat": 41.001, "lng": 29.177})

        # We need a dummy depot point for distance calc
        depot_point = Point(
            id=depot["id"], lat=depot["lat"], lng=depot["lng"], disability_type="So",
            location_code=depot["id"],
        )

        # Start with everyone in their own route
        routes = [[s] for s in students]

        # Directed savings for every ordered pair (tail i, head j)
        savings = []
        for i, s1 in enumerate(students):
            to_depot = get_duration(s1, depot_point, time_matrix)
            for j, s2 in enumerate(students):
                if i == j:
                    continue
                from_depot = get_duration(depot_point, s2, time_matrix)
                arc = get_duration(s1, s2, time_matrix)
                savings.append((to_depot + from_depot - arc, i, j, s1, s2))

        # Descending saving; ties keep input order (deterministic)
        savings.sort(key=lambda x: (-x[0], x[1], x[2]))

        # Merge routes
        for _saving, _i, _j, tail, head in savings:
            if len(routes) <= num_vehicles:
                break # Reached desired number of clusters

            route1_idx = next((k for k, r in enumerate(routes) if r[-1].id == tail.id), -1)
            route2_idx = next((k for k, r in enumerate(routes) if r[0].id == head.id), -1)

            if route1_idx != -1 and route2_idx != -1 and route1_idx != route2_idx:
                r1 = routes[route1_idx]
                r2 = routes[route2_idx]

                combined = r1 + r2
                sw_count = sum(1 for p in combined if p.disability_type == "Sw")
                so_count = sum(1 for p in combined if p.disability_type == "So")

                if sw_count <= self.sw_capacity and so_count <= self.so_capacity:
                    # Valid merge. The CW max-tour-time is not checked here: the
                    # cluster is handed to the local TSP solver afterwards.
                    routes.pop(max(route1_idx, route2_idx))
                    routes.pop(min(route1_idx, route2_idx))
                    routes.append(combined)

        # Convert back to Clusters
        clusters = []
        for r in routes:
            clusters.append(Cluster(
                centroid=calculate_centroid(r),
                points=r,
                sw_count=sum(1 for p in r if p.disability_type == "Sw"),
                so_count=sum(1 for p in r if p.disability_type == "So")
            ))
            
        return clusters
