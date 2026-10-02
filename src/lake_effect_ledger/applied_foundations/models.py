"""Authored content and isolated durable state for The Supply Gap."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lake_effect_ledger.accounting.models import Ledger
from lake_effect_ledger.commodity.models import FuturesPosition, MarginAccount
from lake_effect_ledger.learning.models import (
    CalculationDefinition,
    CareerTrajectory,
    CheckOption,
    KnowledgeCheckDefinition,
    KnowledgeCheckType,
    NumericRule,
    QuestionCategory,
    RetryPolicy,
    SeasonReviewState,
    TrajectoryTag,
)


class AppliedSeasonStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    LEGACY_SKIPPED = "legacy_skipped"


class LearningSeasonDefinition(BaseModel):
    id: Literal["applied_foundations"]
    title: str
    chapter_id: Literal["supply_gap"]
    chapter_title: str
    start_date: date
    end_date: date
    estimated_minutes: int = Field(ge=55, le=70)
    role: str
    purpose: str
    supplement_limit: str
    coverage_upgrades: list[str] = Field(min_length=7, max_length=7)
    supporting_objectives: list[str] = Field(min_length=1)


class ScenarioDefinition(BaseModel):
    id: str
    fictional: Literal[True]
    regional_hub: str
    contract_id: str
    contract_month: str
    physical_requirement_mmbtu: Decimal = Field(gt=0)
    initially_confirmed_mmbtu: Decimal = Field(gt=0)
    initially_provisional_mmbtu: Decimal = Field(gt=0)
    contract_size_mmbtu: Decimal = Field(gt=0)
    futures_side: Literal["long"]
    authorized_contracts: int = Field(gt=0)
    initial_henry_hub_price: Decimal = Field(gt=0)
    initial_chicago_basis: Decimal
    final_henry_hub_price: Decimal = Field(gt=0)
    final_chicago_basis: Decimal
    initial_margin_per_contract: Decimal = Field(gt=0)
    maintenance_margin_per_contract: Decimal = Field(gt=0)
    physical_purchase_completed: Literal[False]
    assumptions: list[str] = Field(min_length=5)

    @model_validator(mode="after")
    def validate_case(self) -> ScenarioDefinition:
        if self.initially_confirmed_mmbtu + self.initially_provisional_mmbtu != (
            self.physical_requirement_mmbtu
        ):
            raise ValueError("confirmed and provisional volume must equal the requirement")
        if self.maintenance_margin_per_contract >= self.initial_margin_per_contract:
            raise ValueError("maintenance margin must be below initial margin")
        return self


class OrderExampleDefinition(BaseModel):
    id: str
    order_type: Literal["market", "limit", "stop"]
    side: Literal["buy"]
    contracts: int = Field(gt=0)
    result: Literal["filled", "unfilled"]
    fill_price: Decimal | None = None
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    trigger_price: Decimal | None = None
    explanation: str


class ActualOrderDefinition(BaseModel):
    authorized_by: str
    transmitting_user: str
    prepared_by: str
    order_type: Literal["market"]
    side: Literal["buy"]
    contracts: int = Field(gt=0)
    fill_price: Decimal = Field(gt=0)


class OrderTapeDefinition(BaseModel):
    current_price: Decimal = Field(gt=0)
    subsequent_prices: list[Decimal] = Field(min_length=3, max_length=3)
    examples: list[OrderExampleDefinition] = Field(min_length=3, max_length=3)
    actual_order: ActualOrderDefinition

    @model_validator(mode="after")
    def validate_examples(self) -> OrderTapeDefinition:
        if {item.order_type for item in self.examples} != {"market", "limit", "stop"}:
            raise ValueError("order tape must contain market, limit, and stop examples")
        if self.actual_order.prepared_by != "player":
            raise ValueError("the player prepares but does not authorize the order")
        if self.actual_order.authorized_by != self.actual_order.transmitting_user:
            raise ValueError("the authored supervisor must authorize and transmit")
        return self


class RecordDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    owner: str
    status: str


class BoundaryDefinition(BaseModel):
    autosave: Literal[True]
    allow_return_to_menu: Literal[True]
    message: str | None = None
    retention_message: str | None = None


class AppliedDayDefinition(BaseModel):
    id: str
    day_number: int = Field(ge=1, le=3)
    date: date
    title: str
    lead_characters: list[str] = Field(min_length=2)
    teaching_points: list[str] = Field(min_length=3, max_length=3)
    decision_ids: list[str] = Field(min_length=3, max_length=3)
    check_ids: list[str] = Field(min_length=3, max_length=3)
    boundary: BoundaryDefinition


class AppliedChoiceDefinition(BaseModel):
    id: str
    text: str
    relationship_deltas: dict[str, int]
    tendency_tags: dict[TrajectoryTag, int]
    evidence_delta: int = Field(ge=0, le=2)
    documentation_delta: int = Field(ge=0, le=2)
    communication_delta: int = Field(ge=0, le=2)


class AppliedDecisionDefinition(BaseModel):
    id: str
    day: int = Field(ge=1, le=3)
    title: str
    prompt: str
    choices: list[AppliedChoiceDefinition] = Field(min_length=3, max_length=3)


class AppliedQuestionDefinition(BaseModel):
    id: str
    day: int | None = Field(default=None, ge=1, le=3)
    check_type: KnowledgeCheckType
    category: QuestionCategory
    remediation_category: str | None = None
    prompt: str
    objectives: list[str] = Field(min_length=1)
    source_id: str
    options: list[CheckOption] = Field(default_factory=list)
    correct_option_id: str | None = None
    calculation: CalculationDefinition | None = None
    expected_answer: Decimal | None = None
    answer_unit: str | None = None
    explanation: str | None = None

    @model_validator(mode="after")
    def validate_answer(self) -> AppliedQuestionDefinition:
        if self.check_type == KnowledgeCheckType.NUMERIC:
            if self.calculation is None or self.expected_answer is None or not self.answer_unit:
                raise ValueError(f"numeric Applied question {self.id} lacks calculation data")
            if self.options or self.correct_option_id is not None:
                raise ValueError(f"numeric Applied question {self.id} cannot contain choices")
        else:
            ids = [item.id for item in self.options]
            if not ids or self.correct_option_id not in ids or len(ids) != len(set(ids)):
                raise ValueError(f"Applied question {self.id} lacks a valid unique answer")
            if self.calculation is not None or self.expected_answer is not None:
                raise ValueError(f"choice Applied question {self.id} cannot be numeric")
        return self

    def as_knowledge_check(self) -> KnowledgeCheckDefinition:
        explanation = self.explanation or self._default_explanation()
        if self.check_type == KnowledgeCheckType.NUMERIC:
            return KnowledgeCheckDefinition(
                id=self.id,
                check_type=self.check_type,
                prompt=self.prompt,
                learning_objective_ids=self.objectives,
                source_id=self.source_id,
                calculation=self.calculation,
                numeric_rule=NumericRule(
                    rounding_quantum=(
                        Decimal("1") if self.answer_unit == "contracts" else Decimal("0.01")
                    ),
                    tolerance=Decimal("0"),
                    rounding="half_up",
                    answer_unit=self.answer_unit,
                ),
                explanation=explanation,
                numeric_wrong_answer_feedback=self._numeric_feedback(),
                hints=[self._numeric_hint()],
                worked_solution=self._numeric_solution(),
                retry_policy=RetryPolicy.UNTIL_CORRECT,
            )
        wrong_feedback = {
            item.id: (f"That choice does not preserve the tested distinction. {explanation}")
            for item in self.options
            if item.id != self.correct_option_id
        }
        return KnowledgeCheckDefinition(
            id=self.id,
            check_type=self.check_type,
            prompt=self.prompt,
            learning_objective_ids=self.objectives,
            source_id=self.source_id,
            options=self.options,
            correct_option_id=self.correct_option_id,
            explanation=explanation,
            wrong_answer_feedback=wrong_feedback,
            hints=[f"Focus on this distinction: {explanation}"],
            worked_solution=explanation,
            retry_policy=RetryPolicy.UNTIL_CORRECT,
        )

    def _default_explanation(self) -> str:
        if self.check_type == KnowledgeCheckType.NUMERIC:
            return (
                "The shared Decimal calculation produces "
                f"{self.expected_answer} {self.answer_unit}."
            )
        correct = next(item.text for item in self.options if item.id == self.correct_option_id)
        return f"The supported answer is: {correct}"

    def _numeric_feedback(self) -> str:
        return "Rebuild the result from the stated quantity, price, or margin inputs."

    def _numeric_hint(self) -> str:
        kind = self.calculation.kind.value
        return f"Identify the inputs for {kind}, keep the signs explicit, then calculate."

    def _numeric_solution(self) -> str:
        return (
            f"Using the authored inputs, the result is {self.expected_answer} {self.answer_unit}."
        )


class ReviewDefinition(BaseModel):
    style_defaults: dict[Literal["guided", "standard"], Literal["learning", "checkpoint"]]
    required_count: Literal[10]
    remediation_count: Literal[4]
    required: list[AppliedQuestionDefinition] = Field(min_length=10, max_length=10)
    remediation: list[AppliedQuestionDefinition] = Field(min_length=4, max_length=4)


class FormulaDefinition(BaseModel):
    id: str
    expression: str
    expected: Decimal


class AppliedFoundationsBlueprint(BaseModel):
    schema_version: Literal[1]
    season: LearningSeasonDefinition
    scenario: ScenarioDefinition
    order_tape: OrderTapeDefinition
    record_chain: list[RecordDefinition] = Field(min_length=8, max_length=8)
    days: list[AppliedDayDefinition] = Field(min_length=3, max_length=3)
    decisions: list[AppliedDecisionDefinition] = Field(min_length=9, max_length=9)
    checks: list[AppliedQuestionDefinition] = Field(min_length=9, max_length=9)
    review: ReviewDefinition
    formulas: list[FormulaDefinition] = Field(min_length=11, max_length=11)
    scripted_paths: dict[str, list[str]]

    @model_validator(mode="after")
    def validate_blueprint(self) -> AppliedFoundationsBlueprint:
        expected_upgrades = {
            "long_futures_hedge",
            "liquidity_not_profit",
            "order_types",
            "trade_lifecycle",
            "trade_reconciliation",
            "authorization_vs_outcome",
            "records_and_ethical_conduct",
        }
        if set(self.season.coverage_upgrades) != expected_upgrades:
            raise ValueError("Applied Foundations must upgrade exactly seven objectives")
        if [item.day_number for item in self.days] != [1, 2, 3]:
            raise ValueError("Applied days must be ordered 1, 2, 3")
        decision_ids = [item.id for item in self.decisions]
        check_ids = [item.id for item in self.checks]
        if set(decision_ids) != {item for day in self.days for item in day.decision_ids}:
            raise ValueError("every Applied decision must belong to exactly one day")
        if set(check_ids) != {item for day in self.days for item in day.check_ids}:
            raise ValueError("every Applied check must belong to exactly one day")
        for day in self.days:
            if any(self.decision(item).day != day.day_number for item in day.decision_ids):
                raise ValueError(f"Applied decision ownership disagrees for {day.id}")
            if any(self.question(item).day != day.day_number for item in day.check_ids):
                raise ValueError(f"Applied check ownership disagrees for {day.id}")
        question_ids = [item.id for item in self.all_questions]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Applied question IDs must be unique across the full bank")
        choice_ids = [choice.id for item in self.decisions for choice in item.choices]
        if set(self.scripted_paths) != {
            "evidence_first",
            "concise_operator",
            "escalation_first",
        }:
            raise ValueError("Applied scripted paths are incomplete")
        if len(choice_ids) != len(set(choice_ids)):
            raise ValueError("Applied choice IDs must be unique")
        selected_choices = [item for path in self.scripted_paths.values() for item in path]
        if len(selected_choices) != len(choice_ids) or set(selected_choices) != set(choice_ids):
            raise ValueError("scripted paths must cover every Applied choice")
        for path_name, path in self.scripted_paths.items():
            if len(path) != len(self.decisions) or len(path) != len(set(path)):
                raise ValueError(f"Applied path {path_name} must select nine unique choices")
            for decision, choice_id in zip(self.decisions, path, strict=True):
                if choice_id not in {item.id for item in decision.choices}:
                    raise ValueError(f"Applied path {path_name} does not follow decision order")
        record_ids = [item.id for item in self.record_chain]
        if record_ids != [
            "physical_support",
            "analyst_recommendation",
            "hedge_authorization",
            "order_transmission",
            "execution",
            "original_confirmation",
            "reconciliation",
            "control_review",
        ]:
            raise ValueError("Applied record chain is not the authored fixed sequence")
        required_categories = {item.remediation_category for item in self.review.required}
        remediation_categories = {item.remediation_category for item in self.review.remediation}
        if None in required_categories or required_categories != remediation_categories:
            raise ValueError("Applied remediation categories must cover the required bank")
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


class AuthoredOrderResult(BaseModel):
    order_id: str
    order_type: str
    filled: bool
    triggered: bool = False
    fill_price: Decimal | None = None


class AppliedFinancialState(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    initialized: bool = False
    settled: bool = False
    opening_operating_cash: Decimal = Field(default=Decimal("0"), ge=0)
    operating_cash: Decimal = Field(default=Decimal("0"), ge=0)
    operating_cash_movement: Decimal = Decimal("0")
    ledger: Ledger = Field(default_factory=Ledger)
    margin: MarginAccount | None = None
    position: FuturesPosition | None = None
    physical_memorandum: dict[str, Decimal] = Field(default_factory=dict)
    calculations: dict[str, Decimal] = Field(default_factory=dict)
    order_results: list[AuthoredOrderResult] = Field(default_factory=list)


class AppliedFoundationsState(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    status: AppliedSeasonStatus = AppliedSeasonStatus.NOT_STARTED
    current_day_index: int = Field(default=0, ge=0, le=3)
    current_decision_index: int = Field(default=0, ge=0)
    current_check_index: int = Field(default=0, ge=0)
    decisions: list[str] = Field(default_factory=list)
    relationships: dict[str, int] = Field(default_factory=dict)
    trajectory: CareerTrajectory = Field(default_factory=CareerTrajectory)
    evidence_score: int = Field(default=0, ge=0)
    documentation_score: int = Field(default=0, ge=0)
    communication_score: int = Field(default=0, ge=0)
    confirmed_volume: bool = False
    record_chain: list[str] = Field(default_factory=list)
    record_statuses: dict[str, str] = Field(default_factory=dict)
    financial: AppliedFinancialState = Field(default_factory=AppliedFinancialState)
    review: SeasonReviewState = Field(default_factory=SeasonReviewState)
    debrief_completed: bool = False
    snapshot_finalized: bool = False
    legacy_skip_reason: str | None = None

    @model_validator(mode="after")
    def validate_skip(self) -> AppliedFoundationsState:
        if self.status == AppliedSeasonStatus.LEGACY_SKIPPED and not self.legacy_skip_reason:
            raise ValueError("legacy-skipped Applied state requires a reason")
        return self


def choice_effect_payload(choice: AppliedChoiceDefinition) -> dict[str, Any]:
    return {
        "relationships": dict(choice.relationship_deltas),
        "tendencies": {tag.value: amount for tag, amount in choice.tendency_tags.items()},
        "evidence": choice.evidence_delta,
        "documentation": choice.documentation_delta,
        "communication": choice.communication_delta,
    }
