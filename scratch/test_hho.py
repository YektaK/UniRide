from academic_benchmark.engine_core import AlgorithmRegistry as _AlgoReg
from academic_benchmark.core.registry_setup import *

class MockProblem:
    name = 'att48'
    dimension = 48
    coordinates = [(1,2)] * 48
    is_time_matrix = False
    optimal = 0

prob = MockProblem()
executor = _AlgoReg.get_executor('Numba-HHO')
executor(prob, {'max_iterations':10, 'population_size':10}, 42, 0)
