"""PostgreSQL connection helper."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row


class Database:
    """Opens short-lived connections from a DATABASE_URL.

    Args:
        database_url: PostgreSQL connection string.
    """

    def __init__(self, database_url: str):
        if not database_url:
            raise ValueError('DATABASE_URL is required.')
        self._url = database_url

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection]:
        """Yields a dict-row connection and closes it afterward.

        Yields:
            An open psycopg connection.
        """
        connection = psycopg.connect(self._url, row_factory=dict_row)
        try:
            yield connection
        finally:
            connection.close()
