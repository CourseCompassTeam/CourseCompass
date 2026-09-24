"""Turns a tool result into the reply the student sees."""

from typing import Any

from app.schemas.query import QueryResponse


class ResponseAssembler:
    """Builds a natural-language reply from a tool result.

    The reply must not add anything the tool did not return (QA-02).
    """

    def assemble(self, intent: str,
                 tool_result: dict[str, Any]) -> QueryResponse:
        """Builds the API response.

        Args:
            intent: The intent that produced the result.
            tool_result: The verified data returned by the tool.

        Returns:
            The response sent to the frontend.
        """
        raise NotImplementedError
