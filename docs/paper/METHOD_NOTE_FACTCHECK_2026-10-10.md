# Independent fact-check — DUZELT round-one re-check

**Verdict: DUZELT**

The revision applies all 13 original tagged-claim corrections and removes the two unsupported access-history assertions. All 60 requested untagged-sentence edits are present. However, eight of those sentences still need wording or citation corrections, and re-checking retained tags found five further citation gaps. The fresh checks yield 163 OK, 6 WRONG_LINE and 7 PARTIAL; there are no UNSUPPORTED, CONTRADICTED or newly UNTAGGED sentences. The seven PARTIAL verdicts require DUZELT under the requested acceptance rule.

No draft, code, archive, design or decision-log file was edited. This report supersedes the current verdict of the first report; that complete historical report remains in commit `93295f501579e77a56edd8a2994d8fef9b0e7f6d`.

## Checked material and scope

- Audit date: 2026-10-10, Europe/Istanbul.
- Updated draft: `docs/paper/DAILY_STUDENT_TRANSPORT_PLANNING_METHOD.md` at `08aee7016a91ccd5d58bbfb0a1682ba702db1d99`, branch `docs/method-note-2026-10-10`. The user supplied `<hash>` as a placeholder; the named branch and its clean worktree identify this actual revision.
- Round-one draft: `89cfd7c5cd23a04ee5d2e720dd4d2c844a28b4a2`. The updated commit has that commit as its parent and changes only the method note: 27 lines replaced, with no line-number shifts.
- Every draft line and tag ID in this current report refers to `08aee70`, unless explicitly labelled old. New IDs are ordinal source-tag occurrences 1-356; old IDs refer to the original 278-tag ledger.
- `AGENTS.md`, the user-supplied instructions, the writing brief `docs/CODEX_TASK_METHOD_NOTE_UPDATE.md`, and the original report were read. Sources were read using pinned Git blobs, not the writer worktree filesystem.
- The draft contains 356 source tags at 42 distinct paths. Every path exists and every line range is valid at 08aee70. All 42 cited source files are byte-identical to 89cfd7c and to the stated code baseline f7b8570. The R50 SVG was also inspected for a proposed correction.
- Touched is conservatively defined as every tag on any changed draft line, including unchanged adjacent tags: 146 occurrences. All 146 were re-checked. Of 210 occurrences on unchanged lines, 30 were randomly sampled and re-checked; the other 180 retain their round-one OK verdicts after confirming identical claims, tags and source blobs.
- All 73 original duzeltmeler items were checked: 13 tagged-claim items and 60 UNTAGGED items. Both original dayanaksizIddialar items were also checked. The same changed-main-section scope as round one is retained; unchanged §§1 and 3 are not newly classified as UNTAGGED. Definitions, normative instructions, prospective research directions, bibliographic metadata and explicit EKSİK placeholders are excluded as before.
- Output: `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.claude\worktrees\method-factcheck\docs\paper\METHOD_NOTE_FACTCHECK_2026-10-10.md`, on `docs/method-note-factcheck`. Only this file is authorized for modification and commit.

Complementary adjacent tags are evaluated collectively for their natural clauses. Table headers are read as context; a correct row is not rejected just because its header is outside the selected range. A compound sentence is not accepted if a factual qualification lacks support. WRONG_LINE means that the missing support is elsewhere in the same cited file; PARTIAL identifies an unsupported clause or qualification, including support that requires a different file. No uncertain item is counted as OK.

## Counts

| Verdict | Touched, fresh | Unchanged sample, fresh | Fresh total | Carried forward | Current inventory |
|---|---:|---:|---:|---:|---:|
| OK | 136 | 27 | 163 | 180 | 343 |
| WRONG_LINE | 4 | 2 | 6 | 0 | 6 |
| PARTIAL | 6 | 1 | 7 | 0 | 7 |
| UNSUPPORTED | 0 | 0 | 0 | 0 | 0 |
| CONTRADICTED | 0 | 0 | 0 | 0 | 0 |
| Total source tags | 146 | 30 | 176 | 180 | 356 |

**UNTAGGED: 0** factual sentences in the changed sections. This is a sentence count, separate from source tags. Formerly UNTAGGED sentences can be tagged yet still have PARTIAL or WRONG_LINE support; those defects are counted above, not counted again as UNTAGGED.

Original UNTAGGED disposition: 52 closed (47 supported factual sentences plus 5 accepted metadata/replacement edits); 8 reopened below (4 PARTIAL and 4 WRONG_LINE). The original 13 tagged-claim corrections and both access-history removals are closed.

## duzeltmeler

These are the current outstanding corrections. They concern evidence and meaning, not writing style. Eight revise citation/wording suggestions supplied in the first report; five were missed retained-tag problems discovered by the requested re-check or random sample.

1. **Draft line 15 — PARTIAL — new tag 8 / U02 (touched).** The cited design says the matrix is directed. It does not establish the stronger wording that c(i,j) generally differs from c(j,i); a directed matrix can still have equal reverse arcs. The source supports possible asymmetry, not an observed directional-inequality result.

    - Current tag: `[S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:20]`.
    - Evidence at 08aee70: `docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:20; src/services/daily-plan-run.ts:539-540`.
    - Exact correction: c(i,j) may differ from c(j,i). [S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:20]

2. **Draft line 19 — WRONG_LINE — new tag 18 / U10 (touched).** The matrix recosting range stops at 355 before the explicit request-bound-snapshot statement. The companion orchestration citation shows the snapshot identity, but the certifier citation should include the bound lookup qualification.

    - Current tag: `[S: optimizer_api/verification/response_certifier.py:348-355]`.
    - Evidence at 08aee70: `optimizer_api/verification/response_certifier.py:348-358, especially 356-358`.
    - Exact correction: [S: optimizer_api/verification/response_certifier.py:348-358]

3. **Draft line 19 — PARTIAL — new tag 19 / U11 (touched).** The cited limitations support a fixed matrix and absent traffic/boarding/driver modelling. They do not literally document the matrix collection conditions or its loading-delay/accessibility conditions. Vehicle-capacity assumptions at 187 are not evidence about the road-time matrix collection conditions.

    - Current tag: `[S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:185-189]`.
    - Evidence at 08aee70: `docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:185-189`.
    - Exact correction: The archived analysis uses a fixed travel-time matrix, with no traffic, boarding times or driver assignment. [S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:185]

4. **Draft line 60 — PARTIAL — new tag 53 (sampled unchanged).** The strategy default dictionary supports Hybrid. It does not describe education of a selected giant tour; that implementation is in a different file. This was an unchanged tag selected in the random sample.

    - Current tag: `[S: optimizer_api/strategies/ga_split_strategy.py:58-70]`.
    - Evidence at 08aee70: `optimizer_api/strategies/ga_split_strategy.py:67-68; uniride_core/algorithms/ga_split_engine.py:351-370`.
    - Exact correction: Append [S: uniride_core/algorithms/ga_split_engine.py:351-370] to this table row.

