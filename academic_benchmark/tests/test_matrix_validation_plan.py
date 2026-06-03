from __future__ import annotations

from academic_benchmark.matrix_validation_plan import (
    build_validation_jobs,
    main,
    run_validation_jobs,
)


def test_build_validation_jobs_creates_named_solver_variants():
    jobs = build_validation_jobs(run_id_prefix="validation", n_runs=3, seed=2100)

    assert [job.run_id for job in jobs] == [
        "validation-time10-scale1000",
        "validation-time20-scale1000",
    ]
    assert all(job.algorithms == ("OR-Tools", "PyVRP") for job in jobs)
    assert all(job.n_runs == 3 for job in jobs)
    assert all("C101" in job.problems and "RC101" in job.problems for job in jobs)
    assert all(job.problem_types == () for job in jobs)
    assert all(job.max_dim == 10_000 for job in jobs)
    assert all(job.limit == 100 for job in jobs)
    assert jobs[0].params == {"time_limit_seconds": 10, "scale": 1000}
    assert jobs[1].params == {"time_limit_seconds": 20, "scale": 1000}
    assert jobs[0].per_algorithm_params["OR-Tools"]["first_solution_strategy"] == "PARALLEL_CHEAPEST_INSERTION"
    assert jobs[0].per_algorithm_params["OR-Tools"]["local_search_metaheuristic"] == "GUIDED_LOCAL_SEARCH"
    assert jobs[0].seed == 2100
    assert jobs[1].seed == 2200


def test_run_validation_jobs_calls_runner_and_summarizer():
    calls = []

    def fake_runner(**kwargs):
        calls.append(kwargs)
        return {"run_id": kwargs["run_id"], "saved_results": 2, "errors": []}

    def fake_summarizer(run_id, db_path, limit):
        return {"run_id": run_id, "total_rows": limit, "db_path": db_path}

    jobs = build_validation_jobs(
        run_id_prefix="validation",
        n_runs=2,
        seed=100,
        problems=("C101",),
        variants=(("fast", 5),),
    )

    results = run_validation_jobs(jobs, db_path="test.db", runner=fake_runner, summarizer=fake_summarizer)

    assert len(results) == 1
    assert calls[0]["run_id"] == "validation-fast"
    assert calls[0]["problems"] == ("C101",)
    assert calls[0]["problem_types"] == ()
    assert calls[0]["n_runs"] == 2
    assert calls[0]["max_dim"] == 10_000
    assert calls[0]["limit"] == 100
    assert calls[0]["algorithm_params"] == {"time_limit_seconds": 5, "scale": 1000}
    assert calls[0]["source"] == "academic_matrix_validation"
    assert results[0]["result"] == {"run_id": "validation-fast", "saved_results": 2, "errors": []}
    assert results[0]["summary"]["run_id"] == "validation-fast"
    assert results[0]["summary"]["db_path"] == "test.db"


def test_main_serializes_summary_tuple_keys(monkeypatch, capsys):
    monkeypatch.setattr(
        "academic_benchmark.matrix_validation_plan.run_validation_jobs",
        lambda jobs, db_path: [
            {
                "job": {"run_id": "validation-fast"},
                "result": {"run_id": "validation-fast", "errors": []},
                "summary": {
                    "run_id": "validation-fast",
                    "best_feasible": {("C101", "OR-Tools"): {"objective_cost": 828.9}},
                },
            }
        ],
    )

    exit_code = main(["--run-id-prefix", "validation", "--variants", "fast:1"])

    assert exit_code == 0
    assert '"C101::OR-Tools"' in capsys.readouterr().out


def test_main_all_imported_profile_uses_cvrp_cvrptw_selection(monkeypatch):
    captured_jobs = []

    def fake_run_validation_jobs(jobs, db_path):
        captured_jobs.extend(jobs)
        return [
            {
                "job": {"run_id": jobs[0].run_id},
                "result": {"run_id": jobs[0].run_id, "errors": []},
                "summary": {"run_id": jobs[0].run_id},
            }
        ]

    monkeypatch.setattr(
        "academic_benchmark.matrix_validation_plan.run_validation_jobs",
        fake_run_validation_jobs,
    )

    exit_code = main(["--profile", "all-imported", "--run-id-prefix", "validation"])

    assert exit_code == 0
    assert len(captured_jobs) == 1
    job = captured_jobs[0]
    assert job.run_id == "validation-time10-scale1000"
    assert job.problems == ()
    assert job.problem_types == ("cvrp", "cvrptw")
    assert job.algorithms == ("OR-Tools", "PyVRP")
    assert job.n_runs == 1
    assert job.limit == 100_000
    assert job.params == {"time_limit_seconds": 10, "scale": 1000}


def test_main_all_imported_profile_allows_explicit_overrides(monkeypatch):
    captured_jobs = []

    monkeypatch.setattr(
        "academic_benchmark.matrix_validation_plan.run_validation_jobs",
        lambda jobs, db_path: captured_jobs.extend(jobs) or [],
    )

    exit_code = main(
        [
            "--profile",
            "all-imported",
            "--run-id-prefix",
            "validation",
            "--problems",
            "C101",
            "--problem-types",
            "cvrptw",
            "--n-runs",
            "2",
            "--limit",
            "5",
            "--variants",
            "tiny:1",
        ]
    )

    assert exit_code == 0
    assert len(captured_jobs) == 1
    job = captured_jobs[0]
    assert job.run_id == "validation-tiny"
    assert job.problems == ("C101",)
    assert job.problem_types == ("cvrptw",)
    assert job.n_runs == 2
    assert job.limit == 5
    assert job.params == {"time_limit_seconds": 1, "scale": 1000}
