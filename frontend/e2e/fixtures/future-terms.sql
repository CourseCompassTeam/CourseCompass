-- E2E test data, applied after migrations and seeds/seed.py.
-- The seed's terms end in 2027 and the planner only uses terms that start after
-- today, so add two terms relative to the current date and offer every active
-- course in both. Never run this against a shared database.

INSERT INTO terms (term_name, start_date, end_date) VALUES
  ('E2E TERM 1', CURRENT_DATE + 30, CURRENT_DATE + 85),
  ('E2E TERM 2', CURRENT_DATE + 90, CURRENT_DATE + 145)
ON CONFLICT (term_name) DO NOTHING;

INSERT INTO course_offerings (course_id, term_id)
SELECT c.course_id, t.term_id
FROM courses c
CROSS JOIN terms t
WHERE c.is_active AND t.term_name IN ('E2E TERM 1', 'E2E TERM 2')
ON CONFLICT (course_id, term_id) DO NOTHING;
