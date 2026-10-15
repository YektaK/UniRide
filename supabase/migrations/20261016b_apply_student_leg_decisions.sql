-- =============================================================================
-- Apply the student trip-confirmation table to the LIVE database (hardened)
-- Audit: docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md (student_leg_decisions live-apply entry 2026-10-15)
-- Owner decision 2026-10-15: create the table now.
--
-- Why
--   supabase/migrations/20260929_create_student_leg_decisions.sql (commit a8b18c9) was never
--   applied. Read-only checks on 2026-10-15 found that neither public.student_leg_decisions nor
--   public.set_student_leg_decided_at() exists live. As a result the Dudullu readiness probe
--   (legDecisionsReadable) reports false, the daily plan preview emits LEG_DECISIONS_UNAVAILABLE
--   and blocks outside the demo mode, and POST/GET /api/ride-confirmation answer 503.
--   The 2026-09-29 file is historical and is deliberately NOT edited.
--
-- What this migration does
--   Brings the live database to the SAME contract as 20260929 (identical columns, checks and
--   primary key; same trigger semantics; RLS on with no policies; anon/authenticated revoked;
--   service_role granted), with the trigger function hardened like the other live trigger
--   functions (20261015_time_matrix_updated_at.sql, 20261016_update_updated_at_search_path.sql):
--   SECURITY INVOKER, SET search_path = '' and the schema-qualified pg_catalog.clock_timestamp()
--   (Supabase advisor lint 0011 function_search_path_mutable).
--
--   Contract in short: one row per (user_id, service_date, direction); direction in
--   ('pickup','dropoff'); decision in ('confirmed','cancelled'); flexibility_minutes 0..1439;
--   decided_at is set by the trigger: on INSERT, and on UPDATE only when decision or
--   flexibility_minutes actually changes (otherwise the old decided_at is kept).
--   Access is server-side only: the app reaches the table through the service_role key
--   (getSupabaseAdmin), which bypasses RLS; there are no policies on purpose.
--
-- Safety: single transaction, idempotent (CREATE TABLE IF NOT EXISTS, CREATE OR REPLACE
--   FUNCTION, DROP TRIGGER IF EXISTS + CREATE TRIGGER), no data is read, changed or deleted,
--   nothing is dropped except the trigger of this very table. CREATE TABLE IF NOT EXISTS does
--   not alter a table that already exists: run the pre-check below first; it must return NULL.
--
-- Operator notes
--   * Paste the WHOLE file and press Run; do not use "Run selected".
--   * Pre-check (read-only, expect one row with a NULL value):
--       select to_regclass('public.student_leg_decisions');   -- expect NULL before applying
--   * Post-apply verification (read-only), expected results in brackets:
--       -- 1. columns [6 rows: user_id uuid NO, service_date date NO, direction text NO,
--       --             decision text NO, decided_at timestamptz NO default now(),
--       --             flexibility_minutes integer NO default 0]
--       select column_name, data_type, is_nullable, column_default
--         from information_schema.columns
--        where table_schema = 'public' and table_name = 'student_leg_decisions'
--        order by ordinal_position;
--       -- 2. constraints [PK (user_id, service_date, direction); FK to public.users(id) ON DELETE
--       --             CASCADE; three CHECKs for direction, decision, flexibility_minutes]
--       select conname, contype, pg_get_constraintdef(oid)
--         from pg_constraint where conrelid = 'public.student_leg_decisions'::regclass order by 1;
--       -- 3. RLS on, no policies [relrowsecurity = true; 0 policy rows]
--       select relrowsecurity from pg_class where oid = 'public.student_leg_decisions'::regclass;
--       select policyname from pg_policies where tablename = 'student_leg_decisions';
--       -- 4. grants [only service_role: DELETE, INSERT, SELECT, UPDATE; no anon/authenticated]
--       select grantee, privilege_type from information_schema.role_table_grants
--        where table_schema = 'public' and table_name = 'student_leg_decisions'
--          and grantee in ('anon', 'authenticated', 'service_role') order by 1, 2;
--       -- 5. function [prosecdef = false; proconfig = {search_path=""}]
--       select prosecdef, proconfig from pg_proc
--        where oid = 'public.set_student_leg_decided_at()'::regprocedure;
--       -- 6. trigger [1 row: student_leg_decisions_set_decided_at, BEFORE INSERT OR UPDATE, row-level]
--       select tgname, tgenabled, pg_get_triggerdef(oid) from pg_trigger
--        where tgrelid = 'public.student_leg_decisions'::regclass and not tgisinternal;
--   * Afterwards the advisor must not list set_student_leg_decided_at under lint 0011, and
--     /api/admin/dudullu-readiness should report legDecisionsReadable = true.
--   * Rollback (only if needed and the table holds no wanted rows):
--       drop table public.student_leg_decisions;  drop function public.set_student_leg_decided_at();
-- Mirrored in supabase/schema.sql.
-- =============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.student_leg_decisions (
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  service_date DATE NOT NULL,
  direction TEXT NOT NULL CHECK (direction IN ('pickup', 'dropoff')),
  decision TEXT NOT NULL CHECK (decision IN ('confirmed', 'cancelled')),
  decided_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  flexibility_minutes INTEGER NOT NULL DEFAULT 0
    CHECK (flexibility_minutes BETWEEN 0 AND 1439),
  PRIMARY KEY (user_id, service_date, direction)
);

CREATE OR REPLACE FUNCTION public.set_student_leg_decided_at()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    NEW.decided_at := pg_catalog.clock_timestamp();
  ELSIF ROW(NEW.decision, NEW.flexibility_minutes) IS DISTINCT FROM
        ROW(OLD.decision, OLD.flexibility_minutes) THEN
    NEW.decided_at := pg_catalog.clock_timestamp();
  ELSE
    NEW.decided_at := OLD.decided_at;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS student_leg_decisions_set_decided_at
  ON public.student_leg_decisions;
CREATE TRIGGER student_leg_decisions_set_decided_at
BEFORE INSERT OR UPDATE ON public.student_leg_decisions
FOR EACH ROW EXECUTE FUNCTION public.set_student_leg_decided_at();

ALTER TABLE public.student_leg_decisions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.student_leg_decisions FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.student_leg_decisions TO service_role;

COMMIT;
