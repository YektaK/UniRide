import re

with open("optimizer_api/strategies/aoea_strategy.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    "from strategies.sota_common.paoea import PAOEA, PAOEAConfig",
    "from uniride_core.algorithms.sota_tsp import PAOEA_TSP, PAOEAConfig"
)

text = re.sub(
    r"def __init__\(self, config: Optional\[PAOEAConfig\] = None\):\s+self\._config = config or PAOEAConfig\(\)",
    "def __init__(self, config: Optional[PAOEAConfig] = None):\n        self._config = config or PAOEAConfig(population_size=10, max_iterations=100)",
    text
)

old_block = """        class _ProblemWrapper:
            \"\"\"Thin wrapper matching PAOEA's expected interface.\"\"\"
            def __init__(self):
                self.node_names = [str(i) for i in range(n)]
                self.dimension = n
                self.dist_matrix = int_dm
                self.optimal = None

            def cost_fn(self, tour):
                total = 0
                for i in range(len(tour) - 1):
                    total += int_dm[int(tour[i])][int(tour[i + 1])]
                if len(tour) >= 2:
                    total += int_dm[int(tour[-1])][int(tour[0])]
                return float(total)

        prob = _ProblemWrapper()

        # ── Run P-AOEA ──
        try:
            paoea = PAOEA(self._config)
            result = paoea.solve(prob)

            # Convert PAOEA result tour to student order
            best_order = [student_ids[int(idx)] for idx in result.tour]
        except Exception as e:
            logger.error(f"P-AOEA optimization failed: {e}")"""

new_block = """        # ── Run P-AOEA ──
        try:
            paoea = PAOEA_TSP(self._config)
            matrix = [[float(int_dm[i][j]) for j in range(n)] for i in range(n)]
            paoea.set_dist_matrix(matrix)
            dummy_coords = [(0.0, 0.0) for _ in range(n)]
            result = paoea.solve(dummy_coords)

            # Convert PAOEA result tour to student order
            best_order = [student_ids[idx] for idx in result.tour]
        except Exception as e:
            logger.error(f"P-AOEA optimization failed: {e}")"""

text = text.replace(old_block, new_block)
text = text.replace("from strategies.sota_common.paoea import PAOEA", "from uniride_core.algorithms.sota_tsp import PAOEA_TSP")

with open("optimizer_api/strategies/aoea_strategy.py", "w", encoding="utf-8") as f:
    f.write(text)
