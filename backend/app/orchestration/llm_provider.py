"""Interface to the external LLM provider.

CourseCompass uses Vertex AI Gemini by default (see
``vertex_gemini_provider``). The rest of the code depends only on this
interface, so the vendor can change without touching other layers (QA-04).
"""

from __future__ import annotations

import abc
from typing import Any
from typing import TypedDict


class ToolChoice(TypedDict):
    """Result of asking the LLM which tool to call.

    Attributes:
        tool: Tool name from the catalog, or None for a redirect.
        arguments: Arguments for the tool (never includes student_id).
        redirect: True when the query is out of scope.
    """

    tool: str | None
    arguments: dict[str, Any]
    redirect: bool


class LLMProvider(abc.ABC):
    """An LLM that can choose from a fixed set of tools."""

    @abc.abstractmethod
    def choose_tool(self, query: str,
                    tools: list[dict[str, Any]]) -> ToolChoice:
        """Asks the LLM which tool, if any, answers the query.

        Args:
            query: The student's question, treated as data and never as
                instructions.
            tools: The tool definitions the LLM may choose from. Each item
                has ``name``, ``description``, and ``parameters`` (JSON
                Schema object).

        Returns:
            The chosen tool name and its arguments, or a redirect.
        """

    @abc.abstractmethod
    def phrase_response(self, tool_result: dict[str, Any]) -> str:
        """Asks the LLM to phrase a verified tool result as a reply.

        Args:
            tool_result: The data returned by the tool.

        Returns:
            Natural-language text.
        """
