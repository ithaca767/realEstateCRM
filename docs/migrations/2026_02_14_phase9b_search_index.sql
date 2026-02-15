CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS search_index (
  id bigserial PRIMARY KEY,
  user_id bigint NOT NULL,
  object_type text NOT NULL,
  object_id bigint NOT NULL,
  contact_id bigint,
  label text,
  search_text text NOT NULL,
  embedding vector(1536) NOT NULL,
  updated_at timestamp without time zone NOT NULL DEFAULT NOW(),
  created_at timestamp without time zone NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, object_type, object_id)
);

CREATE INDEX IF NOT EXISTS search_index_user_type_idx
  ON search_index (user_id, object_type);

CREATE INDEX IF NOT EXISTS search_index_user_object_idx
  ON search_index (user_id, object_type, object_id);

CREATE INDEX IF NOT EXISTS search_index_embedding_idx
  ON search_index USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
