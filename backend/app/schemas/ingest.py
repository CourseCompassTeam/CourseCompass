"""Models for the admin ingestion endpoints."""

from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator


class TranscriptEntryIn(BaseModel):
    """One course row from an uploaded student transcript.

    Attributes:
        code: Catalog course code, e.g. ``MSSE 601``.
        term: Term label as written on the transcript.
        status: Whether the course is done, in progress, or planned.
    """

    code: str
    term: str
    status: Literal['completed', 'in_progress', 'planned']

    @field_validator('code', 'term')
    @classmethod
    def _strip_required(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError('must not be empty')
        return stripped


class TranscriptUpload(BaseModel):
    """JSON body of a transcript file posted to the ingest API.

    Persistence into ``transcript_entries`` is not wired yet. This model
    only checks that the backend can receive a transcript payload.

    Attributes:
        clerk_user_id: Optional Clerk subject for the student.
        email: Optional student email on the transcript.
        entries: Course rows to load.
    """

    clerk_user_id: str | None = None
    email: str | None = None
    entries: list[TranscriptEntryIn] = Field(min_length=1)


class IngestJobStatus(BaseModel):
    """Status of an ingestion job.

    Attributes:
        job_id: The job's ID.
        status: Current state of the job.
        records_processed: Number of records loaded so far.
        error_message: Why the job failed, if it did.
    """

    job_id: str
    status: Literal['running', 'succeeded', 'failed']
    records_processed: int
    error_message: str | None = None
