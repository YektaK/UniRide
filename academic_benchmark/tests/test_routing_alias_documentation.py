"""The CVRP-*/CVRPTW-* alias table in HOW_TO_USE.md must match the engines the aliases run.

Owner decision (2026-10-23): CVRP-/CVRPTW-Numba-Swap and -Hybrid keep their names, but the
documentation says plainly that they run the legacy 2-opt matrix engine.
"""
from __future__ import annotations

import re
from pathlib import Path

import academic_benchmark.core.registry_setup as rs

HOW_TO_USE = Path(rs.__file__).resolve().parents[1] / "HOW_TO_USE.md"


def _alias_section() -> str:
    text = HOW_TO_USE.read_text(encoding="utf-8")
    start = text.index("### What the `CVRP-*` / `CVRPTW-*` aliases actually run")
    end = text.index("\n### ", start + 1)
    return text[start:end]


def _documented_engines() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for line in _alias_section().splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 2 or not cells[0].startswith("`"):
            continue
        engine = re.search(r"`(Matrix-[A-Za-z-]+-legacy)`", cells[1])
        if engine is None:
            continue
        for base in re.findall(r"`([^`]+)`", cells[0]):
            mapping[base] = engine.group(1)
    return mapping


def test_documented_alias_engines_match_the_registry_table() -> None:
    documented = _documented_engines()
    expected = {
        base: engine for base, engine in rs._ROUTING_ALIAS_ENGINES.items()
        if base != "Core-Greedy-Routing"
    }
    assert documented == expected


def test_doc_says_swap_and_hybrid_aliases_run_the_legacy_two_opt_engine() -> None:
    section = " ".join(_alias_section().split())
    for alias in ("CVRP-Numba-Swap", "CVRP-Numba-Hybrid", "CVRPTW-Numba-Swap", "CVRPTW-Numba-Hybrid"):
        assert f"`{alias}`" in section
    assert "run the legacy 2-opt matrix engine (`Matrix-TwoOpt-TSP-legacy`)" in section
    assert rs._ROUTING_ALIAS_ENGINES["Numba-Swap"] == "Matrix-TwoOpt-TSP-legacy"
    assert rs._ROUTING_ALIAS_ENGINES["Numba-Hybrid"] == "Matrix-TwoOpt-TSP-legacy"
