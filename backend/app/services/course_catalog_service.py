"""Course information: descriptions and prerequisites."""

from app.repositories.interfaces import ICourseCatalogRepository


class CourseCatalogService:
    """Gathers course information from the course catalog repository."""

    def __init__(self, course_catalog_repository: ICourseCatalogRepository):
        raise NotImplementedError

    def get_course(self, course_id: str) -> dict:
        """Gets a course's details.

        Args:
            course_id: The course to look up.

        Returns:
            The course's code, title, credits, and description.

        Raises:
            ApiError: 404 if the course does not exist.
        """
        raise NotImplementedError

    def get_prerequisites(self, course_id: str) -> list[str]:
        """Gets the courses required before a course.

        Args:
            course_id: The course to look up.

        Returns:
            IDs of the prerequisite courses.
        """
        raise NotImplementedError
