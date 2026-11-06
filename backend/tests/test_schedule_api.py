"""Route tests for the schedule builder. No database: the service is a fake."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import register_exception_handlers
from app.api.v1 import schedule as schedule_module

SCHEDULE = {
    'schedule_id': 's1',
    'student_id': 'u1',
    'status': 'draft',
    'created_at': '2026-11-04T00:00:00',
    'terms': [
        {
            'schedule_term_id': 't1',
            'schedule_id': 's1',
            'term_name': 'Spring 2027',
            'term_order': 1,
            'items': [
                {
                    'schedule_item_id': 'i1',
                    'schedule_term_id': 't1',
                    'course_id': 'c1',
                    'code': 'MSSE 601',
                    'title': 'Requirements',
                    'credits': 3,
                }
            ],
        }
    ],
}


class FakeService:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def build_draft(self, student_id, **kwargs):
        self.calls.append((student_id, kwargs))
        return self.result


class FakeRepository:
    def __init__(self, schedules=(), exported=True):
        self.schedules = list(schedules)
        self.exported = exported
        self.calls = []

    def get_schedules(self, student_id):
        self.calls.append(('get', student_id))
        return self.schedules

    def mark_exported(self, student_id, schedule_id):
        self.calls.append(('export', student_id, schedule_id))
        return self.exported


def make_client(monkeypatch, service=None, repository=None):
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(schedule_module.router)
    app.state.settings = object()
    app.state.schedule_service = service
    app.state.schedule_repository = repository
    monkeypatch.setattr(
        schedule_module,
        'resolve_student_id',
        lambda headers, settings: headers.get('x-test-user', ''),
    )
    return TestClient(app, raise_server_exceptions=False)


SIGNED_IN = {'X-Test-User': 'clerk_1'}


def code(response):
    return response.json()['error']['code']


class TestBuild:
    def test_requires_sign_in(self, monkeypatch):
        client = make_client(monkeypatch, service=FakeService({'schedule': None, 'unplaced': []}))
        response = client.post('/api/v1/schedule/build')
        assert response.status_code == 401 and code(response) == 'UNAUTHORIZED'

    def test_not_configured_is_501(self, monkeypatch):
        client = make_client(monkeypatch, service=None)
        response = client.post('/api/v1/schedule/build', headers=SIGNED_IN)
        assert response.status_code == 501 and code(response) == 'NOT_IMPLEMENTED'

    def test_returns_the_saved_schedule_and_unplaced_courses(self, monkeypatch):
        unplaced = [{'course_id': 'c9', 'code': 'MSSE 699', 'title': 'X', 'reason': 'not offered in any available term'}]
        service = FakeService({'schedule': SCHEDULE, 'unplaced': unplaced})
        response = make_client(monkeypatch, service=service).post(
            '/api/v1/schedule/build', headers=SIGNED_IN
        )
        assert response.status_code == 200
        body = response.json()
        assert body['status'] == 'success'
        assert body['schedule'] == SCHEDULE
        assert body['unplaced'] == unplaced
        assert 'message' not in body

    def test_uses_the_signed_in_student_and_the_default_when_no_body(self, monkeypatch):
        service = FakeService({'schedule': SCHEDULE, 'unplaced': []})
        make_client(monkeypatch, service=service).post('/api/v1/schedule/build', headers=SIGNED_IN)
        assert service.calls == [('clerk_1', {})]

    def test_a_student_id_in_the_body_is_ignored(self, monkeypatch):
        service = FakeService({'schedule': SCHEDULE, 'unplaced': []})
        make_client(monkeypatch, service=service).post(
            '/api/v1/schedule/build', headers=SIGNED_IN, json={'student_id': 'someone-else'}
        )
        assert service.calls == [('clerk_1', {})]

    def test_courses_per_term_is_passed_on(self, monkeypatch):
        service = FakeService({'schedule': SCHEDULE, 'unplaced': []})
        make_client(monkeypatch, service=service).post(
            '/api/v1/schedule/build', headers=SIGNED_IN, json={'courses_per_term': 3}
        )
        assert service.calls == [('clerk_1', {'max_per_term': 3})]

    @pytest.mark.parametrize('bad', [0, -1, 7, 'two', 2.5, True, None])
    def test_bad_courses_per_term_is_400(self, monkeypatch, bad):
        service = FakeService({'schedule': SCHEDULE, 'unplaced': []})
        response = make_client(monkeypatch, service=service).post(
            '/api/v1/schedule/build', headers=SIGNED_IN, json={'courses_per_term': bad}
        )
        assert response.status_code == 400 and code(response) == 'BAD_REQUEST'
        assert service.calls == []

    def test_unknown_student_is_404(self, monkeypatch):
        response = make_client(monkeypatch, service=FakeService(None)).post(
            '/api/v1/schedule/build', headers=SIGNED_IN
        )
        assert response.status_code == 404 and code(response) == 'NOT_FOUND'

    def test_nothing_placed_returns_null_schedule_with_a_message(self, monkeypatch):
        service = FakeService({'schedule': None, 'unplaced': []})
        body = make_client(monkeypatch, service=service).post(
            '/api/v1/schedule/build', headers=SIGNED_IN
        ).json()
        assert body['schedule'] is None
        assert 'not changed' in body['message']


class TestList:
    def test_requires_sign_in(self, monkeypatch):
        assert make_client(monkeypatch, repository=FakeRepository()).get('/api/v1/schedule').status_code == 401

    def test_returns_the_students_schedules_as_a_list(self, monkeypatch):
        repository = FakeRepository([SCHEDULE])
        response = make_client(monkeypatch, repository=repository).get(
            '/api/v1/schedule', headers=SIGNED_IN
        )
        assert response.status_code == 200 and response.json() == [SCHEDULE]
        assert repository.calls == [('get', 'clerk_1')]

    def test_no_schedules_is_an_empty_list(self, monkeypatch):
        response = make_client(monkeypatch, repository=FakeRepository()).get(
            '/api/v1/schedule', headers=SIGNED_IN
        )
        assert response.json() == []

    def test_not_configured_is_501(self, monkeypatch):
        assert make_client(monkeypatch).get('/api/v1/schedule', headers=SIGNED_IN).status_code == 501


class TestExport:
    def test_requires_sign_in(self, monkeypatch):
        client = make_client(monkeypatch, repository=FakeRepository())
        assert client.post('/api/v1/schedule/s1/export').status_code == 401

    def test_marks_the_schedule_for_the_signed_in_student(self, monkeypatch):
        repository = FakeRepository(exported=True)
        response = make_client(monkeypatch, repository=repository).post(
            '/api/v1/schedule/s1/export', headers=SIGNED_IN
        )
        assert response.status_code == 200
        assert response.json() == {'status': 'success', 'schedule_id': 's1', 'exported': True}
        assert repository.calls == [('export', 'clerk_1', 's1')]

    def test_unknown_or_someone_elses_schedule_is_404(self, monkeypatch):
        response = make_client(monkeypatch, repository=FakeRepository(exported=False)).post(
            '/api/v1/schedule/s1/export', headers=SIGNED_IN
        )
        assert response.status_code == 404 and code(response) == 'NOT_FOUND'
