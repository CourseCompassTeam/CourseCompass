"""Shared fixtures for backend API integration tests."""

from __future__ import annotations

from datetime import date
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.orchestration.tool_dispatcher import ToolDispatcher
from app.services.audit_service import AuditService
from app.services.campus_directory_service import CampusDirectoryService
from app.services.course_catalog_service import CourseCatalogService
from app.services.student_milestone_service import StudentMilestoneService
from app.tools.mcp_tools import MCPTools


class ScriptedLLM:
    """Returns a fixed tool choice and phrase for each request."""

    def __init__(self):
        self.choice = {
            'tool': 'audit_degree',
            'arguments': {},
            'redirect': False,
        }
        self.message = 'Integration reply.'
        self.last_facts = None

    def choose_tool(self, query, tools, history=None):
        del query, tools, history
        return dict(self.choice)

    def phrase_response(self, facts):
        self.last_facts = facts
        return self.message


class _AuditRepo:
    def __init__(self):
        self._program = {
            'program_id': 'p1',
            'name': 'Master of Science - Software Engineering',
            'total_credits_required': 36,
        }
        self._students = {
            'user_nearly_done': {
                'student_id': 's-nearly',
                'program_id': 'p1',
                'clerk_user_id': 'user_nearly_done',
                'email': 'nearly.done@example.edu',
                'full_name': 'Nearly Done',
                'status': 'active',
            },
            'user_just_started': {
                'student_id': 's-started',
                'program_id': 'p1',
                'clerk_user_id': 'user_just_started',
                'email': 'just.started@example.edu',
                'full_name': 'Just Started',
                'status': 'active',
            },
        }
        self._completed = {
            'user_nearly_done': [
                {'code': 'MSSE 601', 'credits': 3},
                {'code': 'MSSE 635', 'credits': 3},
            ],
            'user_just_started': [
                {'code': 'MSSE 601', 'credits': 3},
            ],
        }
        self._requirements = [
            {
                'code': 'MSSE 601',
                'title': 'Software Engineer Fundamentals',
                'description': 'Intro to software engineering.',
                'credits': 3,
                'category': 'core',
            },
            {
                'code': 'MSSE 635',
                'title': 'Software Architecture and Design',
                'description': 'Architecture patterns.',
                'credits': 3,
                'category': 'core',
            },
            {
                'code': 'MSSE 692',
                'title': 'Software Engineering Practicum I',
                'description': 'Capstone preparation.',
                'credits': 3,
                'category': 'core',
            },
            {
                'code': 'MSSE 696',
                'title': 'Software Engineering Practicum II',
                'description': 'Capstone completion.',
                'credits': 3,
                'category': 'core',
            },
        ]

    def get_student(self, student_id: str):
        return self._students.get(student_id)

    def get_completed_courses(self, student_id: str):
        return list(self._completed.get(student_id, []))

    def get_in_progress_courses(self, student_id: str):
        del student_id
        return []

    def get_program_requirements(self, student_id: str):
        del student_id
        return list(self._requirements)

    def get_program(self, program_id: str):
        if program_id == 'p1':
            return dict(self._program)
        return None

    def get_default_program(self):
        return dict(self._program)

    def get_program_by_name(self, name: str):
        if 'software engineering' in name.lower():
            return dict(self._program)
        return None

    def get_requirements_for_program(self, program_id: str):
        del program_id
        return list(self._requirements)


