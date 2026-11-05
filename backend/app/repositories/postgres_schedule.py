"""PostgreSQL implementation of IScheduleRepository."""

from __future__ import annotations

import uuid

from app.repositories.connection import Database
from app.repositories.interfaces import IScheduleRepository
from app.repositories.row_utils import serialize_row
from app.scheduling import schedule_repository


class PostgresScheduleRepository(IScheduleRepository):
    """Reads and writes student schedules, terms, and items.

    Args:
        database: Shared PostgreSQL connection helper.
    """

    def __init__(self, database: Database):
        self._database = database

    def get_schedules(self, student_id: str) -> list[dict]:
        """Gets schedules for a student.

        Args:
            student_id: UUID or clerk user id.

        Returns:
            Schedule rows with nested terms and items when present.
        """
        if not student_id:
            return []
        schedule_sql = """
            SELECT s.schedule_id, s.student_id, s.status, s.created_at
            FROM schedules s
            JOIN students st ON st.student_id = s.student_id
            WHERE st.student_id::text = %s
               OR st.clerk_user_id = %s
            ORDER BY s.created_at
        """
        term_sql = """
            SELECT schedule_term_id, schedule_id, term_name, term_order
            FROM schedule_terms
            WHERE schedule_id = %s
            ORDER BY term_order, term_name
        """
        item_sql = """
            SELECT i.schedule_item_id, i.schedule_term_id, i.course_id,
                   c.code, c.title, c.credits
            FROM schedule_items i
            JOIN courses c ON c.course_id = i.course_id
            WHERE i.schedule_term_id = %s
            ORDER BY c.code
        """
        with self._database.connect() as connection:
            schedules = [
                serialize_row(row)
                for row in connection.execute(
                    schedule_sql, (student_id, student_id)
                ).fetchall()
            ]
            for schedule in schedules:
                terms = [
                    serialize_row(row)
                    for row in connection.execute(
                        term_sql, (schedule['schedule_id'],)
                    ).fetchall()
                ]
                for term in terms:
                    term['items'] = [
                        serialize_row(row)
                        for row in connection.execute(
                            item_sql, (term['schedule_term_id'],)
                        ).fetchall()
                    ]
                schedule['terms'] = terms
        return schedules

    def replace_draft(
        self, student_id: str, planned_terms: list[tuple[str, list[str]]]
    ) -> str | None:
        """Replaces the student's draft schedules with a new draft.

        Exported schedules are kept. The old drafts are deleted only if the new
        one saves.

        Args:
            student_id: UUID or clerk user id.
            planned_terms: (term name, [course_id, ...]) in the order taken.

        Returns:
            The new schedule_id, or None if the student does not exist.
        """
        # The student lookup runs inside the transaction on purpose: any query
        # outside it would open an implicit transaction, and the block below
        # would then become a savepoint that is never committed.
        with self._database.connect() as connection, connection.transaction():
            resolved = find_student_id(connection, student_id)
            if resolved is None:
                return None
            new_id = schedule_repository.replace_draft(
                connection, resolved, planned_terms
            )
        return str(new_id)

    def mark_exported(self, student_id: str, schedule_id: str) -> bool:
        """Marks one of the student's schedules as exported.

        Args:
            student_id: UUID or clerk user id.
            schedule_id: The schedule to mark.

        Returns:
            False if the student or schedule does not exist, or the schedule
            belongs to another student.
        """
        try:
            uuid.UUID(str(schedule_id))
        except ValueError:
            return False
        with self._database.connect() as connection, connection.transaction():
            resolved = find_student_id(connection, student_id)
            if resolved is None:
                return False
            return schedule_repository.mark_exported(
                connection, resolved, schedule_id
            )


def find_student_id(connection, student_id: str):
    """Resolves a UUID or clerk user id to the student's UUID, or None."""
    if not student_id:
        return None
    row = connection.execute(
        'SELECT student_id FROM students '
        'WHERE student_id::text = %s OR clerk_user_id = %s',
        (student_id, student_id),
    ).fetchone()
    return row['student_id'] if row else None
