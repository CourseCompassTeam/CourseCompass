"""Admin data ingestion endpoints: /api/v1/admin/ingest/...

These are rate limited to 10 requests per minute per API key.
"""

from fastapi import APIRouter
from fastapi import UploadFile

from app.schemas.ingest import IngestJobStatus

router = APIRouter(prefix='/api/v1/admin/ingest')


@router.post('/course', status_code=202)
def ingest_courses(file: UploadFile) -> IngestJobStatus:
    """Loads course, prerequisite, and requirement records.

    Args:
        file: A CSV or JSON upload.

    Returns:
        The created ingestion job (202 Accepted).
    """
    raise NotImplementedError


@router.post('/transcripts', status_code=202)
def ingest_transcripts(file: UploadFile) -> IngestJobStatus:
    """Loads student transcripts into transcript_entries.

    Args:
        file: The transcript upload.

    Returns:
        The created ingestion job (202 Accepted).
    """
    raise NotImplementedError


@router.get('/status/{job_id}')
def get_ingest_status(job_id: str) -> IngestJobStatus:
    """Reports the status of an ingestion job.

    Args:
        job_id: The job to look up.

    Returns:
        The job's current status.

    Raises:
        ApiError: 404 if the job does not exist.
    """
    raise NotImplementedError
