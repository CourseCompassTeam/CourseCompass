"""Database QA suite for CourseCompass.

Covers: schema validation, migration records, seed-data persistence, constraint
violations, delete behavior, edge-case queries, and documented schema gaps.

SAFE BY DESIGN: every test runs inside a transaction that is rolled back, so
nothing is ever written to the database. It still connects to the real database
in DATABASE_URL, so it only runs when you opt in:

    RUN_DB_TESTS=1 python -m pytest backend/tests/db/test_database_qa.py -v

Seed-count tests assume the current seed script. If you change the seed on
purpose, update EXPECTED_COUNTS below.
"""

import os
import uuid

import psycopg
import pytest
from dotenv import find_dotenv, load_dotenv
from psycopg import errors

load_dotenv(find_dotenv())

DATABASE_URL = os.getenv("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1" or not DATABASE_URL,
    reason="Set RUN_DB_TESTS=1 (and DATABASE_URL) to run database QA tests.",
)

EXPECTED_TABLES = {
    "programs", "students", "courses", "prerequisites", "requirements",
    "transcript_entries", "syllabus_chunks", "schedules", "schedule_terms",
    "schedule_items", "advisor_contacts", "data_ingestion_logs", "milestones",
    "terms", "course_offerings", "pgmigrations",
}

EXPECTED_COLUMNS = {
    "programs": {"program_id", "name", "total_credits_required", "created_at"},
    "students": {"student_id", "program_id", "clerk_user_id", "email", "full_name", "status", "created_at"},
    "courses": {"course_id", "code", "title", "description", "credits", "is_active"},
    "prerequisites": {"prerequisite_id", "course_id", "prerequisite_course_id", "requirement_type"},
    "requirements": {"requirement_id", "program_id", "course_id", "category", "credits_required"},
    "transcript_entries": {"entry_id", "student_id", "course_id", "term", "status"},
    "syllabus_chunks": {"chunk_id", "course_id", "chunk_index", "chunk_text", "embedding"},
    "schedules": {"schedule_id", "student_id", "status", "created_at"},
    "schedule_terms": {"schedule_term_id", "schedule_id", "term_name", "term_order"},
    "schedule_items": {"schedule_item_id", "schedule_term_id", "course_id"},
    "advisor_contacts": {"advisor_id", "name", "email", "contact_type", "booking_url"},
    "data_ingestion_logs": {"log_id", "source", "started_at", "completed_at", "status", "records_processed", "error_message"},
    "milestones": {"milestone_id", "credit_min", "credit_max", "label", "next_actions"},
    "terms": {"term_id", "term_name", "start_date", "end_date"},
    "course_offerings": {"offering_id", "course_id", "term_id"},
}

# (table, column, referenced table, delete rule). a=no action r=restrict c=cascade n=set null
EXPECTED_FOREIGN_KEYS = {
    ("students", "program_id", "programs", "r"),
    ("prerequisites", "course_id", "courses", "c"),
    ("prerequisites", "prerequisite_course_id", "courses", "c"),
    ("requirements", "program_id", "programs", "c"),
    ("requirements", "course_id", "courses", "n"),
    ("transcript_entries", "student_id", "students", "c"),
    ("transcript_entries", "course_id", "courses", "r"),
    ("syllabus_chunks", "course_id", "courses", "c"),
    ("schedules", "student_id", "students", "c"),
    ("schedule_terms", "schedule_id", "schedules", "c"),
    ("schedule_items", "schedule_term_id", "schedule_terms", "c"),
    ("schedule_items", "course_id", "courses", "r"),
    ("course_offerings", "course_id", "courses", "c"),
    ("course_offerings", "term_id", "terms", "c"),
}

EXPECTED_INDEXES = {
    "transcript_entries_student_id_index", "transcript_entries_course_id_index",
    "prerequisites_course_id_index", "requirements_program_id_index",
    "students_program_id_index", "schedules_student_id_index",
    "course_offerings_course_id_index", "idx_syllabus_chunks_embedding",
    "unique_course_term", "unique_term_course", "unique_schedule_term_order",
    "unique_course_chunk_index",
}

