import asyncio
import builtins
import json
from pathlib import Path

import pytest
from fastapi import HTTPException, Request
from fastapi.exception_handlers import http_exception_handler

from optimizer_api.auth import require_internal_api_key
from optimizer_api.runtime_config import optimizer_host
from optimizer_api.routers import benchmark


def test_optimizer_host_defaults_to_loopback(monkeypatch):
    monkeypatch.delenv("OPTIMIZER_HOST", raising=False)

    assert optimizer_host() == "127.0.0.1"


def test_internal_key_is_required_and_rejects_mismatch(monkeypatch):
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)

    with pytest.raises(HTTPException) as exc_unset:
        asyncio.run(require_internal_api_key(None))
    assert exc_unset.value.status_code == 403

    with pytest.raises(HTTPException) as exc_unset_with_header:
        asyncio.run(require_internal_api_key("anything"))
    assert exc_unset_with_header.value.status_code == 403

    monkeypatch.setenv("INTERNAL_API_KEY", "expected")

    with pytest.raises(HTTPException) as exc_wrong:
        asyncio.run(require_internal_api_key("wrong"))

    assert exc_wrong.value.status_code == 403


def test_cli_filename_cannot_escape_result_roots(tmp_path, monkeypatch):
    root = tmp_path / "results"
    root.mkdir()
    (root / "valid.json").write_text("[]", encoding="utf-8")
    outside = tmp_path / "outside.json"
    outside.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(benchmark, "CLI_RESULTS_DIR", str(root))
    monkeypatch.setattr(benchmark, "CLI_RESULTS_NUMBA_DIR", str(tmp_path / "missing"))

    assert benchmark._resolve_cli_filename("valid.json") == str((root / "valid.json").resolve())

    with pytest.raises(HTTPException):
        benchmark._resolve_cli_filename("../outside.json")


def test_cli_filename_cannot_follow_symlink_outside_result_roots(tmp_path, monkeypatch):
    root = tmp_path / "results"
    root.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("[]", encoding="utf-8")
    (root / "outside-link.json").symlink_to(outside)
    monkeypatch.setattr(benchmark, "CLI_RESULTS_DIR", str(root))
    monkeypatch.setattr(benchmark, "CLI_RESULTS_NUMBA_DIR", str(tmp_path / "missing"))

    with pytest.raises(HTTPException):
        benchmark._resolve_cli_filename("outside-link.json")


def test_cli_file_listing_does_not_expose_absolute_paths(tmp_path, monkeypatch):
    root = tmp_path / "results"
    root.mkdir()
    (root / "valid.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(benchmark, "CLI_RESULTS_DIR", str(root))
    monkeypatch.setattr(benchmark, "CLI_RESULTS_NUMBA_DIR", str(tmp_path / "missing"))

    rows = benchmark._find_cli_json_files()

    assert rows[0]["filename"] == "valid.json"
    assert "filepath" not in rows[0]


def test_cli_file_listing_hides_absolute_scan_directories(tmp_path, monkeypatch):
    results_root = tmp_path / "results"
    numba_root = tmp_path / "numba-results"
    results_root.mkdir()
    numba_root.mkdir()
    monkeypatch.setattr(benchmark, "CLI_RESULTS_DIR", str(results_root))
    monkeypatch.setattr(benchmark, "CLI_RESULTS_NUMBA_DIR", str(numba_root))

    response = benchmark.list_cli_benchmark_files()

    assert response["scan_directories"] == ["results", "numba-results"]
    assert all(str(tmp_path) not in value for value in response["scan_directories"])


def test_cli_preview_hides_resolved_path_when_file_disappears_after_resolution(tmp_path, monkeypatch):
    root = tmp_path / "results"
    root.mkdir()
    result_file = root / "valid.json"
    result_file.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(benchmark, "CLI_RESULTS_DIR", str(root))
    monkeypatch.setattr(benchmark, "CLI_RESULTS_NUMBA_DIR", str(tmp_path / "missing"))

    resolve_filename = benchmark._resolve_cli_filename

    def resolve_then_remove(filename):
        resolved = resolve_filename(filename)
        Path(resolved).unlink()
        return resolved

    monkeypatch.setattr(benchmark, "_resolve_cli_filename", resolve_then_remove)
    preview_route = next(
        route
        for route in benchmark.router.routes
        if route.path == "/api/v1/benchmark/cli/preview"
    )

    with pytest.raises(HTTPException) as exc:
        preview_route.endpoint(filename="valid.json")

    response = asyncio.run(http_exception_handler(
        Request({"type": "http", "method": "GET", "path": preview_route.path, "headers": []}),
        exc.value,
    ))

    assert response.status_code == 404
    assert json.loads(response.body)["detail"] == "File not found"
    assert str(tmp_path).encode() not in response.body


def test_cli_preview_hides_resolved_path_when_file_disappears_during_open(tmp_path, monkeypatch):
    root = tmp_path / "results"
    root.mkdir()
    result_file = root / "valid.json"
    result_file.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(benchmark, "CLI_RESULTS_DIR", str(root))
    monkeypatch.setattr(benchmark, "CLI_RESULTS_NUMBA_DIR", str(tmp_path / "missing"))

    original_open = builtins.open

    def open_missing_target(file, *args, **kwargs):
        if Path(file) == result_file:
            raise FileNotFoundError(file)
        return original_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", open_missing_target)
    preview_route = next(
        route
        for route in benchmark.router.routes
        if route.path == "/api/v1/benchmark/cli/preview"
    )

    with pytest.raises(HTTPException) as exc:
        preview_route.endpoint(filename="valid.json")

    response = asyncio.run(http_exception_handler(
        Request({"type": "http", "method": "GET", "path": preview_route.path, "headers": []}),
        exc.value,
    ))

    assert response.status_code == 404
    assert json.loads(response.body)["detail"] == "File not found"
    assert str(tmp_path).encode() not in response.body


def test_only_cli_file_routes_require_the_internal_api_key():
    cli_routes = {
        route.path: route
        for route in benchmark.router.routes
        if route.path.startswith("/api/v1/benchmark/cli/")
    }

    assert set(cli_routes) == {
        "/api/v1/benchmark/cli/files",
        "/api/v1/benchmark/cli/import",
        "/api/v1/benchmark/cli/preview",
    }
    assert all(route.dependencies for route in cli_routes.values())
