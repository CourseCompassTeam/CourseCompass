"""Database tests for the schedule repository and the planner inputs.

Needs a database with the migrations applied. Skipped unless RUN_DB_TESTS=1.
Every test builds its own rows inside a transaction that is rolled back at the
end, so nothing is left behind and the seeded data is never touched.

Run:  RUN_DB_TESTS=1 python -m pytest backend/tests/db/test_schedule_repository.py -v
"""

import os
import uuid
from datetime import date

import psycopg
import pytest
from psycopg import errors
from psycopg.rows import dict_row, tuple_row

from app.repositories.connection import Database
from app.repositories.postgres_schedule import PostgresScheduleRepository
from app.scheduling import schedule_repository as repo
from app.scheduling.planner import build_plan

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1", reason="set RUN_DB_TESTS=1 to run database tests"
)

FAR_FUTURE = date(2098, 1, 1)  # "today" for planner inputs, so seeded 2027 terms are ignored


@pytest.fixture(params=[tuple_row, dict_row], ids=["tuple_rows", "dict_rows"])
def conn(request):
    """Runs every repository test with plain rows and with Database.connect's dict rows."""
    connection = psycopg.connect(os.environ["DATABASE_URL"], row_factory=request.param)
    yield connection
    connection.rollback()
    connection.close()


@pytest.fixture()
def dict_conn():
    connection = psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)
    yield connection
    connection.rollback()
    connection.close()


def uid():
    return uuid.uuid4().hex[:10]


def make_program(conn):
    with conn.cursor(row_factory=tuple_row) as cur:
        cur.execute(
            "INSERT INTO programs (name, total_credits_required) VALUES (%s, 12) "
            "RETURNING program_id",
            (f"Test program {uid()}",),
        )
        return cur.fetchone()[0]


def make_course(conn, label, is_active=True):
    with conn.cursor(row_factory=tuple_row) as cur:
        cur.execute(
            "INSERT INTO courses (code, title, description, credits, is_active) "
            "VALUES (%s, %s, 'test course', 3, %s) RETURNING course_id",
            (f"TST {label}-{uid()}", f"Course {label}", is_active),
        )
        return cur.fetchone()[0]


def make_student(conn, program_id):
    with conn.cursor(row_factory=tuple_row) as cur:
        cur.execute(
            "INSERT INTO students (program_id, clerk_user_id, email, full_name, status) "
            "VALUES (%s, %s, %s, 'Test Student', 'active') RETURNING student_id",
            (program_id, f"clerk_{uid()}", f"{uid()}@example.edu"),
        )
        return cur.fetchone()[0]


def make_term(conn, name, start):
    with conn.cursor(row_factory=tuple_row) as cur:
        cur.execute(
            "INSERT INTO terms (term_name, start_date, end_date) VALUES (%s, %s, %s) "
            "RETURNING term_id",
            (f"{name} {uid()}", start, start.replace(day=28)),
        )
        return cur.fetchone()[0]


def make_world(conn):
    """A program with courses A, B, C (B needs A, C needs B), a student and 3 terms."""
    program_id = make_program(conn)
    a, b, c = (make_course(conn, x) for x in "ABC")
    student_id = make_student(conn, program_id)
    terms = [make_term(conn, f"T{i}", date(2099, i, 1)) for i in (1, 2, 3)]
    return {"program": program_id, "courses": (a, b, c), "student": student_id, "terms": terms}


def read_schedule(conn, schedule_id):
    """Reads a schedule back with plain SQL: (status, [[course_id, ...] per term])."""
    with conn.cursor(row_factory=tuple_row) as cur:
        cur.execute("SELECT status FROM schedules WHERE schedule_id = %s", (schedule_id,))
        head = cur.fetchone()
        if head is None:
            return None
        cur.execute(
            "SELECT st.term_name, st.term_order, si.course_id FROM schedule_terms st "
            "LEFT JOIN schedule_items si ON si.schedule_term_id = st.schedule_term_id "
            "WHERE st.schedule_id = %s ORDER BY st.term_order",
            (schedule_id,),
        )
        terms = {}
        for name, order, course_id in cur.fetchall():
            terms.setdefault(order, (name, []))
            if course_id is not None:
                terms[order][1].append(course_id)
    return head[0], [terms[k] for k in sorted(terms)]


def latest_draft_id(conn, student_id):
    with conn.cursor(row_factory=tuple_row) as cur:
        cur.execute(
            "SELECT schedule_id FROM schedules WHERE student_id = %s AND status = 'draft' "
            "ORDER BY created_at DESC LIMIT 1",
            (student_id,),
        )
        row = cur.fetchone()
    return row[0] if row else None


def count(conn, table, where="true", params=()):
    with conn.cursor(row_factory=tuple_row) as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", params)
        return cur.fetchone()[0]


