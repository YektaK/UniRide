-- UniRide Row Level Security Policies (Fixed)
-- Run this in Supabase SQL Editor
-- These policies avoid infinite recursion by using auth.uid() directly

-- First, enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE ride_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE vehicles ENABLE ROW LEVEL SECURITY;
ALTER TABLE routes ENABLE ROW LEVEL SECURITY;
ALTER TABLE route_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_settings ENABLE ROW LEVEL SECURITY;

-- Drop existing policies to avoid conflicts
DO $$ 
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT policyname, tablename FROM pg_policies WHERE schemaname = 'public') LOOP
        EXECUTE 'DROP POLICY IF EXISTS "' || r.policyname || '" ON ' || r.tablename;
    END LOOP;
END $$;

-- Helper function to check if user is admin
CREATE OR REPLACE FUNCTION is_admin()
RETURNS BOOLEAN AS $$
BEGIN
  RETURN (
    SELECT role = 'admin'
    FROM public.users
    WHERE id = auth.uid()
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==================== USERS POLICIES ====================

-- Users can read their own data
CREATE POLICY "users_select_own"
  ON users FOR SELECT
  USING (auth.uid() = id);

-- Users can insert themselves (for registration)
CREATE POLICY "users_insert_self"
  ON users FOR INSERT
  WITH CHECK (auth.uid() = id);

-- Users can update their own data (role is protected by trigger below)
CREATE POLICY "users_update_own"
  ON users FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- Trigger: prevent self-role-escalation
-- Regular authenticated users cannot change the `role` column.
-- Service-role connections (server-side admin operations) are exempt.
CREATE OR REPLACE FUNCTION prevent_role_change()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- Allow service_role to change the role column (admin operations via server)
  IF auth.role() = 'service_role' THEN
    RETURN NEW;
  END IF;

  IF NEW.role IS DISTINCT FROM OLD.role THEN
    RAISE EXCEPTION 'Direct role modification not allowed - use server-side admin endpoints';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS enforce_no_role_change ON users;
CREATE TRIGGER enforce_no_role_change
  BEFORE UPDATE OF role ON users
  FOR EACH ROW
  EXECUTE FUNCTION prevent_role_change();

-- Service role can do anything (for admin operations via server)
-- Note: This requires using service_role key on server-side

-- ==================== WEEKLY SCHEDULES POLICIES ====================

-- Users can manage their own schedules
CREATE POLICY "schedules_select_own"
  ON weekly_schedules FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "schedules_insert_own"
  ON weekly_schedules FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "schedules_update_own"
  ON weekly_schedules FOR UPDATE
  USING (auth.uid() = user_id);

-- ==================== RIDE REQUESTS POLICIES ====================

-- Users can view their own ride requests
CREATE POLICY "ride_requests_select_own"
  ON ride_requests FOR SELECT
  USING (auth.uid() = user_id);

-- Users can create their own ride requests
CREATE POLICY "ride_requests_insert_own"
  ON ride_requests FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can update their own ride requests
CREATE POLICY "ride_requests_update_own"
  ON ride_requests FOR UPDATE
  USING (auth.uid() = user_id);

-- ==================== VEHICLES POLICIES ====================

-- All authenticated users can view vehicles
CREATE POLICY "vehicles_select_all"
  ON vehicles FOR SELECT
  USING (auth.uid() IS NOT NULL);

-- Admin can manage vehicles
CREATE POLICY "vehicles_all_admin"
  ON vehicles FOR ALL
  TO authenticated
  USING (is_admin())
  WITH CHECK (is_admin());

-- ==================== ROUTES POLICIES ====================

-- All authenticated users can view routes
CREATE POLICY "routes_select_all"
  ON routes FOR SELECT
  USING (auth.uid() IS NOT NULL);

-- Admin can manage routes
CREATE POLICY "routes_all_admin"
  ON routes FOR ALL
  TO authenticated
  USING (is_admin())
  WITH CHECK (is_admin());

-- ==================== ROUTE ASSIGNMENTS POLICIES ====================

-- Users can view assignments they're part of
CREATE POLICY "route_assignments_select_own"
  ON route_assignments FOR SELECT
  USING (auth.uid() = ANY(student_ids) OR auth.uid() = driver_id);

-- Admin can manage route assignments
CREATE POLICY "route_assignments_all_admin"
  ON route_assignments FOR ALL
  TO authenticated
  USING (is_admin())
  WITH CHECK (is_admin());

-- ==================== NOTIFICATIONS POLICIES ====================

-- Users can view their own notifications
CREATE POLICY "notifications_select_own"
  ON notifications FOR SELECT
  USING (auth.uid() = user_id);

-- Users can update their own notifications (mark as read)
CREATE POLICY "notifications_update_own"
  ON notifications FOR UPDATE
  USING (auth.uid() = user_id);

-- System can create notifications (using service role)
CREATE POLICY "notifications_insert_system"
  ON notifications FOR INSERT TO service_role
  WITH CHECK (true);

-- ==================== ADMIN SETTINGS POLICIES ====================

-- All authenticated users can view admin settings
CREATE POLICY "admin_settings_select_all"
  ON admin_settings FOR SELECT
  USING (auth.uid() IS NOT NULL);

-- Note: For admin-only operations (managing users, vehicles, etc.),
-- use service_role key on the server side or create a separate
-- admin API endpoint that verifies the user's role first.