5. **Draft line 72 — WRONG_LINE — new tag 70 / U29 (touched).** The cited docstring covers continuity, closure, reported-load consistency and matrix recosting, but the explicit required-occurrence-coverage and hard-constraint calls occur later in the same file.

    - Current tag: `[S: optimizer_api/verification/response_certifier.py:333-355]`.
    - Evidence at 08aee70: `optimizer_api/verification/response_certifier.py:660-684, especially 662, 665, 671-684`.
    - Exact correction: Append [S: optimizer_api/verification/response_certifier.py:660-684] after the existing 333-355 tag.

6. **Draft line 72 — WRONG_LINE — new tag 71 / U30 (touched).** The first range supports the 0.005-minute per-arc formatting tolerance and the second supports checks on matrix durations. Neither selected range states the aggregate formatting checks; those are at 339-341 in the same file.

    - Current tag: `[S: optimizer_api/verification/response_certifier.py:129-140]`.
    - Evidence at 08aee70: `optimizer_api/verification/response_certifier.py:129-140, 339-341, 348-355`.
    - Exact correction: Append [S: optimizer_api/verification/response_certifier.py:339-341] after the two existing tags for this sentence.

7. **Draft line 82 — PARTIAL — new tag 95 / U46 (touched).** The two current tags establish conditional fixed-route minimality after heuristic routing. They do not identify the virtual fleet as identical copies. Because this is an implementation description, that qualification needs the virtual-fleet constructor.

    - Current tag: `[S: docs/DECISION_LOG.md:197-198]`.
    - Evidence at 08aee70: `docs/DECISION_LOG.md:197-198; docs/paper/results/week-2026-10-05-4sw5so/README.md:26; src/services/dudullu-preview.ts:246-256`.
    - Exact correction: Append [S: src/services/dudullu-preview.ts:246-256] to the sentence.

8. **Draft line 86 — WRONG_LINE — new tag 99 / U49 (touched).** The cited range shows controls, the preview request and storing the plan. Route and fleet inspection is rendered elsewhere in the same UI file.

    - Current tag: `[S: src/app/(app)/admin/daily-plan/page.tsx:439-475]`.
    - Evidence at 08aee70: `src/app/(app)/admin/daily-plan/page.tsx:132-169, 253-275, 400-435, 602`.
    - Exact correction: Append [S: src/app/(app)/admin/daily-plan/page.tsx:132-169] [S: src/app/(app)/admin/daily-plan/page.tsx:253-275] [S: src/app/(app)/admin/daily-plan/page.tsx:400-435] [S: src/app/(app)/admin/daily-plan/page.tsx:602] to the sentence.

9. **Draft line 88 — PARTIAL — new tag 112 / U55 (touched).** The split and assignment code supports the routing/overlap/cooldown constraints. AGENTS.md:43 prohibits causal proof claims from pilots; it does not establish how this displayed gap is measured. The gap-not-cause qualification is conservative, but its implementation evidence is missing from the tag group, so it is not accepted as fully supported.

    - Current tag: `[S: AGENTS.md:43]`.
    - Evidence at 08aee70: `uniride_core/algorithms/string_split_decoder.py:337-358; src/services/dudullu-preview.ts:623-634; AGENTS.md:43; src/app/(app)/admin/daily-plan/page.tsx:93-127`.
    - Exact correction: Replace [S: AGENTS.md:43] for this sentence with [S: src/app/(app)/admin/daily-plan/page.tsx:93-127].

10. **Draft line 144 — PARTIAL — new tag 183 (touched).** The README lists archived figures and the generation script, but does not describe the named R50 chart or its stacked weekday panels. The linked SVG supplies the missing support; the current source tag does not.

    - Current tag: `[S: docs/paper/results/week-2026-10-05-4sw5so/README.md:12]`.
    - Evidence at 08aee70: `docs/paper/results/week-2026-10-05-4sw5so/README.md:12, 31-39; docs/paper/results/week-2026-10-05-4sw5so/figures/resource_week_R50.svg:2, 7, 116, 224, 323, 433`.
    - Exact correction: Replace [S: docs/paper/results/week-2026-10-05-4sw5so/README.md:12] after the weekly-chart sentence with [S: docs/paper/results/week-2026-10-05-4sw5so/figures/resource_week_R50.svg:2-433].

11. **Draft line 152 — PARTIAL — new tag 214 (touched).** The README range supports menu-limited sedan minima and assignment status. The sentence also defines weekly need as the maximum daily need and explicitly limits the all-large A proof to fixed routes; those clauses need their separate archive evidence.

    - Current tag: `[S: docs/paper/results/week-2026-10-05-fleet/README.md:41-56]`.
    - Evidence at 08aee70: `docs/paper/results/week-2026-10-05-fleet/README.md:41-56; docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:3, 24; docs/paper/results/week-2026-10-05-4sw5so/README.md:26`.
    - Exact correction: Append [S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:3] [S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:24] [S: docs/paper/results/week-2026-10-05-4sw5so/README.md:26] to the sentence.

12. **Draft line 173 — WRONG_LINE — new tag 231 (sampled unchanged).** Line3 defines the dash and the weekly fleet calculation, but not the x symbol. The x/day mapping is in the following weekly table, read with the companion menu-infeasibility explanation. This was an unchanged sampled tag.

    - Current tag: `[S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:3]`.
    - Evidence at 08aee70: `docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:3-22; docs/paper/results/week-2026-10-05-fleet/README.md:51-56`.
    - Exact correction: Replace the weekly-summary tag with [S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:3-22], retaining [S: docs/paper/results/week-2026-10-05-fleet/README.md:51-56].

13. **Draft line 182 — WRONG_LINE — new tag 250 (sampled unchanged).** README line 3 supports descriptive reporting, but the heuristic-route qualifier is stated later in the same file. This was an unchanged sampled tag.

    - Current tag: `[S: docs/paper/results/week-2026-10-05-fleet/README.md:3]`.
    - Evidence at 08aee70: `docs/paper/results/week-2026-10-05-fleet/README.md:3, 33, 43`.
    - Exact correction: Replace [S: docs/paper/results/week-2026-10-05-fleet/README.md:3] for this sentence with [S: docs/paper/results/week-2026-10-05-fleet/README.md:3-43].

## dayanaksizIddialar

No new wholly unsupported factual sentence was found in this bounded re-check. No UNSUPPORTED or CONTRADICTED verdict remains. The PARTIAL items above are not accepted as fully supported as written; their exact source/wording corrections are given in duzeltmeler rather than treating them as invented results.

The original two items are resolved:

1. **Old/new draft line 66 — CLOSED.** “an active deployment's configuration was not queried for this update” was removed. The supported constructor-overlay sentence remains with `ga_split_strategy.py:72-79`, followed by `[EKSİK: method-note deployment-inspection record]`.
2. **Old/new draft line 236 — CLOSED.** “repository files and archived outputs inspected, with no operational data access” was removed. The remaining metadata is explicitly `[EKSİK: method-note review date, checked baseline and access-history record]`; it no longer asserts the writer's access history.

## Disposition of all original tagged-claim corrections

