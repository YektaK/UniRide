"""H12 / QW7: no code under academic_benchmark / uniride_core / optimizer_api may reseed
the process-global ``random`` or ``numpy.random`` state (shared across threads and runs)."""

import ast
import random
from pathlib import Path

from academic_benchmark.benchmark_utils import generate_combinations

REPO = Path(__file__).resolve().parents[2]
SCAN_DIRS = ["academic_benchmark", "uniride_core", "optimizer_api"]
SKIP_PARTS = {"tests", "archive", "__pycache__", "tsplib_data", "benchmark_results", "benchmark_db", "golden"}


def _production_files():
    for top in SCAN_DIRS:
        for path in (REPO / top).rglob("*.py"):
            rel = path.relative_to(REPO)
            if SKIP_PARTS & set(rel.parts):
                continue
            if rel.name.startswith("test_"):
                continue
            yield path


def _is_global_seed_call(node: ast.Call) -> bool:
    func = node.func
    if not (isinstance(func, ast.Attribute) and func.attr == "seed"):
        return False
    owner = func.value
    if isinstance(owner, ast.Name) and owner.id == "random":
        return True
    # np.random.seed / numpy.random.seed
    return (
        isinstance(owner, ast.Attribute)
        and owner.attr == "random"
        and isinstance(owner.value, ast.Name)
        and owner.value.id in {"np", "numpy", "_np"}
    )


def test_no_global_reseeding_in_production_code():
    offenders = []
    for path in _production_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _is_global_seed_call(node):
                offenders.append(f"{path.relative_to(REPO)}:{node.lineno}")
    assert offenders == []


def test_generate_combinations_fractional_sample_leaves_global_state_alone():
    space = {"a": list(range(6)), "b": list(range(6))}
    random.seed(2468)
    before = random.getstate()
    sample = generate_combinations(space, 7, strategy="fractional_fallback", random_seed=5)
    assert random.getstate() == before
    # Same sample the former global seed()+sample() produced.
    keys = list(space)
    import itertools
    all_combos = [dict(zip(keys, v)) for v in itertools.product(*(space[k] for k in keys))]
    assert sample == random.Random(5).sample(all_combos, 7)
