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
            'Return degree requirements or a student audit: program name, '
            'credits completed, credits remaining, required courses, and '
            'the prerequisite order. Use this when the student asks what '
            'a degree requires, which courses are left, what order to '
            'take them in, which course is needed first, or what course '
            'they should take next.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {
                'program_name': {
                    'type': 'string',
                    'description': (
                        'Degree name when the student names a program, '
                        'e.g. Master of Science - Software Engineering.'
                    ),
                },
            },
            'additionalProperties': False,
        },
    },
    {
        'name': 'get_course_description',
        'description': (
            'Return a course description, when it is offered, and the '
            'advising URL. Use this when the student asks about one '
            'course, including whether that course is offered next term.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {
                'course_id': {
                    'type': 'string',
                    'description': (
                        'Course code or number, e.g. MSCC 697 or 697.'
                    ),
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
            'requirements. Also returns milestones that match the '
            'interest or the student\'s current stage.'
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
        'name': 'list_term_offerings',
        'description': (
            'List the courses published for the next term, or the '
            'current term when the student says this term. Use this '
            'when they ask which courses are offered, not whether one '
            'named course fits their personal timetable.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {
                'scope': {
                    'type': 'string',
                    'description': 'next or current. Default next.',
                },
            },
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
            'Return non-course milestones for the student stage. Use '
            'this for next steps outside class, internships, a resume, '
            'or a portfolio. Pass interest when they name a topic.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {
                'interest': {
                    'type': 'string',
                    'description': (
                        'Topic from the question, such as internships.'
                    ),
                },
            },
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
