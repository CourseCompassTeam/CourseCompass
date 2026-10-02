"""The fixed set of tools the LLM is allowed to call.

Each tool is single-purpose and returns only the authenticated student's
own data. The LLM cannot query the database any other way (QA-03).
"""

import re
from datetime import date
from typing import Any

from app.api.errors import ApiError
from app.api.errors import NOT_FOUND
from app.embeddings.embedding_provider import TASK_DOCUMENT
from app.embeddings.embedding_provider import TASK_QUERY
from app.embeddings.embedding_provider import EmbeddingProvider
from app.repositories.interfaces import IScheduleRepository
from app.services.audit_service import AuditService
from app.services.audit_service import _current_term
from app.services.audit_service import _curriculum_key
from app.services.audit_service import _next_term
from app.services.campus_directory_service import CampusDirectoryService
from app.services.course_catalog_service import CourseCatalogService
from app.services.student_milestone_service import StudentMilestoneService


class MCPTools:
    """Directory of every tool available to the LLM provider.

    Args:
        audit_service: Degree audit logic.
        course_catalog_service: Course catalog lookups.
        campus_directory_service: Advising and career contacts.
        student_milestone_service: Non-course next steps.
        embedding_provider: Optional leftover-course ranker.
        schedule_repository: Optional student schedule access.
    """

    def __init__(
        self,
        audit_service: AuditService,
        course_catalog_service: CourseCatalogService,
        campus_directory_service: CampusDirectoryService,
        student_milestone_service: StudentMilestoneService,
        embedding_provider: EmbeddingProvider | None = None,
        schedule_repository: IScheduleRepository | None = None,
    ):
        self._audit = audit_service
        self._catalog = course_catalog_service
        self._directory = campus_directory_service
        self._milestones = student_milestone_service
        self._embeddings = embedding_provider
        self._schedules = schedule_repository

    def audit_degree(
        self,
        student_id: str,
        program_name: str | None = None,
    ) -> dict[str, Any]:
        """US-01: credits completed, credits remaining, missing courses.

        Args:
            student_id: The authenticated student's ID.
            program_name: Optional named program from the query.

        Returns:
            The student's degree audit.
        """
        facts = self._audit.audit(student_id, program_name)
        if facts.get('needsAdvising'):
            advisor = self._directory.get_advisor_contact(student_id)
            facts['advisingResourceName'] = advisor.get('resourceName')
            facts['advisingUrl'] = advisor.get('url')
        return facts

    def get_course_description(self, student_id: str,
                               course_id: str) -> dict[str, Any]:
        """US-02: a course description plus the advising URL.

        Args:
            student_id: The authenticated student's ID.
            course_id: The course to describe.

        Returns:
            The course description and advising_url.
        """
        courses = self._catalog.find_courses(course_id)
        if not courses:
            status, code = NOT_FOUND
            raise ApiError(
                status,
                code,
                f'Course {course_id} was not found.',
            )
        offerings = self._catalog.list_offerings()
        today = date.today().isoformat()
        next_term = _next_term(offerings, today)
        offered_names = _terms_by_code(offerings)
        next_name = next_term['name'] if next_term else ''
        syllabus = self._catalog.syllabus_text_by_code()
        for course in courses:
            code = str(course.get('code') or course_id)
            course['prerequisites'] = self._catalog.get_prerequisites(code)
            terms = offered_names.get(code, [])
            course['offeredTerms'] = terms
            course['offeredNextTerm'] = next_name in terms
            syllabus_text = syllabus.get(code, '')
            if syllabus_text:
                course['syllabusText'] = syllabus_text
        advisor = self._directory.get_advisor_contact(student_id)
        facts = {
            'courses': courses,
            'nextTerm': next_term,
            'advisingResourceName': advisor.get('resourceName'),
            'advisingUrl': advisor.get('url'),
        }
        if len(courses) > 1:
            facts['courseNumberAmbiguous'] = True
        return facts

    def list_term_offerings(
        self,
        student_id: str,
        scope: str = 'next',
    ) -> dict[str, Any]:
        """Lists courses published for the current or next term.

        Args:
            student_id: Unused. Offerings are catalog data.
            scope: ``next`` or ``current``.

        Returns:
            The term and the courses offered in it.
        """
        del student_id
        offerings = self._catalog.list_offerings()
        today = date.today().isoformat()
        if scope == 'current':
            term = _current_term(offerings, today) or _next_term(
                offerings, today
            )
        else:
            term = _next_term(offerings, today)
        if term is None:
            return {
                'nextTerm': None,
                'courses': [],
                'offeringNote': 'No term offerings are loaded.',
            }
        seen: set[str] = set()
        courses: list[dict[str, str]] = []
        for row in offerings:
            code = row.get('code')
            if not code or code in seen:
                continue
            if row.get('termName') != term['name']:
                continue
            seen.add(code)
            courses.append({
                'code': code,
                'title': row.get('title') or '',
            })
        courses.sort(key=lambda course: _curriculum_key(course['code']))
        return {'nextTerm': term, 'courses': courses}

    def recommend_courses(self, student_id: str,
                          interest: str) -> dict[str, Any]:
        """US-03: leftover required courses ranked by interest.

        Args:
            student_id: The authenticated student's ID.
            interest: The topic the student is interested in.

        Returns:
            Recommended leftover courses with descriptions.
        """
        leftover = self._audit.leftover_courses(student_id)
        syllabus = self._catalog.syllabus_text_by_code()
        ranked = leftover
        search_method = 'none'
        if self._embeddings is not None and leftover:
            ranked = _rank_with_embeddings(
                self._embeddings, interest, leftover, syllabus
            )
            ranked = ranked[:1]
            search_method = 'gemini-embedding-001'
        milestone_facts = self.get_next_milestones(student_id, interest)
        if milestone_facts.get('searchMethod'):
            search_method = milestone_facts['searchMethod']
        milestones = [
            row for row in milestone_facts.get('milestones') or []
            if _mentions(interest, row)
        ]
        return {
            'courses': ranked,
            'milestones': milestones,
            'studentInterest': interest,
            'searchMethod': search_method,
            'leftoverCount': len(leftover),
        }

    def build_schedule(self, student_id: str) -> dict[str, Any]:
        """US-04 (Could Have): a term schedule exportable as .ics.

        Args:
            student_id: The authenticated student's ID.

        Returns:
            The proposed course schedule, or an advising handoff.
        """
        advisor = self._directory.get_advisor_contact(student_id)
        schedules = []
        if self._schedules is not None:
            schedules = self._schedules.get_schedules(student_id)
        if not schedules:
            return {
                'scheduleChecked': False,
                'scheduleNote': (
                    'No saved schedule was found. Do not claim a course '
                    'fits their timetable.'
                ),
                'advisingResourceName': advisor.get('resourceName'),
                'advisingUrl': advisor.get('url'),
                'resourceName': advisor.get('resourceName'),
                'url': advisor.get('url'),
            }
        return {
            'scheduleChecked': True,
            'schedules': schedules,
        }

    def get_advisor_contact(self, student_id: str) -> dict[str, Any]:
        """US-05: who to contact when the chatbot cannot answer.

        Args:
            student_id: The authenticated student's ID.

        Returns:
            The advising_url.
        """
        return self._directory.get_advisor_contact(student_id)

    def get_career_services(self, student_id: str) -> dict[str, Any]:
        """US-06: route career questions to Career Services.

        Args:
            student_id: The authenticated student's ID.

        Returns:
            The career_services_url.
        """
        del student_id
        return self._directory.get_career_services_contact()

    def get_next_milestones(
        self,
        student_id: str,
        interest: str = '',
    ) -> dict[str, Any]:
        """US-07 (Could Have): next steps outside of class.

        The student's credit band is always included. A search topic
        can also pull in a later milestone, such as internships.

        Args:
            student_id: The authenticated student's ID.
            interest: Optional topic from the student question.

        Returns:
            Milestones to consider at the student's stage.
        """
        band = self._milestones.get_next_milestones(student_id)
        catalog = self._milestones.list_milestones()
        ranked = catalog
        search_method = 'none'
        if self._embeddings is not None and catalog and interest:
            ranked = _rank_milestones(self._embeddings, interest, catalog)
            search_method = 'gemini-embedding-001'
        facts = {
            'milestones': _milestones_for_search(band, ranked, interest),
        }
        if interest:
            facts['studentInterest'] = interest
            facts['searchMethod'] = search_method
        return facts


