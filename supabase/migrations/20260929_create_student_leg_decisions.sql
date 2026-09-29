CREATE TABLE IF NOT EXISTS public.student_leg_decisions (
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  service_date DATE NOT NULL,
  direction TEXT NOT NULL CHECK (direction IN ('pickup', 'dropoff')),
  decision TEXT NOT NULL CHECK (decision IN ('confirmed', 'cancelled')),
  decided_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  flexibility_minutes INTEGER NOT NULL DEFAULT 0
    CHECK (flexibility_minutes BETWEEN 0 AND 1439),
  PRIMARY KEY (user_id, service_date, direction)
);

CREATE OR REPLACE FUNCTION public.set_student_leg_decided_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    NEW.decided_at := clock_timestamp();
  ELSIF ROW(NEW.decision, NEW.flexibility_minutes) IS DISTINCT FROM
        ROW(OLD.decision, OLD.flexibility_minutes) THEN
    NEW.decided_at := clock_timestamp();
  ELSE
    NEW.decided_at := OLD.decided_at;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS student_leg_decisions_set_decided_at
  ON public.student_leg_decisions;
CREATE TRIGGER student_leg_decisions_set_decided_at
BEFORE INSERT OR UPDATE ON public.student_leg_decisions
FOR EACH ROW EXECUTE FUNCTION public.set_student_leg_decided_at();

ALTER TABLE public.student_leg_decisions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.student_leg_decisions FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.student_leg_decisions TO service_role;
