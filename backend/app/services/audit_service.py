"""Degree audit: deterministic credit and prerequisite logic.

This logic never uses the LLM, so audit answers cannot be hallucinated.
"""

from app.api.errors import ApiError
from app.api.errors import NOT_FOUND
from app.repositories.interfaces import IStudentAuditRepository
from app.services.course_catalog_service import CourseCatalogService


class AuditService:
    """Checks a student's progress through their degree.

    Args:
        student_audit_repository: Student, transcript, and program access.
        course_catalog_service: Used for prerequisite lookups.
    """

    def __init__(self, student_audit_repository: IStudentAuditRepository,
                 course_catalog_service: CourseCatalogService):
        self._audit = student_audit_repository
        self._catalog = course_catalog_service

    def audit(self, student_id: str, program_name: str | None = None) -> dict:
        """Computes credits completed and remaining and missing courses.

        When no student row exists, leftover requirements are every
        required course in the named or default program.

        Args:
            student_id: The student to audit. May be empty.
            program_name: Optional program name from the student query.

        Returns:
            Credits completed, credits remaining, and remaining
            requirements.

        Raises:
            ApiError: 404 if no matching program exists.
        """
        student = self._audit.get_student(student_id) if student_id else None
        completed = (
            self._audit.get_completed_courses(student_id)
            if student is not None else []
        )
        program = self._resolve_program(student, program_name)
        if program is None:
            status, code = NOT_FOUND
            raise ApiError(
                status,
                code,
                'No degree program was found.',
            )
        requirements = self._audit.get_requirements_for_program(
            program['program_id']
        )
        required_courses = [
            {
                'code': row.get('code'),
                'title': row.get('title'),
                'description': row.get('description') or '',
                'credits': (
                    row.get('credits')
                    or row.get('credits_required')
                    or 0
                ),
                'category': row.get('category') or 'core',
            }
            for row in requirements
            if row.get('code')
        ]
        completed_codes = {
            row.get('code') for row in completed if row.get('code')
        }
        missing = [
            course for course in required_courses
            if course['code'] not in completed_codes
        ]
        credits_completed = sum(
            int(row.get('credits') or 0) for row in completed
        )
        credits_required = int(
            program.get('total_credits_required') or 0
        )
        missing_credits = sum(int(course['credits'] or 0) for course in missing)
        if credits_required:
            credits_remaining = max(0, credits_required - credits_completed)
        else:
            credits_remaining = missing_credits
        return {
            'programName': program.get('name'),
            'creditsRequired': credits_required,
            'creditsCompleted': credits_completed,
            'creditsRemaining': credits_remaining,
            'requirementsMet': len(missing) == 0 and credits_remaining == 0,
            'missingCourses': [course['code'] for course in missing],
            'requiredCourses': required_courses,
        }

    def check_prerequisites(self, student_id: str, course_id: str) -> bool:
        """Checks whether the student completed a course's prerequisites.

        Args:
            student_id: The student to check.
            course_id: The course the student wants to take.

        Returns:
            True if every prerequisite has a 'completed' transcript entry.
        """
        required = self._catalog.get_prerequisites(course_id)
        if not required:
            return True
        completed = {
            row.get('code')
            for row in self._audit.get_completed_courses(student_id)
            if row.get('code')
        }
        return all(code in completed for code in required)

    def leftover_courses(
        self,
        student_id: str,
        program_name: str | None = None,
    ) -> list[dict]:
        """Returns required courses the student has not completed.

        Args:
            student_id: The student to audit. May be empty.
            program_name: Optional program name.

        Returns:
            Leftover required-course dicts.
        """
        result = self.audit(student_id, program_name)
        missing = set(result['missingCourses'])
        return [
            course for course in result['requiredCourses']
            if course['code'] in missing
        ]

    def _resolve_program(
        self,
        student: dict | None,
        program_name: str | None,
    ) -> dict | None:
        """Picks the program for an audit.

        Args:
            student: Student row, if found.
            program_name: Optional name from the query.

        Returns:
            A program row, or None.
        """
        if program_name:
            named = self._audit.get_program_by_name(program_name)
            if named is not None:
                return named
        if student and student.get('program_id'):
            enrolled = self._audit.get_program(student['program_id'])
            if enrolled is not None:
                return enrolled
        if program_name:
            return None
        return self._audit.get_default_program()
