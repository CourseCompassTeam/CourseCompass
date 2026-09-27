"""Interface to the embedding model.

Course catalog search and syllabus ingest depend on this interface, not
on Vertex, so the vendor can change without touching those layers.
"""

from __future__ import annotations

import abc

# Vertex task types: documents at ingest, queries at search time.
TASK_DOCUMENT = 'RETRIEVAL_DOCUMENT'
TASK_QUERY = 'RETRIEVAL_QUERY'


class EmbeddingProvider(abc.ABC):
    """Turns text into a fixed-length vector for pgvector."""

    @abc.abstractmethod
    def embed(self, text: str, task: str = TASK_QUERY) -> list[float]:
        """Embeds a single string.

        Args:
            text: Chunk or student interest to encode.
            task: Vertex task type (query vs document).

        Returns:
            A vector whose length matches the syllabus_chunks column.
        """

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embeds syllabus chunks for ingest.

        Args:
            texts: Chunk strings in order.

        Returns:
            One vector per input string.
        """
        return [self.embed(text, task=TASK_DOCUMENT) for text in texts]
