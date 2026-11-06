"""Writes schedules and gathers planner inputs in PostgreSQL.

Reading saved schedules is PostgresScheduleRepository.get_schedules; this module
does not duplicate it.

Every function takes an open psycopg (v3) connection. Rows are read by position
whatever row factory the connection uses (Database.connect uses dict rows). Multi-step writes run in
conn.transaction(), so a failure leaves nothing half-saved. If the caller already
has a transaction open, that becomes a savepoint and the caller commits (tests use
this to roll everything back). On a fresh connection with nothing open, the write
commits itself when it finishes.
"""

from datetime import date

from psycopg.rows import tuple_row

from app.scheduling.planner import Term

# ------------------------------------------------------------------ write --


def create_schedule(conn, student_id, planned_terms):
    """Saves a new draft schedule and returns its schedule_id.

    planned_terms: [(term_name, [course_id, ...]), ...] in the order the student
    takes them. term_order is stored as 1, 2, 3, ...
    """
    with conn.transaction(), conn.cursor(row_factory=tuple_row) as cur:
        cur.execute(
            "INSERT INTO schedules (student_id, status) VALUES (%s, 'draft') "
            "RETURNING schedule_id",
            (student_id,),
        )
        schedule_id = cur.fetchone()[0]
        for order, (term_name, course_ids) in enumerate(planned_terms, start=1):
            cur.execute(
                "INSERT INTO schedule_terms (schedule_id, term_name, term_order) "
                "VALUES (%s, %s, %s) RETURNING schedule_term_id",
                (schedule_id, term_name, order),
            )
            schedule_term_id = cur.fetchone()[0]
            for course_id in course_ids:
                cur.execute(
                    "INSERT INTO schedule_items (schedule_term_id, course_id) "
                    "VALUES (%s, %s)",
                    (schedule_term_id, course_id),
                )
    return schedule_id


def replace_draft(conn, student_id, planned_terms):
    """Deletes the student's draft schedules and saves a new one, all or nothing.

    Exported schedules are kept. Returns the new schedule_id.
    """
    with conn.transaction():
        delete_drafts(conn, student_id)
        return create_schedule(conn, student_id, planned_terms)


def delete_drafts(conn, student_id):
    """Deletes the student's draft schedules (children first). Returns the count."""
    with conn.cursor(row_factory=tuple_row) as cur:
        cur.execute(
            "SELECT schedule_id FROM schedules "
            "WHERE student_id = %s AND status = 'draft'",
            (student_id,),
        )
        ids = [row[0] for row in cur.fetchall()]
        for schedule_id in ids:
            cur.execute(
                "DELETE FROM schedule_items WHERE schedule_term_id IN "
                "(SELECT schedule_term_id FROM schedule_terms WHERE schedule_id = %s)",
                (schedule_id,),
            )
            cur.execute("DELETE FROM schedule_terms WHERE schedule_id = %s", (schedule_id,))
            cur.execute("DELETE FROM schedules WHERE schedule_id = %s", (schedule_id,))
    return len(ids)


def mark_exported(conn, student_id, schedule_id):
    """Marks one of the student's schedules as exported.

    Returns False if that schedule does not exist or belongs to someone else.
    """
    with conn.cursor(row_factory=tuple_row) as cur:
        cur.execute(
            "UPDATE schedules SET status = 'exported' "
            "WHERE schedule_id = %s AND student_id = %s",
            (schedule_id, student_id),
        )
        return cur.rowcount == 1


# ----------------------------------------------------------- planner input --


def load_planning_inputs(conn, student_id, today=None):
    """Gathers everything build_plan needs for one student.

    Returns a dict with keys remaining, satisfied, prerequisites, offerings, terms,
    or None if the student does not exist. Only active courses are planned, and
    only terms that have not started yet are offered.
    """
    today = today or date.today()
    with conn.cursor(row_factory=tuple_row) as cur:
        cur.execute("SELECT program_id FROM students WHERE student_id = %s", (student_id,))
        row = cur.fetchone()
        if row is None:
            return None
        program_id = row[0]

        # Required courses for the program. A requirement with no course
        # (a generic elective slot) cannot be placed, so it is skipped.
        cur.execute(
            "SELECT r.course_id FROM requirements r "
            "JOIN courses c ON c.course_id = r.course_id "
            "WHERE r.program_id = %s AND r.course_id IS NOT NULL AND c.is_active "
            "ORDER BY c.code",
            (program_id,),
        )
        required = [r[0] for r in cur.fetchall()]

        # Completed and in-progress courses both count as done for planning.
        cur.execute(
            "SELECT DISTINCT course_id FROM transcript_entries "
            "WHERE student_id = %s AND status IN ('completed', 'in_progress')",
            (student_id,),
        )
        satisfied = [r[0] for r in cur.fetchall()]

        cur.execute(
            "SELECT course_id, prerequisite_course_id, requirement_type FROM prerequisites"
        )
        prerequisites = {}
        for course_id, required_id, kind in cur.fetchall():
            prerequisites.setdefault(course_id, []).append((required_id, kind))

        cur.execute(
            "SELECT term_id, term_name FROM terms WHERE start_date > %s ORDER BY start_date",
            (today,),
        )
        terms = [Term(term_id=r[0], name=r[1]) for r in cur.fetchall()]
        future = {t.term_id for t in terms}

        cur.execute("SELECT course_id, term_id FROM course_offerings")
        offerings = {}
        for course_id, term_id in cur.fetchall():
            if term_id in future:
                offerings.setdefault(course_id, set()).add(term_id)

    return {
        "remaining": required,
        "satisfied": satisfied,
        "prerequisites": prerequisites,
        "offerings": offerings,
        "terms": terms,
    }
