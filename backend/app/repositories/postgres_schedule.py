"""PostgreSQL implementation of IScheduleRepository."""

from __future__ import annotations

from app.repositories.connection import Database
from app.repositories.interfaces import IScheduleRepository
from app.repositories.row_utils import serialize_row


class PostgresScheduleRepository(IScheduleRepository):
    """Reads student schedules, terms, and items.

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
