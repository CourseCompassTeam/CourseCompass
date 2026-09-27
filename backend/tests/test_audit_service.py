"""Tests for AuditService, based on the US-01 scenarios."""

from app.services.audit_service import AuditService
from app.services.course_catalog_service import CourseCatalogService


class _FakeAuditRepo:
    def __init__(self, completed=None, student=None):
        self._completed = completed or []
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

    def get_student(self, student_id: str):
        return self._student

    def get_completed_courses(self, student_id: str):
        return self._completed

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
        return {'code': course_id, 'title': course_id, 'credits': 3}

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


def _service(completed=None, student=None) -> AuditService:
    return AuditService(
        _FakeAuditRepo(completed=completed, student=student),
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


def test_check_prerequisites_false_when_missing():
    service = _service(
        completed=[{'code': 'MSSE 601', 'credits': 3}],
        student={'student_id': 's1', 'program_id': 'p1'},
    )
    assert service.check_prerequisites('s1', 'MSSE 696') is False
