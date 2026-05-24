from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Callable, Optional
import time

from uniride_core.models import ProblemInstance, TSPResult

@dataclass
class RunResult:
    """Standardized output from any algorithm strategy."""
    problem: str
    algorithm: str
    run: int
    seed: int
    dimension: int
    optimal: Optional[float]
    tour_cost: float
    gap_pct: Optional[float]
    elapsed_sec: float
    iterations: int = 0
    evaluations: int = 0
    convergence_profile: List[float] = field(default_factory=list)
    tour: Optional[List[int]] = None
    error: Optional[str] = None



@dataclass
class BenchmarkTask:
    """A single execution task defining problem, algorithm, and specific parameters."""
    problem_name: str
    algorithm: str
    run_idx: int
    seed: int
    params: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class BenchmarkConfig:
    """A collection of tasks that can be serialized to/from JSON."""
    name: str
    created_at: str
    tasks: List[BenchmarkTask]
    
    def to_json(self) -> str:
        import json
        data = {
            "name": self.name,
            "created_at": self.created_at,
            "tasks": [t.__dict__ for t in self.tasks]
        }
        return json.dumps(data, indent=4)
        
    @classmethod
    def from_json(cls, json_str: str) -> 'BenchmarkConfig':
        import json
        data = json.loads(json_str)
        tasks = [BenchmarkTask(**t) for t in data["tasks"]]
        return cls(name=data.get("name", "Unnamed"), created_at=data.get("created_at", ""), tasks=tasks)

class AlgorithmRegistry:
    """Registry to route algorithm strings to their respective implementations."""
    _registry: Dict[str, Callable] = {}
    _param_spaces: Dict[str, Callable] = {}
    _warmup_fns: Dict[str, Callable] = {}

    @classmethod
    def register(cls, name: str):
        def wrapper(func: Callable):
            cls._registry[name] = func
            return func
        return wrapper

    @classmethod
    def register_param_space(cls, name: str):
        def wrapper(func: Callable):
            cls._param_spaces[name] = func
            return func
        return wrapper

    @classmethod
    def get_param_space(cls, name: str) -> Optional[Dict[str, List[Any]]]:
        if name not in cls._param_spaces:
            return None
        return cls._param_spaces[name]()

    @classmethod
    def register_warmup(cls, name: str):
        def wrapper(func: Callable):
            cls._warmup_fns[name] = func
            return func
        return wrapper

    @classmethod
    def warmup(cls, name: str, probe_problem) -> None:
        if name in cls._warmup_fns:
            cls._warmup_fns[name](probe_problem)

    @classmethod
    def get_executor(cls, name: str) -> Callable:
        if name not in cls._registry:
            raise ValueError(f"Algorithm '{name}' not found in registry.")
        return cls._registry[name]

    @classmethod
    def list_algorithms(cls) -> List[str]:
        return list(cls._registry.keys())

# --- Config Schema Validation ---

class ConfigSchema:
    """Validates benchmark tuning config dicts against expected schema."""
    SUPPORTED_VERSIONS = (1,)
    REQUIRED_SECTIONS = ("problems", "algorithms", "settings")
    VALID_PROBLEM_MODES = ("index", "name")

    @classmethod
    def validate(cls, config: Dict[str, Any], problems: Optional[List[str]] = None,
                 algorithms: Optional[List[str]] = None) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        if not isinstance(config, dict):
            return False, ["Config must be a dict"]
        version = config.get("version")
        if version not in cls.SUPPORTED_VERSIONS:
            errors.append(f"Unsupported config version: {version} (supported: {cls.SUPPORTED_VERSIONS})")
        for section in cls.REQUIRED_SECTIONS:
            if section not in config:
                errors.append(f"Missing required section: '{section}'")
        if errors:
            return False, errors
        prob = config["problems"]
        if not isinstance(prob, dict):
            errors.append("'problems' must be a dict")
        else:
            mode = prob.get("mode")
            if mode not in cls.VALID_PROBLEM_MODES:
                errors.append(f"Invalid problems.mode: '{mode}' (expected: {cls.VALID_PROBLEM_MODES})")
            sel = prob.get("selection")
            if not isinstance(sel, list) or not sel:
                errors.append("'problems.selection' must be a non-empty list")
            elif mode == "index" and problems:
                for idx in sel:
                    if not isinstance(idx, int) or idx < 1 or idx > len(problems):
                        errors.append(f"Problem index {idx} out of range [1..{len(problems)}]")
                        break
            elif mode == "name" and problems:
                for name in sel:
                    if name not in problems:
                        errors.append(f"Unknown problem name: '{name}'")
                        break
        algo = config["algorithms"]
        if not isinstance(algo, dict):
            errors.append("'algorithms' must be a dict")
        else:
            sel = algo.get("selection")
            if not isinstance(sel, list) or not sel:
                errors.append("'algorithms.selection' must be a non-empty list")
            elif isinstance(sel[0], int) and algorithms:
                for idx in sel:
                    if not isinstance(idx, int) or idx < 1 or idx > len(algorithms):
                        errors.append(f"Algorithm index {idx} out of range [1..{len(algorithms)}]")
                        break
            elif isinstance(sel[0], str) and algorithms:
                for name in sel:
                    if name not in algorithms:
                        errors.append(f"Unknown algorithm: '{name}'")
                        break
        settings = config["settings"]
        if not isinstance(settings, dict):
            errors.append("'settings' must be a dict")
        else:
            runs = settings.get("runs")
            if not isinstance(runs, int) or runs < 1:
                errors.append(f"'settings.runs' must be a positive integer, got: {runs}")
            workers = settings.get("workers")
            if not isinstance(workers, int) or workers < 1:
                errors.append(f"'settings.workers' must be a positive integer, got: {workers}")
        if "param_overrides" in config:
            overrides = config["param_overrides"]
            if not isinstance(overrides, dict):
                errors.append("'param_overrides' must be a dict")
            elif algorithms:
                for key in overrides:
                    if key not in algorithms:
                        errors.append(f"Unknown algorithm in param_overrides: '{key}'")
                        break
        return (len(errors) == 0, errors)

# --- Basic Executor Signatures ---
# An executor function should look like this:
# def execute_algorithm(problem: ProblemInstance, params: Dict[str, Any], seed: int, run_idx: int) -> RunResult:
#     pass
