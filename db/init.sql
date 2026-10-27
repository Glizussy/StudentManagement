CREATE TABLE IF NOT EXISTS students (
  id         SERIAL PRIMARY KEY,
  name       TEXT NOT NULL,
  email      TEXT NOT NULL UNIQUE,
  course     TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO students (name, email, course) VALUES
  ('Aarav Sharma', 'aarav.sharma@example.com', 'Computer Engineering'),
  ('Diya Patel', 'diya.patel@example.com', 'Information Technology'),
  ('Rohan Mehta', 'rohan.mehta@example.com', 'Electronics'),
  ('Ananya Iyer', 'ananya.iyer@example.com', 'Data Science'),
  ('Kabir Singh', 'kabir.singh@example.com', 'Mechanical Engineering')
ON CONFLICT (email) DO NOTHING;
