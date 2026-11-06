"""Map parsed transcript rows onto a student and replace their DB rows.

Does not use an LLM. Unknown catalog codes are skipped, not invented.
"""

from __future__ import annotations

import logging
from typing import Any

from app.api.errors import BAD_REQUEST
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

        Retakes collapse to one row per course, keeping a completed row over
        an in-progress one. Declared substitutions that no longer hold after
        the rewrite are deleted in the same transaction and returned as
        ``cleared``.

        Args:
            clerk_user_id: Clerk ``sub`` / ``students.clerk_user_id``.
            courses: Parsed PDF course dicts (code, grade, dates).

        Returns:
            Student identity, ``saved`` and ``skipped`` course lists, and
            ``cleared`` substitutions.

        Raises:
            ApiError: 404 if no student row matches the Clerk id. 400 if no
                parsed row can be stored; the existing transcript is kept.
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
        skipped: list[dict[str, str]] = []
        chosen: dict[str, dict[str, Any]] = {}

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
            entry = {
                'course_id': course['course_id'],
                'code': course['code'],
                'status': status,
                'term': term_label(str(row.get('dates') or '')),
                'grade': grade,
            }
            current = chosen.get(course['course_id'])
            if current is None or (
                current['status'] != 'completed'
                and status == 'completed'
            ):
                chosen[course['course_id']] = entry

        if not chosen:
            status, code = BAD_REQUEST
            raise ApiError(
                status,
                code,
                'None of the parsed courses are in the catalog; existing '
                'transcript was not changed.',
            )

        saved = list(chosen.values())
        completed_ids = [
            entry['course_id'] for entry in saved
            if entry['status'] == 'completed'
        ]
        with self._database.connect() as connection:
            stale = connection.execute(
                """
                SELECT s.substitution_id,
                       rc.code AS requirement_code,
                       sc.code AS substitute_code
                FROM student_substitutions s
                JOIN courses rc ON rc.course_id = s.requirement_course_id
                JOIN courses sc ON sc.course_id = s.substitute_course_id
                WHERE s.student_id = %s
                  AND (
                    s.substitute_course_id <> ALL(%s::uuid[])
                    OR s.requirement_course_id = ANY(%s::uuid[])
                  )
                """,
                (
                    student['student_id'],
                    [entry['course_id'] for entry in saved],
                    completed_ids,
                ),
            ).fetchall()
            if stale:
                connection.execute(
                    'DELETE FROM student_substitutions '
                    'WHERE substitution_id = ANY(%s::uuid[])',
                    ([row['substitution_id'] for row in stale],),
                )
            connection.execute(
                'DELETE FROM transcript_entries WHERE student_id = %s',
                (student['student_id'],),
            )
            for entry in saved:
                connection.execute(
                    'INSERT INTO transcript_entries '
                    '(student_id, course_id, term, status) '
                    'VALUES (%s, %s, %s, %s)',
                    (
                        student['student_id'],
                        entry['course_id'],
                        entry['term'],
                        entry['status'],
                    ),
                )
            connection.commit()

        cleared = [
            {
                'requirementCode': row['requirement_code'],
                'substituteCode': row['substitute_code'],
            }
            for row in stale
        ]
        _LOG.info(
            'transcript replaced clerk=%s saved=%s skipped=%s cleared=%s',
            clerk_user_id,
            len(saved),
            len(skipped),
            len(cleared),
        )
        return {
            'student_id': student['student_id'],
            'clerk_user_id': student.get('clerk_user_id') or clerk_user_id,
            'email': student.get('email'),
            'saved': [
                {
                    'code': entry['code'],
                    'status': entry['status'],
                    'term': entry['term'],
                    'grade': entry['grade'],
                }
                for entry in saved
            ],
            'skipped': skipped,
            'cleared': cleared,
        }

    def _courses_by_code(self, codes: list[str]) -> dict[str, dict]:
        """Loads catalog rows keyed by normalized code, active or not.

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
