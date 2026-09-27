"""PostgreSQL implementation of IStudentMilestoneRepository."""

from __future__ import annotations

from app.repositories.connection import Database
from app.repositories.interfaces import IStudentMilestoneRepository
from app.repositories.row_utils import serialize_row


class PostgresMilestoneRepository(IStudentMilestoneRepository):
    """Reads milestone suggestions.

    Args:
        database: Shared PostgreSQL connection helper.
    """

    def __init__(self, database: Database):
        self._database = database

    def get_milestones(self) -> list[dict]:
        """Gets all milestones.

        Returns:
            Milestone records.
        """
        sql = """
            SELECT milestone_id, credit_min, credit_max, label,
                   next_actions
            FROM milestones
            ORDER BY credit_min, label
        """
        with self._database.connect() as connection:
            rows = connection.execute(sql).fetchall()
        return [serialize_row(row) for row in rows]
