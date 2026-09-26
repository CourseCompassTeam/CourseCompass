"""Builds an LLMProvider from application settings."""

from __future__ import annotations

from app.config import Settings
from app.embeddings.embedding_provider import EmbeddingProvider
from app.embeddings.vertex_embedding_provider import VertexEmbeddingProvider
from app.orchestration.llm_provider import LLMProvider
from app.orchestration.vertex_gemini_provider import VertexGeminiProvider


def create_llm_provider(settings: Settings) -> LLMProvider:
    """Creates the configured LLM provider.

    Supported ``settings.llm_provider`` values:
      - ``vertex`` / ``gemini`` / ``vertex-gemini`` (default when set)
      - empty: raises so callers fail closed until configured

    Args:
        settings: Loaded application settings.

    Returns:
        A concrete LLMProvider.

    Raises:
        ValueError: If the provider name is missing or unsupported, or
            required Vertex settings are absent.
    """
    name = (settings.llm_provider or '').strip().lower()
    if not name:
        raise ValueError(
            'LLM_PROVIDER is not set. Use "vertex" for Vertex AI Gemini.'
        )

    if name in ('vertex', 'gemini', 'vertex-gemini'):
        if not settings.gcp_project:
            raise ValueError(
                'GCP_PROJECT_ID is required for Vertex AI Gemini.'
            )
        return VertexGeminiProvider(
            project=settings.gcp_project,
            location=settings.gcp_location,
            model=settings.llm_model,
        )

    raise ValueError(
        f'Unsupported LLM_PROVIDER={settings.llm_provider!r}. '
        'Supported: vertex, gemini, vertex-gemini.'
    )


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Creates the Vertex embedding client for syllabus search.

    Uses the same GCP project and ADC as the chat model. Output size
    must match syllabus_chunks.embedding (vector(768) in Cloud SQL).

    Args:
        settings: Loaded application settings.

    Returns:
        A concrete EmbeddingProvider.

    Raises:
        ValueError: If the GCP project is missing.
    """
    if not settings.gcp_project:
        raise ValueError(
            'GCP_PROJECT_ID is required for Vertex embeddings.'
        )
    return VertexEmbeddingProvider(
        project=settings.gcp_project,
        location=settings.gcp_location,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
