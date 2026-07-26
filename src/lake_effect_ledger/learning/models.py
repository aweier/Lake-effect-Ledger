"""Content schemas and saved state for Guided Career learning."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lake_effect_ledger.commodity.models import PositionSide


class GameMode(StrEnum):
    GUIDED = "guided"
    STANDARD = "standard"


class ShowMathMode(StrEnum):
    ALWAYS = "always"
    ON_REQUEST = "on_request"
    OFF = "off"


class LearningStatus(StrEnum):
    UNSEEN = "unseen"
    INTRODUCED = "introduced"
    PRACTICED_WITH_HELP = "practiced_with_help"
    DEMONSTRATED = "demonstrated"
    REVIEW_RECOMMENDED = "review_recommended"


class TrajectoryTag(StrEnum):
    PRINCIPLED = "principled"
    COMPANY_LOYAL = "company_loyal"
    AMBITIOUS = "ambitious"
    SELF_PROTECTIVE = "self_protective"
    CONFLICTED = "conflicted"
    COOPERATIVE = "cooperative"
    DETAIL_ORIENTED = "detail_oriented"
    RISK_SEEKING = "risk_seeking"


TRAJECTORY_LABELS = {
    TrajectoryTag.PRINCIPLED: "Principled professional",
    TrajectoryTag.COMPANY_LOYAL: "Company loyalist",
    TrajectoryTag.AMBITIOUS: "Ambitious operator",
    TrajectoryTag.SELF_PROTECTIVE: "Self-protective survivor",
    TrajectoryTag.CONFLICTED: "Conflicted insider",
    TrajectoryTag.COOPERATIVE: "Future cooperator or whistleblower",
    TrajectoryTag.DETAIL_ORIENTED: "Detail-oriented control specialist",
    TrajectoryTag.RISK_SEEKING: "Risk-seeking market operator",
}


class ObjectiveProgress(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    status: LearningStatus = LearningStatus.UNSEEN
    attempts: int = Field(default=0, ge=0)
    correct_applications: int = Field(default=0, ge=0)
    help_uses: int = Field(default=0, ge=0)
    last_check_id: str | None = None


class KnowledgeCheckProgress(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    check_id: str
    attempts: int = Field(default=0, ge=0)
    incorrect_attempts: int = Field(default=0, ge=0)
    hints_used: int = Field(default=0, ge=0)
    walkthrough_used: bool = False
    completed: bool = False
    independently_demonstrated: bool = False
    last_answer: str | None = None


class LearningNotebookState(BaseModel):
    unlocked_glossary_ids: list[str] = Field(default_factory=list)
    worked_example_ids: list[str] = Field(default_factory=list)
    review_check_ids: list[str] = Field(default_factory=list)


class LearningProfile(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    objectives: dict[str, ObjectiveProgress] = Field(default_factory=dict)
    checks: dict[str, KnowledgeCheckProgress] = Field(default_factory=dict)
    notebook: LearningNotebookState = Field(default_factory=LearningNotebookState)
    completed_day_ids: list[str] = Field(default_factory=list)


class CareerTrajectory(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    tag_weights: dict[TrajectoryTag, int] = Field(default_factory=dict)
    decision_tags: dict[str, dict[TrajectoryTag, int]] = Field(default_factory=dict)

    def record(self, decision_id: str, tag: TrajectoryTag, amount: int) -> None:
        if decision_id in self.decision_tags and tag in self.decision_tags[decision_id]:
            raise ValueError(f"trajectory tag already recorded for decision {decision_id}")
        tagged = dict(self.decision_tags.get(decision_id, {}))
        tagged[tag] = amount
        self.decision_tags[decision_id] = tagged
        self.tag_weights[tag] = self.tag_weights.get(tag, 0) + amount

    @property
    def tendencies(self) -> list[str]:
        ranked = sorted(
            ((weight, tag) for tag, weight in self.tag_weights.items() if weight >= 3),
            key=lambda item: (-item[0], item[1].value),
        )
        return [TRAJECTORY_LABELS[tag] for _, tag in ranked] or ["Still forming"]


class PrologueState(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    started: bool = False
    completed: bool = False
    skipped: bool = False
    transitioned_to_episode_1: bool = False
    current_day_index: int = Field(default=0, ge=0, le=3)
    current_check_index: int = Field(default=0, ge=0)
    story_choice_id: str | None = None


class GameModeDefinition(BaseModel):
    id: GameMode
    label: str = Field(min_length=1)
    recommended: bool = False
    description: str = Field(min_length=1)
    default_show_math: ShowMathMode
    starts_with_prologue: bool


class GameModeFile(BaseModel):
    schema_version: Literal[1]
    modes: list[GameModeDefinition] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_modes(self) -> GameModeFile:
        ids = [item.id for item in self.modes]
        if set(ids) != set(GameMode):
            raise ValueError("game modes must define guided and standard")
        if sum(item.recommended for item in self.modes) != 1:
            raise ValueError("exactly one game mode must be recommended")
        guided = next(item for item in self.modes if item.id == GameMode.GUIDED)
        standard = next(item for item in self.modes if item.id == GameMode.STANDARD)
        if not guided.starts_with_prologue or standard.starts_with_prologue:
            raise ValueError("only Guided Career may start with the prologue")
        return self


class SourceReference(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    organization: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(pattern=r"^https://")
    note: str = Field(min_length=1)


class SourceReferenceFile(BaseModel):
    schema_version: Literal[1]
    sources: list[SourceReference] = Field(min_length=1)


class GlossaryTerm(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    term: str = Field(min_length=1)
    definition: str = Field(min_length=1, max_length=320)
    learning_objective_ids: list[str] = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)
    series_3_topics: list[str] = Field(min_length=1)


class GlossaryFile(BaseModel):
    schema_version: Literal[1]
    terms: list[GlossaryTerm] = Field(min_length=17)


class KnowledgeCheckType(StrEnum):
    MULTIPLE_CHOICE = "multiple_choice"
    NUMERIC = "numeric"
    POSITION_DIRECTION = "position_direction"
    INTERPRETATION = "interpretation"
    PREDICTION = "prediction"


class RetryPolicy(StrEnum):
    UNTIL_CORRECT = "until_correct"


class CalculationKind(StrEnum):
    FUTURES_PNL = "futures_pnl"
    TICK_VALUE = "tick_value"
    REGIONAL_PRICE = "regional_price"
    HEDGE_RATIO = "hedge_ratio"
    MARGIN_CALL = "margin_call"


class CheckOption(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    text: str = Field(min_length=1)


class NumericRule(BaseModel):
    rounding_quantum: Decimal = Field(gt=0)
    tolerance: Decimal = Field(ge=0)
    rounding: Literal["half_up"]


class CalculationDefinition(BaseModel):
    kind: CalculationKind
    contract_id: str | None = None
    side: PositionSide | None = None
    previous_price: Decimal | None = None
    current_price: Decimal | None = None
    contracts: int | None = Field(default=None, ge=0)
    henry_hub_price: Decimal | None = None
    regional_basis: Decimal | None = None
    physical_quantity_mmbtu: Decimal | None = None
    initial_requirement: Decimal | None = None
    maintenance_requirement: Decimal | None = None
    margin_balance: Decimal | None = None

    @model_validator(mode="after")
    def validate_inputs(self) -> CalculationDefinition:
        required_by_kind = {
            CalculationKind.FUTURES_PNL: (
                "contract_id",
                "side",
                "previous_price",
                "current_price",
                "contracts",
            ),
            CalculationKind.TICK_VALUE: ("contract_id",),
            CalculationKind.REGIONAL_PRICE: ("henry_hub_price", "regional_basis"),
            CalculationKind.HEDGE_RATIO: (
                "contract_id",
                "contracts",
                "physical_quantity_mmbtu",
            ),
            CalculationKind.MARGIN_CALL: (
                "initial_requirement",
                "maintenance_requirement",
                "margin_balance",
            ),
        }
        missing = [name for name in required_by_kind[self.kind] if getattr(self, name) is None]
        if missing:
            raise ValueError(f"{self.kind.value} calculation is missing: {', '.join(missing)}")
        return self


class KnowledgeCheckDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    check_type: KnowledgeCheckType
    prompt: str = Field(min_length=1)
    learning_objective_ids: list[str] = Field(min_length=1)
    source_id: str = Field(pattern=r"^[a-z0-9_]+$")
    options: list[CheckOption] = Field(default_factory=list)
    correct_option_id: str | None = None
    calculation: CalculationDefinition | None = None
    numeric_rule: NumericRule | None = None
    explanation: str = Field(min_length=1)
    hints: list[str] = Field(min_length=1)
    worked_solution: str = Field(min_length=1)
    retry_policy: RetryPolicy
    unsure_text: str = "I'm not sure—walk me through it."

    @model_validator(mode="after")
    def validate_answer(self) -> KnowledgeCheckDefinition:
        option_ids = [item.id for item in self.options]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError(f"knowledge check {self.id} contains duplicate options")
        if self.check_type == KnowledgeCheckType.NUMERIC:
            if self.calculation is None:
                raise ValueError(f"numeric check {self.id} requires a calculation")
            if self.numeric_rule is None:
                raise ValueError(f"numeric check {self.id} requires rounding and tolerance")
            if self.correct_option_id is not None:
                raise ValueError(f"numeric check {self.id} cannot use a choice answer")
        else:
            if not self.options or self.correct_option_id not in option_ids:
                raise ValueError(f"knowledge check {self.id} lacks a valid correct answer")
            if self.calculation is not None or self.numeric_rule is not None:
                raise ValueError(f"choice check {self.id} cannot use numeric calculation rules")
        return self


class ConceptPanelDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    title: str = Field(min_length=1)
    speaker: str = Field(min_length=1)
    text: str = Field(min_length=1)
    learning_objective_ids: list[str] = Field(min_length=1)
    glossary_ids: list[str] = Field(min_length=1)


class TutorialDayDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    day_number: int = Field(ge=1, le=3)
    title: str = Field(min_length=1)
    subtitle: str = Field(min_length=1)
    concept_panels: list[ConceptPanelDefinition] = Field(min_length=2)
    check_ids: list[str] = Field(min_length=1)
    story_scene_id: str | None = None
    end_note: str = Field(min_length=1)


class PrologueDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    title: str = Field(min_length=1)
    role_title: str = Field(min_length=1)
    start_date: date
    estimated_minutes: int = Field(ge=20, le=30)
    days: list[TutorialDayDefinition] = Field(min_length=3, max_length=3)
    episode_1_transition_scene_id: str = Field(pattern=r"^[a-z0-9_]+$")
    transition_text: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_days(self) -> PrologueDefinition:
        if [item.day_number for item in self.days] != [1, 2, 3]:
            raise ValueError("prologue days must be ordered 1, 2, 3")
        if len({item.id for item in self.days}) != 3:
            raise ValueError("prologue contains duplicate day IDs")
        return self


class PrologueFile(BaseModel):
    schema_version: Literal[1]
    prologue: PrologueDefinition
    checks: list[KnowledgeCheckDefinition] = Field(min_length=15)

    @model_validator(mode="after")
    def validate_check_coverage(self) -> PrologueFile:
        present = {item.check_type for item in self.checks}
        missing = set(KnowledgeCheckType) - present
        if missing:
            raise ValueError(f"prologue is missing knowledge-check types: {missing}")
        return self
