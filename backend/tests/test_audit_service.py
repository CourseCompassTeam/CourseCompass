"""Tests for AuditService, based on the US-01 scenarios."""

from datetime import date

from app.services.audit_service import AuditService
from app.services.course_catalog_service import CourseCatalogService


class _FakeAuditRepo:
    def __init__(
        self,
        completed=None,
        student=None,
        requirements=None,
        in_progress=None,
    ):
        self._completed = completed or []
        self._in_progress = in_progress or []
        self._student = student
        self._program = {
            'program_id': 'p1',
            'name': 'Master of Science - Software Engineering',
            'total_credits_required': 36,
        }
        self._requirements = [
            {
                'code': 'MSSE 601',
                'title': 'Software Engineer Fundamentals',
                'description': 'Core software engineering.',
                'credits': 3,
                'category': 'core',
            },
            {
                'code': 'MSSE 635',
                'title': 'Software Architecture and Design',
                'description': 'Architecture.',
                'credits': 3,
                'category': 'core',
            },
            {
                'code': 'MSSE 696',
                'title': 'Software Engineering Practicum II',
                'description': 'Capstone.',
                'credits': 3,
                'category': 'core',
            },
        ]
        if requirements is not None:
            self._requirements = requirements

    def get_student(self, student_id: str):
        return self._student

    def get_completed_courses(self, student_id: str):
        del student_id
        return self._completed

    def get_in_progress_courses(self, student_id: str):
        del student_id
        return self._in_progress

    def get_program_requirements(self, student_id: str):
        return list(self._requirements)

    def get_program(self, program_id: str):
        if program_id == 'p1':
            return dict(self._program)
        return None

    def get_default_program(self):
        return dict(self._program)

    def get_program_by_name(self, name: str):
        if 'software engineering' in name.lower():
            return dict(self._program)
        return None

    def get_requirements_for_program(self, program_id: str):
        del program_id
        return list(self._requirements)


class _FakeCatalogRepo:
    def get_course(self, course_id: str):
        return {
            'course_id': course_id,
            'code': course_id,
            'title': course_id,
            'credits': 3,
        }

    def find_courses(self, course_id: str):
        return [self.get_course(course_id)]

    def list_programs_for_course(self, course_id: str):
        del course_id
        return []

    def get_prerequisites(self, course_id: str):
        if course_id == 'MSSE 696':
            return [{
                'code': 'MSSE 692',
                'requirement_type': 'prereq',
            }]
        return []

    def list_active_courses(self):
        return []

    def list_syllabus_chunks(self, course_id: str):
        return []

    def list_offerings(self):
        return []


def _service(
    completed=None,
    student=None,
    requirements=None,
    in_progress=None,
) -> AuditService:
    return AuditService(
        _FakeAuditRepo(
            completed=completed,
            student=student,
            requirements=requirements,
            in_progress=in_progress,
        ),
        CourseCatalogService(_FakeCatalogRepo()),
    )


def test_audit_when_only_final_course_remains():
    """Scenario 1: every requirement is done except the final course."""
    result = _service(
        completed=[
            {'code': 'MSSE 601', 'credits': 3},
            {'code': 'MSSE 635', 'credits': 3},
        ],
        student={'student_id': 's1', 'program_id': 'p1'},
    ).audit('s1')
    assert result['missingCourses'] == ['MSSE 696']
    assert result['requirementsMet'] is False
    assert result['programName'] == (
        'Master of Science - Software Engineering'
    )


def test_audit_when_all_courses_completed():
    """Scenario 2: all courses complete, show next steps for graduation."""
    result = _service(
        completed=[
            {'code': 'MSSE 601', 'credits': 12},
            {'code': 'MSSE 635', 'credits': 12},
            {'code': 'MSSE 696', 'credits': 12},
        ],
        student={'student_id': 's1', 'program_id': 'p1'},
    ).audit('s1')
    assert result['missingCourses'] == []
    assert result['creditsRemaining'] == 0
    assert result['requirementsMet'] is True


