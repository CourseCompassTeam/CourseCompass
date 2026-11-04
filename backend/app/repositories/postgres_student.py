"""PostgreSQL implementation of IStudentRepository."""

from __future__ import annotations

from app.repositories.connection import Database
from app.repositories.interfaces import IStudentRepository


class PostgresStudentRepository(IStudentRepository):
    """Writes student rows.

    Args:
        database: Shared PostgreSQL connection helper.
    """

    def __init__(self, database: Database):
        self._database = database

    def insert_student_if_absent(
        self,
        clerk_user_id: str,
        email: str,
        full_name: str,
        program_id: str,
    ) -> bool:
        """Inserts an active student unless the Clerk id or email exists.

        Args:
            clerk_user_id: Clerk ``sub`` for the new user.
            email: Primary email address.
            full_name: Display name.
            program_id: Program the student is enrolled in.

        Returns:
            True when a row was inserted, False when one already matched.
        """
        sql = """
            INSERT INTO students
                (program_id, clerk_user_id, email, full_name, status)
            VALUES (%s, %s, %s, %s, 'active')
            ON CONFLICT DO NOTHING
            RETURNING student_id
        """
        with self._database.connect() as connection:
            row = connection.execute(
                sql, (program_id, clerk_user_id, email, full_name)
            ).fetchone()
            connection.commit()
        return row is not None