| Original item | Old tag ID(s) | Old/new draft line | Status | Verified handling | Evidence at 08aee70 |
|---|---|---:|---|---|---|
| 1 | 12, 13 | 21 | CLOSED | Research-note assertion and both absent-path tags removed; the pending-research EKSİK marker remains. | draft:21; absent research path at 08aee70 |
| 2 | 29 | 64 | CLOSED | Seed-resolver tag 7-17 added; DEFAULT_SEED=42 and the None branch are explicit. | optimizer_api/strategies/ga_split_strategy.py:66; optimizer_api/strategies/seed_utils.py:7-17 |
| 3 | 30 | 66 | CLOSED | Overlay statement retained and supported; deployment-query assertion replaced by its EKSİK marker. | optimizer_api/strategies/ga_split_strategy.py:72-79; draft:66 |
| 4 | 33 | 66 | CLOSED | Ordering-sensitive initialization tag 79-92 added alongside the input/configuration archive rule. | docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:251-258; uniride_core/algorithms/ga_split_engine.py:79-92 |
| 5 | 40 | 94 | CLOSED | Ordering-sensitive initialization tag 79-92 added to the future paired-comparison condition. | docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:251-255; uniride_core/algorithms/ga_split_engine.py:79-92 |
| 6 | 47 | 98 | CLOSED | Unverified heuristic-failure clause replaced by the supported witness/minimality/heuristic-routing sentence. | docs/DECISION_LOG.md:197-198 |
| 7 | 107 | 144 | CLOSED | Friday R70 busy-peak start corrected to 13:16, retaining the cited schedule range. | docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:279 |
| 8 | 132 | 152 | CLOSED | CSV range expanded to 2-14 and now includes every A row for all four R values. | docs/paper/results/week-2026-10-05-fleet/scenario_weekly.csv:2, 6, 10, 14 |
| 9 | 222 | 210 | CLOSED | Pareto range expanded to 9-34, including both tested L values and the R grid. | docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:9, 34 |
| 10 | 230 | 212 | CLOSED | Protocol tag corrected to AGENTS.md:38-39. | AGENTS.md:38-39 |
| 11 | 245 | 218 | CLOSED | Fleet README range expanded to 13-43; typed pools/scenarios and the non-global menu limitation are present. | docs/paper/results/week-2026-10-05-fleet/README.md:13, 24-29, 43 |
| 12 | 266 | 228 | CLOSED | Earlier 28-student statement now identifies the D0 read-only inventory and its 2026-10-04 date. | docs/DEMO_ROADMAP_2026-10-04.md:276 |
| 13 | 277, 278 | 236 | CLOSED | Outside-snapshot citation explanation and both tags removed; pending-research provenance is an EKSİK marker. | draft:236; absent research path at 08aee70 |

The closure of original item8 (the 226-legs CSV range) does not close the separate retained weekly-definition/proof-scope claim at the same draft line; that is current correction11. Original item11's range13-43 supplies the archived fleet pools/scenarios and the explicit non-global-minimum qualification.

## Disposition of all 60 original UNTAGGED sentences

Each row identifies the original sentence, the original duzeltmeler item and the current support. All 55 carried-over method sentences were retained and tagged. The five metadata/navigational sentences received the requested replacements. Source ranges below are those actually inserted, not an automatic acceptance of the first report's suggestions.

