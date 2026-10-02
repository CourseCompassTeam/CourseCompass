"""Degree audit: deterministic credit and prerequisite logic.

This logic never uses the LLM, so audit answers cannot be hallucinated.
"""

from datetime import date

from app.api.errors import ApiError
from app.api.errors import NOT_FOUND
from app.repositories.interfaces import IStudentAuditRepository
from app.services.course_catalog_service import CourseCatalogService

# Preferred MSSE curriculum sequence. Prerequisite rules still decide
# what is actually open; this only orders the requirement list.
_CURRICULUM_ORDER = (
    'MSSE 601',
    'MSSE 603',
    'MSSE 610',
    'MSSE 613',
    'MSSE 615',
    'MSSE 635',
    'MSSE 640',
    'MSSE 642',
    'MSES 602',
    'MSCC 697',
    'MSSE 692',
    'MSSE 696',
)
_CURRICULUM_RANK = {
    code: index for index, code in enumerate(_CURRICULUM_ORDER)
}
# 696 continues the project from 692. It is open once 692 is completed
# or already in progress, even when the prerequisites table has no row.
_FOLLOW_ON = {'MSSE 696': ('MSSE 692',)}


def _with_follow_on(course: str, prerequisites: list[str]) -> list[str]:
    """Adds follow-on rules that the prerequisites table may omit.

    Args:
        course: Course code being checked.
        prerequisites: Prerequisite codes already stored.

    Returns:
        Prerequisite codes, including a follow-on course when required.
    """
    required = list(prerequisites)
    for code in _FOLLOW_ON.get(course, ()):
        if code not in required:
            required.append(code)
    return required


def _requirement_met(
    course: str,
    requirement: str,
    completed: set[str],
    in_progress: set[str],
) -> bool:
    """Checks one prerequisite against the student's transcript.

    A follow-on course such as MSSE 696 is open when its earlier
    course is completed or already in progress.

    Args:
        course: The course that has the requirement.
        requirement: Prerequisite course code.
        completed: Completed course codes.
        in_progress: Courses the student is currently taking.

    Returns:
        Whether this requirement is satisfied.
    """
    if requirement in completed:
        return True
    return (
        requirement in _FOLLOW_ON.get(course, ())
        and requirement in in_progress
    )


def _curriculum_key(code: str) -> tuple[int, str]:
    """Sorts a course by the preferred curriculum sequence.

    Args:
        code: Catalog course code.

    Returns:
        Rank, then the code for courses outside the sequence.
    """
    return (_CURRICULUM_RANK.get(code, len(_CURRICULUM_ORDER)), code)


