# Independent fact-check of the updated method note

**Verdict: DUZELT**

The draft contains a contradicted busy-peak start, incomplete source support, and untagged factual statements. The main sensitivity, vehicle-count, Pareto and wave-census numbers otherwise match the checked archives. No draft text was edited.

## Checked material and scope

- Audit date: 2026-10-10 (Europe/Istanbul).
- Draft: `docs/paper/DAILY_STUDENT_TRANSPORT_PLANNING_METHOD.md` at `89cfd7c5cd23a04ee5d2e720dd4d2c844a28b4a2`, branch `docs/method-note-2026-10-10`. Draft line numbers below always refer to that commit.
- Comparison only: the same path on WIP, `f7b8570d3c133a5c334e68c3271ed5366d07a65f`, the draft commit's parent. `git diff --name-only f7b8570 89cfd7c` lists only the method note; ordinary cited source blobs are unchanged.
- Repository `AGENTS.md`, the user-supplied instructions, and the untracked writing brief `docs/CODEX_TASK_METHOD_NOTE_UPDATE.md` in the main checkout were read. The decision log and cited designs/archives were checked at the pinned commit.
- Output worktree: `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.claude\worktrees\method-factcheck`; branch `docs/method-note-factcheck`, created from WIP.
- Every source tag was enumerated in order of appearance and checked using `git show 89cfd7c:<source-path>`. There are 278 tag occurrences, 39 distinct cited paths and 38 paths present in the pinned tree. The missing path was additionally inspected at its declared secondary commit, `d7aab08`; that check does not waive the requested pinned-commit requirement.

Adjacent complementary tags are evaluated against their natural clauses, with collective coverage required for the factual sentence. Table headers and section headings are read as context; a correct row is not called WRONG_LINE merely because its header is outside the cited range. WRONG_LINE is reserved for support elsewhere in the same file. No uncertainty is counted as OK.

For the untagged check, changed sections means changed main sections, including retained factual sentences in §§2, 4 and 5. Thus 55 carried-over sentences are listed, in addition to 5 changed header/provenance sentences. Pure definitions, the normative instruction to record provenance, proposed research directions, section numbering, navigational link lists and the retained bibliographic entry are excluded. The linked Prins sentence in the body remains a factual sentence without an `[S: ...]` tag. This section-level scope is broader than the writing brief's new-or-changed-sentence rule.

## Counts

| Verdict | Count | Unit |
|---|---:|---|
| OK | 263 | Source tag occurrences |
| WRONG_LINE | 4 | Source tag occurrences |
| PARTIAL | 6 | Source tag occurrences |
| UNSUPPORTED | 4 | Source tag occurrences |
| CONTRADICTED | 1 | Source tag occurrences |
| UNTAGGED | 60 | Factual sentences, separate from the 278 tags |

Tag verdicts sum to 278. The 4 UNSUPPORTED tags attach to two sentences and cite one absent path; they are not four independent invented scientific claims. The 60 UNTAGGED sentences include 55 carried-over statements and 5 changed metadata/provenance statements.

## duzeltmeler

Only factual/source corrections are proposed below. Each item identifies the draft line, defect, evidence and exact correction. A PARTIAL item identifies the unsupported portion, rather than rejecting the supported part.

1. **Draft line 21 — UNSUPPORTED — tags 12, 13.** The source path is absent at 89cfd7c. The declared secondary commit does support fractional seconds, but cannot satisfy the requested pinned-source audit.

    - Evidence: `89cfd7c tree: path absent; d7aab08:docs/research/ARCHITECTURE_RESEARCH_2026-10.md:71 (secondary only)`.
    - Exact correction: Replace the separate research-note sentence and its two commit-prefixed tags with `[EKSİK: pending fractional-second research report is outside the checked repository snapshot]`.

2. **Draft line 64 — PARTIAL — tag 29.** The tagged default dictionary says seed=None, but does not define the helper or its effective value 42. The interpretation cell needs the seed resolver.

    - Evidence: `optimizer_api/strategies/ga_split_strategy.py:66; optimizer_api/strategies/seed_utils.py:7-17`.
    - Exact correction: Append `[S: optimizer_api/strategies/seed_utils.py:7-17]` to the source cell.

3. **Draft line 66 — PARTIAL — tag 30.** Source supports the constructor overlay, but cannot establish that the method-note author did not query an active deployment.

    - Evidence: `optimizer_api/strategies/ga_split_strategy.py:72-79`.
    - Exact correction: The constructor can overlay promoted parameters on the defaults. [S: optimizer_api/strategies/ga_split_strategy.py:72-79] [EKSİK: method-note deployment-inspection record]

4. **Draft line 66 — PARTIAL — tag 33.** The cited design specifies matching inputs/configuration and archiving outputs, but does not explicitly specify demand ordering. A seed-plus-order claim needs the GA initialization path.

    - Evidence: `docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:251-258; uniride_core/algorithms/ga_split_engine.py:79-92`.
    - Exact correction: Append `[S: uniride_core/algorithms/ga_split_engine.py:79-92]` after the existing tag, retaining the stated reproducibility limit.

5. **Draft line 94 — PARTIAL — tag 40.** The preflight requires occurrence sets and other inputs to match, but does not specify preserving passenger ordering.

    - Evidence: `docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:251-255; uniride_core/algorithms/ga_split_engine.py:79-92`.
    - Exact correction: Append `[S: uniride_core/algorithms/ga_split_engine.py:79-92]` to cover the ordering-sensitive initialization, or replace `passenger ordering` with `occurrence IDs per wave`.

6. **Draft line 98 — PARTIAL — tag 47.** V01/V02 support assignment-witness limits and heuristic routes; they do not literally state the separate assertion about routing-search failure proving infeasibility.

    - Evidence: `docs/DECISION_LOG.md:197-204`.
    - Exact correction: Indeterminate assignments must remain visible; witness counts must not be reported as optima, and route generation remains heuristic. [S: docs/DECISION_LOG.md:197-198]

7. **Draft line 144 — CONTRADICTED — tag 107.** Friday R=70 busy-peak start is 13:16, not 13:15. Direct source quote: `13:16-13:33`.

    - Evidence: `docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:279`.
    - Exact correction: Thursday's busy-peak windows at R = 50, 70 and 90 are 12:39–12:55, 13:35–13:53 and 13:35–13:52, respectively; Friday's at R = 50, 60, 70 and 90 are 13:15–13:35, 13:15–13:33, 13:16–13:33 and 13:15–13:33. [S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:268-284]

8. **Draft line 152 — WRONG_LINE — tag 132.** The tag selects only the R=50 A row for a claim about all four R values.

    - Evidence: `docs/paper/results/week-2026-10-05-fleet/scenario_weekly.csv:2,6,10,14`.
    - Exact correction: [S: docs/paper/results/week-2026-10-05-fleet/scenario_weekly.csv:2-14]

9. **Draft line 210 — WRONG_LINE — tag 222.** Line9 specifies menu approximation and tested L values; the R grid is stated at34.

    - Evidence: `docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:9,34`.
    - Exact correction: [S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:9-34]