| ID | Original item | Old/new draft line | Original sentence | Current disposition / evidence |
|---|---:|---:|---|---|
| U01 | 16 | 15 | Planning uses a stored, directed matrix derived from road-network routing. | CLOSED — sourced; [S: docs/DECISION_LOG.md:95-98] |
| U02 | 17 | 15 | In general c(i,j) differs from c(j,i). | REOPENED — PARTIAL; current correction 1. [S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:20] |
| U03 | 18 | 15 | Straight-line distances and coordinate-based travel-time approximations are not used in this operational method. | CLOSED — sourced; [S: docs/DECISION_LOG.md:97-98] |
| U04 | 19 | 15 | Missing or invalid required arcs prevent certification rather than being silently assigned zero travel time. | CLOSED — sourced; [S: optimizer_api/verification/response_certifier.py:348-355] |
| U05 | 20 | 17 | The matrix is not assumed to satisfy the triangle inequality. | CLOSED — sourced; [S: docs/DECISION_LOG.md:167-168] |
| U06 | 21 | 17 | A direct campus-to-stop time is therefore not a certified lower bound on a route reaching that stop through other stops. | CLOSED — sourced; [S: docs/DECISION_LOG.md:167-168] |
| U07 | 22 | 17 | A wave cannot be rejected solely because a direct arc exceeds its ride limit. | CLOSED — sourced; [S: docs/DECISION_LOG.md:167-169] |
| U08 | 23 | 17 | Different passenger occurrences at one physical location may have a zero connecting hop; this does not justify zero travel between different locations. | CLOSED — sourced; [S: optimizer_api/verification/response_certifier.py:125-127] [S: optimizer_api/verification/response_certifier.py:348-355] |
| U09 | 24 | 19 | A matrix snapshot is captured before solving. | CLOSED — sourced; [S: src/services/daily-plan-run.ts:522-539] |
| U10 | 25 | 19 | Wave requests are bound to its identity, and route verification uses the captured authoritative arc values. | REOPENED — WRONG_LINE; current correction 2. [S: src/services/daily-plan-run.ts:522-539] [S: optimizer_api/verification/response_certifier.py:348-355] |
| U11 | 26 | 19 | The matrix represents collection conditions, not necessarily current traffic, loading delays, or accessibility conditions. | REOPENED — PARTIAL; current correction 3. [S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:185-189] |
| U12 | 27 | 44 | Each wave uses a genetic algorithm (GA) over a permutation of passenger occurrences, called a giant tour. | CLOSED — sourced; [S: src/services/daily-plan-run.ts:526-554] [S: uniride_core/algorithms/ga_split_engine.py:97-120] |
| U13 | 28 | 44 | A split decoder partitions consecutive subsequences into depot-closed vehicle routes. | CLOSED — sourced; [S: uniride_core/algorithms/string_split_decoder.py:324-367] [S: uniride_core/algorithms/string_split_decoder.py:249-269] |
| U14 | 29 | 44 | This follows the route-first, cluster-second representation associated with [Prins (2004)](https://doi.org/10.1016/S0305-0548(03)00158-8). | CLOSED — sourced; [S: optimizer_api/strategies/ga_split_strategy.py:44-55] |
| U15 | 30 | 44 | The present implementation has its own constraints and acceptance checks; no comparative performance claim is inferred from the reference. | CLOSED — sourced; [S: uniride_core/algorithms/string_split_decoder.py:337-367] [S: optimizer_api/verification/response_certifier.py:333-358] |
| U16 | 31 | 46 | Initialization combines randomized permutations and a nearest-neighbour tour. | CLOSED — sourced; [S: uniride_core/algorithms/ga_split_engine.py:71-94] |
| U17 | 32 | 46 | Tournament selection, order crossover, mutation, and elitism generate new candidates. | CLOSED — sourced; [S: uniride_core/algorithms/ga_split_engine.py:251-293] |
| U18 | 33 | 46 | Periodic local search modifies a selected giant tour, which is then decoded and evaluated again. | CLOSED — sourced; [S: uniride_core/algorithms/ga_split_engine.py:352-370] |
| U19 | 34 | 46 | The outer ranking prioritizes feasibility, then route count, then total travel time. | CLOSED — sourced; [S: docs/DECISION_LOG.md:173] |
| U20 | 35 | 48 | The decoder enumerates feasible contiguous segments under both passenger capacities and the tour and ride limits. | CLOSED — sourced; [S: uniride_core/algorithms/string_split_decoder.py:324-367] |
| U21 | 36 | 48 | Dynamic programming chooses a minimum-travel-time partition for a fixed permutation, preferring partitions without violations. | CLOSED — sourced; [S: uniride_core/algorithms/string_split_decoder.py:202-228] |
| U22 | 37 | 48 | This restricted calculation does not optimize all permutations, and its cost objective differs from the outer GA's route-count priority. | CLOSED — sourced; [S: uniride_core/algorithms/string_split_decoder.py:190-228] [S: docs/DECISION_LOG.md:173] |
| U23 | 38 | 48 | Neither a decoded partition nor the final wave result proves globally minimum route count. | CLOSED — sourced; [S: uniride_core/algorithms/string_split_decoder.py:202-228] [S: uniride_core/algorithms/ga_split_engine.py:318-379] |
| U24 | 39 | 48 | With nonmetric travel, a duration violation also does not imply that every longer segment violates the limit; alternatives must still be examined. | CLOSED — sourced; [S: uniride_core/algorithms/string_split_decoder.py:350-358] [S: docs/DECISION_LOG.md:167-168] |
| U25 | 40 | 68 | The defaults were not demonstrated to be tuned for this campus problem. | CLOSED — sourced; [S: docs/DECISION_LOG.md:407] |
| U26 | 41 | 68 | Correctness and feasibility tests do not establish solution quality or comparative superiority. | CLOSED — sourced; [S: docs/DECISION_LOG.md:90] |
| U27 | 42 | 68 | Current termination uses iterations and stagnation; it is not a fixed objective-evaluation-budget experiment. | CLOSED — sourced; [S: uniride_core/algorithms/ga_split_engine.py:336-379] |
| U28 | 43 | 72 | An independent certificate reconstructs every route using the captured matrix. | CLOSED — sourced; [S: optimizer_api/verification/response_certifier.py:348-358] |
| U29 | 44 | 72 | It checks required occurrence coverage, continuity, depot closure, passenger counts and capacities, tour duration, and direction-specific ride limits. | REOPENED — WRONG_LINE; current correction 5. [S: optimizer_api/verification/response_certifier.py:333-355] |
| U30 | 45 | 72 | A 0.005-minute tolerance per reported arc accommodates two-decimal formatting, with corresponding aggregate formatting checks; it is not extra operational ride allowance. | REOPENED — WRONG_LINE; current correction 6. [S: optimizer_api/verification/response_certifier.py:129-140] [S: optimizer_api/verification/response_certifier.py:348-355] |
| U31 | 46 | 72 | Solver-reported durations alone do not establish feasibility. | CLOSED — sourced; [S: optimizer_api/verification/response_certifier.py:348-355] |
| U32 | 47 | 72 | The preview also checks whether accepted output can form consistent daily route jobs. | CLOSED — sourced; [S: src/services/dudullu-preview.ts:887-925] |
| U33 | 48 | 74 | Only accepted routes proceed to vehicle assignment. | CLOSED — sourced; [S: src/services/dudullu-preview.ts:911-932] |
| U34 | 49 | 74 | A failed certificate establishes that the returned candidate is unacceptable. | CLOSED — sourced; [S: src/services/dudullu-preview.ts:918-925] |
| U35 | 50 | 74 | Failure to generate a candidate or exhaustion of a search budget does not prove that no feasible routing exists. | CLOSED — sourced; [S: uniride_core/algorithms/string_split_decoder.py:236-247] [S: uniride_core/algorithms/ga_split_engine.py:318-379] |
| U36 | 51 | 74 | A feasibility certificate is not an optimality certificate. | CLOSED — sourced; [S: optimizer_api/verification/response_certifier.py:357-358] |
| U37 | 52 | 78 | A pickup route with duration t and arrival anchor a becomes the interval [a−t, a]; a drop-off route becomes [a, a+t]. | CLOSED — sourced; [S: src/services/dudullu-preview.ts:489-494] |
| U38 | 53 | 78 | Intervals outside the service day are rejected. | CLOSED — sourced; [S: src/services/dudullu-preview.ts:495-502] |
| U39 | 54 | 78 | A vehicle can serve multiple routes if both capacity pools suffice and each next route starts no earlier than the preceding route's end plus its cooldown. | CLOSED — sourced; [S: src/services/dudullu-preview.ts:623-634] |
| U40 | 55 | 80 | Daily assignment searches for the fewest distinct vehicles for these fixed route jobs. | CLOSED — sourced; [S: src/services/dudullu-preview.ts:829-877] |
| U41 | 56 | 80 | It explores assignments in time order, uses concurrency lower bounds, and avoids equivalent branches for vehicles with matching capacities, cooldowns, and availability. | CLOSED — sourced; [S: src/services/dudullu-preview.ts:724-742] [S: src/services/dudullu-preview.ts:784-826] |
| U42 | 57 | 80 | The default budget is 50,000 visited nodes. | CLOSED — sourced; [S: src/services/dudullu-preview.ts:6] [S: src/services/dudullu-preview.ts:745-748] [S: src/services/dudullu-preview.ts:829-835] |
| U43 | 58 | 80 | A completed search, or a feasible witness meeting a valid lower bound, can prove the minimum for the given routes. | CLOSED — sourced; [S: src/services/dudullu-preview.ts:829-877] [S: docs/DECISION_LOG.md:197-198] |
| U44 | 59 | 80 | If the budget is exhausted before proof, the result is indeterminate; an available witness gives only an upper bound. | CLOSED — sourced; [S: src/services/dudullu-preview.ts:829-877] [S: docs/DECISION_LOG.md:197-198] |
| U45 | 60 | 80 | Completed failure establishes a shortage for the fixed routes and candidate fleet, not for every alternative routing. | CLOSED — sourced; [S: src/services/dudullu-preview.ts:866-877] [S: docs/DECISION_LOG.md:203-204] |
| U46 | 61 | 82 | For identical virtual vehicles this provides a conditional fleet minimum after heuristic routing. | REOPENED — PARTIAL; current correction 7. [S: docs/DECISION_LOG.md:197-198] [S: docs/paper/results/week-2026-10-05-4sw5so/README.md:26] |
| U47 | 62 | 82 | It is not a joint minimum over all possible routes. | CLOSED — sourced; [S: docs/paper/results/week-2026-10-05-4sw5so/README.md:26] |
| U48 | 63 | 82 | Comparing its count with a heterogeneous real fleet's vehicle count is insufficient: physical capacities, cooldowns, and assignment feasibility require separate evidence. | CLOSED — sourced; [S: docs/DECISION_LOG.md:203-204] |
| U49 | 64 | 86 | The planner selects the service date, admission scenario, ride cap, tour cap, and fleet mode, then inspects the routes and fleet requirement. | REOPENED — WRONG_LINE; current correction 8. [S: src/app/(app)/admin/daily-plan/page.tsx:439-475] |
| U50 | 65 | 86 | The fleet template is supplied as a parameter; this study uses the physical minibus layout, 4 Sw + 5 So, with a 10-minute cooldown. | CLOSED — sourced; [S: src/services/daily-plan-run.ts:542-553] [S: docs/paper/results/week-2026-10-05-4sw5so/README.md:20] [S: docs/DECISION_LOG.md:354] |
| U51 | 66 | 86 | Template capacities are effective scenario inputs, although the current planning screen does not expose them as freely editable parameters. | CLOSED — sourced; [S: src/app/(app)/admin/daily-plan/page.tsx:439-472] [S: src/app/(app)/admin/daily-plan/page.tsx:491-570] |
| U52 | 67 | 88 | Results include waves, routes, longest passenger ride, capacity floors, and assignment status. | CLOSED — sourced; [S: src/services/daily-plan-view.ts:81-114] [S: src/services/daily-plan-view.ts:172-205] |
| U53 | 68 | 88 | A proven minimum, an unproven witness, and a shortage have different meanings. | CLOSED — sourced; [S: src/services/dudullu-preview.ts:866-877] [S: docs/DECISION_LOG.md:197-204] |
| U54 | 69 | 88 | Re-running with different limits supports exploring service-level trade-offs. | CLOSED — sourced; [S: src/app/(app)/admin/daily-plan/page.tsx:457-475] |
| U55 | 70 | 88 | Vehicles above the seat floor can be associated with routing constraints, overlap, or cooldown, but the observed gap does not measure each cause. | REOPENED — PARTIAL; current correction 9. [S: uniride_core/algorithms/string_split_decoder.py:337-358] [S: src/services/dudullu-preview.ts:623-634] [S: AGENTS.md:43] |
| U56 | 14 | 3 | Method note for co-authors — 10 October 2026. | CLOSED — marker/replacement; [EKSİK: dated method-note review provenance file] |
| U57 | 15 | 3 | Checked code baseline: `f7b8570` (`git rev-parse --short HEAD` after merging `WIP`). | CLOSED — marker/replacement; Checked code baseline: `f7b8570`. [EKSİK: committed method-note review provenance for this baseline] |
| U58 | 71 | 236 | Review metadata: 10 October 2026; checked code baseline `f7b8570`, obtained with `git rev-parse --short HEAD` after merging `WIP`; repository files and archived outputs inspected, with no operational data access. | CLOSED — marker/replacement; Review metadata: [EKSİK: method-note review date, checked baseline and access-history record]. |
| U59 | 72 | 236 | Ordinary source tags refer to files at that baseline. | CLOSED — marker/replacement; [EKSİK: committed provenance confirming the source blobs at the checked baseline] |
| U60 | 73 | 236 | The links below resolve from `docs/paper/` and support maintenance; they can be omitted from a publication. | CLOSED — marker/replacement; These repository links support maintenance and can be omitted from a publication. |

## Rule checks over the whole draft

| Requested rule | Result | Checked draft / repository evidence |
|---|---|---|
| No superiority, causality, global optimality or validated service-quality claim | PASS | Draft:136, 144, 182, 185, 189, 210, 212, 230; `AGENTS.md:38-43`; fleet `README.md:3, 43`; Pareto `pareto_analysis.md:185-189`. Statements are descriptive and retain explicit limits. Current correction9 asks for direct gap-calculation evidence; it is not a positive causal claim. |
| Proven is confined to fixed-route assignment, generated menus, or the planned union menu | PASS | Draft:74, 80, 82, 102, 148-185, 210, 222, 230; sensitivity `README.md:26`; fleet `README.md:41-54`; exact design:125-127. Current corrections7 and 11 concern citation completeness for the correctly limited wording, not a global-optimality claim. |
| Results labelled one snapshot week, one run per cell, seed 42, native protocol | PASS | Draft:96, 102, 136, 140, 148, 152, 177, 189, 193, 210, 230; sensitivity `README.md:19-27`; fleet `README.md:13, 33`; valid-extra READMEs. GA seed 42 remains distinct from CP-SAT seed 20261008 at draft:150. |
| Exact-solver work planned, not executed; only WP-E0 implemented | PASS | Draft:3, 220-224, 230; `uniride_core/exact/__init__.py:1-14`; `scripts/exact_archive_loader.py:1-5`; exact design:237-244. Solver limits and proof labels are expressly future-plan conditions. |
| Google duration units unverified | PASS | Draft:21; `docs/DECISION_LOG.md:139-142`; live-response EKSİK marker retained. No separate fractional-seconds report is asserted as checked evidence. |
| No scientific number absent from repository evidence | PASS | Source blobs and numerical tables are unchanged; after removing source tags and missing-evidence markers, the only newly introduced numeric token is 13:16, supported by sensitivity `schedule_verification.md:279`. The new D0 date/count is literal at `docs/DEMO_ROADMAP_2026-10-04.md:276`. Fresh numerical assertions below passed; other numeric support retains the original audit. |

**Rule violations: none** under these six content rules. The outstanding PARTIAL citation/qualification findings independently keep the verdict at DUZELT.

## Broken repository links

**None.** All 44 local link occurrences (43 distinct targets), including images and directory links, resolve from `docs/paper/` in the 08aee70 Git tree. Files must be tracked at that commit; directory targets require tracked descendants. External DOI availability was not checked.

## Internal consistency

- Weekly identical-vehicle / scenarioA peaks remain 6, 6, 6, 4 for R=50, 60, 70, 90 in the draft, sensitivity CSV and fleet weekly CSV. L3 peaks remain 7, 6, 6, 4 total vehicles, with sedan peaks4, 3, 3, 1.
- Each R retains57 waves,226 legs and 113 student-days; daily students remain 27, 21, 23, 23, 19. The 113 sum is not presented as a unique-student census. The earlier 28 count is the dated D0 inventory. Matrix provenance still declares29 locations.
- Pareto inventory remains 36 options:32 non-derived,4 day-level hybrids,28 feasible. There are six non-dominated points per R. The R60 displayed points remain(0, 7, 135.5),(1, 5, 83.6),(2, 4, 42.5),(3, 3, 18.2),(4, 2, 4.2),(6, 0, 0.0) in (owned, peak borrowed, borrowed hours). The R90 A/L4 equality remains(4, 0, 0), with differing mean rides.
- The corrected Friday R70 busy window is 13:16–13:33. The remainder of the changed resource-profile paragraph matches `schedule_verification.md:265-284`.
- The checked code baseline f7b8570 is the original draft's parent; the ordinary source blobs are unchanged through 89cfd7c and 08aee70. Historical campaign commits remain 6be127d,8ab88ca,4200acb, and L4 afc7208, with dirty-tree qualifiers. No source/result/provenance file changed in this round. The original manifest and Git-ancestry checks therefore retain their conclusions.

**Internal contradictions: none found in the requested re-check.** Citation completeness is reported separately.

## Touched-tag ledger

All 146 tags on changed lines were re-read. IDs are new draft ordinals; each row records the actual tag, so duplicate tag text remains separate occurrences.

| New ID | Draft line | Verdict | Source tag | Current correction |
|---:|---:|---|---|---|
| 1 | 3 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/README.md:3-21] | — |
| 2 | 3 | OK | [S: docs/paper/results/week-2026-10-05-fleet/README.md:13] | — |
| 3 | 3 | OK | [S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:26-36] | — |
| 4 | 3 | OK | [S: uniride_core/exact/__init__.py:1-14] | — |
| 5 | 3 | OK | [S: scripts/exact_archive_loader.py:1-5] | — |
| 6 | 3 | OK | [S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:237-242] | — |
| 7 | 15 | OK | [S: docs/DECISION_LOG.md:95-98] | — |
| 8 | 15 | PARTIAL | [S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:20] | 1 |
| 9 | 15 | OK | [S: docs/DECISION_LOG.md:97-98] | — |
| 10 | 15 | OK | [S: optimizer_api/verification/response_certifier.py:348-355] | — |
| 11 | 17 | OK | [S: docs/DECISION_LOG.md:167-168] | — |
| 12 | 17 | OK | [S: docs/DECISION_LOG.md:167-168] | — |
| 13 | 17 | OK | [S: docs/DECISION_LOG.md:167-169] | — |
| 14 | 17 | OK | [S: optimizer_api/verification/response_certifier.py:125-127] | — |
| 15 | 17 | OK | [S: optimizer_api/verification/response_certifier.py:348-355] | — |
| 16 | 19 | OK | [S: src/services/daily-plan-run.ts:522-539] | — |
| 17 | 19 | OK | [S: src/services/daily-plan-run.ts:522-539] | — |
| 18 | 19 | WRONG_LINE | [S: optimizer_api/verification/response_certifier.py:348-355] | 2 |
| 19 | 19 | PARTIAL | [S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:185-189] | 3 |
| 20 | 21 | OK | [S: src/services/fleet-scenario-run.ts:544-578] | — |
| 21 | 21 | OK | [S: docs/DECISION_LOG.md:382-386] | — |
| 22 | 21 | OK | [S: docs/DECISION_LOG.md:21] | — |
| 23 | 21 | OK | [S: docs/DECISION_LOG.md:138-142] | — |
| 24 | 21 | OK | [S: docs/DECISION_LOG.md:139] | — |
| 25 | 44 | OK | [S: src/services/daily-plan-run.ts:526-554] | — |
| 26 | 44 | OK | [S: uniride_core/algorithms/ga_split_engine.py:97-120] | — |
| 27 | 44 | OK | [S: uniride_core/algorithms/string_split_decoder.py:324-367] | — |
| 28 | 44 | OK | [S: uniride_core/algorithms/string_split_decoder.py:249-269] | — |
| 29 | 44 | OK | [S: optimizer_api/strategies/ga_split_strategy.py:44-55] | — |
| 30 | 44 | OK | [S: uniride_core/algorithms/string_split_decoder.py:337-367] | — |
| 31 | 44 | OK | [S: optimizer_api/verification/response_certifier.py:333-358] | — |
| 32 | 46 | OK | [S: uniride_core/algorithms/ga_split_engine.py:71-94] | — |
| 33 | 46 | OK | [S: uniride_core/algorithms/ga_split_engine.py:251-293] | — |
| 34 | 46 | OK | [S: uniride_core/algorithms/ga_split_engine.py:352-370] | — |
| 35 | 46 | OK | [S: docs/DECISION_LOG.md:173] | — |
| 36 | 48 | OK | [S: uniride_core/algorithms/string_split_decoder.py:324-367] | — |
| 37 | 48 | OK | [S: uniride_core/algorithms/string_split_decoder.py:202-228] | — |
| 38 | 48 | OK | [S: uniride_core/algorithms/string_split_decoder.py:190-228] | — |
| 39 | 48 | OK | [S: docs/DECISION_LOG.md:173] | — |
| 40 | 48 | OK | [S: uniride_core/algorithms/string_split_decoder.py:202-228] | — |
| 41 | 48 | OK | [S: uniride_core/algorithms/ga_split_engine.py:318-379] | — |
| 42 | 48 | OK | [S: uniride_core/algorithms/string_split_decoder.py:350-358] | — |
| 43 | 48 | OK | [S: docs/DECISION_LOG.md:167-168] | — |
| 59 | 64 | OK | [S: optimizer_api/strategies/ga_split_strategy.py:58-70] | — |
| 60 | 64 | OK | [S: optimizer_api/strategies/seed_utils.py:7-17] | — |
| 61 | 66 | OK | [S: optimizer_api/strategies/ga_split_strategy.py:72-79] | — |
| 62 | 66 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/run_manifest.json:39-53] | — |
| 63 | 66 | OK | [S: optimizer_api/strategies/seed_utils.py:7-21] | — |
| 64 | 66 | OK | [S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:251-258] | — |
| 65 | 66 | OK | [S: uniride_core/algorithms/ga_split_engine.py:79-92] | — |
| 66 | 68 | OK | [S: docs/DECISION_LOG.md:407] | — |
| 67 | 68 | OK | [S: docs/DECISION_LOG.md:90] | — |
| 68 | 68 | OK | [S: uniride_core/algorithms/ga_split_engine.py:336-379] | — |
| 69 | 72 | OK | [S: optimizer_api/verification/response_certifier.py:348-358] | — |
| 70 | 72 | WRONG_LINE | [S: optimizer_api/verification/response_certifier.py:333-355] | 5 |
| 71 | 72 | WRONG_LINE | [S: optimizer_api/verification/response_certifier.py:129-140] | 6 |
| 72 | 72 | OK | [S: optimizer_api/verification/response_certifier.py:348-355] | — |
| 73 | 72 | OK | [S: optimizer_api/verification/response_certifier.py:348-355] | — |
| 74 | 72 | OK | [S: src/services/dudullu-preview.ts:887-925] | — |
| 75 | 74 | OK | [S: src/services/dudullu-preview.ts:911-932] | — |
| 76 | 74 | OK | [S: src/services/dudullu-preview.ts:918-925] | — |
| 77 | 74 | OK | [S: uniride_core/algorithms/string_split_decoder.py:236-247] | — |
| 78 | 74 | OK | [S: uniride_core/algorithms/ga_split_engine.py:318-379] | — |
| 79 | 74 | OK | [S: optimizer_api/verification/response_certifier.py:357-358] | — |
| 80 | 78 | OK | [S: src/services/dudullu-preview.ts:489-494] | — |
| 81 | 78 | OK | [S: src/services/dudullu-preview.ts:495-502] | — |
| 82 | 78 | OK | [S: src/services/dudullu-preview.ts:623-634] | — |
| 83 | 80 | OK | [S: src/services/dudullu-preview.ts:829-877] | — |
| 84 | 80 | OK | [S: src/services/dudullu-preview.ts:724-742] | — |
| 85 | 80 | OK | [S: src/services/dudullu-preview.ts:784-826] | — |
| 86 | 80 | OK | [S: src/services/dudullu-preview.ts:6] | — |
| 87 | 80 | OK | [S: src/services/dudullu-preview.ts:745-748] | — |
| 88 | 80 | OK | [S: src/services/dudullu-preview.ts:829-835] | — |
| 89 | 80 | OK | [S: src/services/dudullu-preview.ts:829-877] | — |
| 90 | 80 | OK | [S: docs/DECISION_LOG.md:197-198] | — |
| 91 | 80 | OK | [S: src/services/dudullu-preview.ts:829-877] | — |
| 92 | 80 | OK | [S: docs/DECISION_LOG.md:197-198] | — |
| 93 | 80 | OK | [S: src/services/dudullu-preview.ts:866-877] | — |
| 94 | 80 | OK | [S: docs/DECISION_LOG.md:203-204] | — |
| 95 | 82 | PARTIAL | [S: docs/DECISION_LOG.md:197-198] | 7 |
| 96 | 82 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/README.md:26] | — |
| 97 | 82 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/README.md:26] | — |
| 98 | 82 | OK | [S: docs/DECISION_LOG.md:203-204] | — |
| 99 | 86 | WRONG_LINE | [S: src/app/(app)/admin/daily-plan/page.tsx:439-475] | 8 |
| 100 | 86 | OK | [S: src/services/daily-plan-run.ts:542-553] | — |
| 101 | 86 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/README.md:20] | — |
| 102 | 86 | OK | [S: docs/DECISION_LOG.md:354] | — |
| 103 | 86 | OK | [S: src/app/(app)/admin/daily-plan/page.tsx:439-472] | — |
| 104 | 86 | OK | [S: src/app/(app)/admin/daily-plan/page.tsx:491-570] | — |
| 105 | 88 | OK | [S: src/services/daily-plan-view.ts:81-114] | — |
| 106 | 88 | OK | [S: src/services/daily-plan-view.ts:172-205] | — |
| 107 | 88 | OK | [S: src/services/dudullu-preview.ts:866-877] | — |
| 108 | 88 | OK | [S: docs/DECISION_LOG.md:197-204] | — |
| 109 | 88 | OK | [S: src/app/(app)/admin/daily-plan/page.tsx:457-475] | — |
| 110 | 88 | OK | [S: uniride_core/algorithms/string_split_decoder.py:337-358] | — |
| 111 | 88 | OK | [S: src/services/dudullu-preview.ts:623-634] | — |
| 112 | 88 | PARTIAL | [S: AGENTS.md:43] | 9 |
| 117 | 94 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/README.md:7-21] | — |
| 118 | 94 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/README.md:20-21] | — |
| 119 | 94 | OK | [S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:251-255] | — |
| 120 | 94 | OK | [S: uniride_core/algorithms/ga_split_engine.py:79-92] | — |
| 124 | 98 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:1-2] | — |
| 125 | 98 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:5] | — |
| 126 | 98 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:259] | — |
| 127 | 98 | OK | [S: docs/DECISION_LOG.md:197-198] | — |
| 172 | 144 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:267] | — |
| 173 | 144 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:272] | — |
| 174 | 144 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:277] | — |
| 175 | 144 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:265-284] | — |
| 176 | 144 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:259] | — |
| 177 | 144 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/README.md:27] | — |
| 178 | 144 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:265] | — |
| 179 | 144 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:270] | — |
| 180 | 144 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:275] | — |
| 181 | 144 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:280] | — |
| 182 | 144 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:267-284] | — |
| 183 | 144 | PARTIAL | [S: docs/paper/results/week-2026-10-05-4sw5so/README.md:12] | 10 |
| 184 | 144 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:267] | — |
| 185 | 144 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:272] | — |
| 186 | 144 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:277] | — |
| 187 | 144 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/schedule_verification.md:268-284] | — |
| 209 | 152 | OK | [S: docs/paper/results/week-2026-10-05-fleet/README.md:13] | — |
| 210 | 152 | OK | [S: docs/paper/results/week-2026-10-05-fleet/README.md:33] | — |
| 211 | 152 | OK | [S: docs/paper/results/week-2026-10-05-fleet/README.md:47] | — |
| 212 | 152 | OK | [S: docs/paper/results/week-2026-10-05-fleet/scenario_weekly.csv:2-14] | — |
| 213 | 152 | OK | [S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:30-34] | — |
| 214 | 152 | PARTIAL | [S: docs/paper/results/week-2026-10-05-fleet/README.md:41-56] | 11 |
| 302 | 210 | OK | [S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:9-34] | — |
| 303 | 210 | OK | [S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:9] | — |
| 304 | 210 | OK | [S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:9] | — |
| 305 | 210 | OK | [S: docs/paper/results/week-2026-10-05-fleet/README.md:33] | — |
| 306 | 210 | OK | [S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:185-189] | — |
| 307 | 212 | OK | [S: AGENTS.md:38-54] | — |
| 308 | 212 | OK | [S: docs/paper/results/week-2026-10-05-fleet/README.md:3] | — |
| 309 | 212 | OK | [S: docs/paper/results/week-2026-10-05-fleet/README.md:33-43] | — |
| 310 | 212 | OK | [S: AGENTS.md:38-39] | — |
| 322 | 218 | OK | [S: docs/DECISION_LOG.md:344-348] | — |
| 323 | 218 | OK | [S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:185] | — |
| 324 | 218 | OK | [S: docs/designs/HETEROGENEOUS_FLEET_DESIGN.md:34-37] | — |
| 325 | 218 | OK | [S: docs/paper/results/week-2026-10-05-fleet/README.md:13-43] | — |
| 326 | 218 | OK | [S: docs/DECISION_LOG.md:119-123] | — |
| 344 | 228 | OK | [S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:30-34] | — |
| 345 | 228 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/run_manifest.json:63-67] | — |
| 346 | 228 | OK | [S: docs/DEMO_ROADMAP_2026-10-04.md:276] | — |
| 347 | 228 | OK | [S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:22] | — |
| 348 | 228 | OK | [S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:185-188] | — |

