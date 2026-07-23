from __future__ import annotations

import ast
import os
import runpy
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "bildiri2026" / "3_run_benchmark.py"


def _source_and_tree() -> tuple[str, ast.Module]:
    source = SCRIPT.read_text(encoding="utf-8")
    return source, ast.parse(source, filename=str(SCRIPT))


def _replicate_loop(tree: ast.Module) -> ast.For:
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        if not isinstance(node.target, ast.Name) or node.target.id != "run":
            continue
        iterator = node.iter
        if (
            isinstance(iterator, ast.Call)
            and isinstance(iterator.func, ast.Name)
            and iterator.func.id == "range"
            and len(iterator.args) == 1
            and isinstance(iterator.args[0], ast.Name)
            and iterator.args[0].id == "num_runs"
        ):
            return node
    raise AssertionError("replicate loop was not found")


def test_standalone_benchmark_script_compiles_and_imports_without_main():
    source, tree = _source_and_tree()
    compile(source, str(SCRIPT), "exec")
    os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
    namespace = runpy.run_path(str(SCRIPT), run_name="__test__")
    assert callable(namespace["solve_run"])
    assert callable(namespace["main"])


def test_replicate_loop_uses_model_independent_paired_seed_and_submits_it():
    _, tree = _source_and_tree()
    loop = _replicate_loop(tree)

    seed_assignments = [
        node
        for node in loop.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "seed" for target in node.targets)
    ]
    assert len(seed_assignments) == 1
    seed_value = seed_assignments[0].value
    assert isinstance(seed_value, ast.BinOp)
    assert isinstance(seed_value.op, ast.Add)
    assert isinstance(seed_value.left, ast.Constant) and seed_value.left.value == 9000
    assert isinstance(seed_value.right, ast.Name) and seed_value.right.id == "run"
    assert not any(
        isinstance(node, ast.Name) and node.id == "model_id"
        for node in ast.walk(seed_value)
    )

    submits = [
        node
        for node in ast.walk(loop)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "submit"
    ]
    assert len(submits) == 1
    submit = submits[0]
    assert submit.args and isinstance(submit.args[0], ast.Name)
    assert submit.args[0].id == "solve_run"
    assert len(submit.args) > 4
    assert isinstance(submit.args[4], ast.Name)
    assert submit.args[4].id == "seed"