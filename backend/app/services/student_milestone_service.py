"""Next steps for a student based on where they are in their degree."""

from app.repositories.interfaces import IStudentMilestoneRepository
from app.services.audit_service import AuditService


class StudentMilestoneService:
    """Determines milestones to consider at the student's stage.

    Args:
        student_milestone_repository: Milestone table access.
        audit_service: Optional audit used to pick the credit band.
    """

    def __init__(self,
                 student_milestone_repository: IStudentMilestoneRepository,
                 audit_service: AuditService | None = None):
        self._milestones = student_milestone_repository
        self._audit = audit_service

    def get_next_milestones(self, student_id: str) -> list[dict]:
        """Gets suggested next steps (resume, internships, portfolio).

        Args:
            student_id: The student to advise.

        Returns:
            Milestones relevant to the student's progress.
        """
        rows = self._milestones.get_milestones()
        credits = 0
        if self._audit is not None:
            audit = self._audit.audit(student_id)
            credits = int(audit.get('creditsCompleted') or 0)
        matching = [
            {
                'label': row.get('label'),
                'creditMin': row.get('credit_min'),
                'creditMax': row.get('credit_max'),
                'nextActions': row.get('next_actions') or [],
            }
            for row in rows
            if _in_credit_band(credits, row)
        ]
        return matching or [
            {
                'label': row.get('label'),
                'creditMin': row.get('credit_min'),
                'creditMax': row.get('credit_max'),
                'nextActions': row.get('next_actions') or [],
            }
            for row in rows
        ]


def _in_credit_band(credits: int, row: dict) -> bool:
    """Returns whether completed credits fall in a milestone range.

    Args:
        credits: Credits the student has completed.
        row: Milestone row.

    Returns:
        True if credits are inside the inclusive band.
    """
    low = row.get('credit_min')
    high = row.get('credit_max')
    if low is not None and credits < int(low):
        return False
    if high is not None and credits > int(high):
        return False
    return True
