"""Tests for Clerk session JWT → student_id resolution."""

from __future__ import annotations

import base64
import time
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.api.errors import ApiError
from app.auth.clerk_auth import frontend_api_from_publishable_key
from app.auth.clerk_auth import resolve_student_id
from app.auth.clerk_auth import verify_clerk_token
from app.config import Settings
from app.main import create_app


def _settings(**overrides) -> Settings:
    base = dict(
        app_name='coursecompass-api-test',
        environment='test',
        database_url='',
        clerk_secret_key='',
        clerk_publishable_key='',
        clerk_jwks_url='',
        clerk_jwt_key='',
        clerk_issuer='https://modern-monarch-6759.clerk.accounts.dev',
        clerk_authorized_parties=('http://localhost:5173',),
        llm_provider='',
        llm_api_key='',
        llm_model='gemini-2.5-flash',
        embedding_model='gemini-embedding-001',
        embedding_dimensions=768,
        gcp_project='',
        gcp_location='us-central1',
        cors_origins=('http://localhost:5173',),
    )
    base.update(overrides)
    return Settings(**base)


def _rsa_pem_pair() -> tuple[str, object]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode('utf-8')
    return public_pem, key


def test_frontend_api_from_publishable_key():
    host = 'modern-monarch-6759.clerk.accounts.dev'
    encoded = base64.urlsafe_b64encode(f'{host}$'.encode()).decode().rstrip('=')
    pk = f'pk_test_{encoded}'
    assert frontend_api_from_publishable_key(pk) == f'https://{host}'


def test_verify_clerk_token_with_pem_returns_sub():
    public_pem, private_key = _rsa_pem_pair()
    settings = _settings(clerk_jwt_key=public_pem)
    now = int(time.time())
    token = jwt.encode(
        {
            'sub': 'user_abc123',
            'iss': settings.clerk_issuer,
            'azp': 'http://localhost:5173',
            'iat': now,
            'exp': now + 60,
            'nbf': now,
        },
        private_key,
        algorithm='RS256',
    )
    assert verify_clerk_token(token, settings) == 'user_abc123'


def test_verify_clerk_token_rejects_bad_azp():
    public_pem, private_key = _rsa_pem_pair()
    settings = _settings(clerk_jwt_key=public_pem)
    now = int(time.time())
    token = jwt.encode(
        {
            'sub': 'user_abc123',
            'iss': settings.clerk_issuer,
            'azp': 'https://evil.example',
            'iat': now,
            'exp': now + 60,
            'nbf': now,
        },
        private_key,
        algorithm='RS256',
    )
    with pytest.raises(ApiError) as exc:
        verify_clerk_token(token, settings)
    assert exc.value.status == 401


def test_resolve_prefers_bearer_over_dev_header():
    public_pem, private_key = _rsa_pem_pair()
    settings = _settings(clerk_jwt_key=public_pem)
    now = int(time.time())
    token = jwt.encode(
        {
            'sub': 'user_from_jwt',
            'iss': settings.clerk_issuer,
            'azp': 'http://localhost:5173',
            'iat': now,
            'exp': now + 60,
            'nbf': now,
        },
        private_key,
        algorithm='RS256',
    )
    headers = {
        'Authorization': f'Bearer {token}',
        'X-Dev-Student-Id': 'test_clerk_user_1',
    }
    assert resolve_student_id(headers, settings) == 'user_from_jwt'


def test_resolve_dev_header_when_no_bearer():
    settings = _settings()
    headers = {'X-Dev-Student-Id': 'test_clerk_user_1'}
    assert resolve_student_id(headers, settings) == 'test_clerk_user_1'


def test_resolve_ignores_dev_placeholder_token():
    settings = _settings(environment='local')
    headers = {'Authorization': 'Bearer dev-token'}
    assert resolve_student_id(headers, settings) == ''


def test_resolve_anonymous_when_no_identity():
    settings = _settings()
    assert resolve_student_id({}, settings) == ''


def test_post_query_uses_dev_student_header():
    app = create_app(_settings(environment='test'))
    provider = type('P', (), {})()
    provider.choose_tool = lambda q, tools: {
        'tool': 'audit_degree',
        'arguments': {},
        'redirect': False,
    }
    provider.phrase_response = lambda facts: 'ok'

    captured = {}

    def _fake_answer(provider, query, embedding_provider=None,
                     tool_dispatcher=None, student_id='', history=None):
        del history
        captured['student_id'] = student_id
        from app.schemas.query import QueryResponse
        return QueryResponse(
            id='1',
            type='audit',
            content={'message': 'ok', 'creditsRemaining': 0},
            timestamp='2026-01-01T00:00:00Z',
        )

    app.state.llm_provider = provider
    with patch('app.api.v1.query.answer_query', side_effect=_fake_answer):
        client = TestClient(app)
        response = client.post(
            '/api/v1/query',
            json={'query': 'How many credits left?'},
            headers={'X-Dev-Student-Id': 'test_clerk_user_2'},
        )
    assert response.status_code == 200
    assert captured['student_id'] == 'test_clerk_user_2'
