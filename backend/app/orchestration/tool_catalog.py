"""Static tool definitions exposed to the LLM provider.

These describe ``MCPTools`` methods. The LLM may only choose from this
list. ``student_id`` is never a tool argument — the server injects it in
``ToolDispatcher`` (QA-03).
"""

from __future__ import annotations

from typing import Any

# Sentinel tool: out-of-scope questions must route here (QA-02).
REDIRECT_TOOL = 'redirect_out_of_scope'

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        'name': 'audit_degree',
        'description': (
            'Return the student degree audit: credits completed, credits '
            'remaining, and missing required courses.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {},
            'additionalProperties': False,
        },
    },
    {
        'name': 'get_course_description',
        'description': (
            'Return a course description and the advising URL for a '
            'specific course.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {
                'course_id': {
                    'type': 'string',
                    'description': 'Course code or ID, e.g. CS501.',
                },
            },
            'required': ['course_id'],
            'additionalProperties': False,
        },
    },
    {
        'name': 'recommend_courses',
        'description': (
            'Recommend courses that fit the student interests and degree '
            'requirements.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {
                'interest': {
                    'type': 'string',
                    'description': 'Topic or interest stated by the student.',
                },
            },
            'required': ['interest'],
            'additionalProperties': False,
        },
    },
    {
        'name': 'build_schedule',
        'description': (
            'Propose a term course schedule the student can export.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {},
            'additionalProperties': False,
        },
    },
    {
        'name': 'get_advisor_contact',
        'description': (
            'Return advising contact information when the chatbot cannot '
            'answer.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {},
            'additionalProperties': False,
        },
    },
    {
        'name': 'get_career_services',
        'description': (
            'Route career-related questions to Career Services and return '
            'the contact URL.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {},
            'additionalProperties': False,
        },
    },
    {
        'name': 'get_next_milestones',
        'description': (
            'Return non-course milestones appropriate for the student stage.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {},
            'additionalProperties': False,
        },
    },
    {
        'name': REDIRECT_TOOL,
        'description': (
            'Use when the question is out of scope (financial aid, profile '
            'changes, medical, legal, or anything not covered by the other '
            'tools). Never invent an answer.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {
                'reason': {
                    'type': 'string',
                    'description': 'Short reason the query is out of scope.',
                },
            },
            'required': ['reason'],
            'additionalProperties': False,
        },
    },
]
