"""Clerk session JWT verification and student identity resolution.

The LLM never receives student_id. The server extracts it from a verified
Clerk Bearer token (QA-03). In local/staging/test, ``X-Dev-Student-Id`` can
override for seed personas such as ``test_clerk_user_1``.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

import jwt
from jwt import PyJWKClient

from app.api.errors import UNAUTHORIZED
from app.api.errors import ApiError
from app.config import Settings

_LOG = logging.getLogger(__name__)
_JWKS_CLIENTS: dict[str, PyJWKClient] = {}


def resolve_student_id(request_headers: Any, settings: Settings) -> str:
    """Resolves the student identity for a query request.

    Order:
      1. Valid ``Authorization: Bearer`` Clerk JWT → ``sub`` claim
      2. Non-prod ``X-Dev-Student-Id`` header (seed clerks)
      3. Empty string (anonymous / program-level tools)

    Args:
        request_headers: Mapping-like header object (FastAPI Request.headers).
        settings: Application settings.

    Returns:
        Clerk user id, seed clerk id, or empty string.

    Raises:
        ApiError: 401 if a Bearer token is present but invalid.
    """
    bearer = _bearer_token(request_headers)
    env = (settings.environment or '').lower()
    # Local chat sends a placeholder Bearer token when Clerk is off.
    # Only real JWTs (three segments) are verified.
    if bearer and _looks_like_jwt(bearer):
        return verify_clerk_token(bearer, settings)
    if bearer and env not in ('local', 'staging', 'test'):
        return verify_clerk_token(bearer, settings)

    if env in ('local', 'staging', 'test'):
        dev_id = (
            request_headers.get('X-Dev-Student-Id')
            or request_headers.get('x-dev-student-id')
            or ''
        ).strip()
        if dev_id:
            return dev_id
    return ''


def verify_clerk_token(token: str, settings: Settings) -> str:
    """Verifies a Clerk session JWT and returns the ``sub`` claim.

    Prefers networkless verification when ``CLERK_JWT_KEY`` (PEM) is set.
    Otherwise fetches JWKS from the Frontend API URL.

    Args:
        token: Raw JWT (no ``Bearer`` prefix).
        settings: Application settings with Clerk config.

    Returns:
        The Clerk user id (``sub``).

    Raises:
        ApiError: 401 if verification fails or Clerk is not configured.
    """
    if not settings.clerk_jwt_key and not settings.clerk_jwks_url:
        status, code = UNAUTHORIZED
        raise ApiError(
            status,
            code,
            'Clerk JWT verification is not configured. Set '
            'CLERK_JWKS_URL or CLERK_JWT_KEY (and optionally '
            'CLERK_PUBLISHABLE_KEY).',
        )

    try:
        if settings.clerk_jwt_key:
            payload = jwt.decode(
                token,
                settings.clerk_jwt_key,
                algorithms=['RS256'],
                options={
                    'verify_aud': False,
                    'verify_iss': bool(settings.clerk_issuer),
                },
                issuer=settings.clerk_issuer or None,
                leeway=10,
            )
        else:
            client = _jwks_client(settings.clerk_jwks_url)
            signing_key = client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=['RS256'],
                options={
                    'verify_aud': False,
                    'verify_iss': bool(settings.clerk_issuer),
                },
                issuer=settings.clerk_issuer or None,
                leeway=10,
            )
    except jwt.PyJWTError as exc:
        _LOG.warning('Clerk token verification failed: %s', exc)
        status, code = UNAUTHORIZED
        raise ApiError(
            status,
            code,
            'Invalid or expired session token.',
            {'reason': type(exc).__name__},
        ) from exc

    if settings.clerk_authorized_parties:
        azp = payload.get('azp')
        if azp not in settings.clerk_authorized_parties:
            status, code = UNAUTHORIZED
            raise ApiError(
                status,
                code,
                'Session token authorized party is not allowed.',
                {'azp': azp},
            )

    subject = str(payload.get('sub') or '').strip()
    if not subject:
        status, code = UNAUTHORIZED
        raise ApiError(status, code, 'Session token is missing sub claim.')
    return subject


def frontend_api_from_publishable_key(publishable_key: str) -> str:
    """Derives the Clerk Frontend API host from a publishable key.

    Args:
        publishable_key: ``pk_test_...`` or ``pk_live_...``.

    Returns:
        Frontend API base URL such as
        ``https://modern-monarch-6759.clerk.accounts.dev``.
    """
    parts = publishable_key.split('_', 2)
    if len(parts) < 3:
        raise ValueError('CLERK_PUBLISHABLE_KEY format is invalid.')
    raw = parts[2]
    raw += '=' * (-len(raw) % 4)
    decoded = base64.urlsafe_b64decode(raw).decode('utf-8')
    host = decoded.rstrip('$').strip()
    if not host:
        raise ValueError('CLERK_PUBLISHABLE_KEY did not contain a host.')
    if host.startswith('http://') or host.startswith('https://'):
        return host.rstrip('/')
    return f'https://{host}'


def _looks_like_jwt(token: str) -> bool:
    """Returns whether a token has the three-part JWT shape.

    Args:
        token: Raw Authorization token.

    Returns:
        True when the token contains two dots.
    """
    return token.count('.') == 2


def _bearer_token(headers: Any) -> str:
    """Extracts a Bearer token from Authorization header.

    Args:
        headers: Request headers.

    Returns:
        The JWT string, or empty if absent.
    """
    auth = headers.get('Authorization') or headers.get('authorization') or ''
    if not auth:
        return ''
    scheme, _, token = auth.partition(' ')
    if scheme.lower() != 'bearer' or not token.strip():
        return ''
    return token.strip()


def _jwks_client(jwks_url: str) -> PyJWKClient:
    """Returns a cached PyJWKClient for a JWKS URL.

    Args:
        jwks_url: Full JWKS URL.

    Returns:
        Cached client instance.
    """
    client = _JWKS_CLIENTS.get(jwks_url)
    if client is None:
        client = PyJWKClient(jwks_url, cache_keys=True)
        _JWKS_CLIENTS[jwks_url] = client
    return client
