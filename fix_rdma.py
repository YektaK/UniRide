import re

with open("optimizer_api/strategies/rdma_strategy.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    "from strategies.sota_common.r2dma import R2DMA, R2DMAConfig",
    "from uniride_core.algorithms.sota_tsp import R2DMA_TSP, R2DMATSPConfig"
)

text = text.replace("R2DMAConfig", "R2DMATSPConfig")
text = text.replace("self._config = config or R2DMATSPConfig()", "self._config = config or R2DMATSPConfig(population_size=10, max_iterations=100)")


old_block = """        class _ProblemWrapper:
            \"\"\"Thin wrapper matching R²DMA's expected interface.\"\"\"
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

        # ── Run R²DMA ──
        try:
            r2dma = R2DMA(self._config)
            result = r2dma.solve(prob)

            # Convert result tour to student order
            best_order = [student_ids[int(idx)] for idx in result.tour]
        except Exception as e:
            logger.error(f"R²DMA optimization failed: {e}")"""

new_block = """        # ── Run R²DMA ──
        try:
            r2dma = R2DMA_TSP(self._config)
            matrix = [[float(int_dm[i][j]) for j in range(n)] for i in range(n)]
            r2dma.set_dist_matrix(matrix)
            dummy_coords = [(0.0, 0.0) for _ in range(n)]
            result = r2dma.solve(dummy_coords)

            # Convert result tour to student order
            best_order = [student_ids[idx] for idx in result.tour]
        except Exception as e:
            logger.error(f"R²DMA optimization failed: {e}")"""

text = text.replace(old_block, new_block)
text = text.replace("from strategies.sota_common.r2dma import R2DMA", "from uniride_core.algorithms.sota_tsp import R2DMA_TSP")

with open("optimizer_api/strategies/rdma_strategy.py", "w", encoding="utf-8") as f:
    f.write(text)