## Random unchanged-tag sample

The 210 eligible tags were on byte-identical unchanged lines and were matched by line and occurrence position to old IDs. For each, compute SHA-256 of the UTF-8 string `08aee7016a91ccd5d58bbfb0a1682ba702db1d99|unchanged-tag|<old ordinal ID>`; sort ascending by the hexadecimal digest and select the first 30. This gives a deterministic pseudorandom sample without replacement. The revision hash is the audit sampling seed; it is separate from the campaigns' GA seed 42.

| Sample order | New ID | Old ID | Draft line | Verdict | Source tag | Current correction |
|---:|---:|---:|---:|---|---|---|
| 1 | 329 | 249 | 220 | OK | [S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:86] | — |
| 2 | 231 | 151 | 173 | WRONG_LINE | [S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:3] | 12 |
| 3 | 250 | 170 | 182 | WRONG_LINE | [S: docs/paper/results/week-2026-10-05-fleet/README.md:3] | 13 |
| 4 | 142 | 62 | 114 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:10] | — |
| 5 | 116 | 37 | 90 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:1-2] | — |
| 6 | 45 | 15 | 50 | OK | [S: src/services/fleet-scenario-run.ts:493-508] | — |
| 7 | 356 | 276 | 230 | OK | [S: AGENTS.md:38-54] | — |
| 8 | 335 | 255 | 222 | OK | [S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:258] | — |
| 9 | 195 | 115 | 148 | OK | [S: docs/paper/results/week-2026-10-05-fleet/README.md:58-68] | — |
| 10 | 46 | 16 | 50 | OK | [S: optimizer_api/strategies/ga_split_strategy.py:58-70] | — |
| 11 | 292 | 212 | 202 | OK | [S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:113] | — |
| 12 | 244 | 164 | 181 | OK | [S: docs/paper/results/week-2026-10-05-fleet/car_usage_windows.csv:39] | — |
| 13 | 275 | 195 | 191 | OK | [S: docs/paper/results/week-2026-10-05-fleet/pareto_analysis.md:7] | — |
| 14 | 197 | 117 | 150 | OK | [S: uniride_core/algorithms/typed_split_decoder.py:150-172] | — |
| 15 | 246 | 166 | 182 | OK | [S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:7-22] | — |
| 16 | 136 | 56 | 108 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:4] | — |
| 17 | 200 | 120 | 150 | OK | [S: docs/paper/results/week-2026-10-05-fleet/extra/L4/README.md:13] | — |
| 18 | 219 | 139 | 160 | OK | [S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:11] | — |
| 19 | 199 | 119 | 150 | OK | [S: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md:18] | — |
| 20 | 222 | 142 | 163 | OK | [S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:14] | — |
| 21 | 353 | 273 | 230 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/README.md:25-27] | — |
| 22 | 166 | 86 | 136 | OK | [S: docs/paper/results/week-2026-10-05-4sw5so/summary.csv:2-21] | — |
| 23 | 220 | 140 | 161 | OK | [S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:12] | — |
| 24 | 51 | 21 | 58 | OK | [S: optimizer_api/strategies/ga_split_strategy.py:58-70] | — |
| 25 | 230 | 150 | 171 | OK | [S: docs/paper/results/week-2026-10-05-fleet/weekly_summary.md:22] | — |
| 26 | 249 | 169 | 182 | OK | [S: docs/paper/results/week-2026-10-05-fleet/scenario_weekly.csv:9] | — |
| 27 | 245 | 165 | 181 | OK | [S: docs/paper/results/week-2026-10-05-fleet/car_usage_windows.csv:56-57] | — |
| 28 | 248 | 168 | 182 | OK | [S: docs/paper/results/week-2026-10-05-fleet/scenario_weekly.csv:6] | — |
| 29 | 58 | 28 | 63 | OK | [S: uniride_core/algorithms/ga_split_engine.py:378-382] | — |
| 30 | 53 | 23 | 60 | PARTIAL | [S: optimizer_api/strategies/ga_split_strategy.py:58-70] | 4 |

