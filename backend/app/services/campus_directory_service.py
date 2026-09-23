"""Contact information for advising and career services."""

from app.repositories.interfaces import ICampusDirectoryRepository


class CampusDirectoryService:
    """Finds an advisor or career services contact."""

    def __init__(self,
                 campus_directory_repository: ICampusDirectoryRepository):
        raise NotImplementedError

    def get_advisor_contact(self, student_id: str) -> dict:
        """Gets the advisor contact for a student.

        Args:
            student_id: The student who needs an advisor.

        Returns:
            The advisor's name, email, and booking link.
        """
        raise NotImplementedError

    def get_career_services_contact(self) -> dict:
        """Gets the Career Services contact.

        Returns:
            Career Services contact information and URL.
        """
        raise NotImplementedError
