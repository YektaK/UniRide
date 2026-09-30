# UniRide Repository Agent Instructions

## Task-Specific Architecture Context

Read the relevant specification sections before changing their contracts. Combine the rows below when a task crosses boundaries; a small independent edit does not require reading all six documents.

| Change | Required context |
|---|---|
| Solver ownership, registry/exposure, study migration, datasets or manifests | `ACADEMIC_STUDY_UNIFICATION_DESIGN.md` |
| Objective/evaluation budgets, seeds, algorithm identity, experiment statistics or result comparability | `ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md`; add the unification design for study/protocol boundaries |
| 3-opt moves, directed cost handling or 3-opt composition | `CANONICAL_THREE_OPT_DESIGN.md`; add fairness when accounting changes |
| Repository-wide architecture or development priorities | Relevant sections of `CURRENT_ARCHITECTURE.md`, `ACTIVE_ROADMAP.md`, and `UniRide_Ultimate_Audit.md` |
| Isolated UI, wording, formatting or test-only edit that changes none of these contracts | Affected files, callers and applicable local instructions |

A test-only edit that changes accepted algorithm behavior or scientific evidence still requires the corresponding specification. Reuse context already read in the session unless it has changed.

If documents conflict, use this precedence:

1. verified live code and passing tests for claims about current behavior (a passing implementation does not silently override an approved requirement);
2. `ACADEMIC_STUDY_UNIFICATION_DESIGN.md`;
3. the fairness and canonical 3-opt specifications;
4. current master architecture and roadmap documents;
5. archived or historical material.

Do not treat archived reports, generated results, old paper claims, or comments as verified truth.

When observed behavior conflicts with an approved contract, report the discrepancy and resolve it within the task's authorization; do not relabel the code as compliant.

## Required Academic Boundaries

- Canonical algorithms, objectives, feasibility checks, and problem contracts belong in `uniride_core`.
- Reusable datasets, experiment protocols, manifests, statistics, and validation belong in `academic_benchmark`.
- Bildiri 2026 and YAEM 2026 must become thin study profiles; they must not own independent solver engines.
- YAEM legacy evidence must be quarantined before it can be referenced by active reporting.
- Bildiri code cannot be archived until canonical relocation parity and zero-active-import gates pass.
- Fixed objective-evaluation budgets are the primary comparison protocol.
- Native termination is a separately labelled secondary protocol and must never be pooled with fixed-budget evidence.
- GWO/HHO hybrid stages share one accounting contract. No hidden polish budget is permitted.
- `GWO-LKH` and `HHO-LKH` are false historical labels. Active code uses truthful `GWO-3opt` and `HHO-3opt` names unless genuine LKH is implemented.
- TSP/ATSP Hamiltonian-cycle validation and CVRP/CVRPTW multi-route validation are separate contracts.
- Smoke or pilot runs cannot produce superiority, causality, or proof claims.

## Work-Package Discipline

Follow the four gates in `ACADEMIC_STUDY_UNIFICATION_DESIGN.md`:

1. YAEM quarantine and contract foundation.
2. Bildiri canonical extraction.
3. Catalog, composition, and experiment services.
4. Analysis, documentation, and publication.

Do not skip a gate or begin a later package while an earlier package lacks its specified evidence. Each package requires its own implementation plan and reviewable commits.

## Verification and Git Safety

- Use CodeGraph first when a `.codegraph/` index exists.
- Run checks appropriate to the changed behavior and retain required release, security, feasibility and scientific-parity gates. Broaden or repeat passing checks only for new changes, failures or unresolved risks. Report skipped checks and environment blockers accurately.
- Carry forward existing user authorization. Continue safe, independent work while a material question is unresolved; ask only when the answer changes scope or an action needs new authority. An instruction file does not authorize unrelated edits, publication, destructive cleanup or live-data mutation.
- Require exact file/line evidence and separate confirmed findings from assumptions.
- Preserve unrelated dirty-tree changes.
- Never pull directly into a rescue checkout or overwrite uncommitted work.