## Notes (do not affect the verdict)

- Several source suggestions in the first report were too short or lacked a qualification. The writer applied them verbatim. The reopened U-items above correct that earlier verification gap; they are not evidence of a new runtime defect. The sample and changed-line checks also found retained citation problems that round one had missed.
- Suggested objections to student-count tags at draft:152 and 228 were rejected: `weekly_summary.md:30-34` contains the correct rows and its table header at 28 is valid context. The student-day sum 113 is a direct sum of those five rows. Expanding the tag solely to include the header is unnecessary.
- The suggested objection to draft:218's joint-optimum limitation was rejected: fleet `README.md:13-43` identifies the fixed scenario/type pools and explicitly denies a global minimum over all possible routes. This supports the stated evidence limitation.
- Nine explicit EKSİK markers remain: review-date/baseline provenance (draft:3), live Google units/fractional handling and outside-snapshot research (21), deployment-inspection record (66), replay evidence (214), and review/access/source-blob/research provenance (236). These are acknowledged missing evidence, not accepted positive findings.
- The archived fleet README's30-seconds-per-stage wording is historical. Draft:150 describes the current shared call allowance with `typed_day_selection.py:211-220`; this distinction remains intact. The 171-day replay was not executed or represented as verified.
- CodeGraph `index` failed, `init --yes` reported already initialized, and the index retry failed with the same active-daemon-stop-verification error. No shared daemon or process was stopped; pinned `git show` reads supplied the evidence.
- No operational data, Google response, solver benchmark, AMPL solve, application build or runtime test suite was queried or executed for this documentation-only re-check. External literature facts/DOI availability were not re-audited.

