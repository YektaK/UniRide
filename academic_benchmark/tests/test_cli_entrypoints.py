from __future__ import annotations

import json

import pytest

from academic_benchmark import promotion_manager, run_matrix_benchmark


def test_run_matrix_benchmark_main_parses_csv_and_json_params(monkeypatch, capsys):
    captured: dict[str, object] = {}

    def fake_run_matrix_benchmark(**kwargs):
        captured.update(kwargs)
        return {"run_id": kwargs["run_id"], "saved_results": 3, "errors": []}

    monkeypatch.setattr(run_matrix_benchmark, "run_matrix_benchmark", fake_run_matrix_benchmark)

    exit_code = run_matrix_benchmark.main(
        [
            "--db-path",
            "bench.db",
            "--run-id",
            "cli-smoke",
            "--algorithms",
            "Core-Greedy-Routing,OR-Tools",
            "--problems",
            "smoke-cvrp,smoke-solomon",
            "--problem-types",
            "CVRP,CVRPTW",
            "--n-runs",
            "2",
            "--seed",
            "123",
            "--max-dim",
            "200",
            "--limit",
            "5",
            "--seed-smoke",
            "--params-json",
            '{"time_limit_seconds": 1}',
            "--algorithm-params-json",
            '{"OR-Tools": {"scale": 1000}}',
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "run_id=cli-smoke" in output
    assert "saved_results=3" in output
    assert captured == {
        "db_path": "bench.db",
        "run_id": "cli-smoke",
        "algorithms": ["Core-Greedy-Routing", "OR-Tools"],
        "problems": ["smoke-cvrp", "smoke-solomon"],
        "problem_types": ["CVRP", "CVRPTW"],
        "n_runs": 2,
        "seed": 123,
        "max_dim": 200,
        "limit": 5,
        "seed_missing_smoke": True,
        "algorithm_params": {"time_limit_seconds": 1},
        "per_algorithm_params": {"OR-Tools": {"scale": 1000}},
    }


def test_run_matrix_benchmark_main_rejects_non_object_params_json():
    with pytest.raises(SystemExit) as exc:
        run_matrix_benchmark.main(["--params-json", "[1, 2, 3]"])

    assert exc.value.code == 2


def test_promotion_manager_main_dry_run_prints_summary(monkeypatch, capsys):
    captured: dict[str, object] = {}

    def fake_promote_configs(**kwargs):
        captured.update(kwargs)
        return {"generated_at": "2026-06-05T00:00:00Z", "configs": [{"algorithm": "A"}]}

    monkeypatch.setattr(promotion_manager, "promote_configs", fake_promote_configs)

    exit_code = promotion_manager.main(
        [
            "--db-path",
            "bench.db",
            "--output",
            "promoted.json",
            "--limit",
            "50",
            "--min-configs",
            "1",
            "--min-evidence-runs",
            "2",
            "--allow-empty-params",
            "--dry-run",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == {"configs": 1, "dry_run": True, "output": None}
    assert captured == {
        "db_path": "bench.db",
        "output_path": "promoted.json",
        "limit": 50,
        "min_configs": 1,
        "require_params": False,
        "min_evidence_runs": 2,
        "dry_run": True,
    }


def test_promotion_manager_main_reports_validation_failure(monkeypatch, capsys):
    def fake_promote_configs(**kwargs):
        raise ValueError("expected at least 2 promoted config(s)")

    monkeypatch.setattr(promotion_manager, "promote_configs", fake_promote_configs)

    exit_code = promotion_manager.main(["--min-configs", "2", "--dry-run"])

    assert exit_code == 2
    assert "[PROMOTE] validation failed: expected at least 2 promoted config(s)" in capsys.readouterr().out
