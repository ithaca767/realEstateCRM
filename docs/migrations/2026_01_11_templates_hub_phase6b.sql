-- Phase 6b: Templates Hub (non-destructive, additive)
-- Creates a single templates table for reusable client communications.

CREATE TABLE IF NOT EXISTS templates (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'General',
  delivery_type TEXT NOT NULL DEFAULT 'either', -- email | text | either
  body TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '',
  is_locked BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_templates_category ON templates(category);
CREATE INDEX IF NOT EXISTS idx_templates_locked ON templates(is_locked);
CREATE INDEX IF NOT EXISTS idx_templates_updated_at ON templates(updated_at DESC);
