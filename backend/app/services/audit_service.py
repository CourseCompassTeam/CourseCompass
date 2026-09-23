"""Degree audit: deterministic credit and prerequisite logic.

This logic never uses the LLM, so audit answers cannot be hallucinated.
"""

from app.repositories.interfaces import IStudentAuditRepository
from app.services.course_catalog_service import CourseCatalogService


class AuditService:
    """Checks a student's progress through their degree."""

    def __init__(self, student_audit_repository: IStudentAuditRepository,
                 course_catalog_service: CourseCatalogService):
        raise NotImplementedError

    def audit(self, student_id: str) -> dict:
        """Computes credits completed and remaining and missing courses.

        Args:
            student_id: The student to audit.

        Returns:
            Credits completed, credits remaining, and remaining requirements.

        Raises:
            ApiError: 404 if the student does not exist.
        """
        raise NotImplementedError

    def check_prerequisites(self, student_id: str, course_id: str) -> bool:
        """Checks whether the student completed a course's prerequisites.

        Args:
            student_id: The student to check.
            course_id: The course the student wants to take.

        Returns:
            True if every prerequisite has a 'completed' transcript entry.
        """
        raise NotImplementedError
