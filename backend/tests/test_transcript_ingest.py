"""Spike: can the backend receive a student transcript payload?"""

import json

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


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


NEARLY_DONE_TRANSCRIPT = {
    'clerk_user_id': 'user_nearly_done',
    'email': 'nearly.done@example.edu',
    'entries': [
        {'code': 'MSSE 601', 'term': 'Fall 2024', 'status': 'completed'},
        {'code': 'MSSE 603', 'term': 'Fall 2024', 'status': 'completed'},
        {'code': 'MSSE 610', 'term': 'Spring 2025', 'status': 'completed'},
        {'code': 'MSSE 613', 'term': 'Spring 2025', 'status': 'completed'},
        {'code': 'MSSE 615', 'term': 'Summer 2025', 'status': 'completed'},
        {'code': 'MSSE 635', 'term': 'Summer 2025', 'status': 'completed'},
        {'code': 'MSSE 640', 'term': 'Fall 2025', 'status': 'completed'},
        {'code': 'MSSE 642', 'term': 'Fall 2025', 'status': 'completed'},
        {'code': 'MSES 602', 'term': 'Fall 2025', 'status': 'completed'},
        {'code': 'MSCC 697', 'term': 'Fall 2025', 'status': 'completed'},
    ],
}


def _post_transcript(body: dict | str, filename: str = 'transcript.json'):
    client = TestClient(create_app(_settings()))
    raw = body if isinstance(body, str) else json.dumps(body)
    return client.post(
        '/api/v1/admin/ingest/transcripts',
        files={'file': (filename, raw, 'application/json')},
    )


def test_backend_accepts_a_json_transcript_upload():
    response = _post_transcript(NEARLY_DONE_TRANSCRIPT)

    assert response.status_code == 202
    body = response.json()
    assert body['status'] == 'succeeded'
    assert body['records_processed'] == 10
    assert body['job_id']
    assert body.get('error_message') is None


def test_transcript_rejects_empty_entries():
    response = _post_transcript({
        'email': 'just.started@example.edu',
        'entries': [],
    })

    assert response.status_code == 400
    assert response.json()['error']['code'] == 'BAD_REQUEST'


def test_transcript_rejects_invalid_status():
    response = _post_transcript({
        'entries': [
            {'code': 'MSSE 601', 'term': 'Fall 2024', 'status': 'dropped'},
        ],
    })

    assert response.status_code == 400
    assert response.json()['error']['code'] == 'BAD_REQUEST'


def test_transcript_rejects_non_json_file():
    response = _post_transcript('not json')

    assert response.status_code == 400
    assert response.json()['error']['code'] == 'BAD_REQUEST'


NEARLY_DONE = 'user_3K1pC0YksFOD8HW1dIiz4ITDt90'

PARSED_TWO_COURSES = {
    'course_count': 2,
    'courses': [
        {
            'code': 'MSSE 600',
            'title': 'Object-Oriented So',
            'grade': 'A',
            'hours_attempted': 3.0,
            'hours_completed': 3.0,
            'hours_gpa': 3.0,
            'points': 12.0,
            'dates': '01/15/24-03/10/24',
        },
        {
            'code': 'MSSE 610',
            'title': 'Software Req and P',
            'grade': 'A',
            'hours_attempted': 3.0,
            'hours_completed': 3.0,
            'hours_gpa': 3.0,
            'points': 12.0,
            'dates': '10/20/25-12/14/25',
        },
    ],
    'term_summaries': [],
    'cumulative_summary': {},
}


def test_pdf_upload_rejects_non_pdf():
    client = TestClient(create_app(_settings()))
    response = client.post(
        '/api/v1/transcript/upload',
        files={'file': ('transcript.txt', b'not a pdf', 'text/plain')},
    )
    assert response.status_code == 400
    assert response.json()['error']['code'] == 'BAD_REQUEST'


def test_pdf_upload_requires_student_identity(monkeypatch):
    from app.api.v1 import transcript as transcript_api

    monkeypatch.setattr(
        transcript_api, 'process_pdf_bytes', lambda _pdf: PARSED_TWO_COURSES
    )
    client = TestClient(create_app(_settings()))
    response = client.post(
        '/api/v1/transcript/upload',
        files={'file': ('transcript.pdf', b'%PDF-fake', 'application/pdf')},
    )
    assert response.status_code == 401
    assert response.json()['error']['code'] == 'UNAUTHORIZED'


def test_pdf_upload_overwrites_transcript_for_dev_student(monkeypatch):
    from app.api.v1 import transcript as transcript_api
    from tests.test_transcript_store import _FakeStore

    monkeypatch.setattr(
        transcript_api, 'process_pdf_bytes', lambda _pdf: PARSED_TWO_COURSES
    )
    app = create_app(_settings())
    store = _FakeStore()
    app.state.transcript_store = store
    client = TestClient(app)
    response = client.post(
        '/api/v1/transcript/upload',
        files={'file': ('transcript.pdf', b'%PDF-fake', 'application/pdf')},
        headers={'X-Dev-Student-Id': NEARLY_DONE},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['clerk_user_id'] == NEARLY_DONE
    assert body['saved'][0]['code'] == 'MSSE 610'
    assert body['skipped'][0]['code'] == 'MSSE 600'
    assert store.rows['s-nearly'] == [
        ('c-610', '102025-121425', 'completed'),
    ]
