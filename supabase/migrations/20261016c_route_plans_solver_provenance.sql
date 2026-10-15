-- =============================================================================
-- Solver provenance saved with each route plan
-- Decision: docs/DECISION_LOG.md S08 (owner decision 2026-10-15); audit H17 / M26.
--
-- What this adds
--   public.route_plans.solver_provenance jsonb NULL
--     { algorithm_requested, algorithm_used, fallback_reason,
--       effective_config_source, effective_seed } - only the keys the optimizer
--     reported at save time. The API allowlists the keys (src/services/solver-provenance.ts).
--   NULL means "unknown": every row saved before this migration, and plans from an
--   optimizer that reported no provenance, stay NULL. There is no backfill and no default.
--   A CHECK keeps the column NULL or a JSON object (no scalar, no array).
--
-- Not changed
--   No policy, grant or role lock. The route_plans policies from 20261009 / 20261010 are
--   table-level (no column lists), so the new column is covered by them as is: admins
--   read and write it, drivers read it only for confirmed/active/completed plans.
--
-- Safety: idempotent (IF NOT EXISTS, guarded constraint), single transaction, no row is
-- modified. Apply BEFORE deploying the app version that sends solver_provenance, otherwise
-- saving a plan with provenance fails (the app omits the key when it has none).
--
-- Operator note: paste the WHOLE file and press Run; do not use "Run selected".
-- =============================================================================

BEGIN;

ALTER TABLE public.route_plans
  ADD COLUMN IF NOT EXISTS solver_provenance jsonb NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.route_plans'::regclass
      AND conname = 'route_plans_solver_provenance_is_object'
  ) THEN
    ALTER TABLE public.route_plans
      ADD CONSTRAINT route_plans_solver_provenance_is_object
      CHECK (solver_provenance IS NULL OR jsonb_typeof(solver_provenance) = 'object');
  END IF;
END $$;

COMMIT;
