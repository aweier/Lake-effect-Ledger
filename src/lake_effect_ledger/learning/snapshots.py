"""Immutable historical assessment snapshots for Core and later seasons."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lake_effect_ledger.learning.models import (
    AssessmentQuestionSnapshot,
    AssessmentSnapshot,
    KnowledgeCheckType,
    ObjectiveEvidenceSnapshot,
    QuestionCategory,
    SnapshotProvenance,
)

if TYPE_CHECKING:
    from lake_effect_ledger.narrative.models import ContentBundle
    from lake_effect_ledger.state import GameState


def finalize_core_snapshot(
    state: GameState,
    content: ContentBundle,
    *,
    provenance: SnapshotProvenance = SnapshotProvenance.NATIVE_V10,
) -> AssessmentSnapshot:
    existing = next(
        (item for item in state.learning.assessment_snapshots if item.season_id == "series3_core"),
        None,
    )
    if existing is not None:
        raise ValueError("the Series 3 Core snapshot is append-only")
    review = state.learning.core_review
    if not state.core_campaign_completed and not review.completed:
        raise ValueError("cannot snapshot an incomplete Series 3 Core assessment")
    references = content.curriculum.review_questions
    complete_history = (
        review.completed
        and len(review.responses) == len(references)
        and all(
            reference.id in review.responses
            and (
                review.responses[reference.id].attempts > 0
                or review.responses[reference.id].walkthrough_used
            )
            for reference in references
        )
    )
    if provenance == SnapshotProvenance.RECONSTRUCTED_FROM_V9 and not complete_history:
        provenance = SnapshotProvenance.LEGACY_ATTEMPT_HISTORY_UNKNOWN
    questions = tuple(
        _core_question_snapshot(
            state,
            content,
            reference.id,
            reference.check_id,
            history_known=(provenance != SnapshotProvenance.LEGACY_ATTEMPT_HISTORY_UNKNOWN),
        )
        for reference in references
    )
    calculation_questions = [
        item for item in questions if item.category == QuestionCategory.CALCULATION
    ]
    conceptual_questions = [
        item for item in questions if item.category == QuestionCategory.CONCEPTUAL
    ]
    objective_evidence = tuple(
        _core_objective_snapshot(state, content, objective.id)
        for objective in content.curriculum.objectives
        if objective.counts_toward_core
    )
    history_known = provenance != SnapshotProvenance.LEGACY_ATTEMPT_HISTORY_UNKNOWN
    snapshot = AssessmentSnapshot(
        season_id="series3_core",
        completed_story_date=content.eleventh_scenario.day_3_date,
        provenance=provenance,
        questions=questions,
        objective_evidence=objective_evidence,
        calculation_first_attempt_correct=(
            sum(item.first_attempt_correct is True for item in calculation_questions)
            if history_known
            else None
        ),
        calculation_first_attempt_total=len(calculation_questions),
        conceptual_first_attempt_correct=(
            sum(item.first_attempt_correct is True for item in conceptual_questions)
            if history_known
            else None
        ),
        conceptual_first_attempt_total=len(conceptual_questions),
    )
    state.learning.assessment_snapshots.append(snapshot)
    return snapshot


def _core_question_snapshot(
    state: GameState,
    content: ContentBundle,
    question_id: str,
    check_id: str,
    *,
    history_known: bool,
) -> AssessmentQuestionSnapshot:
    response = state.learning.core_review.responses.get(question_id)
    check = content.knowledge_check(check_id)
    if not history_known:
        response = None
    return AssessmentQuestionSnapshot(
        question_id=question_id,
        check_id=check_id,
        category=(
            QuestionCategory.CALCULATION
            if check.check_type == KnowledgeCheckType.NUMERIC
            else QuestionCategory.CONCEPTUAL
        ),
        first_answer=response.first_answer if response is not None else None,
        first_attempt_correct=(response.first_attempt_correct if response is not None else None),
        final_answer=response.final_answer if response is not None else None,
        final_correct=response.final_correct if response is not None else None,
        attempts=response.attempts if response is not None else None,
        hints_used=response.hints_used if response is not None else None,
        walkthrough_used=response.walkthrough_used if response is not None else None,
        independently_demonstrated=(
            response.independently_demonstrated if response is not None else None
        ),
    )


def _core_objective_snapshot(
    state: GameState,
    content: ContentBundle,
    objective_id: str,
) -> ObjectiveEvidenceSnapshot:
    objective = content.curriculum_objective(objective_id)
    question_ids = tuple(
        reference.id
        for reference in content.curriculum.review_questions
        if objective_id in content.knowledge_check(reference.check_id).learning_objective_ids
    )
    responses = [
        state.learning.core_review.responses[item]
        for item in question_ids
        if item in state.learning.core_review.responses
    ]
    progress = state.learning.objectives.get(objective_id)
    return ObjectiveEvidenceSnapshot(
        objective_id=objective_id,
        story_application_ids=tuple(objective.chapter_ids),
        required_question_ids=question_ids,
        first_attempt_correct=(
            sum(item.first_attempt_correct is True for item in responses)
            if responses and all(item.first_attempt_correct is not None for item in responses)
            else None
        ),
        final_correct=(sum(item.final_correct for item in responses) if responses else None),
        assistance_used=(
            any(item.hints_used or item.walkthrough_used for item in responses)
            if responses
            else None
        ),
        demonstrated_status=progress.status if progress is not None else None,
    )
