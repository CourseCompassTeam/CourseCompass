"""PostgreSQL implementation of ICourseCatalogRepository."""

from __future__ import annotations

from app.repositories.connection import Database
from app.repositories.interfaces import ICourseCatalogRepository
from app.repositories.row_utils import normalize_code
from app.repositories.row_utils import serialize_row


class PostgresCatalogRepository(ICourseCatalogRepository):
    """Reads courses, prerequisites, and syllabus chunks.

    Args:
        database: Shared PostgreSQL connection helper.
    """

    def __init__(self, database: Database):
        self._database = database

    def get_course(self, course_id: str) -> dict | None:
        """Gets a course by UUID or catalog code.

        Args:
            course_id: Course UUID or code such as ``MSSE 635``.

        Returns:
            The course, or None if it does not exist.
        """
        if not course_id:
            return None
        sql = """
            SELECT course_id, code, title, description, credits, is_active
            FROM courses
            WHERE course_id::text = %s
               OR replace(upper(code), ' ', '') = %s
            LIMIT 1
        """
        with self._database.connect() as connection:
            row = connection.execute(
                sql, (course_id, normalize_code(course_id))
            ).fetchone()
        return serialize_row(row)

    def get_prerequisites(self, course_id: str) -> list[dict]:
        """Gets a course's prerequisites and corequisites.

        Args:
            course_id: Course UUID or code.

        Returns:
            Prerequisite records for the course.
        """
        course = self.get_course(course_id)
        if course is None:
            return []
        sql = """
            SELECT p.prerequisite_id, p.course_id,
                   p.prerequisite_course_id, p.requirement_type,
                   c.code, c.title, c.credits
            FROM prerequisites p
            JOIN courses c ON c.course_id = p.prerequisite_course_id
            WHERE p.course_id = %s
            ORDER BY c.code
        """
        with self._database.connect() as connection:
            rows = connection.execute(
                sql, (course['course_id'],)
            ).fetchall()
        return [serialize_row(row) for row in rows]

    def list_active_courses(self) -> list[dict]:
        """Lists every active catalog course.

        Returns:
            Active course rows.
        """
        sql = """
            SELECT course_id, code, title, description, credits, is_active
            FROM courses
            WHERE is_active = TRUE
            ORDER BY code
        """
        with self._database.connect() as connection:
            rows = connection.execute(sql).fetchall()
        return [serialize_row(row) for row in rows]

    def list_syllabus_chunks(self, course_id: str) -> list[dict]:
        """Lists syllabus chunks for a course.

        Args:
            course_id: Course UUID or code.

        Returns:
            Chunk rows (without embeddings).
        """
        course = self.get_course(course_id)
        if course is None:
            return []
        sql = """
            SELECT chunk_id, course_id, chunk_index, chunk_text
            FROM syllabus_chunks
            WHERE course_id = %s
            ORDER BY chunk_index
        """
        with self._database.connect() as connection:
            rows = connection.execute(
                sql, (course['course_id'],)
            ).fetchall()
        return [serialize_row(row) for row in rows]
