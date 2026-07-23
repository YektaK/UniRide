# Task 7 YAEM boundary hardening report

## Scope

Changed only `academic_benchmark/tests/test_yaem_quarantine_boundary.py` plus this required report. No production code, package configuration, archive contents, manifest, or dependencies were changed.

## Test-first evidence

Added helper-level regression coverage before helper implementation. The shared interpreter RED run reported `3 failed, 8 passed`; each failure was the expected missing-helper `NameError` for `_import_violations`, `_patterns_expose_quarantined_packages`, and `_is_historical_archive_file`.

## Guard changes

- AST import checks now recognize direct imports, aliases, `from academic_benchmark import yaem2026`, relative imports resolved from the scanned path, and legacy archive namespaces.
- Discovery reads configured setuptools include patterns once; setuptools discovery uses them, while fallback validates the same patterns. A direct regression proves `archive*` is rejected.
- Historical inventory excludes only root-relative metadata. Sensitive scanning includes every archive file, including the root manifest.

## Verification

All commands used `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe`.

- Focused guard: 11 passed in 1.42s.
- Architecture guard: 2 passed in 1.65s.
- Package A: 78 passed in 12.92s.
- Full academic suite: 406 passed in 40.44s.