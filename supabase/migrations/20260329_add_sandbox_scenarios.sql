-- UniRide Sandbox Scenarios Migration
-- Run this in Supabase SQL Editor
-- Added: sandbox_scenarios table for IE sandbox mode scenarios

-- sandbox_scenarios table
CREATE TABLE IF NOT EXISTS sandbox_scenarios (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  vehicles JSONB NOT NULL,
  student_ids UUID[] DEFAULT '{}'::uuid[],
  time_window_minutes INTEGER DEFAULT 0,
  notes TEXT,
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index
CREATE INDEX IF NOT EXISTS idx_sandbox_scenarios_created_by ON sandbox_scenarios(created_by);

-- Trigger
DROP TRIGGER IF EXISTS update_sandbox_scenarios_updated_at ON sandbox_scenarios;
CREATE TRIGGER update_sandbox_scenarios_updated_at BEFORE UPDATE ON sandbox_scenarios
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS
ALTER TABLE sandbox_scenarios ENABLE ROW LEVEL SECURITY;

-- RLS Policy
CREATE POLICY "Admins can CRUD sandbox_scenarios" ON sandbox_scenarios
  FOR ALL USING (
    EXISTS (SELECT 1 FROM users WHERE id = auth.uid() AND role = 'admin')
  );

COMMENT ON TABLE sandbox_scenarios IS 'Stores sandbox mode scenarios for IE analysis';