# ------------------------------------------------------------- saving --

class TestCreateAndGet:
    def test_round_trip_keeps_term_order_and_courses(self, conn):
        w = make_world(conn)
        a, b, c = w["courses"]
        schedule_id = repo.create_schedule(
            conn, w["student"], [("Fall", [a]), ("Spring", [b, c])]
        )
        status, terms = read_schedule(conn, schedule_id)
        assert status == "draft"
        assert [name for name, _ in terms] == ["Fall", "Spring"]
        assert terms[0][1] == [a]
        assert set(terms[1][1]) == {b, c}

    def test_empty_term_is_kept(self, conn):
        w = make_world(conn)
        schedule_id = repo.create_schedule(conn, w["student"], [("Break", [])])
        assert read_schedule(conn, schedule_id) == ("draft", [("Break", [])])

    def test_unknown_schedule_reads_as_none(self, conn):
        assert read_schedule(conn, uuid.uuid4()) is None

    def test_failed_save_leaves_nothing_behind(self, conn):
        w = make_world(conn)
        a = w["courses"][0]
        with pytest.raises(errors.ForeignKeyViolation):
            repo.create_schedule(
                conn, w["student"], [("Fall", [a]), ("Spring", [uuid.uuid4()])]
            )
        assert count(conn, "schedules", "student_id = %s", (w["student"],)) == 0
        assert latest_draft_id(conn, w["student"]) is None

    def test_same_course_twice_in_one_term_is_rejected(self, conn):
        w = make_world(conn)
        a = w["courses"][0]
        with pytest.raises(errors.UniqueViolation):
            repo.create_schedule(conn, w["student"], [("Fall", [a, a])])

    def test_unknown_student_is_rejected(self, conn):
        make_world(conn)
        with pytest.raises(errors.ForeignKeyViolation):
            repo.create_schedule(conn, uuid.uuid4(), [("Fall", [])])


# --------------------------------------------------- replace and export --

class TestReplaceAndExport:
    def test_replace_draft_swaps_the_old_draft_for_the_new_one(self, conn):
        w = make_world(conn)
        a, b, _ = w["courses"]
        first = repo.create_schedule(conn, w["student"], [("Fall", [a])])
        second = repo.replace_draft(conn, w["student"], [("Spring", [b])])
        assert read_schedule(conn, first) is None
        assert latest_draft_id(conn, w["student"]) == second
        assert count(conn, "schedules", "student_id = %s", (w["student"],)) == 1

    def test_replace_draft_keeps_exported_schedules(self, conn):
        w = make_world(conn)
        a, b, _ = w["courses"]
        exported = repo.create_schedule(conn, w["student"], [("Fall", [a])])
        assert repo.mark_exported(conn, w["student"], exported) is True
        repo.replace_draft(conn, w["student"], [("Spring", [b])])
        assert read_schedule(conn, exported)[0] == "exported"

    def test_failed_replace_keeps_the_old_draft(self, conn):
        w = make_world(conn)
        a = w["courses"][0]
        old = repo.create_schedule(conn, w["student"], [("Fall", [a])])
        with pytest.raises(errors.ForeignKeyViolation):
            repo.replace_draft(conn, w["student"], [("Spring", [uuid.uuid4()])])
        assert read_schedule(conn, old) is not None

    def test_delete_drafts_removes_children_and_returns_the_count(self, conn):
        w = make_world(conn)
        a, b, _ = w["courses"]
        repo.create_schedule(conn, w["student"], [("Fall", [a])])
        repo.create_schedule(conn, w["student"], [("Spring", [b])])
        assert repo.delete_drafts(conn, w["student"]) == 2
        assert count(conn, "schedules", "student_id = %s", (w["student"],)) == 0

    def test_mark_exported_on_an_unknown_schedule_is_false(self, conn):
        w = make_world(conn)
        assert repo.mark_exported(conn, w["student"], uuid.uuid4()) is False

    def test_a_student_cannot_export_someone_elses_schedule(self, conn):
        w = make_world(conn)
        other = make_student(conn, w["program"])
        theirs = repo.create_schedule(conn, other, [("Fall", [w["courses"][0]])])
        assert repo.mark_exported(conn, w["student"], theirs) is False
        assert read_schedule(conn, theirs)[0] == "draft"

    def test_latest_draft_is_none_when_there_is_none(self, conn):
        w = make_world(conn)
        assert latest_draft_id(conn, w["student"]) is None


# ------------------------------------------------------ planner inputs --

def add_requirement(conn, program_id, course_id, category="core"):
    with conn.cursor(row_factory=tuple_row) as cur:
        cur.execute(
            "INSERT INTO requirements (program_id, course_id, category, credits_required) "
            "VALUES (%s, %s, %s, 3)",
            (program_id, course_id, category),
        )


