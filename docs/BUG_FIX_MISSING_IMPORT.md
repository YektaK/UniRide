# 🐛 Bug Fix: Missing Import in main.py - DEFAULT_TRAVEL_FALLBACK_MINUTES

**Date:** 13 Nisan 2026, 20:45  
**Priority:** 🔴 CRITICAL - Runtime Error  
**Status:** FIXED (Commit 9e8a022)  
**Related:** Commit 6010796 (refactor: Consolidate magic numbers)

---

## 🚨 The Bug

### What Happened
Commit `6010796` refactored magic number `15.0` to `DEFAULT_TRAVEL_FALLBACK_MINUTES` constant.

**Lines modified in `optimizer_api/main.py`:**
- Line 230: `distance_matrix.get(from_loc, {}).get(to_loc, DEFAULT_TRAVEL_FALLBACK_MINUTES)`
- Line 264: `distance_matrix.get(from_loc, {}).get(to_loc, DEFAULT_TRAVEL_FALLBACK_MINUTES)`

**Missing:** The import statement!

### The Error
When `calculate_time_windows()` is called with backward/forward scheduling:

```python
# Runtime Error:
NameError: name 'DEFAULT_TRAVEL_FALLBACK_MINUTES' is not defined

# Stack trace would show:
File "optimizer_api/main.py", line 230, in calculate_time_windows
    travel_time = distance_matrix.get(...).get(to_loc, DEFAULT_TRAVEL_FALLBACK_MINUTES)
NameError: name 'DEFAULT_TRAVEL_FALLBACK_MINUTES' is not defined
```

### When It Occurs
- Any request to `/api/v1/extract-time-windows` endpoint
- Using backward scheduling (geliş)
- Using forward scheduling (gidiş)
- With missing distance matrix entries (fallback triggered)

---

## ✅ The Fix

### Commit 9e8a022
Added missing import to `optimizer_api/main.py` line 44:

```python
# BEFORE (❌ BROKEN)
from utils.resource_profiler import ResourceProfiler
from utils.time_window_extractor import TimeWindowExtractor
from benchmark_runner import BenchmarkRunner, BenchmarkProblem, AlgorithmConfig

# AFTER (✅ FIXED)
from utils.resource_profiler import ResourceProfiler
from utils.time_window_extractor import TimeWindowExtractor
from utils.constants import DEFAULT_TRAVEL_FALLBACK_MINUTES  # ← ADDED
from benchmark_runner import BenchmarkRunner, BenchmarkProblem, AlgorithmConfig
```

### Impact
- ✅ Lines 230 & 264 now have defined reference to `DEFAULT_TRAVEL_FALLBACK_MINUTES`
- ✅ No more NameError
- ✅ Backward/forward scheduling works correctly
- ✅ Fallback time properly sourced from centralized constant

---

## 📊 Root Cause Analysis

### Why It Happened
Commit `6010796` was part of larger refactoring:
1. ✅ Created `utils/constants.py` with `DEFAULT_TRAVEL_FALLBACK_MINUTES = 15.0`
2. ✅ Updated `main.py` lines 230 & 264 to use constant
3. ❌ **MISSED:** Adding import statement in `main.py`

### Quality Gate Failure
- No pre-commit hook to check undefined names
- `mypy` type checking not catching undefined variables in dict fallback
- Testing not run on time window endpoints after refactoring

---

## 🔍 Prevention

### What Caused This
- Large refactoring across multiple files
- Easy to forget imports when centralizing constants
- No static analysis validation before commit

### How to Prevent
1. **Pre-commit hook:** Check for undefined names
   ```bash
   # Check for undefined symbols
   python -m pylint optimizer_api/main.py
   ```

2. **mypy with --strict:**
   ```bash
   mypy --strict optimizer_api/main.py
   ```

3. **Test the affected code:**
   ```bash
   pytest optimizer_api/test_api.py::test_calculate_time_windows
   ```

---

## 📋 Summary

| Item | Details |
|------|---------|
| **Bug Type** | Missing import (NameError) |
| **Severity** | 🔴 CRITICAL (runtime error) |
| **File** | `optimizer_api/main.py` |
| **Fix Commit** | `9e8a022` |
| **Release Impact** | Breaks time window calculation endpoints |
| **Test Requirement** | Yes - endpoints would fail |

---

## ✨ Lessons Learned

1. **Large refactorings need thorough testing**
   - Changed constant across multiple files
   - Need to verify all uses are properly imported

2. **Centralized constants are good BUT need validation**
   - Benefits: Single source of truth ✅
   - Risk: Forget imports 🐛
   - Solution: Automated checks ✅

3. **Static analysis is essential**
   - `mypy`, `pylint`, `flake8` catch these issues
   - Should be pre-commit requirement

---

**Status:** RESOLVED ✅  
**Commit:** 9e8a022  
**All fixes:** import added, no behavior changes
