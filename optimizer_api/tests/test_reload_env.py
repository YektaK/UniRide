"""L14: uvicorn auto-reload is controlled by UNIRIDE_API_RELOAD (default on)."""

import pytest

from runtime_config import reload_enabled


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", " Yes "])
def test_truthy_values_enable_reload(value):
    assert reload_enabled({"UNIRIDE_API_RELOAD": value}) is True


@pytest.mark.parametrize("value", ["0", "false", "False", "no", " NO "])
def test_falsy_values_disable_reload(value):
    assert reload_enabled({"UNIRIDE_API_RELOAD": value}) is False


@pytest.mark.parametrize("env", [{}, {"UNIRIDE_API_RELOAD": ""}, {"UNIRIDE_API_RELOAD": "maybe"}])
def test_unset_or_unrecognised_keeps_default_on(env):
    assert reload_enabled(env) is True


def test_reads_process_environment_when_no_mapping_given(monkeypatch):
    monkeypatch.setenv("UNIRIDE_API_RELOAD", "0")
    assert reload_enabled() is False
    monkeypatch.delenv("UNIRIDE_API_RELOAD")
    assert reload_enabled() is True
