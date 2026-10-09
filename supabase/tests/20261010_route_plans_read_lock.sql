-- C1.d: behavioural test for supabase/migrations/20261010_route_plans_read_lock.sql
--
-- HOW TO RUN (owner, AFTER applying the migration; prefer staging):
--   Dashboard -> SQL Editor -> paste this whole file -> Run
--   (or: psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f supabase/tests/20261010_route_plans_read_lock.sql).
--   BEGIN ... ROLLBACK: nothing is committed. Success = every step emits NOTICE 'PASS ...'
--   and the last NOTICE says 'ALL ROUTE-PLANS READ-LOCK TESTS PASSED'. Failure raises 'FAIL ...'.
-- Only the expected SQLSTATE counts as a pass for blocked writes: 42501 (insufficient
-- privilege / RLS violation). Any other error raises 'FAIL: unexpected error'.
BEGIN;

-- Seed as session owner, with a service_role claim so the role trigger allows non-student users.
SELECT set_config('request.jwt.claims', '{"role":"service_role"}', true);
SELECT set_config('request.jwt.claim.role', 'service_role', true);
INSERT INTO public.users (id, email, name, role) VALUES
  ('00000000-0000-4000-8000-0000000000c1', 'rp-student@example.invalid', 'RP Student', 'student'),
  ('00000000-0000-4000-8000-0000000000c2', 'rp-driver@example.invalid',  'RP Driver',  'driver'),
  ('00000000-0000-4000-8000-0000000000c3', 'rp-admin@example.invalid',   'RP Admin',   'admin');

INSERT INTO public.route_plans (id, plan_date, direction, algorithm_used, total_vehicles, total_duration_minutes, status, routes)
VALUES
  ('00000000-0000-4000-8000-0000000000d1', '2099-01-01', 'pickup', 'rp-test', 1, 10, 'confirmed', '[]'::jsonb),
  ('00000000-0000-4000-8000-0000000000d2', '2099-01-01', 'pickup', 'rp-test', 1, 10, 'draft',     '[]'::jsonb);

-- ---------- anon ----------
SELECT set_config('request.jwt.claims', '{"role":"anon"}', true);
SELECT set_config('request.jwt.claim.sub', '', true);
SELECT set_config('request.jwt.claim.role', 'anon', true);
SET LOCAL ROLE anon;

DO $$ DECLARE n int; BEGIN
  BEGIN
    SELECT count(*) INTO n FROM public.route_plans;
    IF n <> 0 THEN RAISE EXCEPTION 'FAIL T1: anon read % route_plans rows', n; END IF;
    RAISE NOTICE 'PASS T1: anon sees 0 route_plans rows';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM LIKE 'FAIL%' THEN RAISE; END IF;
    IF SQLSTATE <> '42501' THEN RAISE EXCEPTION 'FAIL: unexpected error % (%)', SQLERRM, SQLSTATE; END IF;
    RAISE NOTICE 'PASS T1: anon denied at privilege level (%)', SQLERRM;
  END;
END $$;

-- ---------- student ----------
SELECT set_config('request.jwt.claims',
  '{"sub":"00000000-0000-4000-8000-0000000000c1","role":"authenticated"}', true);
SELECT set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-0000000000c1', true);
SELECT set_config('request.jwt.claim.role', 'authenticated', true);
SET LOCAL ROLE authenticated;

DO $$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM public.route_plans;
  IF n <> 0 THEN RAISE EXCEPTION 'FAIL T2: student read % route_plans rows', n; END IF;
  RAISE NOTICE 'PASS T2: student sees 0 route_plans rows';
  BEGIN
    INSERT INTO public.route_plans (plan_date, direction, algorithm_used, total_vehicles, total_duration_minutes, routes)
    VALUES ('2099-01-02', 'pickup', 'rp-test', 1, 1, '[]'::jsonb);
    RAISE EXCEPTION 'FAIL T3: student inserted a route plan';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM LIKE 'FAIL%' THEN RAISE; END IF;
    IF SQLSTATE <> '42501' THEN RAISE EXCEPTION 'FAIL: unexpected error % (%)', SQLERRM, SQLSTATE; END IF;
    RAISE NOTICE 'PASS T3: student insert blocked (%)', SQLERRM;
  END;
