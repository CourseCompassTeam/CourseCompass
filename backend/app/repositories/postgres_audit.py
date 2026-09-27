"""PostgreSQL implementation of IStudentAuditRepository."""

from __future__ import annotations

from app.repositories.connection import Database
from app.repositories.interfaces import IStudentAuditRepository
from app.repositories.row_utils import serialize_row


class PostgresAuditRepository(IStudentAuditRepository):
    """Reads students, transcripts, programs, and requirements.

    Args:
        database: Shared PostgreSQL connection helper.
    """

    def __init__(self, database: Database):
        self._database = database

    def get_student(self, student_id: str) -> dict | None:
        """Gets a student by UUID or Clerk user id.

        Args:
            student_id: UUID or clerk user id.

        Returns:
            The student row, or None.
        """
        if not student_id:
            return None
        sql = """
            SELECT student_id, program_id, clerk_user_id, email,
                   full_name, status, created_at
            FROM students
            WHERE student_id::text = %s
               OR clerk_user_id = %s
            LIMIT 1
        """
        with self._database.connect() as connection:
            row = connection.execute(sql, (student_id, student_id)).fetchone()
        return serialize_row(row)

    def get_completed_courses(self, student_id: str) -> list[dict]:
        """Gets completed transcript rows for a student.

        Args:
            student_id: The student to look up.

        Returns:
            Completed courses with their credits.
        """
        student = self.get_student(student_id)
        if student is None:
            return []
        sql = """
            SELECT c.course_id, c.code, c.title, c.credits,
                   t.status, t.term
            FROM transcript_entries t
            JOIN courses c ON c.course_id = t.course_id
            WHERE t.student_id = %s
              AND t.status = 'completed'
            ORDER BY c.code
        """
        with self._database.connect() as connection:
            rows = connection.execute(
                sql, (student['student_id'],)
            ).fetchall()
        return [serialize_row(row) for row in rows]

    def get_program_requirements(self, student_id: str) -> list[dict]:
        """Gets requirements for the student's enrolled program.

        Args:
            student_id: The student to look up.

        Returns:
            The program's core and elective requirements.
        """
        student = self.get_student(student_id)
        if student is None or not student.get('program_id'):
            return []
        return self.get_requirements_for_program(student['program_id'])

    def get_program(self, program_id: str) -> dict | None:
        """Gets a program by id.

        Args:
            program_id: Program UUID.

        Returns:
            A program row, or None.
        """
        if not program_id:
            return None
        sql = """
            SELECT program_id, name, total_credits_required, created_at
            FROM programs
            WHERE program_id::text = %s
            LIMIT 1
        """
        with self._database.connect() as connection:
            row = connection.execute(sql, (program_id,)).fetchone()
        return serialize_row(row)

    def get_default_program(self) -> dict | None:
        """Gets the first program (used when no student is signed in).

        Returns:
            A program row, or None if the table is empty.
        """
        sql = """
            SELECT program_id, name, total_credits_required, created_at
            FROM programs
            ORDER BY created_at
            LIMIT 1
        """
        with self._database.connect() as connection:
            row = connection.execute(sql).fetchone()
        return serialize_row(row)

    def get_program_by_name(self, name: str) -> dict | None:
        """Finds a program by name.

        Args:
            name: Full or partial program name.

        Returns:
            A program row, or None.
        """
        if not name or not name.strip():
            return None
        sql = """
            SELECT program_id, name, total_credits_required, created_at
            FROM programs
            WHERE name ILIKE %s
            ORDER BY length(name)
            LIMIT 1
        """
        with self._database.connect() as connection:
            row = connection.execute(
                sql, (f'%{name.strip()}%',)
            ).fetchone()
        return serialize_row(row)

    def get_requirements_for_program(self, program_id: str) -> list[dict]:
        """Gets required courses for a program.

        Args:
            program_id: Program UUID.

        Returns:
            Requirement rows joined to course catalog fields.
        """
        sql = """
            SELECT r.requirement_id, r.program_id, r.course_id,
                   r.category, r.credits_required,
                   c.code, c.title, c.description, c.credits,
                   c.is_active
            FROM requirements r
            LEFT JOIN courses c ON c.course_id = r.course_id
            WHERE r.program_id = %s
            ORDER BY c.code
        """
        with self._database.connect() as connection:
            rows = connection.execute(sql, (program_id,)).fetchall()
        return [serialize_row(row) for row in rows]
