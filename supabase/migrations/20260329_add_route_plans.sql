-- UniRide Route Plans Migration
-- Run this in Supabase SQL Editor
-- Added: route_plans table for optimization result persistence

-- Enable UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- route_plans table
CREATE TABLE IF NOT EXISTS route_plans (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  plan_date DATE NOT NULL,
  direction TEXT NOT NULL CHECK (direction IN ('pickup', 'dropoff')),
  algorithm_used TEXT NOT NULL,
  clustering_used TEXT DEFAULT 'kmeans',
  total_vehicles INTEGER NOT NULL,
  total_duration_minutes FLOAT NOT NULL,
  execution_time_seconds FLOAT,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'confirmed', 'active', 'completed', 'cancelled')),
  routes JSONB NOT NULL,
  student_count INTEGER,
  driver_assignments JSONB DEFAULT '[]'::jsonb,
  notes TEXT,
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  confirmed_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_route_plans_date ON route_plans(plan_date);
CREATE INDEX IF NOT EXISTS idx_route_plans_status ON route_plans(status);
CREATE INDEX IF NOT EXISTS idx_route_plans_direction ON route_plans(direction);
CREATE INDEX IF NOT EXISTS idx_route_plans_created_by ON route_plans(created_by);

-- Updated_at trigger
DROP TRIGGER IF EXISTS update_route_plans_updated_at ON route_plans;
CREATE TRIGGER update_route_plans_updated_at BEFORE UPDATE ON route_plans
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security
ALTER TABLE route_plans ENABLE ROW LEVEL SECURITY;

-- RLS Policies
-- Admins can do everything
CREATE POLICY "Admins can CRUD route_plans" ON route_plans
  FOR ALL USING (
    EXISTS (SELECT 1 FROM users WHERE id = auth.uid() AND role = 'admin')
  );

-- Drivers can read active/confirmed plans
CREATE POLICY "Drivers can read route_plans" ON route_plans
  FOR SELECT USING (status IN ('confirmed', 'active', 'completed'));

-- Function to get route_plans with student details
CREATE OR REPLACE FUNCTION get_route_plans_with_students(p_date DATE, p_direction TEXT)
RETURNS TABLE (
  id UUID,
  plan_date DATE,
  direction TEXT,
  algorithm_used TEXT,
  total_vehicles INTEGER,
  total_duration_minutes FLOAT,
  status TEXT,
  routes JSONB,
  student_count INTEGER,
  driver_assignments JSONB,
  created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT
    rp.id,
    rp.plan_date,
    rp.direction,
    rp.algorithm_used,
    rp.total_vehicles,
    rp.total_duration_minutes,
    rp.status,
    rp.routes,
    rp.student_count,
    rp.driver_assignments,
    rp.created_at
  FROM route_plans rp
  WHERE rp.plan_date = p_date AND rp.direction = p_direction
  ORDER BY rp.created_at DESC;
END;
$$;

-- Function to get available drivers for assignment
CREATE OR REPLACE FUNCTION get_available_drivers()
RETURNS TABLE (
  id UUID,
  name TEXT,
  email TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT u.id, u.name, u.email
  FROM users u
  WHERE u.role = 'driver'
  ORDER BY u.name;
END;
$$;

-- Comment
COMMENT ON TABLE route_plans IS 'Stores optimization results for persistence';
COMMENT ON COLUMN route_plans.direction IS 'pickup or dropoff';
COMMENT ON COLUMN route_plans.status IS 'draft -> confirmed -> active -> completed/cancelled';