EXPECTED_COUNTS = {
    "programs": 1, "courses": 12, "requirements": 12, "prerequisites": 25,
    "students": 2, "transcript_entries": 12, "advisor_contacts": 2,
    "milestones": 3, "course_offerings": 15, "syllabus_chunks": 34, "terms": 4,
}

NON_PRACTICUM = {
    "MSSE 601", "MSSE 603", "MSSE 610", "MSSE 613", "MSSE 615",
    "MSSE 635", "MSSE 640", "MSSE 642", "MSES 602", "MSCC 697",
}

# A blocked DELETE on an ON DELETE RESTRICT key is reported differently by different
# PostgreSQL versions: ForeignKeyViolation (23503) on older ones, RestrictViolation (23001)
# on PostgreSQL 18. Either means the database correctly refused the delete.
DELETE_BLOCKED = (errors.ForeignKeyViolation, errors.RestrictViolation)

NEARLY_DONE = "nearly.done@example.edu"
JUST_STARTED = "just.started@example.edu"


# ---------------------------------------------------------------- fixtures --

@pytest.fixture(scope="module")
def conn():
    c = psycopg.connect(DATABASE_URL)
    yield c
    c.rollback()
    c.close()


@pytest.fixture(autouse=True)
def _always_rollback(conn):
    """Open a transaction before each test and roll it back after, no matter what."""
    conn.rollback()
    conn.execute("SELECT 1")  # guarantees conn.transaction() creates a savepoint, never a commit
    assert conn.info.transaction_status == psycopg.pq.TransactionStatus.INTRANS
    yield
    conn.rollback()


# ----------------------------------------------------------------- helpers --

def uid():
    return uuid.uuid4().hex[:10]


def scalar(conn, sql, params=None):
    return conn.execute(sql, params).fetchone()[0]


def column(conn, sql, params=None):
    return [r[0] for r in conn.execute(sql, params).fetchall()]


def new_program(conn, credits=36):
    return scalar(conn, "INSERT INTO programs (name, total_credits_required) VALUES (%s, %s) RETURNING program_id",
                  (f"QA program {uid()}", credits))


def new_course(conn, code=None, credits=3):
    return scalar(conn, "INSERT INTO courses (code, title, credits) VALUES (%s, %s, %s) RETURNING course_id",
                  (code or f"QA{uid()}", "QA course", credits))


def new_student(conn, program_id, email=None, clerk=None, status="active"):
    return scalar(conn, "INSERT INTO students (program_id, clerk_user_id, email, full_name, status) "
                        "VALUES (%s, %s, %s, 'QA Student', %s) RETURNING student_id",
                  (program_id, clerk or f"qa_{uid()}", email or f"qa_{uid()}@example.com", status))


def new_term(conn, name=None, start="2030-01-01", end="2030-02-01"):
    return scalar(conn, "INSERT INTO terms (term_name, start_date, end_date) VALUES (%s, %s, %s) RETURNING term_id",
                  (name or f"QA{uid()}", start, end))


def missing_prereqs(conn, email, course_code):
    return set(column(conn, """
        SELECT pc.code FROM prerequisites p
        JOIN courses c  ON c.course_id  = p.course_id
        JOIN courses pc ON pc.course_id = p.prerequisite_course_id
        WHERE c.code = %s AND NOT EXISTS (
            SELECT 1 FROM transcript_entries t JOIN students s ON s.student_id = t.student_id
            WHERE s.email = %s AND t.course_id = p.prerequisite_course_id AND t.status = 'completed')
    """, (course_code, email)))


# ======================================================= 1. SCHEMA VALIDATION

