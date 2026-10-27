# `sota_common` Legacy Code Quarantine

Status: historical archive; not executable code

This directory preserves the tracked bytes formerly located at
`uniride_core/algorithms/sota_common` (nine files: acceptance criteria, destroy
and repair operators, diversity controller, multi-layer local search,
multi-start initializer, penalty manager and a smoke entry point). It is
excluded from active packages, imports, benchmark execution, analysis, and
current reports.

## Why it was archived

- No active solver imported it. The only importers were nine re-export shims
  under `optimizer_api/strategies/sota_common/` and two compatibility tests;
  all three were removed with this archive (audit L3-e, L3-i; plan MT6F-01).
- Production SOTA solvers (E2BSO and the others) use
  `uniride_core/algorithms/sota_tsp/`, not this package.
- Its `_layer_3opt` in `multi_layer_ls.py` reverses one segment, which is a
  2-opt, not the canonical 3-opt neighbourhood of
  `CANONICAL_THREE_OPT_DESIGN.md`. Several of its stopping rules read the wall
  clock, so they are not budget-governed.
- `PenaltyManager` had no other definition or user.

## Classification

Every file is `REFERENCE_ONLY`: it may explain design history but cannot support
numerical claims, and no result was ever produced from it by an active study.

## Permitted use

Use this archive only for provenance and design-history review. Do not import its
Python modules, execute its smoke entry point, or relabel any of its moves as
canonical 3-opt. Reviving an idea needs the canonical algorithm contract in
`uniride_core` and the fixed-budget accounting of the fairness protocol.

`manifest.json` records the original path, archived path, byte size, SHA-256,
and evidence classification for each archived file. Verify it with
`python -m academic_benchmark.archive_manifest verify --repo-root . --manifest archive/uniride_core/sota_common_legacy/manifest.json`.
