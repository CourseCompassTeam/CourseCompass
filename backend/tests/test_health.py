"""Smoke tests for the runnable backend skeleton."""

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _settings() -> Settings:
    return Settings(
        app_name='coursecompass-api-test',
        environment='test',
        database_url='',
        clerk_secret_key='',
        llm_provider='',
        llm_api_key='',
        llm_model='gemini-2.5-flash',
        gcp_project='',
        gcp_location='us-central1',
        cors_origins=('http://localhost:5173',),
    )


def test_health_returns_ok():
    client = TestClient(create_app(_settings()))
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_ready_returns_ready():
    client = TestClient(create_app(_settings()))
    response = client.get('/ready')
    assert response.status_code == 200
    assert response.json() == {'status': 'ready'}


def test_query_stub_returns_not_implemented_envelope():
    client = TestClient(create_app(_settings()))
    response = client.post('/api/v1/query', json={'query': 'Am I done?'})
    assert response.status_code == 501
    body = response.json()
    assert body['error']['code'] == 'NOT_IMPLEMENTED'
