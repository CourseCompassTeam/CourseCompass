"""Deterministic stand-in for the LLM, for end-to-end tests.

Selected with ``LLM_PROVIDER=fake``. It picks a tool from simple keyword
rules and phrases every reply with a fixed sentence, so the rest of the
pipeline (tools, services, database, response assembly) runs for real
without calling Vertex AI. ``create_llm_provider`` refuses it in
production.
"""

from __future__ import annotations

import re
from typing import Any

from app.orchestration.llm_provider import LLMProvider
from app.orchestration.llm_provider import ToolChoice

_COURSE_CODE_RE = re.compile(r'\b(MS[A-Z]{2})[\s-]?(\d{3})\b', re.IGNORECASE)

# First matching rule wins. Anything unmatched is treated as out of scope.
_KEYWORD_RULES: list[tuple[str, tuple[str, ...]]] = [
    ('get_career_services', ('career',)),
    ('get_advisor_contact', ('advisor',)),
    ('get_next_milestones', ('milestone',)),
    ('audit_degree', ('graduate', 'credits', 'requirement', 'degree')),
]

FAKE_REPLY = 'Scripted test reply.'


class FakeLLMProvider(LLMProvider):
    """Keyword router with a fixed reply. Test environments only."""

    def choose_tool(
        self,
        query: str,
        tools: list[dict[str, Any]],
        history: list[dict[str, str]] | None = None,
    ) -> ToolChoice:
        del tools, history
        text = query or ''
        code = _COURSE_CODE_RE.search(text)
        if code:
            course_id = f'{code.group(1).upper()} {code.group(2)}'
            return ToolChoice(
                tool='get_course_description',
                arguments={'course_id': course_id},
                redirect=False,
            )
        lowered = text.lower()
        for tool, keywords in _KEYWORD_RULES:
            if any(word in lowered for word in keywords):
                return ToolChoice(tool=tool, arguments={}, redirect=False)
        return ToolChoice(
            tool=None,
            arguments={'reason': 'Not covered by the test LLM.'},
            redirect=True,
        )

    def phrase_response(self, tool_result: dict[str, Any]) -> str:
        del tool_result
        return FAKE_REPLY
