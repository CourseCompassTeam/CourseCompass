"""Admin data ingestion endpoints: /api/v1/admin/ingest/...

These are rate limited to 10 requests per minute per API key.
"""

import json
import uuid

from fastapi import APIRouter
from fastapi import UploadFile
from pydantic import ValidationError

from app.api.errors import BAD_REQUEST
from app.api.errors import ApiError
from app.schemas.ingest import IngestJobStatus
from app.schemas.ingest import TranscriptUpload

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
    """Accepts a JSON transcript upload and reports how many rows parsed.

    Does not write ``transcript_entries`` yet. That persistence is the
    next step after this receive-and-validate spike.

    Args:
        file: JSON transcript (``entries`` of code, term, status).

    Returns:
        A succeeded job whose ``records_processed`` is the parsed row count.

    Raises:
        ApiError: 400 if the file is not valid transcript JSON.
    """
    try:
        payload = TranscriptUpload.model_validate(
            json.loads(file.file.read())
        )
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as exc:
        status, code = BAD_REQUEST
        raise ApiError(
            status,
            code,
            'Transcript file must be JSON with at least one entry '
            'of code, term, and status.',
            {'reason': type(exc).__name__},
        ) from exc
    return IngestJobStatus(
        job_id=str(uuid.uuid4()),
        status='succeeded',
        records_processed=len(payload.entries),
    )


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
