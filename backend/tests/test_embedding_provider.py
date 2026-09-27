"""Tests for Vertex embedding provider (mocked client)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.embeddings.embedding_provider import TASK_DOCUMENT
from app.embeddings.vertex_embedding_provider import VertexEmbeddingProvider
from app.orchestration.provider_factory import create_embedding_provider


def _settings(**overrides) -> Settings:
    base = dict(
        app_name='coursecompass-api-test',
        environment='test',
        database_url='',
        clerk_secret_key='',
        llm_provider='vertex',
        llm_api_key='',
        llm_model='gemini-2.5-flash',
        embedding_model='gemini-embedding-001',
        embedding_dimensions=768,
        gcp_project='coursecompass-509519',
        gcp_location='us-central1',
        cors_origins=('http://localhost:5173',),
    )
    base.update(overrides)
    return Settings(**base)


def test_create_embedding_provider_requires_project():
    with pytest.raises(ValueError, match='GCP_PROJECT_ID'):
        create_embedding_provider(_settings(gcp_project=''))


def test_embed_returns_configured_dimensions():
    values = [0.1] * 768
    client = MagicMock()
    client.models.embed_content.return_value = SimpleNamespace(
        embeddings=[SimpleNamespace(values=values)],
    )
    provider = VertexEmbeddingProvider(
        project='coursecompass-509519',
        client=client,
    )
    vector = provider.embed('cloud computing')
    assert len(vector) == 768
    assert vector[0] == 0.1
    kwargs = client.models.embed_content.call_args.kwargs
    assert kwargs['model'] == 'gemini-embedding-001'
    assert kwargs['config'].output_dimensionality == 768


def test_embed_documents_uses_document_task():
    values = [0.2] * 768
    client = MagicMock()
    client.models.embed_content.return_value = SimpleNamespace(
        embeddings=[SimpleNamespace(values=values)],
    )
    provider = VertexEmbeddingProvider(
        project='coursecompass-509519',
        client=client,
    )
    vectors = provider.embed_documents(['chunk a', 'chunk b'])
    assert len(vectors) == 2
    assert client.models.embed_content.call_count == 2
    task = client.models.embed_content.call_args.kwargs['config'].task_type
    assert task == TASK_DOCUMENT


def test_embed_rejects_wrong_length():
    client = MagicMock()
    client.models.embed_content.return_value = SimpleNamespace(
        embeddings=[SimpleNamespace(values=[0.1] * 3072)],
    )
    provider = VertexEmbeddingProvider(
        project='coursecompass-509519',
        client=client,
    )
    with pytest.raises(ValueError, match='Expected 768'):
        provider.embed('too long')
