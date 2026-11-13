"""Tests for the scripted e2e LLM provider and its production guard."""

from __future__ import annotations

import pytest

from app.orchestration.fake_llm_provider import FAKE_REPLY
from app.orchestration.fake_llm_provider import FakeLLMProvider
from app.orchestration.provider_factory import create_llm_provider
from app.orchestration.tool_catalog import TOOL_DEFINITIONS
from tests.test_llm_provider import _settings


def _choose(query: str):
    return FakeLLMProvider().choose_tool(query, TOOL_DEFINITIONS)


@pytest.mark.parametrize('query, tool', [
    ('What do I still need to graduate?', 'audit_degree'),
    ('How many credits do I have left?', 'audit_degree'),
    ('How do I reach my advisor?', 'get_advisor_contact'),
    ('Can career services review my resume?', 'get_career_services'),
    ('What milestone am I at?', 'get_next_milestones'),
])
def test_keywords_pick_a_tool(query, tool):
    choice = _choose(query)

    assert choice == {'tool': tool, 'arguments': {}, 'redirect': False}


@pytest.mark.parametrize('query', [
    'Tell me about MSSE 635',
    'tell me about msse-635',
    'What is MSSE635 about? Does it count toward my degree?',
])
def test_course_code_picks_course_description(query):
    choice = _choose(query)

    assert choice['tool'] == 'get_course_description'
    assert choice['arguments'] == {'course_id': 'MSSE 635'}


def test_unmatched_query_redirects():
    choice = _choose('Can I get more financial aid?')

    assert choice['redirect'] is True
    assert choice['tool'] is None


def test_phrase_response_is_fixed():
    assert FakeLLMProvider().phrase_response({'any': 'facts'}) == FAKE_REPLY


@pytest.mark.parametrize('environment', ['test', 'local', 'TEST'])
def test_factory_builds_fake_outside_production(environment):
    settings = _settings(llm_provider='fake', environment=environment)

    assert isinstance(create_llm_provider(settings), FakeLLMProvider)


@pytest.mark.parametrize('environment', ['production', 'prod', 'staging', ''])
def test_factory_refuses_fake_elsewhere(environment):
    settings = _settings(llm_provider='fake', environment=environment)

    with pytest.raises(ValueError, match='only allowed'):
        create_llm_provider(settings)
