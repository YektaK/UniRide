-- Migration: Add disability_type and location_code to users table
-- Run this in Supabase SQL Editor if tables already exist

-- Add disability_type column (Sw = wheelchair, So = other disability)
ALTER TABLE users ADD COLUMN IF NOT EXISTS disability_type TEXT 
  CHECK (disability_type IN ('Sw', 'So'));

-- Add location_code column (for test data: Sw1, So5, etc.)
ALTER TABLE users ADD COLUMN IF NOT EXISTS location_code TEXT;

-- Add index for faster filtering by disability type
CREATE INDEX IF NOT EXISTS idx_users_disability_type ON users(disability_type);

-- Verify changes
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'users' 
  AND column_name IN ('disability_type', 'location_code');
