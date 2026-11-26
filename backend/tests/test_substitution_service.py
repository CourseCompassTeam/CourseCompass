"""Unit tests for SubstitutionService with a fake database and audit."""

from __future__ import annotations

import pytest

from app.api.errors import ApiError
from app.repositories.connection import Database
from app.services.substitution_service import SubstitutionService

STUDENT = {'student_id': 'stu-1', 'clerk_user_id': 'user_1'}
REQUIRED = {'course_id': 'c-req', 'code': 'MSSE 635'}
SUBSTITUTE = {'course_id': 'c-sub', 'code': 'MSES 602'}


class FakeResult:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class FakeConnection:
    def __init__(self, database):
        self._database = database

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self._database.statements.append((sql, params))
        return self._database.next_result()

    def commit(self):
        self._database.commits += 1


class FakeDatabase(Database):
    """Replays queued results in order and records every statement."""

    def __init__(self, results=None):
        super().__init__('postgresql://fake')
        self.results = list(results or [])
        self.statements = []
        self.commits = 0

    def next_result(self):
        return self.results.pop(0) if self.results else FakeResult()

    def connect(self):
        return FakeConnection(self)


class FakeAudit:
    def __init__(self, result):
        self.result = result

    def audit(self, student_id):
        return self.result


class FakeAuditRepo:
    def __init__(self, student=STUDENT):
        self.student = student

    def get_student(self, clerk_user_id):
        return self.student


def _audit_result(matches, transcript=None, substitutions=None):
    return {
        'requirementMatches': matches,
        'requiredCourses': [
            {'code': 'MSSE 635', 'title': 'Software Architecture', 'credits': 3},
            {'code': 'MSSE 692', 'title': 'Practicum', 'credits': 3},
        ],
        'transcriptCourses': transcript or [],
        'substitutions': substitutions or [],
    }


@pytest.fixture
def make_service():
    def build(database=None, audit_result=None, student=STUDENT,
              courses=None, taken=None):
        service = SubstitutionService(database or FakeDatabase())
        service._audit_repo = FakeAuditRepo(student)
        service._audit = FakeAudit(audit_result or _audit_result([
            {'code': 'MSSE 635', 'status': 'missing'},
            {'code': 'MSSE 692', 'status': 'direct'},
        ]))
        courses = courses if courses is not None else {
            'MSSE 635': REQUIRED, 'MSES 602': SUBSTITUTE,
        }
        service._course = lambda code: courses.get(code.upper())
        taken = taken if taken is not None else {'c-sub'}
        service._taken_course_ids = lambda student_id: taken
        return service
    return build


def test_declare_inserts_substitution_and_returns_review(make_service):
    database = FakeDatabase()
    service = make_service(database)

    result = service.declare('user_1', 'MSSE 635', 'MSES 602')

    assert database.commits == 1
    sql, params = database.statements[0]
    assert 'INSERT INTO student_substitutions' in sql
    assert params == ('stu-1', 'c-req', 'c-sub')
    assert result['requirements'] == [
        {'code': 'MSSE 635', 'title': 'Software Architecture', 'credits': 3}
    ]


def test_declare_rejects_unknown_course(make_service):
    service = make_service(courses={'MSSE 635': REQUIRED})

    with pytest.raises(ApiError) as caught:
        service.declare('user_1', 'MSSE 635', 'NOPE 000')

    assert caught.value.status == 404


def test_declare_rejects_same_course(make_service):
    service = make_service(courses={'MSSE 635': REQUIRED, 'X': REQUIRED})

    with pytest.raises(ApiError) as caught:
        service.declare('user_1', 'MSSE 635', 'X')

    assert caught.value.status == 400
    assert 'cannot substitute for itself' in caught.value.message


def test_declare_rejects_course_not_required_by_program(make_service):
    service = make_service(audit_result=_audit_result([
        {'code': 'MSSE 692', 'status': 'direct'},
    ]))

    with pytest.raises(ApiError) as caught:
        service.declare('user_1', 'MSSE 635', 'MSES 602')

    assert caught.value.status == 400
    assert 'not required for your program' in caught.value.message


def test_declare_rejects_already_completed_requirement(make_service):
    service = make_service(audit_result=_audit_result([
        {'code': 'MSSE 635', 'status': 'direct'},
    ]))

    with pytest.raises(ApiError) as caught:
        service.declare('user_1', 'MSSE 635', 'MSES 602')

    assert caught.value.status == 400
    assert 'already completed' in caught.value.message


def test_declare_rejects_substitute_not_on_transcript(make_service):
    service = make_service(taken=set())

    with pytest.raises(ApiError) as caught:
        service.declare('user_1', 'MSSE 635', 'MSES 602')

    assert caught.value.status == 400
    assert 'not on your transcript' in caught.value.message


def test_remove_deletes_and_returns_review(make_service):
    database = FakeDatabase(results=[FakeResult(row={'substitution_id': 's-1'})])
    service = make_service(database)

    service.remove('user_1', 's-1')

    assert database.commits == 1
    assert database.statements[0][1] == ('s-1', 'stu-1')


def test_remove_missing_substitution_is_not_found(make_service):
    service = make_service(FakeDatabase(results=[FakeResult(row=None)]))

    with pytest.raises(ApiError) as caught:
        service.remove('user_1', 'missing')

    assert caught.value.status == 404


def test_review_skips_directly_completed_requirements(make_service):
    service = make_service(audit_result=_audit_result(
        [
            {'code': 'MSSE 635', 'status': 'missing'},
            {'code': 'MSSE 692', 'status': 'direct'},
        ],
        transcript=[{'code': 'MSES 602'}],
        substitutions=[{'requirementCode': 'MSSE 635', 'counted': True}],
    ))

    review = service.review('user_1')

    assert [item['code'] for item in review['requirements']] == ['MSSE 635']
    assert review['courses'] == [{'code': 'MSES 602'}]
    assert review['substitutions'] == [
        {'requirementCode': 'MSSE 635', 'counted': True}
    ]


def test_review_uses_empty_title_for_unknown_requirement(make_service):
    service = make_service(audit_result=_audit_result([
        {'code': 'MSSE 999', 'status': 'missing'},
    ]))

    review = service.review('user_1')

    assert review['requirements'] == [
        {'code': 'MSSE 999', 'title': '', 'credits': 0}
    ]


def test_student_lookup_fails_when_no_record(make_service):
    service = make_service(student=None)

    with pytest.raises(ApiError) as caught:
        service.review('user_unknown')

    assert caught.value.status == 404


def test_course_lookup_returns_none_without_row():
    service = SubstitutionService(FakeDatabase(results=[FakeResult(row=None)]))

    assert service._course('MSSE 635') is None


def test_course_lookup_returns_id_and_code():
    row = {'course_id': 'c-req', 'code': 'MSSE 635'}
    service = SubstitutionService(FakeDatabase(results=[FakeResult(row=row)]))

    assert service._course('msse 635') == {'course_id': 'c-req', 'code': 'MSSE 635'}


def test_taken_course_ids_collects_completed_and_in_progress():
    rows = [{'course_id': 'c-1'}, {'course_id': 'c-2'}]
    database = FakeDatabase(results=[FakeResult(rows=rows)])
    service = SubstitutionService(database)

    assert service._taken_course_ids('stu-1') == {'c-1', 'c-2'}
    assert database.statements[0][1] == ('stu-1',)
