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
            course_id: The course to look up.

        Returns:
            The course's code, title, credits, and description.

        Raises:
            ApiError: 404 if the course does not exist.
        """
        course = self._courses.get_course(course_id)
        if course is None:
            status, code = NOT_FOUND
            raise ApiError(
                status,
                code,
                f'Course {course_id} was not found.',
            )
        return {
            'courseId': course.get('course_id'),
            'code': course.get('code'),
            'title': course.get('title'),
            'description': course.get('description') or '',
            'credits': course.get('credits') or 0,
            'isActive': course.get('is_active', True),
        }

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