def test_audit_when_enrolled_in_final_class():
    """Scenario 3: in-progress work does not count as completed."""
    result = _service(
        completed=[
            {'code': 'MSSE 601', 'credits': 3},
            {'code': 'MSSE 635', 'credits': 3},
        ],
        student={'student_id': 's1', 'program_id': 'p1'},
    ).audit('s1')
    assert 'MSSE 696' in result['missingCourses']


def test_audit_program_without_student_lists_all_requirements():
    result = _service().audit(
        '',
        program_name='Master of Science - Software Engineering',
    )
    assert result['creditsCompleted'] == 0
    assert result['creditsRemaining'] == 36
    assert result['missingCourses'] == [
        'MSSE 601', 'MSSE 635', 'MSSE 696',
    ]
    assert len(result['requiredCourses']) == 3


def test_audit_orders_courses_by_prerequisite():
    result = _service().audit('s1')
    assert result['prerequisites'] == [
        {'course': 'MSSE 696', 'requires': ['MSSE 692']},
    ]
    steps = result['courseOrder']
    assert steps[0]['courses'] == ['MSSE 601', 'MSSE 635']
    assert steps[1]['courses'] == ['MSSE 696']


def test_audit_lists_requirements_in_curriculum_order():
    result = _service(requirements=[
        {
            'code': 'MSSE 696',
            'title': 'Practicum II',
            'credits': 3,
            'category': 'core',
        },
        {
            'code': 'MSCC 697',
            'title': 'Research Methods',
            'credits': 3,
            'category': 'core',
        },
        {
            'code': 'MSSE 601',
            'title': 'Fundamentals',
            'credits': 3,
            'category': 'core',
        },
        {
            'code': 'MSSE 610',
            'title': 'Requirements',
            'credits': 3,
            'category': 'core',
        },
    ]).audit('')
    assert result['missingCourses'] == [
        'MSSE 601', 'MSSE 610', 'MSCC 697', 'MSSE 696',
    ]


def test_next_courses_are_offered_in_the_next_term():
    class _TermCatalog(_FakeCatalogRepo):
        def get_prerequisites(self, course_id: str):
            if course_id == 'MSSE 610':
                return [{
                    'code': 'MSSE 601',
                    'requirement_type': 'prereq',
                }]
            return []

        def list_offerings(self):
            return [
                {
                    'code': 'MSSE 601',
                    'term_name': '2026 FALL 8W1',
                    'start_date': '2026-08-24',
                    'end_date': '2026-10-18',
                },
                {
                    'code': 'MSSE 615',
                    'term_name': '2026 FALL 8W2',
                    'start_date': '2026-10-19',
                    'end_date': '2026-12-13',
                },
                {
                    'code': 'MSSE 610',
                    'term_name': '2026 FALL 8W2',
                    'start_date': '2026-10-19',
                    'end_date': '2026-12-13',
                },
            ]

    requirements = [
        {
            'code': 'MSSE 610',
            'title': 'Requirements',
            'credits': 3,
            'category': 'core',
        },
        {
            'code': 'MSSE 615',
            'title': 'Society',
            'credits': 3,
            'category': 'core',
        },
        {
            'code': 'MSSE 601',
            'title': 'Fundamentals',
            'credits': 3,
            'category': 'core',
        },
    ]
    service = AuditService(
        _FakeAuditRepo(requirements=requirements),
        CourseCatalogService(_TermCatalog()),
    )
    result = service.audit('', today=date(2026, 10, 1))
    assert result['nextTerm']['name'] == '2026 FALL 8W2'
    assert [course['code'] for course in result['nextCourses']] == [
        'MSSE 615',
    ]
    offered = {
        course['code']: course['offeredTerms']
        for course in result['requiredCourses']
    }
    assert offered['MSSE 601'] == ['2026 FALL 8W1']
    assert result['leadCourseNotOfferedNextTerm'] is True
    assert result['leadCourse']['code'] == 'MSSE 601'
    assert result['needsAdvising'] is False
    assert offered['MSSE 610'] == ['2026 FALL 8W2']


