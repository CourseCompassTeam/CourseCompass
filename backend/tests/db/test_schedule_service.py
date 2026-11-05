"""Database tests for ScheduleBuilderService (load inputs, plan, save the draft).

Needs a database with the migrations applied. Skipped unless RUN_DB_TESTS=1.
Every test works inside one transaction that is rolled back, so nothing is left
behind. Run:  RUN_DB_TESTS=1 python -m pytest backend/tests/db/test_schedule_service.py -v
"""

import os
import uuid
from contextlib import contextmanager
from datetime import date

import psycopg
import pytest
from psycopg.rows import dict_row, tuple_row

from app.repositories.postgres_schedule import PostgresScheduleRepository
from app.scheduling.service import ScheduleBuilderService

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1", reason="set RUN_DB_TESTS=1 to run database tests"
)


class SameConnection:
    """Database stand-in that hands out the test's own connection and never closes it."""

    def __init__(self, connection):
        self._connection = connection

    @contextmanager
    def connect(self):
        yield self._connection


@pytest.fixture()
def conn():
    connection = psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)
    yield connection
    connection.rollback()
    connection.close()


@pytest.fixture()
def service(conn):
    database = SameConnection(conn)
    return ScheduleBuilderService(database, PostgresScheduleRepository(database))


def uid():
    return uuid.uuid4().hex[:10]


def one(conn, sql, params=()):
    with conn.cursor(row_factory=tuple_row) as cur:
        cur.execute(sql, params)
        return cur.fetchone()[0]


def run(conn, sql, params=()):
    with conn.cursor(row_factory=tuple_row) as cur:
        cur.execute(sql, params)


def make_world(conn, courses=3):
    """A program, `courses` required courses, a student and two future terms (2099)."""
    program = one(conn, "INSERT INTO programs (name, total_credits_required) VALUES (%s, 12) RETURNING program_id", (f"Test program {uid()}",))
    ids = []
    for i in range(courses):
        course = one(
            conn,
            "INSERT INTO courses (code, title, description, credits, is_active) "
            "VALUES (%s, %s, 'test', 3, true) RETURNING course_id",
            (f"TST {i}-{uid()}", f"Course {i}"),
        )
        run(conn, "INSERT INTO requirements (program_id, course_id, category, credits_required) VALUES (%s, %s, 'core', 3)", (program, course))
        ids.append(course)
    student = one(
        conn,
        "INSERT INTO students (program_id, clerk_user_id, email, full_name, status) "
        "VALUES (%s, %s, %s, 'Test Student', 'active') RETURNING student_id",
        (program, f"clerk_{uid()}", f"{uid()}@example.edu"),
    )
    terms = [
        one(conn, "INSERT INTO terms (term_name, start_date, end_date) VALUES (%s, %s, %s) RETURNING term_id",
            (f"T{i} {uid()}", date(2099, i, 1), date(2099, i, 28)))
        for i in (1, 2)
    ]
    return {"program": program, "courses": ids, "student": student, "terms": terms}


def offer(conn, course, term):
    run(conn, "INSERT INTO course_offerings (course_id, term_id) VALUES (%s, %s)", (course, term))


def draft_count(conn, student):
    return one(conn, "SELECT COUNT(*) FROM schedules WHERE student_id = %s AND status = 'draft'", (student,))


def test_unknown_student_returns_none(service):
    assert service.build_draft("no-such-student") is None


def test_builds_and_saves_a_draft_found_by_clerk_id(conn, service):
    w = make_world(conn, courses=2)
    for course in w["courses"]:
        offer(conn, course, w["terms"][0])
    clerk_id = one(conn, "SELECT clerk_user_id FROM students WHERE student_id = %s", (w["student"],))
    result = service.build_draft(clerk_id)
    assert result["unplaced"] == []
    schedule = result["schedule"]
    assert schedule["status"] == "draft" and schedule["student_id"] == str(w["student"])
    placed = {item["course_id"] for term in schedule["terms"] for item in term["items"]}
    assert placed == {str(c) for c in w["courses"]}
    assert draft_count(conn, w["student"]) == 1


def test_a_second_build_replaces_the_first_draft(conn, service):
    w = make_world(conn, courses=1)
    offer(conn, w["courses"][0], w["terms"][0])
    first = service.build_draft(str(w["student"]))["schedule"]["schedule_id"]
    second = service.build_draft(str(w["student"]))["schedule"]["schedule_id"]
    assert first != second
    assert draft_count(conn, w["student"]) == 1


def test_max_per_term_spreads_courses_over_terms(conn, service):
    w = make_world(conn, courses=2)
    for course in w["courses"]:
        offer(conn, course, w["terms"][0])
        offer(conn, course, w["terms"][1])
    result = service.build_draft(str(w["student"]), max_per_term=1)
    assert [len(t["items"]) for t in result["schedule"]["terms"]] == [1, 1]


def test_unplaced_courses_are_described_with_code_and_reason(conn, service):
    w = make_world(conn, courses=2)
    offer(conn, w["courses"][0], w["terms"][0])  # the second course is offered nowhere
    result = service.build_draft(str(w["student"]))
    assert len(result["unplaced"]) == 1
    missing = result["unplaced"][0]
    assert missing["course_id"] == str(w["courses"][1])
    assert missing["code"].startswith("TST 1-")
    assert missing["reason"] == "not offered in any available term"


def test_when_nothing_can_be_placed_the_old_draft_is_kept(conn, service):
    w = make_world(conn, courses=1)
    offer(conn, w["courses"][0], w["terms"][0])
    kept = service.build_draft(str(w["student"]))["schedule"]["schedule_id"]
    run(conn, "DELETE FROM course_offerings WHERE course_id = %s", (w["courses"][0],))
    result = service.build_draft(str(w["student"]))
    assert result["schedule"] is None and len(result["unplaced"]) == 1
    assert one(conn, "SELECT schedule_id::text FROM schedules WHERE student_id = %s AND status = 'draft'", (w["student"],)) == kept


def test_completed_courses_are_not_planned_again(conn, service):
    w = make_world(conn, courses=2)
    for course in w["courses"]:
        offer(conn, course, w["terms"][0])
    run(conn, "INSERT INTO transcript_entries (student_id, course_id, term, status) VALUES (%s, %s, 'Fall 2025', 'completed')", (w["student"], w["courses"][0]))
    schedule = service.build_draft(str(w["student"]))["schedule"]
    placed = [item["course_id"] for term in schedule["terms"] for item in term["items"]]
    assert placed == [str(w["courses"][1])]