def add_prereq(conn, course_id, required_id, kind="prereq"):
    with conn.cursor(row_factory=tuple_row) as cur:
        cur.execute(
            "INSERT INTO prerequisites (course_id, prerequisite_course_id, requirement_type) "
            "VALUES (%s, %s, %s)",
            (course_id, required_id, kind),
        )


def add_offering(conn, course_id, term_id):
    with conn.cursor(row_factory=tuple_row) as cur:
        cur.execute(
            "INSERT INTO course_offerings (course_id, term_id) VALUES (%s, %s)",
            (course_id, term_id),
        )


def add_transcript(conn, student_id, course_id, status):
    with conn.cursor(row_factory=tuple_row) as cur:
        cur.execute(
            "INSERT INTO transcript_entries (student_id, course_id, term, status) "
            "VALUES (%s, %s, 'Fall 2025', %s)",
            (student_id, course_id, status),
        )


class TestLoadPlanningInputs:
    def test_unknown_student_returns_none(self, conn):
        assert repo.load_planning_inputs(conn, uuid.uuid4(), today=FAR_FUTURE) is None

    def test_remaining_courses_come_from_the_students_program(self, conn):
        w = make_world(conn)
        a, b, _ = w["courses"]
        add_requirement(conn, w["program"], a)
        add_requirement(conn, w["program"], b)
        other_program = make_program(conn)
        add_requirement(conn, other_program, w["courses"][2])
        data = repo.load_planning_inputs(conn, w["student"], today=date(2000, 1, 1))
        assert set(data["remaining"]) == {a, b}

    def test_inactive_courses_and_empty_requirement_slots_are_skipped(self, conn):
        w = make_world(conn)
        a = w["courses"][0]
        legacy = make_course(conn, "OLD", is_active=False)
        add_requirement(conn, w["program"], a)
        add_requirement(conn, w["program"], legacy)
        with conn.cursor(row_factory=tuple_row) as cur:
            cur.execute(
                "INSERT INTO requirements (program_id, course_id, category, credits_required) "
                "VALUES (%s, NULL, 'elective', 3)",
                (w["program"],),
            )
        data = repo.load_planning_inputs(conn, w["student"], today=date(2000, 1, 1))
        assert data["remaining"] == [a]

    def test_completed_and_in_progress_count_but_planned_does_not(self, conn):
        w = make_world(conn)
        a, b, c = w["courses"]
        add_transcript(conn, w["student"], a, "completed")
        add_transcript(conn, w["student"], b, "in_progress")
        add_transcript(conn, w["student"], c, "planned")
        data = repo.load_planning_inputs(conn, w["student"], today=date(2000, 1, 1))
        assert set(data["satisfied"]) == {a, b}

    def test_only_future_terms_and_their_offerings_are_returned(self, conn):
        w = make_world(conn)
        a = w["courses"][0]
        t1, t2, t3 = w["terms"]  # starts 2099-01, 2099-02, 2099-03
        for t in (t1, t2, t3):
            add_offering(conn, a, t)
        data = repo.load_planning_inputs(conn, w["student"], today=date(2099, 1, 15))
        assert [t.term_id for t in data["terms"] if t.term_id in w["terms"]] == [t2, t3]
        assert data["offerings"][a] == {t2, t3}

    def test_prerequisites_keep_their_type(self, conn):
        w = make_world(conn)
        a, b, c = w["courses"]
        add_prereq(conn, b, a, "prereq")
        add_prereq(conn, c, b, "coreq")
        data = repo.load_planning_inputs(conn, w["student"], today=date(2000, 1, 1))
        assert (a, "prereq") in data["prerequisites"][b]
        assert (b, "coreq") in data["prerequisites"][c]


# ------------------------------------------------------------ end to end --

def test_plan_and_save_round_trip(conn):
    w = make_world(conn)
    a, b, c = w["courses"]
    t1, t2, t3 = w["terms"]
    for course in (a, b, c):
        add_requirement(conn, w["program"], course)
        for t in w["terms"]:
            add_offering(conn, course, t)
    add_prereq(conn, b, a)
    add_prereq(conn, c, b)
    add_transcript(conn, w["student"], a, "completed")

    data = repo.load_planning_inputs(conn, w["student"], today=date(2098, 1, 1))
    # Real terms from the shared database could appear too; keep this test's own.
    data["terms"] = [t for t in data["terms"] if t.term_id in w["terms"]]
    plan = build_plan(**data)
    assert plan.unplaced == []

    saved = repo.replace_draft(
        conn, w["student"], [(pt.term.name, pt.course_ids) for pt in plan.terms]
    )
    assert [ids for _, ids in read_schedule(conn, saved)[1]] == [[b], [c]]


