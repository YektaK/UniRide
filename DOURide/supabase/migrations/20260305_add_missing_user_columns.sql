-- Missing fields from earlier implementation:
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password_hint TEXT;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS home_coordinates JSONB;
