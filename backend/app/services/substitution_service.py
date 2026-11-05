"""Student-declared substitutions: declare, remove, and review.

A substitution says "I took X in place of required course Y." The app does
not approve these; the frontend tells the student to verify with an advisor.
Only the audit decides whether a declaration counts.
"""

from __future__ import annotations

from typing import Any

from app.api.errors import BAD_REQUEST
from app.api.errors import NOT_FOUND
from app.api.errors import ApiError
from app.repositories.connection import Database
from app.repositories.postgres_audit import PostgresAuditRepository
from app.repositories.postgres_catalog import PostgresCatalogRepository
from app.repositories.row_utils import normalize_code
from app.services.audit_service import AuditService
from app.services.course_catalog_service import CourseCatalogService


class SubstitutionService:
    """Reads and writes ``student_substitutions`` for one student.

    Args:
        database: PostgreSQL helper.
    """

    def __init__(self, database: Database):
        self._database = database
        self._audit_repo = PostgresAuditRepository(database)
        self._audit = AuditService(
            self._audit_repo,
            CourseCatalogService(PostgresCatalogRepository(database)),
        )

    def declare(
        self,
        clerk_user_id: str,
        requirement_code: str,
        substitute_code: str,
    ) -> dict[str, Any]:
        """Records or replaces the substitute for one required course.

        Args:
            clerk_user_id: Clerk ``sub`` for the signed-in student.
            requirement_code: Required course the student is excused from.
            substitute_code: Course the student took instead.

        Returns:
            The student's updated substitution list (see ``review``).

        Raises:
            ApiError: 404 unknown student. 400 if the requirement is not in
                the student's program, already completed, or the substitute
                is not on the student's transcript.
        """
        student = self._student(clerk_user_id)
        student_id = str(student['student_id'])
        requirement = self._course(requirement_code)
        substitute = self._course(substitute_code)
        if requirement is None or substitute is None:
            status, code = NOT_FOUND
            raise ApiError(status, code, 'That course is not in the catalog.')
        if requirement['course_id'] == substitute['course_id']:
            status, code = BAD_REQUEST
            raise ApiError(
                status, code, 'A course cannot substitute for itself.'
            )

        result = self._audit.audit(student_id)
        matches = {
            match['code']: match['status']
            for match in result['requirementMatches']
        }
        if requirement['code'] not in matches:
            status, code = BAD_REQUEST
            raise ApiError(
                status,
                code,
                f"{requirement['code']} is not required for your program.",
            )
        if matches[requirement['code']] == 'direct':
            status, code = BAD_REQUEST
            raise ApiError(
                status,
                code,
                f"You have already completed {requirement['code']}.",
            )
        if substitute['course_id'] not in self._taken_course_ids(student_id):
            status, code = BAD_REQUEST
            raise ApiError(
                status,
                code,
                f"{substitute['code']} is not on your transcript as completed "
                'or in progress.',
            )

        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO student_substitutions
                    (student_id, requirement_course_id,
                     substitute_course_id, source)
                VALUES (%s, %s, %s, 'student')
                ON CONFLICT (student_id, requirement_course_id)
                DO UPDATE SET substitute_course_id =
                    EXCLUDED.substitute_course_id,
                    created_at = now()
                """,
                (student_id, requirement['course_id'],
                 substitute['course_id']),
            )
            connection.commit()
        return self.review(clerk_user_id)

    def remove(self, clerk_user_id: str, substitution_id: str) -> dict[str, Any]:
        """Deletes one of the student's declared substitutions.

        Args:
            clerk_user_id: Clerk ``sub`` for the signed-in student.
            substitution_id: Row to delete.

        Returns:
            The student's updated substitution list (see ``review``).

        Raises:
            ApiError: 404 if the student or the substitution is not theirs.
        """
        student = self._student(clerk_user_id)
        with self._database.connect() as connection:
            deleted = connection.execute(
                """
                DELETE FROM student_substitutions
                WHERE substitution_id = %s::uuid AND student_id = %s
                RETURNING substitution_id
                """,
                (substitution_id, student['student_id']),
            ).fetchone()
            connection.commit()
        if deleted is None:
            status, code = NOT_FOUND
            raise ApiError(status, code, 'No such substitution.')
        return self.review(clerk_user_id)

    def review(self, clerk_user_id: str) -> dict[str, Any]:
        """Builds the data the substitution matcher needs.

        Args:
            clerk_user_id: Clerk ``sub`` for the signed-in student.

        Returns:
            ``requirements``: required courses that are not directly
            completed (open slots, including ones with a declared substitute).
            ``courses``: transcript courses that are not required (the pool).
            ``substitutions``: the student's declarations, with ``counted``.

        Raises:
            ApiError: 404 if no student record matches.
        """
        student = self._student(clerk_user_id)
        result = self._audit.audit(str(student['student_id']))
        titles = {
            course['code']: course for course in result['requiredCourses']
        }
        requirements = []
        for match in result['requirementMatches']:
            if match['status'] == 'direct':
                continue
            course = titles.get(match['code'], {})
            requirements.append({
                'code': match['code'],
                'title': course.get('title') or '',
                'credits': course.get('credits') or 0,
            })
        return {
            'requirements': requirements,
            'courses': result['transcriptCourses'],
            'substitutions': result['substitutions'],
        }

    def _student(self, clerk_user_id: str) -> dict[str, Any]:
        student = self._audit_repo.get_student(clerk_user_id)
        if student is None:
            status, code = NOT_FOUND
            raise ApiError(
                status,
                code,
                'No student record matches this account.',
            )
        return student

    def _course(self, code: str) -> dict[str, Any] | None:
        """Finds a catalog course by code, ignoring spaces and case."""
        sql = """
            SELECT course_id, code
            FROM courses
            WHERE replace(upper(code), ' ', '') = %s
        """
        with self._database.connect() as connection:
            row = connection.execute(sql, (normalize_code(code),)).fetchone()
        if row is None:
            return None
        return {'course_id': str(row['course_id']), 'code': row['code']}

    def _taken_course_ids(self, student_id: str) -> set[str]:
        """Course ids the student has completed or is taking."""
        sql = """
            SELECT course_id
            FROM transcript_entries
            WHERE student_id = %s AND status IN ('completed', 'in_progress')
        """
        with self._database.connect() as connection:
            rows = connection.execute(sql, (student_id,)).fetchall()
        return {str(row['course_id']) for row in rows}
