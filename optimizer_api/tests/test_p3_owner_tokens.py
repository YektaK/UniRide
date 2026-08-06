"""Phase 3 — benchmark run ownership (P3) tests.

See docs/superpowers/specs/2026-08-06-p3-benchmark-run-owner-tokens-design.md
"""

import hashlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from optimizer_api.benchmark_state import (
    BenchmarkRunState,
    BenchmarkStateManager,
    hash_owner_token,
    verify_owner_token,
)
from optimizer_api.routers import benchmark

API_HEADERS = {"X-Internal-Api-Key": "phase3-test-key"}


def _state_with_hash(token_plain):
    return BenchmarkRunState(
        run_id="st",
        owner_token_hash=hash_owner_token(token_plain),
    )


def test_hash_owner_token_is_sha256_hex():
    assert hash_owner_token("tok") == hashlib.sha256(b"tok").hexdigest()


def test_verify_owner_token_correct_wrong_missing():
    st = _state_with_hash("secret")
    assert verify_owner_token(st, "secret") is True
    assert verify_owner_token(st, "wrong") is False
    assert verify_owner_token(st, None) is False


def test_verify_owner_token_missing_hash_is_false():
    st = BenchmarkRunState(run_id="x")
    assert verify_owner_token(st, "anything") is False
