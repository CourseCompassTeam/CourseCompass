"""Data access interfaces.

Repositories are the only code that talks to PostgreSQL. Services depend
on these interfaces, not on concrete implementations, so a new data source
only needs a new implementation here (QA-04) and tests can use fakes.
"""

import abc


class IStudentAuditRepository(abc.ABC):
    """Student degree-related data."""

    @abc.abstractmethod
    def get_completed_courses(self, student_id: str) -> list[dict]:
        """Gets the student's transcript entries with status 'completed'.

        Args:
            student_id: The student to look up.

        Returns:
            Completed courses with their credits.
        """

    @abc.abstractmethod
    def get_program_requirements(self, student_id: str) -> list[dict]:
        """Gets the requirements of the student's program.

        Args:
            student_id: The student to look up.

        Returns:
            The program's core and elective requirements.
        """


class ICourseCatalogRepository(abc.ABC):
    """Course-related data."""

    @abc.abstractmethod
    def get_course(self, course_id: str) -> dict | None:
        """Gets a course by ID.

        Args:
            course_id: The course to look up.

        Returns:
            The course, or None if it does not exist.
        """

    @abc.abstractmethod
    def get_prerequisites(self, course_id: str) -> list[dict]:
        """Gets a course's prerequisites and corequisites.

        Args:
            course_id: The course to look up.

        Returns:
            Prerequisite records for the course.
        """


class ICampusDirectoryRepository(abc.ABC):
    """Campus contact data (advisors, career services)."""

    @abc.abstractmethod
    def get_advisor_contacts(self) -> list[dict]:
        """Gets all advisor contacts.

        Returns:
            Advisor names and emails.
        """


class IStudentMilestoneRepository(abc.ABC):
    """Milestone data used for next-step suggestions."""

    @abc.abstractmethod
    def get_milestones(self) -> list[dict]:
        """Gets all milestones.

        Returns:
            Milestone records.
        """
