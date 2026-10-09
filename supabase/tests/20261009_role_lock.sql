-- QW1 (audit C1 / C1.b): behavioural test for
-- supabase/migrations/20261009_lock_user_role_and_ride_status.sql
--
-- HOW TO RUN (owner, AFTER applying the migration):
--   Supabase Dashboard -> SQL Editor -> paste this whole file -> Run
--   (or: psql "$SUPABASE_DB_URL" -f supabase/tests/20261009_role_lock.sql).
--   Prefer a staging/branch database. The script is BEGIN ... ROLLBACK, so it
--   leaves no rows behind, but it still executes against whatever DB you point it at.
--   Success: every step emits NOTICE 'PASS ...' and the final NOTICE says
--   'ALL ROLE-LOCK TESTS PASSED'. Any failure raises an exception ('FAIL ...')
--   and the transaction aborts (nothing is committed either way).
--
-- Notes:
--   * Uses fixed UUIDs and impersonates users via set local role + request.jwt.claims.
--   * Only touches public.users and public.ride_requests inside the transaction.
--   * The Dashboard SQL editor shows NOTICEs in the "Messages"/results pane; if it
--     only shows the last statement, run it through psql instead.
BEGIN;

-- Seed as the session owner (superuser): two students.
-- The trigger allows an INSERT of role 'student' without claims.
INSERT INTO public.users (id, email, name, role)
VALUES ('00000000-0000-4000-8000-0000000000a1', 'qw1-student-a@example.invalid', 'QW1 A', 'student'),
       ('00000000-0000-4000-8000-0000000000a2', 'qw1-student-b@example.invalid', 'QW1 B', 'student');

INSERT INTO public.ride_requests
  (id, user_id, type, requested_pickup_time, requested_dropoff_time,
   pickup_location, dropoff_location, status)
VALUES ('00000000-0000-4000-8000-0000000000b1', '00000000-0000-4000-8000-0000000000a1',
        'adhoc', now(), now(), '{}'::jsonb, '{}'::jsonb, 'pending_admin_approval');

-- ---------- impersonate student A (authenticated) ----------
SELECT set_config('request.jwt.claims',
  '{"sub":"00000000-0000-4000-8000-0000000000a1","role":"authenticated"}', true);
SELECT set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-0000000000a1', true);
SELECT set_config('request.jwt.claim.role', 'authenticated', true);
SET LOCAL ROLE authenticated;

-- T1: cannot update own role
DO $$ BEGIN
  BEGIN
    UPDATE public.users SET role = 'admin' WHERE id = '00000000-0000-4000-8000-0000000000a1';
    RAISE EXCEPTION 'FAIL T1: own role update to admin succeeded';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM LIKE 'FAIL%' THEN RAISE; END IF;
    RAISE NOTICE 'PASS T1: update own role blocked (%)', SQLERRM;
  END;
END $$;

-- T2: cannot insert a row with role admin or driver (own id)
DO $$ BEGIN
  BEGIN
    INSERT INTO public.users (id, email, name, role)
    VALUES ('00000000-0000-4000-8000-0000000000a1', 'qw1-x@example.invalid', 'X', 'admin');
    RAISE EXCEPTION 'FAIL T2a: insert role=admin succeeded';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM LIKE 'FAIL%' THEN RAISE; END IF;
    RAISE NOTICE 'PASS T2a: insert admin blocked (%)', SQLERRM;
  END;
  BEGIN
    INSERT INTO public.users (id, email, name, role)
    VALUES ('00000000-0000-4000-8000-0000000000a1', 'qw1-y@example.invalid', 'Y', 'driver');
    RAISE EXCEPTION 'FAIL T2b: insert role=driver succeeded';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM LIKE 'FAIL%' THEN RAISE; END IF;
    RAISE NOTICE 'PASS T2b: insert driver blocked (%)', SQLERRM;
  END;
END $$;

-- T3: ordinary self-update (non-role column) still works and role is unchanged
DO $$ DECLARE r text; BEGIN
  UPDATE public.users SET name = 'QW1 A renamed' WHERE id = '00000000-0000-4000-8000-0000000000a1';
  SELECT role INTO r FROM public.users WHERE id = '00000000-0000-4000-8000-0000000000a1';
  IF r IS DISTINCT FROM 'student' THEN RAISE EXCEPTION 'FAIL T3: role is %', r; END IF;
  RAISE NOTICE 'PASS T3: self update of name works, role still student';
END $$;

-- T4: cannot update another user's row (RLS USING) - must change nothing
DO $$ DECLARE n int; BEGIN
  UPDATE public.users SET name = 'hijack' WHERE id = '00000000-0000-4000-8000-0000000000a2';
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 0 THEN RAISE EXCEPTION 'FAIL T4: updated % foreign rows', n; END IF;
  RAISE NOTICE 'PASS T4: foreign row not updatable';
