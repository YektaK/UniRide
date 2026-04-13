-- UniRide Supabase Database Schema
-- Run this in Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('student', 'admin', 'driver')),
  student_number TEXT UNIQUE,
  home_address TEXT,
  home_coordinates JSONB,
  accessibility_needs TEXT[],
  disability_type TEXT CHECK (disability_type IN ('Sw', 'So')),
  location_code TEXT,
  weekly_schedule_id UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Weekly Schedules table
CREATE TABLE IF NOT EXISTS weekly_schedules (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  entries JSONB NOT NULL DEFAULT '[]'::jsonb,
  last_updated TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ride Requests table
CREATE TABLE IF NOT EXISTS ride_requests (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('scheduled', 'adhoc')),
  requested_pickup_time TIMESTAMPTZ NOT NULL,
  requested_dropoff_time TIMESTAMPTZ NOT NULL,
  actual_pickup_time TIMESTAMPTZ,
  actual_dropoff_time TIMESTAMPTZ,
  pickup_location JSONB NOT NULL,
  dropoff_location JSONB NOT NULL,
  status TEXT NOT NULL CHECK (status IN (
    'pending_student_confirmation',
    'confirmed',
    'cancelled_by_student',
    'cancelled_by_admin',
    'in_progress',
    'completed',
    'pending_admin_approval'
  )),
  vehicle_id UUID,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vehicles table
CREATE TABLE IF NOT EXISTS vehicles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('minibus', 'bus', 'van')),
  plate_number TEXT,
  wheelchair_capacity INTEGER NOT NULL DEFAULT 0,
  seating_capacity INTEGER NOT NULL DEFAULT 0,
  cooldown_minutes INTEGER NOT NULL DEFAULT 10,
  status TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'maintenance')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Routes table
CREATE TABLE IF NOT EXISTS routes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  date DATE NOT NULL,
  timeslot TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('pickup', 'dropoff')),
  waypoints TEXT[] NOT NULL,
  optimized_path JSONB NOT NULL,
  total_duration INTEGER NOT NULL, -- in minutes
  total_distance DECIMAL(10, 2) NOT NULL, -- in kilometers
  vehicle_count INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(date, timeslot)
);

-- Route Assignments table
CREATE TABLE IF NOT EXISTS route_assignments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  date DATE NOT NULL,
  vehicle_id UUID NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
  driver_id UUID REFERENCES users(id) ON DELETE SET NULL,
  route_id UUID NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
  student_ids UUID[] NOT NULL,
  pickup_time TIMESTAMPTZ NOT NULL,
  estimated_dropoff_time TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('scheduled', 'in_progress', 'completed', 'cancelled')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('ride_confirmation', 'ride_reminder', 'route_update', 'system')),
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  related_request_id UUID REFERENCES ride_requests(id) ON DELETE CASCADE,
  related_route_id UUID REFERENCES routes(id) ON DELETE CASCADE,
  read BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Admin Settings table
CREATE TABLE IF NOT EXISTS admin_settings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  notification_time TEXT NOT NULL,
  arrival_notification_template TEXT NOT NULL,
  departure_notification_template TEXT NOT NULL,
  departure_reminder_time TEXT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(id)
);

-- Time Matrix table for distance/duration caching
CREATE TABLE IF NOT EXISTS time_matrix (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    origin_code TEXT NOT NULL,
    destination_code TEXT NOT NULL,
    duration_minutes NUMERIC NOT NULL,
    distance_meters NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(origin_code, destination_code)
);

-- Route Plans table for optimization result persistence
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

-- Sandbox Scenarios table for IE sandbox mode
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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_student_number ON users(student_number);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_weekly_schedules_user_id ON weekly_schedules(user_id);
CREATE INDEX IF NOT EXISTS idx_ride_requests_user_id ON ride_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_ride_requests_status ON ride_requests(status);
CREATE INDEX IF NOT EXISTS idx_ride_requests_pickup_time ON ride_requests(requested_pickup_time);
CREATE INDEX IF NOT EXISTS idx_route_assignments_date ON route_assignments(date);
CREATE INDEX IF NOT EXISTS idx_route_assignments_vehicle_id ON route_assignments(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_route_assignments_driver_id ON route_assignments(driver_id);
CREATE INDEX IF NOT EXISTS idx_routes_date ON routes(date);
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(read);
CREATE INDEX IF NOT EXISTS idx_time_matrix_origin_dest ON time_matrix(origin_code, destination_code);
CREATE INDEX IF NOT EXISTS idx_route_plans_date ON route_plans(plan_date);
CREATE INDEX IF NOT EXISTS idx_route_plans_status ON route_plans(status);
CREATE INDEX IF NOT EXISTS idx_sandbox_scenarios_created_by ON sandbox_scenarios(created_by);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at (drop first if exists)
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_weekly_schedules_updated_at ON weekly_schedules;
CREATE TRIGGER update_weekly_schedules_updated_at BEFORE UPDATE ON weekly_schedules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_ride_requests_updated_at ON ride_requests;
CREATE TRIGGER update_ride_requests_updated_at BEFORE UPDATE ON ride_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_vehicles_updated_at ON vehicles;
CREATE TRIGGER update_vehicles_updated_at BEFORE UPDATE ON vehicles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_route_assignments_updated_at ON route_assignments;
CREATE TRIGGER update_route_assignments_updated_at BEFORE UPDATE ON route_assignments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_admin_settings_updated_at ON admin_settings;
CREATE TRIGGER update_admin_settings_updated_at BEFORE UPDATE ON admin_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_route_plans_updated_at ON route_plans;
CREATE TRIGGER update_route_plans_updated_at BEFORE UPDATE ON route_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_sandbox_scenarios_updated_at ON sandbox_scenarios;
CREATE TRIGGER update_sandbox_scenarios_updated_at BEFORE UPDATE ON sandbox_scenarios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE ride_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE vehicles ENABLE ROW LEVEL SECURITY;
ALTER TABLE routes ENABLE ROW LEVEL SECURITY;
ALTER TABLE route_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE time_matrix ENABLE ROW LEVEL SECURITY;
ALTER TABLE route_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE sandbox_scenarios ENABLE ROW LEVEL SECURITY;
