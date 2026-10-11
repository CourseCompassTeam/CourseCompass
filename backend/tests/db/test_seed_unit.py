"""Unit tests for seeds/seed.py. No database needed.

A fake cursor records every SQL statement the seed script sends and answers its
"does this row exist?" checks, so the script's logic can be tested in isolation:
which rows it inserts, that it skips rows that already exist, that it refuses to
run in production, and that the seed data itself is internally consistent.

Run with code coverage (coverage.py through pytest-cov):

    python -m pytest backend/tests/db/test_seed_unit.py --cov=seeds --cov-report=term-missing -v
"""

import importlib.util
import itertools
import re
import uuid
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("seed", ROOT / "seeds" / "seed.py")
seed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed)

GUARDED_TABLES = ["programs", "requirements", "prerequisites", "transcript_entries",
                  "advisor_contacts", "milestones", "course_offerings", "syllabus_chunks"]


class FakeCursor:
    """Stands in for a database cursor and records what the script does."""

    def __init__(self, rows_already_exist=False):
        self.rows_already_exist = rows_already_exist
        self.executed = []
        self._last_sql = ""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        self._last_sql = sql

    def fetchone(self):
        sql = self._last_sql
        if sql.startswith("SELECT 1 FROM"):
            return (1,) if self.rows_already_exist else None
        if sql.startswith("SELECT program_id FROM programs"):
            return (uuid.uuid4(),) if self.rows_already_exist else None
        if sql.startswith("SELECT COUNT"):
            return (7,)
        return (uuid.uuid4(),)  # RETURNING ... and SELECT student_id

    def inserts_into(self, table):
        pattern = re.compile(rf"^INSERT INTO {table}\b")
        return [sql for sql, _ in self.executed if pattern.match(sql)]


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return self._cursor


# ------------------------------------------------------- insert_if_missing --

class TestInsertIfMissing:
    def test_inserts_when_the_row_is_absent(self):
        cur = FakeCursor(rows_already_exist=False)
        seed.insert_if_missing(cur, "SELECT 1 FROM t WHERE x = %s", "INSERT INTO t VALUES (%s)", (1,))
        assert [sql for sql, _ in cur.executed] == ["SELECT 1 FROM t WHERE x = %s", "INSERT INTO t VALUES (%s)"]

    def test_skips_the_insert_when_the_row_exists(self):
        cur = FakeCursor(rows_already_exist=True)
        seed.insert_if_missing(cur, "SELECT 1 FROM t WHERE x = %s", "INSERT INTO t VALUES (%s)", (1,))
        assert [sql for sql, _ in cur.executed] == ["SELECT 1 FROM t WHERE x = %s"]


# ----------------------------------------------------------------- seed() --

class TestSeedOnEmptyDatabase:
    @pytest.fixture()
    def cur(self):
        c = FakeCursor(rows_already_exist=False)
        seed.seed(c)
        return c

    def test_inserts_one_program(self, cur):
        assert len(cur.inserts_into("programs")) == 1

    def test_one_requirement_per_course(self, cur):
        assert len(cur.inserts_into("requirements")) == len(seed.COURSES)

    def test_inserts_every_prerequisite(self, cur):
        assert len(cur.inserts_into("prerequisites")) == len(seed.PREREQUISITES)

    def test_inserts_every_transcript_entry(self, cur):
        expected = sum(len(entries) for entries in seed.TRANSCRIPTS.values())
        assert len(cur.inserts_into("transcript_entries")) == expected

    def test_inserts_contacts_and_milestones(self, cur):
        assert len(cur.inserts_into("advisor_contacts")) == len(seed.CONTACTS)
        assert len(cur.inserts_into("milestones")) == len(seed.MILESTONES)

    def test_inserts_every_course_offering(self, cur):
        expected = sum(len(terms) for terms in seed.COURSE_OFFERINGS.values())
        assert len(cur.inserts_into("course_offerings")) == expected

    def test_inserts_every_syllabus_chunk_with_a_null_embedding(self, cur):
        expected = sum(len(chunks) for chunks in seed.SYLLABUS_CHUNKS.values())
        inserts = cur.inserts_into("syllabus_chunks")
        assert len(inserts) == expected
        assert all(sql.rstrip().endswith("NULL)") for sql in inserts)

    def test_courses_and_terms_are_upserts(self, cur):
        for table, expected in (("courses", len(seed.COURSES)), ("terms", len(seed.TERMS))):
            inserts = cur.inserts_into(table)
            assert len(inserts) == expected
            assert all("ON CONFLICT" in sql for sql in inserts)

    def test_students_insert_never_overwrites(self, cur):
        inserts = cur.inserts_into("students")
        assert len(inserts) == len(seed.STUDENTS)
        assert all("ON CONFLICT DO NOTHING" in sql for sql in inserts)