10. **Draft line 212 — WRONG_LINE — tag 230.** Lines44-46 contain a blank line, the Work-Package Discipline heading, and another blank line. The two protocol requirements are38-39.

    - Evidence: `AGENTS.md:38-39`.
    - Exact correction: [S: AGENTS.md:38-39]

11. **Draft line 218 — WRONG_LINE — tag 245.** Line43 gives menu-conditional minimum scope, but does not identify the executed typed-fleet scenarios or their Sw/So pools.

    - Evidence: `docs/paper/results/week-2026-10-05-fleet/README.md:13,24-29,43`.
    - Exact correction: [S: docs/paper/results/week-2026-10-05-fleet/README.md:13-43]

12. **Draft line 228 — PARTIAL — tag 266.** The source records 28 students in a D0 inventory, but does not establish a study-specific unique-student census. Remove the unverified census characterization.

    - Evidence: `docs/DEMO_ROADMAP_2026-10-04.md:276`.
    - Exact correction: Earlier planning notes reported 28 students in a D0 read-only inventory dated 2026-10-04. [S: docs/DEMO_ROADMAP_2026-10-04.md:276]

13. **Draft line 236 — UNSUPPORTED — tags 277, 278.** The declared research-note blob exists only at secondary commit d7aab08; the source path is absent in 89cfd7c.

    - Evidence: `89cfd7c tree: path absent; d7aab08:docs/research/ARCHITECTURE_RESEARCH_2026-10.md:255 (secondary only)`.
    - Exact correction: Replace the commit-prefixed-citation explanation and its two tags with `[EKSİK: pending research-note provenance is outside the checked repository snapshot]`.

For the following UNTAGGED items, the quoted sentence identifies the exact occurrence. Unless replacement text is specified, the exact correction is to append the supplied source tag(s) immediately after that sentence; retain the sentence itself. The evidence is the same source range at `89cfd7c`. These are missing-citation findings, not assertions that all the sentences are false.

14. **Draft line 3 — UNTAGGED — U56 (changed metadata).** Updated date metadata has no source tag.

    - Sentence: Method note for co-authors — 10 October 2026.
    - Evidence: `Git commit 89cfd7c metadata is dated 2026-10-10; no committed independent review-date record is tagged.`.
    - Exact correction: [EKSİK: dated method-note review provenance file]

15. **Draft line 3 — UNTAGGED — U57 (changed metadata).** Baseline/process metadata has no source tag; Git confirms the parent, but does not record the author's command history.

    - Sentence: Checked code baseline: `f7b8570` (`git rev-parse --short HEAD` after merging `WIP`).
    - Evidence: `git show -s --format=%P 89cfd7c returns f7b8570d3c133a5c334e68c3271ed5366d07a65f; the diff changes only the method note.`.
    - Exact correction: Checked code baseline: `f7b8570`. [EKSİK: committed method-note review provenance for this baseline]

16. **Draft line 15 — UNTAGGED — U01 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Planning uses a stored, directed matrix derived from road-network routing.
    - Evidence: `docs/DECISION_LOG.md:95-98`.
    - Exact correction: [S: docs/DECISION_LOG.md:95-98]

17. **Draft line 15 — UNTAGGED — U02 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: In general c(i,j) differs from c(j,i).
    - Evidence: `docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:20`.
    - Exact correction: [S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:20]

18. **Draft line 15 — UNTAGGED — U03 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Straight-line distances and coordinate-based travel-time approximations are not used in this operational method.
    - Evidence: `docs/DECISION_LOG.md:97-98`.
    - Exact correction: [S: docs/DECISION_LOG.md:97-98]

19. **Draft line 15 — UNTAGGED — U04 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Missing or invalid required arcs prevent certification rather than being silently assigned zero travel time.
    - Evidence: `optimizer_api/verification/response_certifier.py:348-355`.
    - Exact correction: [S: optimizer_api/verification/response_certifier.py:348-355]

20. **Draft line 17 — UNTAGGED — U05 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: The matrix is not assumed to satisfy the triangle inequality.
    - Evidence: `docs/DECISION_LOG.md:167-168`.
    - Exact correction: [S: docs/DECISION_LOG.md:167-168]

21. **Draft line 17 — UNTAGGED — U06 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: A direct campus-to-stop time is therefore not a certified lower bound on a route reaching that stop through other stops.
    - Evidence: `docs/DECISION_LOG.md:167-168`.
    - Exact correction: [S: docs/DECISION_LOG.md:167-168]

22. **Draft line 17 — UNTAGGED — U07 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: A wave cannot be rejected solely because a direct arc exceeds its ride limit.
    - Evidence: `docs/DECISION_LOG.md:167-169`.
    - Exact correction: [S: docs/DECISION_LOG.md:167-169]

23. **Draft line 17 — UNTAGGED — U08 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Different passenger occurrences at one physical location may have a zero connecting hop; this does not justify zero travel between different locations.
    - Evidence: `optimizer_api/verification/response_certifier.py:125-127; optimizer_api/verification/response_certifier.py:348-355`.
    - Exact correction: [S: optimizer_api/verification/response_certifier.py:125-127] [S: optimizer_api/verification/response_certifier.py:348-355]

24. **Draft line 19 — UNTAGGED — U09 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: A matrix snapshot is captured before solving.
    - Evidence: `src/services/daily-plan-run.ts:522-539`.
    - Exact correction: [S: src/services/daily-plan-run.ts:522-539]

25. **Draft line 19 — UNTAGGED — U10 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Wave requests are bound to its identity, and route verification uses the captured authoritative arc values.
    - Evidence: `src/services/daily-plan-run.ts:522-539; optimizer_api/verification/response_certifier.py:348-355`.
    - Exact correction: [S: src/services/daily-plan-run.ts:522-539] [S: optimizer_api/verification/response_certifier.py:348-355]

26. **Draft line 19 — UNTAGGED — U11 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: The matrix represents collection conditions, not necessarily current traffic, loading delays, or accessibility conditions.
    - Evidence: `docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:185-189`.
    - Exact correction: [S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:185-189]

27. **Draft line 44 — UNTAGGED — U12 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Each wave uses a genetic algorithm (GA) over a permutation of passenger occurrences, called a giant tour.
    - Evidence: `src/services/daily-plan-run.ts:526-554; uniride_core/algorithms/ga_split_engine.py:97-120`.
    - Exact correction: [S: src/services/daily-plan-run.ts:526-554] [S: uniride_core/algorithms/ga_split_engine.py:97-120]

28. **Draft line 44 — UNTAGGED — U13 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: A split decoder partitions consecutive subsequences into depot-closed vehicle routes.
    - Evidence: `uniride_core/algorithms/string_split_decoder.py:324-367; uniride_core/algorithms/string_split_decoder.py:249-269`.
    - Exact correction: [S: uniride_core/algorithms/string_split_decoder.py:324-367] [S: uniride_core/algorithms/string_split_decoder.py:249-269]

