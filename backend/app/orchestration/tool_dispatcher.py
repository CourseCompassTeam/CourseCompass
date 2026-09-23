"""Calls the one tool that matches a routed intent."""

from typing import Any


class ToolDispatcher:
    """Dispatches an intent to its MCPTools function.

    The authenticated student's ID is always supplied by the server, never
    by the LLM, so a tool can only return that student's own data (QA-03).
    """

    def dispatch(self, intent: str, student_id: str,
                 arguments: dict[str, Any]) -> dict[str, Any]:
        """Calls the tool for an intent.

        Every call is logged with student ID, timestamp, and query.

        Args:
            intent: The tool name chosen by the IntentRouter.
            student_id: The authenticated student's ID.
            arguments: Tool arguments extracted from the query.

        Returns:
            The tool's verified result.
        """
        raise NotImplementedError
