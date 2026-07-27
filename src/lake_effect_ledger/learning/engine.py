"""Retryable learning rules kept separate from durable narrative consequences."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_HALF_UP

from lake_effect_ledger.learning.calculations import (
    calculate_answer,
    numeric_answer_matches,
)
from lake_effect_ledger.learning.models import (
    KnowledgeCheckDefinition,
    KnowledgeCheckProgress,
    KnowledgeCheckType,
    LearningStatus,
    ObjectiveProgress,
    TutorialDayDefinition,
)
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.state import GameState


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    correct: bool
    completed: bool
    independent: bool
    explanation: str
    worked_solution: str | None = None
    wrong_answer_feedback: str | None = None


class LearningEngine:
    """Owns tutorial progress; it has no API for moral or market effects."""

    def __init__(self, content: ContentBundle) -> None:
        self.content = content

    def introduce_day(self, state: GameState, day: TutorialDayDefinition) -> None:
        state.prologue.started = True
        state.prologue.current_day_index = day.day_number - 1
        state.current_date = self.content.prologue.prologue.start_date + timedelta(
            days=day.day_number - 1
        )
        for panel in day.concept_panels:
            for objective_id in panel.learning_objective_ids:
                objective = self._objective(state, objective_id)
                if objective.status == LearningStatus.UNSEEN:
                    objective.status = LearningStatus.INTRODUCED
                self._append_unique(objective.chapter_ids, "first_rotation")
            for glossary_id in panel.glossary_ids:
                self._append_unique(state.learning.notebook.unlocked_glossary_ids, glossary_id)
        state.record(
            phase="system",
            event_type="learning_day_started",
            source_id=day.id,
            message=f"{day.title} started.",
        )

    def hint(self, state: GameState, check_id: str) -> str:
        check = self.content.knowledge_check(check_id)
        progress = self._progress(state, check_id)
        if progress.completed:
            raise ValueError(f"knowledge check already completed: {check_id}")
        progress.hints_used += 1
        for objective_id in check.learning_objective_ids:
            objective = self._objective(state, objective_id)
            objective.help_uses += 1
            objective.status = LearningStatus.PRACTICED_WITH_HELP
            self._append_unique(objective.check_ids, check_id)
        return check.hints[min(progress.hints_used - 1, len(check.hints) - 1)]

    def walkthrough(self, state: GameState, check_id: str) -> CheckResult:
        check = self.content.knowledge_check(check_id)
        progress = self._progress(state, check_id)
        if progress.completed:
            raise ValueError(f"knowledge check already completed: {check_id}")
        protected = self._protected_snapshot(state)
        progress.hints_used += 1
        progress.walkthrough_used = True
        progress.completed = True
        progress.independently_demonstrated = False
        progress.final_correct = True
        progress.review_recommended = True
        progress.last_answer = None
        self._append_unique(state.learning.notebook.worked_example_ids, check_id)
        self._append_unique(state.learning.notebook.review_check_ids, check_id)
        for objective_id in check.learning_objective_ids:
            objective = self._objective(state, objective_id)
            objective.help_uses += 1
            objective.last_check_id = check_id
            self._append_unique(objective.check_ids, check_id)
            objective.correct_applications += 1
            objective.assisted_completions += 1
            objective.status = LearningStatus.PRACTICED_WITH_HELP
        for objective_id in check.learning_objective_ids:
            self._refresh_objective_status(state, objective_id)
        self._assert_protected_unchanged(state, protected)
        return CheckResult(
            check_id=check_id,
            correct=True,
            completed=True,
            independent=False,
            explanation=check.explanation,
            worked_solution=check.worked_solution,
        )

    def submit(self, state: GameState, check_id: str, answer: str) -> CheckResult:
        check = self.content.knowledge_check(check_id)
        progress = self._progress(state, check_id)
        if progress.completed:
            raise ValueError(f"knowledge check already completed: {check_id}")
        protected = self._protected_snapshot(state)
        progress.attempts += 1
        progress.last_answer = answer
        correct = self._answer_is_correct(check, answer)
        if progress.attempts == 1:
            progress.first_answer = answer
            progress.first_attempt_correct = correct
        if not correct:
            progress.incorrect_attempts += 1
            self._append_unique(state.learning.notebook.review_check_ids, check_id)
            if progress.incorrect_attempts >= 2:
                progress.review_recommended = True
        for objective_id in check.learning_objective_ids:
            objective = self._objective(state, objective_id)
            objective.attempts += 1
            objective.last_check_id = check_id
            self._append_unique(objective.check_ids, check_id)
            if correct:
                objective.correct_applications += 1
                if progress.hints_used or progress.walkthrough_used:
                    objective.assisted_completions += 1
                elif progress.attempts == 1:
                    objective.independent_demonstrations += 1
                else:
                    objective.retry_demonstrations += 1
        if correct:
            progress.completed = True
            progress.final_correct = True
            progress.independently_demonstrated = (
                progress.attempts == 1 and not progress.hints_used and not progress.walkthrough_used
            )
            if (
                not progress.review_recommended
                and check_id in state.learning.notebook.review_check_ids
            ):
                state.learning.notebook.review_check_ids.remove(check_id)
        for objective_id in check.learning_objective_ids:
            self._refresh_objective_status(state, objective_id)
        self._assert_protected_unchanged(state, protected)
        return CheckResult(
            check_id=check_id,
            correct=correct,
            completed=correct,
            independent=progress.independently_demonstrated,
            explanation=check.explanation,
            wrong_answer_feedback=(
                None if correct else self.wrong_answer_feedback(check_id, answer)
            ),
        )

    def wrong_answer_feedback(self, check_id: str, answer: str) -> str:
        check = self.content.knowledge_check(check_id)
        if check.check_type == KnowledgeCheckType.NUMERIC:
            expected = self.expected_answer(check_id)
            return (
                f"{check.numeric_wrong_answer_feedback} "
                f"Expected {expected} {check.numeric_rule.answer_unit}."
            )
        return check.wrong_answer_feedback.get(
            answer,
            (
                "That response is not one of the authored choices. "
                + " ".join(
                    f"{item.text}: "
                    + (
                        "correct"
                        if item.id == check.correct_option_id
                        else check.wrong_answer_feedback[item.id]
                    )
                    for item in check.options
                )
            ),
        )

    def answer_is_correct(self, check_id: str, answer: str) -> bool:
        return self._answer_is_correct(self.content.knowledge_check(check_id), answer)

    def introduce_objectives(
        self,
        state: GameState,
        objective_ids: list[str],
        *,
        chapter_id: str,
    ) -> None:
        for objective_id in objective_ids:
            objective = self._objective(state, objective_id)
            if objective.status == LearningStatus.UNSEEN:
                objective.status = LearningStatus.INTRODUCED
            self._append_unique(objective.chapter_ids, chapter_id)

    def complete_day(
        self,
        state: GameState,
        day: TutorialDayDefinition,
        *,
        require_checks: bool = True,
    ) -> None:
        incomplete = [
            check_id for check_id in day.check_ids if not self._progress(state, check_id).completed
        ]
        if require_checks and incomplete:
            raise ValueError(f"cannot complete {day.id}; incomplete checks: {incomplete}")
        self._append_unique(state.learning.completed_day_ids, day.id)
        state.prologue.current_day_index = day.day_number
        state.prologue.current_check_index = 0
        state.record(
            phase="system",
            event_type="learning_day_completed",
            source_id=day.id,
            message=f"{day.title} completed.",
        )

    def complete_prologue(self, state: GameState) -> None:
        expected_days = [item.id for item in self.content.prologue.prologue.days]
        if state.learning.completed_day_ids != expected_days:
            raise ValueError("all First Rotation days must be completed in order")
        state.prologue.completed = True
        state.prologue.transitioned_to_episode_1 = True
        state.prologue.current_day_index = 3
        state.prologue.current_check_index = 0
        state.current_date = self.content.markets.scenarios[0].game_date
        state.record(
            phase="system",
            event_type="prologue_completed",
            source_id=self.content.prologue.prologue.id,
            message="First Rotation completed; Episode 1 is now available.",
        )

    def skip_prologue(self, state: GameState) -> None:
        if state.prologue.completed and state.prologue.transitioned_to_episode_1:
            return
        state.prologue.completed = True
        state.prologue.skipped = True
        state.prologue.transitioned_to_episode_1 = True
        state.prologue.current_day_index = 3
        state.prologue.current_check_index = 0
        state.current_date = self.content.markets.scenarios[0].game_date
        state.record(
            phase="system",
            event_type="prologue_skipped",
            source_id=self.content.prologue.prologue.id,
            message="First Rotation skipped without awarding learning progress.",
        )

    def expected_answer(self, check_id: str) -> str:
        check = self.content.knowledge_check(check_id)
        if check.check_type == KnowledgeCheckType.NUMERIC:
            expected = calculate_answer(check, self.content)
            return format(
                expected.quantize(
                    check.numeric_rule.rounding_quantum,
                    rounding=ROUND_HALF_UP,
                ),
                "f",
            )
        return str(check.correct_option_id)

    def _answer_is_correct(self, check: KnowledgeCheckDefinition, answer: str) -> bool:
        if check.check_type == KnowledgeCheckType.NUMERIC:
            expected = calculate_answer(check, self.content)
            return numeric_answer_matches(
                answer,
                expected=expected,
                quantum=check.numeric_rule.rounding_quantum,
                tolerance=check.numeric_rule.tolerance,
            )
        return answer.strip().lower() == check.correct_option_id

    @staticmethod
    def _objective(state: GameState, objective_id: str) -> ObjectiveProgress:
        return state.learning.objectives.setdefault(objective_id, ObjectiveProgress())

    @staticmethod
    def _progress(state: GameState, check_id: str) -> KnowledgeCheckProgress:
        return state.learning.checks.setdefault(check_id, KnowledgeCheckProgress(check_id=check_id))

    def _refresh_objective_status(self, state: GameState, objective_id: str) -> None:
        objective = self._objective(state, objective_id)
        checks = [
            state.learning.checks[check_id]
            for check_id in objective.check_ids
            if check_id in state.learning.checks
        ]
        if any(item.incorrect_attempts >= 2 for item in checks):
            objective.status = LearningStatus.REVIEW_RECOMMENDED
        elif any(item.independently_demonstrated for item in checks):
            objective.status = LearningStatus.DEMONSTRATED_INDEPENDENTLY
        elif any(item.final_correct and item.incorrect_attempts for item in checks):
            objective.status = LearningStatus.DEMONSTRATED_AFTER_RETRY
        elif any(item.final_correct for item in checks):
            objective.status = LearningStatus.PRACTICED_WITH_HELP
        elif checks and objective.status == LearningStatus.UNSEEN:
            objective.status = LearningStatus.INTRODUCED

    @staticmethod
    def _append_unique(values: list[str], value: str) -> None:
        if value not in values:
            values.append(value)

    @staticmethod
    def _protected_snapshot(state: GameState) -> dict[str, object]:
        return {
            "resources": state.resources.model_dump(mode="json"),
            "cash": (state.corporate_cash, state.personal_cash, state.margin_due),
            "ledger": state.ledger.model_dump(mode="json"),
            "flags": dict(state.flags),
            "decisions": list(state.decisions),
            "evidence": [item.model_dump(mode="json") for item in state.evidence_log],
            "trajectory": state.career_trajectory.model_dump(mode="json"),
            "hedge_book": (
                state.hedge_book.model_dump(mode="json") if state.hedge_book is not None else None
            ),
            "treasury": (
                state.treasury.model_dump(mode="json") if state.treasury is not None else None
            ),
            "eleventh_contract": (
                state.eleventh_contract.model_dump(mode="json")
                if state.eleventh_contract is not None
                else None
            ),
            "no_surprises": (
                state.no_surprises.model_dump(mode="json")
                if state.no_surprises is not None
                else None
            ),
            "diligence_room": (
                state.diligence_room.model_dump(mode="json")
                if state.diligence_room is not None
                else None
            ),
        }

    @staticmethod
    def _assert_protected_unchanged(state: GameState, protected: dict[str, object]) -> None:
        after = LearningEngine._protected_snapshot(state)
        if after != protected:
            raise RuntimeError("educational check changed protected narrative or financial state")
