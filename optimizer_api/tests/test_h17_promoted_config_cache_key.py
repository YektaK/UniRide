"""H17 polish: the promoted-config cache is keyed by the RESOLVED path.

Before the fix ``get_promoted_params`` called the lru-cached loader with key
``(None,)`` and ``promoted_config_provenance`` with key ``()``, so what a path
change did depended on which key had been filled first. A malformed file also
raised out of strategy construction (flag on) and still stored a hash.

Semantics chosen (DECISION_LOG A12): the SHA in provenance is the hash of the
file at the resolved path whenever that file parsed as a promoted-config
document, whether or not the flag is on (the flag is reported separately); a
file that is missing, unreadable or malformed reports ``None``. Production
never raises because of the file: it falls back to defaults and logs a warning.
"""

import hashlib
import json
import logging

import pytest

from strategies import get_strategy
from strategies.ga_split_strategy import GASplitStrategy
from strategies.promoted_config_loader import (
    PROMOTED_CONFIG_PATH_ENV,
    clear_promoted_config_cache,
    promoted_config_provenance,
)

USE_PROMOTED_ENV = "UNIRIDE_USE_PROMOTED_CONFIG"


def _write(path, pop_size):
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source": "test",
                "configs": [
                    {
                        "algorithm": "ga_split",
                        "problem_type": "cvrptw",
                        "matrix_kind": "travel_time",
                        "params": {"pop_size": pop_size, "generations": 3, "seed": 5},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv(PROMOTED_CONFIG_PATH_ENV, raising=False)
    monkeypatch.delenv(USE_PROMOTED_ENV, raising=False)
    clear_promoted_config_cache()
    yield
    clear_promoted_config_cache()


def test_path_set_after_import_time_provenance_is_used_by_strategy_and_provenance(
    tmp_path, monkeypatch
):
    promoted_config_provenance()  # what strategies/__init__ does at import (default path)
    new_file = tmp_path / "later.json"
    digest = _write(new_file, 13)
    monkeypatch.setenv(PROMOTED_CONFIG_PATH_ENV, str(new_file))
    monkeypatch.setenv(USE_PROMOTED_ENV, "1")

    assert get_strategy("ga_split").config["population_size"] == 13
    provenance = promoted_config_provenance()
    assert provenance["promoted_config_flag"] is True
    assert provenance["promoted_config_sha256"] == digest


def test_changing_the_path_is_not_masked_by_an_earlier_lookup(tmp_path, monkeypatch):
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    _write(first, 7)
    digest_second = _write(second, 11)
    monkeypatch.setenv(USE_PROMOTED_ENV, "1")
    monkeypatch.setenv(PROMOTED_CONFIG_PATH_ENV, str(first))
    assert get_strategy("ga_split").config["population_size"] == 7

    monkeypatch.setenv(PROMOTED_CONFIG_PATH_ENV, str(second))

    assert get_strategy("ga_split").config["population_size"] == 11
    assert promoted_config_provenance()["promoted_config_sha256"] == digest_second


def test_flag_off_with_path_reports_file_sha_but_strategy_uses_defaults(tmp_path, monkeypatch):
    path = tmp_path / "off.json"
    digest = _write(path, 17)
    monkeypatch.setenv(PROMOTED_CONFIG_PATH_ENV, str(path))

    assert get_strategy("ga_split").config == GASplitStrategy.DEFAULT_CONFIG
    provenance = promoted_config_provenance()
    assert provenance["promoted_config_flag"] is False
    assert provenance["promoted_config_sha256"] == digest


@pytest.mark.parametrize("payload", [b"{not json", b"[]", b"\xff\xfe\x00bad"])
def test_malformed_file_falls_back_to_defaults_logs_and_stores_no_hash(
    tmp_path, monkeypatch, caplog, payload
):
    path = tmp_path / "bad.json"
    path.write_bytes(payload)
    monkeypatch.setenv(PROMOTED_CONFIG_PATH_ENV, str(path))
    monkeypatch.setenv(USE_PROMOTED_ENV, "1")

    with caplog.at_level(logging.WARNING, logger="strategies.promoted_config_loader"):
        config = get_strategy("ga_split").config  # must not raise
        provenance = promoted_config_provenance()

    assert config == GASplitStrategy.DEFAULT_CONFIG
    assert provenance["promoted_config_sha256"] is None
    assert any("promoted" in r.getMessage().lower() and r.levelno == logging.WARNING for r in caplog.records)
    assert "not json" not in caplog.text  # file content is never logged


def test_malformed_file_with_flag_off_reports_no_hash(tmp_path, monkeypatch):
    path = tmp_path / "bad.json"
    path.write_text("{oops", encoding="utf-8")
    monkeypatch.setenv(PROMOTED_CONFIG_PATH_ENV, str(path))

    assert promoted_config_provenance()["promoted_config_sha256"] is None
