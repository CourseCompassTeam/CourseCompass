"""Tests for MCPTools + ToolDispatcher with fake repositories."""

from datetime import date
from datetime import timedelta

from app.orchestration.mock_query import answer_query
from app.orchestration.tool_dispatcher import ToolDispatcher
from app.services.audit_service import AuditService
from app.services.campus_directory_service import CampusDirectoryService
from app.services.course_catalog_service import CourseCatalogService
from app.services.student_milestone_service import StudentMilestoneService
from app.tools.mcp_tools import MCPTools
from tests.test_audit_service import _FakeAuditRepo
from tests.test_audit_service import _FakeCatalogRepo
from tests.test_mock_query import _provider


class _FakeDirectory:
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
            'name': 'Advising',
            'email': 'advise@example.com',
            'booking_url': 'https://example.com/advising',
        }]


class _FakeMilestones:
    def get_milestones(self):
        return [{
            'label': 'Build a portfolio',
            'credit_min': 0,
            'credit_max': 36,
            'next_actions': ['Collect project work'],
        }]


class _FakeSchedules:
    def get_schedules(self, student_id: str):
        del student_id
        return []


def _dispatcher() -> ToolDispatcher:
    catalog = CourseCatalogService(_FakeCatalogRepo())
    audit = AuditService(_FakeAuditRepo(), catalog)
    tools = MCPTools(
        audit,
        catalog,
        CampusDirectoryService(_FakeDirectory()),
        StudentMilestoneService(_FakeMilestones(), audit),
        schedule_repository=_FakeSchedules(),
    )
    return ToolDispatcher(tools)


def test_shared_course_number_is_marked_ambiguous():
    class _SharedNumberRepo(_FakeCatalogRepo):
        def find_courses(self, course_id: str):
            del course_id
            return [
                {
                    'course_id': 'c1',
                    'code': 'MSCC 697',
                    'title': 'Research Methods',
                    'description': 'Research.',
                    'credits': 3,
                },
                {
                    'course_id': 'c2',
                    'code': 'MSIT 697',
                    'title': 'Other Research',
                    'description': 'Other.',
                    'credits': 3,
                },
            ]

        def list_programs_for_course(self, course_id: str):
            if course_id == 'c1':
                return ['Master of Science - Software Engineering']
            return ['Master of Science - Information Technology']

    catalog = CourseCatalogService(_SharedNumberRepo())
    audit = AuditService(_FakeAuditRepo(), catalog)
    tools = MCPTools(
        audit,
        catalog,
        CampusDirectoryService(_FakeDirectory()),
        StudentMilestoneService(_FakeMilestones(), audit),
    )
    facts = tools.get_course_description('s1', '697')
    assert facts['courseNumberAmbiguous'] is True
    assert [course['code'] for course in facts['courses']] == [
        'MSCC 697', 'MSIT 697',
    ]
    assert facts['courses'][0]['programs'] == [
        'Master of Science - Software Engineering',
    ]
    assert facts['courses'][1]['programs'] == [
        'Master of Science - Information Technology',
    ]


def test_dispatch_audit_lists_program_requirements():
    facts = _dispatcher().dispatch(
        'audit_degree',
        '',
        {'program_name': 'Master of Science - Software Engineering'},
    )
    assert facts['programName'] == (
        'Master of Science - Software Engineering'
    )
    assert facts['creditsRemaining'] == 36
    assert 'MSSE 601' in facts['missingCourses']


def test_next_course_question_uses_audit_even_if_routed_away():
    provider = _provider(
        None,
        arguments={'reason': 'too_vague'},
        redirect=True,
        message='Take MSSE 601 or MSSE 635 next.',
    )
    response = answer_query(
        provider,
        'What course should I take next?',
        tool_dispatcher=_dispatcher(),
    )
    assert response.type == 'audit'
    assert [course['code'] for course in response.content['nextCourses']] == [
        'MSSE 601', 'MSSE 635',
    ]


def test_list_term_offerings_returns_only_the_next_term():
    today = date.today()
    later = today + timedelta(days=20)
    end = today + timedelta(days=70)

    class _OfferingRepo(_FakeCatalogRepo):
        def list_offerings(self):
            return [
                {
                    'code': 'MSSE 601',
                    'title': 'Intro',
                    'term_name': 'NOW',
                    'start_date': (today - timedelta(days=10)).isoformat(),
                    'end_date': (today + timedelta(days=10)).isoformat(),
                },
                {
                    'code': 'MSES 602',
                    'title': 'DevOps',
                    'term_name': 'LATER',
                    'start_date': later.isoformat(),
                    'end_date': end.isoformat(),
                },
            ]

    catalog = CourseCatalogService(_OfferingRepo())
    tools = MCPTools(
        AuditService(_FakeAuditRepo(), catalog),
        catalog,
        CampusDirectoryService(_FakeDirectory()),
        StudentMilestoneService(_FakeMilestones(), AuditService(
            _FakeAuditRepo(), catalog
        )),
    )
    result = tools.list_term_offerings('s1', 'next')
    assert result['nextTerm']['name'] == 'LATER'
    assert result['courses'] == [{'code': 'MSES 602', 'title': 'DevOps'}]


