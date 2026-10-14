-- =============================================================================
-- M4 / MT2 (staleness half): date the travel-time DATA, not the load
-- Audit: docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md  Appendix J row M4
-- Decision: docs/DECISION_LOG.md T09 (C2 gate stays fail-closed; the age is shown).
--
-- Why
--   The optimizer reloads public.time_matrix before every snapshot, so the age of the
--   LOAD is ~0 s and says nothing about how old the travel times are. The data age is
--   max(updated_at) over the loaded rows. Live state found 2026-10-15: 812 rows, no
--   updated_at column, created_at 2026-03-05 on every row.
--
-- What this migration changes
--   1. public.time_matrix.updated_at timestamptz, NOT NULL, DEFAULT now().
--      Existing rows are backfilled with coalesce(created_at, now()) BEFORE the
--      constraint and default are set, so the history is not reset to "today".
--   2. BEFORE UPDATE trigger time_matrix_set_updated_at: sets updated_at = now()
--      on every update (an upsert's update path included). New rows get the default.
--      The function is SECURITY INVOKER, search_path = '' and fully schema-qualified.
--
-- Safety: idempotent (IF NOT EXISTS / CREATE OR REPLACE / DROP TRIGGER IF EXISTS),
-- single transaction, no arc value changes, no policy or grant changes. The optimizer
-- tolerates the column being absent, so this can be applied independently of a deploy.
--
-- Operator note: paste the WHOLE file and press Run; do not use "Run selected".
-- Mirrored in supabase/schema.sql.
-- =============================================================================

BEGIN;

ALTER TABLE public.time_matrix
    ADD COLUMN IF NOT EXISTS updated_at timestamptz;

UPDATE public.time_matrix
SET updated_at = coalesce(created_at, now())
WHERE updated_at IS NULL;

ALTER TABLE public.time_matrix
    ALTER COLUMN updated_at SET DEFAULT now(),
    ALTER COLUMN updated_at SET NOT NULL;

CREATE OR REPLACE FUNCTION public.set_time_matrix_updated_at()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
BEGIN
    NEW.updated_at := pg_catalog.now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS time_matrix_set_updated_at ON public.time_matrix;
CREATE TRIGGER time_matrix_set_updated_at
    BEFORE UPDATE ON public.time_matrix
    FOR EACH ROW EXECUTE FUNCTION public.set_time_matrix_updated_at();

COMMIT;
