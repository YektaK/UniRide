from academic_benchmark import cli_engine


def _problem():
    return cli_engine.DOEProblem(
        name="tiny4",
        dimension=4,
        coordinates=[],
        optimal=100.0,
        category="small",
    )


def _spec():
    return cli_engine.StrategySpec(
        name="Numba-GA",
        payload=None,
        default_params={},
        algorithm_type="ga",
    )


def test_save_best_to_param_db_mirrors_doe_route_scores(monkeypatch):
    param_rows = []
    solution_rows = []
    monkeypatch.setattr(cli_engine, "_param_db_save", lambda **kwargs: param_rows.append(kwargs) or 1)
    monkeypatch.setattr(cli_engine, "_save_best_solution", lambda **kwargs: solution_rows.append(kwargs) or 1)

    saved = cli_engine._save_best_to_param_db(
        {
            "tiny4::Numba-GA": {
                "params": {"pop_size": 80},
                "avg_length": 123.4,
                "avg_gap": 23.4,
                "n_runs": 5,
                "tour": [0, 1, 2, 3],
            }
        },
        [_problem()],
        [_spec()],
    )

    assert saved == 1
    assert param_rows[0]["best_score"] == 123.4
    assert param_rows[0]["gap"] == 23.4
    assert solution_rows[0]["tour_length"] == 123.4
    assert solution_rows[0]["tour"] == [0, 1, 2, 3]


def test_save_best_to_param_db_keeps_optuna_gap_out_of_best_solutions(monkeypatch):
    param_rows = []
    solution_rows = []
    monkeypatch.setattr(cli_engine, "_param_db_save", lambda **kwargs: param_rows.append(kwargs) or 1)
    monkeypatch.setattr(cli_engine, "_save_best_solution", lambda **kwargs: solution_rows.append(kwargs) or 1)

    saved = cli_engine._save_best_to_param_db(
        {
            "tiny4::Numba-GA": {
                "params": {"pop_size": 120},
                "avg_gap": 1.2,
                "trials_used": 50,
                "tuning_method": "optuna",
            }
        },
        [_problem()],
        [_spec()],
    )

    assert saved == 1
    assert param_rows[0]["best_score"] == 1.2
    assert param_rows[0]["gap"] == 1.2
    assert solution_rows == []


def test_save_best_to_param_db_skips_invalid_scores(monkeypatch):
    param_rows = []
    solution_rows = []
    monkeypatch.setattr(cli_engine, "_param_db_save", lambda **kwargs: param_rows.append(kwargs) or 1)
    monkeypatch.setattr(cli_engine, "_save_best_solution", lambda **kwargs: solution_rows.append(kwargs) or 1)

    saved = cli_engine._save_best_to_param_db(
        {"tiny4::Numba-GA": {"params": {"pop_size": 120}, "avg_gap": float("inf")}},
        [_problem()],
        [_spec()],
    )

    assert saved == 0
    assert param_rows == []
    assert solution_rows == []
