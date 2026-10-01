# Migrations

Schema changes are managed with **node-pg-migrate**. Every change to the
database is a migration file checked in here, so the schema's full history
lives in git. Migrations run manually for now.

The tables below reflect the schema as actually implemented, not the
original design. See `docs/OPEN_QUESTIONS.md` for known gaps.

## Tables (as implemented)

| Table | Columns |
|---|---|
| `programs` | program_id (PK), name, total_credits_required, created_at |
| `students` | student_id (PK), program_id (FK), clerk_user_id (unique), email (unique), full_name, status (`active`/`leave`/`graduated`), created_at |
| `courses` | course_id (PK), code (unique), title, description, credits, is_active |
| `prerequisites` | prerequisite_id (PK), course_id (FK), prerequisite_course_id (FK), requirement_type (`prereq`/`coreq`) |
| `requirements` | requirement_id (PK), program_id (FK), course_id (FK, nullable), category (`core`/`elective`), credits_required |
| `transcript_entries` | entry_id (PK), student_id (FK), course_id (FK), term, status (`completed`/`in_progress`/`planned`) |
| `schedules` | schedule_id (PK), student_id (FK), status (`draft`/`exported`), created_at |
| `schedule_terms` | schedule_term_id (PK), schedule_id (FK), term_name, term_order |
| `schedule_items` | schedule_item_id (PK), schedule_term_id (FK), course_id (FK) |
| `syllabus_chunks` | chunk_id (PK), course_id (FK), chunk_index, chunk_text, embedding `VECTOR(768)` nullable (pgvector) |
| `advisor_contacts` | advisor_id (PK), name, email, contact_type (`advisor`/`career_services`), booking_url |
| `data_ingestion_logs` | log_id (PK), source (`course_catalog`/`transcript`), started_at, completed_at, status (`running`/`succeeded`/`failed`), records_processed, error_message |
| `milestones` | milestone_id (PK), credit_min, credit_max, label, next_actions (text array) |
| `terms` | term_id (PK), term_name (unique), start_date, end_date |
| `course_offerings` | offering_id (PK), course_id (FK), term_id (FK) |

## Indexes

* `idx_transcript_student_id` on `transcript_entries(student_id)`
* `idx_transcript_course_id` on `transcript_entries(course_id)`
* `idx_prerequisites_course_id` on `prerequisites(course_id)`
* `idx_requirements_program_id` on `requirements(program_id)`
* `students_program_id_index` on `students(program_id)`
* `schedules_student_id_index` on `schedules(student_id)`
* `course_offerings_course_id_index` on `course_offerings(course_id)`
* `idx_syllabus_chunks_embedding` on `syllabus_chunks(embedding)` — ivfflat, pgvector similarity search