class AuditService:
    """Checks a student's progress through their degree.

    Args:
        student_audit_repository: Student, transcript, and program access.
        course_catalog_service: Used for prerequisite lookups.
    """

    def __init__(self, student_audit_repository: IStudentAuditRepository,
                 course_catalog_service: CourseCatalogService):
        self._audit = student_audit_repository
        self._catalog = course_catalog_service

    def audit(
        self,
        student_id: str,
        program_name: str | None = None,
        today: date | None = None,
    ) -> dict:
        """Computes credits completed and remaining and missing courses.

        When no student row exists, leftover requirements are every
        required course in the named or default program.

        Args:
            student_id: The student to audit. May be empty.
            program_name: Optional program name from the student query.
            today: Date used to choose the next term. Defaults to today.

        Returns:
            Credits completed, credits remaining, and remaining
            requirements.

        Raises:
            ApiError: 404 if no matching program exists.
        """
        student = self._audit.get_student(student_id) if student_id else None
        completed = (
            self._audit.get_completed_courses(student_id)
            if student is not None else []
        )
        program = self._resolve_program(student, program_name)
        if program is None:
            status, code = NOT_FOUND
            raise ApiError(
                status,
                code,
                'No degree program was found.',
            )
        requirements = self._audit.get_requirements_for_program(
            program['program_id']
        )
        required_courses = [
            {
                'code': row.get('code'),
                'title': row.get('title'),
                'description': row.get('description') or '',
                'credits': (
                    row.get('credits')
                    or row.get('credits_required')
                    or 0
                ),
                'category': row.get('category') or 'core',
            }
            for row in requirements
            if row.get('code')
        ]
        required_courses.sort(key=lambda course: _curriculum_key(course['code']))
        offerings = self._catalog.list_offerings()
        offered_terms = _offered_terms(offerings)
        for course in required_courses:
            course['offeredTerms'] = offered_terms.get(course['code'], [])
        completed_codes = {
            row.get('code') for row in completed if row.get('code')
        }
        in_progress_codes = {
            row.get('code')
            for row in self._in_progress_courses(student_id, student)
            if row.get('code')
        }
        prerequisites = self._prerequisite_rules(
            [course['code'] for course in required_courses]
        )
        for course in required_courses:
            course['prerequisites'] = prerequisites.get(course['code'], [])
        missing = [
            course for course in required_courses
            if course['code'] not in completed_codes
        ]
        credits_completed = sum(
            int(row.get('credits') or 0) for row in completed
        )
        credits_required = int(
            program.get('total_credits_required') or 0
        )
        missing_credits = sum(int(course['credits'] or 0) for course in missing)
        if credits_required:
            credits_remaining = max(0, credits_required - credits_completed)
        else:
            credits_remaining = missing_credits
        course_order = self._course_order(
            [course['code'] for course in missing],
            prerequisites,
            completed_codes,
            in_progress_codes,
        )
        as_of = today or date.today()
        next_term = _next_term(offerings, as_of.isoformat())
        next_courses = [
            course for course in self._next_courses(
                course_order, required_courses
            )
            if course['code'] not in in_progress_codes
        ]
        if next_term is not None:
            offered_next = {
                row['code']
                for row in offerings
                if row.get('termName') == next_term['name']
            }
            next_courses = [
                course for course in next_courses
                if course['code'] in offered_next
            ]
        lead = missing[0] if missing else None
        lead_terms = lead.get('offeredTerms') or [] if lead else []
        lead_not_offered = bool(
            lead
            and next_term
            and next_term['name'] not in lead_terms
        )
        return {
            'programName': program.get('name'),
            'creditsRequired': credits_required,
            'creditsCompleted': credits_completed,
            'creditsRemaining': credits_remaining,
            'requirementsMet': len(missing) == 0 and credits_remaining == 0,
            'missingCourses': [course['code'] for course in missing],
            'requiredCourses': required_courses,
            'prerequisites': [
                {'course': code, 'requires': requires}
                for code, requires in prerequisites.items()
                if requires
            ],
            'courseOrder': course_order,
            'nextTerm': next_term,
            'nextCourses': next_courses,
            'needsAdvising': lead_not_offered and not next_courses,
            'leadCourseNotOfferedNextTerm': lead_not_offered,
            'leadCourse': {
                'code': lead['code'],
                'title': lead.get('title') or '',
                'offeredTerms': lead_terms,
            } if lead_not_offered else None,
        }

    def check_prerequisites(self, student_id: str, course_id: str) -> bool:
        """Checks whether the student completed a course's prerequisites.

        Args:
            student_id: The student to check.
            course_id: The course the student wants to take.

        Returns:
            True if every prerequisite has a 'completed' transcript entry.
        """
        required = _with_follow_on(
            course_id,
            self._catalog.get_prerequisites(course_id),
        )
        if not required:
            return True
        completed = {
            row.get('code')
            for row in self._audit.get_completed_courses(student_id)
            if row.get('code')
        }
        student = self._audit.get_student(student_id)
        in_progress = {
            row.get('code')
            for row in self._in_progress_courses(student_id, student)
            if row.get('code')
        }
        return all(
            _requirement_met(course_id, code, completed, in_progress)
            for code in required
        )

    def leftover_courses(
        self,
        student_id: str,
        program_name: str | None = None,
    ) -> list[dict]:
        """Returns required courses the student has not completed.

        Args:
            student_id: The student to audit. May be empty.
            program_name: Optional program name.

        Returns:
            Leftover required-course dicts.
        """
        result = self.audit(student_id, program_name)
        missing = set(result['missingCourses'])
        return [
            course for course in result['requiredCourses']
            if course['code'] in missing
        ]

    def _next_courses(
        self,
        course_order: list[dict],
        required_courses: list[dict],
    ) -> list[dict]:
        """Returns leftover courses the student can take now.

        Args:
            course_order: Prerequisite steps for leftover courses.
            required_courses: Catalog rows for required courses.

        Returns:
            Code and title for the first step, skipping a blocked step.
        """
        titles = {
            course['code']: course.get('title') or ''
            for course in required_courses
        }
        for step in course_order:
            if step.get('note'):
                continue
            return [
                {'code': code, 'title': titles.get(code, '')}
                for code in step.get('courses') or []
            ]
        return []

    def _prerequisite_rules(self, course_codes: list[str]) -> dict[str, list[str]]:
        """Loads catalog prerequisites for each required course.

        Args:
            course_codes: Course codes in the program.

        Returns:
            Map of course code to prerequisite codes.
        """
        rules: dict[str, list[str]] = {}
        for code in course_codes:
            rules[code] = _with_follow_on(
                code,
                self._catalog.get_prerequisites(code),
            )
        return rules

    def _in_progress_courses(
        self,
        student_id: str,
        student: dict | None,
    ) -> list[dict]:
        """Loads courses the student is currently taking.

        Args:
            student_id: The student to look up.
            student: Student row, if one was found.

        Returns:
            In-progress transcript rows, or an empty list.
        """
        if student is None:
            return []
        loader = getattr(self._audit, 'get_in_progress_courses', None)
        if loader is None:
            return []
        return loader(student_id)

    def _course_order(
        self,
        missing_codes: list[str],
        prerequisites: dict[str, list[str]],
        completed_codes: set[str],
        in_progress_codes: set[str] | None = None,
    ) -> list[dict]:
        """Groups leftover courses by how many prerequisites block them.

        A course is in the first group when every stored prerequisite is
        already completed. Later groups wait on earlier leftover courses.

        Args:
            missing_codes: Required courses the student has not completed.
            prerequisites: Course code to prerequisite codes.
            completed_codes: Completed course codes.
            in_progress_codes: Courses the student is currently taking.

        Returns:
            Ordered steps the student can take from the catalog rules.
        """
        remaining = list(missing_codes)
        done = set(completed_codes)
        underway = set(in_progress_codes or ())
        steps: list[dict] = []
        guard = 0
        while remaining and guard <= len(missing_codes):
            guard += 1
            ready = [
                code for code in remaining
                if all(
                    _requirement_met(code, req, done, underway)
                    for req in prerequisites.get(code, [])
                )
            ]
            if not ready:
                steps.append({
                    'step': len(steps) + 1,
                    'courses': list(remaining),
                    'note': (
                        'These still have a prerequisite that is not in '
                        'the completed list.'
                    ),
                })
                break
            steps.append({'step': len(steps) + 1, 'courses': ready})
            done.update(ready)
            remaining = [code for code in remaining if code not in done]
        return steps

    def _resolve_program(
        self,
        student: dict | None,
        program_name: str | None,
    ) -> dict | None:
        """Picks the program for an audit.

        Args:
            student: Student row, if found.
            program_name: Optional name from the query.

        Returns:
            A program row, or None.
        """
        if program_name:
            named = self._audit.get_program_by_name(program_name)
            if named is not None:
                return named
        if student and student.get('program_id'):
            enrolled = self._audit.get_program(student['program_id'])
            if enrolled is not None:
                return enrolled
        if program_name:
            return None
        return self._audit.get_default_program()


