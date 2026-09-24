# Migrations

Schema changes are managed with **node-pg-migrate**. Every change to the
database is a migration file checked in here, so the schema's full history
lives in git. Migrations run in CI before the test suite, and again as a deploy
step.

No migrations have been written yet. The documented schema is summarized below.
See `docs/OPEN_QUESTIONS.md` for the gaps and typos that need a team decision.

## Tables (from the Detailed Design)

| Table                | Columns |
|----------------------|---------|
| `programs`           | program_id (PK), name, total_credits_required, created_at |
| `students`           | student_id (PK), program_id (FK), email (unique), full_name, status (`active` / `leave` / `graduated`) |
| `courses`            | course_id (PK), code (unique), title, credits, is_active |
| `prerequisites`      | prerequisite_id (PK), course_id (FK), prerequisite_course_id (FK), requirement_type (`prereq` / `coreq`) |
| `requirements`       | requirement_id (PK), program_id (FK), course_id (FK, nullable), category (`core` / `elective`), credits_required |
| `transcript_entries` | entry_id (PK), student_id (FK), course_id (FK), term, status (`completed` / `in_progress` / `planned`) |
| `schedules`          | schedule_id (PK), student_id (FK), status (`draft` / `exported`) |
| `schedule_terms`     | schedule_term_id (PK), schedule_id (FK), term_name |
| `schedule_items`     | schedule_item_id (PK), schedule term (FK), course_id (FK) |
| `syllabus_chunks`    | chunk_id (PK), course_id (FK), chunk_index, chunk_text, embedding `VECTOR(1536)` (pgvector) |
| `advisor_contacts`   | advisor_id (PK), name, email (standalone, no FKs) |

## Indexes

- `idx_transcript_student_id` on `transcript_entries(student_id)`
- `idx_transcript_course_id` on `transcript_entries(course_id)`
- `idx_prerequisites_course_id` on `prerequisites(course_id)`
- `idx_requirements_program_id` on `requirements(program_id)`
