"""Tests for Vertex Gemini LLMProvider (mocked client)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.orchestration.provider_factory import create_llm_provider
from app.orchestration.tool_catalog import TOOL_DEFINITIONS
from app.orchestration.vertex_gemini_provider import VertexGeminiProvider


def _settings(**overrides) -> Settings:
    base = dict(
        app_name='coursecompass-api-test',
        environment='test',
        database_url='',
        clerk_secret_key='',
        llm_provider='vertex',
        llm_api_key='',
        llm_model='gemini-2.5-flash',
        gcp_project='coursecompass-509519',
        gcp_location='us-central1',
        cors_origins=('http://localhost:5173',),
    )
    base.update(overrides)
    return Settings(**base)


def _response_with_function(name: str, args: dict):
    part = SimpleNamespace(function_call=SimpleNamespace(name=name, args=args))
    content = SimpleNamespace(parts=[part])
    candidate = SimpleNamespace(content=content)
    return SimpleNamespace(candidates=[candidate], text=None)


def test_create_llm_provider_requires_name():
    with pytest.raises(ValueError, match='LLM_PROVIDER'):
        create_llm_provider(_settings(llm_provider=''))


def test_create_llm_provider_requires_project():
    with pytest.raises(ValueError, match='GCP_PROJECT_ID'):
        create_llm_provider(_settings(gcp_project=''))


def test_choose_tool_returns_audit_degree():
    client = MagicMock()
    client.models.generate_content.return_value = _response_with_function(
        'audit_degree', {}
    )
    provider = VertexGeminiProvider(
        project='coursecompass-509519',
        client=client,
    )
    choice = provider.choose_tool('How many credits do I have left?',
                                  TOOL_DEFINITIONS)
    assert choice['tool'] == 'audit_degree'
    assert choice['redirect'] is False
    assert choice['arguments'] == {}
    client.models.generate_content.assert_called_once()


def test_choose_tool_strips_hallucinated_student_id():
    client = MagicMock()
    client.models.generate_content.return_value = _response_with_function(
        'get_course_description',
        {'course_id': 'CS501', 'student_id': 'should-not-pass'},
    )
    provider = VertexGeminiProvider(
        project='coursecompass-509519',
        client=client,
    )
    choice = provider.choose_tool('What is CS501?', TOOL_DEFINITIONS)
    assert choice['tool'] == 'get_course_description'
    assert choice['arguments'] == {'course_id': 'CS501'}


def test_choose_tool_redirect_sentinel():
    client = MagicMock()
    client.models.generate_content.return_value = _response_with_function(
        'redirect_out_of_scope',
        {'reason': 'financial_aid'},
    )
    provider = VertexGeminiProvider(
        project='coursecompass-509519',
        client=client,
    )
    choice = provider.choose_tool('How do I pay my tuition?', TOOL_DEFINITIONS)
    assert choice['redirect'] is True
    assert choice['tool'] is None


def test_phrase_response_returns_text():
    client = MagicMock()
    client.models.generate_content.return_value = SimpleNamespace(
        text='You have 6 credits remaining.',
        candidates=[],
    )
    provider = VertexGeminiProvider(
        project='coursecompass-509519',
        client=client,
    )
    text = provider.phrase_response({'credits_remaining': 6})
    assert text == 'You have 6 credits remaining.'
