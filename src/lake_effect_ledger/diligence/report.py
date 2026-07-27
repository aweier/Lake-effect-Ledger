"""Actual-state Diligence Room Report."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from lake_effect_ledger.diligence.engine import DiligenceEngine
from lake_effect_ledger.diligence.models import (
    DiligenceFinding,
    DiligenceOutcome,
    DiligenceQuestion,
    DiligenceRequest,
    DiligenceResponse,
    DisclosureInconsistency,
    DisclosurePackage,
    ManagementRepresentationDraft,
    RemediationStatus,
    RiskSchedule,
    ScenarioAnalysisPackage,
    Stakeholder,
    StakeholderReaction,
    SupplementalResponse,
    TransactionStatus,
)
from lake_effect_ledger.learning.models import TRAJECTORY_LABELS, TrajectoryTag
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.state import GameState


class AuditFindingReference(BaseModel):
    finding_id: str
    title: str
    severity: str
    status: str


class LiquidityPosition(BaseModel):
    operating_cash: Decimal
    revolver_outstanding: Decimal
    undrawn_availability: Decimal
    available_liquidity: Decimal
    covenant_minimum: Decimal
    covenant_headroom: Decimal
    covenant_passed: bool


class DiligenceRoomReport(BaseModel):
    report_id: str
    title: str
    outcome: DiligenceOutcome
    engagement_purpose: str
    transaction_structure: str
    stakeholders: list[Stakeholder]
    requested_items: list[DiligenceRequest]
    package_versions: list[DisclosurePackage]
    included_records: list[str]
    missing_records: list[str]
    source_links: list[str] = Field(min_length=1)
    risk_schedule: RiskSchedule
    scenario_sensitivities: ScenarioAnalysisPackage
    questions: list[DiligenceQuestion]
    responses: list[DiligenceResponse]
    supplemental_responses: list[SupplementalResponse]
    disclosure_inconsistencies: list[DisclosureInconsistency]
    audit_findings_referenced: list[AuditFindingReference]
    remediation_status: RemediationStatus
    liquidity_position: LiquidityPosition
    management_representations: list[ManagementRepresentationDraft]
    diligence_findings: list[DiligenceFinding]
    unresolved_issues: list[str]
    stakeholder_reactions: list[StakeholderReaction]
    transaction_status: TransactionStatus
    career_consequences: list[str] = Field(min_length=1)
    prior_choice_effects: list[str] = Field(min_length=1)
    practiced_learning_objectives: list[str] = Field(min_length=1)
    simplifying_assumptions: list[str] = Field(min_length=1)
    reconciled_to_source_records: bool
    original_package_versions_preserved: bool

    @model_validator(mode="after")
    def validate_report(self) -> DiligenceRoomReport:
        if not self.reconciled_to_source_records:
            raise ValueError("diligence report must reconcile to source records")
        if not self.original_package_versions_preserved:
            raise ValueError("diligence report must preserve original package versions")
        if any(
            not package.versions or package.versions[0].version != 1
            for package in self.package_versions
        ):
            raise ValueError("diligence report is missing an original package version")
        return self


def build_diligence_room_report(
    state: GameState,
    content: ContentBundle,
) -> DiligenceRoomReport:
    diligence = state.diligence_room
    audit = state.no_surprises
    treasury = state.treasury
    if (
        diligence is None
        or not diligence.completed
        or diligence.outcome is None
        or diligence.transaction_status is None
        or diligence.risk_schedule is None
        or diligence.scenario_analysis is None
        or audit is None
        or treasury is None
        or treasury.covenant_result is None
    ):
        raise ValueError("complete The Diligence Room before building its report")
    engine = DiligenceEngine(content)
    engine.assert_source_reconciliation(state)
    included = list(
        dict.fromkeys(
            source_id
            for package in diligence.packages
            for version in package.versions
            for source_id in version.source_record_ids
        )
    )
    available_requested = {
        source_id
        for request in diligence.requests
        for item in request.items
        if item.available
        for source_id in item.source_record_ids
    }
    missing = sorted(available_requested - set(included))
    source_links = list(
        dict.fromkeys(
            [
                *(item.record_id for item in diligence.source_references),
                *included,
                *(
                    source_id
                    for finding in diligence.findings
                    for source_id in finding.source_record_ids
                ),
            ]
        )
    )
    audit_findings = [
        AuditFindingReference(
            finding_id=item.finding_id,
            title=item.title,
            severity=item.severity.value,
            status=item.status.value,
        )
        for item in audit.findings
    ]
    covenant = treasury.covenant_result
    liquidity = LiquidityPosition(
        operating_cash=state.corporate_cash,
        revolver_outstanding=treasury.facility.outstanding,
        undrawn_availability=treasury.facility.undrawn_availability,
        available_liquidity=covenant.available_liquidity,
        covenant_minimum=covenant.minimum_required,
        covenant_headroom=covenant.available_liquidity - covenant.minimum_required,
        covenant_passed=covenant.passed,
    )
    unresolved = [item.title for item in diligence.findings if not item.resolved] or [
        "No unresolved diligence finding remains beyond monitored audit remediation."
    ]
    objectives = [
        content.lesson(objective_id).title for objective_id in diligence.practiced_objective_ids
    ]
    career = _career_consequences(state)
    prior = _prior_choice_effects(state)
    original_versions = all(
        package.versions[0].change_kind == "initial"
        and package.versions[0].supersedes_version is None
        for package in diligence.packages
    )
    return DiligenceRoomReport(
        report_id="diligence_room_report_majority_acquisition",
        title="Diligence Room Report",
        outcome=diligence.outcome,
        engagement_purpose=diligence.engagement.purpose,
        transaction_structure=diligence.engagement.transaction_structure,
        stakeholders=list(diligence.stakeholders),
        requested_items=list(diligence.requests),
        package_versions=list(diligence.packages),
        included_records=included,
        missing_records=missing,
        source_links=source_links,
        risk_schedule=diligence.risk_schedule,
        scenario_sensitivities=diligence.scenario_analysis,
        questions=list(diligence.questions),
        responses=list(diligence.responses),
        supplemental_responses=list(diligence.supplemental_responses),
        disclosure_inconsistencies=list(diligence.inconsistencies),
        audit_findings_referenced=audit_findings,
        remediation_status=engine.actual_remediation_status(state),
        liquidity_position=liquidity,
        management_representations=list(diligence.management_representations),
        diligence_findings=list(diligence.findings),
        unresolved_issues=unresolved,
        stakeholder_reactions=list(diligence.stakeholder_reactions),
        transaction_status=diligence.transaction_status,
        career_consequences=career,
        prior_choice_effects=prior,
        practiced_learning_objectives=objectives,
        simplifying_assumptions=list(content.diligence_scenario.simplifying_assumptions),
        reconciled_to_source_records=True,
        original_package_versions_preserved=original_versions,
    )


def _career_consequences(state: GameState) -> list[str]:
    diligence = state.diligence_room
    if diligence is None:
        return []
    consequences = []
    for tag, current in state.career_trajectory.tag_weights.items():
        beginning = diligence.beginning_career_weights.get(tag.value, 0)
        if current > beginning:
            consequences.append(
                f"The chapter reinforced a {TRAJECTORY_LABELS[tag].lower()} pattern."
            )
    if diligence.relationships.get("evelyn_marsh", 0) >= 1:
        consequences.append("Evelyn allows the player to present source-linked schedules.")
    else:
        consequences.append(
            "Evelyn retains presentation responsibility and limits the junior role."
        )
    if diligence.relationships.get("sofia_marin", 0) >= 2:
        consequences.append("Sofia directs later commodity-control questions to the player.")
    if diligence.relationships.get("cal_rourke", 0) >= 3:
        consequences.append(
            "Management sees the player as useful inside the preferred commercial narrative."
        )
    elif state.career_trajectory.tag_weights.get(TrajectoryTag.CHALLENGES_MANAGEMENT, 0) >= 2:
        consequences.append(
            "Management treats the player as capable and potentially dangerous to weak drafts."
        )
    return list(dict.fromkeys(consequences)) or [
        "The player's longer-term professional direction remains unresolved."
    ]


def _prior_choice_effects(state: GameState) -> list[str]:
    diligence = state.diligence_room
    audit = state.no_surprises
    chapter = state.eleventh_contract
    if diligence is None or audit is None or chapter is None:
        return []
    effects = [
        f"The Eleventh Contract enters diligence as {chapter.outcome.value}.",
        f"Noah's final audit outcome enters diligence as {audit.outcome.value}.",
        (
            "Noah initially trusts the player's package work."
            if diligence.diligence_flags.get("noah_initially_trusts_package")
            else "Noah initially requires closer review of the player's package work."
        ),
        (
            "Cal applies private pressure because prior choices increased access."
            if diligence.diligence_flags.get("cal_applies_pressure")
            else "Cal provides information without established leverage over the player."
        ),
        (
            "Evelyn initially permits the player to present subject to owner review."
            if diligence.diligence_flags.get("evelyn_initially_allows_presentation")
            else "Evelyn initially retains presentation responsibility until reliability improves."
        ),
    ]
    return effects
