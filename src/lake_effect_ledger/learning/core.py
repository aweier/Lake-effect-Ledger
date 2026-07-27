"""Series 3 Core review, chapter summaries, and honest cumulative debrief."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from pydantic import BaseModel

from lake_effect_ledger.learning.calculations import calculate_answer
from lake_effect_ledger.learning.engine import LearningEngine
from lake_effect_ledger.learning.models import (
    CoreReviewResponse,
    KnowledgeCheckType,
    LearningStatus,
    ObjectiveProgress,
    ReviewStyle,
)
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.state import GameState


@dataclass(frozen=True)
class ReviewSubmission:
    question_id: str
    check_id: str
    correct: bool
    completed: bool
    explanation: str
    feedback: str | None


class CoreReviewDiagnostic(BaseModel):
    style: ReviewStyle
    total_questions: int
    first_attempt_correct: int
    first_attempt_unknown: int
    final_correct: int
    hints_used: int
    walkthroughs_used: int
    review_recommended_ids: list[str]


class CoreDebrief(BaseModel):
    objectives_introduced: list[str]
    objectives_independently_demonstrated: list[str]
    objectives_completed_with_help: list[str]
    objectives_recommended_for_review: list[str]
    core_topics_not_encountered: list[str]
    future_curriculum_topics: list[str]
    calculation_accuracy: str
    concept_accuracy: str
    strengths: list[str]
    suggested_next_study_area: str
    source_titles: list[str]
    disclaimer: str


class CoreReviewEngine:
    """Runs a review without erasing first-attempt history from chapter checks."""

    def __init__(self, content: ContentBundle) -> None:
        self.content = content
        self.learning = LearningEngine(content)

    def start(self, state: GameState, style: ReviewStyle) -> None:
        review = state.learning.core_review
        if review.started and review.style != style:
            raise ValueError(f"the saved review already uses {review.style.value}")
        review.started = True
        review.style = style

    def current_reference(self, state: GameState):
        review = state.learning.core_review
        if not review.started or review.style is None:
            raise ValueError("core review has not started")
        if review.current_question_index >= len(self.content.curriculum.review_questions):
            return None
        return self.content.curriculum.review_questions[review.current_question_index]

    def hint(self, state: GameState) -> str:
        review = state.learning.core_review
        if review.style != ReviewStyle.LEARNING:
            raise ValueError("Checkpoint Review does not reveal hints before submission")
        reference = self.current_reference(state)
        response = self._response(state, reference.id, reference.check_id)
        response.hints_used += 1
        check = self.content.knowledge_check(reference.check_id)
        return check.hints[min(response.hints_used - 1, len(check.hints) - 1)]

    def walkthrough(self, state: GameState) -> ReviewSubmission:
        review = state.learning.core_review
        if review.style != ReviewStyle.LEARNING:
            raise ValueError("Checkpoint Review does not offer walkthroughs before submission")
        reference = self.current_reference(state)
        check = self.content.knowledge_check(reference.check_id)
        response = self._response(state, reference.id, reference.check_id)
        response.walkthrough_used = True
        response.final_correct = True
        response.explanation_shown = True
        self._record_objectives(
            state,
            check.learning_objective_ids,
            response=response,
            correct=True,
            after_retry=False,
        )
        self._advance(state)
        return ReviewSubmission(
            question_id=reference.id,
            check_id=reference.check_id,
            correct=True,
            completed=True,
            explanation=check.explanation,
            feedback=check.worked_solution,
        )

    def submit(self, state: GameState, answer: str) -> ReviewSubmission:
        reference = self.current_reference(state)
        check = self.content.knowledge_check(reference.check_id)
        response = self._response(state, reference.id, reference.check_id)
        response.attempts += 1
        correct = self.learning.answer_is_correct(reference.check_id, answer)
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
        checkpoint = state.learning.core_review.style == ReviewStyle.CHECKPOINT
        completed = correct or checkpoint
        if completed:
            response.explanation_shown = checkpoint
            self._record_objectives(
                state,
                check.learning_objective_ids,
                response=response,
                correct=correct,
                after_retry=after_retry,
            )
            self._advance(state)
        feedback = None
        if not correct:
            feedback = self.learning.wrong_answer_feedback(reference.check_id, answer)
        return ReviewSubmission(
            question_id=reference.id,
            check_id=reference.check_id,
            correct=correct,
            completed=completed,
            explanation=check.explanation,
            feedback=feedback,
        )

    def diagnostic(self, state: GameState) -> CoreReviewDiagnostic:
        review = state.learning.core_review
        if not review.completed or review.style is None:
            raise ValueError("diagnostic requires a completed core review")
        responses = list(review.responses.values())
        return CoreReviewDiagnostic(
            style=review.style,
            total_questions=len(self.content.curriculum.review_questions),
            first_attempt_correct=sum(item.first_attempt_correct is True for item in responses),
            first_attempt_unknown=sum(item.first_attempt_correct is None for item in responses),
            final_correct=sum(item.final_correct for item in responses),
            hints_used=sum(item.hints_used for item in responses),
            walkthroughs_used=sum(item.walkthrough_used for item in responses),
            review_recommended_ids=[
                item.question_id
                for item in responses
                if item.first_attempt_correct is not True
                or item.hints_used
                or item.walkthrough_used
            ],
        )

    @staticmethod
    def _response(
        state: GameState,
        question_id: str,
        check_id: str,
    ) -> CoreReviewResponse:
        return state.learning.core_review.responses.setdefault(
            question_id,
            CoreReviewResponse(question_id=question_id, check_id=check_id),
        )

    def _advance(self, state: GameState) -> None:
        review = state.learning.core_review
        review.current_question_index += 1
        if review.current_question_index == len(self.content.curriculum.review_questions):
            review.completed = True

    @staticmethod
    def _record_objectives(
        state: GameState,
        objective_ids: list[str],
        *,
        response: CoreReviewResponse,
        correct: bool,
        after_retry: bool,
    ) -> None:
        for objective_id in objective_ids:
            objective = state.learning.objectives.setdefault(objective_id, ObjectiveProgress())
            if "core_review" not in objective.chapter_ids:
                objective.chapter_ids.append("core_review")
            if response.question_id not in objective.check_ids:
                objective.check_ids.append(response.question_id)
            objective.attempts += response.attempts
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


def chapter_calculation_lines(
    state: GameState,
    content: ContentBundle,
    chapter_id: str,
) -> list[str]:
    """Format only values produced by shared engines or validated check calculations."""
    if chapter_id == "first_rotation":
        lines: list[str] = []
        for check in content.prologue.checks:
            if check.check_type != KnowledgeCheckType.NUMERIC:
                continue
            progress = state.learning.checks.get(check.id)
            if progress is None or not progress.completed:
                continue
            answer = calculate_answer(check, content)
            lines.append(f"{check.id}: {answer} {check.numeric_rule.answer_unit}")
        return lines
    if chapter_id == "december_difference":
        return [
            f"{entry.transaction_id}: debits ${entry.total_debits:,.2f}; "
            f"credits ${entry.total_credits:,.2f}"
            for entry in state.ledger.entries
            if entry.source_id != "game_setup"
        ] or ["No journal amount was posted; the unresolved item remained in evidence."]
    if chapter_id == "hedge_book" and state.hedge_book is not None:
        return [
            (
                f"{item.settlement_date}: Chicago ${item.chicago_price:.3f}/MMBtu; "
                f"futures P&L ${item.daily_futures_pnl:+,.2f}; "
                f"margin call ${item.margin_call_amount:,.2f}"
            )
            for item in state.hedge_book.settlements
        ]
    if chapter_id == "two_oclock_call" and state.treasury is not None:
        latest = state.treasury.liquidity_snapshots[-1]
        return [
            f"FCM call: ${state.treasury.original_margin_call_amount:,.2f}",
            f"Operating cash: ${state.corporate_cash:,.2f}",
            f"Available liquidity: ${latest.available_liquidity:,.2f}",
        ]
    if chapter_id == "eleventh_contract" and state.eleventh_contract is not None:
        chapter = state.eleventh_contract
        return [
            (
                f"Authorized {chapter.authorization.maximum_quantity}; executed "
                f"{chapter.execution.quantity}; confirmed {chapter.confirmation.quantity}"
            ),
            (
                f"Supported {chapter.blotter.supported_physical_volume_mmbtu:,.0f} "
                f"MMBtu; hedge ratio {chapter.blotter.hedge_ratio:.0%}"
            ),
            (
                f"Daily futures P&L ${chapter.blotter.daily_pnl:+,.2f}; "
                f"margin ${chapter.blotter.margin_requirement:,.2f}"
            ),
        ]
    return []


def build_core_debrief(state: GameState, content: ContentBundle) -> CoreDebrief:
    core_objectives = [item for item in content.curriculum.objectives if item.counts_toward_core]
    progress_by_id = state.learning.objectives

    def labels(objectives) -> list[str]:
        return [item.game_concept_label for item in objectives]

    introduced = [
        item
        for item in core_objectives
        if progress_by_id.get(item.id, ObjectiveProgress()).status != LearningStatus.UNSEEN
    ]
    independent = [
        item
        for item in core_objectives
        if progress_by_id.get(item.id, ObjectiveProgress()).independent_demonstrations > 0
    ]
    assisted = [
        item
        for item in core_objectives
        if progress_by_id.get(item.id, ObjectiveProgress()).assisted_completions > 0
    ]
    review = [
        item
        for item in core_objectives
        if progress_by_id.get(item.id, ObjectiveProgress()).status
        in {
            LearningStatus.REVIEW_RECOMMENDED,
            LearningStatus.PRACTICED_WITH_HELP,
            LearningStatus.DEMONSTRATED_AFTER_RETRY,
            LearningStatus.COMPLETED_HISTORY_UNKNOWN,
        }
    ]
    not_encountered = [item for item in core_objectives if item not in introduced]

    completed_checks = [
        (content.knowledge_check(check_id), progress)
        for check_id, progress in state.learning.checks.items()
        if progress.completed
    ]
    numeric = [
        progress
        for check, progress in completed_checks
        if check.check_type == KnowledgeCheckType.NUMERIC
    ]
    concepts = [
        progress
        for check, progress in completed_checks
        if check.check_type != KnowledgeCheckType.NUMERIC
    ]
    review_responses = list(state.learning.core_review.responses.values())
    numeric_review = [
        response
        for response in review_responses
        if content.knowledge_check(response.check_id).check_type == KnowledgeCheckType.NUMERIC
    ]
    concept_review = [
        response
        for response in review_responses
        if content.knowledge_check(response.check_id).check_type != KnowledgeCheckType.NUMERIC
    ]

    calculation_correct = sum(item.first_attempt_correct is True for item in numeric)
    calculation_total = len(numeric)
    calculation_correct += sum(item.first_attempt_correct is True for item in numeric_review)
    calculation_total += len(numeric_review)
    concept_correct = sum(item.first_attempt_correct is True for item in concepts)
    concept_total = len(concepts)
    concept_correct += sum(item.first_attempt_correct is True for item in concept_review)
    concept_total += len(concept_review)

    strengths = labels(independent)[:5] or ["No objective has independent evidence yet."]
    suggested = (
        review[0].game_concept_label
        if review
        else (
            content.curriculum.future_topics[0].official_topic_label
            if content.curriculum.future_topics
            else "Continue with an independent Series 3 study program."
        )
    )
    source_ids = {item.source_id for item in core_objectives} | {
        content.curriculum.outline.source_id
    }
    return CoreDebrief(
        objectives_introduced=labels(introduced),
        objectives_independently_demonstrated=labels(independent),
        objectives_completed_with_help=labels(assisted),
        objectives_recommended_for_review=labels(review),
        core_topics_not_encountered=labels(not_encountered),
        future_curriculum_topics=[
            item.official_topic_label for item in content.curriculum.future_topics
        ],
        calculation_accuracy=_accuracy_text(calculation_correct, calculation_total),
        concept_accuracy=_accuracy_text(concept_correct, concept_total),
        strengths=strengths,
        suggested_next_study_area=suggested,
        source_titles=[content.source(item).title for item in sorted(source_ids)],
        disclaimer=(
            "This diagnostic reflects only concepts implemented and encountered in "
            "Lake Effect Ledger. It is not a complete Series 3 mock exam or an "
            "exam-readiness score."
        ),
    )


def _accuracy_text(correct: int, total: int) -> str:
    if total == 0:
        return "No first-attempt evidence available."
    percent = (Decimal(correct) / Decimal(total) * Decimal("100")).quantize(Decimal("0.1"))
    return f"{correct}/{total} first attempts correct ({percent}%)."
