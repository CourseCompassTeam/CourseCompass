"""Request and response models for POST /api/v1/query."""

from typing import Any, Literal

from pydantic import BaseModel


class QueryRequest(BaseModel):
    """A student's question.

    Attributes:
        query: The student's natural-language question.
    """

    query: str


class QueryResponse(BaseModel):
    """The answer to a student's question.

    Attributes:
        id: Unique message ID.
        type: Which kind of answer this is.
        content: Shape varies by type (see AuditContent for 'audit').
        timestamp: ISO 8601 timestamp.
    """

    id: str
    type: Literal['audit', 'recommendation', 'redirect']
    content: dict[str, Any]
    timestamp: str


class AuditContent(BaseModel):
    """Content of an 'audit' response (US-01).

    The API spec uses camelCase in JSON (creditsRemaining, requirementsMet,
    missingCourses). How these fields map to it is still to be decided.

    Attributes:
        credits_remaining: Credits the student still needs.
        requirements_met: Whether every degree requirement is met.
        missing_courses: Codes of the courses still required.
    """

    credits_remaining: int
    requirements_met: bool
    missing_courses: list[str]
