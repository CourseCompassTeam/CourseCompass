"""StudentProvisioningService: default program lookup and insert."""

import pytest

from app.api.errors import ApiError
from app.services.student_provisioning_service import (
    StudentProvisioningService,
)


class _FakeStudents:
    def __init__(self, inserted=True):
        self.calls = []
        self._inserted = inserted

    def insert_student_if_absent(self, clerk_user_id, email, full_name,
                                 program_id):
        self.calls.append((clerk_user_id, email, full_name, program_id))
        return self._inserted


class _FakeAudit:
    def __init__(self, program):
        self.program = program
        self.names = []

    def get_program_by_name(self, name):
        self.names.append(name)
        return self.program


def test_provision_inserts_student_in_default_program():
    students = _FakeStudents()
    audit = _FakeAudit({'program_id': 'prog-1', 'name': 'MSSE'})
    service = StudentProvisioningService(students, audit, 'MSSE')

    created = service.provision('user_1', 'a@example.edu', 'Ada Lovelace')

    assert created is True
    assert audit.names == ['MSSE']
    assert students.calls == [
        ('user_1', 'a@example.edu', 'Ada Lovelace', 'prog-1'),
    ]


def test_provision_reports_false_when_student_exists():
    service = StudentProvisioningService(
        _FakeStudents(inserted=False),
        _FakeAudit({'program_id': 'prog-1'}),
        'MSSE',
    )

    assert service.provision('user_1', 'a@example.edu', '') is False


def test_missing_default_program_raises_422_and_inserts_nothing():
    students = _FakeStudents()
    service = StudentProvisioningService(
        students,
        _FakeAudit(None),
        'MSSE',
    )

    with pytest.raises(ApiError) as exc_info:
        service.provision('user_1', 'a@example.edu', 'Ada')

    assert exc_info.value.status == 422
    assert students.calls == []
