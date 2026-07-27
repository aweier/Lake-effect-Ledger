"""Source-linked rules for the four-day Diligence Room chapter."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from lake_effect_ledger.audit.engine import InternalAuditEngine
from lake_effect_ledger.audit.models import FindingStatus
from lake_effect_ledger.commodity.engine import futures_daily_pnl
from lake_effect_ledger.commodity.models import money
from lake_effect_ledger.diligence.models import (
    AccessDeliveryRecord,
    AnswerPosture,
    CommitteePosture,
    DiligenceChoiceDefinition,
    DiligenceEngagement,
    DiligenceFinding,
    DiligenceOutcome,
    DiligenceQuestion,
    DiligenceRequest,
    DiligenceResponse,
    DiligenceRoomState,
    DiligenceStage,
    DisclosureInconsistency,
    DisclosurePackage,
    DisclosureScope,
    DisclosureStatus,
    ExceptionDescription,
    ExceptionSchedule,
    ExceptionScheduleItem,
    FinalAction,
    InconsistencyAction,
    ManagementRepresentationDraft,
    NumbersPosture,
    PackageVersion,
    RemediationPosture,
    RemediationStatus,
    RepresentationPosture,
    RequestedDisclosureItem,
    ReviewerChoice,
    RiskMetric,
    RiskSchedule,
    ScenarioAnalysisPackage,
    ScenarioPosture,
    ScenarioSensitivity,
    SignificanceAssessment,
    SourceRecordReference,
    StakeholderReaction,
    SupplementalResponse,
    TransactionStatus,
)
from lake_effect_ledger.trading.models import PhysicalVolumeOutcome

if TYPE_CHECKING:
    from lake_effect_ledger.narrative.models import ContentBundle
    from lake_effect_ledger.state import GameState


CHICAGO_TZ = timezone(timedelta(hours=-6), name="CST")


class DiligenceEngine:
    """Project existing records into immutable diligence packages and responses."""

    def __init__(self, content: ContentBundle) -> None:
        self.content = content
        self.scenario = content.diligence_scenario

    def initialize(self, state: GameState) -> DiligenceRoomState:
        if state.diligence_room is not None:
            return state.diligence_room
        audit = state.no_surprises
        chapter = state.eleventh_contract
        if (
            audit is None
            or not audit.completed
            or audit.outcome is None
            or chapter is None
            or not chapter.completed
        ):
            raise ValueError("complete No Surprises before The Diligence Room")
        self._require_financial_sources(state)
        engagement = DiligenceEngagement(
            engagement_id="diligence_majority_acquisition_2028",
            title=self.scenario.title,
            purpose=self.scenario.purpose,
            transaction_structure=self.scenario.transaction_structure,
            buyer_name=self.scenario.buyer_name,
            opened_at=self._at(1, 8, 30),
            target_committee_date=self.scenario.day_dates["day_4"],
            stakeholder_ids=[item.stakeholder_id for item in self.scenario.stakeholders],
        )
        available_ids = self.available_source_record_ids(state)
        requests = [
            self._build_request(
                stakeholder_id="sofia_marin",
                request_id="request_buyer_001",
                item_ids={item.item_id for item in self.scenario.request_specs},
                available_ids=available_ids,
                issued_at=self._at(1, 8, 35),
            ),
            self._build_request(
                stakeholder_id="mara_voss",
                request_id="request_lender_001",
                item_ids={
                    "req_physical_exposure",
                    "req_futures_positions",
                    "req_margin_history",
                    "req_revolver",
                    "req_covenant",
                    "req_audit_report",
                    "req_open_findings",
                    "req_remediation",
                    "req_exceptions",
                },
                available_ids=available_ids,
                issued_at=self._at(1, 8, 45),
            ),
            self._build_request(
                stakeholder_id="ingrid_holtz",
                request_id="request_board_001",
                item_ids={
                    "req_hedge_authorizations",
                    "req_audit_report",
                    "req_open_findings",
                    "req_management_response",
                    "req_remediation",
                    "req_exceptions",
                    "req_communications",
                },
                available_ids=available_ids,
                issued_at=self._at(1, 9, 0),
            ),
        ]
        relationships = {
            "sofia_marin": 0,
            "ingrid_holtz": 0,
            "mara_voss": 0,
            "noah_shah": audit.relationships.get("noah_shah", 0),
            "evelyn_marsh": audit.relationships.get("evelyn_marsh", 0),
            "cal_rourke": audit.relationships.get("cal_rourke", 0),
            "marisol_vega": audit.relationships.get("marisol_vega", 0),
        }
        diligence = DiligenceRoomState(
            scenario_id=self.scenario.id,
            engagement=engagement,
            stakeholders=deepcopy(self.scenario.stakeholders),
            requests=requests,
            source_references=self.build_source_references(state),
            relationships=relationships,
            beginning_relationships=dict(relationships),
            beginning_career_weights={
                tag.value: value for tag, value in state.career_trajectory.tag_weights.items()
            },
            diligence_flags={
                "noah_initially_trusts_package": relationships["noah_shah"] > 0,
                "evelyn_initially_allows_presentation": relationships["evelyn_marsh"] >= 0,
                "cal_applies_pressure": relationships["cal_rourke"] > 0,
            },
        )
        state.diligence_room = diligence
        state.current_date = self.scenario.day_dates["day_1"]
        state.record(
            phase="system",
            event_type="diligence_started",
            source_id=engagement.engagement_id,
            message=("Great Lakes Infrastructure Partners opened majority-acquisition diligence."),
            changes={"transaction_structure": engagement.transaction_structure},
        )
        return diligence

    def advance_request_list(self, state: GameState) -> None:
        diligence = self._diligence(state)
        if diligence.current_stage == DiligenceStage.REQUEST_LIST:
            diligence.current_stage = DiligenceStage.INITIAL_PACKAGE
            state.record(
                phase="system",
                event_type="diligence_request_list_prepared",
                source_id=diligence.engagement.engagement_id,
                message="Buyer, lender, and board request lists were resolved to source records.",
                changes={"request_count": len(diligence.requests)},
            )

    def apply_choice(
        self,
        state: GameState,
        scene_id: str,
        choice_id: str,
    ) -> DiligenceChoiceDefinition:
        diligence = self._diligence(state)
        scene = self.content.diligence_scene(scene_id)
        if choice_id in diligence.decisions or choice_id in state.decisions:
            raise ValueError(f"diligence choice has already been applied: {choice_id}")
        if any(choice.id in diligence.decisions for choice in scene.choices):
            raise ValueError(f"diligence scene already has a durable choice: {scene_id}")
        try:
            choice = next(item for item in scene.choices if item.id == choice_id)
        except StopIteration as error:
            raise ValueError(f"unknown diligence choice {choice_id} for {scene_id}") from error
        protected = self._protected_records(state)
        diligence.decisions.append(choice.id)
        state.decisions.append(choice.id)
        for objective_id in choice.learning_objective_ids:
            if objective_id not in diligence.practiced_objective_ids:
                diligence.practiced_objective_ids.append(objective_id)
            if objective_id not in state.learning_objectives:
                state.learning_objectives.append(objective_id)
        effect = choice.effect
        for field in (
            "disclosure_scope",
            "exception_description",
            "reviewer_choice",
            "numbers_posture",
            "scenario_posture",
            "remediation_posture",
            "buyer_answer_posture",
            "lender_answer_posture",
            "representation_posture",
            "inconsistency_action",
            "committee_posture",
            "final_action",
        ):
            value = getattr(effect, field)
            if value is not None:
                setattr(diligence, field, value)
        diligence.diligence_flags.update(effect.flags)
        for person_id, amount in effect.relationship_deltas.items():
            current = diligence.relationships.get(person_id, 0)
            diligence.relationships[person_id] = max(-10, min(10, current + amount))
        for tag, amount in effect.trajectory_deltas.items():
            state.career_trajectory.record(choice.id, tag, amount)
        state.record(
            phase="decision",
            event_type="diligence_decision",
            source_id=choice.id,
            message=choice.text,
            changes={"scene_id": scene_id},
        )
        self._assert_records_unchanged(state, protected)
        return choice

    def prepare_initial_packages(self, state: GameState) -> list[DisclosurePackage]:
        diligence = self._diligence(state)
        if diligence.packages:
            return diligence.packages
        if diligence.current_stage != DiligenceStage.INITIAL_PACKAGE:
            raise ValueError("initial packages are not the current diligence stage")
        if not all(
            (
                diligence.disclosure_scope,
                diligence.exception_description,
                diligence.reviewer_choice,
            )
        ):
            raise ValueError("complete the Day 1 package decisions first")
        canonical = self.canonical_facts(state)
        package_specs = [
            ("package_buyer", "request_buyer_001", "sofia_marin", self._at(1, 15, 10)),
            ("package_lender", "request_lender_001", "mara_voss", self._at(1, 15, 30)),
            ("package_board", "request_board_001", "ingrid_holtz", self._at(1, 16, 0)),
        ]
        packages: list[DisclosurePackage] = []
        deliveries: list[AccessDeliveryRecord] = []
        for package_id, request_id, stakeholder_id, delivered_at in package_specs:
            request = next(item for item in diligence.requests if item.request_id == request_id)
            included, omitted = self._initial_item_selection(diligence, request, stakeholder_id)
            facts = self._package_facts(
                state,
                stakeholder_id=stakeholder_id,
                canonical=canonical,
            )
            reviewed_by = self._reviewers(diligence, stakeholder_id)
            source_ids = list(
                dict.fromkeys(
                    source_id for item in included for source_id in item.source_record_ids
                )
            )
            version = PackageVersion(
                package_id=package_id,
                version=1,
                intended_stakeholder_id=stakeholder_id,
                included_item_ids=[item.item_id for item in included],
                omitted_requested_item_ids=[item.item_id for item in omitted],
                source_record_ids=source_ids,
                fact_values=facts,
                created_at=delivered_at - timedelta(minutes=20),
                delivered_at=delivered_at,
                prepared_by_id="player",
                reviewed_by_ids=reviewed_by,
            )
            packages.append(
                DisclosurePackage(
                    package_id=package_id,
                    request_id=request_id,
                    intended_stakeholder_id=stakeholder_id,
                    versions=[version],
                )
            )
            deliveries.append(
                AccessDeliveryRecord(
                    delivery_id=f"delivery_{package_id}_v1",
                    package_id=package_id,
                    package_version=1,
                    stakeholder_id=stakeholder_id,
                    delivered_at=delivered_at,
                    acknowledged_at=delivered_at + timedelta(minutes=5),
                    delivery_method=(
                        "structured_room"
                        if stakeholder_id == "sofia_marin"
                        else "committee_packet"
                        if stakeholder_id == "ingrid_holtz"
                        else "secure_email"
                    ),
                )
            )
            for item in request.items:
                if item.item_id in version.included_item_ids:
                    item.status = DisclosureStatus.INCLUDED
                elif item.available:
                    item.status = DisclosureStatus.OMITTED
                elif item.relevant:
                    item.status = DisclosureStatus.UNABLE_TO_SUBSTANTIATE
                else:
                    item.status = DisclosureStatus.NOT_APPLICABLE
        diligence.packages = packages
        diligence.deliveries = deliveries
        diligence.inconsistencies = self.detect_inconsistencies(
            state,
            detected_at=self._at(1, 16, 15),
        )
        diligence.current_stage = DiligenceStage.RISK_SCHEDULE
        state.current_date = self.scenario.day_dates["day_2"]
        state.record(
            phase="system",
            event_type="diligence_initial_packages_delivered",
            source_id=diligence.engagement.engagement_id,
            message="Immutable buyer, lender, and board package version 1 records were delivered.",
            changes={"package_count": len(packages)},
        )
        return packages

    def prepare_risk_schedule(
        self,
        state: GameState,
    ) -> tuple[RiskSchedule, ScenarioAnalysisPackage]:
        diligence = self._diligence(state)
        if diligence.risk_schedule is not None and diligence.scenario_analysis is not None:
            return diligence.risk_schedule, diligence.scenario_analysis
        if diligence.current_stage != DiligenceStage.RISK_SCHEDULE:
            raise ValueError("risk schedule is not the current diligence stage")
        if not all(
            (
                diligence.numbers_posture,
                diligence.scenario_posture,
                diligence.remediation_posture,
            )
        ):
            raise ValueError("complete the Day 2 schedule decisions first")
        protected = self._protected_records(state)
        risk_schedule = self.build_risk_schedule(state)
        analysis = self.build_scenario_analysis(state)
        diligence.risk_schedule = risk_schedule
        diligence.scenario_analysis = analysis
        self._append_analysis_package_version(state)
        diligence.inconsistencies = self.detect_inconsistencies(
            state,
            preserve_existing=True,
            detected_at=self._at(2, 14, 0),
        )
        diligence.current_stage = DiligenceStage.Q_AND_A
        state.current_date = self.scenario.day_dates["day_3"]
        self._assert_records_unchanged(state, protected)
        state.record(
            phase="system",
            event_type="diligence_risk_schedule_prepared",
            source_id=risk_schedule.schedule_id,
            message=(
                "Source-linked commodity, liquidity, control, and sensitivity "
                "schedules were prepared."
            ),
            changes={
                "scenario_count": len(analysis.rows),
                "inconsistency_count": len(diligence.inconsistencies),
            },
        )
        return risk_schedule, analysis

    def prepare_q_and_a(self, state: GameState) -> list[DiligenceResponse]:
        diligence = self._diligence(state)
        if diligence.responses:
            return diligence.responses
        if diligence.current_stage != DiligenceStage.Q_AND_A:
            raise ValueError("Q&A is not the current diligence stage")
        if not all(
            (
                diligence.buyer_answer_posture,
                diligence.lender_answer_posture,
                diligence.representation_posture,
            )
        ):
            raise ValueError("complete the Day 3 response decisions first")
        diligence.questions = self._questions()
        responses: list[DiligenceResponse] = []
        for index, question in enumerate(diligence.questions, start=1):
            if question.stakeholder_id == "sofia_marin":
                posture = diligence.buyer_answer_posture
            elif question.stakeholder_id == "mara_voss":
                posture = diligence.lender_answer_posture
            else:
                posture = (
                    AnswerPosture.COMPLETE
                    if diligence.representation_posture
                    != RepresentationPosture.PREFERRED_INCOMPLETE
                    else AnswerPosture.NARROW
                )
            source_ids = self._question_source_ids(question.question_id, state)
            complete = posture in {AnswerPosture.COMPLETE, AnswerPosture.REFER_TO_OWNER}
            responses.append(
                DiligenceResponse(
                    response_id=f"response_{index:02d}",
                    question_id=question.question_id,
                    responded_at=question.asked_at + timedelta(minutes=20 + index),
                    responder_id="player",
                    posture=posture,
                    text=self._response_text(question.question_id, posture, state),
                    source_record_ids=source_ids,
                    complete=complete,
                    acknowledges_uncertainty=posture == AnswerPosture.ACKNOWLEDGE_UNCERTAINTY,
                )
            )
        diligence.responses = responses
        diligence.management_representations = [self._management_representation(state, version=1)]
        diligence.current_stage = DiligenceStage.SUPPLEMENTAL
        state.current_date = self.scenario.day_dates["day_4"]
        state.record(
            phase="system",
            event_type="diligence_q_and_a_recorded",
            source_id=diligence.engagement.engagement_id,
            message="All buyer, lender, and board questions received timestamped responses.",
            changes={"response_count": len(responses)},
        )
        return responses

    def prepare_supplement(self, state: GameState) -> None:
        diligence = self._diligence(state)
        if diligence.current_stage != DiligenceStage.SUPPLEMENTAL:
            if diligence.current_stage in {
                DiligenceStage.BEFORE_COMMITTEE,
                DiligenceStage.COMPLETE,
            }:
                return
            raise ValueError("supplement is not the current diligence stage")
        if diligence.inconsistency_action is None:
            raise ValueError("select an inconsistency action before supplementing")
        protected = self._protected_records(state)
        if diligence.inconsistency_action == InconsistencyAction.CORRECT:
            self._correct_conflicting_packages(state)
        elif diligence.inconsistency_action == InconsistencyAction.SUPPLEMENT:
            self._supplement_limited_packages(state)
        incomplete = next((item for item in diligence.responses if not item.complete), None)
        if incomplete is not None:
            supplement = SupplementalResponse(
                supplemental_response_id="supplemental_response_001",
                original_response_id=incomplete.response_id,
                provided_at=self._at(4, 9, 45),
                text=(
                    "The source chronology, authorization quantity, liquidity schedule, and "
                    "remediation status are supplied without replacing the original response."
                ),
                source_record_ids=[
                    "auth_live_week_ten_short",
                    "reconciliation_eleventh_contract",
                    "internal_audit_walkthrough_no_surprises",
                    "episode_01_two_oclock_call",
                ],
            )
            diligence.supplemental_responses.append(supplement)
        diligence.inconsistencies = self.detect_inconsistencies(
            state,
            preserve_existing=True,
        )
        diligence.findings = self._build_findings(state)
        diligence.current_stage = DiligenceStage.BEFORE_COMMITTEE
        self._assert_records_unchanged(state, protected)
        state.record(
            phase="system",
            event_type="diligence_supplement_prepared",
            source_id=diligence.engagement.engagement_id,
            message="Package and Q&A supplements were preserved as later records.",
            changes={
                "supplemental_responses": len(diligence.supplemental_responses),
                "package_versions": sum(len(item.versions) for item in diligence.packages),
            },
        )

    def complete(self, state: GameState) -> DiligenceOutcome:
        diligence = self._diligence(state)
        if diligence.current_stage != DiligenceStage.BEFORE_COMMITTEE:
            raise ValueError("complete the supplement stage before the committee meeting")
        if diligence.committee_posture is None or diligence.final_action is None:
            raise ValueError("complete the committee decisions first")
        if diligence.final_action == FinalAction.CORRECT_DISCLOSURE:
            self._correct_conflicting_packages(state)
        elif diligence.final_action == FinalAction.ESCALATE_REPRESENTATION:
            diligence.diligence_flags["management_representation_escalated"] = True
            if diligence.management_representations:
                diligence.management_representations[-1].escalated = True
        diligence.inconsistencies = self.detect_inconsistencies(
            state,
            preserve_existing=True,
        )
        diligence.findings = self._build_findings(state)
        outcome = self._derive_outcome(state)
        transaction_status = self._transaction_status(outcome)
        diligence.outcome = outcome
        diligence.transaction_status = transaction_status
        diligence.stakeholder_reactions = self._stakeholder_reactions(state, outcome)
        diligence.current_stage = DiligenceStage.COMPLETE
        diligence.completed = True
        state.current_date = self.scenario.day_dates["day_4"]
        self.assert_source_reconciliation(state)
        state.record(
            phase="system",
            event_type="diligence_completed",
            source_id=diligence.engagement.engagement_id,
            message=f"Diligence Room outcome: {outcome.value}.",
            changes={
                "outcome": outcome.value,
                "transaction_status": transaction_status.value,
            },
        )
        return outcome

    def available_source_record_ids(self, state: GameState) -> set[str]:
        chapter = self._chapter(state)
        audit = self._audit(state)
        treasury = state.treasury
        book = state.hedge_book
        audit_records = InternalAuditEngine(self.content).available_records(state)
        available = {
            "northstar_commodity_risk_policy_v1",
            chapter.physical_forecast.forecast_id,
            chapter.market_brief.brief_id,
            chapter.recommendation.recommendation_id,
            chapter.order.order_id,
            chapter.execution.execution_id,
            chapter.confirmation.confirmation_id,
            chapter.blotter.blotter_id,
            chapter.authorization.authorization_id,
            chapter.reconciliation.reconciliation_id,
            "analyst_case_file_eleventh_contract",
            audit.engagement.engagement_id,
            audit.evidence_request.request_id,
            "internal_audit_walkthrough_no_surprises",
            *(record_id for record_id, record in audit_records.items() if record.available),
            *(item.response_id for item in audit.package_responses),
            *(item.step_id for item in audit.walkthrough_steps),
            *(item.result_id for item in audit.control_results),
            *(item.exception_id for item in audit.exceptions),
            *(item.finding_id for item in audit.findings),
            *(item.response_id for item in audit.management_responses),
            *(item.remediation_id for item in audit.remediations),
            *(item.transaction_id for item in state.ledger.entries),
        }
        if audit.chronology is not None:
            available.add(audit.chronology.chronology_id)
            available.update(item.record_id for item in audit.chronology.entries)
        if book is not None and book.completed:
            available.add(book.scenario_id)
            available.update(book.journal_transaction_ids)
        if treasury is not None and treasury.completed:
            available.update({treasury.scenario_id, treasury.facility.facility_id})
            available.update(treasury.journal_transaction_ids)
        available.update(item.record_id for item in state.evidence_log)
        return available

    def build_source_references(self, state: GameState) -> list[SourceRecordReference]:
        chapter = self._chapter(state)
        audit = self._audit(state)
        treasury = state.treasury
        book = state.hedge_book
        if treasury is None or treasury.covenant_result is None or book is None:
            raise ValueError("completed commodity and treasury records are required")
        basis_effect = self._eleventh_basis_effect(state)
        remediation = self.actual_remediation_status(state)
        references = [
            self._reference(
                "ref_policy",
                "northstar_commodity_risk_policy_v1",
                "PolicyReference",
                "commodity_policy",
                "Policy requires documented quantity authorization and reconciliation.",
            ),
            self._reference(
                "ref_supported_volume",
                chapter.physical_forecast.forecast_id,
                "PhysicalForecastRecord",
                "supported_volume_trade_date",
                str(chapter.physical_forecast.supported_volume_mmbtu),
            ),
            self._reference(
                "ref_possible_volume",
                chapter.physical_forecast.forecast_id,
                "PhysicalForecastRecord",
                "possible_volume_trade_date",
                str(chapter.physical_forecast.possible_additional_volume_mmbtu),
            ),
            self._reference(
                "ref_later_supported_volume",
                chapter.physical_forecast.forecast_id,
                "PhysicalForecastRecord",
                "eventual_supported_volume",
                str(chapter.physical_forecast.eventual_supported_volume_mmbtu),
                as_of=chapter.physical_forecast.outcome_resolved_at,
            ),
            self._reference(
                "ref_authorized",
                chapter.authorization.authorization_id,
                "TradeAuthorization",
                "authorized_contracts",
                str(chapter.authorization.maximum_quantity),
                as_of=chapter.authorization.approved_at,
            ),
            self._reference(
                "ref_executed",
                chapter.blotter.blotter_id,
                "TradeBlotterEntry",
                "executed_contracts",
                str(chapter.execution.quantity),
                as_of=chapter.execution.fill_timestamp,
            ),
            self._reference(
                "ref_current_contracts",
                chapter.blotter.blotter_id,
                "TradeBlotterEntry",
                "current_contracts",
                str(chapter.position.open_contracts),
            ),
            self._reference(
                "ref_initial_ratio",
                chapter.blotter.blotter_id,
                "TradeBlotterEntry",
                "initial_hedge_ratio",
                str(chapter.position.initial_hedge_ratio),
            ),
            self._reference(
                "ref_current_ratio",
                chapter.blotter.blotter_id,
                "TradeBlotterEntry",
                "current_hedge_ratio",
                str(chapter.position.current_hedge_ratio),
            ),
            self._reference(
                "ref_futures_pnl",
                chapter.blotter.blotter_id,
                "TradeBlotterEntry",
                "futures_pnl",
                str(chapter.position.cumulative_pnl),
            ),
            self._reference(
                "ref_physical_pnl",
                chapter.physical_forecast.forecast_id,
                "PhysicalForecastRecord",
                "physical_economic_pnl",
                str(chapter.physical_economic_pnl),
            ),
            self._reference(
                "ref_basis_effect",
                chapter.physical_forecast.forecast_id,
                "PhysicalForecastRecord",
                "basis_effect",
                str(basis_effect),
                calculation="(final Chicago basis - initial Chicago basis) × supported volume",
            ),
            self._reference(
                "ref_margin_history",
                book.scenario_id,
                "HedgeBookState",
                "historical_variation_margin",
                str(book.margin.total_variation_margin),
            ),
            self._reference(
                "ref_operating_cash",
                treasury.scenario_id,
                "TreasuryState",
                "operating_cash",
                str(state.corporate_cash),
            ),
            self._reference(
                "ref_revolver",
                treasury.facility.facility_id,
                "RevolvingCreditState",
                "revolver_outstanding",
                str(treasury.facility.outstanding),
            ),
            self._reference(
                "ref_undrawn",
                treasury.facility.facility_id,
                "RevolvingCreditState",
                "undrawn_availability",
                str(treasury.facility.undrawn_availability),
                calculation="commitment - outstanding",
            ),
            self._reference(
                "ref_covenant",
                treasury.scenario_id,
                "CovenantResult",
                "covenant_headroom",
                str(
                    money(
                        treasury.covenant_result.available_liquidity
                        - treasury.covenant_result.minimum_required
                    )
                ),
                as_of=treasury.covenant_result.tested_at,
                calculation="available liquidity - fictional minimum",
            ),
            self._reference(
                "ref_audit_report",
                "internal_audit_walkthrough_no_surprises",
                "InternalAuditWalkthroughReport",
                "audit_outcome",
                audit.outcome.value,
            ),
            self._reference(
                "ref_remediation_status",
                audit.engagement.engagement_id,
                "ManagementResponse",
                "remediation_status",
                remediation.value,
            ),
            self._reference(
                "ref_exception",
                chapter.reconciliation.reconciliation_id,
                "TradeReconciliationRecord",
                "authorization_exception",
                (
                    f"{chapter.execution.quantity} executed against "
                    f"{chapter.authorization.maximum_quantity} authorized"
                ),
            ),
            self._reference(
                "ref_case_file",
                "analyst_case_file_eleventh_contract",
                "AnalystCaseFile",
                "eleventh_outcome",
                chapter.outcome.value,
            ),
        ]
        return references

    def canonical_facts(self, state: GameState) -> dict[str, str]:
        return {item.fact_key: item.value_text for item in self.build_source_references(state)} | {
            "margin_call_disclosed": "yes",
            "audit_report_included": "yes",
        }

    def actual_remediation_status(self, state: GameState) -> RemediationStatus:
        audit = self._audit(state)
        if any(
            response.status == FindingStatus.RISK_ACCEPTED
            for response in audit.management_responses
        ):
            return RemediationStatus.RISK_ACCEPTED
        return RemediationStatus.APPROVED

    def build_risk_schedule(self, state: GameState) -> RiskSchedule:
        chapter = self._chapter(state)
        audit = self._audit(state)
        treasury = state.treasury
        book = state.hedge_book
        if treasury is None or treasury.covenant_result is None or book is None:
            raise ValueError("completed financial records are required")
        offset_contracts = 1 if chapter.position.offset_trade is not None else 0
        headroom = money(
            treasury.covenant_result.available_liquidity - treasury.covenant_result.minimum_required
        )
        protected_obligations = sum(
            (item.amount for item in treasury.obligations if item.protected),
            Decimal("0"),
        )
        metrics = [
            self._metric(
                "supported_volume",
                "Supported physical volume at trade date",
                chapter.physical_forecast.supported_volume_mmbtu,
                "MMBtu",
                [chapter.physical_forecast.forecast_id],
            ),
            self._metric(
                "possible_volume",
                "Possible, unsupported volume at trade date",
                chapter.physical_forecast.possible_additional_volume_mmbtu,
                "MMBtu",
                [chapter.physical_forecast.forecast_id],
            ),
            self._metric(
                "eventual_supported_volume",
                "Eventual supported volume",
                chapter.physical_forecast.eventual_supported_volume_mmbtu,
                "MMBtu",
                [chapter.physical_forecast.forecast_id],
            ),
            self._metric(
                "authorized_contracts",
                "Authorized futures quantity",
                Decimal(chapter.authorization.maximum_quantity),
                "contracts",
                [chapter.authorization.authorization_id],
            ),
            self._metric(
                "executed_contracts",
                "Executed futures quantity",
                Decimal(chapter.execution.quantity),
                "contracts",
                [chapter.execution.execution_id],
            ),
            self._metric(
                "corrective_offset",
                "Corrective offset",
                Decimal(offset_contracts),
                "contracts",
                [
                    chapter.position.offset_trade.trade_id
                    if chapter.position.offset_trade
                    else chapter.reconciliation.reconciliation_id
                ],
            ),
            self._metric(
                "initial_hedge_ratio",
                "Initial supported-volume hedge ratio",
                chapter.position.initial_hedge_ratio,
                "ratio",
                [chapter.blotter.blotter_id],
            ),
            self._metric(
                "current_hedge_ratio",
                "Current hedge ratio",
                chapter.position.current_hedge_ratio,
                "ratio",
                [chapter.blotter.blotter_id],
            ),
            self._metric(
                "futures_pnl",
                "Eleventh Contract futures P&L",
                chapter.position.cumulative_pnl,
                "USD",
                [chapter.blotter.blotter_id],
            ),
            self._metric(
                "physical_pnl",
                "Physical economic P&L",
                chapter.physical_economic_pnl,
                "USD",
                [chapter.physical_forecast.forecast_id],
            ),
            self._metric(
                "basis_effect",
                "Chicago basis effect",
                self._eleventh_basis_effect(state),
                "USD",
                [chapter.physical_forecast.forecast_id],
            ),
            self._metric(
                "margin_cash",
                "Historical variation-margin movement",
                book.margin.total_variation_margin,
                "USD",
                [book.scenario_id],
            ),
            self._metric(
                "operating_cash",
                "Operating cash",
                state.corporate_cash,
                "USD",
                [treasury.scenario_id],
            ),
            self._metric(
                "revolver",
                "Revolver borrowing",
                treasury.facility.outstanding,
                "USD",
                [treasury.facility.facility_id],
            ),
            self._metric(
                "undrawn",
                "Undrawn revolver availability",
                treasury.facility.undrawn_availability,
                "USD",
                [treasury.facility.facility_id],
                "commitment - outstanding",
            ),
            self._metric(
                "interest",
                "Accrued revolver interest",
                treasury.facility.accrued_interest,
                "USD",
                [treasury.facility.facility_id],
            ),
            self._metric(
                "protected_obligations",
                "Protected scheduled obligations",
                protected_obligations,
                "USD",
                [treasury.scenario_id],
            ),
            self._metric(
                "covenant_headroom",
                "Fictional available-liquidity covenant headroom",
                headroom,
                "USD",
                [treasury.scenario_id],
                "available liquidity - minimum required",
            ),
            RiskMetric(
                metric_id="audit_findings",
                label="No Surprises findings",
                value_text=str(len(audit.findings)),
                numeric_value=Decimal(len(audit.findings)),
                unit="findings",
                source_record_ids=["internal_audit_walkthrough_no_surprises"],
            ),
            RiskMetric(
                metric_id="remediation_status",
                label="Remediation status",
                value_text=self.actual_remediation_status(state).value,
                source_record_ids=[audit.engagement.engagement_id],
            ),
        ]
        exception = ExceptionScheduleItem(
            exception_id="exception_eleventh_contract",
            title="Eleven contracts executed against ten authorized",
            description=(
                "The external execution and confirmation show eleven contracts. "
                "The contemporaneous authorization permits ten."
            ),
            source_record_ids=[
                chapter.authorization.authorization_id,
                chapter.execution.execution_id,
                chapter.confirmation.confirmation_id,
                chapter.reconciliation.reconciliation_id,
            ],
            corrected=chapter.position.offset_trade is not None,
            unresolved=chapter.position.offset_trade is None,
            significance_context=[
                "Authorization",
                "Inaccurate certification or delayed notification where applicable",
                "Liquidity-control interaction",
                "Potential recurrence",
                "Management and record credibility",
            ],
        )
        amount = abs(chapter.position.extra_contract_pnl)
        qualitative = list(exception.significance_context)
        significance = SignificanceAssessment(
            assessment_id="significance_eleventh_contract",
            review_threshold=self.scenario.fictional_review_threshold,
            amount_considered=amount,
            exceeds_review_threshold=amount >= self.scenario.fictional_review_threshold,
            qualitative_factors=qualitative,
            significant_for_diligence=bool(qualitative)
            or amount >= self.scenario.fictional_review_threshold,
            caveat=(
                "Northstar's $50,000 threshold is a fictional diligence review threshold, "
                "not a universal accounting-materiality rule, legal conclusion, or "
                "substitute for professional judgment."
            ),
        )
        return RiskSchedule(
            schedule_id="risk_schedule_diligence_room",
            as_of=self._at(2, 11, 30),
            metrics=metrics,
            exception_schedule=ExceptionSchedule(
                schedule_id="exception_schedule_diligence_room",
                as_of=self._at(2, 11, 30),
                items=[exception],
            ),
            significance=significance,
        )

    def build_scenario_analysis(self, state: GameState) -> ScenarioAnalysisPackage:
        chapter = self._chapter(state)
        treasury = state.treasury
        if treasury is None or treasury.covenant_result is None:
            raise ValueError("completed treasury state is required")
        protected = self._protected_records(state)
        quantity = chapter.physical_forecast.eventual_supported_volume_mmbtu
        contracts = chapter.position.open_contracts
        contract_size = chapter.position.contract_size_mmbtu
        current_headroom = money(
            treasury.covenant_result.available_liquidity - treasury.covenant_result.minimum_required
        )
        rows: list[ScenarioSensitivity] = []
        reference_price = Decimal("5.000")
        for definition in self.scenario.sensitivities:
            henry_component = money(definition.henry_hub_change * quantity)
            basis_effect = money(definition.chicago_basis_change * quantity)
            physical = money(henry_component + basis_effect)
            futures = futures_daily_pnl(
                side=chapter.position.side,
                previous_settlement=reference_price,
                current_settlement=reference_price + definition.henry_hub_change,
                contract_size_mmbtu=contract_size,
                contracts=contracts,
            )
            variation = futures
            resulting_headroom = money(current_headroom + min(variation, Decimal("0")))
            rows.append(
                ScenarioSensitivity(
                    scenario_id=definition.scenario_id,
                    label=definition.label,
                    henry_hub_change=definition.henry_hub_change,
                    chicago_basis_change=definition.chicago_basis_change,
                    physical_economic_effect=physical,
                    futures_effect=futures,
                    basis_effect=basis_effect,
                    net_economic_effect=money(physical + futures),
                    estimated_variation_margin_cash_movement=variation,
                    resulting_liquidity_headroom=resulting_headroom,
                )
            )
        package = ScenarioAnalysisPackage(
            analysis_id="scenario_analysis_diligence_room",
            prepared_at=self._at(2, 12, 0),
            source_record_ids=[
                chapter.physical_forecast.forecast_id,
                chapter.blotter.blotter_id,
                treasury.scenario_id,
                treasury.facility.facility_id,
            ],
            rows=rows,
            assumptions=list(self.scenario.simplifying_assumptions),
        )
        self._assert_records_unchanged(state, protected)
        return package

    def detect_inconsistencies(
        self,
        state: GameState,
        *,
        preserve_existing: bool = False,
        detected_at: datetime | None = None,
    ) -> list[DisclosureInconsistency]:
        diligence = self._diligence(state)
        existing = {
            (
                item.fact_key,
                item.first_package_id,
                item.first_version,
                item.second_package_id,
                item.second_version,
            ): item
            for item in diligence.inconsistencies
        }
        detected: list[DisclosureInconsistency] = (
            list(existing.values()) if preserve_existing else []
        )
        latest = [package.versions[-1] for package in diligence.packages]
        keys = (
            set.intersection(*(set(version.fact_values) for version in latest)) if latest else set()
        )
        counter = len(detected)
        for fact_key in sorted(keys):
            for index, first in enumerate(latest):
                for second in latest[index + 1 :]:
                    first_value = first.fact_values[fact_key]
                    second_value = second.fact_values[fact_key]
                    identity = (
                        fact_key,
                        first.package_id,
                        first.version,
                        second.package_id,
                        second.version,
                    )
                    if first_value == second_value or identity in existing:
                        continue
                    counter += 1
                    detected.append(
                        DisclosureInconsistency(
                            inconsistency_id=f"inconsistency_{counter:02d}",
                            fact_key=fact_key,
                            first_package_id=first.package_id,
                            first_version=first.version,
                            first_value=first_value,
                            second_package_id=second.package_id,
                            second_version=second.version,
                            second_value=second_value,
                            detected_at=detected_at or self._at(3, 14, 15),
                        )
                    )
        return detected

    def assert_source_reconciliation(self, state: GameState) -> None:
        diligence = self._diligence(state)
        if diligence.risk_schedule is None or diligence.scenario_analysis is None:
            raise ValueError("diligence schedules are incomplete")
        rebuilt_risk = self.build_risk_schedule(state)
        rebuilt_scenarios = self.build_scenario_analysis(state)
        if diligence.risk_schedule != rebuilt_risk:
            raise RuntimeError("diligence risk schedule no longer agrees with source records")
        if diligence.scenario_analysis != rebuilt_scenarios:
            raise RuntimeError("diligence sensitivity table no longer reconciles")
        known = self.available_source_record_ids(state) | {
            reference.record_id for reference in diligence.source_references
        }
        linked_source_sets: list[list[str]] = []
        for package in diligence.packages:
            for version in package.versions:
                linked_source_sets.append(version.source_record_ids)
        linked_source_sets.extend(
            item.source_record_ids for item in diligence.responses if item.source_record_ids
        )
        linked_source_sets.extend(
            item.source_record_ids for item in diligence.supplemental_responses
        )
        linked_source_sets.extend(
            item.source_record_ids for item in diligence.management_representations
        )
        linked_source_sets.extend(item.source_record_ids for item in diligence.findings)
        linked_source_sets.extend(
            item.source_record_ids for item in diligence.risk_schedule.metrics
        )
        linked_source_sets.extend(
            item.source_record_ids for item in diligence.risk_schedule.exception_schedule.items
        )
        linked_source_sets.append(diligence.scenario_analysis.source_record_ids)
        for source_ids in linked_source_sets:
            unknown = set(source_ids) - known
            if unknown:
                raise RuntimeError(
                    f"diligence record contains unknown source record(s): "
                    f"{', '.join(sorted(unknown))}"
                )
        canonical = self.canonical_facts(state)
        for package in diligence.packages:
            for version in package.versions:
                for fact_key, value in version.fact_values.items():
                    if fact_key not in canonical or value == canonical[fact_key]:
                        continue
                    covered = any(
                        item.fact_key == fact_key
                        and (
                            (
                                item.first_package_id == package.package_id
                                and item.first_version == version.version
                            )
                            or (
                                item.second_package_id == package.package_id
                                and item.second_version == version.version
                            )
                        )
                        for item in diligence.inconsistencies
                    )
                    if not covered:
                        raise RuntimeError(
                            "package fact disagrees with its source without a typed "
                            f"inconsistency: {package.package_id} v{version.version} "
                            f"{fact_key}"
                        )

    def _build_request(
        self,
        *,
        stakeholder_id: str,
        request_id: str,
        item_ids: set[str],
        available_ids: set[str],
        issued_at: datetime,
    ) -> DiligenceRequest:
        items = []
        for spec in self.scenario.request_specs:
            if spec.item_id not in item_ids:
                continue
            available = (
                bool(spec.source_record_ids) and set(spec.source_record_ids) <= available_ids
            )
            items.append(
                RequestedDisclosureItem(
                    item_id=spec.item_id,
                    label=spec.label,
                    source_record_ids=list(spec.source_record_ids),
                    relevant=spec.relevant,
                    available=available,
                    status=(
                        DisclosureStatus.AVAILABLE
                        if available
                        else DisclosureStatus.UNABLE_TO_SUBSTANTIATE
                    ),
                )
            )
        return DiligenceRequest(
            request_id=request_id,
            engagement_id="diligence_majority_acquisition_2028",
            stakeholder_id=stakeholder_id,
            issued_at=issued_at,
            due_at=self._at(1, 16, 30),
            items=items,
        )

    def _initial_item_selection(
        self,
        diligence: DiligenceRoomState,
        request: DiligenceRequest,
        stakeholder_id: str,
    ) -> tuple[list[RequestedDisclosureItem], list[RequestedDisclosureItem]]:
        available = [item for item in request.items if item.available and item.relevant]
        if diligence.disclosure_scope == DisclosureScope.LIMITED:
            sensitive = {
                "req_audit_report",
                "req_open_findings",
                "req_management_response",
                "req_remediation",
                "req_exceptions",
                "req_communications",
            }
            included = [item for item in available if item.item_id not in sensitive]
        else:
            included = available
        if (
            stakeholder_id == "mara_voss"
            and diligence.numbers_posture == NumbersPosture.OMIT_MARGIN_CALL
        ):
            included = [item for item in included if item.item_id != "req_margin_history"]
        included_ids = {item.item_id for item in included}
        omitted = [item for item in request.items if item.item_id not in included_ids]
        return included, omitted

    def _reviewers(
        self,
        diligence: DiligenceRoomState,
        stakeholder_id: str,
    ) -> list[str]:
        if diligence.reviewer_choice == ReviewerChoice.CAL:
            return ["cal_rourke"]
        if diligence.reviewer_choice == ReviewerChoice.SELF:
            return []
        if diligence.reviewer_choice == ReviewerChoice.MARISOL:
            if stakeholder_id in {"sofia_marin", "mara_voss"}:
                return ["marisol_vega", "evelyn_marsh"]
            return ["evelyn_marsh", "noah_shah"]
        if stakeholder_id == "sofia_marin":
            return ["evelyn_marsh", "noah_shah"]
        if stakeholder_id == "mara_voss":
            return ["evelyn_marsh", "june_halvorsen"]
        return ["evelyn_marsh", "noah_shah"]

    def _package_facts(
        self,
        state: GameState,
        *,
        stakeholder_id: str,
        canonical: dict[str, str],
    ) -> dict[str, str]:
        diligence = self._diligence(state)
        facts = {
            key: canonical[key]
            for key in (
                "supported_volume_trade_date",
                "eventual_supported_volume",
                "authorized_contracts",
                "executed_contracts",
                "remediation_status",
                "audit_outcome",
                "covenant_headroom",
                "margin_call_disclosed",
            )
        }
        if stakeholder_id == "sofia_marin":
            if diligence.exception_description == ExceptionDescription.AUTHORIZED_ELEVEN:
                facts["authorized_contracts"] = "11"
            if diligence.numbers_posture == NumbersPosture.LATER_SUPPORT_AS_TRADE_DATE:
                facts["supported_volume_trade_date"] = canonical["eventual_supported_volume"]
            if diligence.remediation_posture == RemediationPosture.IMPLEMENTED_CLAIM:
                facts["remediation_status"] = RemediationStatus.IMPLEMENTED.value
        elif stakeholder_id == "mara_voss":
            if diligence.numbers_posture == NumbersPosture.OMIT_MARGIN_CALL:
                facts["margin_call_disclosed"] = "no"
            if diligence.remediation_posture == RemediationPosture.IMPLEMENTED_CLAIM:
                facts["remediation_status"] = RemediationStatus.IMPLEMENTED.value
        return facts

    def _append_analysis_package_version(self, state: GameState) -> None:
        diligence = self._diligence(state)
        canonical = self.canonical_facts(state)
        for index, package in enumerate(diligence.packages):
            prior = package.versions[-1]
            included_ids = list(prior.included_item_ids)
            omitted_ids = list(prior.omitted_requested_item_ids)
            source_ids = list(prior.source_record_ids)
            if (
                package.intended_stakeholder_id == "mara_voss"
                and diligence.numbers_posture == NumbersPosture.OMIT_MARGIN_CALL
            ):
                included_ids = [item for item in included_ids if item != "req_margin_history"]
                if "req_margin_history" not in omitted_ids:
                    omitted_ids.append("req_margin_history")
                source_ids = [item for item in source_ids if item != "episode_01_hedge_book"]
            else:
                source_ids = list(
                    dict.fromkeys(
                        [
                            *source_ids,
                            "forecast_live_week_2028",
                            "blotter_eleventh_contract",
                            "episode_01_two_oclock_call",
                            "great_lakes_revolver",
                        ]
                    )
                )
            facts = self._package_facts(
                state,
                stakeholder_id=package.intended_stakeholder_id,
                canonical=canonical,
            )
            if (
                package.intended_stakeholder_id == "sofia_marin"
                and diligence.scenario_posture == ScenarioPosture.ESCALATE
            ):
                note = "Risk schedule added; sensitivity assumptions pending owner review."
            elif package.intended_stakeholder_id == "sofia_marin":
                note = (
                    "Full sensitivity table and source-linked risk schedule added."
                    if diligence.scenario_posture == ScenarioPosture.FULL
                    else "Summary sensitivity and source-linked risk schedule added."
                )
            else:
                note = "Source-linked risk, liquidity, and remediation status added."
            new_version = PackageVersion(
                package_id=package.package_id,
                version=prior.version + 1,
                intended_stakeholder_id=package.intended_stakeholder_id,
                included_item_ids=included_ids,
                omitted_requested_item_ids=omitted_ids,
                source_record_ids=source_ids,
                fact_values=facts,
                created_at=self._at(2, 13, 0) + timedelta(minutes=index * 10),
                delivered_at=self._at(2, 13, 15) + timedelta(minutes=index * 10),
                prepared_by_id="player",
                reviewed_by_ids=list(prior.reviewed_by_ids),
                supersedes_version=prior.version,
                change_kind="supplement",
                change_note=note,
            )
            package.versions.append(new_version)
            diligence.deliveries.append(
                AccessDeliveryRecord(
                    delivery_id=f"delivery_{package.package_id}_v{new_version.version}",
                    package_id=package.package_id,
                    package_version=new_version.version,
                    stakeholder_id=package.intended_stakeholder_id,
                    delivered_at=new_version.delivered_at,
                    acknowledged_at=new_version.delivered_at + timedelta(minutes=3),
                    delivery_method=(
                        "structured_room"
                        if package.intended_stakeholder_id == "sofia_marin"
                        else "committee_packet"
                        if package.intended_stakeholder_id == "ingrid_holtz"
                        else "secure_email"
                    ),
                )
            )

    def _questions(self) -> list[DiligenceQuestion]:
        questions = [
            (
                "question_buyer_quantity",
                "sofia_marin",
                "Why were eleven contracts executed against ten authorized?",
                ["authorized_contracts", "executed_contracts"],
            ),
            (
                "question_buyer_timing",
                "sofia_marin",
                "When was the mismatch found, corrected, and supported physically?",
                ["supported_volume_trade_date", "eventual_supported_volume"],
            ),
            (
                "question_buyer_recurrence",
                "sofia_marin",
                "Has remediation been implemented and could the issue recur?",
                ["remediation_status", "audit_outcome"],
            ),
            (
                "question_lender_liquidity",
                "mara_voss",
                "Did Northstar approach its liquidity covenant during the margin call?",
                ["covenant_headroom", "margin_call_disclosed"],
            ),
            (
                "question_lender_economics",
                "mara_voss",
                "Does Northstar distinguish economic hedging from cash liquidity?",
                ["futures_pnl", "physical_economic_pnl"],
            ),
            (
                "question_board_credibility",
                "ingrid_holtz",
                "Do management's statements agree with Noah's report and chronology?",
                ["audit_outcome", "remediation_status"],
            ),
            (
                "question_board_notification",
                "ingrid_holtz",
                "When was the exception reported, and did the certification agree?",
                ["audit_outcome", "authorized_contracts", "executed_contracts"],
            ),
            (
                "question_board_correction",
                "ingrid_holtz",
                "Was the excess position corrected under a separate approval?",
                ["executed_contracts", "authorized_contracts"],
            ),
        ]
        return [
            DiligenceQuestion(
                question_id=question_id,
                stakeholder_id=stakeholder_id,
                asked_at=self._at(3, 9 + index, 0),
                text=text,
                source_fact_keys=fact_keys,
            )
            for index, (question_id, stakeholder_id, text, fact_keys) in enumerate(questions)
        ]

    def _question_source_ids(self, question_id: str, state: GameState) -> list[str]:
        chapter = self._chapter(state)
        treasury = state.treasury
        mapping = {
            "question_buyer_quantity": [
                chapter.authorization.authorization_id,
                chapter.execution.execution_id,
                chapter.confirmation.confirmation_id,
            ],
            "question_buyer_timing": [
                chapter.physical_forecast.forecast_id,
                chapter.reconciliation.reconciliation_id,
            ],
            "question_buyer_recurrence": [
                "internal_audit_walkthrough_no_surprises",
                self._audit(state).engagement.engagement_id,
            ],
            "question_lender_liquidity": [
                treasury.scenario_id,
                treasury.facility.facility_id,
            ],
            "question_lender_economics": [
                chapter.blotter.blotter_id,
                chapter.physical_forecast.forecast_id,
                state.hedge_book.scenario_id,
            ],
            "question_board_credibility": [
                "internal_audit_walkthrough_no_surprises",
                chapter.reconciliation.reconciliation_id,
            ],
            "question_board_notification": [
                chapter.reconciliation.reconciliation_id,
                *(
                    [chapter.notifications[0].communication_record_id]
                    if chapter.notifications
                    else []
                ),
            ],
            "question_board_correction": [
                chapter.reconciliation.reconciliation_id,
                *(
                    [chapter.position.offset_trade.trade_id]
                    if chapter.position.offset_trade is not None
                    else [chapter.blotter.blotter_id]
                ),
            ],
        }
        return mapping[question_id]

    def _response_text(
        self,
        question_id: str,
        posture: AnswerPosture,
        state: GameState,
    ) -> str:
        chapter = self._chapter(state)
        treasury = state.treasury
        if posture == AnswerPosture.NARROW:
            return {
                "question_buyer_quantity": "The position was corrected prospectively.",
                "question_buyer_timing": "Later physical support is included in the file.",
                "question_buyer_recurrence": "Management approved remediation.",
                "question_lender_liquidity": "The fictional covenant passed.",
                "question_lender_economics": "The hedge reduced price exposure.",
                "question_board_credibility": "Management believes the issue is resolved.",
                "question_board_notification": (
                    "The exception appears in the completed reconciliation."
                ),
                "question_board_correction": "The ending position reflects later activity.",
            }[question_id]
        if posture == AnswerPosture.ACKNOWLEDGE_UNCERTAINTY:
            return (
                "The linked records establish the dated facts. They do not establish "
                "that an approved action plan has been implemented or tested."
            )
        if posture == AnswerPosture.REFER_TO_OWNER:
            return (
                "The schedule reconciles the recorded amounts; June Halvorsen and Evelyn "
                "retain ownership of facility interpretation and representations."
            )
        headroom = money(
            treasury.covenant_result.available_liquidity - treasury.covenant_result.minimum_required
        )
        complete = {
            "question_buyer_quantity": (
                f"Authorization permitted {chapter.authorization.maximum_quantity}; execution "
                f"and FCM confirmation recorded {chapter.execution.quantity}. The difference "
                "was preserved as an exception."
            ),
            "question_buyer_timing": (
                "The reconciliation timestamp records discovery. Any offset is a later "
                "prospective correction, and later physical support retains its own date."
            ),
            "question_buyer_recurrence": (
                f"The current supported remediation status is "
                f"{self.actual_remediation_status(state).value}; no effectiveness test is "
                "claimed, so recurrence risk remains."
            ),
            "question_lender_liquidity": (
                f"The fictional covenant passed with ${headroom:,.2f} headroom after the "
                "recorded margin and protected-obligation sequence."
            ),
            "question_lender_economics": (
                "Physical and futures economic effects are shown separately from daily "
                "variation-margin cash and operating liquidity."
            ),
            "question_board_credibility": (
                "The representation draft is compared with Noah's report, the authorization, "
                "the chronology, and the evidence-supported remediation status."
            ),
            "question_board_notification": (
                "The linked notification retains its actual timestamp. The certification "
                "is described according to the reconciliation record, including any "
                "qualification or unresolved exception."
            ),
            "question_board_correction": (
                "Any correction is a separately approved opposite trade with its own time; "
                "it does not rewrite the original eleven-contract execution."
            ),
        }
        return complete[question_id]

    def _management_representation(
        self,
        state: GameState,
        *,
        version: int,
    ) -> ManagementRepresentationDraft:
        diligence = self._diligence(state)
        canonical = self.canonical_facts(state)
        incomplete = diligence.representation_posture == RepresentationPosture.PREFERRED_INCOMPLETE
        statements = {
            "authorization": (
                "The business authorized the executed hedge."
                if incomplete
                else (
                    f"{canonical['executed_contracts']} contracts executed against "
                    f"{canonical['authorized_contracts']} authorized."
                )
            ),
            "liquidity": (
                "No liquidity issue occurred."
                if incomplete
                else "The covenant passed; margin liquidity and headroom are disclosed separately."
            ),
            "remediation": (
                "Remediation is complete."
                if incomplete
                else (
                    f"Remediation status is {canonical['remediation_status']}; "
                    "effectiveness has not been claimed."
                )
            ),
        }
        return ManagementRepresentationDraft(
            representation_id="management_representation_draft",
            version=version,
            drafted_at=self._at(3, 15, 0),
            drafted_by_id="player",
            reviewed_by_ids=["evelyn_marsh"] if not incomplete else ["cal_rourke"],
            statements=statements,
            source_record_ids=[
                "auth_live_week_ten_short",
                "execution_live_week_eleven",
                "episode_01_two_oclock_call",
                "internal_audit_walkthrough_no_surprises",
            ],
            consistent_with_sources=not incomplete,
            escalated=diligence.representation_posture == RepresentationPosture.ESCALATE,
        )

    def _correct_conflicting_packages(self, state: GameState) -> None:
        diligence = self._diligence(state)
        canonical = self.canonical_facts(state)
        changed: dict[str, int] = {}
        for package in diligence.packages:
            prior = package.versions[-1]
            corrected_facts = dict(prior.fact_values)
            needs_correction = False
            restore_margin_history = (
                prior.fact_values.get("margin_call_disclosed") == "no"
                and canonical["margin_call_disclosed"] == "yes"
                and "req_margin_history" in prior.omitted_requested_item_ids
            )
            for key, value in list(corrected_facts.items()):
                if key in canonical and value != canonical[key]:
                    corrected_facts[key] = canonical[key]
                    needs_correction = True
            if restore_margin_history:
                needs_correction = True
            if not needs_correction:
                continue
            included_item_ids = list(prior.included_item_ids)
            omitted_item_ids = list(prior.omitted_requested_item_ids)
            source_record_ids = list(prior.source_record_ids)
            if restore_margin_history:
                request = next(
                    item for item in diligence.requests if item.request_id == package.request_id
                )
                margin_item = next(
                    item for item in request.items if item.item_id == "req_margin_history"
                )
                included_item_ids = list(dict.fromkeys([*included_item_ids, margin_item.item_id]))
                omitted_item_ids.remove(margin_item.item_id)
                source_record_ids = list(
                    dict.fromkeys([*source_record_ids, *margin_item.source_record_ids])
                )
                margin_item.status = DisclosureStatus.CORRECTED
            new_version = PackageVersion(
                package_id=package.package_id,
                version=prior.version + 1,
                intended_stakeholder_id=package.intended_stakeholder_id,
                included_item_ids=included_item_ids,
                omitted_requested_item_ids=omitted_item_ids,
                source_record_ids=source_record_ids,
                fact_values=corrected_facts,
                created_at=self._at(4, 10, 0) + timedelta(minutes=len(changed) * 5),
                delivered_at=self._at(4, 10, 10) + timedelta(minutes=len(changed) * 5),
                prepared_by_id="player",
                reviewed_by_ids=["evelyn_marsh", "noah_shah"],
                supersedes_version=prior.version,
                change_kind="correction",
                change_note="Conflicting description corrected to the dated source records.",
            )
            package.versions.append(new_version)
            changed[package.package_id] = new_version.version
            diligence.deliveries.append(
                AccessDeliveryRecord(
                    delivery_id=f"delivery_{package.package_id}_v{new_version.version}",
                    package_id=package.package_id,
                    package_version=new_version.version,
                    stakeholder_id=package.intended_stakeholder_id,
                    delivered_at=new_version.delivered_at,
                    acknowledged_at=new_version.delivered_at + timedelta(minutes=2),
                    delivery_method=(
                        "structured_room"
                        if package.intended_stakeholder_id == "sofia_marin"
                        else "committee_packet"
                        if package.intended_stakeholder_id == "ingrid_holtz"
                        else "secure_email"
                    ),
                )
            )
        package_by_id = {item.package_id: item for item in diligence.packages}
        canonical = self.canonical_facts(state)
        for inconsistency in diligence.inconsistencies:
            for package_id in (
                inconsistency.first_package_id,
                inconsistency.second_package_id,
            ):
                if package_id in changed:
                    correction = package_by_id[package_id].versions[-1]
                    if correction.fact_values.get(inconsistency.fact_key) == canonical.get(
                        inconsistency.fact_key
                    ):
                        inconsistency.corrected_by_package_id = package_id
                        inconsistency.corrected_by_version = changed[package_id]
                        break

    def _supplement_limited_packages(self, state: GameState) -> None:
        diligence = self._diligence(state)
        for package in diligence.packages:
            prior = package.versions[-1]
            if not prior.omitted_requested_item_ids:
                continue
            request = next(
                item for item in diligence.requests if item.request_id == package.request_id
            )
            available_omitted = [
                item
                for item in request.items
                if item.available and item.item_id in prior.omitted_requested_item_ids
            ]
            if not available_omitted:
                continue
            added_ids = {item.item_id for item in available_omitted}
            source_ids = list(
                dict.fromkeys(
                    [
                        *prior.source_record_ids,
                        *(
                            source_id
                            for item in available_omitted
                            for source_id in item.source_record_ids
                        ),
                    ]
                )
            )
            version = PackageVersion(
                package_id=package.package_id,
                version=prior.version + 1,
                intended_stakeholder_id=package.intended_stakeholder_id,
                included_item_ids=list(dict.fromkeys([*prior.included_item_ids, *added_ids])),
                omitted_requested_item_ids=[
                    item for item in prior.omitted_requested_item_ids if item not in added_ids
                ],
                source_record_ids=source_ids,
                fact_values=dict(prior.fact_values),
                created_at=self._at(4, 9, 20),
                delivered_at=self._at(4, 9, 30),
                prepared_by_id="player",
                reviewed_by_ids=["evelyn_marsh", "noah_shah"],
                supersedes_version=prior.version,
                change_kind="supplement",
                change_note="Available requested records added; prior delivery preserved.",
            )
            package.versions.append(version)
            diligence.deliveries.append(
                AccessDeliveryRecord(
                    delivery_id=f"delivery_{package.package_id}_v{version.version}",
                    package_id=package.package_id,
                    package_version=version.version,
                    stakeholder_id=package.intended_stakeholder_id,
                    delivered_at=version.delivered_at,
                    acknowledged_at=version.delivered_at + timedelta(minutes=3),
                    delivery_method=(
                        "structured_room"
                        if package.intended_stakeholder_id == "sofia_marin"
                        else "committee_packet"
                        if package.intended_stakeholder_id == "ingrid_holtz"
                        else "secure_email"
                    ),
                )
            )
            for item in available_omitted:
                item.status = DisclosureStatus.SUPPLEMENTED

    def _build_findings(self, state: GameState) -> list[DiligenceFinding]:
        diligence = self._diligence(state)
        chapter = self._chapter(state)
        findings = [
            DiligenceFinding(
                finding_id="finding_eleventh_significance",
                title="The Eleventh Contract remains qualitatively significant",
                description=(
                    "The authorization, chronology, certification, liquidity, recurrence, "
                    "and credibility context remains relevant irrespective of dollar size."
                ),
                source_record_ids=[
                    chapter.authorization.authorization_id,
                    chapter.reconciliation.reconciliation_id,
                    "internal_audit_walkthrough_no_surprises",
                ],
                stakeholder_ids=["sofia_marin", "ingrid_holtz", "mara_voss"],
                significance_basis=list(
                    diligence.risk_schedule.significance.qualitative_factors
                    if diligence.risk_schedule
                    else ["Authorization and credibility"]
                ),
                resolved=False,
            )
        ]
        for index, inconsistency in enumerate(diligence.inconsistencies, start=1):
            findings.append(
                DiligenceFinding(
                    finding_id=f"finding_inconsistency_{index:02d}",
                    title=f"Inconsistent disclosure: {inconsistency.fact_key}",
                    description=(
                        f"Package versions recorded {inconsistency.first_value!r} and "
                        f"{inconsistency.second_value!r} for the same dated fact."
                    ),
                    source_record_ids=[
                        *self._package_source_ids(
                            diligence, inconsistency.first_package_id, inconsistency.first_version
                        ),
                        *self._package_source_ids(
                            diligence, inconsistency.second_package_id, inconsistency.second_version
                        ),
                    ],
                    stakeholder_ids=["sofia_marin", "ingrid_holtz", "mara_voss"],
                    significance_basis=["Stakeholder consistency", "Management credibility"],
                    resolved=inconsistency.corrected_by_package_id is not None,
                )
            )
        if diligence.diligence_flags.get("remediation_overstated"):
            findings.append(
                DiligenceFinding(
                    finding_id="finding_remediation_overstated",
                    title="Remediation status exceeded supporting evidence",
                    description=(
                        "A package used implemented while the underlying audit record "
                        f"supports {self.actual_remediation_status(state).value}."
                    ),
                    source_record_ids=[self._audit(state).engagement.engagement_id],
                    stakeholder_ids=["sofia_marin", "ingrid_holtz"],
                    significance_basis=["Control status", "Credibility", "Potential recurrence"],
                    resolved=any(
                        item.change_kind == "correction"
                        for package in diligence.packages
                        for item in package.versions
                    ),
                )
            )
        if diligence.diligence_flags.get("margin_call_omitted"):
            findings.append(
                DiligenceFinding(
                    finding_id="finding_margin_omitted",
                    title="Known margin history was omitted from the lender package",
                    description=(
                        "The omission is evaluated with availability, relevance, correction, "
                        "and management representations; omission alone is not labeled misconduct."
                    ),
                    source_record_ids=[state.hedge_book.scenario_id, state.treasury.scenario_id],
                    stakeholder_ids=["mara_voss"],
                    significance_basis=["Liquidity", "Reporting accuracy"],
                    resolved=any(
                        "req_margin_history" in version.included_item_ids
                        for package in diligence.packages
                        if package.intended_stakeholder_id == "mara_voss"
                        for version in package.versions[1:]
                    ),
                )
            )
        if (
            diligence.management_representations
            and not diligence.management_representations[-1].consistent_with_sources
        ):
            findings.append(
                DiligenceFinding(
                    finding_id="finding_management_representation",
                    title="Management representation is not fully substantiated",
                    description=(
                        "Authorization, liquidity, and remediation statements do not all "
                        "agree with the linked source records."
                    ),
                    source_record_ids=list(
                        diligence.management_representations[-1].source_record_ids
                    ),
                    stakeholder_ids=["sofia_marin", "ingrid_holtz"],
                    significance_basis=["Management credibility", "Record consistency"],
                    resolved=(
                        diligence.final_action == FinalAction.ESCALATE_REPRESENTATION
                        or diligence.representation_posture == RepresentationPosture.CORRECT
                    ),
                )
            )
        return findings

    def _derive_outcome(self, state: GameState) -> DiligenceOutcome:
        diligence = self._diligence(state)
        unresolved_inconsistencies = [
            item for item in diligence.inconsistencies if item.corrected_by_package_id is None
        ]
        representation_incomplete = (
            diligence.representation_posture == RepresentationPosture.PREFERRED_INCOMPLETE
        )
        if len({item.fact_key for item in unresolved_inconsistencies}) >= 4 or (
            representation_incomplete
            and diligence.inconsistency_action == InconsistencyAction.LEAVE
            and diligence.final_action == FinalAction.STAY_SILENT
        ):
            return DiligenceOutcome.BUYER_WALKS
        if diligence.remediation_posture == RemediationPosture.IMPLEMENTED_CLAIM:
            return DiligenceOutcome.REMEDIATION_ON_PAPER
        if (
            diligence.committee_posture == CommitteePosture.PROTECT_CAL
            and representation_incomplete
        ):
            return DiligenceOutcome.BELLANDI_CONFIDENCE
        if unresolved_inconsistencies:
            return DiligenceOutcome.THREE_VERSIONS_OF_MONDAY
        if (
            diligence.scenario_posture == ScenarioPosture.ESCALATE
            and diligence.lender_answer_posture == AnswerPosture.COMPLETE
        ):
            return DiligenceOutcome.COVENANT_CONVERSATION
        if (
            diligence.disclosure_scope == DisclosureScope.LIMITED
            and diligence.inconsistency_action
            in {InconsistencyAction.SUPPLEMENT, InconsistencyAction.CORRECT}
            and diligence.buyer_answer_posture == AnswerPosture.COMPLETE
        ):
            return DiligenceOutcome.PRICE_OF_CANDOR
        if (
            diligence.committee_posture == CommitteePosture.ACKNOWLEDGE_INCOMPLETE
            and diligence.remediation_posture == RemediationPosture.ACTUAL_STATUS
        ):
            return DiligenceOutcome.CONDITIONAL_CLOSE
        return DiligenceOutcome.CLEAN_ROOM

    @staticmethod
    def _transaction_status(outcome: DiligenceOutcome) -> TransactionStatus:
        return {
            DiligenceOutcome.CLEAN_ROOM: TransactionStatus.DILIGENCE_CONTINUES,
            DiligenceOutcome.PRICE_OF_CANDOR: TransactionStatus.TOUGHER_TERMS,
            DiligenceOutcome.THREE_VERSIONS_OF_MONDAY: TransactionStatus.ADDITIONAL_TESTING,
            DiligenceOutcome.REMEDIATION_ON_PAPER: TransactionStatus.ADDITIONAL_TESTING,
            DiligenceOutcome.COVENANT_CONVERSATION: TransactionStatus.TOUGHER_TERMS,
            DiligenceOutcome.BELLANDI_CONFIDENCE: TransactionStatus.STALLED,
            DiligenceOutcome.BUYER_WALKS: TransactionStatus.BUYER_WITHDREW,
            DiligenceOutcome.CONDITIONAL_CLOSE: TransactionStatus.CONDITIONAL_CLOSE,
        }[outcome]

    def _stakeholder_reactions(
        self,
        state: GameState,
        outcome: DiligenceOutcome,
    ) -> list[StakeholderReaction]:
        diligence = self._diligence(state)
        unresolved = sum(
            1 for item in diligence.inconsistencies if item.corrected_by_package_id is None
        )
        buyer_delta = diligence.relationships.get("sofia_marin", 0) - unresolved
        board_delta = diligence.relationships.get("ingrid_holtz", 0) - unresolved
        lender_delta = diligence.relationships.get("mara_voss", 0) - int(
            diligence.diligence_flags.get("margin_call_omitted", False)
        )
        return [
            StakeholderReaction(
                stakeholder_id="sofia_marin",
                trust_delta=max(-10, min(10, buyer_delta)),
                reaction=(
                    "Sofia can trace the schedules to source records."
                    if buyer_delta >= 0
                    else "Sofia expands consistency testing before relying on management."
                ),
                requested_follow_up=(
                    "Documented remediation conditions"
                    if outcome == DiligenceOutcome.CONDITIONAL_CLOSE
                    else None
                ),
            ),
            StakeholderReaction(
                stakeholder_id="ingrid_holtz",
                trust_delta=max(-10, min(10, board_delta)),
                reaction=(
                    "The committee sees clear ownership and residual risk."
                    if board_delta >= 0
                    else "The committee questions management's version control."
                ),
                requested_follow_up="Quarterly remediation reporting",
            ),
            StakeholderReaction(
                stakeholder_id="mara_voss",
                trust_delta=max(-10, min(10, lender_delta)),
                reaction=(
                    "The lender distinguishes covenant compliance from thin headroom."
                    if lender_delta >= 0
                    else "The lender asks for additional liquidity reporting."
                ),
                requested_follow_up=(
                    "Monthly margin-liquidity and covenant schedule"
                    if outcome
                    in {
                        DiligenceOutcome.COVENANT_CONVERSATION,
                        DiligenceOutcome.PRICE_OF_CANDOR,
                    }
                    else None
                ),
            ),
        ]

    def _eleventh_basis_effect(self, state: GameState) -> Decimal:
        chapter = self._chapter(state)
        scenario = self.content.eleventh_scenario
        final_basis = (
            scenario.day_3_arrives_basis
            if chapter.physical_forecast.outcome == PhysicalVolumeOutcome.ARRIVES
            else scenario.day_3_fails_basis
        )
        return money(
            (final_basis - scenario.chicago_basis)
            * chapter.physical_forecast.eventual_supported_volume_mmbtu
        )

    @staticmethod
    def _metric(
        metric_id: str,
        label: str,
        value: Decimal,
        unit: str,
        source_record_ids: list[str],
        calculation: str | None = None,
    ) -> RiskMetric:
        return RiskMetric(
            metric_id=metric_id,
            label=label,
            value_text=str(value),
            numeric_value=value,
            unit=unit,
            source_record_ids=source_record_ids,
            calculation=calculation,
        )

    @staticmethod
    def _reference(
        reference_id: str,
        record_id: str,
        record_type: str,
        fact_key: str,
        value_text: str,
        *,
        as_of=None,
        calculation: str | None = None,
    ) -> SourceRecordReference:
        return SourceRecordReference(
            reference_id=reference_id,
            record_id=record_id,
            record_type=record_type,
            fact_key=fact_key,
            as_of=as_of,
            value_text=value_text,
            calculation=calculation,
        )

    @staticmethod
    def _package_source_ids(
        diligence: DiligenceRoomState,
        package_id: str,
        version: int,
    ) -> list[str]:
        package = next(item for item in diligence.packages if item.package_id == package_id)
        return list(
            next(item for item in package.versions if item.version == version).source_record_ids
        )

    def _at(self, day: int, hour: int, minute: int) -> datetime:
        return datetime.combine(
            self.scenario.day_dates[f"day_{day}"],
            time(hour, minute),
            tzinfo=CHICAGO_TZ,
        )

    @staticmethod
    def _diligence(state: GameState) -> DiligenceRoomState:
        if state.diligence_room is None:
            raise ValueError("The Diligence Room has not started")
        return state.diligence_room

    @staticmethod
    def _chapter(state: GameState):
        chapter = state.eleventh_contract
        if (
            chapter is None
            or not chapter.completed
            or chapter.authorization is None
            or chapter.execution is None
            or chapter.confirmation is None
            or chapter.reconciliation is None
            or chapter.blotter is None
            or chapter.position is None
        ):
            raise ValueError("completed Eleventh Contract records are required")
        return chapter

    @staticmethod
    def _audit(state: GameState):
        audit = state.no_surprises
        if audit is None or not audit.completed or audit.outcome is None:
            raise ValueError("completed No Surprises records are required")
        return audit

    @staticmethod
    def _require_financial_sources(state: GameState) -> None:
        if (
            state.hedge_book is None
            or not state.hedge_book.completed
            or state.treasury is None
            or not state.treasury.completed
            or state.treasury.covenant_result is None
        ):
            raise ValueError("completed commodity and treasury records are required")

    @staticmethod
    def _protected_records(state: GameState) -> dict[str, object]:
        return {
            "hedge_book": (state.hedge_book.model_dump(mode="json") if state.hedge_book else None),
            "treasury": state.treasury.model_dump(mode="json") if state.treasury else None,
            "chapter": (
                state.eleventh_contract.model_dump(mode="json") if state.eleventh_contract else None
            ),
            "audit": (state.no_surprises.model_dump(mode="json") if state.no_surprises else None),
            "evidence": [item.model_dump(mode="json") for item in state.evidence_log],
            "ledger": state.ledger.model_dump(mode="json"),
            "cash": (state.corporate_cash, state.personal_cash, state.margin_due),
        }

    @staticmethod
    def _assert_records_unchanged(
        state: GameState,
        protected: dict[str, object],
    ) -> None:
        if DiligenceEngine._protected_records(state) != protected:
            raise RuntimeError("diligence work changed a preserved source record")
