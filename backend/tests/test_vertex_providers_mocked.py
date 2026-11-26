"""Mocked calls to the Vertex AI embedding and Gemini providers.

No network. The genai client is a MagicMock, so these tests check that we
build the right request, read the right response fields, and handle the
common failures. They do not check model quality.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from google.genai import errors as genai_errors

from app.config import Settings
from app.embeddings.embedding_provider import TASK_DOCUMENT
from app.embeddings.vertex_embedding_provider import VertexEmbeddingProvider
from app.orchestration import vertex_gemini_provider as gemini_module
from app.orchestration.provider_factory import create_embedding_provider
from app.orchestration.provider_factory import create_llm_provider
from app.orchestration.vertex_gemini_provider import VertexGeminiProvider


def _settings(**overrides) -> Settings:
    values = dict(
        app_name='coursecompass-api-test',
        environment='test',
        database_url='',
        clerk_secret_key='',
        clerk_publishable_key='',
        clerk_jwks_url='',
        clerk_jwt_key='',
        clerk_issuer='',
        clerk_authorized_parties=(),
        llm_provider='vertex',
        llm_api_key='',
        llm_model='gemini-2.5-flash',
        embedding_model='gemini-embedding-001',
        embedding_dimensions=768,
        gcp_project='test-project',
        gcp_location='us-central1',
        cors_origins=('http://localhost:5173',),
    )
    values.update(overrides)
    return Settings(**values)


# ------------------------------------------------------------------ embedding

def _embed_response(size):
    return SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1] * size)])


def test_embedding_calls_model_with_dimensions_and_task():
    client = MagicMock()
    client.models.embed_content.return_value = _embed_response(768)
    provider = VertexEmbeddingProvider(project='p', client=client)

    vector = provider.embed('  software architecture  ', task=TASK_DOCUMENT)

    assert len(vector) == 768
    kwargs = client.models.embed_content.call_args.kwargs
    assert kwargs['model'] == 'gemini-embedding-001'
    assert kwargs['contents'] == 'software architecture'
    assert kwargs['config'].output_dimensionality == 768
    assert kwargs['config'].task_type == TASK_DOCUMENT


def test_embedding_rejects_blank_text():
    provider = VertexEmbeddingProvider(project='p', client=MagicMock())

    with pytest.raises(ValueError, match='must not be empty'):
        provider.embed('   ')


def test_embedding_rejects_wrong_vector_length():
    client = MagicMock()
    client.models.embed_content.return_value = _embed_response(10)
    provider = VertexEmbeddingProvider(project='p', client=client)

    with pytest.raises(ValueError, match='Expected 768 dimensions'):
        provider.embed('text')


def test_embedding_rejects_empty_response():
    client = MagicMock()
    client.models.embed_content.return_value = SimpleNamespace(embeddings=[])
    provider = VertexEmbeddingProvider(project='p', client=client)

    with pytest.raises(ValueError, match='returned no vectors'):
        provider.embed('text')


def test_embedding_requires_project_and_positive_dimensions():
    with pytest.raises(ValueError, match='GCP project is required'):
        VertexEmbeddingProvider(project='', client=MagicMock())
    with pytest.raises(ValueError, match='must be positive'):
        VertexEmbeddingProvider(project='p', dimensions=0, client=MagicMock())


def test_embedding_factory_uses_settings():
    provider = create_embedding_provider(_settings())

    assert isinstance(provider, VertexEmbeddingProvider)


def test_embedding_factory_requires_project():
    with pytest.raises(ValueError, match='GCP_PROJECT_ID'):
        create_embedding_provider(_settings(gcp_project=''))


# ----------------------------------------------------------------- Gemini chat

TOOLS = [{
    'name': 'audit_degree',
    'description': 'Audits the degree.',
    'parameters': {'type': 'object', 'properties': {}},
}]


def _function_call_response(name, args):
    part = SimpleNamespace(function_call=SimpleNamespace(name=name, args=args))
    return SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[part]))])


def _text_response(text):
    return SimpleNamespace(text=text)


def test_choose_tool_returns_selected_function():
    client = MagicMock()
    client.models.generate_content.return_value = _function_call_response(
        'audit_degree', {'student_id': 'hallucinated', 'program_name': 'MSSE'})
    provider = VertexGeminiProvider(project='p', client=client)

    choice = provider.choose_tool('what do I still need?', TOOLS)

    assert choice['tool'] == 'audit_degree'
    assert choice['arguments'] == {'program_name': 'MSSE'}
    assert choice['redirect'] is False
    kwargs = client.models.generate_content.call_args.kwargs
    assert kwargs['model'] == 'gemini-2.5-flash'
    assert kwargs['config'].tools[0].function_declarations[0].name == 'audit_degree'


def test_choose_tool_redirects_when_no_function_call():
    client = MagicMock()
    client.models.generate_content.return_value = _text_response('hello')
    provider = VertexGeminiProvider(project='p', client=client)

    choice = provider.choose_tool('hi', TOOLS)

    assert choice['redirect'] is True
    assert choice['arguments'] == {'reason': 'no_tool_selected'}


def test_choose_tool_redirects_on_empty_query_without_calling_model():
    client = MagicMock()
    provider = VertexGeminiProvider(project='p', client=client)

    choice = provider.choose_tool('   ', TOOLS)

    assert choice['redirect'] is True
    client.models.generate_content.assert_not_called()


def test_choose_tool_requires_tools():
    provider = VertexGeminiProvider(project='p', client=MagicMock())

    with pytest.raises(ValueError, match='tools must not be empty'):
        provider.choose_tool('query', [])


def test_phrase_response_returns_model_text():
    client = MagicMock()
    client.models.generate_content.return_value = _text_response(' You need 692. ')
    provider = VertexGeminiProvider(project='p', client=client)

    assert provider.phrase_response({'missing': ['MSSE 692']}) == 'You need 692.'


def test_phrase_response_falls_back_on_empty_text():
    client = MagicMock()
    client.models.generate_content.return_value = _text_response('')
    provider = VertexGeminiProvider(project='p', client=client)

    reply = provider.phrase_response({})

    assert 'could not phrase' in reply


def test_generate_retries_on_unavailable_then_succeeds(monkeypatch):
    monkeypatch.setattr(gemini_module.time, 'sleep', lambda _seconds: None)
    client = MagicMock()
    busy = genai_errors.APIError(503, {'error': {'message': 'busy', 'status': 'UNAVAILABLE'}})
    client.models.generate_content.side_effect = [busy, _text_response('ok')]
    provider = VertexGeminiProvider(project='p', client=client)

    assert provider.phrase_response({}) == 'ok'
    assert client.models.generate_content.call_count == 2


def test_generate_raises_non_retryable_error(monkeypatch):
    monkeypatch.setattr(gemini_module.time, 'sleep', lambda _seconds: None)
    client = MagicMock()
    bad = genai_errors.APIError(400, {'error': {'message': 'bad', 'status': 'INVALID_ARGUMENT'}})
    client.models.generate_content.side_effect = bad
    provider = VertexGeminiProvider(project='p', client=client)

    with pytest.raises(genai_errors.APIError):
        provider.phrase_response({})
    assert client.models.generate_content.call_count == 1


def test_gemini_requires_project():
    with pytest.raises(ValueError, match='GCP project is required'):
        VertexGeminiProvider(project='', client=MagicMock())


def test_llm_factory_builds_vertex_provider():
    assert isinstance(create_llm_provider(_settings()), VertexGeminiProvider)


def test_llm_factory_rejects_missing_or_unknown_provider():
    with pytest.raises(ValueError, match='LLM_PROVIDER is not set'):
        create_llm_provider(_settings(llm_provider=''))
    with pytest.raises(ValueError, match='Unsupported LLM_PROVIDER'):
        create_llm_provider(_settings(llm_provider='openai'))
    with pytest.raises(ValueError, match='GCP_PROJECT_ID is required'):
        create_llm_provider(_settings(gcp_project=''))
