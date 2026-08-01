from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_ci_targets_wip_and_uses_declared_install_contracts():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "push:" in text
    assert "pull_request:" in text
    _assert_wip_trigger(text, "push")
    _assert_wip_trigger(text, "pull_request")
    assert "permissions:\n  contents: read" in text
    assert "ubuntu-latest" in text
    assert "node-version: 22" in text
    assert "npm ci" in text
    assert "npm run lint" in text
    assert "npm run typecheck" in text
    assert "npm test -- --run" in text
    assert 'python-version: "3.14"' in text
    assert 'pip install -e ".[test]" -c academic_benchmark/jit-benchmark-constraints.txt' in text
    assert (
        "python -m pip install -r optimizer_api/requirements.txt "
        "-c academic_benchmark/jit-benchmark-constraints.txt"
    ) in text
    assert "pip install fastapi uvicorn python-dotenv httpx" not in text
    assert "python -m pip check" in text
    assert "--collect-only academic_benchmark/tests" in text
    assert "optimizer_api/tests/test_phase0_containment.py" in text
    assert "requirements-lock.txt" not in text


def test_ci_rejects_single_trigger_branch_mutations():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for trigger in ("push", "pull_request"):
        mutated = text.replace(
            f"  {trigger}:\n    branches: [WIP]",
            f"  {trigger}:\n    branches: [main]",
            1,
        )
        with pytest.raises(AssertionError):
            _assert_wip_trigger(mutated, trigger)


def _assert_wip_trigger(text: str, trigger: str) -> None:
    lines = text.splitlines()
    marker_index = lines.index(f"  {trigger}:")
    assert lines[marker_index + 1] == "    branches: [WIP]"
