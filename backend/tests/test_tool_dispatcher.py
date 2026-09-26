"""Tests for MCPTools + ToolDispatcher with fake repositories."""

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
