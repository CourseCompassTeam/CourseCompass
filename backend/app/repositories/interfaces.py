"""Data access interfaces.

Repositories are the only code that talks to PostgreSQL. Services depend
on these interfaces, not on concrete implementations, so a new data source
only needs a new implementation here (QA-04) and tests can use fakes.
"""

import abc


class IStudentAuditRepository(abc.ABC):
    """Student degree-related data."""

    @abc.abstractmethod
    def get_student(self, student_id: str) -> dict | None:
        """Gets a student by id.

        Args:
            student_id: UUID or clerk user id.

        Returns:
            The student row, or None.
        """

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

    @abc.abstractmethod
    def get_program(self, program_id: str) -> dict | None:
        """Gets a program by id.

        Args:
            program_id: Program UUID.

        Returns:
            A program row, or None.
        """

    @abc.abstractmethod
    def get_default_program(self) -> dict | None:
        """Gets the first program (used when no student is signed in).

        Returns:
            A program row, or None if the table is empty.
        """

    @abc.abstractmethod
    def get_program_by_name(self, name: str) -> dict | None:
        """Finds a program by name.

        Args:
            name: Full or partial program name.

        Returns:
            A program row, or None.
        """

    @abc.abstractmethod
    def get_requirements_for_program(self, program_id: str) -> list[dict]:
        """Gets required courses for a program.

        Args:
            program_id: Program UUID.

        Returns:
            Requirement rows joined to course catalog fields.
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

    @abc.abstractmethod
    def list_active_courses(self) -> list[dict]:
        """Lists every active catalog course.

        Returns:
            Active course rows.
        """

    @abc.abstractmethod
    def list_syllabus_chunks(self, course_id: str) -> list[dict]:
        """Lists syllabus chunks for a course.

        Args:
            course_id: Course UUID or code.

        Returns:
            Chunk rows (without embeddings).
        """


class ICampusDirectoryRepository(abc.ABC):
    """Campus contact data (advisors, career services)."""

    @abc.abstractmethod
    def get_advisor_contacts(self) -> list[dict]:
        """Gets all advisor contacts.

        Returns:
            Advisor names and emails.
        """

    @abc.abstractmethod
    def get_contacts_by_type(self, contact_type: str) -> list[dict]:
        """Gets contacts of one type.

        Args:
            contact_type: ``advisor`` or ``career_services``.

        Returns:
            Matching contact rows.
        """


class IStudentMilestoneRepository(abc.ABC):
    """Milestone data used for next-step suggestions."""

    @abc.abstractmethod
    def get_milestones(self) -> list[dict]:
        """Gets all milestones.

        Returns:
            Milestone records.
        """


class IScheduleRepository(abc.ABC):
    """Student schedule tables."""

    @abc.abstractmethod
    def get_schedules(self, student_id: str) -> list[dict]:
        """Gets schedules for a student.

        Args:
            student_id: The student to look up.

        Returns:
            Schedule rows with nested terms and items when present.
        """


class IIngestionLogRepository(abc.ABC):
    """Admin ingestion log table."""

    @abc.abstractmethod
    def list_logs(self, limit: int = 20) -> list[dict]:
        """Gets recent ingestion jobs.

        Args:
            limit: Maximum rows to return.

        Returns:
            Ingestion log rows.
        """
