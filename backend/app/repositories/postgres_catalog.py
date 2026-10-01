"""PostgreSQL implementation of ICourseCatalogRepository."""

from __future__ import annotations

from app.repositories.connection import Database
from app.repositories.interfaces import ICourseCatalogRepository
from app.repositories.row_utils import course_number_query
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
        matches = self.find_courses(course_id)
        if len(matches) == 1:
            return matches[0]
        return None

    def find_courses(self, course_id: str) -> list[dict]:
        """Finds a course by UUID, code, or a bare number such as 697.

        A number matches the digits in the catalog code, so ``697``
        finds ``MSCC 697``. A full code stays an exact match.

        Args:
            course_id: Course UUID, code, or number.

        Returns:
            Matching course rows, ordered by code.
        """
        if not course_id:
            return []
        exact_sql = """
            SELECT course_id, code, title, description, credits, is_active
            FROM courses
            WHERE course_id::text = %s
               OR replace(upper(code), ' ', '') = %s
            ORDER BY code
        """
        with self._database.connect() as connection:
            rows = connection.execute(
                exact_sql, (course_id, normalize_code(course_id))
            ).fetchall()
            if rows:
                return [serialize_row(row) for row in rows]
            number = course_number_query(course_id)
            if not number:
                return []
            number_sql = """
                SELECT course_id, code, title, description, credits,
                       is_active
                FROM courses
                WHERE regexp_replace(code, '[^0-9]', '', 'g') = %s
                ORDER BY code
            """
            rows = connection.execute(number_sql, (number,)).fetchall()
        return [serialize_row(row) for row in rows]

    def list_programs_for_course(self, course_id: str) -> list[str]:
        """Lists programs whose requirements include this course.

        Args:
            course_id: Course UUID.

        Returns:
            Program names.
        """
        if not course_id:
            return []
        sql = """
            SELECT DISTINCT p.name
            FROM requirements r
            JOIN programs p ON p.program_id = r.program_id
            WHERE r.course_id = %s
            ORDER BY p.name
        """
        with self._database.connect() as connection:
            rows = connection.execute(sql, (course_id,)).fetchall()
        return [
            row['name']
            for row in rows
            if row.get('name')
        ]

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

    def list_offerings(self) -> list[dict]:
        """Lists each offering with its term name and dates.

        Returns:
            Rows of course code, term name, start date, and end date.
        """
        sql = """
            SELECT c.code, c.title, t.term_name, t.start_date, t.end_date
            FROM course_offerings o
            JOIN courses c ON c.course_id = o.course_id
            JOIN terms t ON t.term_id = o.term_id
            ORDER BY t.start_date, c.code
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

    def list_all_syllabus_chunks(self) -> list[dict]:
        """Lists syllabus text for every course.

        Returns:
            Rows with course code, chunk index, and chunk text.
        """
        sql = """
            SELECT c.code, s.chunk_index, s.chunk_text
            FROM syllabus_chunks s
            JOIN courses c ON c.course_id = s.course_id
            ORDER BY c.code, s.chunk_index
        """
        with self._database.connect() as connection:
            rows = connection.execute(sql).fetchall()
        return [serialize_row(row) for row in rows]