def test_search_includes_the_named_milestone_and_current_band():
    class _Embed:
        def embed(self, text, task='RETRIEVAL_QUERY'):
            del task
            if 'internship' in text.lower():
                return [1.0, 0.0]
            return [0.0, 1.0]

    class _Milestones:
        def get_milestones(self):
            return [
                {
                    'label': 'Foundations',
                    'credit_min': 0,
                    'credit_max': 12,
                    'next_actions': ['Start a portfolio repository'],
                },
                {
                    'label': 'Internships',
                    'credit_min': 13,
                    'credit_max': 24,
                    'next_actions': ['Apply to internships'],
                },
                {
                    'label': 'Capstone',
                    'credit_min': 25,
                    'credit_max': None,
                    'next_actions': ['Prepare for your practicum'],
                },
            ]

    catalog = CourseCatalogService(_FakeCatalogRepo())
    audit = AuditService(_FakeAuditRepo(), catalog)
    tools = MCPTools(
        audit,
        catalog,
        CampusDirectoryService(_FakeDirectory()),
        StudentMilestoneService(_Milestones(), audit),
        embedding_provider=_Embed(),
    )
    found = tools.get_next_milestones('', 'internships')
    assert [item['label'] for item in found['milestones']] == [
        'Internships',
        'Foundations',
    ]
    recommended = tools.recommend_courses('', 'software design')
    assert recommended['milestones'] == []
    assert len(recommended['courses']) == 1


def test_syllabus_text_ranks_a_course_the_description_misses():
    from app.tools.mcp_tools import _rank_with_embeddings

    class _Embed:
        def embed(self, text, task='RETRIEVAL_QUERY'):
            del task
            if 'penetration' in text.lower():
                return [1.0, 0.0]
            return [0.0, 1.0]

    ranked = _rank_with_embeddings(
        _Embed(),
        'penetration testing',
        [
            {
                'code': 'MSSE 601',
                'title': 'Fundamentals',
                'description': 'UML and agile.',
            },
            {
                'code': 'MSSE 642',
                'title': 'Assurance',
                'description': 'Software testing tools.',
            },
        ],
        {
            'MSSE 642': (
                'Week 7, penetration testing using Kali and Metasploit.'
            ),
        },
    )
    assert ranked[0]['code'] == 'MSSE 642'
    assert 'penetration testing' in ranked[0]['syllabusText']


def test_course_description_includes_the_full_syllabus():
    class _SyllabusRepo(_FakeCatalogRepo):
        def find_courses(self, course_id: str):
            del course_id
            return [{
                'course_id': 'c692',
                'code': 'MSSE 692',
                'title': 'Practicum I',
                'description': 'Catalog blurb.',
                'credits': 3,
            }]

        def list_all_syllabus_chunks(self):
            return [
                {
                    'code': 'MSSE 692',
                    'chunk_index': 0,
                    'chunk_text': 'Applied practicum overview.',
                },
                {
                    'code': 'MSSE 692',
                    'chunk_index': 2,
                    'chunk_text': (
                        'Weekly topics: Week 1, project initiation. '
                        'Week 8, delivery and presentation.'
                    ),
                },
            ]

    catalog = CourseCatalogService(_SyllabusRepo())
    tools = MCPTools(
        AuditService(_FakeAuditRepo(), catalog),
        catalog,
        CampusDirectoryService(_FakeDirectory()),
        StudentMilestoneService(_FakeMilestones(), AuditService(
            _FakeAuditRepo(), catalog
        )),
    )
    facts = tools.get_course_description('s1', 'MSSE 692')
    text = facts['courses'][0]['syllabusText']
    assert 'Applied practicum overview.' in text
    assert 'Week 8, delivery and presentation.' in text


def test_answer_query_uses_live_dispatcher_for_audit():
    provider = _provider(
        'audit_degree',
        arguments={
            'program_name': 'Master of Science - Software Engineering',
        },
        message='MSSE requires 36 credits.',
    )
    response = answer_query(
        provider,
        'What are the requirements for the Master of Science - '
        'Software Engineering degree?',
        tool_dispatcher=_dispatcher(),
    )
    assert response.type == 'audit'
    assert response.content['creditsRequired'] == 36
    assert 'MSSE 635' in response.content['missingCourses']
    assert response.content['message'] == 'MSSE requires 36 credits.'
