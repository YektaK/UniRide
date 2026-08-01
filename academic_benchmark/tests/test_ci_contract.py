from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_ci_targets_wip_and_uses_declared_install_contracts():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "push:" in text
    assert "pull_request:" in text
    assert "branches: [WIP]" in text
    assert "ubuntu-latest" in text
    assert "node-version: 22" in text
    assert "npm ci" in text
    assert "npm run lint" in text
    assert "npm run typecheck" in text
    assert "npm test -- --run" in text
    assert 'python-version: "3.14"' in text
    assert 'pip install -e ".[test]" -c academic_benchmark/jit-benchmark-constraints.txt' in text
    assert "python -m pip check" in text
    assert "--collect-only academic_benchmark/tests" in text
    assert "optimizer_api/tests/test_phase0_containment.py" in text
    assert "requirements-lock.txt" not in text
