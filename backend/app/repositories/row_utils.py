"""Helpers for turning PostgreSQL rows into JSON-safe dicts."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from uuid import UUID


def serialize_value(value):
    """Converts UUID, datetime, and nested values for JSON.

    Args:
        value: A database cell value.

    Returns:
        A JSON-serializable value.
    """
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [serialize_value(item) for item in value]
    if isinstance(value, dict):
        return serialize_row(value)
    return value


def serialize_row(row: dict | None) -> dict | None:
    """Copies a mapping and serializes UUID/date values.

    Args:
        row: A psycopg dict row, or None.

    Returns:
        A JSON-safe dict, or None.
    """
    if row is None:
        return None
    return {key: serialize_value(value) for key, value in row.items()}


def normalize_code(value: str) -> str:
    """Normalizes a course code for comparison.

    Args:
        value: A course code or id.

    Returns:
        Uppercase code with spaces removed.
    """
    return str(value or '').replace(' ', '').upper()
