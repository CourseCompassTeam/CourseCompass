"""Interface to the external LLM provider.

The provider is still to be decided (Gemini, OpenAI, or Claude). The rest
of the code depends only on this interface, so the vendor can change
without touching other layers (QA-04).
"""

import abc
from typing import Any


class LLMProvider(abc.ABC):
    """An LLM that can choose from a fixed set of tools."""

    @abc.abstractmethod
    def choose_tool(self, query: str,
                    tools: list[dict[str, Any]]) -> dict[str, Any]:
        """Asks the LLM which tool, if any, answers the query.

        Args:
            query: The student's question, treated as data and never as
                instructions.
            tools: The tool definitions the LLM may choose from.

        Returns:
            The chosen tool name and its arguments.
        """

    @abc.abstractmethod
    def phrase_response(self, tool_result: dict[str, Any]) -> str:
        """Asks the LLM to phrase a verified tool result as a reply.

        Args:
            tool_result: The data returned by the tool.

        Returns:
            Natural-language text.
        """