def test_needs_advising_when_no_course_is_open_next_term():
    class _BlockedCatalog(_FakeCatalogRepo):
        def get_prerequisites(self, course_id: str):
            if course_id == 'MSSE 610':
                return [{
                    'code': 'MSSE 601',
                    'requirement_type': 'prereq',
                }]
            return []

        def list_offerings(self):
            return [
                {
                    'code': 'MSSE 601',
                    'term_name': '2026 FALL 8W1',
                    'start_date': '2026-08-24',
                    'end_date': '2026-10-18',
                },
                {
                    'code': 'MSSE 610',
                    'term_name': '2026 FALL 8W2',
                    'start_date': '2026-10-19',
                    'end_date': '2026-12-13',
                },
            ]

    requirements = [
        {
            'code': 'MSSE 601',
            'title': 'Fundamentals',
            'credits': 3,
            'category': 'core',
        },
        {
            'code': 'MSSE 610',
            'title': 'Requirements',
            'credits': 3,
            'category': 'core',
        },
    ]
    result = AuditService(
        _FakeAuditRepo(requirements=requirements),
        CourseCatalogService(_BlockedCatalog()),
    ).audit('', today=date(2026, 10, 1))
    assert result['nextCourses'] == []
    assert result['needsAdvising'] is True


def test_audit_names_courses_ready_to_take_next():
    result = _service().audit('s1')
    assert [course['code'] for course in result['nextCourses']] == [
        'MSSE 601', 'MSSE 635',
    ]


def test_696_is_offered_only_after_692_starts():
    class _TermCatalog(_FakeCatalogRepo):
        def get_prerequisites(self, course_id: str):
            del course_id
            return []

        def list_offerings(self):
            return [
                {
                    'code': 'MSSE 601',
                    'term_name': '2026 FALL 8W1',
                    'start_date': '2026-08-24',
                    'end_date': '2026-10-18',
                },
                {
                    'code': 'MSSE 615',
                    'term_name': '2026 FALL 8W2',
                    'start_date': '2026-10-19',
                    'end_date': '2026-12-13',
                },
                {
                    'code': 'MSSE 696',
                    'term_name': '2026 FALL 8W2',
                    'start_date': '2026-10-19',
                    'end_date': '2026-12-13',
                },
            ]

    requirements = [
        {
            'code': 'MSSE 601',
            'title': 'Fundamentals',
            'credits': 3,
            'category': 'core',
        },
        {
            'code': 'MSSE 615',
            'title': 'Society',
            'credits': 3,
            'category': 'core',
        },
        {
            'code': 'MSSE 692',
            'title': 'Practicum I',
            'credits': 3,
            'category': 'core',
        },
        {
            'code': 'MSSE 696',
            'title': 'Practicum II',
            'credits': 3,
            'category': 'core',
        },
    ]
    catalog = CourseCatalogService(_TermCatalog())
    blocked = AuditService(
        _FakeAuditRepo(requirements=requirements),
        catalog,
    ).audit('', today=date(2026, 10, 1))
    assert [course['code'] for course in blocked['nextCourses']] == [
        'MSSE 615',
    ]
    assert {
        'course': 'MSSE 696',
        'requires': ['MSSE 692'],
    } in blocked['prerequisites']

    started = AuditService(
        _FakeAuditRepo(
            requirements=requirements,
            student={'student_id': 's1', 'program_id': 'p1'},
            in_progress=[{'code': 'MSSE 692', 'credits': 3}],
        ),
        catalog,
    ).audit('s1', today=date(2026, 10, 1))
    assert [course['code'] for course in started['nextCourses']] == [
        'MSSE 615',
        'MSSE 696',
    ]


def test_check_prerequisites_false_when_missing():
    service = _service(
        completed=[{'code': 'MSSE 601', 'credits': 3}],
        student={'student_id': 's1', 'program_id': 'p1'},
    )
    assert service.check_prerequisites('s1', 'MSSE 696') is False
    underway = _service(
        student={'student_id': 's1', 'program_id': 'p1'},
        in_progress=[{'code': 'MSSE 692', 'credits': 3}],
    )
    assert underway.check_prerequisites('s1', 'MSSE 696') is True
