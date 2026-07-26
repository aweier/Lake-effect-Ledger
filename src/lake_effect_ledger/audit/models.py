"""Typed records for the deliberately scoped No Surprises audit walkthrough."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lake_effect_ledger.learning.models import (
    KnowledgeCheckDefinition,
    TrajectoryTag,
)
from lake_effect_ledger.trading.models import EleventhOutcome


def _aware(value: datetime | None) -> bool:
    return value is None or (value.tzinfo is not None and value.utcoffset() is not None)


class AuditStage(StrEnum):
    REQUEST_LIST = "request_list"
    WALKTHROUGH = "walkthrough"
    CONTROL_TESTING = "control_testing"
    PRELIMINARY_FINDINGS = "preliminary_findings"
    MANAGEMENT_RESPONSE = "management_response"
    BEFORE_EXIT = "before_exit"
    COMPLETE = "complete"


class PackageStrategy(StrEnum):
    COMPLETE = "complete_linked_chain"
    REQUESTED_ONLY = "requested_records_only"
    EVELYN_REVIEW = "evelyn_review_first"


class ChronologyStyle(StrEnum):
    CLEAR = "clear_chronology"
    MINIMAL = "minimal_context"


class SelectionNotice(StrEnum):
    EVELYN = "tell_evelyn"
    CAL = "tell_cal"
    NEITHER = "tell_neither"


class WalkthroughPosture(StrEnum):
    ACCURATE = "accurate_and_complete"
    NARROW = "narrow"
    UNCERTAIN = "acknowledge_uncertainty"
    FALSE_PROCESS_CLAIM = "claim_process_followed"


class VolumeExplanation(StrEnum):
    RECORD_BASED = "record_based"
    CAL_EXPECTATION = "cal_expectation"
    PLAYER_RECOMMENDATION = "player_recommendation"


class ResponsibilityPosture(StrEnum):
    ACCEPT_OWN = "accept_own_actions"
    DISPUTE_WITH_EVIDENCE = "dispute_with_evidence"
    PROTECT_CAL = "protect_cal"


class ControlView(StrEnum):
    DESIGN_AND_OPERATION = "design_and_operation"
    ISOLATED_ERROR = "isolated_error"
    POLICY_SUFFICIENT = "policy_sufficient"


class FindingPosture(StrEnum):
    AGREE = "agree"
    EVIDENCE_DISPUTE = "evidence_dispute"
    UNSUPPORTED_DISPUTE = "unsupported_dispute"


class SupplementChoice(StrEnum):
    DISCLOSE_OMITTED = "disclose_omitted"
    KEEP_INITIAL_SCOPE = "keep_initial_scope"
    NO_SUPPLEMENT_NEEDED = "no_supplement_needed"


class ResponseAgreement(StrEnum):
    AGREE = "agree"
    PARTIAL = "partially_agree"
    DISAGREE = "disagree"


class RootCauseCategory(StrEnum):
    UNCLEAR_OWNERSHIP = "unclear_ownership"
    INADEQUATE_AUTHORIZATION_DESIGN = "inadequate_authorization_design"
    MANUAL_PROCESS_ERROR = "manual_process_error"
    SYSTEM_INTEGRATION_GAP = "system_integration_gap"
    TRAINING_GAP = "training_gap"
    MANAGEMENT_OVERRIDE = "management_override"
    INCOMPLETE_PHYSICAL_INFORMATION = "incomplete_physical_information"
    UNTIMELY_ESCALATION = "untimely_escalation"


class RemediationKind(StrEnum):
    AUTOMATED_THREE_WAY_MATCH = "automated_three_way_match"
    DAILY_SUPERVISORY_REVIEW = "daily_supervisory_review"
    PHYSICAL_SUPPORT_GATE = "physical_support_gate"
    TRAINING_AND_POLICY = "training_and_policy"
    FORMAL_RISK_ACCEPTANCE = "formal_risk_acceptance"


class ControlNature(StrEnum):
    PREVENTIVE = "preventive"
    DETECTIVE = "detective"


class ControlExecution(StrEnum):
    MANUAL = "manual"
    AUTOMATED = "automated"


class TestResultRating(StrEnum):
    PASSED = "passed"
    PASSED_WITH_EXCEPTION = "passed_with_exception"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"
    UNABLE_TO_TEST = "unable_to_test"
    REMEDIATED_AFTER_DISCOVERY = "remediated_after_discovery"


class ExceptionCategory(StrEnum):
    ERROR = "error"
    DOCUMENTATION_GAP = "documentation_gap"
    LATE_CONTROL = "late_control"
    CONTROL_DESIGN_WEAKNESS = "control_design_weakness"
    NONPERFORMANCE = "failure_to_perform"
    MANAGEMENT_OVERRIDE = "management_override"
    INACCURATE_STATEMENT = "deliberate_inaccurate_statement"
    CORRECTED_EXCEPTION = "corrected_exception"


class FindingSeverity(StrEnum):
    ADVISORY = "advisory"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class FindingStatus(StrEnum):
    OPEN = "open"
    MANAGEMENT_RESPONSE_RECEIVED = "management_response_received"
    REMEDIATION_PLANNED = "remediation_planned"
    RISK_ACCEPTED = "risk_accepted"
    CLOSED = "closed"


class AuditOutcome(StrEnum):
    CONTROL_WORKED_LATE = "control_worked_late"
    CLEAN_WALKTHROUGH = "clean_walkthrough"
    MANAGEMENT_OVERRIDE = "management_override"
    QUIET_FILE_OPENS = "quiet_file_opens"
    POLICY_IS_NOT_A_CONTROL = "policy_is_not_a_control"
    NO_SURPRISES = "no_surprises"
    TWO_VERSIONS_OF_MONDAY = "two_versions_of_monday"


class AuditScope(BaseModel):
    transaction_reference: str = Field(min_length=1)
    period_start: date
    period_end: date
    included_processes: list[str] = Field(min_length=1)
    excluded_processes: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_period(self) -> AuditScope:
        if self.period_end < self.period_start:
            raise ValueError("audit scope period is inverted")
        return self


class AuditEngagement(BaseModel):
    engagement_id: str = Field(pattern=r"^[a-z0-9_]+$")
    title: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    lead_auditor_id: str = Field(min_length=1)
    opened_at: datetime
    scope: AuditScope

    @model_validator(mode="after")
    def validate_timestamp(self) -> AuditEngagement:
        if not _aware(self.opened_at):
            raise ValueError("audit engagement timestamp must include a UTC offset")
        return self


class RequestedItem(BaseModel):
    request_item_id: str = Field(pattern=r"^[a-z0-9_]+$")
    requested_record: str = Field(min_length=1)
    stable_record_id: str = Field(min_length=1)
    record_type: str = Field(min_length=1)
    available: bool
    included_initially: bool = False
    date_created: datetime | None = None
    date_provided: datetime | None = None
    related_transaction: str = Field(min_length=1)
    contemporaneous: bool | None = None
    response_status: Literal["pending", "provided", "missing", "supplemented"] = "pending"

    @model_validator(mode="after")
    def validate_dates_and_status(self) -> RequestedItem:
        if not _aware(self.date_created) or not _aware(self.date_provided):
            raise ValueError("evidence timestamps must include UTC offsets")
        if not self.available and self.included_initially:
            raise ValueError("missing evidence cannot be included")
        if self.response_status == "missing" and self.available:
            raise ValueError("available evidence cannot be represented as deleted or missing")
        if self.response_status in {"provided", "supplemented"} and self.date_provided is None:
            raise ValueError("provided evidence requires a provided date")
        return self


class EvidenceRequest(BaseModel):
    request_id: str = Field(pattern=r"^[a-z0-9_]+$")
    engagement_id: str
    issued_at: datetime
    due_at: datetime
    requested_items: list[RequestedItem] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_request(self) -> EvidenceRequest:
        if not _aware(self.issued_at) or not _aware(self.due_at):
            raise ValueError("evidence request timestamps must include UTC offsets")
        if self.due_at <= self.issued_at:
            raise ValueError("evidence request due date must follow issue date")
        ids = [item.request_item_id for item in self.requested_items]
        records = [item.stable_record_id for item in self.requested_items]
        if len(ids) != len(set(ids)) or len(records) != len(set(records)):
            raise ValueError("duplicate evidence request or stable record ID")
        return self


class EvidencePackageResponse(BaseModel):
    response_id: str = Field(pattern=r"^[a-z0-9_]+$")
    request_id: str
    submitted_at: datetime
    prepared_by_id: str
    included_request_item_ids: list[str]
    additional_record_ids: list[str] = Field(default_factory=list)
    supplemental: bool = False
    note: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_response(self) -> EvidencePackageResponse:
        if not _aware(self.submitted_at):
            raise ValueError("evidence response timestamp must include a UTC offset")
        if len(self.included_request_item_ids) != len(set(self.included_request_item_ids)):
            raise ValueError("duplicate item in evidence response")
        if len(self.additional_record_ids) != len(set(self.additional_record_ids)):
            raise ValueError("duplicate additional record in evidence response")
        return self


class ChronologyEntry(BaseModel):
    chronology_entry_id: str = Field(pattern=r"^[a-z0-9_]+$")
    event_label: str = Field(min_length=1)
    record_id: str = Field(min_length=1)
    record_type: str = Field(min_length=1)
    timestamp: datetime | None = None
    contemporaneous: bool
    observation: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_timestamp(self) -> ChronologyEntry:
        if not _aware(self.timestamp):
            raise ValueError("chronology timestamps must include a UTC offset")
        return self


class AuditChronology(BaseModel):
    chronology_id: str = Field(pattern=r"^[a-z0-9_]+$")
    transaction_reference: str
    generated_at: datetime
    entries: list[ChronologyEntry] = Field(min_length=1)
    contradictions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_chronology(self) -> AuditChronology:
        if not _aware(self.generated_at):
            raise ValueError("chronology generation timestamp must include a UTC offset")
        ids = [item.chronology_entry_id for item in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate chronology entry ID")
        known_times = [item.timestamp for item in self.entries if item.timestamp is not None]
        if known_times != sorted(known_times):
            raise ValueError("chronology entries with timestamps must be ordered")
        return self


class WalkthroughStep(BaseModel):
    step_id: str = Field(pattern=r"^[a-z0-9_]+$")
    sequence: int = Field(ge=1, le=14)
    question: str = Field(min_length=1)
    evidence_record_ids: list[str] = Field(min_length=1)
    player_posture: WalkthroughPosture
    player_explanation: str = Field(min_length=1)
    consistent_with_records: bool
    auditor_observation: str = Field(min_length=1)


class ControlOwner(BaseModel):
    owner_id: str = Field(pattern=r"^[a-z0-9_]+$")
    person_id: str
    role: str = Field(min_length=1)


class ControlActivity(BaseModel):
    activity_id: str = Field(pattern=r"^[a-z0-9_]+$")
    objective_id: str = Field(pattern=r"^[a-z0-9_]+$")
    description: str = Field(min_length=1)
    owner_id: str = Field(pattern=r"^[a-z0-9_]+$")
    nature: ControlNature
    execution: ControlExecution


class ControlObjective(BaseModel):
    objective_id: str = Field(pattern=r"^[a-z0-9_]+$")
    title: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    activity_ids: list[str] = Field(min_length=1)


class TestProcedure(BaseModel):
    procedure_id: str = Field(pattern=r"^[a-z0-9_]+$")
    control_objective_id: str = Field(pattern=r"^[a-z0-9_]+$")
    description: str = Field(min_length=1)


class PopulationReference(BaseModel):
    population_id: str = Field(pattern=r"^[a-z0-9_]+$")
    transaction_reference: str = Field(min_length=1)
    record_ids: list[str] = Field(min_length=1)


class AuditException(BaseModel):
    exception_id: str = Field(pattern=r"^[a-z0-9_]+$")
    control_objective_id: str = Field(pattern=r"^[a-z0-9_]+$")
    category: ExceptionCategory
    description: str = Field(min_length=1)
    evidence_record_ids: list[str] = Field(min_length=1)
    discovered_at: datetime

    @model_validator(mode="after")
    def validate_timestamp(self) -> AuditException:
        if not _aware(self.discovered_at):
            raise ValueError("audit exception timestamp must include a UTC offset")
        return self


class ControlTestResult(BaseModel):
    result_id: str = Field(pattern=r"^[a-z0-9_]+$")
    control_objective_id: str = Field(pattern=r"^[a-z0-9_]+$")
    procedure_id: str = Field(pattern=r"^[a-z0-9_]+$")
    population_id: str = Field(pattern=r"^[a-z0-9_]+$")
    rating: TestResultRating
    design_effective: bool
    operating_effective: bool
    evidence_record_ids: list[str] = Field(min_length=1)
    exception_ids: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_result(self) -> ControlTestResult:
        if (
            self.rating
            in {
                TestResultRating.FAILED,
                TestResultRating.PASSED_WITH_EXCEPTION,
                TestResultRating.REMEDIATED_AFTER_DISCOVERY,
            }
            and not self.exception_ids
        ):
            raise ValueError("exception-bearing test result requires an exception")
        return self


class Finding(BaseModel):
    finding_id: str = Field(pattern=r"^[a-z0-9_]+$")
    title: str = Field(min_length=1)
    severity: FindingSeverity
    exception_ids: list[str] = Field(default_factory=list)
    evidence_record_ids: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)
    documented_rationale_without_exception: bool = False
    status: FindingStatus = FindingStatus.OPEN

    @model_validator(mode="after")
    def validate_basis(self) -> Finding:
        if not self.exception_ids and not self.documented_rationale_without_exception:
            raise ValueError("finding requires an exception or documented rationale")
        return self


class RemediationOwner(BaseModel):
    owner_id: str = Field(pattern=r"^[a-z0-9_]+$")
    person_id: str
    role: str = Field(min_length=1)


class RemediationRecommendation(BaseModel):
    remediation_id: str = Field(pattern=r"^[a-z0-9_]+$")
    finding_ids: list[str] = Field(min_length=1)
    kind: RemediationKind
    proposed_action: str = Field(min_length=1)
    owner: RemediationOwner
    target_date: date
    interim_control: str = Field(min_length=1)
    residual_risk: str = Field(min_length=1)
    approved: bool


class ManagementResponse(BaseModel):
    response_id: str = Field(pattern=r"^[a-z0-9_]+$")
    finding_id: str = Field(pattern=r"^[a-z0-9_]+$")
    agreement: ResponseAgreement
    disagreement_evidence_ids: list[str] = Field(default_factory=list)
    root_cause: RootCauseCategory
    proposed_action: str = Field(min_length=1)
    owner: RemediationOwner
    target_date: date
    interim_control: str = Field(min_length=1)
    residual_risk: str = Field(min_length=1)
    status: FindingStatus

    @model_validator(mode="after")
    def validate_disagreement(self) -> ManagementResponse:
        if self.agreement != ResponseAgreement.AGREE and not self.disagreement_evidence_ids:
            raise ValueError("management disagreement requires supporting evidence")
        return self


class AuditChoiceEffect(BaseModel):
    package_strategy: PackageStrategy | None = None
    chronology_style: ChronologyStyle | None = None
    selection_notice: SelectionNotice | None = None
    walkthrough_posture: WalkthroughPosture | None = None
    volume_explanation: VolumeExplanation | None = None
    responsibility_posture: ResponsibilityPosture | None = None
    control_view: ControlView | None = None
    finding_posture: FindingPosture | None = None
    supplement_choice: SupplementChoice | None = None
    remediation_kind: RemediationKind | None = None
    response_agreement: ResponseAgreement | None = None
    elevate_unresolved: bool | None = None
    flags: dict[str, bool] = Field(default_factory=dict)
    relationship_deltas: dict[str, int] = Field(default_factory=dict)
    trajectory_deltas: dict[TrajectoryTag, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_effect(self) -> AuditChoiceEffect:
        fields = self.model_dump(exclude={"flags", "relationship_deltas", "trajectory_deltas"})
        if (
            all(value is None for value in fields.values())
            and not self.flags
            and not self.relationship_deltas
            and not self.trajectory_deltas
        ):
            raise ValueError("audit choice must have at least one effect")
        if any(
            amount == 0 or not -3 <= amount <= 3 for amount in self.relationship_deltas.values()
        ):
            raise ValueError("audit relationship deltas must be between -3 and 3 and nonzero")
        if any(amount == 0 or not -3 <= amount <= 3 for amount in self.trajectory_deltas.values()):
            raise ValueError("audit trajectory deltas must be between -3 and 3 and nonzero")
        return self


class AuditChoiceDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    text: str = Field(min_length=1)
    effect: AuditChoiceEffect
    learning_objective_ids: list[str] = Field(min_length=1)


class AuditSceneDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    day: int = Field(ge=1, le=4)
    speaker: str = Field(min_length=1)
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    choices: list[AuditChoiceDefinition] = Field(min_length=2)


class AuditScenario(BaseModel):
    schema_version: Literal[1]
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    title: str = Field(min_length=1)
    estimated_minutes: int = Field(ge=35, le=50)
    day_dates: dict[Literal["day_1", "day_2", "day_3", "day_4"], date]
    engagement_objective: str = Field(min_length=1)
    scope_inclusions: list[str] = Field(min_length=1)
    scope_exclusions: list[str] = Field(min_length=1)
    request_specs: list[RequestedItem] = Field(min_length=15)
    control_owners: list[ControlOwner] = Field(min_length=1)
    control_objectives: list[ControlObjective] = Field(min_length=8, max_length=8)
    control_activities: list[ControlActivity] = Field(min_length=8)
    test_procedures: list[TestProcedure] = Field(min_length=8, max_length=8)
    scenes: list[AuditSceneDefinition] = Field(min_length=10)
    possible_outcomes: list[AuditOutcome] = Field(min_length=7, max_length=7)
    simplifying_assumptions: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scenario(self) -> AuditScenario:
        dates = [self.day_dates[f"day_{day}"] for day in range(1, 5)]
        if dates != sorted(dates) or len(dates) != len(set(dates)):
            raise ValueError("audit day dates must be unique and ordered")
        if {item for item in self.possible_outcomes} != set(AuditOutcome):
            raise ValueError("all No Surprises outcomes must be reachable")
        request_ids = [item.request_item_id for item in self.request_specs]
        finding_scene_ids = [item.id for item in self.scenes]
        if len(request_ids) != len(set(request_ids)):
            raise ValueError("duplicate audit request ID")
        if len(finding_scene_ids) != len(set(finding_scene_ids)):
            raise ValueError("duplicate audit scene ID")
        objective_ids = {item.objective_id for item in self.control_objectives}
        owner_ids = {item.owner_id for item in self.control_owners}
        activity_ids = {item.activity_id for item in self.control_activities}
        if len(objective_ids) != 8:
            raise ValueError("No Surprises requires eight unique control objectives")
        if any(item.objective_id not in objective_ids for item in self.control_activities):
            raise ValueError("control activity references an unknown objective")
        if any(item.owner_id not in owner_ids for item in self.control_activities):
            raise ValueError("control activity references an unknown owner")
        if any(set(item.activity_ids) - activity_ids for item in self.control_objectives):
            raise ValueError("control objective references an unknown activity")
        if {item.control_objective_id for item in self.test_procedures} != objective_ids:
            raise ValueError("every control objective requires exactly one test procedure")
        if {item.day for item in self.scenes} != {1, 2, 3, 4}:
            raise ValueError("audit narrative requires scenes on all four days")
        return self


class AuditLearningFile(BaseModel):
    schema_version: Literal[1]
    checks: list[KnowledgeCheckDefinition] = Field(min_length=6, max_length=6)
    day_check_ids: dict[
        Literal["day_1", "day_2", "day_3", "day_4"],
        list[str],
    ]

    @model_validator(mode="after")
    def validate_checks(self) -> AuditLearningFile:
        check_ids = [item.id for item in self.checks]
        assigned = [
            check_id for day_checks in self.day_check_ids.values() for check_id in day_checks
        ]
        if len(check_ids) != len(set(check_ids)):
            raise ValueError("duplicate No Surprises check ID")
        if len(check_ids) != 6:
            raise ValueError("No Surprises requires exactly six checks")
        if len(assigned) != len(set(assigned)) or set(assigned) != set(check_ids):
            raise ValueError("each No Surprises check must appear in exactly one day")
        return self


class NoSurprisesState(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    scenario_id: str
    started: bool = True
    completed: bool = False
    current_stage: AuditStage = AuditStage.REQUEST_LIST
    current_scene_index: int = Field(default=0, ge=0)
    selected_story_path_id: str | None = None
    prior_eleventh_outcome: EleventhOutcome
    engagement: AuditEngagement
    evidence_request: EvidenceRequest
    package_responses: list[EvidencePackageResponse] = Field(default_factory=list)
    chronology: AuditChronology | None = None
    walkthrough_steps: list[WalkthroughStep] = Field(default_factory=list)
    control_results: list[ControlTestResult] = Field(default_factory=list)
    exceptions: list[AuditException] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    management_responses: list[ManagementResponse] = Field(default_factory=list)
    remediations: list[RemediationRecommendation] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    learning_check_ids: list[str] = Field(default_factory=list)
    practiced_objective_ids: list[str] = Field(default_factory=list)
    audit_flags: dict[str, bool] = Field(default_factory=dict)
    relationships: dict[str, int] = Field(
        default_factory=lambda: {
            "noah_shah": 0,
            "evelyn_marsh": 0,
            "cal_rourke": 0,
            "marisol_vega": 0,
        }
    )
    beginning_relationships: dict[str, int] = Field(default_factory=dict)
    package_strategy: PackageStrategy | None = None
    chronology_style: ChronologyStyle | None = None
    selection_notice: SelectionNotice | None = None
    walkthrough_posture: WalkthroughPosture | None = None
    volume_explanation: VolumeExplanation | None = None
    responsibility_posture: ResponsibilityPosture | None = None
    control_view: ControlView | None = None
    finding_posture: FindingPosture | None = None
    supplement_choice: SupplementChoice | None = None
    remediation_kind: RemediationKind | None = None
    response_agreement: ResponseAgreement | None = None
    elevate_unresolved: bool | None = None
    outcome: AuditOutcome | None = None

    @model_validator(mode="after")
    def validate_audit_links(self) -> NoSurprisesState:
        response_ids = [item.response_id for item in self.package_responses]
        exception_ids = [item.exception_id for item in self.exceptions]
        finding_ids = [item.finding_id for item in self.findings]
        if len(response_ids) != len(set(response_ids)):
            raise ValueError("duplicate evidence package response")
        if len(exception_ids) != len(set(exception_ids)):
            raise ValueError("duplicate audit exception ID")
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("duplicate finding ID")
        known_request_items = {
            item.request_item_id for item in self.evidence_request.requested_items
        }
        if any(
            set(response.included_request_item_ids) - known_request_items
            for response in self.package_responses
        ):
            raise ValueError("evidence response references an unknown request item")
        known_exceptions = set(exception_ids)
        if any(set(item.exception_ids) - known_exceptions for item in self.control_results):
            raise ValueError("test result references an unknown exception")
        if any(set(item.exception_ids) - known_exceptions for item in self.findings):
            raise ValueError("finding references an unknown exception")
        known_findings = set(finding_ids)
        if any(item.finding_id not in known_findings for item in self.management_responses):
            raise ValueError("management response references an unknown finding")
        if any(set(item.finding_ids) - known_findings for item in self.remediations):
            raise ValueError("remediation references an unknown finding")
        if self.completed and (self.current_stage != AuditStage.COMPLETE or self.outcome is None):
            raise ValueError("completed audit requires a derived outcome")
        return self
