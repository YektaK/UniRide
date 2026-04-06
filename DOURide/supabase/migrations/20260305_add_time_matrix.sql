CREATE TABLE IF NOT EXISTS public.time_matrix (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    origin_code TEXT NOT NULL,
    destination_code TEXT NOT NULL,
    duration_minutes NUMERIC NOT NULL,
    distance_meters NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(origin_code, destination_code)
);

-- RLS policies 
ALTER TABLE public.time_matrix ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read access for authenticated users" 
ON public.time_matrix FOR SELECT 
TO authenticated 
USING (true);

-- Allow service role full access
CREATE POLICY "Allow full access for service role" 
ON public.time_matrix FOR ALL 
TO service_role 
USING (true);
