-- =============================================================================
-- Supabase security advisor, lint 0011 function_search_path_mutable
-- https://supabase.com/docs/guides/database/database-linter?lint=0011_function_search_path_mutable
-- Audit: docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md (go-live security entry 2026-10-15)
--
-- Why
--   The advisor flags public.update_updated_at_column() because its search_path is
--   role-mutable (proconfig is null): the name now() inside the body is resolved through
--   whatever search_path the calling role has, so a schema earlier in that path could
--   shadow it. Live definition found 2026-10-15 (read-only): SECURITY INVOKER plpgsql,
--   body  NEW.updated_at = NOW(); RETURN NEW;  no search_path setting.
--
-- What this migration changes
--   Re-defines the SAME function (same name, no arguments, RETURNS trigger) with
--   SET search_path = '' and the schema-qualified pg_catalog.now(). It stays SECURITY
--   INVOKER. The behaviour is identical: NEW.updated_at is set to the transaction time.
--
-- Why the 8 triggers are untouched
--   CREATE OR REPLACE FUNCTION keeps the function's identity (OID), so the BEFORE UPDATE
--   triggers on users, weekly_schedules, ride_requests, vehicles, route_assignments,
--   admin_settings, route_plans and sandbox_scenarios keep working and are not re-created.
--   The function is NOT dropped (a DROP would fail on the dependent triggers or, with
--   CASCADE, remove them).
--
-- Safety: idempotent (CREATE OR REPLACE), single transaction, no data, policy or grant
-- changes. Rolling back means re-running the old body without the SET clause.
--
-- Operator notes:
--   * Paste the WHOLE file and press Run; do not use "Run selected".
--   * Afterwards the advisor should no longer list update_updated_at_column under lint 0011.
--   * Other functions on the advisor list (if any) are outside this migration.
-- Mirrored in supabase/schema.sql.
-- =============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
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

COMMIT;
