"""Authored content and isolated durable state for The Notice Window."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lake_effect_ledger.applied_foundations.models import (
    AppliedDayDefinition,
    AppliedDecisionDefinition,
    AppliedQuestionDefinition,
    FormulaDefinition,
    RecordDefinition,
    ReviewDefinition,
)
from lake_effect_ledger.learning.models import CareerTrajectory, SeasonReviewState


class NoticeWindowStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    LEGACY_SKIPPED = "legacy_skipped"


class NoticeSeasonDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Literal["notice_window"]
    title: str
    chapter_id: Literal["notice_window"]
    chapter_title: str
    start_date: date
    end_date: date
    estimated_minutes: int = Field(ge=65, le=85)
    role: str
    purpose: str
    supplement_limit: str
    coverage_additions: list[str] = Field(min_length=7, max_length=7)
    supporting_objectives: list[str] = Field(min_length=1)


class CurveSnapshotDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    nearby_price: Decimal = Field(gt=0)
    deferred_price: Decimal = Field(gt=0)
    classification: Literal["normal", "inverted"]
    explanation: str

    @property
    def spread(self) -> Decimal:
        return self.deferred_price - self.nearby_price


class LimitStateDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fictional: Literal[True]
    state: Literal["locked_limit_up"]
    resting_orders_guaranteed_fills: Literal[False]
    margin_effect_possible: Literal[True]
    disclaimer: str


class NoticeScenarioDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    fictional: Literal[True]
    contract_id: str
    nearby_contract_month: str
    deferred_contract_month: str
    open_side: Literal["long"]
    open_contracts: int = Field(gt=0)
    contract_size_mmbtu: Decimal = Field(gt=0)
    delivery_month_start: date
    exchange_last_trading_day: date
    exchange_notice_day: date
    delivery_month_end: date
    northstar_internal_action_deadline: date
    normal_curve: CurveSnapshotDefinition
    inverted_curve: CurveSnapshotDefinition
    authored_carry_estimate: Decimal = Field(ge=0)
    planned_resolution: Literal["offset_before_internal_deadline"]
    offset_contracts: int = Field(gt=0)
    final_open_contracts: Literal[0]
    delivery_intended: Literal[False]
    limit_state: LimitStateDefinition
    assumptions: list[str] = Field(min_length=6)

    @model_validator(mode="after")
    def validate_case(self) -> NoticeScenarioDefinition:
        if self.open_contracts != self.offset_contracts:
            raise ValueError("the authored offset must close the complete local position")
        if not (
            self.northstar_internal_action_deadline
            < self.exchange_last_trading_day
            < self.exchange_notice_day
            < self.delivery_month_start
            <= self.delivery_month_end
        ):
            raise ValueError("the Notice Window calendar is not chronologically valid")
        if self.normal_curve.spread <= 0 or self.normal_curve.classification != "normal":
            raise ValueError("the normal curve must have a positive deferred-minus-nearby spread")
        if self.inverted_curve.spread >= 0 or self.inverted_curve.classification != "inverted":
            raise ValueError("the inverted curve must have a negative spread")
        return self


class NoticeWindowBlueprint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    season: NoticeSeasonDefinition
    scenario: NoticeScenarioDefinition
    record_chain: list[RecordDefinition] = Field(min_length=11, max_length=11)
    days: list[AppliedDayDefinition] = Field(min_length=3, max_length=3)
    decisions: list[AppliedDecisionDefinition] = Field(min_length=9, max_length=9)
    checks: list[AppliedQuestionDefinition] = Field(min_length=9, max_length=9)
    review: ReviewDefinition
    formulas: list[FormulaDefinition] = Field(min_length=6, max_length=6)
    scripted_paths: dict[str, list[str]]

    @model_validator(mode="after")
    def validate_blueprint(self) -> NoticeWindowBlueprint:
        expected_additions = {
            "clearinghouse_mechanics",
            "delivery",
            "first_notice_day",
            "spot_month",
            "price_and_lock_limits",
            "normal_inverted_markets",
            "carrying_charges",
        }
        if set(self.season.coverage_additions) != expected_additions:
            raise ValueError("The Notice Window must add exactly seven objective groups")
        if [item.day_number for item in self.days] != [1, 2, 3]:
            raise ValueError("Notice Window days must be ordered 1, 2, 3")
        decision_ids = [item.id for item in self.decisions]
        check_ids = [item.id for item in self.checks]
        if set(decision_ids) != {item for day in self.days for item in day.decision_ids}:
            raise ValueError("every Notice Window decision must belong to exactly one day")
        if set(check_ids) != {item for day in self.days for item in day.check_ids}:
            raise ValueError("every Notice Window check must belong to exactly one day")
        for day in self.days:
            if any(self.decision(item).day != day.day_number for item in day.decision_ids):
                raise ValueError(f"Notice Window decision ownership disagrees for {day.id}")
            if any(self.question(item).day != day.day_number for item in day.check_ids):
                raise ValueError(f"Notice Window check ownership disagrees for {day.id}")
        question_ids = [item.id for item in self.all_questions]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Notice Window question IDs must be unique")
        choice_ids = [choice.id for decision in self.decisions for choice in decision.choices]
        if len(choice_ids) != len(set(choice_ids)):
            raise ValueError("Notice Window choice IDs must be unique")
        if set(self.scripted_paths) != {
            "evidence_first",
            "concise_operator",
            "escalation_first",
        }:
            raise ValueError("Notice Window scripted paths are incomplete")
        selected = [choice for path in self.scripted_paths.values() for choice in path]
        if len(selected) != len(choice_ids) or set(selected) != set(choice_ids):
            raise ValueError("Notice Window paths must cover every choice exactly once")
        for path_name, path in self.scripted_paths.items():
            if len(path) != len(self.decisions) or len(path) != len(set(path)):
                raise ValueError(f"Notice Window path {path_name} must select nine choices")
            for decision, choice_id in zip(self.decisions, path, strict=True):
                if choice_id not in {item.id for item in decision.choices}:
                    raise ValueError(f"Notice Window path {path_name} breaks decision order")
        record_ids = [item.id for item in self.record_chain]
        if record_ids != [
            "fcm_expiration_report",
            "contract_rule_source",
            "calendar_verification",
            "delivery_capacity_memo",
            "expiry_recommendation",
            "offset_authorization",
            "supervised_transmission",
            "offset_execution",
            "original_confirmation",
            "reconciliation",
            "control_review",
        ]:
            raise ValueError("Notice Window record chain is not the authored fixed sequence")
        required_categories = {item.remediation_category for item in self.review.required}
        remediation_categories = {item.remediation_category for item in self.review.remediation}
        if None in required_categories or required_categories != remediation_categories:
            raise ValueError("Notice remediation categories must cover the required bank")
        return self

    @property
    def all_questions(self) -> list[AppliedQuestionDefinition]:
        return [*self.checks, *self.review.required, *self.review.remediation]

    def day(self, day_number: int) -> AppliedDayDefinition:
        return self.days[day_number - 1]

    def decision(self, decision_id: str) -> AppliedDecisionDefinition:
        return next(item for item in self.decisions if item.id == decision_id)

    def question(self, question_id: str) -> AppliedQuestionDefinition:
        return next(item for item in self.all_questions if item.id == question_id)


class NoticeWindowState(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    status: NoticeWindowStatus = NoticeWindowStatus.NOT_STARTED
    current_day_index: int = Field(default=0, ge=0, le=3)
    current_decision_index: int = Field(default=0, ge=0)
    current_check_index: int = Field(default=0, ge=0)
    decisions: list[str] = Field(default_factory=list)
    relationships: dict[str, int] = Field(default_factory=dict)
    trajectory: CareerTrajectory = Field(default_factory=CareerTrajectory)
    evidence_score: int = Field(default=0, ge=0)
    documentation_score: int = Field(default=0, ge=0)
    communication_score: int = Field(default=0, ge=0)
    record_chain: list[str] = Field(default_factory=list)
    record_statuses: dict[str, str] = Field(default_factory=dict)
    curve_calculations: dict[str, Decimal] = Field(default_factory=dict)
    offset_completed: bool = False
    remaining_contracts: int = Field(default=2, ge=0)
    review: SeasonReviewState = Field(default_factory=SeasonReviewState)
    debrief_completed: bool = False
    snapshot_finalized: bool = False
    legacy_skip_reason: str | None = None

    @model_validator(mode="after")
    def validate_skip(self) -> NoticeWindowState:
        if self.status == NoticeWindowStatus.LEGACY_SKIPPED and not self.legacy_skip_reason:
            raise ValueError("legacy-skipped Notice Window state requires a reason")
        return self
