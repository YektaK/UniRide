-- =============================================================================
-- C1.d: route_plans (published plans) readable by anonymous users
-- Audit: docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md  Appendix J row C1.d
--
-- Live state found 2026-10-09 (all policies had roles {public}):
--   route_plans  "Drivers can read route_plans"  SELECT USING status IN (...)
--                -> no TO clause and no auth check: the anon key could read
--                   confirmed/active/completed plans (routes, student counts).
--   route_plans / sandbox_scenarios "Admins can CRUD ..." ALL, no WITH CHECK
--   admin_settings_select_all, routes_select_all, vehicles_select_all:
--                SELECT USING (auth.uid() IS NOT NULL)  (harmless, but {public})
--
-- What this migration changes (semantics otherwise unchanged)
--   1. route_plans read: TO authenticated, only status confirmed/active/completed,
--      and only for users whose public.users.role is driver or admin. Students
--      and anonymous callers get no rows. Every app reader goes through
--      /api/route-plans (requireAdmin + service-role key), so nothing breaks.
--   2. "Admins can CRUD route_plans" / "... sandbox_scenarios": TO authenticated,
--      same admin EXISTS in USING and now also in WITH CHECK.
--   3. admin_settings / routes / vehicles select_all: TO authenticated, same
--      qual (removes anon from the role list; behaviour unchanged).
--   The admin test relies on users.role being trustworthy; the 20261009 migration
--   locks it (users_insert_self, trigger prevent_role_change).
--
-- Safety: idempotent (DROP POLICY IF EXISTS then CREATE), single transaction,
-- no row is modified. A final check aborts the transaction if any policy on the
-- five tables still applies to public/anon.
--
-- Operator note: paste the WHOLE file and press Run; do not use "Run selected".
--
-- Test: supabase/tests/20261010_route_plans_read_lock.sql (BEGIN ... ROLLBACK).
-- =============================================================================

BEGIN;

ALTER TABLE public.route_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sandbox_scenarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admin_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.routes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vehicles ENABLE ROW LEVEL SECURITY;

-- 1. route_plans: published plans readable by drivers and admins only
DROP POLICY IF EXISTS "Drivers can read route_plans" ON public.route_plans;
CREATE POLICY "Drivers can read route_plans" ON public.route_plans
  FOR SELECT TO authenticated
  USING (
    status IN ('confirmed', 'active', 'completed')
    AND EXISTS (SELECT 1 FROM public.users u WHERE u.id = auth.uid() AND u.role IN ('driver', 'admin'))
  );

-- 2. admin CRUD: authenticated only, WITH CHECK mirrors USING
DROP POLICY IF EXISTS "Admins can CRUD route_plans" ON public.route_plans;
CREATE POLICY "Admins can CRUD route_plans" ON public.route_plans
  FOR ALL TO authenticated
  USING (EXISTS (SELECT 1 FROM public.users u WHERE u.id = auth.uid() AND u.role = 'admin'))
  WITH CHECK (EXISTS (SELECT 1 FROM public.users u WHERE u.id = auth.uid() AND u.role = 'admin'));

DROP POLICY IF EXISTS "Admins can CRUD sandbox_scenarios" ON public.sandbox_scenarios;
CREATE POLICY "Admins can CRUD sandbox_scenarios" ON public.sandbox_scenarios
  FOR ALL TO authenticated
  USING (EXISTS (SELECT 1 FROM public.users u WHERE u.id = auth.uid() AND u.role = 'admin'))
  WITH CHECK (EXISTS (SELECT 1 FROM public.users u WHERE u.id = auth.uid() AND u.role = 'admin'));

-- 3. select_all policies: same qual, no longer {public}
DROP POLICY IF EXISTS "admin_settings_select_all" ON public.admin_settings;
CREATE POLICY "admin_settings_select_all" ON public.admin_settings
  FOR SELECT TO authenticated USING (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS "routes_select_all" ON public.routes;
CREATE POLICY "routes_select_all" ON public.routes
  FOR SELECT TO authenticated USING (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS "vehicles_select_all" ON public.vehicles;
CREATE POLICY "vehicles_select_all" ON public.vehicles
  FOR SELECT TO authenticated USING (auth.uid() IS NOT NULL);

-- Guard: no policy on these tables may still apply to public/anon.
DO $$
DECLARE p record;
BEGIN
  FOR p IN
    SELECT tablename, policyname FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename IN ('route_plans', 'sandbox_scenarios', 'admin_settings', 'routes', 'vehicles')
      AND (roles::text[] && ARRAY['public', 'anon'])
  LOOP
    RAISE EXCEPTION 'policy % on public.% is still open to the public or anon role; review and drop it',
      p.policyname, p.tablename;
  END LOOP;
END $$;

COMMIT;
