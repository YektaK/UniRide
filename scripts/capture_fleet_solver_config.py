#!/usr/bin/env python3
"""Prints, as one JSON line, the solver configuration the fleet campaign records in its manifest.

Read-only: it constructs the two GA strategies, reads the day-selection constants and the installed OR-Tools
version, and touches neither the database nor the network. Used by scripts/run-fleet-scenarios.ts for the
manifest and for the WP-E10 preflight (design rule (c)).

Run: python scripts/capture_fleet_solver_config.py   (from any directory)

``num_workers`` of the CP-SAT day selection is a literal in typed_day_selection.py (``solver.parameters.num_workers
= 1``), not an exported constant. It is read from the source text and reported as null when the source does not
contain exactly one such assignment, so a change of that line is visible instead of assumed.
"""
import inspect
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "optimizer_api"))


def num_workers(module):
    found = re.findall(r"parameters\.num_workers\s*=\s*(\d+)\b", inspect.getsource(module))
    return int(found[0]) if len(found) == 1 else None


def capture():
    from strategies.ga_split_hf_strategy import GASplitHFStrategy
    from strategies.ga_split_strategy import GASplitStrategy
    from uniride_core.planning import typed_day_selection as day_selection
    import ortools

    ga = GASplitStrategy()
    hf = GASplitHFStrategy()
    return {
        "ga": {"defaults": ga.DEFAULT_CONFIG, "config": ga.config, "seed": ga.seed},
        "hf": {"config": hf.config, "seed": hf.seed},
        "cp": {
            "version": getattr(ortools, "__version__", None),
            "seed": day_selection.SOLVER_SEED,
            "workers": num_workers(day_selection),
        },
    }


if __name__ == "__main__":
    print(json.dumps(capture()))
