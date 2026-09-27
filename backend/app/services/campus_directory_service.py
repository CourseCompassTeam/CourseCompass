"""Contact information for advising and career services."""

from app.repositories.interfaces import ICampusDirectoryRepository

_DEFAULT_ADVISING = {
    'resourceName': 'Book an advising appointment',
    'url': 'https://example.com/advising',
    'name': None,
    'email': None,
}

_DEFAULT_CAREER = {
    'resourceName': 'Career Services',
    'url': 'https://example.com/career-services',
    'name': None,
    'email': None,
}


class CampusDirectoryService:
    """Finds an advisor or career services contact.

    Args:
        campus_directory_repository: Campus contact table access.
    """

    def __init__(self,
                 campus_directory_repository: ICampusDirectoryRepository):
        self._directory = campus_directory_repository

    def get_advisor_contact(self, student_id: str) -> dict:
        """Gets the advisor contact for a student.

        Args:
            student_id: The student who needs an advisor.

        Returns:
            The advisor's name, email, and booking link.
        """
        del student_id
        return self._first_contact('advisor', _DEFAULT_ADVISING)

    def get_career_services_contact(self) -> dict:
        """Gets the Career Services contact.

        Returns:
            Career Services contact information and URL.
        """
        return self._first_contact(
            'career_services',
            _DEFAULT_CAREER,
        )

    def _first_contact(self, contact_type: str, fallback: dict) -> dict:
        """Returns the first stored contact of a type, or a fallback.

        Args:
            contact_type: ``advisor`` or ``career_services``.
            fallback: Default contact used when the table is empty.

        Returns:
            Contact fields the frontend can render.
        """
        rows = self._directory.get_contacts_by_type(contact_type)
        if not rows:
            return dict(fallback)
        row = rows[0]
        return {
            'resourceName': row.get('name') or fallback['resourceName'],
            'url': row.get('booking_url') or fallback['url'],
            'name': row.get('name'),
            'email': row.get('email'),
        }
