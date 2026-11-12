"""Unit tests for TranscriptStore mapping and replace logic, with fakes."""

from __future__ import annotations

import pytest

from app.api.errors import ApiError
from app.ingestion.transcript_store import TranscriptStore
from app.ingestion.transcript_store import status_for_grade
from app.ingestion.transcript_store import term_label
from app.repositories.connection import Database

STUDENT = {'student_id': 'stu-1', 'clerk_user_id': 'user_1', 'email': 'a@b.c'}
CATALOG_ROWS = [
    {'course_id': 'c-635', 'code': 'MSSE 635', 'title': 'Architecture', 'credits': 3},
    {'course_id': 'c-601', 'code': 'MSSE 601', 'title': 'Intro', 'credits': 3},
]


class FakeResult:
    def __init__(self, rows=None):
        self._rows = rows or []

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
        self._database.statements.append((sql.strip(), params))
        if self._database.results:
            return FakeResult(self._database.results.pop(0))
        return FakeResult()

    def commit(self):
        self._database.commits += 1


class FakeDatabase(Database):
    def __init__(self, results=None):
        super().__init__('postgresql://fake')
        self.results = list(results or [])
        self.statements = []
        self.commits = 0

    def connect(self):
        return FakeConnection(self)


class FakeAudit:
    def __init__(self, student=STUDENT):
        self.student = student

    def get_student(self, clerk_user_id):
        return self.student


def _store(database, student=STUDENT):
    store = TranscriptStore(database)
    store._audit = FakeAudit(student)
    return store


def _statements(database, prefix):
    return [params for sql, params in database.statements if sql.startswith(prefix)]


@pytest.mark.parametrize('grade,expected', [
    ('A', 'completed'),
    ('b+', 'completed'),
    ('CR', 'completed'),
    ('IP', 'in_progress'),
    ('F', None),
    ('W', None),
    ('Z', None),
    ('', None),
])
def test_status_for_grade(grade, expected):
    assert status_for_grade(grade) == expected


def test_term_label_compacts_dates_and_handles_blank():
    assert term_label('08/26/24-10/20/24') == '082624-102024'
    assert term_label('') == 'unknown'
    assert len(term_label('x' * 40)) == 20


def test_unknown_student_is_not_found():
    store = _store(FakeDatabase(), student=None)

    with pytest.raises(ApiError) as caught:
        store.replace_for_clerk_user('user_x', [])

    assert caught.value.status == 404


def test_no_catalog_match_keeps_existing_transcript():
    database = FakeDatabase(results=[[]])
    store = _store(database)

    with pytest.raises(ApiError) as caught:
        store.replace_for_clerk_user(
            'user_1', [{'code': 'NOPE 1', 'grade': 'A', 'dates': ''}])

    assert caught.value.status == 400
    assert not _statements(database, 'DELETE FROM transcript_entries')


def test_replace_saves_matches_and_reports_skips():
    database = FakeDatabase(results=[CATALOG_ROWS, [], []])
    store = _store(database)

    result = store.replace_for_clerk_user('user_1', [
        {'code': 'MSSE 635', 'grade': 'A', 'dates': '01/01/25-03/01/25'},
        {'code': 'MSSE 601', 'grade': 'F', 'dates': ''},
        {'code': 'MSSE 999', 'grade': 'A', 'dates': ''},
    ])

    assert result['saved'] == [{
        'code': 'MSSE 635', 'status': 'completed',
        'term': '010125-030125', 'grade': 'A',
    }]
    assert {'code': 'MSSE 601', 'reason': 'grade F is not stored'} in result['skipped']
    assert {'code': 'MSSE 999', 'reason': 'not in course catalog'} in result['skipped']
    assert database.commits == 1
    inserts = _statements(database, 'INSERT INTO transcript_entries')
    assert inserts == [('stu-1', 'c-635', '010125-030125', 'completed')]


def test_retake_keeps_completed_over_in_progress():
    database = FakeDatabase(results=[CATALOG_ROWS, [], []])
    store = _store(database)

    result = store.replace_for_clerk_user('user_1', [
        {'code': 'MSSE 635', 'grade': 'IP', 'dates': ''},
        {'code': 'MSSE 635', 'grade': 'B', 'dates': ''},
    ])

    assert [entry['status'] for entry in result['saved']] == ['completed']


def test_stale_substitutions_are_cleared_in_same_transaction():
    stale = [{
        'substitution_id': 's-1',
        'requirement_code': 'MSSE 601',
        'substitute_code': 'MSES 602',
    }]
    database = FakeDatabase(results=[CATALOG_ROWS, stale, []])
    store = _store(database)

    result = store.replace_for_clerk_user('user_1', [
        {'code': 'MSSE 635', 'grade': 'A', 'dates': ''},
    ])

    assert result['cleared'] == [
        {'requirementCode': 'MSSE 601', 'substituteCode': 'MSES 602'}
    ]
    assert _statements(database, 'DELETE FROM student_substitutions') == [
        (['s-1'],)
    ]
    assert database.commits == 1
