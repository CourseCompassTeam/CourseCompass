"""Models for the admin ingestion endpoints."""

from typing import Literal

from pydantic import BaseModel


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