class _CatalogRepo:
    def __init__(self):
        self._courses = {
            'MSSE 601': {
                'course_id': 'c601',
                'code': 'MSSE 601',
                'title': 'Software Engineer Fundamentals',
                'description': 'Introduces the Software Engineering Body of Knowledge.',
                'credits': 3,
                'is_active': True,
            },
            'MSSE 635': {
                'course_id': 'c635',
                'code': 'MSSE 635',
                'title': 'Software Architecture and Design',
                'description': 'Architecture-centric software engineering.',
                'credits': 3,
                'is_active': True,
            },
            'MSSE 692': {
                'course_id': 'c692',
                'code': 'MSSE 692',
                'title': 'Software Engineering Practicum I',
                'description': 'Begins a distributed software system.',
                'credits': 3,
                'is_active': True,
            },
            'MSSE 696': {
                'course_id': 'c696',
                'code': 'MSSE 696',
                'title': 'Software Engineering Practicum II',
                'description': 'Completes the practicum system.',
                'credits': 3,
                'is_active': True,
            },
        }
        later = date.today() + timedelta(days=20)
        end = date.today() + timedelta(days=70)
        self._offerings = [
            {
                'code': 'MSSE 692',
                'title': 'Software Engineering Practicum I',
                'term_name': 'NEXT TERM',
                'start_date': later.isoformat(),
                'end_date': end.isoformat(),
            },
        ]
        self._syllabus = {
            'MSSE 692': [
                {
                    'code': 'MSSE 692',
                    'chunk_index': 0,
                    'chunk_text': (
                        'MSSE-692 Practicum I. Weekly topics: Week 1, '
                        'project initiation. Week 8, delivery.'
                    ),
                },
            ],
        }

    def get_course(self, course_id: str):
        matches = self.find_courses(course_id)
        return matches[0] if len(matches) == 1 else None

    def find_courses(self, course_id: str):
        needle = str(course_id or '').replace(' ', '').upper()
        found = []
        for course in self._courses.values():
            code = course['code'].replace(' ', '').upper()
            if code == needle or course['course_id'] == course_id:
                found.append(dict(course))
            elif needle.isdigit() and code.endswith(needle):
                found.append(dict(course))
        return found

    def list_programs_for_course(self, course_id: str):
        del course_id
        return ['Master of Science - Software Engineering']

    def get_prerequisites(self, course_id: str):
        if course_id == 'MSSE 696':
            return [{'code': 'MSSE 692', 'requirement_type': 'prereq'}]
        if course_id == 'MSSE 692':
            return [{'code': 'MSSE 635', 'requirement_type': 'prereq'}]
        return []

    def list_active_courses(self):
        return [dict(row) for row in self._courses.values()]

    def list_syllabus_chunks(self, course_id: str):
        for course in self._courses.values():
            if course['course_id'] == course_id or course['code'] == course_id:
                return list(self._syllabus.get(course['code'], []))
        return []

    def list_all_syllabus_chunks(self):
        rows = []
        for chunks in self._syllabus.values():
            rows.extend(chunks)
        return rows

    def list_offerings(self):
        return list(self._offerings)


class _DirectoryRepo:
    def get_advisor_contacts(self):
        return []

    def get_contacts_by_type(self, contact_type: str):
        if contact_type == 'career_services':
            return [{
                'name': 'Career Services',
                'email': 'career@example.com',
                'booking_url': 'https://example.com/career-services',
            }]
        return [{
            'name': 'Test Advisor',
            'email': 'advise@example.com',
            'booking_url': 'https://example.edu/book-advisor',
        }]


class _MilestoneRepo:
    def get_milestones(self):
        return [{
            'label': 'Capstone',
            'credit_min': 6,
            'credit_max': 36,
            'next_actions': ['Finalize your portfolio'],
        }]


class _ScheduleRepo:
    def get_schedules(self, student_id: str):
        del student_id
        return []


def _settings() -> Settings:
    return Settings(
        app_name='coursecompass-api-test',
        environment='test',
        database_url='',
        clerk_secret_key='',
        clerk_publishable_key='',
        clerk_jwks_url='',
        clerk_jwt_key='',
        clerk_issuer='',
        clerk_authorized_parties=(),
        llm_provider='',
        llm_api_key='',
        llm_model='gemini-2.5-flash',
        embedding_model='gemini-embedding-001',
        embedding_dimensions=768,
        gcp_project='',
        gcp_location='us-central1',
        cors_origins=('http://localhost:5173',),
    )


def _dispatcher() -> ToolDispatcher:
    catalog = CourseCatalogService(_CatalogRepo())
    audit = AuditService(_AuditRepo(), catalog)
    tools = MCPTools(
        audit,
        catalog,
        CampusDirectoryService(_DirectoryRepo()),
        StudentMilestoneService(_MilestoneRepo(), audit),
        schedule_repository=_ScheduleRepo(),
    )
    return ToolDispatcher(tools)


@pytest.fixture
def llm() -> ScriptedLLM:
    return ScriptedLLM()


@pytest.fixture
def client(llm: ScriptedLLM) -> TestClient:
    app = create_app(_settings())
    app.state.llm_provider = llm
    app.state.tool_dispatcher = _dispatcher()
    return TestClient(app)
