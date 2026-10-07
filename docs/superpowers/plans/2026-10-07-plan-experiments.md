# Daily plan experiment runner

Approved scope: the 2026-10-07 batch handoff. Work on `feat/batch-experiments` from `83f519c`; preserve main/WIP, use SELECT only, never publish credentials, and leave integration to the lead.

1. Extract `runDailyPlan` with injected reader, optimizer fetch and clock. Keep authentication, validation, defaults and JSON in the route unchanged. Add a nonempty parity fixture and retain all existing route tests.
2. Reuse that computation in a CLI for dates, ride/tour limits and fleet mode. Export anonymized responses, daily/weekly metrics, input provenance and repeat comparisons. Test parsing, weighted passenger ride means, closed-tour minutes and aggregation without live services.
3. Document usage and one future-page proposal. Run full Vitest, TypeScript, lint and diff checks. Run a read-only Monday smoke if configured; run the twenty combinations only after matching the reference result. Record exact evidence in the uncommitted handoff report.

The runner describes operational GA plans under native termination. Conditional vehicle-assignment minimality is not global route optimality; sensitivity results do not establish algorithm superiority. Missing or failed daily results must remain visible in weekly coverage.
