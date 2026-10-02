"""Applied Foundations assessment, remediation, diagnostics, and snapshot finalization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel

from lake_effect_ledger.learning.engine import LearningEngine
from lake_effect_ledger.learning.models import (
    AssessmentQuestionSnapshot,
    AssessmentSnapshot,
    LearningStatus,
    ObjectiveEvidenceSnapshot,
    ObjectiveProgress,
    QuestionCategory,
    ReviewStyle,
    SeasonReviewResponse,
    SnapshotProvenance,
)
from lake_effect_ledger.learning.review import ReusableReviewEngine

if TYPE_CHECKING:
    from lake_effect_ledger.applied_foundations.models import AppliedQuestionDefinition
    from lake_effect_ledger.narrative.models import ContentBundle
    from lake_effect_ledger.state import GameState


@dataclass(frozen=True)
class AppliedReviewSubmission:
    question_id: str
    correct: bool
    completed: bool
    explanation: str
    feedback: str | None


class AppliedReviewDiagnostic(BaseModel):
    style: ReviewStyle
    required_questions: int
    required_first_attempt_correct: int
    required_final_correct: int
    calculation_first_attempt_correct: int
    calculation_total: int
    conceptual_first_attempt_correct: int
    conceptual_total: int
    hints_used: int
    walkthroughs_used: int
    recommended_remediation_categories: list[str]
    completed_remediation_ids: list[str]


class AppliedReviewEngine:
    state_attribute = "applied_foundations"
    season_id = "applied_foundations"
    season_label = "Applied Foundations"
    story_label = "The Supply Gap"
    review_chapter_id = "applied_foundations_review"
    snapshot_provenance = SnapshotProvenance.NATIVE_V10

    def __init__(self, content: ContentBundle, *, blueprint=None) -> None:
        self.content = content
        self.blueprint = blueprint or content.applied_foundations
        self.learning = LearningEngine(content)
        self.review_behavior = ReusableReviewEngine(self.learning)

    def start(self, state: GameState, style: ReviewStyle) -> None:
        chapter = self._chapter(state)
        if chapter.current_day_index != 3:
            raise ValueError(f"complete {self.story_label} before starting its review")
        review = chapter.review
        if review.started and review.style != style:
            raise ValueError(
                f"the saved {self.season_label} review already uses {review.style.value}"
            )
        review.started = True
        review.style = style

    def current_question(self, state: GameState) -> AppliedQuestionDefinition | None:
        review = self._chapter(state).review
        if not review.started or review.style is None:
            raise ValueError(f"{self.season_label} review has not started")
        if not review.required_completed:
            if review.current_required_index >= len(self.blueprint.review.required):
                return None
            return self.blueprint.review.required[review.current_required_index]
        if review.current_remediation_index >= len(review.selected_remediation_ids):
            return None
        question_id = review.selected_remediation_ids[review.current_remediation_index]
        return self.blueprint.question(question_id)

    def hint(self, state: GameState) -> str:
        review = self._chapter(state).review
        if review.style != ReviewStyle.LEARNING:
            raise ValueError("Checkpoint Review does not reveal hints before submission")
        question = self.current_question(state)
        if question is None:
            raise ValueError(f"there is no current {self.season_label} review question")
        response = self._response(state, question.id)
        return self.review_behavior.hint(question.id, response)

    def walkthrough(self, state: GameState) -> AppliedReviewSubmission:
        review = self._chapter(state).review
        if review.style != ReviewStyle.LEARNING:
            raise ValueError("Checkpoint Review does not offer walkthroughs before submission")
        question = self.current_question(state)
        if question is None:
            raise ValueError(f"there is no current {self.season_label} review question")
        response = self._response(state, question.id)
        self.review_behavior.walkthrough(response)
        self._record_objectives(state, question, response, correct=True, after_retry=False)
        self._advance(state)
        check = question.as_knowledge_check()
        return AppliedReviewSubmission(
            question_id=question.id,
            correct=True,
            completed=True,
            explanation=check.explanation,
            feedback=check.worked_solution,
        )

    def submit(self, state: GameState, answer: str) -> AppliedReviewSubmission:
        question = self.current_question(state)
        if question is None:
            raise ValueError(f"there is no current {self.season_label} review question")
        response = self._response(state, question.id)
        attempt = self.review_behavior.submit(
            check_id=question.id,
            response=response,
            answer=answer,
            style=self._chapter(state).review.style,
        )
        if attempt.completed:
            self._record_objectives(
                state,
                question,
                response,
                correct=attempt.correct,
                after_retry=attempt.after_retry,
            )
            self._advance(state)
        return AppliedReviewSubmission(
            question_id=question.id,
            correct=attempt.correct,
            completed=attempt.completed,
            explanation=question.as_knowledge_check().explanation,
            feedback=attempt.feedback,
        )

    def prepare_remediation(self, state: GameState, *, take_remediation: bool) -> list[str]:
        review = self._chapter(state).review
        if not review.required_completed:
            raise ValueError("complete the ten required questions before remediation")
        if review.selected_remediation_ids or review.remediation_declined:
            return list(review.selected_remediation_ids)
        if not take_remediation:
            review.remediation_declined = True
            review.completed = True
            return []
        categories = set(review.recommended_remediation_categories)
        review.selected_remediation_ids = [
            item.id
            for item in self.blueprint.review.remediation
            if item.remediation_category in categories
        ]
        if not review.selected_remediation_ids:
            review.completed = True
        return list(review.selected_remediation_ids)

    def diagnostic(self, state: GameState) -> AppliedReviewDiagnostic:
        review = self._chapter(state).review
        if not review.required_completed or review.style is None:
            raise ValueError(f"{self.season_label} diagnostic requires the ten required questions")
        required_ids = {item.id for item in self.blueprint.review.required}
        required_responses = [item for key, item in review.responses.items() if key in required_ids]
        calculations = [
            item
            for item in self.blueprint.review.required
            if item.category == QuestionCategory.CALCULATION
        ]
        concepts = [
            item
            for item in self.blueprint.review.required
            if item.category == QuestionCategory.CONCEPTUAL
        ]
        completed_remediation = [
            item.id
            for item in self.blueprint.review.remediation
            if item.id in review.responses and review.responses[item.id].final_correct
        ]
        return AppliedReviewDiagnostic(
            style=review.style,
            required_questions=len(self.blueprint.review.required),
            required_first_attempt_correct=sum(
                item.first_attempt_correct is True for item in required_responses
            ),
            required_final_correct=sum(item.final_correct for item in required_responses),
            calculation_first_attempt_correct=sum(
                review.responses[item.id].first_attempt_correct is True for item in calculations
            ),
            calculation_total=len(calculations),
            conceptual_first_attempt_correct=sum(
                review.responses[item.id].first_attempt_correct is True for item in concepts
            ),
            conceptual_total=len(concepts),
            hints_used=sum(item.hints_used for item in review.responses.values()),
            walkthroughs_used=sum(item.walkthrough_used for item in review.responses.values()),
            recommended_remediation_categories=list(review.recommended_remediation_categories),
            completed_remediation_ids=completed_remediation,
        )

    def finalize_snapshot(self, state: GameState) -> AssessmentSnapshot:
        chapter = self._chapter(state)
        review = chapter.review
        if not review.completed:
            raise ValueError("finish or decline Applied remediation before finalizing")
        if any(item.season_id == self.season_id for item in state.learning.assessment_snapshots):
            raise ValueError(f"the {self.season_label} snapshot is append-only")
        selected = [
            *self.blueprint.review.required,
            *[self.blueprint.question(item) for item in review.selected_remediation_ids],
        ]
        question_snapshots = tuple(
            self._question_snapshot(
                question,
                review.responses.get(question.id),
                remediation=question.id in review.selected_remediation_ids,
            )
            for question in selected
        )
        objective_ids = sorted({objective for item in selected for objective in item.objectives})
        objective_evidence = tuple(
            self._objective_snapshot(state, objective_id, selected)
            for objective_id in objective_ids
        )
        calculations = [
            item
            for item in question_snapshots
            if not item.remediation and item.category == QuestionCategory.CALCULATION
        ]
        concepts = [
            item
            for item in question_snapshots
            if not item.remediation and item.category == QuestionCategory.CONCEPTUAL
        ]
        snapshot = AssessmentSnapshot(
            season_id=self.season_id,
            completed_story_date=self.blueprint.season.end_date,
            provenance=self.snapshot_provenance,
            questions=question_snapshots,
            objective_evidence=objective_evidence,
            calculation_first_attempt_correct=sum(
                item.first_attempt_correct is True for item in calculations
            ),
            calculation_first_attempt_total=len(calculations),
            conceptual_first_attempt_correct=sum(
                item.first_attempt_correct is True for item in concepts
            ),
            conceptual_first_attempt_total=len(concepts),
        )
        state.learning.assessment_snapshots.append(snapshot)
        chapter.snapshot_finalized = True
        return snapshot

    def _advance(self, state: GameState) -> None:
        review = self._chapter(state).review
        if not review.required_completed:
            review.current_required_index += 1
            if review.current_required_index == len(self.blueprint.review.required):
                review.required_completed = True
                review.recommended_remediation_categories = self._remediation_categories(state)
                if not review.recommended_remediation_categories:
                    review.completed = True
            return
        review.current_remediation_index += 1
        if review.current_remediation_index == len(review.selected_remediation_ids):
            review.completed = True

    def _remediation_categories(self, state: GameState) -> list[str]:
        review = self._chapter(state).review
        categories: list[str] = []
        for question in self.blueprint.review.required:
            response = review.responses[question.id]
            needs_help = (
                response.first_attempt_correct is not True
                or response.hints_used > 0
                or response.walkthrough_used
            )
            if needs_help and question.remediation_category not in categories:
                categories.append(question.remediation_category)
        return categories

    def _response(self, state: GameState, question_id: str) -> SeasonReviewResponse:
        return self._chapter(state).review.responses.setdefault(
            question_id,
            SeasonReviewResponse(question_id=question_id),
        )

    def _record_objectives(
        self,
        state: GameState,
        question: AppliedQuestionDefinition,
        response: SeasonReviewResponse,
        *,
        correct: bool,
        after_retry: bool,
    ) -> None:
        for objective_id in question.objectives:
            objective = state.learning.objectives.setdefault(
                objective_id,
                ObjectiveProgress(),
            )
            if self.review_chapter_id not in objective.chapter_ids:
                objective.chapter_ids.append(self.review_chapter_id)
            if question.id not in objective.check_ids:
                objective.check_ids.append(question.id)
            objective.attempts += 1
            if not correct:
                objective.status = LearningStatus.REVIEW_RECOMMENDED
                continue
            objective.correct_applications += 1
            if response.walkthrough_used or response.hints_used:
                objective.assisted_completions += 1
                objective.status = LearningStatus.PRACTICED_WITH_HELP
            elif after_retry:
                objective.retry_demonstrations += 1
                objective.status = LearningStatus.DEMONSTRATED_AFTER_RETRY
            else:
                objective.independent_demonstrations += 1
                objective.status = LearningStatus.DEMONSTRATED_INDEPENDENTLY

    def _question_snapshot(
        self,
        question: AppliedQuestionDefinition,
        response: SeasonReviewResponse | None,
        *,
        remediation: bool,
    ) -> AssessmentQuestionSnapshot:
        if response is None:
            raise ValueError(f"missing {self.season_label} response for {question.id}")
        return AssessmentQuestionSnapshot(
            question_id=question.id,
            check_id=question.id,
            category=question.category,
            remediation=remediation,
            first_answer=response.first_answer,
            first_attempt_correct=response.first_attempt_correct,
            final_answer=response.final_answer,
            final_correct=response.final_correct,
            attempts=response.attempts,
            hints_used=response.hints_used,
            walkthrough_used=response.walkthrough_used,
            independently_demonstrated=response.independently_demonstrated,
        )

    def _objective_snapshot(
        self,
        state: GameState,
        objective_id: str,
        questions: list[AppliedQuestionDefinition],
    ) -> ObjectiveEvidenceSnapshot:
        required = tuple(
            item.id for item in self.blueprint.review.required if objective_id in item.objectives
        )
        remediation = tuple(
            item.id
            for item in self.blueprint.review.remediation
            if item.id in self._chapter(state).review.selected_remediation_ids
            and objective_id in item.objectives
        )
        responses = [
            self._chapter(state).review.responses[item.id]
            for item in questions
            if objective_id in item.objectives
        ]
        story_days = tuple(
            day.id
            for day in self.blueprint.days
            if any(
                objective_id in self.blueprint.question(check_id).objectives
                for check_id in day.check_ids
            )
        )
        progress = state.learning.objectives.get(objective_id)
        return ObjectiveEvidenceSnapshot(
            objective_id=objective_id,
            story_application_ids=story_days,
            required_question_ids=required,
            remediation_question_ids=remediation,
            first_attempt_correct=sum(item.first_attempt_correct is True for item in responses),
            final_correct=sum(item.final_correct for item in responses),
            assistance_used=any(item.hints_used or item.walkthrough_used for item in responses),
            demonstrated_status=progress.status if progress is not None else None,
        )

    def _chapter(self, state: GameState):
        return getattr(state, self.state_attribute)
