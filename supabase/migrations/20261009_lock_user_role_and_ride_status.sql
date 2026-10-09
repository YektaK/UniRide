-- =============================================================================
-- QW1: lock the user role and the ride-request status in RLS
-- Audit: docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md  C1, C1.b, and the
--        live SECURITY DEFINER finding (Appendix J row C1.c).
--
-- What this migration changes
--   1. public.users
--      - users_insert_self : INSERT TO authenticated, only for the caller's own
--                            id AND role = 'student'.
--      - users_update_own  : UPDATE TO authenticated, now with a WITH CHECK
--                            (id may not be re-pointed to another user).
--      - prevent_role_change() trigger function (SECURITY DEFINER, pinned
--        search_path) fired BEFORE INSERT OR UPDATE OF role. service_role may do
--        anything; everyone else may only INSERT role 'student' and may never
--        change an existing role. It does NOT depend on is_admin() (absent live).
--      - Any other INSERT/UPDATE policy on users is dropped first, because
--        permissive policies are OR-ed and a leftover one would void the lock.
--   2. public.ride_requests (C1.b)
--      - INSERT only with status pending_admin_approval or
--        pending_student_confirmation and no vehicle / actual times.
--      - UPDATE only to status cancelled_by_student on the caller's own rows.
--      - Other INSERT/UPDATE policies are dropped first (same reason).
--      Admin / planner writes go through the BFF with the service-role key.
--   3. get_available_drivers() and get_route_plans_with_students(date, text):
--      SECURITY DEFINER functions that bypass RLS. search_path is pinned to
--      public and EXECUTE is revoked from PUBLIC, anon and authenticated
--      (no caller exists in src/ or optimizer_api/; service_role keeps access).
--
-- Safety
--   - Idempotent: re-runnable. Policies/trigger are dropped before creation,
--     functions use CREATE OR REPLACE, ALTER/REVOKE are guarded by existence.
--   - Safe on the live state: it does not reference is_admin().
--   - Existing rows are not modified. Existing admins/drivers keep their role.
--
-- Operator note: to change a role by hand in the SQL editor, run first
--   select set_config('request.jwt.claims', '{"role":"service_role"}', true);
-- inside the same transaction, or use the service-role admin route.
--
-- Test: supabase/tests/20261009_role_lock.sql (BEGIN ... ROLLBACK).
-- =============================================================================

BEGIN;

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ride_requests ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- 1. users
-- ---------------------------------------------------------------------------

-- Remove every INSERT/UPDATE policy under any name (live names are not guaranteed).
DO $$
DECLARE p record;
BEGIN
  FOR p IN
    SELECT policyname FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'users' AND cmd IN ('INSERT', 'UPDATE')
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.users', p.policyname);
  END LOOP;
END $$;

DROP POLICY IF EXISTS "users_insert_self" ON public.users;
CREATE POLICY "users_insert_self" ON public.users
  FOR INSERT TO authenticated
  WITH CHECK (auth.uid() = id AND role = 'student');

DROP POLICY IF EXISTS "users_update_own" ON public.users;
CREATE POLICY "users_update_own" ON public.users
  FOR UPDATE TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

CREATE OR REPLACE FUNCTION public.prevent_role_change()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- Server-side admin operations (service-role key) are exempt.
  IF auth.role() = 'service_role' THEN
    RETURN NEW;
  END IF;

  IF TG_OP = 'INSERT' THEN
    IF NEW.role IS DISTINCT FROM 'student' THEN
      RAISE EXCEPTION 'Only service_role may create non-student users';
    END IF;
  ELSIF TG_OP = 'UPDATE' THEN
    IF NEW.role IS DISTINCT FROM OLD.role THEN
      RAISE EXCEPTION 'Direct role modification not allowed - use server-side admin endpoints';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS enforce_no_role_change ON public.users;
CREATE TRIGGER enforce_no_role_change
  BEFORE INSERT OR UPDATE OF role ON public.users
  FOR EACH ROW
  EXECUTE FUNCTION public.prevent_role_change();

-- ---------------------------------------------------------------------------
-- 2. ride_requests (C1.b)
-- ---------------------------------------------------------------------------

DO $$
DECLARE p record;
BEGIN
  FOR p IN
    SELECT policyname FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'ride_requests' AND cmd IN ('INSERT', 'UPDATE')
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.ride_requests', p.policyname);
  END LOOP;
END $$;

DROP POLICY IF EXISTS "ride_requests_insert_own" ON public.ride_requests;
CREATE POLICY "ride_requests_insert_own" ON public.ride_requests
  FOR INSERT TO authenticated
  WITH CHECK (auth.uid() = user_id
              AND status IN ('pending_admin_approval', 'pending_student_confirmation')
              AND vehicle_id IS NULL
              AND actual_pickup_time IS NULL
              AND actual_dropoff_time IS NULL);

DROP POLICY IF EXISTS "ride_requests_update_own" ON public.ride_requests;
CREATE POLICY "ride_requests_update_own" ON public.ride_requests
  FOR UPDATE TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id AND status = 'cancelled_by_student');

-- ---------------------------------------------------------------------------
-- 3. SECURITY DEFINER RPCs that bypass RLS (no caller in src/ or optimizer_api/)
-- ---------------------------------------------------------------------------

DO $$
BEGIN
  IF to_regprocedure('public.get_available_drivers()') IS NOT NULL THEN
    ALTER FUNCTION public.get_available_drivers() SET search_path = public;
    REVOKE ALL ON FUNCTION public.get_available_drivers() FROM public, anon, authenticated;
    GRANT EXECUTE ON FUNCTION public.get_available_drivers() TO service_role;
  END IF;

  IF to_regprocedure('public.get_route_plans_with_students(date, text)') IS NOT NULL THEN
    ALTER FUNCTION public.get_route_plans_with_students(date, text) SET search_path = public;
    REVOKE ALL ON FUNCTION public.get_route_plans_with_students(date, text) FROM public, anon, authenticated;
    GRANT EXECUTE ON FUNCTION public.get_route_plans_with_students(date, text) TO service_role;
  END IF;
END $$;

COMMIT;