class TestSeedIsSafeToRunTwice:
    @pytest.mark.parametrize("table", GUARDED_TABLES)
    def test_no_duplicate_rows_when_everything_already_exists(self, table):
        cur = FakeCursor(rows_already_exist=True)
        seed.seed(cur)
        assert cur.inserts_into(table) == []


# ------------------------------------------------------ print_counts / main --

class TestPrintCountsAndMain:
    def test_print_counts_reports_every_seeded_table(self, capsys):
        seed.print_counts(FakeCursor())
        lines = capsys.readouterr().out.strip().splitlines()
        tables = {line.split(":")[0].strip() for line in lines}
        assert {"programs", "courses", "prerequisites", "course_offerings", "syllabus_chunks", "terms"} <= tables
        assert all(line.endswith(": 7") for line in lines)

    @pytest.mark.parametrize("env", ["prod", "production", "PROD"])
    def test_refuses_to_run_in_production(self, monkeypatch, env):
        monkeypatch.setenv("APP_ENV", env)
        monkeypatch.setenv("DATABASE_URL", "postgresql://example")
        with pytest.raises(SystemExit):
            seed.main()

    def test_main_seeds_and_prints_counts_outside_production(self, monkeypatch, capsys):
        cur = FakeCursor()
        monkeypatch.setenv("APP_ENV", "local")
        monkeypatch.setenv("DATABASE_URL", "postgresql://example")
        monkeypatch.setattr(seed.psycopg, "connect", lambda url: FakeConnection(cur))
        seed.main()
        out = capsys.readouterr().out
        assert "Seed complete" in out
        assert cur.inserts_into("programs")


# ------------------------------------------------- seed data consistency --

CODES = [c[0] for c in seed.COURSES]
TERM_NAMES = [t[0] for t in seed.TERMS]


class TestSeedDataConsistency:
    def test_course_codes_are_unique_and_have_descriptions(self):
        assert len(CODES) == len(set(CODES))
        assert all(c[2].strip() for c in seed.COURSES)

    def test_prerequisites_reference_known_courses_without_duplicates_or_self_links(self):
        pairs = [(c, p) for c, p, _ in seed.PREREQUISITES]
        assert all(c in CODES and p in CODES for c, p in pairs)
        assert all(c != p for c, p in pairs)
        assert len(pairs) == len(set(pairs))

    def test_practicum_prerequisites_follow_the_syllabi(self):
        non_practicum = set(CODES) - {"MSSE 692", "MSSE 696"}
        prereqs = lambda code: {p for c, p, _ in seed.PREREQUISITES if c == code}
        assert prereqs("MSSE 692") == non_practicum
        assert prereqs("MSSE 696") == non_practicum | {"MSSE 692"}

    def test_transcripts_reference_known_students_courses_and_statuses(self):
        emails = {s[1] for s in seed.STUDENTS}
        for email, entries in seed.TRANSCRIPTS.items():
            assert email in emails
            for code, _term, status in entries:
                assert code in CODES
                assert status in {"completed", "in_progress", "planned"}

    def test_offerings_and_chunks_reference_known_courses_and_terms(self):
        assert set(seed.COURSE_OFFERINGS) <= set(CODES)
        assert all(t in TERM_NAMES for terms in seed.COURSE_OFFERINGS.values() for t in terms)
        assert set(seed.SYLLABUS_CHUNKS) <= set(CODES)

    def test_terms_are_valid_ordered_and_do_not_overlap(self):
        spans = [(date.fromisoformat(s), date.fromisoformat(e)) for _, s, e in seed.TERMS]
        assert all(start < end for start, end in spans)
        assert all(prev_end < next_start for (_, prev_end), (next_start, _) in itertools.pairwise(spans))

    def test_milestone_brackets_are_valid_and_do_not_overlap(self):
        brackets = [(lo, hi) for lo, hi, _, _ in seed.MILESTONES]
        assert all(hi is None or lo <= hi for lo, hi in brackets)
        assert all(prev_hi is not None and prev_hi < next_lo
                   for (_, prev_hi), (next_lo, _) in itertools.pairwise(brackets))

    def test_syllabus_chunks_are_non_empty_and_within_the_embedding_limit(self):
        # The embedding model accepts about 2,048 tokens (roughly 8,000 characters).
        chunks = [chunk for chunks in seed.SYLLABUS_CHUNKS.values() for chunk in chunks]
        assert all(chunk.strip() for chunk in chunks)
        assert max(len(chunk) for chunk in chunks) < 8000

    def test_two_test_students_with_distinct_ids(self):
        assert len(seed.STUDENTS) == 2
        assert len({s[0] for s in seed.STUDENTS}) == 2 and len({s[1] for s in seed.STUDENTS}) == 2
