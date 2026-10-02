# Seeds

Seed data is for **dev and test only**. Production data is loaded exclusively
through the admin ingestion API (`/api/v1/admin/ingest/...`), never through
seed scripts.

Run from the repo root with the venv active: `python seeds/seed.py`. It is safe
to re-run. It seeds the 12 MSSE courses (real titles, descriptions and
prerequisites from the Regis catalog), the core requirements, two test
students with transcripts, placeholder advisor/career contacts, and the
milestone brackets. 

syllabus_chunks: 11 of 12 courses have real syllabus content (description,
objectives, weekly topics), chunked into 3 rows each. MSSE 696 uses a
placeholder single-chunk entry from the catalog description, since a real
syllabus was not available. embedding is NULL on every row until the team
picks an embedding model.
