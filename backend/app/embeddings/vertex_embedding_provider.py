"""Vertex AI implementation of EmbeddingProvider."""

from __future__ import annotations

from google import genai
from google.genai import types

from app.embeddings.embedding_provider import TASK_QUERY
from app.embeddings.embedding_provider import EmbeddingProvider


class VertexEmbeddingProvider(EmbeddingProvider):
    """Calls gemini-embedding-001 on Vertex AI via ADC.

    The live syllabus_chunks.embedding column is vector(768), so the
    default output dimensionality is 768.

    Args:
        project: GCP project ID for Vertex AI.
        location: Vertex region, e.g. us-central1.
        model: Embedding model id.
        dimensions: Must match the pgvector column length.
        client: Optional prebuilt genai Client (for tests).
    """

    def __init__(
        self,
        project: str,
        location: str = 'us-central1',
        model: str = 'gemini-embedding-001',
        dimensions: int = 768,
        client: genai.Client | None = None,
    ):
        if not project:
            raise ValueError(
                'GCP project is required for Vertex embeddings.'
            )
        if dimensions <= 0:
            raise ValueError('embedding dimensions must be positive.')
        self._project = project
        self._location = location
        self._model = model
        self._dimensions = dimensions
        self._client = client or genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )

    def embed(self, text: str, task: str = TASK_QUERY) -> list[float]:
        """Embeds a single string with the configured dimensionality.

        Args:
            text: Chunk or student interest to encode.
            task: Vertex task type (query vs document).

        Returns:
            A float vector of length ``dimensions``.

        Raises:
            ValueError: If text is empty or the model returns a
                different vector length.
        """
        if not text or not text.strip():
            raise ValueError('text to embed must not be empty.')

        response = self._client.models.embed_content(
            model=self._model,
            contents=text.strip(),
            config=types.EmbedContentConfig(
                task_type=task,
                output_dimensionality=self._dimensions,
            ),
        )
        embeddings = getattr(response, 'embeddings', None) or []
        if not embeddings:
            raise ValueError('Embedding model returned no vectors.')
        values = list(getattr(embeddings[0], 'values', None) or [])
        if len(values) != self._dimensions:
            raise ValueError(
                f'Expected {self._dimensions} dimensions, got '
                f'{len(values)}.'
            )
        return values
