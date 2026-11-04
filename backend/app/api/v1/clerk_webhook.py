"""Clerk webhook: creates a students row when a Clerk user is created."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter
from fastapi import Request
from svix.webhooks import Webhook
from svix.webhooks import WebhookVerificationError

from app.api.errors import NOT_IMPLEMENTED
from app.api.errors import UNAUTHORIZED
from app.api.errors import ApiError

router = APIRouter(prefix='/api/v1/webhooks')
_LOG = logging.getLogger(__name__)
_USER_CREATED = 'user.created'


@router.post('/clerk')
async def clerk_webhook(request: Request) -> dict:
    """Verifies a Clerk webhook and provisions a student for new users.

    Clerk signs each delivery with Svix. Other event types are ignored.
    A non-2xx response makes Clerk retry, so a missing default program
    or database returns an error rather than dropping the event.

    Args:
        request: FastAPI request with the raw body and Svix headers.

    Returns:
        ``created``, ``exists``, ``skipped``, or ``ignored`` status.

    Raises:
        ApiError: 401 bad signature; 501 when no database or student
            service is attached; 503 when the webhook secret is unset;
            422 when the default program is missing.
    """
    settings = request.app.state.settings
    service = getattr(request.app.state, 'student_provisioning_service', None)
    if not settings.clerk_webhook_secret:
        raise ApiError(
            503,
            'SERVICE_UNAVAILABLE',
            'CLERK_WEBHOOK_SECRET is not configured.',
        )
    if service is None:
        status, code = NOT_IMPLEMENTED
        raise ApiError(status, code, 'Student provisioning is not attached.')

    body = await request.body()
    try:
        Webhook(settings.clerk_webhook_secret).verify(
            body,
            dict(request.headers),
        )
    except WebhookVerificationError as exc:
        status, code = UNAUTHORIZED
        raise ApiError(status, code, 'Invalid webhook signature.') from exc
    event = json.loads(body)

    if event.get('type') != _USER_CREATED:
        return {'status': 'ignored'}

    data = event.get('data') or {}
    clerk_user_id = str(data.get('id') or '').strip()
    email = _primary_email(data)
    if not clerk_user_id or not email:
        _LOG.warning('Skipping user.created without id or email.')
        return {'status': 'skipped'}

    full_name = ' '.join(
        part for part in (data.get('first_name'), data.get('last_name'))
        if part
    ).strip()
    created = service.provision(clerk_user_id, email, full_name)
    return {'status': 'created' if created else 'exists'}


def _primary_email(data: dict[str, Any]) -> str:
    """Returns the primary email address from a Clerk user payload.

    Args:
        data: The ``data`` object of a ``user.created`` event.

    Returns:
        The primary email, or an empty string if none is present.
    """
    primary_id = data.get('primary_email_address_id')
    for entry in data.get('email_addresses') or []:
        if entry.get('id') == primary_id:
            return str(entry.get('email_address') or '').strip()
    return ''
