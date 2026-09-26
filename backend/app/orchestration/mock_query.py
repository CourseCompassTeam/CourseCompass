"""Local mock pipeline: LLM routes, hardcoded tool data, LLM phrases.

Used by POST /api/v1/query so a student question can go end-to-end
without a database. Replace ``_mock_result`` with MCPTools later.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from datetime import timezone
from typing import Any

from app.embeddings.embedding_provider import TASK_DOCUMENT
from app.embeddings.embedding_provider import TASK_QUERY
from app.embeddings.embedding_provider import EmbeddingProvider
from app.orchestration.llm_provider import LLMProvider
from app.orchestration.tool_catalog import TOOL_DEFINITIONS
from app.orchestration.tool_dispatcher import ToolDispatcher
from app.schemas.query import QueryResponse

_AUDIT_RESULT = {
    'creditsRemaining': 9,
    'requirementsMet': False,
    'missingCourses': ['CS501', 'CS502', 'CS510'],
}

_REDIRECT_RESULT = {
    'resourceName': 'Book an advising appointment',
    'url': 'https://example.com/advising',
}

_CAREER_REDIRECT = {
    'resourceName': 'Career Services',
    'url': 'https://example.com/career-services',
}

_SAMPLE_COURSES = [
    {
        'code': 'CS501',
        'title': 'Introduction to Graduate Algorithms',
        'description': (
            'Covers algorithm design and analysis used in graduate CS: '
            'graphs, dynamic programming, complexity, and how to argue '
            'that a solution is correct and efficient.'
        ),
        'skills': [
            'algorithm design',
            'complexity analysis',
            'problem decomposition',
        ],
    },
    {
        'code': 'CS502',
        'title': 'Software Systems',
        'description': (
            'Covers design and implementation of larger software '
            'systems: architecture, interfaces, reliability, and how '
            'components work together in production-style projects.'
        ),
        'skills': [
            'system design',
            'software architecture',
            'implementation of multi-component systems',
        ],
    },
    {
        'code': 'CS510',
        'title': 'Theory of Computation',
        'description': (
            'Covers automata, computability, and formal languages. '
            'Focus is proofs and models of computation, not building '
            'production software.'
        ),
        'skills': [
            'formal proofs',
            'automata theory',
            'computability',
        ],
    },
]

_COURSE_RE = re.compile(r'\b([A-Za-z]{2,4}\s?\d{3,4})\b')
_DETAIL_RE = re.compile(
    r'\b(more detail|more details|tell me more|explain more|'
    r'go deeper|in depth|in-depth|elaborate)\b',
    re.I,
)
_SCHEDULE_RE = re.compile(
    r'\b(schedule|timetable|this term|next term|fits? my)\b',
    re.I,
)


def answer_query(
    provider: LLMProvider,
    query: str,
    embedding_provider: EmbeddingProvider | None = None,
    tool_dispatcher: ToolDispatcher | None = None,
    student_id: str = '',
) -> QueryResponse:
    """Runs choose_tool -> tool data -> phrase_response.

    When a dispatcher is attached, tools read PostgreSQL. Otherwise
    leftover mock courses are used. Recommend paths still rank with
    embeddings when a provider is configured on the mock path.

    Args:
        provider: Configured LLM provider.
        query: The student's question.
        embedding_provider: Vertex embedding client, if configured.
        tool_dispatcher: Live MCPTools dispatcher, if the database
            is configured.
        student_id: Server-injected student id (QA-03).

    Returns:
        A QueryResponse the frontend can render.
    """
    choice = provider.choose_tool(query, TOOL_DEFINITIONS)
    if tool_dispatcher is not None:
        response_type, facts = _live_result(
            tool_dispatcher, choice, query, student_id
        )
    else:
        response_type, facts = _mock_result(
            choice, query, embedding_provider
        )
    facts = _with_phrase_context(facts, query)
    message = provider.phrase_response(facts)
    content = dict(facts)
    content['message'] = message
    return QueryResponse(
        id=str(uuid.uuid4()),
        type=response_type,
        content=content,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _mock_result(
    choice: dict[str, Any],
    query: str = '',
    embedding_provider: EmbeddingProvider | None = None,
) -> tuple[str, dict[str, Any]]:
    """Returns (response type, hardcoded facts) for a tool choice.

    Recommend paths rank leftover mock courses with real embeddings
    when an embedding provider is attached.

    Args:
        choice: ToolChoice from the LLM provider.
        query: Original student question.
        embedding_provider: Optional Vertex embedding client.

    Returns:
        Response type and JSON-serializable facts for phrasing.
    """
    if choice.get('redirect') or not choice.get('tool'):
        facts = dict(_REDIRECT_RESULT)
        reason = (choice.get('arguments') or {}).get('reason')
        if reason:
            facts['reason'] = reason
        return 'redirect', facts

    tool = choice['tool']
    arguments = choice.get('arguments') or {}
    named_course = _course_from(arguments, query)

    if tool == 'audit_degree':
        return 'audit', dict(_AUDIT_RESULT)

    if tool == 'get_course_description' or (
            tool == 'get_career_services' and named_course):
        course = _lookup_course(named_course or 'CS501')
        facts = {'courses': [course]}
        return 'recommendation', _with_career_handoff(facts)

    if tool in ('recommend_courses', 'build_schedule',
                'get_next_milestones'):
        interest = str(arguments.get('interest') or query)
        leftover = _leftover_courses()
        ranked = leftover
        search_method = 'none'
        if embedding_provider is not None:
            ranked = _rank_with_embeddings(
                embedding_provider, interest, leftover
            )
            search_method = 'gemini-embedding-001'
        facts = {
            'courses': ranked,
            'studentInterest': interest,
            'searchMethod': search_method,
            'leftoverCount': len(leftover),
        }
        return 'recommendation', _with_career_handoff(facts)

    if tool == 'get_career_services':
        return 'redirect', dict(_CAREER_REDIRECT)

    return 'redirect', dict(_REDIRECT_RESULT)


def _live_result(
    dispatcher: ToolDispatcher,
    choice: dict[str, Any],
    query: str,
    student_id: str,
) -> tuple[str, dict[str, Any]]:
    """Runs the chosen tool against live repositories.

    Args:
        dispatcher: Wired MCPTools dispatcher.
        choice: ToolChoice from the LLM provider.
        query: Original student question.
        student_id: Server-injected student id.

    Returns:
        Response type and JSON-serializable facts for phrasing.
    """
    if choice.get('redirect') or not choice.get('tool'):
        facts = dict(_REDIRECT_RESULT)
        reason = (choice.get('arguments') or {}).get('reason')
        if reason:
            facts['reason'] = reason
        return 'redirect', facts

    tool = choice['tool']
    arguments = dict(choice.get('arguments') or {})
    named_course = _course_from(arguments, query)

    if tool == 'get_career_services' and named_course:
        facts = dispatcher.dispatch(
            'get_course_description',
            student_id,
            {'course_id': named_course},
        )
        return 'recommendation', _with_career_handoff(facts)

    facts = dispatcher.dispatch(tool, student_id, arguments)
    if tool == 'audit_degree':
        return 'audit', facts
    if tool == 'get_course_description':
        return 'recommendation', _with_career_handoff(facts)
    if tool in ('recommend_courses', 'get_next_milestones'):
        return 'recommendation', _with_career_handoff(facts)
    if tool == 'build_schedule':
        if facts.get('scheduleChecked'):
            return 'recommendation', facts
        return 'redirect', facts
    if tool in ('get_advisor_contact', 'get_career_services'):
        return 'redirect', facts
    return 'redirect', facts


def _with_phrase_context(
    facts: dict[str, Any],
    query: str,
) -> dict[str, Any]:
    """Adds detail/schedule flags so phrasing can follow the student.

    Args:
        facts: Mock tool result.
        query: Original student question.

    Returns:
        Facts plus detailLevel and optional schedule notes.
    """
    merged = dict(facts)
    merged['studentQuery'] = query
    if _DETAIL_RE.search(query or ''):
        merged['detailLevel'] = 'detailed'
    else:
        merged['detailLevel'] = 'short'
    if _SCHEDULE_RE.search(query or ''):
        merged['scheduleChecked'] = False
        merged['scheduleNote'] = (
            'Schedule fit has not been checked. Do not claim the '
            'course fits their timetable. Direct them to advising.'
        )
        merged['advisingResourceName'] = _REDIRECT_RESULT['resourceName']
        merged['advisingUrl'] = _REDIRECT_RESULT['url']
    return merged


def _leftover_courses() -> list[dict[str, Any]]:
    """Returns mock leftover-requirement courses (audit stand-in).

    Returns:
        Catalog rows still required in the mock audit.
    """
    return [
        _lookup_course(code)
        for code in _AUDIT_RESULT['missingCourses']
    ]


def _rank_with_embeddings(
    embedding_provider: EmbeddingProvider,
    interest: str,
    leftover: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Ranks leftover courses with Vertex embeddings and cosine similarity.

    Args:
        embedding_provider: Live embedding client.
        interest: Student topic.
        leftover: Mock leftover-requirement courses.

    Returns:
        The same courses, best match first, with matchScore set.
    """
    query_vector = embedding_provider.embed(interest, task=TASK_QUERY)
    ranked: list[dict[str, Any]] = []
    for course in leftover:
        text = _course_embed_text(course)
        doc_vector = embedding_provider.embed(text, task=TASK_DOCUMENT)
        item = dict(course)
        item['matchScore'] = round(_cosine(query_vector, doc_vector), 4)
        ranked.append(item)
    ranked.sort(key=lambda row: row['matchScore'], reverse=True)
    return ranked