## Verification record

Read-only Git checks were executed from the absolute repository path `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide`:

```text
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide rev-parse docs/method-note-2026-10-10
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide show --stat --oneline 08aee7016a91ccd5d58bbfb0a1682ba702db1d99
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide show -s --format=%P 08aee7016a91ccd5d58bbfb0a1682ba702db1d99
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide diff --unified=4 89cfd7c5cd23a04ee5d2e720dd4d2c844a28b4a2 08aee7016a91ccd5d58bbfb0a1682ba702db1d99 -- docs/paper/DAILY_STUDENT_TRANSPORT_PLANNING_METHOD.md
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide ls-tree -r --name-only 08aee7016a91ccd5d58bbfb0a1682ba702db1d99
```

Each of the 42 cited paths was read with `git -C <absolute repository> show 08aee7016a91ccd5d58bbfb0a1682ba702db1d99:<source-path>`. The SVG correction path was read the same way. Source equality was checked with `git diff --name-only` from 89cfd7c to 08aee70 and from f7b8570 to 08aee70, restricted to the full42-path cited-source list; both outputs were empty.

Node.js standard-library assertions passed for the following 13 focused checks (these are offline evidence checks, not application tests):

- Only draft changed between writer commits.
- Source blobs equal round one and the stated baseline.
- All source tags resolve and have valid ranges.
- All 60 requested correction strings appear.
- Changed/unchanged/sample partition.
- Repository links resolve.
- Sensitivity and all-large weekly vehicle counts agree.
- Per-R 57 waves / 226 legs / 113 student-days.
- Pareto option counts preserved.
- Six non-dominated points at every R.
- R60 displayed Pareto points unchanged.
- Friday R70 corrected interval.
- New scientific numeric token exists in cited source.

The report ledger and proposed correction tags were additionally checked for complete/unique IDs, exactly 60 U-items, exactly 30 sample occurrences and valid pinned source ranges. Git diff whitespace and commit-scope checks are required before this report is committed.
