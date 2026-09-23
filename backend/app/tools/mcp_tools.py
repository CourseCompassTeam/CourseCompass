"""The fixed set of tools the LLM is allowed to call.

Each tool is single-purpose and returns only the authenticated student's
own data. The LLM cannot query the database any other way (QA-03).
"""

from typing import Any

from app.services.audit_service import AuditService
from app.services.campus_directory_service import CampusDirectoryService
from app.services.course_catalog_service import CourseCatalogService
from app.services.student_milestone_service import StudentMilestoneService


class MCPTools:
    """Directory of every tool available to the LLM provider."""

    def __init__(self, audit_service: AuditService,
                 course_catalog_service: CourseCatalogService,
                 campus_directory_service: CampusDirectoryService,
                 student_milestone_service: StudentMilestoneService):
        raise NotImplementedError

    def audit_degree(self, student_id: str) -> dict[str, Any]:
        """US-01: credits completed, credits remaining, missing courses.

        Args:
            student_id: The authenticated student's ID.

        Returns:
            The student's degree audit.
        """
        raise NotImplementedError

    def get_course_description(self, student_id: str,
                               course_id: str) -> dict[str, Any]:
        """US-02: a course description plus the advising URL.

        Args:
            student_id: The authenticated student's ID.
            course_id: The course to describe.

        Returns:
            The course description and advising_url.
        """
        raise NotImplementedError

    def recommend_courses(self, student_id: str,
                          interest: str) -> dict[str, Any]:
        """US-03: courses that fit the student's interests and degree.

        Args:
            student_id: The authenticated student's ID.
            interest: The topic the student is interested in.

        Returns:
            Recommended courses with descriptions.
        """
        raise NotImplementedError

    def build_schedule(self, student_id: str) -> dict[str, Any]:
        """US-04 (Could Have): a term schedule exportable as .ics.

        Args:
            student_id: The authenticated student's ID.

        Returns:
            The proposed course schedule.
        """
        raise NotImplementedError

    def get_advisor_contact(self, student_id: str) -> dict[str, Any]:
        """US-05: who to contact when the chatbot cannot answer.

        Args:
            student_id: The authenticated student's ID.

        Returns:
            The advising_url.
        """
        raise NotImplementedError

    def get_career_services(self, student_id: str) -> dict[str, Any]:
        """US-06: route career questions to Career Services.

        Args:
            student_id: The authenticated student's ID.

        Returns:
            The career_services_url.
        """
        raise NotImplementedError

    def get_next_milestones(self, student_id: str) -> dict[str, Any]:
        """US-07 (Could Have): next steps outside of class.

        Args:
            student_id: The authenticated student's ID.

        Returns:
            Milestones to consider at the student's stage.
        """
        raise NotImplementedError
