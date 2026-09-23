"""Next steps for a student based on where they are in their degree."""

from app.repositories.interfaces import IStudentMilestoneRepository


class StudentMilestoneService:
    """Determines milestones to consider at the student's stage."""

    def __init__(self,
                 student_milestone_repository: IStudentMilestoneRepository):
        raise NotImplementedError

    def get_next_milestones(self, student_id: str) -> list[dict]:
        """Gets suggested next steps (resume, internships, portfolio).

        Args:
            student_id: The student to advise.

        Returns:
            Milestones relevant to the student's progress.
        """
        raise NotImplementedError
