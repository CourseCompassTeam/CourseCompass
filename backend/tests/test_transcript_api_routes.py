"""Transcript upload and substitution routes: error paths and happy paths.

The PDF parser and the stores are replaced with fakes, so these tests cover
the HTTP layer and its error handling, not pdfplumber or SQL.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.v1 import transcript as transcript_api
from app.config import Settings
from app.main import create_app

DEV_STUDENT = 'user_3K1pC0YksFOD8HW1dIiz4ITDt90'
PDF = ('transcript.pdf', b'%PDF-fake', 'application/pdf')

PARSED = {
    'course_count': 1,
    'courses': [{'code': 'MSSE 610', 'grade': 'A', 'dates': '10/20/25-12/14/25'}],
    'term_summaries': [],
    'cumulative_summary': {},
}


def _settings() -> Settings:
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
    )


class FakeStore:
    def __init__(self, raises=None):
        self.raises = raises
        self.calls = []

    def replace_for_clerk_user(self, clerk_user_id, courses):
        self.calls.append((clerk_user_id, courses))
        if self.raises:
            raise self.raises
        return {
            'student_id': 's-1',
            'clerk_user_id': clerk_user_id,
            'email': 'a@example.edu',
            'saved': [{'code': 'MSSE 610', 'status': 'completed',
                       'term': '102025-121425', 'grade': 'A'}],
            'skipped': [],
            'cleared': [{'requirementCode': 'MSSE 601', 'substituteCode': 'MSES 602'}],
        }


class FakeSubstitutionService:
    def __init__(self):
        self.calls = []

    def review(self, clerk_user_id):
        self.calls.append(('review', clerk_user_id))
        return {'requirements': [], 'courses': [], 'substitutions': []}

    def declare(self, clerk_user_id, requirement, substitute):
        self.calls.append(('declare', clerk_user_id, requirement, substitute))
        return {'requirements': [], 'courses': [], 'substitutions': [{'id': 1}]}

    def remove(self, clerk_user_id, substitution_id):
        self.calls.append(('remove', clerk_user_id, substitution_id))
        return {'requirements': [], 'courses': [], 'substitutions': []}


def _client(store=None, substitutions=None):
    app = create_app(_settings())
    app.state.transcript_store = store
    app.state.substitution_service = substitutions
    return TestClient(app), app


def _upload(client, headers=None, filename='transcript.pdf'):
    return client.post(
        '/api/v1/transcript/upload',
        files={'file': (filename, PDF[1], PDF[2])},
        headers=headers or {},
    )


def test_upload_rejects_empty_pdf():
    client, _ = _client(store=FakeStore())

    response = client.post(
        '/api/v1/transcript/upload',
        files={'file': ('transcript.pdf', b'', 'application/pdf')},
        headers={'X-Dev-Student-Id': DEV_STUDENT},
    )

    assert response.status_code == 400
    assert 'empty' in response.json()['error']['message']


def test_upload_reports_parse_failure(monkeypatch):
    def boom(_pdf):
        raise RuntimeError('corrupt')

    monkeypatch.setattr(transcript_api, 'process_pdf_bytes', boom)
    client, _ = _client(store=FakeStore())

    response = _upload(client, {'X-Dev-Student-Id': DEV_STUDENT})

    assert response.status_code == 400
    assert response.json()['error']['details']['reason'] == 'RuntimeError'


def test_upload_rejects_pdf_with_no_course_rows(monkeypatch):
    monkeypatch.setattr(transcript_api, 'process_pdf_bytes',
                        lambda _pdf: {**PARSED, 'courses': []})
    store = FakeStore()
    client, _ = _client(store=store)

    response = _upload(client, {'X-Dev-Student-Id': DEV_STUDENT})

    assert response.status_code == 400
    assert 'No course rows' in response.json()['error']['message']
    assert store.calls == []


def test_upload_without_database_is_not_implemented(monkeypatch):
    monkeypatch.setattr(transcript_api, 'process_pdf_bytes', lambda _pdf: PARSED)
    client, _ = _client(store=None)

    response = _upload(client, {'X-Dev-Student-Id': DEV_STUDENT})

    assert response.status_code == 501


def test_upload_returns_saved_rows_and_cleared_substitutions(monkeypatch):
    monkeypatch.setattr(transcript_api, 'process_pdf_bytes', lambda _pdf: PARSED)
    store = FakeStore()
    client, _ = _client(store=store)

    response = _upload(client, {'X-Dev-Student-Id': DEV_STUDENT})

    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'success'
    assert body['course_count'] == 1
    assert body['email'] == 'a@example.edu'
    assert body['clearedSubstitutions'][0]['requirementCode'] == 'MSSE 601'
    assert store.calls == [(DEV_STUDENT, PARSED['courses'])]


def test_review_requires_identity():
    client, _ = _client(substitutions=FakeSubstitutionService())

    response = client.get('/api/v1/transcript/review')

    assert response.status_code == 401


def test_review_returns_service_data():
    service = FakeSubstitutionService()
    client, _ = _client(substitutions=service)

    response = client.get('/api/v1/transcript/review',
                          headers={'X-Dev-Student-Id': DEV_STUDENT})

    assert response.status_code == 200
    assert response.json() == {'requirements': [], 'courses': [], 'substitutions': []}
    assert service.calls == [('review', DEV_STUDENT)]


def test_substitution_routes_call_service():
    service = FakeSubstitutionService()
    client, _ = _client(substitutions=service)
    headers = {'X-Dev-Student-Id': DEV_STUDENT}

    declared = client.post(
        '/api/v1/transcript/substitutions',
        json={'requirementCode': 'MSSE 601', 'substituteCode': 'MSES 602'},
        headers=headers,
    )
    removed = client.delete('/api/v1/transcript/substitutions/s-9', headers=headers)

    assert declared.status_code == 200
    assert declared.json()['substitutions'] == [{'id': 1}]
    assert removed.status_code == 200
    assert service.calls == [
        ('declare', DEV_STUDENT, 'MSSE 601', 'MSES 602'),
        ('remove', DEV_STUDENT, 's-9'),
    ]


def test_substitution_routes_need_database():
    client, _ = _client(substitutions=None)
    headers = {'X-Dev-Student-Id': DEV_STUDENT}

    response = client.get('/api/v1/transcript/review', headers=headers)

    assert response.status_code == 501


def test_substitution_routes_require_identity():
    client, _ = _client(substitutions=FakeSubstitutionService())

    declared = client.post(
        '/api/v1/transcript/substitutions',
        json={'requirementCode': 'MSSE 601', 'substituteCode': 'MSES 602'},
    )
    removed = client.delete('/api/v1/transcript/substitutions/s-9')

    assert declared.status_code == 401
    assert removed.status_code == 401
