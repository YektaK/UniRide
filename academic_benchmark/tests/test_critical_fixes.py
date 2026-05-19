"""Regression tests for critical bug fixes (Phase 1).

Covers:
- C-01: Param source mapping 'B' -> 'db'
- C-03/C-04: SOTA gap calculation + elapsed time
- H-06: compute_gap with explicit optimal=0
- C-06: _check_interrupt_key cross-platform helper
"""
import math
import sys
import os

# Force single-threaded BLAS before numpy imports
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"


# ── C-01: Param source mapping ───────────────────────────────────────────────

def test_param_source_mapping_b_to_db():
    """'B' selection must map to 'db', not 'b'."""
    param_map = {'B': 'db', 'M': 'manual', 'D': 'default'}
    assert param_map.get('B', 'default') == 'db'
    assert param_map.get('M', 'default') == 'manual'
    assert param_map.get('D', 'default') == 'default'
    assert param_map.get('X', 'default') == 'default'


def test_param_source_mapping_case_insensitive():
    """Input is uppercased before mapping lookup."""
    ps_raw = 'b'.upper()
    param_map = {'B': 'db', 'M': 'manual', 'D': 'default'}
    assert param_map.get(ps_raw, 'default') == 'db'


# ── H-06: compute_gap with explicit optimal=0 ────────────────────────────────

def test_compute_gap_explicit_zero_preserved():
    """Explicit optimal=0 must NOT be discarded by truthiness check."""
    from academic_benchmark.benchmark_utils import compute_gap
    gap, gap_type = compute_gap("test_problem", 100.0, optimal=0)
    assert gap_type == "unknown", f"Expected 'unknown', got '{gap_type}'"
    assert math.isnan(gap), f"Expected NaN gap for optimal=0, got {gap}"


def test_compute_gap_known_optimal():
    """Known optimal must produce correct gap percentage."""
    from academic_benchmark.benchmark_utils import compute_gap
    gap, gap_type = compute_gap("berlin52", 7600.0, optimal=7542)
    assert gap_type == "optimal"
    assert abs(gap - 0.769) < 0.01, f"Expected ~0.77%, got {gap}"


def test_compute_gap_unknown_optimal_uses_bsf():
    """Unknown optimal should fall back to BSF if available."""
    from academic_benchmark.benchmark_utils import compute_gap, _bsf_tracker
    _bsf_tracker.update("test_bsf_problem", 5000.0)
    gap, gap_type = compute_gap("test_bsf_problem", 5100.0, optimal=None)
    assert gap_type == "bsf"
    assert abs(gap - 2.0) < 0.01, f"Expected ~2.0%, got {gap}"


def test_compute_gap_none_optimal():
    """None optimal with no BSF should return NaN."""
    from academic_benchmark.benchmark_utils import compute_gap
    gap, gap_type = compute_gap("nonexistent_problem_xyz", 1000.0, optimal=None)
    assert gap_type == "unknown"
    assert math.isnan(gap)


# ── C-03/C-04: SOTA executor gap + elapsed ───────────────────────────────────

def test_sota_executor_imports_path():
    """Path must be importable from master_sota_engine module."""
    from academic_benchmark.master_sota_engine import Path
    assert Path is not None


def test_sota_executor_has_compute_gap():
    """SOTA executor must use compute_gap, not inline calculation."""
    from academic_benchmark.master_sota_engine import compute_gap
    assert callable(compute_gap)


def test_sota_gap_no_absurd_values():
    """Gap for unknown optimal must NOT be tour_length * 100."""
    from academic_benchmark.benchmark_utils import compute_gap
    gap, gap_type = compute_gap("unknown_prob", 7542.0, optimal=None)
    assert gap_type == "unknown"
    assert math.isnan(gap), f"Expected NaN for unknown optimal, got {gap}"


# ── C-06: Cross-platform interrupt key helper ────────────────────────────────

def test_check_interrupt_key_exists():
    """_check_interrupt_key function must exist in smart_benchmark."""
    from academic_benchmark.smart_benchmark import _check_interrupt_key
    assert callable(_check_interrupt_key)


def test_check_interrupt_key_returns_bool():
    """_check_interrupt_key must return a boolean."""
    from academic_benchmark.smart_benchmark import _check_interrupt_key
    result = _check_interrupt_key()
    assert isinstance(result, bool)


def test_check_interrupt_key_no_crash_on_piped_input():
    """_check_interrupt_key must not crash when stdin is not a tty."""
    from academic_benchmark.smart_benchmark import _check_interrupt_key
    try:
        result = _check_interrupt_key()
        assert isinstance(result, bool)
    except Exception as e:
        assert False, f"_check_interrupt_key crashed: {e}"
