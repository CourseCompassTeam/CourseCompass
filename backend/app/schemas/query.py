"""Request and response models for POST /api/v1/query."""

from typing import Any, Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

_MAX_HISTORY_TURNS = 6
_MAX_HISTORY_TEXT = 1000


class HistoryTurn(BaseModel):
    """One earlier chat turn sent with a follow-up question.

    Attributes:
        role: ``student`` or ``assistant``.
        text: The turn text. The current question is not included.
    """

    role: Literal['student', 'assistant']
    text: str

    @field_validator('text')
    @classmethod
    def _clip_text(cls, value: str) -> str:
        return value.strip()[:_MAX_HISTORY_TEXT]


class QueryRequest(BaseModel):
    """A student's question.

    Attributes:
        query: The student's natural-language question.
        history: Up to three earlier exchanges, oldest first.
        questionNumber: How many student questions this one is, counting
            from 1 for the whole chat. Used to offer milestones on the
            3rd and 4th question of every four.
    """

    query: str
    history: list[HistoryTurn] = Field(default_factory=list)
    questionNumber: int = 0

    @field_validator('history')
    @classmethod
    def _limit_history(cls, value: list[HistoryTurn]) -> list[HistoryTurn]:
        kept = [turn for turn in value if turn.text]
        return kept[-_MAX_HISTORY_TURNS:]

    @field_validator('questionNumber')
    @classmethod
    def _non_negative(cls, value: int) -> int:
        return max(0, value)


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