def _offered_terms(offerings: list[dict]) -> dict[str, list[str]]:
    """Groups offering term names by course code.

    Args:
        offerings: Offering rows from the catalog.

    Returns:
        Course code to term names, in date order.
    """
    grouped: dict[str, list[str]] = {}
    for row in offerings:
        code = row.get('code')
        name = row.get('termName')
        if not code or not name:
            continue
        names = grouped.setdefault(code, [])
        if name not in names:
            names.append(name)
    return grouped


def _next_term(offerings: list[dict], today: str) -> dict | None:
    """Picks the soonest term that has not started yet.

    Args:
        offerings: Offering rows with term names and start dates.
        today: ISO date string.

    Returns:
        The next term, or None when no later term is stored.
    """
    terms: dict[str, dict] = {}
    for row in offerings:
        name = row.get('termName')
        start = row.get('startDate')
        if not name or not start:
            continue
        terms[name] = {
            'name': name,
            'startDate': start,
            'endDate': row.get('endDate'),
        }
    upcoming = sorted(
        (
            term for term in terms.values()
            if str(term['startDate']) > today
        ),
        key=lambda term: str(term['startDate']),
    )
    if not upcoming:
        return None
    return upcoming[0]


def _current_term(offerings: list[dict], today: str) -> dict | None:
    """Picks the term that is in progress on a date.

    Args:
        offerings: Offering rows with term names and dates.
        today: ISO date string.

    Returns:
        The current term, or None when today is between terms.
    """
    terms: dict[str, dict] = {}
    for row in offerings:
        name = row.get('termName')
        start = row.get('startDate')
        end = row.get('endDate') or start
        if not name or not start:
            continue
        terms[name] = {
            'name': name,
            'startDate': start,
            'endDate': end,
        }
    active = [
        term for term in terms.values()
        if str(term['startDate']) <= today <= str(term['endDate'])
    ]
    if not active:
        return None
    active.sort(key=lambda term: str(term['startDate']))
    return active[-1]