END $$;

-- ---------- driver ----------
SELECT set_config('request.jwt.claims',
  '{"sub":"00000000-0000-4000-8000-0000000000c2","role":"authenticated"}', true);
SELECT set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-0000000000c2', true);

DO $$ DECLARE n int; d int; BEGIN
  SELECT count(*) INTO n FROM public.route_plans WHERE id = '00000000-0000-4000-8000-0000000000d1';
  IF n <> 1 THEN RAISE EXCEPTION 'FAIL T4: driver cannot read the confirmed plan (% rows)', n; END IF;
  SELECT count(*) INTO d FROM public.route_plans WHERE id = '00000000-0000-4000-8000-0000000000d2';
  IF d <> 0 THEN RAISE EXCEPTION 'FAIL T5: driver can read a draft plan'; END IF;
  RAISE NOTICE 'PASS T4/T5: driver reads the published plan, not the draft';
  UPDATE public.route_plans SET notes = 'x' WHERE id = '00000000-0000-4000-8000-0000000000d1';
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 0 THEN RAISE EXCEPTION 'FAIL T6: driver updated a plan'; END IF;
  RAISE NOTICE 'PASS T6: driver update affects 0 rows';
END $$;

-- ---------- admin ----------
SELECT set_config('request.jwt.claims',
  '{"sub":"00000000-0000-4000-8000-0000000000c3","role":"authenticated"}', true);
SELECT set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-0000000000c3', true);

DO $$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM public.route_plans WHERE algorithm_used = 'rp-test';
  IF n <> 2 THEN RAISE EXCEPTION 'FAIL T7: admin sees % of 2 plans (draft included)', n; END IF;
  INSERT INTO public.route_plans (id, plan_date, direction, algorithm_used, total_vehicles, total_duration_minutes, routes)
  VALUES ('00000000-0000-4000-8000-0000000000d3', '2099-01-03', 'dropoff', 'rp-test', 1, 1, '[]'::jsonb);
  UPDATE public.route_plans SET notes = 'edited' WHERE id = '00000000-0000-4000-8000-0000000000d3';
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 1 THEN RAISE EXCEPTION 'FAIL T8: admin update affected % rows', n; END IF;
  DELETE FROM public.route_plans WHERE id = '00000000-0000-4000-8000-0000000000d3';
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 1 THEN RAISE EXCEPTION 'FAIL T9: admin delete affected % rows', n; END IF;
  INSERT INTO public.sandbox_scenarios (name, vehicles) VALUES ('rp-test', '[]'::jsonb);
  RAISE NOTICE 'PASS T7-T9: admin has full CRUD on route_plans and can write sandbox_scenarios';
END $$;

-- ---------- student on sandbox_scenarios ----------
SELECT set_config('request.jwt.claims',
  '{"sub":"00000000-0000-4000-8000-0000000000c1","role":"authenticated"}', true);
SELECT set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-0000000000c1', true);

DO $$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM public.sandbox_scenarios;
  IF n <> 0 THEN RAISE EXCEPTION 'FAIL T10: student read % sandbox_scenarios rows', n; END IF;
  RAISE NOTICE 'PASS T10: student sees 0 sandbox_scenarios rows';
END $$;

-- ---------- policy role lists ----------
RESET ROLE;
DO $$ DECLARE p record; BEGIN
  FOR p IN SELECT tablename, policyname FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename IN ('route_plans', 'sandbox_scenarios', 'admin_settings', 'routes', 'vehicles')
      AND (roles::text[] && ARRAY['public', 'anon'])
  LOOP
    RAISE EXCEPTION 'FAIL T11: policy % on % still applies to public/anon', p.policyname, p.tablename;
  END LOOP;
  RAISE NOTICE 'PASS T11: no policy on the five tables applies to public/anon';
END $$;

DO $$ BEGIN RAISE NOTICE 'ALL ROUTE-PLANS READ-LOCK TESTS PASSED'; END $$;
ROLLBACK;
