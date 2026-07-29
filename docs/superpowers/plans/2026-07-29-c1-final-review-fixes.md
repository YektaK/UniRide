# Package C1 Final Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Fail closed at CLI and Smart worker boundaries for ungoverned C1 algorithms and persist complete preflight decision provenance without changing solver behavior or legacy non-C1 compatibility.

**Architecture:** Classify worker algorithm IDs before any registry lookup and raise `ExecutorUnavailableError` when a catalog-governed task lacks a valid `GovernedExecutionRequest`. Serialize each actual `PreflightDecision` through one helper, add the primitive metadata to existing CLI dictionaries or Smart `RunResult` instances, and merge it into existing persistence metadata.

**Tech Stack:** Python 3, dataclasses, pytest, SQLite benchmark persistence.

## Global Constraints

- Preserve six-field CLI tuples and request-less Smart tasks for genuine `NON_C1_ROUTING` algorithms.
- Do not change solver equations, evaluation accounting, seeds, termination, capability claims/evidence, manifest schemas, study profiles, production API registry exposure, dependencies, databases, archives, frontend, or generated benchmark artifacts.
- Do not run the whole suite; verify only the focused Package C1 gates and `git diff --check` in `.venv-jit`.

---

### Task 1: Fail-closed worker entrypoints

**Files:**
- Modify: `academic_benchmark/cli_engine.py`
- Modify: `academic_benchmark/smart_benchmark.py`
- Test: `academic_benchmark/tests/test_smart_benchmark_preflight.py`

**Interfaces:**
- Consumes: `classify_academic_algorithm_id(id, RESOLVER_GOVERNED_IDENTIFIERS)` and `GovernedExecutionRequest`.
- Produces: worker-boundary `ExecutorUnavailableError` before `list_algorithms()` or `get_executor()` for ungoverned C1 tasks.

- [x] Add direct CLI and Smart tests whose registry methods explode and whose governed tasks omit requests.
- [x] Run those node IDs and record the expected RED failures.
- [x] Add the minimal classification/type guards before direct fallback.
- [x] Re-run the boundary tests and existing non-C1 compatibility tests for GREEN.

### Task 2: Decision provenance transport and persistence

**Files:**
- Modify: `academic_benchmark/core/execution_gateway.py`
- Modify: `academic_benchmark/cli_engine.py`
- Modify: `academic_benchmark/smart_benchmark.py`
- Modify: `academic_benchmark/fair_pilot.py`
- Test: `academic_benchmark/tests/test_smart_benchmark_preflight.py`
- Test: `academic_benchmark/tests/test_algorithm_execution_gateway.py`
- Test: `academic_benchmark/tests/test_fair_pilot_cli.py`

**Interfaces:**
- Consumes: `PreflightDecision` from `execute_preflighted(...)`.
- Produces: `serialize_preflight_decision(decision) -> dict[str, object]` with requested/canonical IDs, backend policy/profile, fallback state/reason, executor ID, and evidence IDs.

- [x] Add serializer, CLI alias, and Smart PREFER_NUMBA persistence tests.
- [x] Run those node IDs and record the expected RED failures.
- [x] Implement the serializer; reuse it from fair pilot; attach primitive metadata to CLI dictionaries and Smart results; merge it into existing database metadata.
- [x] Re-run focused tests for GREEN and confirm alias and fallback provenance come from the decision.

### Task 3: Verification, report, and commit

**Files:**
- Create: `.superpowers/sdd/task-c1-final-review-fixes-report.md`

**Interfaces:**
- Consumes: RED/GREEN command outputs and final Git diff.
- Produces: the required scoped evidence report and one local commit.

- [x] Run the required focused `.venv-jit` pytest files and directly affected CLI/persistence/fair-pilot tests.
- [x] Run resolver/preflight boundary tests and `git diff --check`.
- [x] Write the report with exact commands/results, files changed, compatibility decisions, remaining risks, and the commit hash workflow.
- [x] Inspect the scoped diff, commit, then record the containing commit as the report identity.
## Execution note

The controller expanded verification to the complete academic suite after focused runs exposed stale compatibility fixtures and the independent reviewer identified shared CSV-header compatibility. The final gate passed 786 tests; no benchmark experiment or generated result artifact was produced.