29. **Draft line 44 — UNTAGGED — U14 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: This follows the route-first, cluster-second representation associated with [Prins (2004)](https://doi.org/10.1016/S0305-0548(03)00158-8).
    - Evidence: `optimizer_api/strategies/ga_split_strategy.py:44-55`.
    - Exact correction: [S: optimizer_api/strategies/ga_split_strategy.py:44-55]

30. **Draft line 44 — UNTAGGED — U15 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: The present implementation has its own constraints and acceptance checks; no comparative performance claim is inferred from the reference.
    - Evidence: `uniride_core/algorithms/string_split_decoder.py:337-367; optimizer_api/verification/response_certifier.py:333-358`.
    - Exact correction: [S: uniride_core/algorithms/string_split_decoder.py:337-367] [S: optimizer_api/verification/response_certifier.py:333-358]

31. **Draft line 46 — UNTAGGED — U16 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Initialization combines randomized permutations and a nearest-neighbour tour.
    - Evidence: `uniride_core/algorithms/ga_split_engine.py:71-94`.
    - Exact correction: [S: uniride_core/algorithms/ga_split_engine.py:71-94]

32. **Draft line 46 — UNTAGGED — U17 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Tournament selection, order crossover, mutation, and elitism generate new candidates.
    - Evidence: `uniride_core/algorithms/ga_split_engine.py:251-293`.
    - Exact correction: [S: uniride_core/algorithms/ga_split_engine.py:251-293]

33. **Draft line 46 — UNTAGGED — U18 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Periodic local search modifies a selected giant tour, which is then decoded and evaluated again.
    - Evidence: `uniride_core/algorithms/ga_split_engine.py:352-370`.
    - Exact correction: [S: uniride_core/algorithms/ga_split_engine.py:352-370]

34. **Draft line 46 — UNTAGGED — U19 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: The outer ranking prioritizes feasibility, then route count, then total travel time.
    - Evidence: `docs/DECISION_LOG.md:173`.
    - Exact correction: [S: docs/DECISION_LOG.md:173]

35. **Draft line 48 — UNTAGGED — U20 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: The decoder enumerates feasible contiguous segments under both passenger capacities and the tour and ride limits.
    - Evidence: `uniride_core/algorithms/string_split_decoder.py:324-367`.
    - Exact correction: [S: uniride_core/algorithms/string_split_decoder.py:324-367]

36. **Draft line 48 — UNTAGGED — U21 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Dynamic programming chooses a minimum-travel-time partition for a fixed permutation, preferring partitions without violations.
    - Evidence: `uniride_core/algorithms/string_split_decoder.py:202-228`.
    - Exact correction: [S: uniride_core/algorithms/string_split_decoder.py:202-228]

37. **Draft line 48 — UNTAGGED — U22 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: This restricted calculation does not optimize all permutations, and its cost objective differs from the outer GA's route-count priority.
    - Evidence: `uniride_core/algorithms/string_split_decoder.py:190-228; docs/DECISION_LOG.md:173`.
    - Exact correction: [S: uniride_core/algorithms/string_split_decoder.py:190-228] [S: docs/DECISION_LOG.md:173]

38. **Draft line 48 — UNTAGGED — U23 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Neither a decoded partition nor the final wave result proves globally minimum route count.
    - Evidence: `uniride_core/algorithms/string_split_decoder.py:202-228; uniride_core/algorithms/ga_split_engine.py:318-379`.
    - Exact correction: [S: uniride_core/algorithms/string_split_decoder.py:202-228] [S: uniride_core/algorithms/ga_split_engine.py:318-379]

39. **Draft line 48 — UNTAGGED — U24 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: With nonmetric travel, a duration violation also does not imply that every longer segment violates the limit; alternatives must still be examined.
    - Evidence: `uniride_core/algorithms/string_split_decoder.py:350-358; docs/DECISION_LOG.md:167-168`.
    - Exact correction: [S: uniride_core/algorithms/string_split_decoder.py:350-358] [S: docs/DECISION_LOG.md:167-168]

40. **Draft line 68 — UNTAGGED — U25 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: The defaults were not demonstrated to be tuned for this campus problem.
    - Evidence: `docs/DECISION_LOG.md:407`.
    - Exact correction: [S: docs/DECISION_LOG.md:407]

41. **Draft line 68 — UNTAGGED — U26 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Correctness and feasibility tests do not establish solution quality or comparative superiority.
    - Evidence: `docs/DECISION_LOG.md:90`.
    - Exact correction: [S: docs/DECISION_LOG.md:90]

42. **Draft line 68 — UNTAGGED — U27 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Current termination uses iterations and stagnation; it is not a fixed objective-evaluation-budget experiment.
    - Evidence: `uniride_core/algorithms/ga_split_engine.py:336-379`.
    - Exact correction: [S: uniride_core/algorithms/ga_split_engine.py:336-379]

43. **Draft line 72 — UNTAGGED — U28 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: An independent certificate reconstructs every route using the captured matrix.
    - Evidence: `optimizer_api/verification/response_certifier.py:348-358`.
    - Exact correction: [S: optimizer_api/verification/response_certifier.py:348-358]

44. **Draft line 72 — UNTAGGED — U29 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: It checks required occurrence coverage, continuity, depot closure, passenger counts and capacities, tour duration, and direction-specific ride limits.
    - Evidence: `optimizer_api/verification/response_certifier.py:333-355`.
    - Exact correction: [S: optimizer_api/verification/response_certifier.py:333-355]

45. **Draft line 72 — UNTAGGED — U30 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: A 0.005-minute tolerance per reported arc accommodates two-decimal formatting, with corresponding aggregate formatting checks; it is not extra operational ride allowance.
    - Evidence: `optimizer_api/verification/response_certifier.py:129-140; optimizer_api/verification/response_certifier.py:348-355`.
    - Exact correction: [S: optimizer_api/verification/response_certifier.py:129-140] [S: optimizer_api/verification/response_certifier.py:348-355]

46. **Draft line 72 — UNTAGGED — U31 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Solver-reported durations alone do not establish feasibility.
    - Evidence: `optimizer_api/verification/response_certifier.py:348-355`.
    - Exact correction: [S: optimizer_api/verification/response_certifier.py:348-355]

47. **Draft line 72 — UNTAGGED — U32 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: The preview also checks whether accepted output can form consistent daily route jobs.
    - Evidence: `src/services/dudullu-preview.ts:887-925`.
    - Exact correction: [S: src/services/dudullu-preview.ts:887-925]

48. **Draft line 74 — UNTAGGED — U33 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Only accepted routes proceed to vehicle assignment.
    - Evidence: `src/services/dudullu-preview.ts:911-932`.
    - Exact correction: [S: src/services/dudullu-preview.ts:911-932]

49. **Draft line 74 — UNTAGGED — U34 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: A failed certificate establishes that the returned candidate is unacceptable.
    - Evidence: `src/services/dudullu-preview.ts:918-925`.
    - Exact correction: [S: src/services/dudullu-preview.ts:918-925]

50. **Draft line 74 — UNTAGGED — U35 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Failure to generate a candidate or exhaustion of a search budget does not prove that no feasible routing exists.
    - Evidence: `uniride_core/algorithms/string_split_decoder.py:236-247; uniride_core/algorithms/ga_split_engine.py:318-379`.
    - Exact correction: [S: uniride_core/algorithms/string_split_decoder.py:236-247] [S: uniride_core/algorithms/ga_split_engine.py:318-379]

51. **Draft line 74 — UNTAGGED — U36 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: A feasibility certificate is not an optimality certificate.
    - Evidence: `optimizer_api/verification/response_certifier.py:357-358`.
    - Exact correction: [S: optimizer_api/verification/response_certifier.py:357-358]

52. **Draft line 78 — UNTAGGED — U37 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: A pickup route with duration t and arrival anchor a becomes the interval [a−t, a]; a drop-off route becomes [a, a+t].
    - Evidence: `src/services/dudullu-preview.ts:489-494`.
    - Exact correction: [S: src/services/dudullu-preview.ts:489-494]

53. **Draft line 78 — UNTAGGED — U38 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Intervals outside the service day are rejected.
    - Evidence: `src/services/dudullu-preview.ts:495-502`.
    - Exact correction: [S: src/services/dudullu-preview.ts:495-502]

54. **Draft line 78 — UNTAGGED — U39 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: A vehicle can serve multiple routes if both capacity pools suffice and each next route starts no earlier than the preceding route's end plus its cooldown.
    - Evidence: `src/services/dudullu-preview.ts:623-634`.
    - Exact correction: [S: src/services/dudullu-preview.ts:623-634]

55. **Draft line 80 — UNTAGGED — U40 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Daily assignment searches for the fewest distinct vehicles for these fixed route jobs.
    - Evidence: `src/services/dudullu-preview.ts:829-877`.
    - Exact correction: [S: src/services/dudullu-preview.ts:829-877]

56. **Draft line 80 — UNTAGGED — U41 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: It explores assignments in time order, uses concurrency lower bounds, and avoids equivalent branches for vehicles with matching capacities, cooldowns, and availability.
    - Evidence: `src/services/dudullu-preview.ts:724-742; src/services/dudullu-preview.ts:784-826`.
    - Exact correction: [S: src/services/dudullu-preview.ts:724-742] [S: src/services/dudullu-preview.ts:784-826]

57. **Draft line 80 — UNTAGGED — U42 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: The default budget is 50,000 visited nodes.
    - Evidence: `src/services/dudullu-preview.ts:6; src/services/dudullu-preview.ts:745-748; src/services/dudullu-preview.ts:829-835`.
    - Exact correction: [S: src/services/dudullu-preview.ts:6] [S: src/services/dudullu-preview.ts:745-748] [S: src/services/dudullu-preview.ts:829-835]

58. **Draft line 80 — UNTAGGED — U43 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: A completed search, or a feasible witness meeting a valid lower bound, can prove the minimum for the given routes.
    - Evidence: `src/services/dudullu-preview.ts:829-877; docs/DECISION_LOG.md:197-198`.
    - Exact correction: [S: src/services/dudullu-preview.ts:829-877] [S: docs/DECISION_LOG.md:197-198]

59. **Draft line 80 — UNTAGGED — U44 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: If the budget is exhausted before proof, the result is indeterminate; an available witness gives only an upper bound.
    - Evidence: `src/services/dudullu-preview.ts:829-877; docs/DECISION_LOG.md:197-198`.
    - Exact correction: [S: src/services/dudullu-preview.ts:829-877] [S: docs/DECISION_LOG.md:197-198]

60. **Draft line 80 — UNTAGGED — U45 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Completed failure establishes a shortage for the fixed routes and candidate fleet, not for every alternative routing.
    - Evidence: `src/services/dudullu-preview.ts:866-877; docs/DECISION_LOG.md:203-204`.
    - Exact correction: [S: src/services/dudullu-preview.ts:866-877] [S: docs/DECISION_LOG.md:203-204]

61. **Draft line 82 — UNTAGGED — U46 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: For identical virtual vehicles this provides a conditional fleet minimum after heuristic routing.
    - Evidence: `docs/DECISION_LOG.md:197-198; docs/paper/results/week-2026-10-05-4sw5so/README.md:26`.
    - Exact correction: [S: docs/DECISION_LOG.md:197-198] [S: docs/paper/results/week-2026-10-05-4sw5so/README.md:26]

62. **Draft line 82 — UNTAGGED — U47 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: It is not a joint minimum over all possible routes.
    - Evidence: `docs/paper/results/week-2026-10-05-4sw5so/README.md:26`.
    - Exact correction: [S: docs/paper/results/week-2026-10-05-4sw5so/README.md:26]

63. **Draft line 82 — UNTAGGED — U48 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Comparing its count with a heterogeneous real fleet's vehicle count is insufficient: physical capacities, cooldowns, and assignment feasibility require separate evidence.
    - Evidence: `docs/DECISION_LOG.md:203-204`.
    - Exact correction: [S: docs/DECISION_LOG.md:203-204]

64. **Draft line 86 — UNTAGGED — U49 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: The planner selects the service date, admission scenario, ride cap, tour cap, and fleet mode, then inspects the routes and fleet requirement.
    - Evidence: `src/app/(app)/admin/daily-plan/page.tsx:439-475`.
    - Exact correction: [S: src/app/(app)/admin/daily-plan/page.tsx:439-475]

65. **Draft line 86 — UNTAGGED — U50 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: The fleet template is supplied as a parameter; this study uses the physical minibus layout, 4 Sw + 5 So, with a 10-minute cooldown.
    - Evidence: `src/services/daily-plan-run.ts:542-553; docs/paper/results/week-2026-10-05-4sw5so/README.md:20; docs/DECISION_LOG.md:354`.
    - Exact correction: [S: src/services/daily-plan-run.ts:542-553] [S: docs/paper/results/week-2026-10-05-4sw5so/README.md:20] [S: docs/DECISION_LOG.md:354]

66. **Draft line 86 — UNTAGGED — U51 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Template capacities are effective scenario inputs, although the current planning screen does not expose them as freely editable parameters.
    - Evidence: `src/app/(app)/admin/daily-plan/page.tsx:439-472; src/app/(app)/admin/daily-plan/page.tsx:491-570`.
    - Exact correction: [S: src/app/(app)/admin/daily-plan/page.tsx:439-472] [S: src/app/(app)/admin/daily-plan/page.tsx:491-570]

67. **Draft line 88 — UNTAGGED — U52 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Results include waves, routes, longest passenger ride, capacity floors, and assignment status.
    - Evidence: `src/services/daily-plan-view.ts:81-114; src/services/daily-plan-view.ts:172-205`.
    - Exact correction: [S: src/services/daily-plan-view.ts:81-114] [S: src/services/daily-plan-view.ts:172-205]

68. **Draft line 88 — UNTAGGED — U53 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: A proven minimum, an unproven witness, and a shortage have different meanings.
    - Evidence: `src/services/dudullu-preview.ts:866-877; docs/DECISION_LOG.md:197-204`.
    - Exact correction: [S: src/services/dudullu-preview.ts:866-877] [S: docs/DECISION_LOG.md:197-204]

69. **Draft line 88 — UNTAGGED — U54 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Re-running with different limits supports exploring service-level trade-offs.
    - Evidence: `src/app/(app)/admin/daily-plan/page.tsx:457-475`.
    - Exact correction: [S: src/app/(app)/admin/daily-plan/page.tsx:457-475]

70. **Draft line 88 — UNTAGGED — U55 (carried over from WIP).** No source tag follows this factual sentence in a changed main section.

    - Sentence: Vehicles above the seat floor can be associated with routing constraints, overlap, or cooldown, but the observed gap does not measure each cause.
    - Evidence: `uniride_core/algorithms/string_split_decoder.py:337-358; src/services/dudullu-preview.ts:623-634; AGENTS.md:43`.
    - Exact correction: [S: uniride_core/algorithms/string_split_decoder.py:337-358] [S: src/services/dudullu-preview.ts:623-634] [S: AGENTS.md:43]

71. **Draft line 236 — UNTAGGED — U58 (changed metadata).** Updated review/access-history sentence has no tag. The unrelated research session cannot establish this session's access history.

    - Sentence: Review metadata: 10 October 2026; checked code baseline `f7b8570`, obtained with `git rev-parse --short HEAD` after merging `WIP`; repository files and archived outputs inspected, with no operational data access.
    - Evidence: `Git parent as above; secondary d7aab08:docs/research/ARCHITECTURE_RESEARCH_2026-10.md:255,483 describes its own research session only.`.
    - Exact correction: Review metadata: [EKSİK: method-note review date, checked baseline and access-history record].

72. **Draft line 236 — UNTAGGED — U59 (changed metadata).** Baseline-equivalence claim has no source tag.

    - Sentence: Ordinary source tags refer to files at that baseline.
    - Evidence: `git diff --name-only f7b8570 89cfd7c returns only docs/paper/DAILY_STUDENT_TRANSPORT_PLANNING_METHOD.md; every ordinary cited source blob is unchanged.`.
    - Exact correction: [EKSİK: committed provenance confirming the source blobs at the checked baseline]

73. **Draft line 236 — UNTAGGED — U60 (changed metadata).** The link-check outcome is stated without a tagged repository validation record.

    - Sentence: The links below resolve from `docs/paper/` and support maintenance; they can be omitted from a publication.
    - Evidence: `This audit resolved all 44 repository link occurrences against git ls-tree -r --name-only 89cfd7c (43 unique targets), with 0 failures.`.
    - Exact correction: These repository links support maintenance and can be omitted from a publication.

## dayanaksizIddialar

The following access-history assertions lack a separate repository record for the method-note session. Their truth cannot be inferred from static code or from a different session's research report. They are not alleged to be false; under the strict verification rule they must be deleted or replaced by the stated missing-evidence marker.

1. **Draft line 66:** “an active deployment's configuration was not queried for this update.” `ga_split_strategy.py:72-79` supports the constructor overlay only. Replace this clause with `[EKSİK: method-note deployment-inspection record]` (tag 30).
2. **Draft line 236:** “repository files and archived outputs inspected, with no operational data access.” The research report at `d7aab08:docs/research/ARCHITECTURE_RESEARCH_2026-10.md:255,483` describes the research session, not the method-note session. Replace the access-history assertion with `[EKSİK: method-note inspection and access-history record]` (U58).

No additional unsupported scientific quantity was found in the checked corpus. The fractional-second research statement has real support in Git at `d7aab08`, so it is not listed as having no support anywhere in the repository. It nevertheless fails the mandatory `89cfd7c` source test. The demand-ordering and global-infeasibility cautions have implementation rationale, but their cited design/log ranges are incomplete as specified above. The D0 count of 28 is supported; its fresh/unique-census characterization is not accepted without further evidence.

## Rule checks over the whole draft

| Step-3 rule | Result | Evidence / assessment |
|---|---|---|
| No superiority, causality, global optimality or validated service quality claim | PASS | Comparative values are described as snapshot outcomes; boundaries are stated at draft lines 68, 136, 144, 185, 210, 212 and 230. No causal or service-validation conclusion is asserted. |
| Proven is used narrowly | PASS | Fixed-route scope is stated for sensitivity and scenario A; borrowed-vehicle minima are conditional on menus. Planned union labels at line 222 follow `EXACT_SOLVER_AMPL_DESIGN.md:125-127`. |
| One snapshot week, one run per cell, GA seed 42, native protocol | PASS | Campaign/result introductions at lines 96, 102, 127, 136, 140, 148, 152, 177, 189, 193, 210 and 230 provide the labels; four checked manifests record native, effective seed 42 and completed state. CP-SAT seed 20261008 is distinguished from the GA seed at line 150. |
| Exact-reference work planned, only WP-E0 implemented | PASS | Lines 3, 220-224 and 230 distinguish plans from execution. At the pinned tree, `uniride_core/exact/` contains only `__init__.py` and `wave_instance.py`; the offline loader is present, while enumeration/AMPL backend/runner/result paths are planned. The existing single-route helper is separately scoped. |
| Google duration units unverified | PASS | Draft line 21 preserves the T08 unverified-unit statement and missing live-response marker. The separate report does not certify the planned collection path. Its out-of-baseline tags are source defects, not a claim of verified integration. |
| No scientific number absent from repository evidence | PASS, with the contradicted scope listed above | Result quantities match the archived sources or explicit arithmetic from them. Decimal 2.7 is printed as Turkish 2,7 in `YONETIM_OZETI.md:62`; census totals and option counts were recomputed. The Friday error reuses a start time from other rows rather than inventing a new numeric token. Dates/commit metadata lacking tags remain UNTAGGED. |

**Step-3 content-rule violations: 0 detected.** The contradicted time, missing/incomplete tags and four pinned-source failures remain verdict-affecting findings under steps 1-2. The source-path failures breach the requested commit boundary even though the draft discloses the secondary commit.

## Broken repository links

**0 broken links.** All 44 local link/image occurrences (43 distinct targets) were resolved from `docs/paper/` against `git ls-tree -r --name-only 89cfd7c`; directories were required to contain tracked descendants. The two DOI links are external and are not repository-link checks. No source tag was treated as a Markdown link.

## Internal consistency

- The 20 sensitivity rows match their CSVs, including capacities, proof flags, rides, routes, floor gaps and route/wave ratios. Weekly maxima are 6, 6, 6 and 4 for R = 50, 60, 70 and 90. Summed travel minutes are 6822, 6450, 6053 and 5862.
- Fleet A uses the same daily minibus vectors as the single-type campaign. L3 weekly totals are 7, 6, 6 and 4, with sedan peaks 4, 3, 3 and 1. Feasible/infeasible weekday counts agree with the weekly tables.
- The Pareto CSV has 36 options: 32 non-derived and 4 hybrids; 28 are feasible. Recomputed dominance on (f1, f2, f3) yields six non-dominated options at each R. R = 60 points agree with source precision: (0,7,135.5), (1,5,83.6), (2,4,42.5), (3,3,18.2), (4,2,4.2), (6,0,0.0). At R = 90, A and L4 both have (4,0,0), with different mean rides; they are not combined.
- All 20 archived single-type response files were inspected offline. For each R: 57 waves, 226 passenger legs, 50 waves of 1-6 legs. Daily waves are 12/13/11/13/8; daily legs are 54/42/46/46/38. Peak waves are pickup at anchor 525 (08:45), with 20/11/11/10/13 legs. Daily student counts 27/21/23/23/19 sum to 113 student-days, not 113 distinct students.
- Manuscript baseline `f7b8570` occurs consistently in the header and provenance paragraph. The audited draft is `89cfd7c`, its direct child. Manifest commits are `6be127d`, `8ab88ca`, `4200acb` and extra L4 `afc7208`; all four manifests are dirty, native and seed 42. Six ancestry checks confirm neither CX-03 merge `b1889cf` nor CX-01 merge `eb54509` is an ancestor of the three core archive commits (all six return exit 1, meaning not an ancestor).
- The confirmed numerical/source discrepancy is Friday R = 70 at draft line 144, tag 107: source busy peak starts 13:16, whereas the draft prints 13:15. No contradictory repeated vehicle count, Pareto point, wave/leg total or commit value was found.

## Notes (do not affect the verdict)

- The 55 retained untagged sentences are distinguished from newly edited sentences by comparison with WIP. They are included because this audit was requested at changed-section scope; the writing brief only required new/changed sentences to receive tags.
- Table headers were inspected rather than treated as missing facts. In particular, the daily student source rows at `weekly_summary.md:30-34` are valid with their header at 28; tag 264 is OK. Header omission alone was not made a false WRONG_LINE finding.
- The CX-01 no-archive-effect statement is attributed to the recorded audit. `ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md:2399` says the archive is unaffected because inputs are whole minutes, and F15 records integer arcs. A 171-day replay record was not found in the checked tracked evidence, so the draft's replay-evidence marker is retained. No replay or solver run was performed by this fact-check.
- The fleet README at line 34 says 30 s per stage; current `typed_day_selection.py:211-220` shares one call's remaining allowance across stages. The draft separates current implementation from archive provenance; the old README wording was not used to claim current per-stage allowances.
- CodeGraph indexing was attempted first, as required. `codegraph index` returned exit 1 because it could not verify the existing active daemon had stopped. `codegraph init --yes` returned Already initialized; a retry of index returned the same error. No shared daemon or another person's process was stopped. Git-pinned blobs were the fallback.
- Three bounded read-only reviewers audited tag partitions. Final counts are the orchestrator's verified adjudication, not copied reviewer totals. The final pass caught the Friday timing error and blank AGENTS citation and resolved differing treatment of the secondary research commit. No external specialist was claimed to have been consulted.
- No application build, runtime test suite, benchmark, AMPL solve, live database/API call, deployment or scientific campaign was executed. This is a source/archival fact-check, not a validation of service quality or fresh runtime outcomes.
- The writer's worktree remained read-only. The main checkout stayed on WIP and its eight pre-existing untracked files were preserved. The only repository output is this report; no merge or push was performed.

## Verification record

All Git commands used an absolute repository/worktree path. Commands and observed results:

```text
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide worktree add C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.claude\worktrees\method-factcheck -b docs/method-note-factcheck WIP
  Success; branch started at f7b8570. The first sandbox attempt failed to create a Git ref lock; the authorized metadata-write retry succeeded.
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide show 89cfd7c:docs/paper/DAILY_STUDENT_TRANSPORT_PLANNING_METHOD.md
  Success; 247 split lines (last is blank), 278 tags.
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide show d7aab08:docs/research/ARCHITECTURE_RESEARCH_2026-10.md
  Success as secondary evidence; not admitted as 89cfd7c support.
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide show 89cfd7c:docs/research/ARCHITECTURE_RESEARCH_2026-10.md
  Failure: path does not exist in 89cfd7c.
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide diff WIP 89cfd7c -- docs/paper/DAILY_STUDENT_TRANSPORT_PLANNING_METHOD.md
  Comparison only; classifies changed sections and carried-over sentences.
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide diff --name-only f7b8570 89cfd7c
  Only docs/paper/DAILY_STUDENT_TRANSPORT_PLANNING_METHOD.md.
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide ls-tree -r --name-only 89cfd7c
  44 local link occurrences resolve to tracked files/directories; 0 failures.
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide merge-base --is-ancestor b1889cf 6be127d
  Exit 1; not an ancestor.
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide merge-base --is-ancestor eb54509 6be127d
  Exit 1; not an ancestor.
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide merge-base --is-ancestor b1889cf 8ab88ca
  Exit 1; not an ancestor.
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide merge-base --is-ancestor eb54509 8ab88ca
  Exit 1; not an ancestor.
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide merge-base --is-ancestor b1889cf 4200acb
  Exit 1; not an ancestor.
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide merge-base --is-ancestor eb54509 4200acb
  Exit 1; not an ancestor.
Pinned CSV/JSON parsing and standard-library assertions:
  20 sensitivity rows and table fields match; weekly maxima/sums and per-R census match; option counts and six non-dominated options at each R match.
```

Every cited path/range in the ledger was opened through `git show 89cfd7c:<path>`; each of the 38 available source paths succeeded. The one unavailable path is recorded above. No full-suite all-tests-pass claim is made. Report-specific checks require exactly one verdict per draft tag, tag counts summing to 278, 60 unique untagged sentence occurrences, and only this new Markdown file staged.

## Complete source-tag ledger

IDs follow source-tag occurrence order in the draft. The full tag, draft line and final verdict are recorded for every occurrence; exceptions refer back to the exact corrections above.

| ID | Draft line | Verdict | Source tag |
|---:|---:|---|---|
| 1 | 3 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/README.md:3-21]` |
| 2 | 3 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:13]` |
| 3 | 3 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:26-36]` |
| 4 | 3 | OK | `[S: uniride_core/exact/__init__.py:1-14]` |
| 5 | 3 | OK | `[S: scripts/exact_archive_loader.py:1-5]` |
| 6 | 3 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:237-242]` |
| 7 | 21 | OK | `[S: src/services/fleet-scenario-run.ts:544-578]` |
| 8 | 21 | OK | `[S: docs/DECISION_LOG.md:382-386]` |
| 9 | 21 | OK | `[S: docs/DECISION_LOG.md:21]` |
| 10 | 21 | OK | `[S: docs/DECISION_LOG.md:138-142]` |
| 11 | 21 | OK | `[S: docs/DECISION_LOG.md:139]` |
| 12 | 21 | UNSUPPORTED | `[S: d7aab08:docs/research/ARCHITECTURE_RESEARCH_2026-10.md:71]` |
| 13 | 21 | UNSUPPORTED | `[S: d7aab08:docs/research/ARCHITECTURE_RESEARCH_2026-10.md:235]` |
| 14 | 50 | OK | `[S: src/services/daily-plan-run.ts:534-554]` |
| 15 | 50 | OK | `[S: src/services/fleet-scenario-run.ts:493-508]` |
| 16 | 50 | OK | `[S: optimizer_api/strategies/ga_split_strategy.py:58-70]` |
| 17 | 54 | OK | `[S: optimizer_api/strategies/ga_split_strategy.py:58-70]` |
| 18 | 55 | OK | `[S: optimizer_api/strategies/ga_split_strategy.py:58-70]` |
| 19 | 56 | OK | `[S: optimizer_api/strategies/ga_split_strategy.py:58-70]` |
| 20 | 57 | OK | `[S: optimizer_api/strategies/ga_split_strategy.py:58-70]` |
| 21 | 58 | OK | `[S: optimizer_api/strategies/ga_split_strategy.py:58-70]` |
| 22 | 59 | OK | `[S: optimizer_api/strategies/ga_split_strategy.py:58-70]` |
| 23 | 60 | OK | `[S: optimizer_api/strategies/ga_split_strategy.py:58-70]` |
| 24 | 61 | OK | `[S: optimizer_api/strategies/ga_split_strategy.py:58-70]` |
| 25 | 61 | OK | `[S: uniride_core/algorithms/ga_split_engine.py:352-370]` |
| 26 | 62 | OK | `[S: optimizer_api/strategies/ga_split_strategy.py:58-70]` |
| 27 | 63 | OK | `[S: optimizer_api/strategies/ga_split_strategy.py:58-70]` |
| 28 | 63 | OK | `[S: uniride_core/algorithms/ga_split_engine.py:378-382]` |
| 29 | 64 | PARTIAL | `[S: optimizer_api/strategies/ga_split_strategy.py:58-70]` |
| 30 | 66 | PARTIAL | `[S: optimizer_api/strategies/ga_split_strategy.py:72-79]` |
| 31 | 66 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/run_manifest.json:39-53]` |
| 32 | 66 | OK | `[S: optimizer_api/strategies/seed_utils.py:7-21]` |
| 33 | 66 | PARTIAL | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:251-258]` |
| 34 | 90 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:1-5]` |
| 35 | 90 | OK | `[S: src/services/daily-plan-view.ts:81-108]` |
| 36 | 90 | OK | `[S: src/services/plan-experiments.ts:106-132]` |
| 37 | 90 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:1-2]` |
| 38 | 94 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/README.md:7-21]` |
| 39 | 94 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/README.md:20-21]` |
| 40 | 94 | PARTIAL | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:251-255]` |
| 41 | 96 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/README.md:19]` |
| 42 | 96 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/run_manifest.json:24-67]` |
| 43 | 96 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:278]` |
| 44 | 98 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:1-2]` |
| 45 | 98 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:5]` |
| 46 | 98 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:259]` |
| 47 | 98 | PARTIAL | `[S: docs/DECISION_LOG.md:195-206]` |
| 48 | 102 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/README.md:19-27]` |
| 49 | 102 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/README.md:5-12]` |
| 50 | 102 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/README.md:3]` |
| 51 | 102 | OK | `[S: docs/paper/results/week-2026-10-05/README.md:1]` |
| 52 | 102 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:1-21]` |
| 53 | 102 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/README.md:26]` |
| 54 | 106 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:2]` |
| 55 | 107 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:3]` |
| 56 | 108 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:4]` |
| 57 | 109 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:5]` |
| 58 | 110 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:6]` |
| 59 | 111 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:7]` |
| 60 | 112 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:8]` |
| 61 | 113 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:9]` |
| 62 | 114 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:10]` |
| 63 | 115 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:11]` |
| 64 | 116 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:12]` |
| 65 | 117 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:13]` |
| 66 | 118 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:14]` |
| 67 | 119 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:15]` |
| 68 | 120 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:16]` |
| 69 | 121 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:17]` |
| 70 | 122 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:18]` |
| 71 | 123 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:19]` |
| 72 | 124 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:20]` |
| 73 | 125 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:21]` |
| 74 | 127 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/run_manifest.json:22-25]` |
| 75 | 127 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/run_manifest.json:52]` |
| 76 | 127 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:55]` |
| 77 | 131 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/weekly.csv:2]` |
| 78 | 132 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/weekly.csv:3]` |
| 79 | 133 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/weekly.csv:4]` |
| 80 | 134 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/weekly.csv:5]` |
| 81 | 136 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/README.md:19-27]` |
| 82 | 136 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/weekly.csv:2-5]` |
| 83 | 136 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:10-13]` |
| 84 | 136 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/weekly.csv:2-5]` |
| 85 | 136 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:2-21]` |
| 86 | 136 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:2-21]` |
| 87 | 136 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:2-21]` |
| 88 | 136 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/README.md:25-27]` |
| 89 | 140 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/README.md:19-20]` |
| 90 | 140 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:257-261]` |
| 91 | 140 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:267-284]` |
| 92 | 144 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:267]` |
| 93 | 144 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:272]` |
| 94 | 144 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:277]` |
| 95 | 144 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:265-284]` |
| 96 | 144 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:259]` |
| 97 | 144 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/README.md:27]` |
| 98 | 144 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:265]` |
| 99 | 144 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:270]` |
| 100 | 144 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:275]` |
| 101 | 144 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:280]` |
| 102 | 144 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:267-284]` |
| 103 | 144 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/README.md:12]` |
| 104 | 144 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:267]` |
| 105 | 144 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:272]` |
| 106 | 144 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:277]` |
| 107 | 144 | CONTRADICTED | `[S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:268-284]` |
| 108 | 148 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:24-36]` |
| 109 | 148 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:29]` |
| 110 | 148 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:29]` |
| 111 | 148 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:17-22]` |
| 112 | 148 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:41-43]` |
| 113 | 148 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:13]` |
| 114 | 148 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:33]` |
| 115 | 148 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:58-68]` |
| 116 | 150 | OK | `[S: uniride_core/algorithms/typed_split_decoder.py:119-148]` |
| 117 | 150 | OK | `[S: uniride_core/algorithms/typed_split_decoder.py:150-172]` |
| 118 | 150 | OK | `[S: src/services/fleet-scenario-run.ts:478-525]` |
| 119 | 150 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:18]` |
| 120 | 150 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/extra/L4/README.md:13]` |
| 121 | 150 | OK | `[S: src/services/fleet-scenario-run.ts:233-235]` |
| 122 | 150 | OK | `[S: src/services/fleet-scenario-run.ts:519-524]` |
| 123 | 150 | OK | `[S: uniride_core/planning/typed_day_selection.py:6-15]` |
| 124 | 150 | OK | `[S: uniride_core/planning/typed_day_selection.py:17-25]` |
| 125 | 150 | OK | `[S: uniride_core/planning/typed_day_selection.py:211-220]` |
| 126 | 150 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/run_manifest.json:80-100]` |
| 127 | 150 | OK | `[S: src/services/fleet-scenario-run.ts:609-636]` |
| 128 | 150 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/fleet_verification.md:3-16]` |
| 129 | 152 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:13]` |
| 130 | 152 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:33]` |
| 131 | 152 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:47]` |
| 132 | 152 | WRONG_LINE | `[S: docs/paper/results/week-2026-10-05-fleet/scenario_weekly.csv:2]` |
| 133 | 152 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:30-34]` |
| 134 | 152 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:41-56]` |
| 135 | 156 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:7]` |
| 136 | 157 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:8]` |
| 137 | 158 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:9]` |
| 138 | 159 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:10]` |
| 139 | 160 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:11]` |
| 140 | 161 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:12]` |
| 141 | 162 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:13]` |
| 142 | 163 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:14]` |
| 143 | 164 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:15]` |
| 144 | 165 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:16]` |
| 145 | 166 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:17]` |
| 146 | 167 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:18]` |
| 147 | 168 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:19]` |
| 148 | 169 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:20]` |
| 149 | 170 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:21]` |
| 150 | 171 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:22]` |
| 151 | 173 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:3]` |
| 152 | 173 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:51-56]` |
| 153 | 173 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:24]` |
| 154 | 177 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:13]` |
| 155 | 177 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:33-43]` |
| 156 | 179 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/YONETIM_OZETI.md:32]` |
| 157 | 179 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:30-34]` |
| 158 | 180 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:9-21]` |
| 159 | 180 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/YONETIM_OZETI.md:33]` |
| 160 | 181 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:10-22]` |
| 161 | 181 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/car_usage_windows.csv:28-30]` |
| 162 | 181 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/car_usage_windows.csv:6-7]` |
| 163 | 181 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/car_usage_windows.csv:22]` |
| 164 | 181 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/car_usage_windows.csv:39]` |
| 165 | 181 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/car_usage_windows.csv:56-57]` |
| 166 | 182 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:7-22]` |
| 167 | 182 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/scenario_weekly.csv:2-17]` |
| 168 | 182 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/scenario_weekly.csv:6]` |
| 169 | 182 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/scenario_weekly.csv:9]` |
| 170 | 182 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:3]` |
| 171 | 182 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/scenario_daily.csv:2-81]` |
| 172 | 182 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/scenario_weekly.csv:5]` |
| 173 | 182 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/scenario_weekly.csv:9]` |
| 174 | 182 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/scenario_weekly.csv:13]` |
| 175 | 182 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/scenario_weekly.csv:17]` |
| 176 | 183 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:10-22]` |
| 177 | 185 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:43-54]` |
| 178 | 185 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:29]` |
| 179 | 185 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:47]` |
| 180 | 185 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/YONETIM_OZETI.md:63-64]` |
| 181 | 185 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:51-54]` |
| 182 | 185 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/YONETIM_OZETI.md:65-67]` |
| 183 | 185 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/fleet_mix_analysis.md:7-14]` |
| 184 | 189 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:24-32]` |
| 185 | 189 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/extra/L4/README.md:8-13]` |
| 186 | 189 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/extra/minivan-cap3/README.md:12-17]` |
| 187 | 189 | OK | `[S: docs/DECISION_LOG.md:370]` |
| 188 | 189 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/extra/minivan-cap3/README.md:7]` |
| 189 | 189 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:24]` |
| 190 | 189 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/extra/minivan/README.md:1]` |
| 191 | 189 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/extra/minivan-cap3/README.md:3-7]` |
| 192 | 189 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/YONETIM_OZETI.md:62]` |
| 193 | 189 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/extra/L4/README.md:13-20]` |
| 194 | 189 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/extra/minivan-cap3/README.md:17-23]` |
| 195 | 191 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:7]` |
| 196 | 191 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:15-19]` |
| 197 | 191 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:18]` |
| 198 | 191 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:7]` |
| 199 | 191 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:40]` |
| 200 | 191 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_options.csv:2-37]` |
| 201 | 191 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:36]` |
| 202 | 191 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:20-22]` |
| 203 | 193 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:33]` |
| 204 | 193 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/extra/L4/README.md:18]` |
| 205 | 193 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/extra/minivan-cap3/README.md:22]` |
| 206 | 193 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:108-113]` |
| 207 | 197 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:108]` |
| 208 | 198 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:109]` |
| 209 | 199 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:110]` |
| 210 | 200 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:111]` |
| 211 | 201 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:112]` |
| 212 | 202 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:113]` |
| 213 | 204 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:102-131]` |
| 214 | 204 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:93-94]` |
| 215 | 204 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:170-171]` |
| 216 | 204 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:127]` |
| 217 | 204 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:135-144]` |
| 218 | 204 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:140-144]` |
| 219 | 204 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:135]` |
| 220 | 204 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:60-66]` |
| 221 | 208 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:174-181]` |
| 222 | 210 | WRONG_LINE | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:9]` |
| 223 | 210 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:9]` |
| 224 | 210 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:9]` |
| 225 | 210 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:33]` |
| 226 | 210 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:185-189]` |
| 227 | 212 | OK | `[S: AGENTS.md:38-54]` |
| 228 | 212 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:3]` |
| 229 | 212 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:33-43]` |
| 230 | 212 | WRONG_LINE | `[S: AGENTS.md:44-46]` |
| 231 | 214 | OK | `[S: docs/DECISION_LOG.md:382-386]` |
| 232 | 214 | OK | `[S: src/services/fleet-scenario-run.ts:544-578]` |
| 233 | 214 | OK | `[S: docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md:2399]` |
| 234 | 214 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:27]` |
| 235 | 214 | OK | `[S: docs/DECISION_LOG.md:374-378]` |
| 236 | 214 | OK | `[S: uniride_core/algorithms/ga_split_typed_engine.py:76-89]` |
| 237 | 214 | OK | `[S: docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md:2398]` |
| 238 | 214 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:26]` |
| 239 | 214 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:26]` |
| 240 | 214 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/extra/L4/README.md:17]` |
| 241 | 214 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:280]` |
| 242 | 218 | OK | `[S: docs/DECISION_LOG.md:344-348]` |
| 243 | 218 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:185]` |
| 244 | 218 | OK | `[S: docs/designs/HETEROGENEOUS_FLEET_DESIGN.md:34-37]` |
| 245 | 218 | WRONG_LINE | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:43]` |
| 246 | 218 | OK | `[S: docs/DECISION_LOG.md:119-123]` |
| 247 | 220 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:36-66]` |
| 248 | 220 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:201-202]` |
| 249 | 220 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:86]` |
| 250 | 220 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:23]` |
| 251 | 220 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:30]` |
| 252 | 222 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:241]` |
| 253 | 222 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:253-258]` |
| 254 | 222 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:251]` |
| 255 | 222 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:258]` |
| 256 | 222 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:121-124]` |
| 257 | 222 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:125-127]` |
| 258 | 222 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:125-127]` |
| 259 | 224 | OK | `[S: uniride_core/exact/__init__.py:1-14]` |
| 260 | 224 | OK | `[S: scripts/exact_archive_loader.py:1-5]` |
| 261 | 224 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:237-244]` |
| 262 | 224 | OK | `[S: docs/DECISION_LOG.md:407]` |
| 263 | 224 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:64-88]` |
| 264 | 228 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:30-34]` |
| 265 | 228 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/run_manifest.json:63-67]` |
| 266 | 228 | PARTIAL | `[S: docs/DEMO_ROADMAP_2026-10-04.md:276]` |
| 267 | 228 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:22]` |
| 268 | 228 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:185-188]` |
| 269 | 230 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/README.md:19-27]` |
| 270 | 230 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:13]` |
| 271 | 230 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:33-43]` |
| 272 | 230 | OK | `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:241-244]` |
| 273 | 230 | OK | `[S: docs/paper/results/week-2026-10-05-4sw5so/README.md:25-27]` |
| 274 | 230 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/README.md:43-47]` |
| 275 | 230 | OK | `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:185-189]` |
| 276 | 230 | OK | `[S: AGENTS.md:38-54]` |
| 277 | 236 | UNSUPPORTED | `[S: d7aab08:docs/research/ARCHITECTURE_RESEARCH_2026-10.md:255]` |
| 278 | 236 | UNSUPPORTED | `[S: d7aab08:docs/research/ARCHITECTURE_RESEARCH_2026-10.md:483]` |
