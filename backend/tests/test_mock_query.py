"""Tests for the local mock query pipeline."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.orchestration.mock_query import answer_query


def _settings() -> Settings:
    return Settings(
        app_name='coursecompass-api-test',
        environment='test',
        database_url='',
        clerk_secret_key='',
        llm_provider='',
        llm_api_key='',
        llm_model='gemini-2.5-flash',
        embedding_model='gemini-embedding-001',
        embedding_dimensions=768,
        gcp_project='',
        gcp_location='us-central1',
        cors_origins=('http://localhost:5173',),
    )


def _provider(tool: str | None, arguments: dict | None = None,
              redirect: bool = False, message: str = 'Mock reply.') -> MagicMock:
    provider = MagicMock()
    provider.choose_tool.return_value = {
        'tool': tool,
        'arguments': arguments or {},
        'redirect': redirect,
    }
    provider.phrase_response.return_value = message
    return provider


def test_answer_query_returns_audit_facts():
    provider = _provider('audit_degree', message='You have 6 credits left.')
    response = answer_query(provider, 'How many credits do I still need?')
    assert response.type == 'audit'
    assert response.content['creditsRemaining'] == 9
    assert response.content['requirementsMet'] is False
    assert response.content['missingCourses'] == [
        'CS501', 'CS502', 'CS510',
    ]
    assert response.content['message'] == 'You have 6 credits left.'
    provider.phrase_response.assert_called_once()


def test_answer_query_redirects_out_of_scope():
    provider = _provider(
        None,
        arguments={'reason': 'financial_aid'},
        redirect=True,
        message='Please contact an advisor.',
    )
    response = answer_query(provider, 'How do I apply for financial aid?')
    assert response.type == 'redirect'
    assert response.content['url'] == 'https://example.com/advising'
    assert response.content['reason'] == 'financial_aid'


def test_answer_query_combines_course_and_career():
    provider = _provider(
        'get_career_services',
        message='CS502 covers software systems. Confirm career fit '
                'with Career Services.',
    )
    response = answer_query(
        provider,
        'Can you tell me about course CS502 and how it applies to '
        'my future career?',
    )
    assert response.type == 'recommendation'
    assert response.content['courses'][0]['code'] == 'CS502'
    assert response.content['resourceName'] == 'Career Services'
    assert response.content['url'] == (
        'https://example.com/career-services'
    )
    assert 'careerDisclaimer' in response.content


def test_recommend_ranks_with_real_embedding_provider():
    llm = _provider(
        'recommend_courses',
        arguments={'interest': 'software design'},
        message='CS502 is the closest match.',
    )
    embeddings = MagicMock()

    def _embed(text: str, task: str = 'RETRIEVAL_QUERY') -> list[float]:
        lowered = text.lower()
        if 'software design' in lowered or 'software systems' in lowered:
            return [1.0, 0.0]
        if 'algorithm' in lowered:
            return [0.4, 0.6]
        return [0.0, 1.0]

    embeddings.embed.side_effect = _embed
    response = answer_query(
        llm,
        'What course can I take if I like software design?',
        embedding_provider=embeddings,
    )
    codes = [course['code'] for course in response.content['courses']]
    assert codes[0] == 'CS502'
    assert response.content['searchMethod'] == 'gemini-embedding-001'
    assert embeddings.embed.call_count >= 2


def test_answer_query_sets_detailed_when_student_asks():
    provider = _provider(
        'recommend_courses',
        arguments={'interest': 'software design'},
        message='Detailed CS502 reply.',
    )
    response = answer_query(
        provider,
        'Recommend a course about software design if it fits my '
        'schedule. Please provide more detail.',
    )
    assert response.content['detailLevel'] == 'detailed'
    assert response.content['scheduleChecked'] is False
    assert response.content['advisingUrl'] == (
        'https://example.com/advising'
    )
    assert response.content['studentInterest'] == 'software design'


def test_answer_query_course_includes_career_handoff():
    provider = _provider(
        'get_course_description',
        arguments={'course_id': 'CS502'},
        message='CS502 builds system design skills.',
    )
    response = answer_query(provider, 'What is course CS502 about?')
    assert response.type == 'recommendation'
    assert response.content['courses'][0]['code'] == 'CS502'
    assert response.content['url'] == (
        'https://example.com/career-services'
    )


def test_post_query_uses_mock_pipeline():
    app = create_app(_settings())
    app.state.llm_provider = _provider(
        'audit_degree',
        message='You have 6 credits remaining.',
    )
    client = TestClient(app)
    response = client.post(
        '/api/v1/query',
        json={'query': 'How many credits do I still need?'},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['type'] == 'audit'
    assert body['content']['creditsRemaining'] == 9
    assert body['content']['message'] == 'You have 6 credits remaining.'
    assert body['id']
    assert body['timestamp']
