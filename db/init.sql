-- Student API — schema + seed
-- Runs only on an empty pgdata volume (docker-entrypoint-initdb.d)

CREATE TABLE IF NOT EXISTS students (
  id         SERIAL PRIMARY KEY,
  name       TEXT NOT NULL,
  email      TEXT NOT NULL UNIQUE,
  course     TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5 seed rows, idempotent
INSERT INTO students (name, email, course) VALUES
  ('Alice Johnson',  'alice@example.com',   'Computer Science'),
  ('Bob Smith',      'bob@example.com',     'Mathematics'),
  ('Carol White',    'carol@example.com',   'Physics'),
  ('David Lee',      'david@example.com',   'Chemistry'),
  ('Eva Martinez',   'eva@example.com',     'Biology')
ON CONFLICT (email) DO NOTHING;
