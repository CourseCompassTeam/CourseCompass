"""Unit tests for grade mapping and transcript overwrite."""

from app.api.errors import ApiError
from app.ingestion.transcript_store import status_for_grade
from app.ingestion.transcript_store import term_label


def test_status_for_grade_maps_passing_and_in_progress():
    assert status_for_grade('A') == 'completed'
    assert status_for_grade('ip') == 'in_progress'
    assert status_for_grade('W') is None
    assert status_for_grade('F') is None


def test_term_label_fits_varchar_20():
    label = term_label('01/15/24-03/10/24')
    assert label == '011524-031024'
    assert len(label) <= 20


class _FakeStore:
    """In-memory stand-in for TranscriptStore.replace_for_clerk_user."""

    def __init__(self):
        self.students = {
            'user_3K1pC0YksFOD8HW1dIiz4ITDt90': {
                'student_id': 's-nearly',
                'clerk_user_id': 'user_3K1pC0YksFOD8HW1dIiz4ITDt90',
                'email': 'nearly.done@example.edu',
            },
        }
        self.catalog = {
            'MSSE610': {'course_id': 'c-610', 'code': 'MSSE 610'},
            'MSSE601': {'course_id': 'c-601', 'code': 'MSSE 601'},
        }
        self.rows = {
            's-nearly': [('c-old', 'Fall 2024', 'completed')],
        }

    def replace_for_clerk_user(self, clerk_user_id, courses):
        student = self.students.get(clerk_user_id)
        if student is None:
            raise ApiError(404, 'NOT_FOUND', 'No student record matches this account.')
        saved = []
        skipped = []
        inserts = []
        for row in courses:
            code = row['code']
            status = status_for_grade(row.get('grade', ''))
            if status is None:
                skipped.append({'code': code, 'reason': 'grade not stored'})
                continue
            course = self.catalog.get(code.replace(' ', '').upper())
            if course is None:
                skipped.append({'code': code, 'reason': 'not in course catalog'})
                continue
            term = term_label(row.get('dates', ''))
            inserts.append((course['course_id'], term, status))
            saved.append({
                'code': course['code'],
                'status': status,
                'term': term,
                'grade': row.get('grade'),
            })
        self.rows[student['student_id']] = inserts
        return {
            'student_id': student['student_id'],
            'clerk_user_id': student['clerk_user_id'],
            'email': student['email'],
            'saved': saved,
            'skipped': skipped,
        }


def test_fake_store_overwrites_and_skips_unknown_codes():
    store = _FakeStore()
    result = store.replace_for_clerk_user(
        'user_3K1pC0YksFOD8HW1dIiz4ITDt90',
        [
            {'code': 'MSSE 610', 'grade': 'A', 'dates': '10/20/25-12/14/25'},
            {'code': 'MSSE 600', 'grade': 'A', 'dates': '01/15/24-03/10/24'},
        ],
    )
    assert result['saved'][0]['code'] == 'MSSE 610'
    assert result['skipped'][0]['code'] == 'MSSE 600'
    assert store.rows['s-nearly'] == [
        ('c-610', '102025-121425', 'completed'),
    ]
