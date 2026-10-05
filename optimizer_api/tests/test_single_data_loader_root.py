"""H5 regression: one DataLoader root and TTL refresh before snapshot binding.

Audit finding H5 (docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md): the
readiness router imported ``optimizer_api.utils.data_loader`` while the
optimizer router and the strategies imported ``utils.data_loader``. With the
repository root importable (editable install) that produced two DataLoader
classes and two singletons, so ``/matrix-snapshot`` refreshed one copy while
``/optimize`` read the other (empty or TTL-expired) copy and failed closed
with "matrix snapshot unavailable or changed".

All tests are offline: no network, no Supabase, no ``.env`` loading.
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

from compute_policy import ComputePolicy
from models import schemas
from routers import optimization
from strategies.canonical import ResolvedStrategy
from utils.data_loader import DataLoader
from utils.matrix_repository import TimeMatrixRepository
from utils.patterns import SingletonMeta

API_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = API_DIR.parent

FEASIBLE = {"is_feasible": True, "violation_count": 0, "violations": []}
CODES = ["D.Kampus", "Sw1", "So1"]
ROWS = [
    {"origin_code": a, "destination_code": b, "duration_minutes": 10 + i + j}
    for i, a in enumerate(CODES)
    for j, b in enumerate(CODES)
    if a != b
]


# --------------------------------------------------------------- import root


def test_readiness_and_optimization_share_one_data_loader_class():
    from optimizer_api.routers import readiness

    assert readiness.DataLoader is optimization.DataLoader
    assert readiness.DataLoader is DataLoader
    assert readiness.DataLoader.get_instance() is optimization.DataLoader.get_instance()


_LAUNCHER_PROBE = textwrap.dedent(
    """
    import os, sys
    root, api = sys.argv[1], sys.argv[2]
    os.chdir(api)
    sys.path.insert(0, api)      # launcher: cwd=optimizer_api, `python main.py`
    sys.path.append(root)        # editable install makes `optimizer_api.*` importable
    import main  # noqa: F401
    flat = "utils.data_loader" in sys.modules
    pkg = "optimizer_api.utils.data_loader" in sys.modules
    from routers import optimization, readiness
    same_class = readiness.DataLoader is optimization.DataLoader
    same_instance = readiness.DataLoader.get_instance() is optimization.DataLoader.get_instance()
    print(f"RESULT flat={flat} pkg={pkg} same_class={same_class} same_instance={same_instance}")
    """
)


def test_launcher_style_startup_loads_a_single_data_loader_module():
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ("UNIRIDE_DISABLE_AUTH", "UNIRIDE_TENANT_KEYS")
    }
    env.update(
        {
            "PYTHON_DOTENV_DISABLED": "1",
            "SUPABASE_URL": "",
            "SUPABASE_SERVICE_ROLE_KEY": "",
            "INTERNAL_API_KEY": "probe-key",
            "APP_ENV": "development",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [sys.executable, "-B", "-c", _LAUNCHER_PROBE, str(ROOT_DIR), str(API_DIR)],
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    result_lines = [
        line for line in completed.stdout.splitlines() if line.startswith("RESULT ")
    ]
    assert result_lines, completed.stdout[-2000:]
    assert result_lines[-1] == (
        "RESULT flat=True pkg=False same_class=True same_instance=True"
    )


# --------------------------------------------------- TTL refresh before binding


class _Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class _Provider:
    def __init__(self):
        self.calls = 0

    def fetch_rows(self):
        self.calls += 1
        return [dict(row) for row in ROWS]


class _Strategy:
    name = "genetic_algorithm"

    def __init__(self):
        self.optimize_calls = 0

    def optimize(self, request):
        self.optimize_calls += 1
        return schemas.OptimizationResponse(
            algorithm_used="genetic_algorithm", success=False, routes=[]
        )


def _install_solver_stubs(monkeypatch, strategy):
    resolution = ResolvedStrategy("ga", "genetic_algorithm", lambda: strategy, ("ga",))
    monkeypatch.setattr(optimization, "resolve_strategy", lambda key: resolution)
    monkeypatch.setattr(optimization, "load_compute_policy", lambda: ComputePolicy())
    monkeypatch.setattr(
        optimization,
        "apply_compute_policy",
        lambda request, actual_resolution, actual_strategy, policy: (
            request.model_copy(deep=True),
            schemas.AppliedComputePolicyInfo(
                profile_id="production-conservative-v1",
                algorithm_requested="ga",
                algorithm_canonical="genetic_algorithm",
                student_count=len(request.students),
                vehicle_count=0,
                cancellation_mode="none",
                limits={},
            ),
        ),
    )
    monkeypatch.setattr(
        optimization, "certify_optimization_response", lambda request, result, arc_lookup=None: FEASIBLE
    )


def _request(digest):
    return schemas.OptimizationRequest(
        algorithm="ga",
        students=[
            schemas.StudentNode(
                id=f"S{i}",
                name=f"S{i}",
                location_code=code,
                coordinates={"lat": 1.0, "lng": 1.0},
                disability_type="Sw" if code.startswith("Sw") else "So",
            )
            for i, code in enumerate(CODES[1:])
        ],
        depot=schemas.LocationNode(id="D.Kampus", lat=0.0, lng=0.0),
        expected_matrix_sha256=digest,
    )


def test_bound_optimize_after_ttl_expiry_refreshes_solver_copy(monkeypatch):
    clock = _Clock()
    provider = _Provider()
    repository = TimeMatrixRepository(provider=provider, ttl_seconds=600, clock=clock)
    repository.load()

    # Fresh, isolated singleton registry so the real DataLoader wraps our repo.
    monkeypatch.setattr(SingletonMeta, "_instances", {})
    loader = DataLoader(repository=repository)
    assert DataLoader.get_instance() is loader

    snapshot = repository.matrix_snapshot(CODES[1:], "D.Kampus")
    strategy = _Strategy()
    _install_solver_stubs(monkeypatch, strategy)

    # The solver copy passes its TTL, as happens in production after 600 s.
    clock.now = 601.0
    assert provider.calls == 1

    result = optimization.optimize_route(_request(snapshot["sha256"]))

    assert provider.calls >= 2, "stale solver copy was not refreshed"
    assert strategy.optimize_calls == 1
    assert result.feasibility_certificate.certify_error is None