def _terms_by_code(offerings: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Groups term names by course code.

    Args:
        offerings: Catalog offering rows.

    Returns:
        Course code to term names.
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


def _milestones_for_search(
    band: list[dict[str, Any]],
    ranked: list[dict[str, Any]],
    interest: str,
) -> list[dict[str, Any]]:
    """Keeps the current milestone and any milestone the query names.

    Args:
        band: Milestones for the student's completed credits.
        ranked: All milestones, best search match first.
        interest: Topic from the student question.

    Returns:
        Search hits first, then the credit-band milestones.
    """
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in ranked:
        label = str(row.get('label') or '')
        if not label or label in seen:
            continue
        if interest and _mentions(interest, row):
            selected.append(row)
            seen.add(label)
    for row in band:
        label = str(row.get('label') or '')
        if not label or label in seen:
            continue
        selected.append(row)
        seen.add(label)
    return selected


def _mentions(interest: str, milestone: dict[str, Any]) -> bool:
    """Returns whether the topic shares a word with a milestone.

    Args:
        interest: Student topic.
        milestone: Milestone payload.

    Returns:
        True when a query word appears in the label or actions.
    """
    haystack = ' '.join([
        str(milestone.get('label') or ''),
        *(str(action) for action in milestone.get('nextActions') or []),
    ]).lower()
    for word in re.findall(r'[a-z0-9]{4,}', interest.lower()):
        if word in haystack or f'{word}s' in haystack:
            return True
        if word.endswith('s') and word[:-1] in haystack:
            return True
    return False


def _rank_milestones(
    embedding_provider: EmbeddingProvider,
    interest: str,
    milestones: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Ranks milestones with embeddings and cosine similarity.

    Args:
        embedding_provider: Live embedding client.
        interest: Student topic.
        milestones: Milestone payloads.

    Returns:
        The same milestones, best match first, with matchScore set.
    """
    query_vector = embedding_provider.embed(interest, task=TASK_QUERY)
    ranked: list[dict[str, Any]] = []
    for milestone in milestones:
        text = ' '.join([
            str(milestone.get('label') or ''),
            *(str(action) for action in milestone.get('nextActions') or []),
        ])
        doc_vector = embedding_provider.embed(text, task=TASK_DOCUMENT)
        item = dict(milestone)
        item['matchScore'] = round(_cosine(query_vector, doc_vector), 4)
        ranked.append(item)
    ranked.sort(key=lambda row: row['matchScore'], reverse=True)
    return ranked


def _rank_with_embeddings(
    embedding_provider: EmbeddingProvider,
    interest: str,
    leftover: list[dict[str, Any]],
    syllabus_by_code: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Ranks leftover courses with embeddings and cosine similarity.

    Syllabus chunks are part of the document when they exist, so a
    topic that only appears in a weekly outline can still match.

    Args:
        embedding_provider: Live embedding client.
        interest: Student topic.
        leftover: Leftover-requirement courses.
        syllabus_by_code: Course code to joined syllabus text.

    Returns:
        The same courses, best match first, with matchScore set.
    """
    syllabus = syllabus_by_code or {}
    query_vector = embedding_provider.embed(interest, task=TASK_QUERY)
    ranked: list[dict[str, Any]] = []
    for course in leftover:
        code = str(course.get('code') or '')
        syllabus_text = syllabus.get(code, '')
        text = ' '.join(
            part for part in (
                str(course.get('title') or ''),
                str(course.get('description') or ''),
                syllabus_text,
            ) if part
        )
        doc_vector = embedding_provider.embed(text, task=TASK_DOCUMENT)
        item = dict(course)
        item['matchScore'] = round(_cosine(query_vector, doc_vector), 4)
        if syllabus_text:
            item['syllabusText'] = syllabus_text[:800]
        ranked.append(item)
    ranked.sort(key=lambda row: row['matchScore'], reverse=True)
    return ranked


def _cosine(left: list[float], right: list[float]) -> float:
    """Returns cosine similarity of two equal-length vectors.

    Args:
        left: Query embedding.
        right: Course embedding.

    Returns:
        Similarity in roughly -1 to 1, or 0 if a vector is empty.
    """
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sum(a * a for a in left) ** 0.5
    right_norm = sum(b * b for b in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
