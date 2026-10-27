"""Map parsed transcript rows onto a student and replace their DB rows.

Does not use an LLM. Unknown catalog codes are skipped, not invented.
"""

from __future__ import annotations

import logging
from typing import Any

from app.api.errors import NOT_FOUND
from app.api.errors import ApiError
from app.repositories.connection import Database
from app.repositories.postgres_audit import PostgresAuditRepository
from app.repositories.row_utils import normalize_code

_LOG = logging.getLogger(__name__)

_COMPLETED_GRADES = {
    'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-',
    'D+', 'D', 'D-', 'P', 'CR',
}
_SKIP_GRADES = {'F', 'W', 'I', 'NP', 'NC'}


def status_for_grade(grade: str) -> str | None:
    """Maps a transcript letter grade to a transcript_entries status.

    Args:
        grade: Parsed grade token, e.g. ``A`` or ``IP``.

    Returns:
        ``completed``, ``in_progress``, or None to skip the row.
    """
    token = str(grade or '').strip().upper()
    if token == 'IP':
        return 'in_progress'
    if token in _SKIP_GRADES:
        return None
    if token in _COMPLETED_GRADES:
        return 'completed'
    return None


def term_label(dates: str) -> str:
    """Fits course dates into transcript_entries.term (varchar 20).

    Args:
        dates: ``MM/DD/YY-MM/DD/YY`` from the PDF.

    Returns:
        A compact date range, or the original string trimmed to 20 chars.
    """
    compact = str(dates or '').replace('/', '')
    if compact:
        return compact[:20]
    return 'unknown'


class TranscriptStore:
    """Overwrites ``transcript_entries`` for one student.

    Args:
        database: PostgreSQL helper.
    """

    def __init__(self, database: Database):
        self._database = database
        self._audit = PostgresAuditRepository(database)

    def replace_for_clerk_user(
        self,
        clerk_user_id: str,
        courses: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Deletes a student's transcript rows and inserts parsed courses.

        Args:
            clerk_user_id: Clerk ``sub`` / ``students.clerk_user_id``.
            courses: Parsed PDF course dicts (code, grade, dates).

        Returns:
            Student identity plus ``saved`` and ``skipped`` course lists.

        Raises:
            ApiError: 404 if no student row matches the Clerk id.
        """
        student = self._audit.get_student(clerk_user_id)
        if student is None:
            status, code = NOT_FOUND
            raise ApiError(
                status,
                code,
                'No student record matches this account.',
                {'clerk_user_id': clerk_user_id},
            )

        catalog = self._courses_by_code(
            [str(row.get('code') or '') for row in courses]
        )
        saved: list[dict[str, Any]] = []
        skipped: list[dict[str, str]] = []
        inserts: list[tuple[str, str, str, str]] = []

        for row in courses:
            code = str(row.get('code') or '').strip()
            grade = str(row.get('grade') or '')
            status = status_for_grade(grade)
            if status is None:
                skipped.append({
                    'code': code,
                    'reason': f'grade {grade} is not stored',
                })
                continue
            course = catalog.get(normalize_code(code))
            if course is None:
                skipped.append({
                    'code': code,
                    'reason': 'not in course catalog',
                })
                continue
            term = term_label(str(row.get('dates') or ''))
            inserts.append(
                (student['student_id'], course['course_id'], term, status)
            )
            saved.append({
                'code': course['code'],
                'status': status,
                'term': term,
                'grade': grade,
            })

        with self._database.connect() as connection:
            connection.execute(
                'DELETE FROM transcript_entries WHERE student_id = %s',
                (student['student_id'],),
            )
            for student_id, course_id, term, status in inserts:
                connection.execute(
                    'INSERT INTO transcript_entries '
                    '(student_id, course_id, term, status) '
                    'VALUES (%s, %s, %s, %s)',
                    (student_id, course_id, term, status),
                )
            connection.commit()

        _LOG.info(
            'transcript replaced clerk=%s saved=%s skipped=%s',
            clerk_user_id,
            len(saved),
            len(skipped),
        )
        return {
            'student_id': student['student_id'],
            'clerk_user_id': student.get('clerk_user_id') or clerk_user_id,
            'email': student.get('email'),
            'saved': saved,
            'skipped': skipped,
        }

    def _courses_by_code(self, codes: list[str]) -> dict[str, dict]:
        """Loads catalog rows keyed by normalized code.

        Args:
            codes: Parsed transcript codes.

        Returns:
            Mapping of ``MSSE610`` -> course row.
        """
        normalized = [normalize_code(code) for code in codes if code.strip()]
        if not normalized:
            return {}
        sql = """
            SELECT course_id, code, title, credits
            FROM courses
            WHERE replace(upper(code), ' ', '') = ANY(%s)
        """
        with self._database.connect() as connection:
            rows = connection.execute(sql, (normalized,)).fetchall()
        found: dict[str, dict] = {}
        for row in rows:
            found[normalize_code(row['code'])] = {
                'course_id': str(row['course_id']),
                'code': row['code'],
            }
        return found
