"""PostgreSQL implementation of ICampusDirectoryRepository."""

from __future__ import annotations

from app.repositories.connection import Database
from app.repositories.interfaces import ICampusDirectoryRepository
from app.repositories.row_utils import serialize_row


class PostgresDirectoryRepository(ICampusDirectoryRepository):
    """Reads advisor and career-services contacts.

    Args:
        database: Shared PostgreSQL connection helper.
    """

    def __init__(self, database: Database):
        self._database = database

    def get_advisor_contacts(self) -> list[dict]:
        """Gets advisor contacts.

        Returns:
            Advisor names and emails.
        """
        return self.get_contacts_by_type('advisor')

    def get_contacts_by_type(self, contact_type: str) -> list[dict]:
        """Gets contacts of one type.

        Args:
            contact_type: ``advisor`` or ``career_services``.

        Returns:
            Matching contact rows.
        """
        sql = """
            SELECT advisor_id, name, email, contact_type, booking_url
            FROM advisor_contacts
            WHERE contact_type = %s
            ORDER BY name
        """
        with self._database.connect() as connection:
            rows = connection.execute(sql, (contact_type,)).fetchall()
        return [serialize_row(row) for row in rows]
