from types import SimpleNamespace

from academic_benchmark.bildiri2026 import orchestrate_batch


def test_run_cmd_executes_argv_without_shell(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(orchestrate_batch.subprocess, "run", fake_run)

    result = orchestrate_batch.run_cmd(["python", "script.py", "1,2,3"])

    assert result.returncode == 0
    assert calls == [
        (
            ["python", "script.py", "1,2,3"],
            {
                "capture_output": True,
                "cwd": orchestrate_batch.SCRIPT_DIR,
                "text": True,
            },
        )
    ]
