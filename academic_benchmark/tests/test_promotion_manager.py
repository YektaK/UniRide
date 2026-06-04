from academic_benchmark.promotion_manager import (
    main,
    promote_configs,
    validate_promoted_document,
)
from academic_benchmark.promoted_configs import load_promoted_configs
from academic_benchmark.tsplib_manager import save_benchmark_result, save_benchmark_run


def test_validate_promoted_document_rejects_empty_configs():
    errors = validate_promoted_document({"configs": []}, min_configs=1)

    assert errors == ["expected at least 1 promoted config(s), found 0"]


def test_promote_configs_writes_valid_document(tmp_path):
    db_path = str(tmp_path / "tsplib.db")
    output_path = str(tmp_path / "promoted_configs.json")
    save_benchmark_run("run-1", db_path=db_path)
    save_benchmark_result(
        "run-1",
        {
            "problem": "tiny-cvrp",
            "algorithm": "Core-Greedy-Routing",
            "problem_type": "cvrp",
            "matrix_kind": "distance",
            "objective_cost": 30.0,
            "params": {"split": "linear"},
        },
        db_path=db_path,
    )

    document = promote_configs(db_path=db_path, output_path=output_path)

    assert load_promoted_configs(output_path) == document
    assert document["configs"][0]["algorithm"] == "Core-Greedy-Routing"


def test_promote_configs_can_dry_run_without_writing(tmp_path):
    db_path = str(tmp_path / "tsplib.db")
    output_path = str(tmp_path / "promoted_configs.json")
    save_benchmark_run("run-1", db_path=db_path)
    save_benchmark_result(
        "run-1",
        {
            "problem": "tiny-atsp",
            "algorithm": "Numba-Or-opt",
            "problem_type": "atsp",
            "matrix_kind": "travel_time",
            "objective_cost": 20.0,
            "params": {"max_passes": 2},
        },
        db_path=db_path,
    )

    document = promote_configs(db_path=db_path, output_path=output_path, dry_run=True)

    assert document["configs"]
    assert not output_path.endswith("not-used")
    assert not (tmp_path / "promoted_configs.json").exists()


def test_main_returns_nonzero_for_empty_database(tmp_path, capsys):
    code = main([
        "--db-path",
        str(tmp_path / "empty.db"),
        "--output",
        str(tmp_path / "promoted_configs.json"),
    ])

    assert code == 2
    assert "validation failed" in capsys.readouterr().out


def test_validate_promoted_document_rejects_empty_params_by_default():
    errors = validate_promoted_document({
        "configs": [
            {
                "algorithm": "TwoOpt",
                "problem_type": "tsp",
                "matrix_kind": "distance",
                "params": {},
            }
        ]
    })

    assert errors == ["configs[0] has empty params"]


def test_validate_promoted_document_can_allow_empty_params():
    errors = validate_promoted_document(
        {
            "configs": [
                {
                    "algorithm": "TwoOpt",
                    "problem_type": "tsp",
                    "matrix_kind": "distance",
                    "params": {},
                }
            ]
        },
        require_params=False,
    )

    assert errors == []


def test_validate_promoted_document_rejects_low_evidence_count():
    errors = validate_promoted_document(
        {
            "configs": [
                {
                    "algorithm": "OR-Tools",
                    "problem_type": "cvrp",
                    "matrix_kind": "distance",
                    "params": {"scale": 1000},
                    "evidence_count": 1,
                }
            ]
        },
        min_evidence_runs=2,
    )

    assert errors == ["configs[0] has evidence_count 1, expected at least 2"]


def test_promote_configs_honors_min_evidence_runs(tmp_path):
    db_path = str(tmp_path / "tsplib.db")
    output_path = str(tmp_path / "promoted_configs.json")
    result = {
        "problem": "A-n32-k5",
        "algorithm": "OR-Tools",
        "problem_type": "cvrp",
        "matrix_kind": "distance",
        "objective_cost": 784.0,
        "capacity_violations": 0,
        "tw_violations": 0,
        "params": {"time_limit_seconds": 5},
    }
    save_benchmark_run("run-1", db_path=db_path)
    save_benchmark_run("run-2", db_path=db_path)
    save_benchmark_result("run-1", result, db_path=db_path)
    save_benchmark_result("run-2", result, db_path=db_path)

    document = promote_configs(
        db_path=db_path,
        output_path=output_path,
        min_evidence_runs=2,
    )

    assert document["configs"][0]["evidence_count"] == 2
    assert load_promoted_configs(output_path) == document
