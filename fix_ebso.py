import re

with open("optimizer_api/strategies/ebso_strategy.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    "from strategies.sota_common.e2bso import E2BSO, E2BSOConfig",
    "from uniride_core.algorithms.sota_tsp import E2BSO_TSP, E2BSOTSPConfig"
)

text = text.replace(
    "PAOEAConfig",
    "PAOEAConfig"
)

# Fix init
text = re.sub(
    r"def __init__\(self, config: Optional\[E2BSOConfig\] = None\):\s+self\._config = config or E2BSOConfig\(\)",
    "def __init__(self, config: Optional[E2BSOTSPConfig] = None):\n        self._config = config or E2BSOTSPConfig(population_size=10, max_iterations=100)",
    text
)

# Fix solve block
old_block = """        class _ProblemWrapper:
            \"\"\"Thin wrapper matching E²BSO's expected interface.\"\"\"
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

        # ── Run E²BSO ──
        try:
            e2bso = E2BSO(self._config)
            result = e2bso.solve(prob)

            # Convert E²BSO result tour to student order
            best_order = [student_ids[int(idx)] for idx in result.tour]
        except Exception as e:
            logger.error(f"E²BSO optimization failed: {e}")"""

new_block = """        # ── Run E²BSO ──
        try:
            e2bso = E2BSO_TSP(self._config)
            matrix = [[float(int_dm[i][j]) for j in range(n)] for i in range(n)]
            e2bso.set_dist_matrix(matrix)
            dummy_coords = [(0.0, 0.0) for _ in range(n)]
            result = e2bso.solve(dummy_coords)

            # Convert E²BSO result tour to student order
            best_order = [student_ids[idx] for idx in result.tour]
        except Exception as e:
            logger.error(f"E²BSO optimization failed: {e}")"""

text = text.replace(old_block, new_block)

text = text.replace("from strategies.sota_common.e2bso import E2BSO", "from uniride_core.algorithms.sota_tsp import E2BSO_TSP")

with open("optimizer_api/strategies/ebso_strategy.py", "w", encoding="utf-8") as f:
    f.write(text)
