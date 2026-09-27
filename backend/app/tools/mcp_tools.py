"""The fixed set of tools the LLM is allowed to call.

Each tool is single-purpose and returns only the authenticated student's
own data. The LLM cannot query the database any other way (QA-03).
"""

from typing import Any

from app.embeddings.embedding_provider import TASK_DOCUMENT
from app.embeddings.embedding_provider import TASK_QUERY
from app.embeddings.embedding_provider import EmbeddingProvider
from app.repositories.interfaces import IScheduleRepository
from app.services.audit_service import AuditService
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
        return self._audit.audit(student_id, program_name)

    def get_course_description(self, student_id: str,
                               course_id: str) -> dict[str, Any]:
        """US-02: a course description plus the advising URL.

        Args:
            student_id: The authenticated student's ID.
            course_id: The course to describe.

        Returns:
            The course description and advising_url.
        """
        course = self._catalog.get_course(course_id)
        advisor = self._directory.get_advisor_contact(student_id)
        return {
            'courses': [course],
            'advisingResourceName': advisor.get('resourceName'),
            'advisingUrl': advisor.get('url'),
        }

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
        ranked = leftover
        search_method = 'none'
        if self._embeddings is not None and leftover:
            ranked = _rank_with_embeddings(
                self._embeddings, interest, leftover
            )
            search_method = 'gemini-embedding-001'
        return {
            'courses': ranked,
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

    def get_next_milestones(self, student_id: str) -> dict[str, Any]:
        """US-07 (Could Have): next steps outside of class.

        Args:
            student_id: The authenticated student's ID.

        Returns:
            Milestones to consider at the student's stage.
        """
        return {'milestones': self._milestones.get_next_milestones(student_id)}


def _rank_with_embeddings(
    embedding_provider: EmbeddingProvider,
    interest: str,
    leftover: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Ranks leftover courses with embeddings and cosine similarity.

    Args:
        embedding_provider: Live embedding client.
        interest: Student topic.
        leftover: Leftover-requirement courses.

    Returns:
        The same courses, best match first, with matchScore set.
    """
    query_vector = embedding_provider.embed(interest, task=TASK_QUERY)
    ranked: list[dict[str, Any]] = []
    for course in leftover:
        text = ' '.join(
            part for part in (
                str(course.get('title') or ''),
                str(course.get('description') or ''),
            ) if part
        )
        doc_vector = embedding_provider.embed(text, task=TASK_DOCUMENT)
        item = dict(course)
        item['matchScore'] = round(_cosine(query_vector, doc_vector), 4)
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
