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


def test_query_rate_limit_includes_cors_header():
    class _BusyProvider:
        def choose_tool(self, query, tools, history=None):
            del query, tools, history
            error = Exception('Resource exhausted')
            error.code = 429
            raise error

    client = TestClient(create_app(_settings()))
    client.app.state.llm_provider = _BusyProvider()
    response = client.post(
        '/api/v1/query',
        json={'query': 'What courses are left?'},
        headers={'Origin': 'http://localhost:5173'},
    )
    assert response.status_code == 429
    assert response.json()['error']['code'] == 'TOO_MANY_REQUESTS'
    assert response.headers['access-control-allow-origin'] == (
        'http://localhost:5173'
    )


def test_query_stub_returns_not_implemented_envelope():
    client = TestClient(create_app(_settings()))
    response = client.post('/api/v1/query', json={'query': 'Am I done?'})
    assert response.status_code == 501
    body = response.json()
    assert body['error']['code'] == 'NOT_IMPLEMENTED'