def _course_embed_text(course: dict[str, Any]) -> str:
    """Builds the text embedded for a leftover course.

    Args:
        course: Catalog-like row.

    Returns:
        Title, description, and skills as one string.
    """
    skills = course.get('skills') or []
    skill_text = ', '.join(str(skill) for skill in skills)
    return ' '.join(
        part for part in (
            str(course.get('title') or ''),
            str(course.get('description') or ''),
            skill_text,
        ) if part
    )


def _cosine(left: list[float], right: list[float]) -> float:
    """Returns cosine similarity of two equal-length vectors.

    Args:
        left: Query embedding.
        right: Course embedding.

    Returns:
        Similarity in roughly -1 to 1, or 0 if a vector is empty.
    """
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sum(a * a for a in left) ** 0.5
    right_norm = sum(b * b for b in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _course_from(arguments: dict[str, Any], query: str) -> str | None:
    """Reads a course code from tool args or the student question.

    Args:
        arguments: Tool arguments from the LLM.
        query: Original student question.

    Returns:
        A normalized course code, or None.
    """
    raw = arguments.get('course_id')
    if raw:
        return str(raw).replace(' ', '').upper()
    match = _COURSE_RE.search(query or '')
    if match:
        return match.group(1).replace(' ', '').upper()
    return None


def _lookup_course(course_id: str) -> dict[str, Any]:
    """Returns a mock catalog row for a course code.

    Args:
        course_id: Normalized course code.

    Returns:
        Course code, title, and description.
    """
    normalized = course_id.replace(' ', '').upper()
    for item in _SAMPLE_COURSES:
        if item['code'] == normalized:
            return dict(item)
    return {
        'code': normalized,
        'title': 'Sample course',
        'description': f'Mock description for {normalized}.',
    }


def _with_career_handoff(facts: dict[str, Any]) -> dict[str, Any]:
    """Adds Career Services contact fields to a course result.

    Args:
        facts: Course facts to extend.

    Returns:
        Facts plus Career Services url and a no-hallucination disclaimer.
    """
    merged = dict(facts)
    merged.update(_CAREER_REDIRECT)
    merged['careerDisclaimer'] = (
        'Explain how listed skills could apply at work as '
        'possibilities only. Then direct the student to Career '
        'Services to explore and confirm a path.'
    )
    return merged
