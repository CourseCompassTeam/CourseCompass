"""Creates a students row for a newly created Clerk user."""

from __future__ import annotations

import logging

from app.api.errors import UNPROCESSABLE_CONTENT
from app.api.errors import ApiError
from app.repositories.interfaces import IStudentAuditRepository
from app.repositories.interfaces import IStudentRepository

_LOG = logging.getLogger(__name__)


class StudentProvisioningService:
    """Maps a Clerk user to a new student in the default program.

    Args:
        students: Repository that writes student rows.
        audit: Repository that looks up programs by name.
        program_name: Program name given to new students.
    """

    def __init__(
        self,
        students: IStudentRepository,
        audit: IStudentAuditRepository,
        program_name: str,
    ):
        self._students = students
        self._audit = audit
        self._program_name = program_name

    def provision(
        self,
        clerk_user_id: str,
        email: str,
        full_name: str,
    ) -> bool:
        """Creates the student row for a Clerk user if none exists.

        Args:
            clerk_user_id: Clerk ``sub`` for the new user.
            email: Primary email address.
            full_name: Display name, may be empty.

        Returns:
            True when a row was created, False when it already existed.

        Raises:
            ApiError: 422 when the default program is not seeded, so the
                webhook is retried after the data is fixed.
        """
        program = self._audit.get_program_by_name(self._program_name)
        if program is None:
            status, code = UNPROCESSABLE_CONTENT
            raise ApiError(
                status,
                code,
                'Default program is not configured for new students.',
                {'program_name': self._program_name},
            )

        created = self._students.insert_student_if_absent(
            clerk_user_id,
            email,
            full_name,
            str(program['program_id']),
        )
        if not created:
            _LOG.info(
                'Student not created for Clerk user %s: already exists or '
                'email is in use.',
                clerk_user_id,
            )
        return created
