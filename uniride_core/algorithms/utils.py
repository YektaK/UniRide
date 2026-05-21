import math

def compute_population_diversity(population: list, n_cities: int, sample_size: int = 0) -> float:
    """
    Measures the average diversity of individuals in the population.
    Evaluates edge-based difference between tours.
    """
    pop_size = len(population)
    if pop_size < 2 or n_cities < 2:
        return 1.0
    if sample_size <= 0:
        sample_size = min(pop_size, int(math.sqrt(pop_size)) + 1)
    sample_size = min(sample_size, pop_size)

    total_dist = 0.0
    pair_count = 0
    for i in range(sample_size):
        for j in range(i + 1, sample_size):
            shared = sum(1 for e in _get_edges(population[i], n_cities) if e in _get_edges(population[j], n_cities))
            dist = 1.0 - (shared / n_cities)
            total_dist += dist
            pair_count += 1
            
    return total_dist / pair_count if pair_count > 0 else 1.0

def _get_edges(tour, n: int) -> set:
    edges = set()
    for i in range(n):
        u = tour[i]
        v = tour[(i + 1) % n]
        edges.add((min(u, v), max(u, v)))
    return edges