END $$;

-- T5: ride_requests status self-approval
DO $$ BEGIN
  BEGIN
    INSERT INTO public.ride_requests
      (user_id, type, requested_pickup_time, requested_dropoff_time,
       pickup_location, dropoff_location, status)
    VALUES ('00000000-0000-4000-8000-0000000000a1', 'adhoc', now(), now(), '{}'::jsonb, '{}'::jsonb, 'confirmed');
    RAISE EXCEPTION 'FAIL T5a: insert status=confirmed succeeded';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM LIKE 'FAIL%' THEN RAISE; END IF;
    RAISE NOTICE 'PASS T5a: insert confirmed blocked (%)', SQLERRM;
  END;
  BEGIN
    UPDATE public.ride_requests SET status = 'confirmed' WHERE id = '00000000-0000-4000-8000-0000000000b1';
    RAISE EXCEPTION 'FAIL T5b: update to confirmed succeeded';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM LIKE 'FAIL%' THEN RAISE; END IF;
    RAISE NOTICE 'PASS T5b: update to confirmed blocked (%)', SQLERRM;
  END;
  BEGIN
    UPDATE public.ride_requests SET status = 'completed' WHERE id = '00000000-0000-4000-8000-0000000000b1';
    RAISE EXCEPTION 'FAIL T5c: update to completed succeeded';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM LIKE 'FAIL%' THEN RAISE; END IF;
    RAISE NOTICE 'PASS T5c: update to completed blocked (%)', SQLERRM;
  END;
  BEGIN
    INSERT INTO public.ride_requests
      (user_id, type, requested_pickup_time, requested_dropoff_time,
       pickup_location, dropoff_location, status, vehicle_id)
    VALUES ('00000000-0000-4000-8000-0000000000a1', 'adhoc', now(), now(), '{}'::jsonb, '{}'::jsonb,
            'pending_admin_approval', '00000000-0000-4000-8000-0000000000c1');
    RAISE EXCEPTION 'FAIL T5d: insert with vehicle_id succeeded';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM LIKE 'FAIL%' THEN RAISE; END IF;
    RAISE NOTICE 'PASS T5d: insert with vehicle_id blocked (%)', SQLERRM;
  END;
END $$;

-- T6: allowed ride_requests flows still work
DO $$ BEGIN
  INSERT INTO public.ride_requests
    (user_id, type, requested_pickup_time, requested_dropoff_time,
     pickup_location, dropoff_location, status)
  VALUES ('00000000-0000-4000-8000-0000000000a1', 'adhoc', now(), now(), '{}'::jsonb, '{}'::jsonb, 'pending_student_confirmation');
  UPDATE public.ride_requests SET status = 'cancelled_by_student'
   WHERE id = '00000000-0000-4000-8000-0000000000b1';
  RAISE NOTICE 'PASS T6: pending insert and cancel by student allowed';
END $$;

-- T7: anon / authenticated cannot call the SECURITY DEFINER RPCs
RESET ROLE;
DO $$ BEGIN
  IF has_function_privilege('anon', 'public.get_available_drivers()', 'EXECUTE')
     OR has_function_privilege('authenticated', 'public.get_available_drivers()', 'EXECUTE')
     OR has_function_privilege('anon', 'public.get_route_plans_with_students(date, text)', 'EXECUTE')
     OR has_function_privilege('authenticated', 'public.get_route_plans_with_students(date, text)', 'EXECUTE')
  THEN RAISE EXCEPTION 'FAIL T7: anon/authenticated can still EXECUTE a SECURITY DEFINER RPC'; END IF;
  RAISE NOTICE 'PASS T7: RPCs not executable by anon/authenticated';
END $$;

-- ---------- service_role ----------
SELECT set_config('request.jwt.claims', '{"role":"service_role"}', true);
SELECT set_config('request.jwt.claim.role', 'service_role', true);
SET LOCAL ROLE service_role;

-- T8: service_role can still create an admin and change a role
DO $$ BEGIN
  INSERT INTO public.users (id, email, name, role)
  VALUES ('00000000-0000-4000-8000-0000000000a3', 'qw1-admin@example.invalid', 'QW1 Admin', 'admin');
  UPDATE public.users SET role = 'driver' WHERE id = '00000000-0000-4000-8000-0000000000a2';
  RAISE NOTICE 'PASS T8: service_role can create admin and change a role';
END $$;

RESET ROLE;
DO $$ BEGIN RAISE NOTICE 'ALL ROLE-LOCK TESTS PASSED'; END $$;
ROLLBACK;
