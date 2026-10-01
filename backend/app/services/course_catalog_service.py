"""Course information: descriptions and prerequisites."""

from app.api.errors import ApiError
from app.api.errors import NOT_FOUND
from app.repositories.interfaces import ICourseCatalogRepository


class CourseCatalogService:
    """Gathers course information from the course catalog repository.

    Args:
        course_catalog_repository: Course table access.
    """

    def __init__(self, course_catalog_repository: ICourseCatalogRepository):
        self._courses = course_catalog_repository

    def get_course(self, course_id: str) -> dict:
        """Gets a course's details.

        Args:
            course_id: The course to look up. A bare number such as
                ``697`` matches the catalog code that ends with it.

        Returns:
            The course's code, title, credits, description, and programs.

        Raises:
            ApiError: 404 if the course does not exist, or if the number
                matches more than one course.
        """
        matches = self.find_courses(course_id)
        if len(matches) == 1:
            return matches[0]
        status, code = NOT_FOUND
        if not matches:
            raise ApiError(
                status,
                code,
                f'Course {course_id} was not found.',
            )
        listed = ', '.join(
            _course_label(course) for course in matches
        )
        raise ApiError(
            status,
            code,
            f'Course {course_id} matches more than one class: {listed}.',
        )

    def find_courses(self, course_id: str) -> list[dict]:
        """Finds every course for a code or a bare course number.

        Args:
            course_id: Course UUID, code, or number such as ``697``.

        Returns:
            Matching courses, each with the programs that require it.
        """
        rows = self._courses.find_courses(course_id)
        found: list[dict] = []
        for course in rows:
            programs = self._courses.list_programs_for_course(
                str(course.get('course_id') or '')
            )
            found.append({
                'courseId': course.get('course_id'),
                'code': course.get('code'),
                'title': course.get('title'),
                'description': course.get('description') or '',
                'credits': course.get('credits') or 0,
                'isActive': course.get('is_active', True),
                'programs': programs,
            })
        return found

    def get_prerequisites(self, course_id: str) -> list[str]:
        """Gets the courses required before a course.

        Args:
            course_id: The course to look up.

        Returns:
            Codes of the prerequisite courses.
        """
        rows = self._courses.get_prerequisites(course_id)
        return [
            row.get('code')
            for row in rows
            if row.get('requirement_type', 'prereq') == 'prereq'
            and row.get('code')
        ]

    def list_offerings(self) -> list[dict]:
        """Lists when each course is offered.

        Returns:
            Course code, term name, and term dates.
        """
        found: list[dict] = []
        for row in self._courses.list_offerings():
            found.append({
                'code': row.get('code'),
                'title': row.get('title') or '',
                'termName': row.get('term_name'),
                'startDate': row.get('start_date'),
                'endDate': row.get('end_date'),
            })
        return found

    def syllabus_text_by_code(self) -> dict[str, str]:
        """Joins each course's syllabus chunks into one text block.

        Returns:
            Course code to syllabus text, in chunk order.
        """
        grouped: dict[str, list[str]] = {}
        loader = getattr(self._courses, 'list_all_syllabus_chunks', None)
        rows = loader() if loader else []
        for row in rows:
            code = row.get('code')
            text = str(row.get('chunk_text') or '').strip()
            if not code or not text:
                continue
            grouped.setdefault(code, []).append(text)
        return {
            code: '\n'.join(parts)
            for code, parts in grouped.items()
        }

    def list_active_courses(self) -> list[dict]:
        """Lists active catalog courses.

        Returns:
            Active course rows in API shape.
        """
        return [
            {
                'courseId': row.get('course_id'),
                'code': row.get('code'),
                'title': row.get('title'),
                'description': row.get('description') or '',
                'credits': row.get('credits') or 0,
            }
            for row in self._courses.list_active_courses()
        ]


def _course_label(course: dict) -> str:
    """Formats a course code with its program names.

    Args:
        course: A course dict from ``find_courses``.

    Returns:
        A short label such as ``MSCC 697 (Master of Science - ...)``.
    """
    code = course.get('code') or 'unknown course'
    programs = course.get('programs') or []
    if not programs:
        return str(code)
    return f'{code} ({", ".join(programs)})'
