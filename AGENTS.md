# UniRide Repository Agent Instructions

## Mandatory Architecture Context

Before changing `uniride_core` algorithms, `academic_benchmark`, academic statistics, study profiles, solver registries, or production algorithm exposure, read these root specifications in order:

1. `ACADEMIC_STUDY_UNIFICATION_DESIGN.md` — authoritative migration, ownership, evidence, protocol, and work-package specification.
2. `ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md` — fixed-budget accounting, seed provenance, algorithm identity, and fair-result contract.
3. `CANONICAL_THREE_OPT_DESIGN.md` — canonical symmetric TSP and directed ATSP 3-opt semantics.

Also consult `CURRENT_ARCHITECTURE.md`, `ACTIVE_ROADMAP.md`, and `UniRide_Ultimate_Audit.md` for repository-wide context.

If documents conflict, use this precedence:

1. verified live code and passing tests;
2. `ACADEMIC_STUDY_UNIFICATION_DESIGN.md`;
3. the fairness and canonical 3-opt specifications;
4. current master architecture and roadmap documents;
5. archived or historical material.

Do not treat archived reports, generated results, old paper claims, or comments as verified truth.

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
- Require exact file/line evidence and separate confirmed findings from assumptions.
- Preserve unrelated dirty-tree changes.
- Never pull directly into a rescue checkout or overwrite uncommitted work.
