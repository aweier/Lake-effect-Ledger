"""Typed records for the transaction-scoped Diligence Room chapter."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import core_schema

from lake_effect_ledger.learning.models import KnowledgeCheckDefinition, TrajectoryTag


class DiligenceStage(StrEnum):
    REQUEST_LIST = "request_list"
    INITIAL_PACKAGE = "initial_package"
    RISK_SCHEDULE = "risk_schedule"
    Q_AND_A = "q_and_a"
    SUPPLEMENTAL = "supplemental"
    BEFORE_COMMITTEE = "before_committee"
    COMPLETE = "complete"


class FrozenFactMap(dict[str, str]):
    """JSON-compatible mapping that cannot mutate after package publication."""

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return core_schema.no_info_after_validator_function(
            cls,
            handler.generate_schema(dict[str, str]),
        )

    @staticmethod
    def _blocked(*args, **kwargs):
        raise TypeError("published package facts are immutable")

    __setitem__ = _blocked
    __delitem__ = _blocked
    clear = _blocked
    pop = _blocked
    popitem = _blocked
    setdefault = _blocked
    update = _blocked
    __ior__ = _blocked


class StakeholderKind(StrEnum):
    BUYER = "buyer"
    BOARD = "board"
    LENDER = "lender"
    MANAGEMENT = "management"
    INTERNAL_AUDIT = "internal_audit"


class DisclosureStatus(StrEnum):
    REQUESTED = "requested"
    AVAILABLE = "available"
    PENDING_REVIEW = "pending_review"
    INCLUDED = "included"
    OMITTED = "omitted"
    NOT_APPLICABLE = "not_applicable"
    SUPPLEMENTED = "supplemented"
    CORRECTED = "corrected"
    DISPUTED = "disputed"
    UNABLE_TO_SUBSTANTIATE = "unable_to_substantiate"


class RemediationStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    TESTED = "tested"
    CLOSED = "closed"
    RISK_ACCEPTED = "risk_accepted"
    OVERDUE = "overdue"


class TransactionStatus(StrEnum):
    DILIGENCE_CONTINUES = "diligence_continues"
    TOUGHER_TERMS = "tougher_terms"
    ADDITIONAL_TESTING = "additional_testing"
    CONDITIONAL_CLOSE = "conditional_close"
    STALLED = "stalled"
    BUYER_WITHDREW = "buyer_withdrew"


class DiligenceOutcome(StrEnum):
    CLEAN_ROOM = "clean_room"
    PRICE_OF_CANDOR = "price_of_candor"
    THREE_VERSIONS_OF_MONDAY = "three_versions_of_monday"
    REMEDIATION_ON_PAPER = "remediation_on_paper"
    COVENANT_CONVERSATION = "covenant_conversation"
    BELLANDI_CONFIDENCE = "bellandi_confidence"
    BUYER_WALKS = "buyer_walks"
    CONDITIONAL_CLOSE = "conditional_close"


class DisclosureScope(StrEnum):
    COMPLETE = "complete"
    SUMMARY_LINKED = "management_summary_linked"
    LIMITED = "limited"
    ESCALATED_REVIEW = "escalated_review"


class ExceptionDescription(StrEnum):
    EXCEPTION_SCHEDULE = "exception_schedule"
    CORRECTED_ERROR = "corrected_trading_error"
    AUTHORIZED_ELEVEN = "authorized_eleven"


class ReviewerChoice(StrEnum):
    EVELYN_AND_NOAH = "evelyn_and_noah"
    MARISOL = "marisol"
    CAL = "cal"
    SELF = "self"


class NumbersPosture(StrEnum):
    RECONCILE_SOURCES = "reconcile_sources"
    LATER_SUPPORT_AS_TRADE_DATE = "later_support_as_trade_date"
    OMIT_MARGIN_CALL = "omit_margin_call"


class ScenarioPosture(StrEnum):
    FULL = "full"
    SUMMARY = "summary"
    ESCALATE = "escalate"


class RemediationPosture(StrEnum):
    ACTUAL_STATUS = "actual_status"
    IMPLEMENTED_CLAIM = "implemented_claim"
    PLANNED_LABEL = "planned_label"


class AnswerPosture(StrEnum):
    COMPLETE = "complete"
    NARROW = "narrow"
    ACKNOWLEDGE_UNCERTAINTY = "acknowledge_uncertainty"
    REFER_TO_OWNER = "refer_to_owner"


class RepresentationPosture(StrEnum):
    CORRECT = "correct"
    PREFERRED_INCOMPLETE = "preferred_incomplete"
    ESCALATE = "escalate"


class InconsistencyAction(StrEnum):
    CORRECT = "correct"
    SUPPLEMENT = "supplement"
    LEAVE = "leave"


class CommitteePosture(StrEnum):
    SUPPORT_CHRONOLOGY = "support_chronology"
    PROTECT_CAL = "protect_cal"
    ACKNOWLEDGE_INCOMPLETE = "acknowledge_incomplete"


class FinalAction(StrEnum):
    CORRECT_DISCLOSURE = "correct_disclosure"
    ESCALATE_REPRESENTATION = "escalate_representation"
    STAY_SILENT = "stay_silent"


class Stakeholder(BaseModel):
    stakeholder_id: str
    name: str
    role: str
    kind: StakeholderKind
    concerns: list[str] = Field(min_length=1)


class DiligenceEngagement(BaseModel):
    engagement_id: str
    title: str
    purpose: str
    transaction_structure: str
    buyer_name: str
    opened_at: datetime
    target_committee_date: date
    stakeholder_ids: list[str] = Field(min_length=3)


class SourceRecordReference(BaseModel):
    reference_id: str
    record_id: str
    record_type: str
    fact_key: str
    as_of: datetime | date | None = None
    value_text: str
    calculation: str | None = None


class RequestedDisclosureItem(BaseModel):
    item_id: str
    label: str
    source_record_ids: list[str] = Field(default_factory=list)
    relevant: bool = True
    available: bool = False
    status: DisclosureStatus = DisclosureStatus.REQUESTED

    @model_validator(mode="after")
    def validate_status(self) -> RequestedDisclosureItem:
        if self.available and not self.source_record_ids:
            raise ValueError("available disclosure item requires a source-record reference")
        if not self.relevant and self.status not in {
            DisclosureStatus.REQUESTED,
            DisclosureStatus.NOT_APPLICABLE,
        }:
            raise ValueError("irrelevant disclosure item must be requested or not applicable")
        return self


class DiligenceRequest(BaseModel):
    request_id: str
    engagement_id: str
    stakeholder_id: str
    issued_at: datetime
    due_at: datetime
    items: list[RequestedDisclosureItem] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_items(self) -> DiligenceRequest:
        item_ids = [item.item_id for item in self.items]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("duplicate requested disclosure item")
        if self.due_at <= self.issued_at:
            raise ValueError("diligence request must be due after issuance")
        return self


class PackageVersion(BaseModel):
    model_config = ConfigDict(frozen=True)

    package_id: str
    version: int = Field(ge=1)
    intended_stakeholder_id: str
    included_item_ids: tuple[str, ...]
    omitted_requested_item_ids: tuple[str, ...]
    source_record_ids: tuple[str, ...]
    fact_values: FrozenFactMap = Field(default_factory=FrozenFactMap)
    created_at: datetime
    delivered_at: datetime | None = None
    prepared_by_id: str
    reviewed_by_ids: tuple[str, ...]
    supersedes_version: int | None = Field(default=None, ge=1)
    change_kind: Literal["initial", "supplement", "correction"] = "initial"
    change_note: str | None = None

    @model_validator(mode="after")
    def validate_delivery(self) -> PackageVersion:
        if self.delivered_at is not None and self.delivered_at < self.created_at:
            raise ValueError("package cannot be delivered before it is created")
        if set(self.included_item_ids) & set(self.omitted_requested_item_ids):
            raise ValueError("package item cannot be both included and omitted")
        if self.included_item_ids and not self.source_record_ids:
            raise ValueError("included package items require source-record IDs")
        if self.version == 1:
            if self.change_kind != "initial" or self.supersedes_version is not None:
                raise ValueError("package version 1 must be an initial version")
        elif self.change_kind == "initial" or self.supersedes_version is None:
            raise ValueError("later package version must identify its change and predecessor")
        return self


class DisclosurePackage(BaseModel):
    package_id: str
    request_id: str
    intended_stakeholder_id: str
    versions: list[PackageVersion] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_versions(self) -> DisclosurePackage:
        numbers = [item.version for item in self.versions]
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError("package versions must be complete, ordered, and unique")
        for index, version in enumerate(self.versions):
            if version.package_id != self.package_id:
                raise ValueError("package version references a different package")
            if version.intended_stakeholder_id != self.intended_stakeholder_id:
                raise ValueError("package version has the wrong intended stakeholder")
            if index and version.supersedes_version != self.versions[index - 1].version:
                raise ValueError("package correction must supersede the prior version")
        return self


class AccessDeliveryRecord(BaseModel):
    delivery_id: str
    package_id: str
    package_version: int = Field(ge=1)
    stakeholder_id: str
    delivered_at: datetime
    delivery_method: Literal["structured_room", "committee_packet", "secure_email"]
    acknowledged_at: datetime | None = None

    @model_validator(mode="after")
    def validate_acknowledgement(self) -> AccessDeliveryRecord:
        if self.acknowledged_at is not None and self.acknowledged_at < self.delivered_at:
            raise ValueError("delivery cannot be acknowledged before delivery")
        return self


class ExceptionScheduleItem(BaseModel):
    exception_id: str
    title: str
    description: str
    source_record_ids: list[str] = Field(min_length=1)
    corrected: bool
    unresolved: bool
    significance_context: list[str] = Field(min_length=1)


class ExceptionSchedule(BaseModel):
    schedule_id: str
    as_of: datetime
    items: list[ExceptionScheduleItem]


class RiskMetric(BaseModel):
    metric_id: str
    label: str
    value_text: str
    numeric_value: Decimal | None = None
    unit: str | None = None
    source_record_ids: list[str] = Field(min_length=1)
    calculation: str | None = None


class SignificanceAssessment(BaseModel):
    assessment_id: str
    review_threshold: Decimal = Field(gt=0)
    amount_considered: Decimal
    exceeds_review_threshold: bool
    qualitative_factors: list[str]
    significant_for_diligence: bool
    accounting_materiality_conclusion: Literal["not_concluded"] = "not_concluded"
    legal_conclusion: Literal["not_concluded"] = "not_concluded"
    caveat: str = Field(min_length=1)


class RiskSchedule(BaseModel):
    schedule_id: str
    as_of: datetime
    metrics: list[RiskMetric] = Field(min_length=10)
    exception_schedule: ExceptionSchedule
    significance: SignificanceAssessment

    @model_validator(mode="after")
    def validate_metrics(self) -> RiskSchedule:
        ids = [item.metric_id for item in self.metrics]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate risk-schedule metric")
        return self


class ScenarioSensitivity(BaseModel):
    scenario_id: str
    label: str
    henry_hub_change: Decimal
    chicago_basis_change: Decimal
    physical_economic_effect: Decimal
    futures_effect: Decimal
    basis_effect: Decimal
    net_economic_effect: Decimal
    estimated_variation_margin_cash_movement: Decimal
    resulting_liquidity_headroom: Decimal

    @model_validator(mode="after")
    def validate_math(self) -> ScenarioSensitivity:
        if self.physical_economic_effect + self.futures_effect != self.net_economic_effect:
            raise ValueError("scenario net economic effect does not reconcile")
        return self


class ScenarioAnalysisPackage(BaseModel):
    analysis_id: str
    prepared_at: datetime
    source_record_ids: list[str] = Field(min_length=1)
    rows: list[ScenarioSensitivity] = Field(min_length=3, max_length=3)
    is_forecast: Literal[False] = False
    probabilities_assigned: Literal[False] = False
    alters_game_state: Literal[False] = False
    creates_accounting_entries: Literal[False] = False
    assumptions_fictional: Literal[True] = True
    assumptions: list[str] = Field(min_length=1)


class DiligenceQuestion(BaseModel):
    question_id: str
    stakeholder_id: str
    asked_at: datetime
    text: str
    source_fact_keys: list[str]


class DiligenceResponse(BaseModel):
    response_id: str
    question_id: str
    responded_at: datetime
    responder_id: str
    posture: AnswerPosture
    text: str
    source_record_ids: list[str]
    complete: bool
    acknowledges_uncertainty: bool = False


class SupplementalResponse(BaseModel):
    supplemental_response_id: str
    original_response_id: str
    provided_at: datetime
    text: str
    source_record_ids: list[str] = Field(min_length=1)


class ManagementRepresentationDraft(BaseModel):
    representation_id: str
    version: int = Field(ge=1)
    drafted_at: datetime
    drafted_by_id: str
    reviewed_by_ids: list[str]
    statements: dict[str, str]
    source_record_ids: list[str]
    consistent_with_sources: bool
    escalated: bool = False


class DisclosureInconsistency(BaseModel):
    inconsistency_id: str
    fact_key: str
    first_package_id: str
    first_version: int = Field(ge=1)
    first_value: str
    second_package_id: str
    second_version: int = Field(ge=1)
    second_value: str
    detected_at: datetime
    corrected_by_package_id: str | None = None
    corrected_by_version: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_conflict(self) -> DisclosureInconsistency:
        if (
            self.first_package_id == self.second_package_id
            and self.first_version == self.second_version
        ):
            raise ValueError("inconsistency requires two distinct package versions")
        if self.first_value == self.second_value:
            raise ValueError("inconsistency requires conflicting values")
        if (self.corrected_by_package_id is None) != (self.corrected_by_version is None):
            raise ValueError("inconsistency correction requires package and version")
        return self


class DiligenceFinding(BaseModel):
    finding_id: str
    title: str
    description: str
    source_record_ids: list[str] = Field(min_length=1)
    stakeholder_ids: list[str] = Field(min_length=1)
    significance_basis: list[str] = Field(min_length=1)
    resolved: bool


class StakeholderReaction(BaseModel):
    stakeholder_id: str
    trust_delta: int = Field(ge=-10, le=10)
    reaction: str
    requested_follow_up: str | None = None


class DiligenceChoiceEffect(BaseModel):
    disclosure_scope: DisclosureScope | None = None
    exception_description: ExceptionDescription | None = None
    reviewer_choice: ReviewerChoice | None = None
    numbers_posture: NumbersPosture | None = None
    scenario_posture: ScenarioPosture | None = None
    remediation_posture: RemediationPosture | None = None
    buyer_answer_posture: AnswerPosture | None = None
    lender_answer_posture: AnswerPosture | None = None
    representation_posture: RepresentationPosture | None = None
    inconsistency_action: InconsistencyAction | None = None
    committee_posture: CommitteePosture | None = None
    final_action: FinalAction | None = None
    flags: dict[str, bool] = Field(default_factory=dict)
    relationship_deltas: dict[str, int] = Field(default_factory=dict)
    trajectory_deltas: dict[TrajectoryTag, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_relationships(self) -> DiligenceChoiceEffect:
        if any(abs(value) > 10 for value in self.relationship_deltas.values()):
            raise ValueError("diligence relationship delta is out of range")
        if any(abs(value) > 5 or value == 0 for value in self.trajectory_deltas.values()):
            raise ValueError("diligence trajectory delta must be nonzero and modest")
        return self


class DiligenceChoiceDefinition(BaseModel):
    id: str
    text: str
    effect: DiligenceChoiceEffect
    learning_objective_ids: list[str] = Field(min_length=1)


class DiligenceSceneDefinition(BaseModel):
    id: str
    day: int = Field(ge=1, le=4)
    speaker: str
    title: str
    text: str
    choices: list[DiligenceChoiceDefinition] = Field(min_length=2)


class DiligenceRequestSpec(BaseModel):
    item_id: str
    label: str
    source_record_ids: list[str] = Field(default_factory=list)
    relevant: bool = True


class SensitivityDefinition(BaseModel):
    scenario_id: str
    label: str
    henry_hub_change: Decimal
    chicago_basis_change: Decimal


class DiligenceScenario(BaseModel):
    schema_version: Literal[1]
    id: str
    title: str
    estimated_minutes: int = Field(ge=40, le=55)
    day_dates: dict[Literal["day_1", "day_2", "day_3", "day_4"], date]
    purpose: str
    transaction_structure: str
    buyer_name: str
    fictional_review_threshold: Decimal = Field(gt=0)
    stakeholders: list[Stakeholder] = Field(min_length=3)
    request_specs: list[DiligenceRequestSpec] = Field(min_length=10)
    sensitivities: list[SensitivityDefinition] = Field(min_length=3, max_length=3)
    scenes: list[DiligenceSceneDefinition] = Field(min_length=12)
    simplifying_assumptions: list[str] = Field(min_length=1)
    possible_outcomes: list[DiligenceOutcome] = Field(min_length=7)

    @model_validator(mode="after")
    def validate_scenario(self) -> DiligenceScenario:
        dates = [self.day_dates[f"day_{day}"] for day in range(1, 5)]
        stakeholder_ids = [item.stakeholder_id for item in self.stakeholders]
        request_ids = [item.item_id for item in self.request_specs]
        scene_ids = [item.id for item in self.scenes]
        choice_ids = [choice.id for scene in self.scenes for choice in scene.choices]
        outcomes = [item.value for item in self.possible_outcomes]
        for label, values in (
            ("stakeholder", stakeholder_ids),
            ("request", request_ids),
            ("scene", scene_ids),
            ("choice", choice_ids),
            ("outcome", outcomes),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate diligence {label} ID")
        if {scene.day for scene in self.scenes} != {1, 2, 3, 4}:
            raise ValueError("Diligence Room scenes must cover all four days")
        if dates != sorted(dates) or len(dates) != len(set(dates)):
            raise ValueError("Diligence Room day dates must be unique and ordered")
        if len(self.scenes) != 12:
            raise ValueError("The Diligence Room requires exactly twelve durable decisions")
        if set(self.possible_outcomes) != set(DiligenceOutcome):
            raise ValueError("all Diligence Room outcomes must be reachable")
        return self


class DiligenceLearningFile(BaseModel):
    schema_version: Literal[1]
    checks: list[KnowledgeCheckDefinition] = Field(min_length=1, max_length=6)
    day_check_ids: dict[
        Literal["day_1", "day_2", "day_3", "day_4"],
        list[str],
    ]

    @model_validator(mode="after")
    def validate_checks(self) -> DiligenceLearningFile:
        check_ids = [item.id for item in self.checks]
        assigned = [
            check_id for day_checks in self.day_check_ids.values() for check_id in day_checks
        ]
        if len(check_ids) != len(set(check_ids)):
            raise ValueError("duplicate Diligence Room check ID")
        if len(check_ids) > 6:
            raise ValueError("The Diligence Room permits at most six checks")
        if len(assigned) != len(set(assigned)) or set(assigned) != set(check_ids):
            raise ValueError("each diligence check must appear in exactly one day")
        return self


class DiligenceRoomState(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    scenario_id: str
    started: bool = True
    completed: bool = False
    current_stage: DiligenceStage = DiligenceStage.REQUEST_LIST
    selected_story_path_id: str | None = None
    engagement: DiligenceEngagement
    stakeholders: list[Stakeholder]
    requests: list[DiligenceRequest]
    source_references: list[SourceRecordReference] = Field(default_factory=list)
    packages: list[DisclosurePackage] = Field(default_factory=list)
    deliveries: list[AccessDeliveryRecord] = Field(default_factory=list)
    risk_schedule: RiskSchedule | None = None
    scenario_analysis: ScenarioAnalysisPackage | None = None
    questions: list[DiligenceQuestion] = Field(default_factory=list)
    responses: list[DiligenceResponse] = Field(default_factory=list)
    supplemental_responses: list[SupplementalResponse] = Field(default_factory=list)
    management_representations: list[ManagementRepresentationDraft] = Field(default_factory=list)
    inconsistencies: list[DisclosureInconsistency] = Field(default_factory=list)
    findings: list[DiligenceFinding] = Field(default_factory=list)
    stakeholder_reactions: list[StakeholderReaction] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    learning_check_ids: list[str] = Field(default_factory=list)
    practiced_objective_ids: list[str] = Field(default_factory=list)
    diligence_flags: dict[str, bool] = Field(default_factory=dict)
    relationships: dict[str, int] = Field(default_factory=dict)
    beginning_relationships: dict[str, int] = Field(default_factory=dict)
    beginning_career_weights: dict[str, int] = Field(default_factory=dict)
    disclosure_scope: DisclosureScope | None = None
    exception_description: ExceptionDescription | None = None
    reviewer_choice: ReviewerChoice | None = None
    numbers_posture: NumbersPosture | None = None
    scenario_posture: ScenarioPosture | None = None
    remediation_posture: RemediationPosture | None = None
    buyer_answer_posture: AnswerPosture | None = None
    lender_answer_posture: AnswerPosture | None = None
    representation_posture: RepresentationPosture | None = None
    inconsistency_action: InconsistencyAction | None = None
    committee_posture: CommitteePosture | None = None
    final_action: FinalAction | None = None
    transaction_status: TransactionStatus | None = None
    outcome: DiligenceOutcome | None = None

    @model_validator(mode="after")
    def validate_links(self) -> DiligenceRoomState:
        stakeholder_id_list = [item.stakeholder_id for item in self.stakeholders]
        stakeholder_ids = set(stakeholder_id_list)
        request_id_list = [item.request_id for item in self.requests]
        request_ids = set(request_id_list)
        request_by_id = {item.request_id: item for item in self.requests}
        package_id_list = [item.package_id for item in self.packages]
        packages = {
            (package.package_id, version.version)
            for package in self.packages
            for version in package.versions
        }
        version_by_key = {
            (package.package_id, version.version): version
            for package in self.packages
            for version in package.versions
        }
        question_id_list = [item.question_id for item in self.questions]
        question_ids = set(question_id_list)
        response_id_list = [item.response_id for item in self.responses]
        response_ids = set(response_id_list)
        unique_groups = (
            ("stakeholder", stakeholder_id_list),
            ("request", request_id_list),
            ("package", package_id_list),
            ("delivery", [item.delivery_id for item in self.deliveries]),
            ("question", question_id_list),
            ("response", response_id_list),
            (
                "supplemental response",
                [item.supplemental_response_id for item in self.supplemental_responses],
            ),
            (
                "management representation",
                [item.representation_id for item in self.management_representations],
            ),
            ("finding", [item.finding_id for item in self.findings]),
        )
        for label, values in unique_groups:
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate diligence {label} ID")
        if set(self.engagement.stakeholder_ids) != stakeholder_ids:
            raise ValueError("diligence engagement stakeholder identities do not reconcile")
        if any(item.engagement_id != self.engagement.engagement_id for item in self.requests):
            raise ValueError("diligence request references an unknown engagement")
        if any(item.stakeholder_id not in stakeholder_ids for item in self.requests):
            raise ValueError("diligence request has an unknown stakeholder")
        if any(package.request_id not in request_ids for package in self.packages):
            raise ValueError("disclosure package has an unknown request")
        if any(
            package.intended_stakeholder_id not in stakeholder_ids
            or request_by_id[package.request_id].stakeholder_id != package.intended_stakeholder_id
            for package in self.packages
            if package.request_id in request_by_id
        ):
            raise ValueError("disclosure package has an unknown or mismatched stakeholder")
        if any((item.package_id, item.package_version) not in packages for item in self.deliveries):
            raise ValueError("delivery references an unknown package version")
        if any(
            item.stakeholder_id not in stakeholder_ids
            or (
                (item.package_id, item.package_version) in version_by_key
                and version_by_key[(item.package_id, item.package_version)].intended_stakeholder_id
                != item.stakeholder_id
            )
            for item in self.deliveries
        ):
            raise ValueError("delivery has an unknown or mismatched stakeholder")
        if any(item.stakeholder_id not in stakeholder_ids for item in self.questions):
            raise ValueError("diligence question has an unknown stakeholder")
        if any(item.question_id not in question_ids for item in self.responses):
            raise ValueError("response references an unknown question")
        if any(
            item.original_response_id not in response_ids for item in self.supplemental_responses
        ):
            raise ValueError("supplement references an unknown response")
        for item in self.inconsistencies:
            if (item.first_package_id, item.first_version) not in packages or (
                item.second_package_id,
                item.second_version,
            ) not in packages:
                raise ValueError("inconsistency references an unknown package version")
        if any(set(item.stakeholder_ids) - stakeholder_ids for item in self.findings) or any(
            item.stakeholder_id not in stakeholder_ids for item in self.stakeholder_reactions
        ):
            raise ValueError("diligence result references an unknown stakeholder")
        reaction_ids = [item.stakeholder_id for item in self.stakeholder_reactions]
        if len(reaction_ids) != len(set(reaction_ids)):
            raise ValueError("duplicate diligence stakeholder reaction")
        if self.completed and (
            self.current_stage != DiligenceStage.COMPLETE
            or self.outcome is None
            or self.transaction_status is None
        ):
            raise ValueError("completed diligence requires outcome and transaction status")
        return self
