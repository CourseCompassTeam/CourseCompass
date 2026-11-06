"""Builds a student's schedule: load the planner inputs, plan, save the draft."""

from __future__ import annotations

from psycopg.rows import dict_row

from app.repositories.postgres_schedule import find_student_id
from app.scheduling import schedule_repository
from app.scheduling.planner import DEFAULT_MAX_PER_TERM
from app.scheduling.planner import build_plan


class ScheduleBuilderService:
    """Plans and saves a draft schedule for one student.

    Args:
        database: Shared PostgreSQL connection helper.
        repository: PostgresScheduleRepository, used to save and read schedules.
    """

    def __init__(self, database, repository):
        self._database = database
        self._repository = repository

    def build_draft(
        self, student_id: str, max_per_term: int = DEFAULT_MAX_PER_TERM
    ) -> dict | None:
        """Plans the student's remaining courses and saves the result as their draft.

        The old draft is replaced only when at least one course could be placed.
        Exported schedules are never touched.

        Args:
            student_id: UUID or clerk user id.
            max_per_term: Most courses placed in one term.

        Returns:
            None if the student does not exist. Otherwise a dict with
            ``schedule`` (the saved schedule in the get_schedules shape, or None
            when nothing could be placed) and ``unplaced`` (a list of
            ``{course_id, code, title, reason}``).
        """
        with self._database.connect() as connection:
            resolved = find_student_id(connection, student_id)
            if resolved is None:
                return None
            inputs = schedule_repository.load_planning_inputs(connection, resolved)
            plan = build_plan(**inputs, max_per_term=max_per_term)
            unplaced = _describe_unplaced(connection, plan.unplaced)

        schedule = None
        if plan.terms:
            planned_terms = [(pt.term.name, pt.course_ids) for pt in plan.terms]
            new_id = self._repository.replace_draft(str(resolved), planned_terms)
            schedule = next(
                (
                    s
                    for s in self._repository.get_schedules(str(resolved))
                    if s['schedule_id'] == new_id
                ),
                None,
            )
        return {'schedule': schedule, 'unplaced': unplaced}


def _describe_unplaced(connection, unplaced) -> list[dict]:
    """Adds the course code and title to each unplaced course."""
    if not unplaced:
        return []
    with connection.cursor(row_factory=dict_row) as cur:
        cur.execute(
            'SELECT course_id, code, title FROM courses WHERE course_id = ANY(%s)',
            ([u.course_id for u in unplaced],),
        )
        by_id = {str(row['course_id']): row for row in cur.fetchall()}
    described = []
    for item in unplaced:
        row = by_id.get(str(item.course_id), {})
        described.append(
            {
                'course_id': str(item.course_id),
                'code': row.get('code'),
                'title': row.get('title'),
                'reason': item.reason,
            }
        )
    return described