class TestSchemaValidation:
    def test_expected_tables_exist(self, conn):
        actual = set(column(conn, "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        assert actual == EXPECTED_TABLES, f"missing: {EXPECTED_TABLES - actual}, unexpected: {actual - EXPECTED_TABLES}"

    @pytest.mark.parametrize("table", sorted(EXPECTED_COLUMNS))
    def test_columns_match_design(self, conn, table):
        actual = set(column(conn, "SELECT column_name FROM information_schema.columns "
                                  "WHERE table_schema = 'public' AND table_name = %s", (table,)))
        assert actual == EXPECTED_COLUMNS[table], (
            f"{table}: missing {EXPECTED_COLUMNS[table] - actual}, unexpected {actual - EXPECTED_COLUMNS[table]}")

    def test_foreign_keys_and_delete_rules(self, conn):
        rows = conn.execute("""
            SELECT c.conrelid::regclass::text, a.attname, c.confrelid::regclass::text, c.confdeltype::text
            FROM pg_constraint c
            JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
            WHERE c.contype = 'f' AND c.connamespace = 'public'::regnamespace
        """).fetchall()
        actual = {tuple(r) for r in rows}
        assert actual == EXPECTED_FOREIGN_KEYS, f"missing {EXPECTED_FOREIGN_KEYS - actual}, unexpected {actual - EXPECTED_FOREIGN_KEYS}"

    def test_expected_indexes_exist(self, conn):
        actual = set(column(conn, "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"))
        assert EXPECTED_INDEXES <= actual, f"missing indexes: {EXPECTED_INDEXES - actual}"

    def test_pgvector_extension_installed(self, conn):
        assert "vector" in column(conn, "SELECT extname FROM pg_extension")

    def test_embedding_column_is_vector_768_and_nullable(self, conn):
        row = conn.execute("""
            SELECT format_type(atttypid, atttypmod), attnotnull FROM pg_attribute
            WHERE attrelid = 'syllabus_chunks'::regclass AND attname = 'embedding'
        """).fetchone()
        assert row == ("vector(768)", False)


class TestMigrationRecords:
    def test_migrations_recorded_once_and_in_order(self, conn):
        names = column(conn, "SELECT name FROM pgmigrations ORDER BY id")
        assert len(names) >= 16, f"expected at least 16 applied migrations, found {len(names)}"
        assert len(names) == len(set(names)), "a migration is recorded twice"
        assert names == sorted(names), "migrations were applied out of timestamp order"

    def test_key_migrations_present(self, conn):
        names = " ".join(column(conn, "SELECT name FROM pgmigrations"))
        for fragment in ("create-programs-table", "create-terms-table", "make-syllabus-embedding-nullable"):
            assert fragment in names


# ============================================= 1b. SEED DATA / PERSISTENCE

class TestSeedPersistence:
    @pytest.mark.parametrize("table", sorted(EXPECTED_COUNTS))
    def test_seed_row_counts(self, conn, table):
        assert scalar(conn, f"SELECT count(*) FROM {table}") == EXPECTED_COUNTS[table], (
            "row count changed; update EXPECTED_COUNTS if the seed was changed on purpose")

    def test_no_duplicate_prerequisites_or_transcripts_in_seed(self, conn):
        dup_pre = conn.execute("SELECT course_id, prerequisite_course_id FROM prerequisites "
                               "GROUP BY 1, 2 HAVING count(*) > 1").fetchall()
        dup_tx = conn.execute("SELECT student_id, course_id, term FROM transcript_entries "
                              "GROUP BY 1, 2, 3 HAVING count(*) > 1").fetchall()
        assert dup_pre == [] and dup_tx == []

    def test_every_course_has_a_description(self, conn):
        assert scalar(conn, "SELECT count(*) FROM courses WHERE description IS NULL OR description = ''") == 0

    def test_syllabus_chunk_counts_per_course(self, conn):
        rows = dict(conn.execute("SELECT c.code, count(s.chunk_id) FROM courses c "
                                 "LEFT JOIN syllabus_chunks s ON s.course_id = c.course_id GROUP BY c.code").fetchall())
        expected = {code: (1 if code == "MSSE 696" else 3) for code in rows}
        assert rows == expected

    def test_practicum_prerequisites_match_syllabi(self, conn):
        def prereqs(code):
            return set(column(conn, "SELECT pc.code FROM prerequisites p JOIN courses c ON c.course_id = p.course_id "
                                    "JOIN courses pc ON pc.course_id = p.prerequisite_course_id WHERE c.code = %s", (code,)))
        assert prereqs("MSSE 692") == NON_PRACTICUM
        assert prereqs("MSSE 696") == NON_PRACTICUM | {"MSSE 692"}

    @pytest.mark.parametrize("name,start,end", [
        ("2026 FALL 8W1", "2026-08-24", "2026-10-18"),
        ("2026 FALL 8W2", "2026-10-19", "2026-12-13"),
        ("2027 SPR 8W1", "2027-01-11", "2027-03-07"),
        ("2027 SPR 8W2", "2027-03-08", "2027-05-02"),
    ])
    def test_term_dates(self, conn, name, start, end):
        row = conn.execute("SELECT start_date::text, end_date::text FROM terms WHERE term_name = %s", (name,)).fetchone()
        assert row == (start, end)

    def test_course_offerings_spot_checks(self, conn):
        def terms(code):
            return set(column(conn, "SELECT t.term_name FROM course_offerings o JOIN courses c ON c.course_id = o.course_id "
                                    "JOIN terms t ON t.term_id = o.term_id WHERE c.code = %s", (code,)))
        assert terms("MSSE 603") == {"2027 SPR 8W1"}
        assert terms("MSES 602") == set() and terms("MSCC 697") == set()


class TestAuditQueries:
    """The core business questions, answered directly from the seeded data."""

    def test_nearly_done_student_has_30_completed_credits(self, conn):
        credits = scalar(conn, "SELECT COALESCE(SUM(c.credits), 0) FROM transcript_entries t "
                               "JOIN courses c ON c.course_id = t.course_id JOIN students s ON s.student_id = t.student_id "
                               "WHERE s.email = %s AND t.status = 'completed'", (NEARLY_DONE,))
        assert credits == 30

    def test_nearly_done_student_only_needs_the_two_practicums(self, conn):
        remaining = set(column(conn, """
            SELECT c.code FROM requirements r JOIN courses c ON c.course_id = r.course_id
            JOIN students s ON s.program_id = r.program_id
            WHERE s.email = %s AND NOT EXISTS (SELECT 1 FROM transcript_entries t WHERE t.student_id = s.student_id
                AND t.course_id = r.course_id AND t.status = 'completed')""", (NEARLY_DONE,)))
        assert remaining == {"MSSE 692", "MSSE 696"}

    @pytest.mark.parametrize("email,course,expected_missing", [
        (JUST_STARTED, "MSSE 610", set()),
        (JUST_STARTED, "MSSE 635", {"MSSE 610"}),
        (NEARLY_DONE, "MSSE 692", set()),
        (NEARLY_DONE, "MSSE 696", {"MSSE 692"}),
    ])
    def test_prerequisite_eligibility(self, conn, email, course, expected_missing):
        assert missing_prereqs(conn, email, course) == expected_missing


# ============================================== 2. CONSTRAINT VIOLATIONS

def _dup_course_code(c):
    code = f"QA{uid()}"
    new_course(c, code); new_course(c, code)

def _dup_email(c):
    p = new_program(c); email = f"qa_{uid()}@example.com"
    new_student(c, p, email=email); new_student(c, p, email=email)

def _dup_clerk(c):
    p = new_program(c); clerk = f"qa_{uid()}"
    new_student(c, p, clerk=clerk); new_student(c, p, clerk=clerk)

def _null_email(c):
    c.execute("INSERT INTO students (program_id, clerk_user_id, email, full_name, status) "
              "VALUES (%s, %s, NULL, 'x', 'active')", (new_program(c), f"qa_{uid()}"))

def _unknown_program(c):
    new_student(c, uuid.uuid4())

def _self_prereq(c):
    cid = new_course(c)
    c.execute("INSERT INTO prerequisites (course_id, prerequisite_course_id, requirement_type) VALUES (%s, %s, 'prereq')", (cid, cid))

def _bad_prereq_type(c):
    a, b = new_course(c), new_course(c)
    c.execute("INSERT INTO prerequisites (course_id, prerequisite_course_id, requirement_type) VALUES (%s, %s, 'maybe')", (a, b))

def _bad_requirement_category(c):
    c.execute("INSERT INTO requirements (program_id, category, credits_required) VALUES (%s, 'optional', 3)", (new_program(c),))

def _zero_requirement_credits(c):
    c.execute("INSERT INTO requirements (program_id, category, credits_required) VALUES (%s, 'core', 0)", (new_program(c),))

def _bad_transcript_status(c):
    s = new_student(c, new_program(c))
    c.execute("INSERT INTO transcript_entries (student_id, course_id, term, status) VALUES (%s, %s, 'Fall 2026', 'dropped')", (s, new_course(c)))

def _transcript_unknown_student(c):
    c.execute("INSERT INTO transcript_entries (student_id, course_id, term, status) VALUES (%s, %s, 'Fall 2026', 'completed')", (uuid.uuid4(), new_course(c)))

def _dup_chunk_index(c):
    cid = new_course(c)
    for _ in range(2):
        c.execute("INSERT INTO syllabus_chunks (course_id, chunk_index, chunk_text) VALUES (%s, 0, 'x')", (cid,))

def _wrong_vector_dims(c):
    c.execute("INSERT INTO syllabus_chunks (course_id, chunk_index, chunk_text, embedding) VALUES (%s, 0, 'x', '[1,2,3]')", (new_course(c),))

def _bad_schedule_status(c):
    c.execute("INSERT INTO schedules (student_id, status) VALUES (%s, 'archived')", (new_student(c, new_program(c)),))

def _dup_schedule_term_order(c):
    s = c.execute("INSERT INTO schedules (student_id) VALUES (%s) RETURNING schedule_id", (new_student(c, new_program(c)),)).fetchone()[0]
    for _ in range(2):
        c.execute("INSERT INTO schedule_terms (schedule_id, term_name, term_order) VALUES (%s, 'T', 1)", (s,))

def _dup_offering(c):
    cid, tid = new_course(c), new_term(c)
    for _ in range(2):
        c.execute("INSERT INTO course_offerings (course_id, term_id) VALUES (%s, %s)", (cid, tid))

def _bad_contact_type(c):
    c.execute("INSERT INTO advisor_contacts (name, email, contact_type) VALUES ('x', 'x@example.com', 'tutor')")

def _bad_ingestion_status(c):
    c.execute("INSERT INTO data_ingestion_logs (source, status) VALUES ('course_catalog', 'paused')")

def _dup_term_name(c):
    name = f"QA{uid()}"
    new_term(c, name); new_term(c, name)

CONSTRAINT_CASES = [
    ("program_zero_credits", errors.CheckViolation, lambda c: new_program(c, credits=0)),
    ("course_zero_credits", errors.CheckViolation, lambda c: new_course(c, credits=0)),
    ("course_duplicate_code", errors.UniqueViolation, _dup_course_code),
    ("student_invalid_status", errors.CheckViolation, lambda c: new_student(c, new_program(c), status="expelled")),
    ("student_duplicate_email", errors.UniqueViolation, _dup_email),
    ("student_duplicate_clerk_id", errors.UniqueViolation, _dup_clerk),
    ("student_null_email", errors.NotNullViolation, _null_email),
    ("student_unknown_program", errors.ForeignKeyViolation, _unknown_program),
    ("prerequisite_self_reference", errors.CheckViolation, _self_prereq),
    ("prerequisite_invalid_type", errors.CheckViolation, _bad_prereq_type),
    ("requirement_invalid_category", errors.CheckViolation, _bad_requirement_category),
    ("requirement_zero_credits", errors.CheckViolation, _zero_requirement_credits),
    ("transcript_invalid_status", errors.CheckViolation, _bad_transcript_status),
    ("transcript_unknown_student", errors.ForeignKeyViolation, _transcript_unknown_student),
    ("chunk_duplicate_index", errors.UniqueViolation, _dup_chunk_index),
    ("chunk_wrong_vector_dimension", errors.DataException, _wrong_vector_dims),
    ("schedule_invalid_status", errors.CheckViolation, _bad_schedule_status),
    ("schedule_term_duplicate_order", errors.UniqueViolation, _dup_schedule_term_order),
    ("offering_duplicate_course_term", errors.UniqueViolation, _dup_offering),
    ("contact_invalid_type", errors.CheckViolation, _bad_contact_type),
    ("ingestion_invalid_status", errors.CheckViolation, _bad_ingestion_status),
    ("term_duplicate_name", errors.UniqueViolation, _dup_term_name),
]


class TestConstraintViolations:
    """Each case must be REJECTED by the database with the right kind of error."""

    @pytest.mark.parametrize("name,error,action", CONSTRAINT_CASES, ids=[c[0] for c in CONSTRAINT_CASES])
    def test_database_rejects_bad_data(self, conn, name, error, action):
        with pytest.raises(error), conn.transaction():
            action(conn)


class TestDeleteBehavior:
    def test_cannot_delete_program_that_has_students(self, conn):
        p = new_program(conn); new_student(conn, p)
        with pytest.raises(DELETE_BLOCKED), conn.transaction():
            conn.execute("DELETE FROM programs WHERE program_id = %s", (p,))

    def test_cannot_delete_course_on_a_transcript(self, conn):
        s, c = new_student(conn, new_program(conn)), new_course(conn)
        conn.execute("INSERT INTO transcript_entries (student_id, course_id, term, status) VALUES (%s, %s, 'Fall 2026', 'completed')", (s, c))
        with pytest.raises(DELETE_BLOCKED), conn.transaction():
            conn.execute("DELETE FROM courses WHERE course_id = %s", (c,))

    def test_deleting_a_course_cascades_to_its_dependents(self, conn):
        c, t = new_course(conn), new_term(conn)
        conn.execute("INSERT INTO syllabus_chunks (course_id, chunk_index, chunk_text) VALUES (%s, 0, 'x')", (c,))
        conn.execute("INSERT INTO course_offerings (course_id, term_id) VALUES (%s, %s)", (c, t))
        conn.execute("INSERT INTO prerequisites (course_id, prerequisite_course_id, requirement_type) VALUES (%s, %s, 'prereq')", (c, new_course(conn)))
        conn.execute("DELETE FROM courses WHERE course_id = %s", (c,))
        for table in ("syllabus_chunks", "course_offerings", "prerequisites"):
            assert scalar(conn, f"SELECT count(*) FROM {table} WHERE course_id = %s", (c,)) == 0

    def test_deleting_a_course_keeps_its_requirement_row_with_null_course(self, conn):
        p, c = new_program(conn), new_course(conn)
        r = scalar(conn, "INSERT INTO requirements (program_id, course_id, category, credits_required) "
                         "VALUES (%s, %s, 'core', 3) RETURNING requirement_id", (p, c))
        conn.execute("DELETE FROM courses WHERE course_id = %s", (c,))
        assert scalar(conn, "SELECT course_id FROM requirements WHERE requirement_id = %s", (r,)) is None

    def test_deleting_a_student_removes_their_transcript_and_schedules(self, conn):
        s, c = new_student(conn, new_program(conn)), new_course(conn)
        conn.execute("INSERT INTO transcript_entries (student_id, course_id, term, status) VALUES (%s, %s, 'Fall 2026', 'completed')", (s, c))
        conn.execute("INSERT INTO schedules (student_id) VALUES (%s)", (s,))
        conn.execute("DELETE FROM students WHERE student_id = %s", (s,))
        assert scalar(conn, "SELECT count(*) FROM transcript_entries WHERE student_id = %s", (s,)) == 0
        assert scalar(conn, "SELECT count(*) FROM schedules WHERE student_id = %s", (s,)) == 0


# ============================================ 2b. EDGE-CASE QUERY BEHAVIOR

class TestEdgeCaseQueries:
    def test_unknown_course_code_returns_no_rows(self, conn):
        assert conn.execute("SELECT * FROM courses WHERE code = 'NOPE 999'").fetchall() == []

    def test_student_with_no_transcript_has_zero_credits_not_null(self, conn):
        s = new_student(conn, new_program(conn))
        credits = scalar(conn, "SELECT COALESCE(SUM(c.credits), 0) FROM transcript_entries t "
                               "JOIN courses c ON c.course_id = t.course_id WHERE t.student_id = %s AND t.status = 'completed'", (s,))
        assert credits == 0

    def test_malformed_uuid_is_rejected_so_the_api_must_validate_ids(self, conn):
        with pytest.raises(errors.InvalidTextRepresentation), conn.transaction():
            conn.execute("SELECT * FROM courses WHERE course_id = 'not-a-uuid'")

    def test_parameterized_queries_are_injection_safe(self, conn):
        before = scalar(conn, "SELECT count(*) FROM courses")
        rows = conn.execute("SELECT * FROM courses WHERE code = %s", ("x'; DROP TABLE courses; --",)).fetchall()
        assert rows == [] and scalar(conn, "SELECT count(*) FROM courses") == before

    def test_similarity_query_runs_even_though_embeddings_are_null(self, conn):
        vec = "[" + ",".join(["1"] * 768) + "]"
        rows = conn.execute("SELECT chunk_id FROM syllabus_chunks ORDER BY embedding <=> %s::vector LIMIT 5", (vec,)).fetchall()
        assert len(rows) <= 5  # no error; results are meaningless until embeddings are populated

    def test_similarity_query_rejects_wrong_dimension(self, conn):
        with pytest.raises(errors.DataException), conn.transaction():
            conn.execute("SELECT chunk_id FROM syllabus_chunks ORDER BY embedding <=> '[1,2,3]'::vector LIMIT 5")


# ===================================================== 3. DOCUMENTED GAPS
# These tests PASS today by asserting the database currently ALLOWS the bad
# data. They exist to document known weaknesses. If one starts failing, a
# constraint was added: update Known Issues and the QA report.

class TestKnownSchemaGaps:
    def test_gap_duplicate_prerequisite_rows_are_allowed(self, conn):
        a, b = new_course(conn), new_course(conn)
        for _ in range(2):
            conn.execute("INSERT INTO prerequisites (course_id, prerequisite_course_id, requirement_type) VALUES (%s, %s, 'prereq')", (a, b))

    def test_gap_prerequisite_cycles_are_allowed(self, conn):
        a, b = new_course(conn), new_course(conn)
        conn.execute("INSERT INTO prerequisites (course_id, prerequisite_course_id, requirement_type) VALUES (%s, %s, 'prereq')", (a, b))
        conn.execute("INSERT INTO prerequisites (course_id, prerequisite_course_id, requirement_type) VALUES (%s, %s, 'prereq')", (b, a))

    def test_gap_duplicate_transcript_entries_are_allowed(self, conn):
        s, c = new_student(conn, new_program(conn)), new_course(conn)
        for _ in range(2):
            conn.execute("INSERT INTO transcript_entries (student_id, course_id, term, status) VALUES (%s, %s, 'Fall 2026', 'completed')", (s, c))

    def test_gap_term_end_date_before_start_date_is_allowed(self, conn):
        new_term(conn, start="2030-05-01", end="2030-01-01")

    def test_gap_milestone_max_below_min_is_allowed(self, conn):
        conn.execute("INSERT INTO milestones (credit_min, credit_max, label) VALUES (20, 5, 'QA backwards bracket')")

    def test_gap_email_format_is_not_validated(self, conn):
        new_student(conn, new_program(conn), email="not-an-email")
