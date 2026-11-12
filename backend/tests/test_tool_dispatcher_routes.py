"""Routing tests for ToolDispatcher: each intent calls the matching tool."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.orchestration.tool_dispatcher import ToolDispatcher
from app.orchestration.intent_router import IntentRouter
from app.orchestration.response_assembler import ResponseAssembler
from app.ingestion.data_source import DataSource


@pytest.fixture
def tools():
    return MagicMock()


@pytest.fixture
def dispatcher(tools):
    return ToolDispatcher(tools)


def test_audit_degree_passes_program_name(dispatcher, tools):
    dispatcher.dispatch('audit_degree', 'stu-1', {'program_name': 'MSSE'})

    tools.audit_degree.assert_called_once_with('stu-1', 'MSSE')


def test_audit_degree_without_arguments(dispatcher, tools):
    dispatcher.dispatch('audit_degree', 'stu-1', {})

    tools.audit_degree.assert_called_once_with('stu-1', None)


def test_course_description_passes_course_id(dispatcher, tools):
    dispatcher.dispatch('get_course_description', 'stu-1', {'course_id': 'MSSE 635'})

    tools.get_course_description.assert_called_once_with('stu-1', 'MSSE 635')


def test_list_term_offerings_defaults_scope_to_next(dispatcher, tools):
    dispatcher.dispatch('list_term_offerings', 'stu-1', None)

    tools.list_term_offerings.assert_called_once_with('stu-1', 'next')


def test_list_term_offerings_uses_given_scope(dispatcher, tools):
    dispatcher.dispatch('list_term_offerings', 'stu-1', {'scope': 'all'})

    tools.list_term_offerings.assert_called_once_with('stu-1', 'all')


def test_recommend_courses_passes_interest(dispatcher, tools):
    dispatcher.dispatch('recommend_courses', 'stu-1', {'interest': 'security'})

    tools.recommend_courses.assert_called_once_with('stu-1', 'security')


def test_build_schedule_routes_to_tool(dispatcher, tools):
    dispatcher.dispatch('build_schedule', 'stu-1', {})

    tools.build_schedule.assert_called_once_with('stu-1')


def test_advisor_and_career_routes(dispatcher, tools):
    dispatcher.dispatch('get_advisor_contact', 'stu-1', {})
    dispatcher.dispatch('get_career_services', 'stu-1', {})

    tools.get_advisor_contact.assert_called_once_with('stu-1')
    tools.get_career_services.assert_called_once_with('stu-1')


def test_milestones_passes_interest(dispatcher, tools):
    dispatcher.dispatch('get_next_milestones', 'stu-1', {'interest': 'cloud'})

    tools.get_next_milestones.assert_called_once_with('stu-1', 'cloud')


def test_unknown_intent_returns_advising_redirect(dispatcher):
    result = dispatcher.dispatch('launch_rocket', 'stu-1', {})

    assert result['reason'] == 'unknown_tool:launch_rocket'
    assert result['url'] == 'https://example.com/advising'


def test_stub_interfaces_are_not_implemented():
    with pytest.raises(NotImplementedError):
        IntentRouter().route('hello')
    with pytest.raises(NotImplementedError):
        ResponseAssembler().assemble('audit_degree', {})


def test_data_source_is_abstract():
    with pytest.raises(TypeError):
        DataSource()
