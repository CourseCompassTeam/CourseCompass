"""Tests for the local mock query pipeline."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.orchestration.mock_query import answer_query
from app.schemas.query import QueryRequest


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


def _provider(tool: str | None, arguments: dict | None = None,
              redirect: bool = False, message: str = 'Mock reply.') -> MagicMock:
    provider = MagicMock()
    provider.choose_tool.return_value = {
        'tool': tool,
        'arguments': arguments or {},
        'redirect': redirect,
    }
    provider.phrase_response.return_value = message
    return provider


def test_query_request_keeps_the_latest_history_turns():
    turns = [{'role': 'student', 'text': f'q{index}'} for index in range(8)]
    body = QueryRequest(query='next', history=turns)
    assert [turn.text for turn in body.history] == [
        'q2', 'q3', 'q4', 'q5', 'q6', 'q7',
    ]


def test_query_request_keeps_the_latest_history_turns():
    turns = [{'role': 'student', 'text': f'q{index}'} for index in range(8)]
    body = QueryRequest(query='next', history=turns)
    assert [turn.text for turn in body.history] == [
        'q2', 'q3', 'q4', 'q5', 'q6', 'q7',
    ]


def test_answer_query_passes_history_and_hides_it_from_the_client():
    provider = _provider('get_course_description', {'course_id': 'MSCC 697'})
    history = [
        {'role': 'student', 'text': 'What is class 697?'},
        {'role': 'assistant', 'text': 'MSCC 697 is research methods.'},
    ]
    response = answer_query(
        provider,
        'What are its prerequisites?',
        history=history,
    )
    provider.choose_tool.assert_called_once()
    assert provider.choose_tool.call_args.args[2] == history
    facts = provider.phrase_response.call_args.args[0]
    assert facts['conversationHistory'] == history
    assert 'conversationHistory' not in response.content


def test_answer_query_returns_audit_facts():
    provider = _provider('audit_degree', message='You have 6 credits left.')
    response = answer_query(provider, 'How many credits do I still need?')
    assert response.type == 'audit'
    assert response.content['creditsRemaining'] == 9
    assert response.content['requirementsMet'] is False
    assert response.content['missingCourses'] == [
        'CS501', 'CS502', 'CS510',
    ]
    assert response.content['message'] == 'You have 6 credits left.'
    provider.phrase_response.assert_called_once()


def test_answer_query_redirects_out_of_scope():
    provider = _provider(
        None,
        arguments={'reason': 'financial_aid'},
        redirect=True,
        message='Please contact an advisor.',
    )
    response = answer_query(provider, 'How do I apply for financial aid?')
    assert response.type == 'redirect'
    assert response.content['url'] == 'https://example.com/advising'
    assert response.content['reason'] == 'financial_aid'


def test_answer_query_combines_course_and_career():
    provider = _provider(
        'get_career_services',
        message='CS502 covers software systems. Confirm career fit '
                'with Career Services.',
    )
    response = answer_query(
        provider,
        'Can you tell me about course CS502 and how it applies to '
        'my future career?',
    )
    assert response.type == 'recommendation'
    assert response.content['courses'][0]['code'] == 'CS502'
    assert response.content['resourceName'] == 'Career Services'
    assert response.content['url'] == (
        'https://example.com/career-services'
    )
    assert 'careerDisclaimer' in response.content


def test_recommend_ranks_with_real_embedding_provider():
    llm = _provider(
        'recommend_courses',
        arguments={'interest': 'software design'},
        message='CS502 is the closest match.',
    )
    embeddings = MagicMock()

    def _embed(text: str, task: str = 'RETRIEVAL_QUERY') -> list[float]:
        lowered = text.lower()
        if 'software design' in lowered or 'software systems' in lowered:
            return [1.0, 0.0]
        if 'algorithm' in lowered:
            return [0.4, 0.6]
        return [0.0, 1.0]

    embeddings.embed.side_effect = _embed
    response = answer_query(
        llm,
        'What course can I take if I like software design?',
        embedding_provider=embeddings,
    )
    codes = [course['code'] for course in response.content['courses']]
    assert codes[0] == 'CS502'
    assert response.content['searchMethod'] == 'gemini-embedding-001'
    assert embeddings.embed.call_count >= 2


def test_answer_query_sets_detailed_when_student_asks():
    provider = _provider(
        'recommend_courses',
        arguments={'interest': 'software design'},
        message='Detailed CS502 reply.',
    )
    response = answer_query(
        provider,
        'Recommend a course about software design if it fits my '
        'schedule. Please provide more detail.',
    )
    assert response.content['detailLevel'] == 'detailed'
    assert response.content['scheduleChecked'] is False
    assert response.content['advisingUrl'] == (
        'https://example.com/advising'
    )
    assert response.content['studentInterest'] == 'software design'


def test_answer_query_course_includes_career_handoff():
    provider = _provider(
        'get_course_description',
        arguments={'course_id': 'CS502'},
        message='CS502 builds system design skills.',
    )
    response = answer_query(provider, 'What is course CS502 about?')
    assert response.type == 'recommendation'
    assert response.content['courses'][0]['code'] == 'CS502'
    assert response.content['url'] == (
        'https://example.com/career-services'
    )


def test_next_term_catalog_question_lists_offerings():
    provider = _provider(None, redirect=True, message='Listed.')
    dispatcher = MagicMock()
    dispatcher.dispatch.return_value = {
        'nextTerm': {'name': '2026 FALL 8W2'},
        'courses': [{'code': 'MSSE 615', 'title': 'Society'}],
    }
    response = answer_query(
        provider,
        'What courses are offered next term?',
        tool_dispatcher=dispatcher,
        history=[{
            'role': 'assistant',
            'text': 'MSES 602 Introduction to DevOps Engineering',
        }],
    )
    assert dispatcher.dispatch.call_args.args[0] == 'list_term_offerings'
    assert response.content['courses'][0]['code'] == 'MSSE 615'
    assert 'scheduleChecked' not in response.content


def test_this_offered_uses_the_course_from_history():
    provider = _provider(None, redirect=True, message='Not offered.')
    dispatcher = MagicMock()
    dispatcher.dispatch.return_value = {
        'courses': [{
            'code': 'MSES 602',
            'title': 'DevOps',
            'offeredTerms': [],
            'offeredNextTerm': False,
        }],
        'nextTerm': {'name': '2026 FALL 8W2'},
    }
    response = answer_query(
        provider,
        'Is this offered next term?',
        tool_dispatcher=dispatcher,
        history=[{
            'role': 'assistant',
            'text': 'MSES 602 Introduction to DevOps Engineering',
        }],
    )
    tool, _student, arguments = dispatcher.dispatch.call_args.args
    assert tool == 'get_course_description'
    assert arguments['course_id'] == 'MSES602'
    assert response.content['courses'][0]['offeredNextTerm'] is False
    assert 'scheduleChecked' not in response.content


def test_instead_question_audits_even_when_history_names_a_course():
    provider = _provider('get_course_description', message='See advising.')
    dispatcher = MagicMock()
    dispatcher.dispatch.return_value = {
        'programName': 'Master of Science - Software Engineering',
        'leadCourseNotOfferedNextTerm': True,
        'leadCourse': {'code': 'MSSE 601', 'offeredTerms': []},
        'advisingUrl': 'https://example.com/advising',
        'nextCourses': [],
    }
    response = answer_query(
        provider,
        'so I can\'t take it since it is not offered next term. '
        'What coureses can I take instead?',
        tool_dispatcher=dispatcher,
        history=[{
            'role': 'assistant',
            'text': 'MSSE 601 Software Engineer Fundamentals',
        }],
    )
    assert dispatcher.dispatch.call_args.args[0] == 'audit_degree'
    assert response.type == 'audit'
    assert response.content['advisingUrl'] == 'https://example.com/advising'


def test_what_is_offered_lists_the_term_not_the_history_course():
    provider = _provider('get_course_description', message='Listed.')
    dispatcher = MagicMock()
    dispatcher.dispatch.return_value = {
        'nextTerm': {'name': '2026 FALL 8W2'},
        'courses': [{'code': 'MSSE 615', 'title': 'Society'}],
    }
    answer_query(
        provider,
        'so what is offered next term?',
        tool_dispatcher=dispatcher,
        history=[{
            'role': 'assistant',
            'text': 'MSSE 601 Software Engineer Fundamentals',
        }],
    )
    assert dispatcher.dispatch.call_args.args[0] == 'list_term_offerings'


def test_third_and_fourth_questions_include_milestones():
    provider = _provider(
        'get_course_description',
        arguments={'course_id': 'MSSE 601'},
        message='601, then start a portfolio.',
    )

    def _dispatch(tool, student_id, arguments):
        del student_id, arguments
        if tool == 'get_next_milestones':
            return {
                'milestones': [{
                    'label': 'Foundations',
                    'nextActions': ['Start a portfolio repository'],
                }],
            }
        return {
            'courses': [{
                'code': 'MSSE 601',
                'title': 'Fundamentals',
            }],
        }

    dispatcher = MagicMock()
    dispatcher.dispatch.side_effect = _dispatch
    third = answer_query(
        provider,
        'What is MSSE 601 about?',
        tool_dispatcher=dispatcher,
        question_number=3,
    )
    assert third.content['milestones'][0]['label'] == 'Foundations'
    assert third.content['offerMilestones'] is True

    fourth = answer_query(
        provider,
        'What is MSSE 601 about?',
        tool_dispatcher=dispatcher,
        question_number=4,
    )
    assert fourth.content['milestones'][0]['label'] == 'Foundations'

    second = answer_query(
        provider,
        'What is MSSE 601 about?',
        tool_dispatcher=dispatcher,
        question_number=2,
    )
    assert 'milestones' not in second.content


def test_syllabus_follow_up_uses_the_history_course():
    provider = _provider(None, redirect=True, message='From the syllabus.')
    dispatcher = MagicMock()
    dispatcher.dispatch.return_value = {
        'courses': [{
            'code': 'MSSE 692',
            'title': 'Practicum I',
            'syllabusText': 'Weekly topics: Week 1, project initiation.',
        }],
    }
    response = answer_query(
        provider,
        'Can you provide more syllabus information about this class '
        'and the type of assignment?',
        tool_dispatcher=dispatcher,
        history=[{
            'role': 'assistant',
            'text': 'MSSE 692 Software Engineering Practicum I',
        }],
    )
    assert dispatcher.dispatch.call_args.args[0] == 'get_course_description'
    assert dispatcher.dispatch.call_args.args[2]['course_id'] == 'MSSE692'
    assert response.content['summarizeSyllabus'] is True
    assert response.content['detailLevel'] == 'detailed'


def test_post_query_uses_mock_pipeline():
    app = create_app(_settings())
    app.state.llm_provider = _provider(
        'audit_degree',
        message='You have 6 credits remaining.',
    )
    client = TestClient(app)
    response = client.post(
        '/api/v1/query',
        json={'query': 'How many credits do I still need?'},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['type'] == 'audit'
    assert body['content']['creditsRemaining'] == 9
    assert body['content']['message'] == 'You have 6 credits remaining.'
    assert body['id']
    assert body['timestamp']
