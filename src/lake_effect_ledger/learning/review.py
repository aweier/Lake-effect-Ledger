"""Reusable first-attempt-preserving behavior for season review wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from lake_effect_ledger.learning.engine import LearningEngine
from lake_effect_ledger.learning.models import ReviewStyle


class MutableReviewResponse(Protocol):
    first_answer: str | None
    first_attempt_correct: bool | None
    final_answer: str | None
    attempts: int
    hints_used: int
    walkthrough_used: bool
    final_correct: bool
    independently_demonstrated: bool
    explanation_shown: bool


@dataclass(frozen=True)
class ReviewAttempt:
    correct: bool
    completed: bool
    after_retry: bool
    feedback: str | None


class ReusableReviewEngine:
    """Own answer/history mechanics while season wrappers own sequencing and evidence."""

    def __init__(self, learning: LearningEngine) -> None:
        self.learning = learning

    def hint(self, check_id: str, response: MutableReviewResponse) -> str:
        response.hints_used += 1
        check = self.learning.content.knowledge_check(check_id)
        return check.hints[min(response.hints_used - 1, len(check.hints) - 1)]

    @staticmethod
    def walkthrough(response: MutableReviewResponse) -> None:
        response.walkthrough_used = True
        response.final_answer = None
        response.final_correct = True
        response.explanation_shown = True

    def submit(
        self,
        *,
        check_id: str,
        response: MutableReviewResponse,
        answer: str,
        style: ReviewStyle,
    ) -> ReviewAttempt:
        response.attempts += 1
        response.final_answer = answer
        correct = self.learning.answer_is_correct(check_id, answer)
        if response.attempts == 1:
            response.first_answer = answer
            response.first_attempt_correct = correct
        after_retry = response.attempts > 1
        if correct:
            response.final_correct = True
            response.independently_demonstrated = (
                response.attempts == 1
                and response.hints_used == 0
                and not response.walkthrough_used
            )
        completed = correct or style == ReviewStyle.CHECKPOINT
        if completed:
            response.explanation_shown = style == ReviewStyle.CHECKPOINT
        return ReviewAttempt(
            correct=correct,
            completed=completed,
            after_retry=after_retry,
            feedback=(None if correct else self.learning.wrong_answer_feedback(check_id, answer)),
        )
