"""Schedule builder: build a draft, list schedules, mark one exported."""

from fastapi import APIRouter
from fastapi import Body
from fastapi import Request

from app.api.errors import BAD_REQUEST
from app.api.errors import NOT_FOUND
from app.api.errors import NOT_IMPLEMENTED
from app.api.errors import UNAUTHORIZED
from app.api.errors import ApiError
from app.auth.clerk_auth import resolve_student_id

router = APIRouter(prefix='/api/v1/schedule')

MAX_COURSES_PER_TERM = 6


def _clerk_user_id(request: Request) -> str:
    """Returns the signed-in student's id, or raises 401."""
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


def _state(request: Request, name: str):
    """Returns an object from app.state, or raises 501 when it is not configured."""
    value = getattr(request.app.state, name, None)
    if value is None:
        status, code = NOT_IMPLEMENTED
        raise ApiError(
            status, code, 'DATABASE_URL is not configured; schedules are unavailable.'
        )
    return value


@router.post('/build')
def build_schedule(request: Request, body: dict | None = Body(default=None)) -> dict:
    """Plans the student's remaining courses and saves the result as their draft.

    Identity comes from a Clerk Bearer token, or ``X-Dev-Student-Id`` in
    local/staging/test. No LLM is used: the plan follows prerequisites and the
    terms each course is offered. The previous draft is replaced only if at
    least one course could be placed. Exported schedules are kept.

    Args:
        request: FastAPI request (settings, schedule service, headers).
        body: Optional JSON ``{"courses_per_term": 1-6}``. Default is 2.

    Returns:
        ``schedule`` (terms with items, or null when nothing could be placed)
        and ``unplaced`` courses with the reason each was left out.

    Raises:
        ApiError: 400 bad ``courses_per_term``; 401 missing identity; 404
            unknown student; 501 if DATABASE_URL is not configured.
    """
    clerk_user_id = _clerk_user_id(request)

    kwargs = {}
    if body and 'courses_per_term' in body:
        value = body['courses_per_term']
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value <= MAX_COURSES_PER_TERM
        ):
            status, code = BAD_REQUEST
            raise ApiError(
                status,
                code,
                f'courses_per_term must be a whole number from 1 to {MAX_COURSES_PER_TERM}.',
            )
        kwargs['max_per_term'] = value

    service = _state(request, 'schedule_service')
    result = service.build_draft(clerk_user_id, **kwargs)
    if result is None:
        status, code = NOT_FOUND
        raise ApiError(status, code, 'Student not found.')

    response = {
        'status': 'success',
        'schedule': result['schedule'],
        'unplaced': result['unplaced'],
    }
    if result['schedule'] is None:
        response['message'] = (
            'No courses could be placed, so your current draft was not changed.'
        )
    return response


@router.get('')
def list_schedules(request: Request) -> list[dict]:
    """Lists the signed-in student's schedules, oldest first.

    Each schedule has ``schedule_id``, ``student_id``, ``status`` (``draft`` or
    ``exported``), ``created_at`` and ``terms``; each term has ``items``.

    Raises:
        ApiError: 401 missing identity; 501 if DATABASE_URL is not configured.
    """
    clerk_user_id = _clerk_user_id(request)
    repository = _state(request, 'schedule_repository')
    return repository.get_schedules(clerk_user_id)


@router.post('/{schedule_id}/export')
def export_schedule(schedule_id: str, request: Request) -> dict:
    """Marks one of the signed-in student's schedules as exported.

    Raises:
        ApiError: 401 missing identity; 404 if the schedule does not exist or
            belongs to another student; 501 if DATABASE_URL is not configured.
    """
    clerk_user_id = _clerk_user_id(request)
    repository = _state(request, 'schedule_repository')
    if not repository.mark_exported(clerk_user_id, schedule_id):
        status, code = NOT_FOUND
        raise ApiError(status, code, 'Schedule not found.')
    return {'status': 'success', 'schedule_id': schedule_id, 'exported': True}
