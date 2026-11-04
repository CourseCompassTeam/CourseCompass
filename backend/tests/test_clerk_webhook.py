"""Clerk user.created webhook: signature checks and provisioning calls."""

import base64
import json
from datetime import datetime
from datetime import timezone

from fastapi.testclient import TestClient
from svix.webhooks import Webhook

from app.config import Settings
from app.main import create_app

SECRET = 'whsec_' + base64.b64encode(b'test-signing-key-0123456789').decode()

USER_CREATED = {
    'type': 'user.created',
    'data': {
        'id': 'user_new_1',
        'first_name': 'Ada',
        'last_name': 'Lovelace',
        'primary_email_address_id': 'idn_2',
        'email_addresses': [
            {'id': 'idn_1', 'email_address': 'old@example.edu'},
            {'id': 'idn_2', 'email_address': 'ada@example.edu'},
        ],
    },
}


class _FakeService:
    def __init__(self, created=True):
        self.calls = []
        self._created = created

    def provision(self, clerk_user_id, email, full_name):
        self.calls.append((clerk_user_id, email, full_name))
        return self._created


def _settings(secret=SECRET) -> Settings:
    return Settings(
        app_name='coursecompass-api-test',
        environment='test',
        database_url='',
        clerk_secret_key='',
        clerk_publishable_key='',
        clerk_jwks_url='',
        clerk_jwt_key='',
        clerk_issuer='',
        clerk_authorized_parties=(),
        llm_provider='',
        llm_api_key='',
        llm_model='gemini-2.5-flash',
        embedding_model='gemini-embedding-001',
        embedding_dimensions=768,
        gcp_project='',
        gcp_location='us-central1',
        cors_origins=('http://localhost:5173',),
        clerk_webhook_secret=secret,
    )


def _post(client, payload, secret=SECRET, msg_id='msg_1'):
    body = json.dumps(payload)
    timestamp = datetime.now(timezone.utc)
    signature = Webhook(secret).sign(msg_id, timestamp, body)
    return client.post(
        '/api/v1/webhooks/clerk',
        content=body,
        headers={
            'svix-id': msg_id,
            'svix-timestamp': str(int(timestamp.timestamp())),
            'svix-signature': signature,
            'content-type': 'application/json',
        },
    )


def _client(service=None, settings=None):
    app = create_app(settings or _settings())
    app.state.student_provisioning_service = service
    return TestClient(app)


def test_user_created_provisions_primary_email_and_full_name():
    service = _FakeService()
    response = _post(_client(service), USER_CREATED)

    assert response.status_code == 200
    assert response.json() == {'status': 'created'}
    assert service.calls == [('user_new_1', 'ada@example.edu', 'Ada Lovelace')]


def test_existing_student_reports_exists():
    service = _FakeService(created=False)
    response = _post(_client(service), USER_CREATED)

    assert response.json() == {'status': 'exists'}


def test_other_event_types_are_ignored():
    service = _FakeService()
    response = _post(_client(service), {'type': 'user.updated', 'data': {}})

    assert response.json() == {'status': 'ignored'}
    assert service.calls == []


def test_user_without_primary_email_is_skipped():
    service = _FakeService()
    payload = {
        'type': 'user.created',
        'data': {'id': 'user_phone_only', 'email_addresses': []},
    }
    response = _post(_client(service), payload)

    assert response.json() == {'status': 'skipped'}
    assert service.calls == []


def test_bad_signature_is_rejected_without_provisioning():
    service = _FakeService()
    other_secret = 'whsec_' + base64.b64encode(b'another-key-0123456789abcdef').decode()
    response = _post(_client(service), USER_CREATED, secret=other_secret)

    assert response.status_code == 401
    assert response.json()['error']['code'] == 'UNAUTHORIZED'
    assert service.calls == []


def test_missing_webhook_secret_returns_503():
    response = _post(
        _client(_FakeService(), _settings(secret='')),
        USER_CREATED,
    )

    assert response.status_code == 503


def test_missing_student_service_returns_501():
    response = _post(_client(service=None), USER_CREATED)

    assert response.status_code == 501
