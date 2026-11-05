"""Student transcript upload: parse a PDF and overwrite that student's rows."""

from fastapi import APIRouter
from fastapi import Request
from fastapi import UploadFile
from pydantic import BaseModel

from app.api.errors import BAD_REQUEST
from app.api.errors import NOT_IMPLEMENTED
from app.api.errors import UNAUTHORIZED
from app.api.errors import ApiError
from app.auth.clerk_auth import resolve_student_id
from app.ingestion.transcript_parser import process_pdf_bytes
from app.services.substitution_service import SubstitutionService

router = APIRouter(prefix='/api/v1/transcript')
# Unofficial transcripts are a few pages. Cap before pdfplumber runs.
_MAX_PDF_BYTES = 10 * 1024 * 1024


@router.post('/upload')
def upload_transcript(file: UploadFile, request: Request) -> dict:
    """Parses a transcript PDF and replaces that student's catalog rows.

    Identity comes from a Clerk Bearer token, or ``X-Dev-Student-Id`` in
    local/staging/test. Does not call an LLM. Courses not in ``courses``
    are skipped. An empty parse does not delete the existing transcript.

    Args:
        file: PDF uploaded as ``multipart/form-data`` field ``file``.
        request: FastAPI request (settings, transcript store, headers).

    Returns:
        Parsed courses plus ``saved`` / ``skipped`` persistence results.

    Raises:
        ApiError: 400 invalid PDF; 401 missing identity; 404 unknown
            student; 501 if DATABASE_URL is not configured.
    """
    filename = (file.filename or '').lower()
    if not filename.endswith('.pdf'):
        status, code = BAD_REQUEST
        raise ApiError(status, code, 'Only PDF transcripts are supported.')

    pdf_bytes = file.file.read()
    if not pdf_bytes:
        status, code = BAD_REQUEST
        raise ApiError(status, code, 'The uploaded PDF was empty.')
    if len(pdf_bytes) > _MAX_PDF_BYTES:
        status, code = BAD_REQUEST
        raise ApiError(
            status,
            code,
            'Transcript PDFs must be 10 MB or smaller.',
        )

    settings = getattr(request.app.state, 'settings', None)
    clerk_user_id = ''
    if settings is not None:
        clerk_user_id = resolve_student_id(request.headers, settings)
    if not clerk_user_id:
        status, code = UNAUTHORIZED
        raise ApiError(
            status,
            code,
            'Sign in, or pass X-Dev-Student-Id in local/staging/test.',
        )

    try:
        parsed = process_pdf_bytes(pdf_bytes)
    except Exception as exc:
        status, code = BAD_REQUEST
        raise ApiError(
            status,
            code,
            'Failed to parse transcript PDF.',
            {'reason': type(exc).__name__},
        ) from exc

    if not parsed.get('courses'):
        status, code = BAD_REQUEST
        raise ApiError(
            status,
            code,
            'No course rows were parsed; existing transcript was not changed.',
        )

    store = getattr(request.app.state, 'transcript_store', None)
    if store is None:
        status, code = NOT_IMPLEMENTED
        raise ApiError(
            status,
            code,
            'DATABASE_URL is not configured; transcript was not saved.',
        )

    persisted = store.replace_for_clerk_user(clerk_user_id, parsed['courses'])
    return {
        'status': 'success',
        'course_count': parsed['course_count'],
        'courses': parsed['courses'],
        'term_summaries': parsed['term_summaries'],
        'cumulative_summary': parsed['cumulative_summary'],
        'student_id': persisted['student_id'],
        'clerk_user_id': persisted['clerk_user_id'],
        'email': persisted.get('email'),
        'saved': persisted['saved'],
        'skipped': persisted['skipped'],
        'clearedSubstitutions': persisted['cleared'],
    }


class SubstitutionIn(BaseModel):
    """A declared substitute: the student took ``substituteCode`` instead.

    Attributes:
        requirementCode: Required course the student is excused from.
        substituteCode: Course the student took in its place.
    """

    requirementCode: str
    substituteCode: str


def _student_clerk_id(request: Request) -> str:
    settings = getattr(request.app.state, 'settings', None)
    clerk_user_id = ''
    if settings is not None:
        clerk_user_id = resolve_student_id(request.headers, settings)
    if not clerk_user_id:
        status, code = UNAUTHORIZED
        raise ApiError(
            status,
            code,
            'Sign in, or pass X-Dev-Student-Id in local/staging/test.',
        )
    return clerk_user_id


def _substitution_service(request: Request) -> SubstitutionService:
    service = getattr(request.app.state, 'substitution_service', None)
    if service is None:
        status, code = NOT_IMPLEMENTED
        raise ApiError(
            status,
            code,
            'DATABASE_URL is not configured; substitutions are unavailable.',
        )
    return service


@router.get('/review')
def review_transcript(request: Request) -> dict:
    """Returns the matcher data: open requirements, pool, and declarations.

    Args:
        request: FastAPI request (identity headers, app state).

    Returns:
        ``requirements``, ``courses``, and ``substitutions``.
    """
    clerk_user_id = _student_clerk_id(request)
    return _substitution_service(request).review(clerk_user_id)


@router.post('/substitutions')
def declare_substitution(body: SubstitutionIn, request: Request) -> dict:
    """Declares or replaces the substitute for one required course.

    Args:
        body: Requirement and substitute course codes.
        request: FastAPI request (identity headers, app state).

    Returns:
        The updated ``requirements``, ``courses``, and ``substitutions``.
    """
    clerk_user_id = _student_clerk_id(request)
    return _substitution_service(request).declare(
        clerk_user_id,
        body.requirementCode,
        body.substituteCode,
    )


@router.delete('/substitutions/{substitution_id}')
def remove_substitution(substitution_id: str, request: Request) -> dict:
    """Removes one of the student's declared substitutions.

    Args:
        substitution_id: The declaration to delete.
        request: FastAPI request (identity headers, app state).

    Returns:
        The updated ``requirements``, ``courses``, and ``substitutions``.
    """
    clerk_user_id = _student_clerk_id(request)
    return _substitution_service(request).remove(
        clerk_user_id,
        substitution_id,
    )
