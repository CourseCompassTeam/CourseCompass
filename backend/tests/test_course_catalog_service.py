"""Tests for course lookup by number and program names."""

import pytest

from app.api.errors import ApiError
from app.repositories.row_utils import course_number_query
from app.services.course_catalog_service import CourseCatalogService


class _Catalog:
    def __init__(self, rows):
        self._rows = rows

    def get_course(self, course_id: str):
        matches = self.find_courses(course_id)
        if len(matches) == 1:
            return matches[0]
        return None

    def find_courses(self, course_id: str):
        number = course_number_query(course_id)
        found = []
        for row in self._rows:
            code = str(row['code']).replace(' ', '').upper()
            if course_id == row['code'] or course_id == code:
                found.append(row)
            elif number and number in str(row['code']):
                found.append(row)
        return found

    def list_programs_for_course(self, course_id: str):
        for row in self._rows:
            if row['course_id'] == course_id:
                return list(row.get('programs') or [])
        return []

    def get_prerequisites(self, course_id: str):
        del course_id
        return []

    def list_active_courses(self):
        return []

    def list_syllabus_chunks(self, course_id: str):
        del course_id
        return []


def test_course_number_query_accepts_class_word():
    assert course_number_query('697') == '697'
    assert course_number_query('class 697') == '697'
    assert course_number_query('MSCC 697') == ''


def test_find_courses_attaches_program_for_a_number():
    service = CourseCatalogService(_Catalog([
        {
            'course_id': 'c1',
            'code': 'MSCC 697',
            'title': 'Information Technology Research Methods',
            'description': 'Research methods.',
            'credits': 3,
            'programs': ['Master of Science - Software Engineering'],
        },
    ]))
    found = service.find_courses('697')
    assert found[0]['code'] == 'MSCC 697'
    assert found[0]['programs'] == [
        'Master of Science - Software Engineering',
    ]


def test_get_course_rejects_an_ambiguous_number():
    service = CourseCatalogService(_Catalog([
        {
            'course_id': 'c1',
            'code': 'MSCC 697',
            'title': 'Research',
            'credits': 3,
            'programs': ['Master of Science - Software Engineering'],
        },
        {
            'course_id': 'c2',
            'code': 'MSSE 697',
            'title': 'Other',
            'credits': 3,
            'programs': ['Other Program'],
        },
    ]))
    with pytest.raises(ApiError, match='more than one class'):
        service.get_course('697')
