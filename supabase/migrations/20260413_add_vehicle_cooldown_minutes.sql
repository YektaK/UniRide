-- Add cooldown_minutes to vehicles for pickup/dropoff gap configuration
ALTER TABLE vehicles
ADD COLUMN IF NOT EXISTS cooldown_minutes INTEGER NOT NULL DEFAULT 10;
