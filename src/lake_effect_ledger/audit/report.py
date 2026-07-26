"""Actual-state Internal Audit Walkthrough Report for No Surprises."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from lake_effect_ledger.audit.models import (
    AuditChronology,
    AuditException,
    AuditOutcome,
    AuditScope,
    ControlObjective,
    ControlTestResult,
    EvidencePackageResponse,
    Finding,
    ManagementResponse,
    RemediationRecommendation,
    RequestedItem,
    TestProcedure,
    WalkthroughStep,
)
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.state import GameState
from lake_effect_ledger.trading.models import EleventhOutcome


class InternalAuditWalkthroughReport(BaseModel):
    report_id: str
    title: str
    outcome: AuditOutcome
    engagement_objective: str
    scope: AuditScope
    transaction_selected: str
    prior_transaction_outcome: EleventhOutcome
    severity_methodology: str
    records_requested: list[RequestedItem]
    records_received_initially: list[str]
    supplemental_responses: list[EvidencePackageResponse]
    actual_chronology: AuditChronology
    control_objectives: list[ControlObjective] = Field(min_length=8, max_length=8)
    procedures_performed: list[TestProcedure] = Field(min_length=8, max_length=8)
    test_results: list[ControlTestResult] = Field(min_length=8, max_length=8)
    exceptions: list[AuditException]
    findings: list[Finding]
    evidence_links: list[str] = Field(min_length=1)
    player_explanations: list[WalkthroughStep] = Field(min_length=14, max_length=14)
    contradictions: list[str]
    management_responses: list[ManagementResponse]
    remediation_plans: list[RemediationRecommendation]
    practiced_learning_objectives: list[str] = Field(min_length=1)
    relationship_effects: list[str]
    simplifying_assumptions: list[str] = Field(min_length=1)
    reconciled_to_preserved_records: bool

    @model_validator(mode="after")
    def validate_report_links(self) -> InternalAuditWalkthroughReport:
        exception_ids = {item.exception_id for item in self.exceptions}
        finding_ids = {item.finding_id for item in self.findings}
        if any(set(item.exception_ids) - exception_ids for item in self.test_results):
            raise ValueError("report test result has an unknown exception")
        if any(set(item.exception_ids) - exception_ids for item in self.findings):
            raise ValueError("report finding has an unknown exception")
        if any(item.finding_id not in finding_ids for item in self.management_responses):
            raise ValueError("report management response has an unknown finding")
        if not self.reconciled_to_preserved_records:
            raise ValueError("audit report must reconcile to preserved transaction records")
        return self


def build_internal_audit_report(
    state: GameState,
    content: ContentBundle,
) -> InternalAuditWalkthroughReport:
    audit = state.no_surprises
    chapter = state.eleventh_contract
    if (
        audit is None
        or chapter is None
        or not audit.completed
        or audit.outcome is None
        or audit.chronology is None
    ):
        raise ValueError("complete No Surprises before building its report")
    initial = audit.package_responses[0]
    supplements = [item for item in audit.package_responses if item.supplemental]
    evidence_links = list(
        dict.fromkeys(
            [
                *(item.stable_record_id for item in audit.evidence_request.requested_items),
                *(
                    evidence_id
                    for result in audit.control_results
                    for evidence_id in result.evidence_record_ids
                ),
                *(
                    evidence_id
                    for finding in audit.findings
                    for evidence_id in finding.evidence_record_ids
                ),
            ]
        )
    )
    objectives = [
        content.lesson(objective_id).title for objective_id in audit.practiced_objective_ids
    ]
    relationships = []
    names = {
        "noah_shah": "Noah",
        "evelyn_marsh": "Evelyn",
        "cal_rourke": "Cal",
        "marisol_vega": "Marisol",
    }
    for person_id, current in audit.relationships.items():
        change = current - audit.beginning_relationships.get(person_id, 0)
        if change:
            direction = "more willing to rely on the player" if change > 0 else "more guarded"
            relationships.append(f"{names.get(person_id, person_id)} became {direction}.")
    if not relationships:
        relationships.append("No audit relationship changed clearly.")
    records_exist = {
        chapter.physical_forecast.forecast_id,
        chapter.market_brief.brief_id,
        chapter.recommendation.recommendation_id,
        chapter.authorization.authorization_id,
        chapter.order.order_id,
        chapter.execution.execution_id,
        chapter.confirmation.confirmation_id,
        chapter.blotter.blotter_id,
        chapter.reconciliation.reconciliation_id,
        *(item.transaction_id for item in state.ledger.entries),
        *(item.record_id for item in state.evidence_log),
        *(item.approval_id for item in chapter.approvals),
        *(chapter.physical_forecast.support_document_ids),
        "analyst_case_file_eleventh_contract",
    }
    if chapter.position.offset_trade:
        records_exist.add(chapter.position.offset_trade.trade_id)
    required_evidence = {
        evidence_id
        for result in audit.control_results
        for evidence_id in result.evidence_record_ids
    }
    reconciled = (
        not (required_evidence - records_exist)
        and all(entry.total_debits == entry.total_credits for entry in state.ledger.entries)
        and chapter.reconciliation.current_status == chapter.blotter.status
    )
    return InternalAuditWalkthroughReport(
        report_id="internal_audit_walkthrough_no_surprises",
        title="Internal Audit Walkthrough Report — No Surprises",
        outcome=audit.outcome,
        engagement_objective=audit.engagement.objective,
        scope=audit.engagement.scope,
        transaction_selected=chapter.scenario_id,
        prior_transaction_outcome=chapter.outcome,
        severity_methodology=(
            "Northstar fictional internal methodology: Advisory, Moderate, High, Critical. "
            "Severity considers authorization, unsupported exposure, timing, evidence, "
            "certification, correction, preservation, repetition, and management involvement; "
            "profit and loss are morally neutral."
        ),
        records_requested=list(audit.evidence_request.requested_items),
        records_received_initially=list(initial.included_request_item_ids),
        supplemental_responses=supplements,
        actual_chronology=audit.chronology,
        control_objectives=list(content.audit_scenario.control_objectives),
        procedures_performed=list(content.audit_scenario.test_procedures),
        test_results=list(audit.control_results),
        exceptions=list(audit.exceptions),
        findings=list(audit.findings),
        evidence_links=evidence_links,
        player_explanations=list(audit.walkthrough_steps),
        contradictions=list(audit.chronology.contradictions),
        management_responses=list(audit.management_responses),
        remediation_plans=list(audit.remediations),
        practiced_learning_objectives=objectives,
        relationship_effects=relationships,
        simplifying_assumptions=list(content.audit_scenario.simplifying_assumptions),
        reconciled_to_preserved_records=reconciled,
    )
