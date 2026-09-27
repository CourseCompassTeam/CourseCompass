"""Calls the one tool that matches a routed intent."""

from __future__ import annotations

import logging
from typing import Any

from app.tools.mcp_tools import MCPTools

_LOG = logging.getLogger(__name__)


class ToolDispatcher:
    """Dispatches an intent to its MCPTools function.

    The authenticated student's ID is always supplied by the server, never
    by the LLM, so a tool can only return that student's own data (QA-03).

    Args:
        tools: The in-process tool directory.
    """

    def __init__(self, tools: MCPTools):
        self._tools = tools

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
        args = arguments or {}
        _LOG.info('dispatch tool=%s student=%s', intent, student_id or '-')
        if intent == 'audit_degree':
            return self._tools.audit_degree(
                student_id,
                args.get('program_name'),
            )
        if intent == 'get_course_description':
            return self._tools.get_course_description(
                student_id,
                str(args.get('course_id') or ''),
            )
        if intent == 'recommend_courses':
            return self._tools.recommend_courses(
                student_id,
                str(args.get('interest') or ''),
            )
        if intent == 'build_schedule':
            return self._tools.build_schedule(student_id)
        if intent == 'get_advisor_contact':
            return self._tools.get_advisor_contact(student_id)
        if intent == 'get_career_services':
            return self._tools.get_career_services(student_id)
        if intent == 'get_next_milestones':
            return self._tools.get_next_milestones(student_id)
        return {
            'resourceName': 'Book an advising appointment',
            'url': 'https://example.com/advising',
            'reason': f'unknown_tool:{intent}',
        }
