"""Deterministic season-local orchestration for The Notice Window."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lake_effect_ledger.commodity.engine import (
    contract_month_spread,
    delivery_contract_value,
)
from lake_effect_ledger.learning.engine import LearningEngine
from lake_effect_ledger.learning.models import CampaignTrack
from lake_effect_ledger.notice_window.models import (
    NoticeWindowState,
    NoticeWindowStatus,
)

if TYPE_CHECKING:
    from lake_effect_ledger.applied_foundations.models import AppliedChoiceDefinition
    from lake_effect_ledger.narrative.models import ContentBundle
    from lake_effect_ledger.state import GameState


class NoticeWindowEngine:
    """Run the expiry story without mutating the established business-story inputs."""

    def __init__(self, content: ContentBundle) -> None:
        self.content = content
        self.blueprint = content.notice_window
        self.learning = LearningEngine(content)

    def start(self, state: GameState) -> NoticeWindowState:
        chapter = state.notice_window
        if chapter.status == NoticeWindowStatus.LEGACY_SKIPPED:
            raise ValueError("this legacy save cannot move backward into The Notice Window")
        if state.applied_foundations.status.value != "completed":
            raise ValueError("complete The Supply Gap before starting The Notice Window")
        if state.diligence_room is not None:
            raise ValueError("The Notice Window cannot begin after diligence has started")
        if state.campaign_track == CampaignTrack.EXTENDED_STORY:
            if state.no_surprises is None or not state.no_surprises.completed:
                raise ValueError(
                    "complete No Surprises before the dated Extended Story Notice Window"
                )
        elif state.no_surprises is not None:
            raise ValueError("the Applied track cannot enter The Notice Window after audit")
        if chapter.status == NoticeWindowStatus.NOT_STARTED:
            chapter.status = NoticeWindowStatus.IN_PROGRESS
            chapter.record_chain = [item.id for item in self.blueprint.record_chain]
            chapter.record_statuses = {
                item.id: ("received" if item.id == "fcm_expiration_report" else "pending")
                for item in self.blueprint.record_chain
            }
            scenario = self.blueprint.scenario
            normal_spread = contract_month_spread(
                nearby_price=scenario.normal_curve.nearby_price,
                deferred_price=scenario.normal_curve.deferred_price,
            )
            inverted_spread = contract_month_spread(
                nearby_price=scenario.inverted_curve.nearby_price,
                deferred_price=scenario.inverted_curve.deferred_price,
            )
            chapter.curve_calculations = {
                "normal_spread": normal_spread,
                "inverted_spread": inverted_spread,
                "normal_residual_after_carry": (normal_spread - scenario.authored_carry_estimate),
                "two_contract_delivery_value_at_normal_nearby": delivery_contract_value(
                    settlement_price=scenario.normal_curve.nearby_price,
                    contract_size_mmbtu=scenario.contract_size_mmbtu,
                    contracts=scenario.open_contracts,
                ),
            }
        if chapter.current_day_index < 3:
            self.begin_day(state, chapter.current_day_index + 1)
        return chapter

    def begin_day(self, state: GameState, day_number: int) -> None:
        chapter = self._active(state)
        if day_number != chapter.current_day_index + 1:
            raise ValueError("Notice Window days must be completed in order")
        day = self.blueprint.day(day_number)
        state.current_date = day.date
        objective_ids = sorted(
            {
                objective
                for check_id in day.check_ids
                for objective in self.blueprint.question(check_id).objectives
            }
        )
        self.learning.introduce_objectives(state, objective_ids, chapter_id="notice_window")

    def current_decision(self, state: GameState):
        chapter = self._active(state)
        day = self.blueprint.day(chapter.current_day_index + 1)
        if chapter.current_decision_index >= len(day.decision_ids):
            return None
        return self.blueprint.decision(day.decision_ids[chapter.current_decision_index])

    def record_decision(
        self,
        state: GameState,
        decision_id: str,
        choice_id: str,
    ) -> AppliedChoiceDefinition:
        chapter = self._active(state)
        decision = self.current_decision(state)
        if decision is None or decision.id != decision_id:
            raise ValueError(f"decision {decision_id} is not the current Notice Window decision")
        if choice_id in chapter.decisions:
            raise ValueError(f"Notice Window choice already recorded: {choice_id}")
        try:
            choice = next(item for item in decision.choices if item.id == choice_id)
        except StopIteration as error:
            raise ValueError(f"choice {choice_id} does not belong to {decision_id}") from error
        for person_id, amount in choice.relationship_deltas.items():
            chapter.relationships[person_id] = chapter.relationships.get(person_id, 0) + amount
        for tag, amount in choice.tendency_tags.items():
            chapter.trajectory.record(choice.id, tag, amount)
        chapter.evidence_score += choice.evidence_delta
        chapter.documentation_score += choice.documentation_delta
        chapter.communication_score += choice.communication_delta
        chapter.decisions.append(choice.id)
        chapter.current_decision_index += 1
        self._advance_records(chapter, decision.id)
        return choice

    def complete_day(self, state: GameState, *, require_checks: bool) -> None:
        chapter = self._active(state)
        day = self.blueprint.day(chapter.current_day_index + 1)
        if chapter.current_decision_index != len(day.decision_ids):
            raise ValueError(f"cannot complete {day.id}; story decisions remain")
        incomplete = [
            check_id
            for check_id in day.check_ids
            if not state.learning.checks.get(check_id)
            or not state.learning.checks[check_id].completed
        ]
        if require_checks and incomplete:
            raise ValueError(f"cannot complete {day.id}; incomplete checks: {incomplete}")
        if day.day_number == 3:
            if not chapter.offset_completed or chapter.remaining_contracts != 0:
                raise ValueError("the authored offset must close the local position")
            expected = {item.id: item.status for item in self.blueprint.record_chain}
            if chapter.record_statuses != expected:
                raise ValueError("the Notice Window record chain is incomplete")
        chapter.current_day_index += 1
        chapter.current_decision_index = 0
        chapter.current_check_index = 0

    def complete_chapter(self, state: GameState) -> None:
        chapter = self._active(state)
        if chapter.current_day_index != 3 or chapter.remaining_contracts != 0:
            raise ValueError("complete all three Notice Window days before its review")

    def mark_completed(self, state: GameState) -> None:
        chapter = self._active(state)
        if not chapter.review.completed or not chapter.snapshot_finalized:
            raise ValueError("complete the Notice Window review and snapshot before the debrief")
        chapter.debrief_completed = True
        chapter.status = NoticeWindowStatus.COMPLETED

    def scripted_choice(self, state: GameState, path_name: str) -> str:
        if path_name not in self.blueprint.scripted_paths:
            valid = ", ".join(sorted(self.blueprint.scripted_paths))
            raise ValueError(f"Notice Window path must be one of: {valid}")
        completed = len(self._active(state).decisions)
        return self.blueprint.scripted_paths[path_name][completed]

    @staticmethod
    def _advance_records(chapter: NoticeWindowState, decision_id: str) -> None:
        if decision_id == "nw_contract_classification":
            chapter.record_statuses["contract_rule_source"] = "linked"
        elif decision_id == "nw_calendar_source":
            chapter.record_statuses["calendar_verification"] = "verified"
        elif decision_id == "nw_delivery_intent":
            chapter.record_statuses.update(
                {
                    "delivery_capacity_memo": "no_delivery_intent",
                    "expiry_recommendation": "prepared",
                }
            )
        elif decision_id == "nw_resolution_route":
            chapter.record_statuses.update(
                {
                    "offset_authorization": "authorized",
                    "supervised_transmission": "transmitted_under_supervision",
                    "offset_execution": "filled",
                }
            )
            chapter.offset_completed = True
            chapter.remaining_contracts = 0
        elif decision_id == "nw_final_packet":
            chapter.record_statuses.update(
                {
                    "original_confirmation": "preserved",
                    "reconciliation": "reconciled",
                    "control_review": "reviewed",
                }
            )

    @staticmethod
    def _active(state: GameState) -> NoticeWindowState:
        chapter = state.notice_window
        if chapter.status not in {
            NoticeWindowStatus.IN_PROGRESS,
            NoticeWindowStatus.NOT_STARTED,
        }:
            raise ValueError(f"The Notice Window is {chapter.status.value}")
        return chapter
