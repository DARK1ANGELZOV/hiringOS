from dataclasses import dataclass

from fastapi import HTTPException, status

from app.models.enums import InterviewStatus


ALLOWED_TRANSITIONS: dict[InterviewStatus, set[InterviewStatus]] = {
    InterviewStatus.DRAFT: {InterviewStatus.SCHEDULED, InterviewStatus.CANCELLED, InterviewStatus.FAILED},
    InterviewStatus.SCHEDULED: {InterviewStatus.IN_PROGRESS, InterviewStatus.CANCELLED, InterviewStatus.FAILED},
    InterviewStatus.IN_PROGRESS: {InterviewStatus.INTRO_DONE, InterviewStatus.CANCELLED, InterviewStatus.FAILED},
    InterviewStatus.INTRO_DONE: {InterviewStatus.THEORY_DONE, InterviewStatus.CANCELLED, InterviewStatus.FAILED},
    InterviewStatus.THEORY_DONE: {InterviewStatus.IDE_IN_PROGRESS, InterviewStatus.CANCELLED, InterviewStatus.FAILED},
    InterviewStatus.IDE_IN_PROGRESS: {InterviewStatus.AWAITING_AI_ANALYSIS, InterviewStatus.CANCELLED, InterviewStatus.FAILED},
    InterviewStatus.AWAITING_AI_ANALYSIS: {InterviewStatus.COMPLETED, InterviewStatus.FAILED},
    InterviewStatus.COMPLETED: {InterviewStatus.REVIEWED},
    InterviewStatus.REVIEWED: set(),
    InterviewStatus.CANCELLED: set(),
    InterviewStatus.FAILED: set(),
}


@dataclass
class InterviewStateMachine:
    status: InterviewStatus

    def to_scheduled(self) -> InterviewStatus:
        return self._transition(InterviewStatus.SCHEDULED)

    def start(self) -> InterviewStatus:
        return self._transition(InterviewStatus.IN_PROGRESS)

    def mark_intro_done(self) -> InterviewStatus:
        return self._transition(InterviewStatus.INTRO_DONE)

    def mark_theory_done(self) -> InterviewStatus:
        return self._transition(InterviewStatus.THEORY_DONE)

    def enter_ide(self) -> InterviewStatus:
        return self._transition(InterviewStatus.IDE_IN_PROGRESS)

    def await_analysis(self) -> InterviewStatus:
        return self._transition(InterviewStatus.AWAITING_AI_ANALYSIS)

    def complete(self) -> InterviewStatus:
        return self._transition(InterviewStatus.COMPLETED)

    def review(self) -> InterviewStatus:
        return self._transition(InterviewStatus.REVIEWED)

    def cancel(self) -> InterviewStatus:
        return self._transition(InterviewStatus.CANCELLED)

    def fail(self) -> InterviewStatus:
        return self._transition(InterviewStatus.FAILED)

    def _transition(self, to_status: InterviewStatus) -> InterviewStatus:
        allowed = ALLOWED_TRANSITIONS.get(self.status, set())
        if to_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f'Invalid interview transition: {self.status.value} -> {to_status.value}',
            )
        self.status = to_status
        return self.status