# --------------------------------------- PostgresScheduleRepository writes --

class SameConnection:
    """Database stand-in that hands out the test's own connection and never closes it,
    so the class under test sees (and later rolls back) the test's rows."""

    def __init__(self, connection):
        self._connection = connection

    def connect(self):
        from contextlib import contextmanager

        @contextmanager
        def manager():
            yield self._connection

        return manager()


class TestRepositoryWrites:
    def test_replace_draft_then_get_schedules_round_trip(self, dict_conn):
        w = make_world(dict_conn)
        a, b, _ = w["courses"]
        store = PostgresScheduleRepository(SameConnection(dict_conn))
        new_id = store.replace_draft(str(w["student"]), [("Fall", [a]), ("Spring", [b])])
        schedules = store.get_schedules(str(w["student"]))
        assert [s["schedule_id"] for s in schedules] == [new_id]
        assert schedules[0]["status"] == "draft"
        terms = schedules[0]["terms"]
        assert [t["term_name"] for t in terms] == ["Fall", "Spring"]
        assert str(terms[0]["items"][0]["course_id"]) == str(a)

    def test_the_student_can_be_found_by_clerk_id(self, dict_conn):
        w = make_world(dict_conn)
        with dict_conn.cursor(row_factory=tuple_row) as cur:
            cur.execute("SELECT clerk_user_id FROM students WHERE student_id = %s", (w["student"],))
            clerk_id = cur.fetchone()[0]
        store = PostgresScheduleRepository(SameConnection(dict_conn))
        assert store.replace_draft(clerk_id, [("Fall", [])]) is not None
        assert len(store.get_schedules(clerk_id)) == 1

    def test_unknown_student_returns_none_and_saves_nothing(self, dict_conn):
        make_world(dict_conn)
        store = PostgresScheduleRepository(SameConnection(dict_conn))
        assert store.replace_draft("no-such-student", [("Fall", [])]) is None
        assert store.replace_draft("", [("Fall", [])]) is None

    def test_mark_exported_checks_the_owner_and_the_id(self, dict_conn):
        w = make_world(dict_conn)
        other = make_student(dict_conn, w["program"])
        store = PostgresScheduleRepository(SameConnection(dict_conn))
        mine = store.replace_draft(str(w["student"]), [("Fall", [])])
        assert store.mark_exported(str(other), mine) is False
        assert store.mark_exported(str(w["student"]), "not-a-uuid") is False
        assert store.mark_exported(str(w["student"]), mine) is True
        assert store.get_schedules(str(w["student"]))[0]["status"] == "exported"


def test_replace_draft_really_commits_through_database_connect():
    """The one test that commits. It uses its own rows and removes them afterwards."""
    url = os.environ["DATABASE_URL"]
    setup = psycopg.connect(url)
    ids = {}
    try:
        ids["program"] = make_program(setup)
        ids["course"] = make_course(setup, "CMT")
        ids["student"] = make_student(setup, ids["program"])
        setup.commit()

        store = PostgresScheduleRepository(Database(url))
        new_id = store.replace_draft(str(ids["student"]), [("Fall", [ids["course"]])])
        again = store.replace_draft(str(ids["student"]), [("Spring", [ids["course"]])])

        # Read through a different connection: only committed rows are visible.
        seen = store.get_schedules(str(ids["student"]))
        assert [s["schedule_id"] for s in seen] == [again]
        assert new_id != again
        assert seen[0]["terms"][0]["term_name"] == "Spring"
        assert store.mark_exported(str(ids["student"]), again) is True
        assert store.get_schedules(str(ids["student"]))[0]["status"] == "exported"
    finally:
        setup.rollback()
        with setup.cursor(row_factory=tuple_row) as cur:
            if "student" in ids:
                cur.execute(
                    "DELETE FROM schedule_items WHERE schedule_term_id IN (SELECT schedule_term_id "
                    "FROM schedule_terms WHERE schedule_id IN "
                    "(SELECT schedule_id FROM schedules WHERE student_id = %s))",
                    (ids["student"],),
                )
                cur.execute(
                    "DELETE FROM schedule_terms WHERE schedule_id IN "
                    "(SELECT schedule_id FROM schedules WHERE student_id = %s)",
                    (ids["student"],),
                )
                cur.execute("DELETE FROM schedules WHERE student_id = %s", (ids["student"],))
                cur.execute("DELETE FROM students WHERE student_id = %s", (ids["student"],))
            if "course" in ids:
                cur.execute("DELETE FROM courses WHERE course_id = %s", (ids["course"],))
            if "program" in ids:
                cur.execute("DELETE FROM programs WHERE program_id = %s", (ids["program"],))
        setup.commit()
        setup.close()
