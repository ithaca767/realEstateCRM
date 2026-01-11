-- Phase 6b: template archiving
ALTER TABLE public.templates
  ADD COLUMN IF NOT EXISTS archived_at timestamp with time zone;

CREATE INDEX IF NOT EXISTS idx_templates_archived_at
  ON public.templates (archived_at);
