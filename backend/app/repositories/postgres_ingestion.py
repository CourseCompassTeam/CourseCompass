"""PostgreSQL implementation of IIngestionLogRepository."""

from __future__ import annotations

from app.repositories.connection import Database
from app.repositories.interfaces import IIngestionLogRepository
from app.repositories.row_utils import serialize_row


class PostgresIngestionRepository(IIngestionLogRepository):
    """Reads admin ingestion log rows.

    Args:
        database: Shared PostgreSQL connection helper.
    """

    def __init__(self, database: Database):
        self._database = database

    def list_logs(self, limit: int = 20) -> list[dict]:
        """Gets recent ingestion jobs.

        Args:
            limit: Maximum rows to return.

        Returns:
            Ingestion log rows.
        """
        sql = """
            SELECT log_id, source, started_at, completed_at, status,
                   records_processed, error_message
            FROM data_ingestion_logs
            ORDER BY started_at DESC
            LIMIT %s
        """
        with self._database.connect() as connection:
            rows = connection.execute(sql, (limit,)).fetchall()
        return [serialize_row(row) for row in rows]
