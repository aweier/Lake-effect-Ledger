"""State-derived rules for the four-stage No Surprises walkthrough."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta, timezone
from typing import TYPE_CHECKING

from lake_effect_ledger.audit.models import (
    AuditChronology,
    AuditEngagement,
    AuditException,
    AuditOutcome,
    AuditScope,
    AuditStage,
    ChronologyEntry,
    ControlTestResult,
    EvidencePackageResponse,
    EvidenceRequest,
    ExceptionCategory,
    Finding,
    FindingSeverity,
    FindingStatus,
    ManagementResponse,
    NoSurprisesState,
    PackageStrategy,
    PopulationReference,
    RemediationKind,
    RemediationOwner,
    RemediationRecommendation,
    RequestedItem,
    ResponseAgreement,
    RootCauseCategory,
    SupplementChoice,
    TestResultRating,
    WalkthroughPosture,
    WalkthroughStep,
)
from lake_effect_ledger.trading.models import (
    EleventhOutcome,
    PhysicalVolumeOutcome,
)

if TYPE_CHECKING:
    from lake_effect_ledger.audit.models import AuditChoiceDefinition
    from lake_effect_ledger.narrative.models import ContentBundle
    from lake_effect_ledger.state import GameState


CHICAGO_TZ = timezone(timedelta(hours=-6), name="CST")


@dataclass(frozen=True)
class ResolvedRecord:
    record_id: str
    record_type: str
    available: bool
    created_at: datetime | None
    contemporaneous: bool


class InternalAuditEngine:
    """Evaluate one completed transaction; this is intentionally not a GRC platform."""

    def __init__(self, content: ContentBundle) -> None:
        self.content = content
        self.scenario = content.audit_scenario

    def initialize(self, state: GameState) -> NoSurprisesState:
        if state.no_surprises is not None:
            return state.no_surprises
        chapter = state.eleventh_contract
        if chapter is None or not chapter.completed or chapter.outcome is None:
            raise ValueError("complete The Eleventh Contract before No Surprises")
        opened_at = self._at(1, 9, 0)
        engagement = AuditEngagement(
            engagement_id="audit_no_surprises_2028",
            title=self.scenario.title,
            objective=self.scenario.engagement_objective,
            lead_auditor_id="noah_shah",
            opened_at=opened_at,
            scope=AuditScope(
                transaction_reference=chapter.scenario_id,
                period_start=self.content.eleventh_scenario.day_1_date,
                period_end=self.content.eleventh_scenario.day_3_date,
                included_processes=list(self.scenario.scope_inclusions),
                excluded_processes=list(self.scenario.scope_exclusions),
            ),
        )
        items = [self._resolve_request_item(state, item) for item in self.scenario.request_specs]
        request = EvidenceRequest(
            request_id="request_no_surprises_001",
            engagement_id=engagement.engagement_id,
            issued_at=self._at(1, 9, 5),
            due_at=self._at(1, 16, 0),
            requested_items=items,
        )
        relationships = {
            "noah_shah": 0,
            "evelyn_marsh": chapter.relationships.get("evelyn_marsh", 0),
            "cal_rourke": chapter.relationships.get("cal_rourke", 0),
            "marisol_vega": chapter.relationships.get("marisol_vega", 0),
        }
        audit = NoSurprisesState(
            scenario_id=self.scenario.id,
            prior_eleventh_outcome=chapter.outcome,
            engagement=engagement,
            evidence_request=request,
            relationships=relationships,
            beginning_relationships=dict(relationships),
        )
        state.no_surprises = audit
        state.current_date = self.scenario.day_dates["day_1"]
        state.record(
            phase="system",
            event_type="internal_audit_started",
            source_id=engagement.engagement_id,
            message="Noah Shah issued the Eleventh Contract walkthrough request.",
            changes={"transaction_reference": chapter.scenario_id},
        )
        return audit

    def apply_choice(
        self,
        state: GameState,
        scene_id: str,
        choice_id: str,
    ) -> AuditChoiceDefinition:
        audit = self._audit(state)
        scene = self.content.audit_scene(scene_id)
        if choice_id in audit.decisions or choice_id in state.decisions:
            raise ValueError(f"audit choice has already been applied: {choice_id}")
        if any(choice.id in audit.decisions for choice in scene.choices):
            raise ValueError(f"audit scene already has a durable choice: {scene_id}")
        try:
            choice = next(item for item in scene.choices if item.id == choice_id)
        except StopIteration as error:
            raise ValueError(f"unknown audit choice {choice_id} for {scene_id}") from error
        prior_records = self._protected_records(state)
        audit.decisions.append(choice.id)
        state.decisions.append(choice.id)
        for objective_id in choice.learning_objective_ids:
            if objective_id not in audit.practiced_objective_ids:
                audit.practiced_objective_ids.append(objective_id)
            if objective_id not in state.learning_objectives:
                state.learning_objectives.append(objective_id)
        effect = choice.effect
        for field in (
            "package_strategy",
            "chronology_style",
            "selection_notice",
            "walkthrough_posture",
            "volume_explanation",
            "responsibility_posture",
            "control_view",
            "finding_posture",
            "supplement_choice",
            "remediation_kind",
            "response_agreement",
            "elevate_unresolved",
        ):
            value = getattr(effect, field)
            if value is not None:
                setattr(audit, field, value)
        audit.audit_flags.update(effect.flags)
        for person_id, amount in effect.relationship_deltas.items():
            current = audit.relationships.get(person_id, 0)
            audit.relationships[person_id] = max(-10, min(10, current + amount))
        for tag, amount in effect.trajectory_deltas.items():
            state.career_trajectory.record(choice.id, tag, amount)
        state.record(
            phase="decision",
            event_type="audit_decision",
            source_id=choice.id,
            message=choice.text,
            changes={"scene_id": scene_id},
        )
        self._assert_records_unchanged(state, prior_records)
        return choice

    def prepare_initial_package(self, state: GameState) -> EvidencePackageResponse:
        audit = self._audit(state)
        if audit.package_responses:
            return audit.package_responses[0]
        strategy = audit.package_strategy or PackageStrategy.COMPLETE
        available = [item for item in audit.evidence_request.requested_items if item.available]
        if strategy == PackageStrategy.EVELYN_REVIEW:
            deferred_ids = {
                "req_notification",
                "req_corrective_approval",
                "req_offset",
                "req_physical_support",
                "req_communications",
            }
            included = [item for item in available if item.request_item_id not in deferred_ids]
        else:
            included = available
        provided_at = self._at(1, 15, 30)
        included_ids = [item.request_item_id for item in included]
        for item in audit.evidence_request.requested_items:
            if item.request_item_id in included_ids:
                item.included_initially = True
                item.date_provided = provided_at
                item.response_status = "provided"
            elif not item.available:
                item.response_status = "missing"
        additional = (
            self._additional_linked_record_ids(state)
            if strategy == PackageStrategy.COMPLETE
            else []
        )
        response = EvidencePackageResponse(
            response_id="audit_response_initial",
            request_id=audit.evidence_request.request_id,
            submitted_at=provided_at,
            prepared_by_id="player",
            included_request_item_ids=included_ids,
            additional_record_ids=additional,
            note={
                PackageStrategy.COMPLETE: (
                    "Complete linked chain supplied, including related records "
                    "not listed separately."
                ),
                PackageStrategy.REQUESTED_ONLY: "Every available requested item supplied.",
                PackageStrategy.EVELYN_REVIEW: (
                    "Core package supplied after controller review; conditional records deferred."
                ),
            }[strategy],
        )
        audit.package_responses.append(response)
        audit.current_stage = AuditStage.WALKTHROUGH
        audit.current_scene_index = 0
        state.current_date = self.scenario.day_dates["day_2"]
        audit.chronology = self.build_chronology(state)
        return response

    def prepare_supplement(self, state: GameState) -> EvidencePackageResponse | None:
        audit = self._audit(state)
        if audit.supplement_choice != SupplementChoice.DISCLOSE_OMITTED:
            return None
        existing = next(
            (item for item in audit.package_responses if item.supplemental),
            None,
        )
        if existing is not None:
            return existing
        omitted = [
            item
            for item in audit.evidence_request.requested_items
            if item.available and not item.included_initially
        ]
        if not omitted:
            audit.audit_flags["supplement_not_needed"] = True
            return None
        provided_at = self._at(4, 9, 30)
        for item in omitted:
            item.date_provided = provided_at
            item.response_status = "supplemented"
        response = EvidencePackageResponse(
            response_id="audit_response_supplement_001",
            request_id=audit.evidence_request.request_id,
            submitted_at=provided_at,
            prepared_by_id="player",
            included_request_item_ids=[item.request_item_id for item in omitted],
            supplemental=True,
            note=(
                "Previously omitted available records supplied without altering "
                "the initial response."
            ),
        )
        audit.package_responses.append(response)
        audit.audit_flags["supplemental_evidence_provided"] = True
        audit.chronology = self.build_chronology(state)
        return response

    def build_chronology(self, state: GameState) -> AuditChronology:
        audit = self._audit(state)
        chapter = self._chapter(state)
        entries: list[ChronologyEntry] = []

        def add(
            entry_id: str,
            label: str,
            record_id: str,
            record_type: str,
            timestamp: datetime | None,
            observation: str,
            *,
            contemporaneous: bool = True,
        ) -> None:
            entries.append(
                ChronologyEntry(
                    chronology_entry_id=entry_id,
                    event_label=label,
                    record_id=record_id,
                    record_type=record_type,
                    timestamp=timestamp,
                    contemporaneous=contemporaneous,
                    observation=observation,
                )
            )

        forecast = chapter.physical_forecast
        add(
            "chrono_forecast",
            "Initial physical forecast",
            forecast.forecast_id,
            "PhysicalForecastRecord",
            None,
            (
                f"{forecast.supported_volume_mmbtu} MMBtu supported; "
                f"{forecast.possible_additional_volume_mmbtu} MMBtu possible but unconfirmed."
            ),
        )
        brief = chapter.market_brief
        add(
            "chrono_market_note",
            "Monday market note",
            brief.brief_id,
            "MarketBrief",
            brief.created_at,
            f"Volume treatment: {brief.volume_treatment.value}.",
        )
        authorization = chapter.authorization
        add(
            "chrono_authorization",
            "Authorization approved",
            authorization.authorization_id,
            "TradeAuthorization",
            authorization.approved_at,
            f"Maximum authorized quantity: {authorization.maximum_quantity} contracts.",
        )
        recommendation = chapter.recommendation
        add(
            "chrono_recommendation",
            "Order recommendation",
            recommendation.recommendation_id,
            "OrderRecommendation",
            recommendation.recommended_at,
            f"Recommended quantity: {recommendation.quantity} contracts.",
        )
        order = chapter.order
        add(
            "chrono_order",
            "Internal order submitted",
            order.order_id,
            "TradeOrder",
            order.submitted_at,
            f"Submitted and internally filled quantity: {order.quantity} contracts.",
        )
        execution = chapter.execution
        add(
            "chrono_execution",
            "Execution recorded",
            execution.execution_id,
            "ExecutionRecord",
            execution.fill_timestamp,
            f"Execution record quantity: {execution.quantity} contracts.",
        )
        confirmation = chapter.confirmation
        add(
            "chrono_confirmation",
            "FCM confirmation received",
            confirmation.confirmation_id,
            "FCMConfirmation",
            confirmation.confirmed_at,
            f"FCM confirmed {confirmation.quantity} contracts.",
        )
        reconciliation = chapter.reconciliation
        add(
            "chrono_reconciliation",
            "Quantity mismatch discovered and reconciled",
            reconciliation.reconciliation_id,
            "TradeReconciliationRecord",
            reconciliation.prepared_at,
            (
                f"{reconciliation.exception_contracts} contract exceeded authorization; "
                f"original status {reconciliation.original_status.value}."
            ),
        )
        notification = next(
            (
                record
                for record in state.evidence_log
                if record.record_id == "comm_ec_formal_exception"
            ),
            None,
        )
        if notification is not None:
            add(
                "chrono_notification",
                "Exception notification",
                notification.record_id,
                "CommunicationRecord",
                notification.timestamp,
                f"Recipients: {', '.join(notification.recipient_ids)}.",
            )
        certification_id = reconciliation.certification_record_id
        if certification_id:
            certification = next(
                (record for record in state.evidence_log if record.record_id == certification_id),
                None,
            )
            add(
                "chrono_certification",
                "Reconciliation certification",
                certification_id,
                "CommunicationRecord",
                certification.timestamp if certification else None,
                f"Certification retained status {reconciliation.current_status.value}.",
            )
        if chapter.approvals:
            approval = chapter.approvals[0]
            add(
                "chrono_corrective_approval",
                "Corrective trade approval",
                approval.approval_id,
                "CorrectiveTradeApprovalRecord",
                approval.approved_at,
                f"Approved {approval.quantity}-contract {approval.side.value} correction.",
            )
        offset = chapter.position.offset_trade
        if offset is not None:
            add(
                "chrono_offset",
                "Approved offset executed",
                offset.trade_id,
                "OffsetTrade",
                offset.executed_at,
                "Offset reduced open exposure and preserved the original execution.",
            )
        support_record_id = (
            forecast.support_document_ids[-1]
            if forecast.support_document_ids
            else forecast.forecast_id
        )
        add(
            "chrono_physical_resolution",
            "Physical support resolved",
            support_record_id,
            (
                "PhysicalSupportDocument"
                if forecast.support_document_ids
                else "PhysicalForecastRecord"
            ),
            forecast.outcome_resolved_at,
            (
                "Additional physical support arrived after execution."
                if forecast.outcome == PhysicalVolumeOutcome.ARRIVES
                else "Additional physical support did not arrive."
            ),
            contemporaneous=False,
        )
        for index, response in enumerate(audit.package_responses, start=1):
            add(
                f"chrono_audit_response_{index}",
                "Audit supplemental response"
                if response.supplemental
                else "Initial audit response",
                response.response_id,
                "EvidencePackageResponse",
                response.submitted_at,
                response.note,
                contemporaneous=False,
            )
        entries.sort(
            key=lambda item: (
                item.timestamp is not None,
                item.timestamp or datetime.min.replace(tzinfo=UTC),
                item.chronology_entry_id,
            )
        )
        contradictions = [
            (
                f"Authorization allowed {authorization.maximum_quantity}, while execution and "
                f"confirmation recorded {execution.quantity}."
            )
        ]
        if forecast.support_obtained_at is not None:
            contradictions.append(
                "Additional physical support arrived after the execution and did "
                "not enlarge prior authority."
            )
        else:
            contradictions.append("The possible additional physical volume never became supported.")
        if notification is None:
            contradictions.append("No formal exception notification record exists.")
        elif notification.timestamp > reconciliation.prepared_at:
            contradictions.append("Formal notification followed the recorded exception discovery.")
        if offset is not None:
            contradictions.append(
                "The offset remediated exposure but preserved the initial breach."
            )
        audit.chronology = AuditChronology(
            chronology_id="chronology_eleventh_contract_audit",
            transaction_reference=chapter.scenario_id,
            generated_at=self._at(2, 10, 0),
            entries=entries,
            contradictions=contradictions,
        )
        return audit.chronology

    def conduct_walkthrough(self, state: GameState) -> list[WalkthroughStep]:
        audit = self._audit(state)
        if audit.walkthrough_steps:
            return audit.walkthrough_steps
        chapter = self._chapter(state)
        posture = audit.walkthrough_posture or WalkthroughPosture.ACCURATE
        forecast = chapter.physical_forecast
        reconciliation = chapter.reconciliation
        notification_ids = [item.communication_record_id for item in chapter.notifications]
        approval_ids = [item.approval_id for item in chapter.approvals]
        offset = chapter.position.offset_trade
        certification_id = reconciliation.certification_record_id
        communications = list(chapter.communication_record_ids)
        actual_facts = [
            (
                "What physical volume was supported initially?",
                [forecast.forecast_id],
                f"{forecast.supported_volume_mmbtu} MMBtu was supported.",
            ),
            (
                "What additional volume was possible but unconfirmed?",
                [forecast.forecast_id],
                f"{forecast.possible_additional_volume_mmbtu} MMBtu was possible and unconfirmed.",
            ),
            (
                "What quantity was recommended?",
                [chapter.recommendation.recommendation_id],
                f"{chapter.recommendation.quantity} contracts were recommended.",
            ),
            (
                "What quantity was authorized?",
                [chapter.authorization.authorization_id],
                f"No more than {chapter.authorization.maximum_quantity} contracts were authorized.",
            ),
            (
                "What order was transmitted?",
                [chapter.order.order_id],
                f"The internal order instruction was {chapter.order.quantity} contracts.",
            ),
            (
                "What was executed?",
                [chapter.execution.execution_id],
                f"The execution record shows {chapter.execution.quantity} contracts.",
            ),
            (
                "What did the FCM confirm?",
                [chapter.confirmation.confirmation_id],
                f"The FCM confirmed {chapter.confirmation.quantity} contracts.",
            ),
            (
                "When was the mismatch discovered?",
                [reconciliation.reconciliation_id],
                f"It was recorded at {reconciliation.prepared_at.isoformat()}.",
            ),
            (
                "Who was notified?",
                notification_ids or [reconciliation.reconciliation_id],
                (
                    f"The formal record names {', '.join(chapter.notifications[0].recipient_ids)}."
                    if chapter.notifications
                    else "No formal exception notification record exists."
                ),
            ),
            (
                "Was correction approved?",
                approval_ids or [reconciliation.reconciliation_id],
                (
                    f"Approval {approval_ids[0]} authorized the correction."
                    if approval_ids
                    else "No corrective approval exists because no correction was executed."
                ),
            ),
            (
                "Was the extra contract offset?",
                [offset.trade_id] if offset else [chapter.blotter.blotter_id],
                (
                    f"Offset {offset.trade_id} reduced the open position."
                    if offset
                    else "The extra contract was not offset."
                ),
            ),
            (
                "When did additional physical support arrive or fail?",
                [
                    forecast.support_document_ids[-1]
                    if forecast.support_document_ids
                    else forecast.forecast_id
                ],
                (
                    f"Resolved at {forecast.outcome_resolved_at.isoformat()}; "
                    f"outcome {forecast.outcome.value}."
                ),
            ),
            (
                "What was certified in reconciliation?",
                [certification_id or reconciliation.reconciliation_id],
                (
                    f"Certification retained status {reconciliation.current_status.value}."
                    if certification_id
                    else (
                        "No separate certification; final status is "
                        f"{reconciliation.current_status.value}."
                    )
                ),
            ),
            (
                "Do contemporaneous communications agree with this explanation?",
                communications or [chapter.market_brief.communication_record_id],
                self._communication_alignment(state),
            ),
        ]
        inconsistent_steps = set()
        if posture == WalkthroughPosture.FALSE_PROCESS_CLAIM:
            inconsistent_steps = {1, 2, 4, 5, 6, 8, 9, 13, 14}
        if (
            audit.volume_explanation is not None
            and audit.volume_explanation.value == "player_recommendation"
            and chapter.brief_hedge_recommendation.value != "recommend_eleventh"
        ):
            inconsistent_steps.add(3)
        explanation_prefix = {
            WalkthroughPosture.ACCURATE: "Complete answer:",
            WalkthroughPosture.NARROW: "Narrow answer:",
            WalkthroughPosture.UNCERTAIN: "Record-based answer after acknowledging uncertainty:",
            WalkthroughPosture.FALSE_PROCESS_CLAIM: "Claimed normal process:",
        }[posture]
        audit.walkthrough_steps = [
            WalkthroughStep(
                step_id=f"walkthrough_{sequence:02d}",
                sequence=sequence,
                question=question,
                evidence_record_ids=evidence_ids,
                player_posture=posture,
                player_explanation=f"{explanation_prefix} {fact}",
                consistent_with_records=sequence not in inconsistent_steps,
                auditor_observation=(
                    "The cited records support the explanation."
                    if sequence not in inconsistent_steps
                    else "The cited records contradict or materially qualify the explanation."
                ),
            )
            for sequence, (question, evidence_ids, fact) in enumerate(actual_facts, start=1)
        ]
        if inconsistent_steps:
            audit.audit_flags["walkthrough_contradiction"] = True
        audit.current_stage = AuditStage.CONTROL_TESTING
        audit.current_scene_index = 0
        state.current_date = self.scenario.day_dates["day_3"]
        return audit.walkthrough_steps

    def evaluate_controls(self, state: GameState) -> list[ControlTestResult]:
        audit = self._audit(state)
        if audit.control_results:
            return audit.control_results
        chapter = self._chapter(state)
        reconciliation = chapter.reconciliation
        evidence = [
            chapter.authorization.authorization_id,
            chapter.order.order_id,
            chapter.execution.execution_id,
            chapter.confirmation.confirmation_id,
            reconciliation.reconciliation_id,
        ]
        exceptions: list[AuditException] = []
        results: list[ControlTestResult] = []

        def exception(
            exception_id: str,
            objective_id: str,
            category: ExceptionCategory,
            description: str,
            record_ids: list[str],
        ) -> str:
            exceptions.append(
                AuditException(
                    exception_id=exception_id,
                    control_objective_id=objective_id,
                    category=category,
                    description=description,
                    evidence_record_ids=record_ids,
                    discovered_at=self._at(3, 10, len(exceptions)),
                )
            )
            return exception_id

        def result(
            objective_id: str,
            rating: TestResultRating,
            *,
            design: bool,
            operating: bool,
            record_ids: list[str],
            exception_ids: list[str] | None = None,
            rationale: str,
        ) -> None:
            procedure = self._procedure(objective_id)
            results.append(
                ControlTestResult(
                    result_id=f"result_{objective_id}",
                    control_objective_id=objective_id,
                    procedure_id=procedure.procedure_id,
                    population_id="population_eleventh_contract",
                    rating=rating,
                    design_effective=design,
                    operating_effective=operating,
                    evidence_record_ids=record_ids,
                    exception_ids=exception_ids or [],
                    rationale=rationale,
                )
            )

        result(
            "ctl_physical_support",
            TestResultRating.PASSED,
            design=True,
            operating=True,
            record_ids=[
                chapter.physical_forecast.forecast_id,
                chapter.authorization.authorization_id,
            ],
            rationale=(
                "The approval was limited to ten contracts against the initially supported "
                "100,000 MMBtu. Later support did not change that test."
            ),
        )
        override = (
            chapter.chapter_flags.get("accepted_cal_explanation", False)
            or chapter.outcome == EleventhOutcome.CALS_ANALYST
        )
        quantity_category = (
            ExceptionCategory.MANAGEMENT_OVERRIDE if override else ExceptionCategory.NONPERFORMANCE
        )
        quantity_exception = exception(
            "exc_authorization_quantity",
            "ctl_authorization_limit",
            quantity_category,
            (
                f"Execution and confirmation recorded {chapter.execution.quantity} contracts "
                f"against authorization for {chapter.authorization.maximum_quantity}."
            ),
            evidence[:4],
        )
        corrected = chapter.position.offset_trade is not None
        result(
            "ctl_authorization_limit",
            (TestResultRating.REMEDIATED_AFTER_DISCOVERY if corrected else TestResultRating.FAILED),
            design=False,
            operating=False,
            record_ids=evidence[:4],
            exception_ids=[quantity_exception],
            rationale=(
                "The quantity limit did not prevent an eleven-contract execution. "
                + (
                    "A later approved offset remediated exposure but not the original breach."
                    if corrected
                    else "The excess position was not offset."
                )
            ),
        )
        match_exception = exception(
            "exc_match_identified_quantity",
            "ctl_prompt_match",
            ExceptionCategory.CORRECTED_EXCEPTION if corrected else ExceptionCategory.ERROR,
            "The match identified the one-contract difference at reconciliation.",
            [
                chapter.order.order_id,
                chapter.execution.execution_id,
                chapter.confirmation.confirmation_id,
                reconciliation.reconciliation_id,
            ],
        )
        result(
            "ctl_prompt_match",
            TestResultRating.PASSED_WITH_EXCEPTION,
            design=True,
            operating=True,
            record_ids=[
                chapter.order.order_id,
                chapter.execution.execution_id,
                chapter.confirmation.confirmation_id,
                reconciliation.reconciliation_id,
            ],
            exception_ids=[match_exception],
            rationale="The detective match operated and preserved the quantity exception promptly.",
        )
        notification = chapter.notifications[0] if chapter.notifications else None
        if notification is None:
            escalation_exception = exception(
                "exc_escalation_missing",
                "ctl_exception_escalation",
                ExceptionCategory.NONPERFORMANCE,
                "No formal exception notification record exists.",
                [reconciliation.reconciliation_id],
            )
            result(
                "ctl_exception_escalation",
                TestResultRating.FAILED,
                design=True,
                operating=False,
                record_ids=[reconciliation.reconciliation_id],
                exception_ids=[escalation_exception],
                rationale=(
                    "The exception remained visible, but the formal escalation "
                    "control did not operate."
                ),
            )
        else:
            delay = notification.notified_at - reconciliation.prepared_at
            if delay > timedelta(hours=4):
                escalation_exception = exception(
                    "exc_escalation_late",
                    "ctl_exception_escalation",
                    ExceptionCategory.LATE_CONTROL,
                    f"Formal notification followed discovery by {delay}.",
                    [
                        reconciliation.reconciliation_id,
                        notification.communication_record_id,
                    ],
                )
                result(
                    "ctl_exception_escalation",
                    TestResultRating.PASSED_WITH_EXCEPTION,
                    design=True,
                    operating=False,
                    record_ids=[
                        reconciliation.reconciliation_id,
                        notification.communication_record_id,
                    ],
                    exception_ids=[escalation_exception],
                    rationale="Escalation occurred and was preserved, but not promptly.",
                )
            else:
                result(
                    "ctl_exception_escalation",
                    TestResultRating.PASSED,
                    design=True,
                    operating=True,
                    record_ids=[
                        reconciliation.reconciliation_id,
                        notification.communication_record_id,
                    ],
                    rationale="The formal notification was timely and linked to the exception.",
                )
        if chapter.position.offset_trade is None:
            result(
                "ctl_corrective_approval",
                TestResultRating.NOT_APPLICABLE,
                design=True,
                operating=True,
                record_ids=[reconciliation.reconciliation_id],
                rationale="No corrective trade occurred in the selected transaction.",
            )
        else:
            approval = chapter.approvals[0] if chapter.approvals else None
            offset = chapter.position.offset_trade
            if approval is None or approval.approved_at > offset.executed_at:
                correction_exception = exception(
                    "exc_corrective_approval",
                    "ctl_corrective_approval",
                    ExceptionCategory.NONPERFORMANCE,
                    "The corrective trade lacks valid prior approval.",
                    [offset.trade_id],
                )
                result(
                    "ctl_corrective_approval",
                    TestResultRating.FAILED,
                    design=True,
                    operating=False,
                    record_ids=[offset.trade_id],
                    exception_ids=[correction_exception],
                    rationale="Corrective approval did not precede execution.",
                )
            else:
                result(
                    "ctl_corrective_approval",
                    TestResultRating.PASSED,
                    design=True,
                    operating=True,
                    record_ids=[approval.approval_id, offset.trade_id],
                    rationale="Evelyn's linked approval preceded the one-contract offset.",
                )
        preserved_ids = [
            chapter.authorization.authorization_id,
            chapter.execution.execution_id,
            chapter.confirmation.confirmation_id,
            chapter.blotter.blotter_id,
        ]
        result(
            "ctl_record_preservation",
            TestResultRating.PASSED,
            design=True,
            operating=True,
            record_ids=preserved_ids,
            rationale=(
                "Original records and blotter status history remain present after disposition."
            ),
        )
        certification_record_id = reconciliation.certification_record_id
        result(
            "ctl_certification_accuracy",
            (
                TestResultRating.PASSED_WITH_EXCEPTION
                if certification_record_id
                else TestResultRating.NOT_APPLICABLE
            ),
            design=True,
            operating=True,
            record_ids=[certification_record_id or reconciliation.reconciliation_id],
            exception_ids=(
                [
                    exception(
                        "exc_certified_open_exception",
                        "ctl_certification_accuracy",
                        ExceptionCategory.DOCUMENTATION_GAP,
                        "Certification described an exception that remained unresolved.",
                        [certification_record_id, reconciliation.reconciliation_id],
                    )
                ]
                if certification_record_id
                else []
            ),
            rationale=(
                "The certification retained the unresolved status rather than marking it matched."
                if certification_record_id
                else "No separate reconciliation certification occurred."
            ),
        )
        people = {
            chapter.execution.transmitting_user_id,
            chapter.authorization.approver_id,
            reconciliation.prepared_by_id,
        }
        separated = len(people) == 3
        if separated:
            result(
                "ctl_segregation",
                TestResultRating.PASSED,
                design=True,
                operating=True,
                record_ids=evidence,
                rationale="Cal transmitted, Evelyn approved, and the analyst reconciled.",
            )
        else:
            segregation_exception = exception(
                "exc_segregation",
                "ctl_segregation",
                ExceptionCategory.CONTROL_DESIGN_WEAKNESS,
                "Incompatible trade lifecycle responsibilities were assigned to one person.",
                evidence,
            )
            result(
                "ctl_segregation",
                TestResultRating.FAILED,
                design=False,
                operating=False,
                record_ids=evidence,
                exception_ids=[segregation_exception],
                rationale="The selected lifecycle lacks independent roles.",
            )
        if audit.audit_flags.get("walkthrough_contradiction"):
            exception(
                "exc_inaccurate_walkthrough",
                "ctl_certification_accuracy",
                ExceptionCategory.INACCURATE_STATEMENT,
                "The player claimed the process was followed although the records show otherwise.",
                evidence,
            )
        audit.exceptions = exceptions
        audit.control_results = results
        audit.audit_flags["records_independently_selected_for_testing"] = True
        audit.current_stage = AuditStage.PRELIMINARY_FINDINGS
        audit.current_scene_index = 0
        return results

    def prepare_findings(self, state: GameState) -> list[Finding]:
        audit = self._audit(state)
        if audit.findings:
            return audit.findings
        chapter = self._chapter(state)
        findings: list[Finding] = []
        quantity = self._exception(audit, "exc_authorization_quantity")
        quantity_severity = self._quantity_severity(state)
        findings.append(
            Finding(
                finding_id="finding_authorization_and_release",
                title="Execution exceeded contemporaneous quantity authorization",
                severity=quantity_severity,
                exception_ids=[quantity.exception_id],
                evidence_record_ids=list(quantity.evidence_record_ids),
                rationale=(
                    "The control allowed eleven confirmed contracts against a ten-contract "
                    "authorization. Profit or loss is not a severity input. "
                    + (
                        "The approved offset reduced residual exposure."
                        if chapter.position.offset_trade
                        else "The excess quantity was not offset."
                    )
                ),
            )
        )
        escalation = next(
            (
                item
                for item in audit.exceptions
                if item.exception_id in {"exc_escalation_missing", "exc_escalation_late"}
            ),
            None,
        )
        if escalation is not None:
            findings.append(
                Finding(
                    finding_id="finding_exception_escalation",
                    title=(
                        "Quantity exception was not formally escalated"
                        if escalation.exception_id == "exc_escalation_missing"
                        else "Quantity exception was escalated after discovery"
                    ),
                    severity=(
                        FindingSeverity.MODERATE
                        if escalation.exception_id == "exc_escalation_missing"
                        else FindingSeverity.ADVISORY
                    ),
                    exception_ids=[escalation.exception_id],
                    evidence_record_ids=list(escalation.evidence_record_ids),
                    rationale=escalation.description,
                )
            )
        inaccurate = next(
            (
                item
                for item in audit.exceptions
                if item.exception_id == "exc_inaccurate_walkthrough"
            ),
            None,
        )
        if inaccurate is not None:
            findings.append(
                Finding(
                    finding_id="finding_inconsistent_walkthrough",
                    title="Walkthrough explanation conflicted with contemporaneous records",
                    severity=FindingSeverity.HIGH,
                    exception_ids=[inaccurate.exception_id],
                    evidence_record_ids=list(inaccurate.evidence_record_ids),
                    rationale=(
                        "The inconsistency concerns the known authorization and quantity, "
                        "not memory of an ambiguous detail."
                    ),
                )
            )
        audit.findings = findings
        audit.current_stage = AuditStage.MANAGEMENT_RESPONSE
        audit.current_scene_index = 0
        return findings

    def prepare_management_response(
        self,
        state: GameState,
    ) -> tuple[list[ManagementResponse], RemediationRecommendation]:
        audit = self._audit(state)
        if audit.management_responses and audit.remediations:
            return audit.management_responses, audit.remediations[0]
        if not audit.findings:
            raise ValueError("prepare preliminary findings before management response")
        kind = audit.remediation_kind or RemediationKind.DAILY_SUPERVISORY_REVIEW
        agreement = audit.response_agreement or ResponseAgreement.AGREE
        action, owner, days, interim, residual = self._remediation_terms(kind)
        finding_ids = [item.finding_id for item in audit.findings]
        recommendation = RemediationRecommendation(
            remediation_id=f"remediation_{kind.value}",
            finding_ids=finding_ids,
            kind=kind,
            proposed_action=action,
            owner=owner,
            target_date=self.scenario.day_dates["day_4"] + timedelta(days=days),
            interim_control=interim,
            residual_risk=residual,
            approved=True,
        )
        root_cause = self._root_cause(state, kind)
        supporting_disagreement = (
            self._disagreement_evidence(state) if agreement != ResponseAgreement.AGREE else []
        )
        responses = []
        for index, finding in enumerate(audit.findings, start=1):
            response = ManagementResponse(
                response_id=f"management_response_{index:02d}",
                finding_id=finding.finding_id,
                agreement=agreement,
                disagreement_evidence_ids=supporting_disagreement,
                root_cause=root_cause,
                proposed_action=action,
                owner=owner,
                target_date=recommendation.target_date,
                interim_control=interim,
                residual_risk=residual,
                status=(
                    FindingStatus.RISK_ACCEPTED
                    if kind == RemediationKind.FORMAL_RISK_ACCEPTANCE
                    else FindingStatus.REMEDIATION_PLANNED
                ),
            )
            responses.append(response)
            finding.status = response.status
        if agreement == ResponseAgreement.DISAGREE:
            audit.audit_flags["unsupported_management_disagreement"] = True
        audit.remediations = [recommendation]
        audit.management_responses = responses
        audit.audit_flags["player_included_in_remediation"] = audit.relationships.get(
            "noah_shah", 0
        ) > 0 and audit.relationships.get("evelyn_marsh", 0) >= audit.beginning_relationships.get(
            "evelyn_marsh", 0
        )
        audit.current_stage = AuditStage.BEFORE_EXIT
        audit.current_scene_index = 0
        return responses, recommendation

    def complete(self, state: GameState) -> AuditOutcome:
        audit = self._audit(state)
        if not audit.management_responses:
            raise ValueError("management response is required before the exit meeting")
        outcome = self._derive_outcome(state)
        audit.outcome = outcome
        external_interest = {
            AuditOutcome.NO_SURPRISES: "potential_buyer_diligence",
            AuditOutcome.CLEAN_WALKTHROUGH: "lender_diligence",
            AuditOutcome.CONTROL_WORKED_LATE: "lender_diligence",
            AuditOutcome.POLICY_IS_NOT_A_CONTROL: "board_committee",
            AuditOutcome.QUIET_FILE_OPENS: "board_committee",
            AuditOutcome.MANAGEMENT_OVERRIDE: "board_committee",
            AuditOutcome.TWO_VERSIONS_OF_MONDAY: "board_committee",
        }[outcome]
        audit.audit_flags[f"final_report_requested_by_{external_interest}"] = True
        audit.current_stage = AuditStage.COMPLETE
        audit.completed = True
        audit.current_scene_index = 0
        state.current_date = self.scenario.day_dates["day_4"]
        state.record(
            phase="system",
            event_type="internal_audit_completed",
            source_id=audit.engagement.engagement_id,
            message=f"Internal Audit Walkthrough Report outcome: {outcome.value}.",
            changes={"outcome": outcome.value},
        )
        return outcome

    def population(self, state: GameState) -> PopulationReference:
        chapter = self._chapter(state)
        return PopulationReference(
            population_id="population_eleventh_contract",
            transaction_reference=chapter.scenario_id,
            record_ids=[
                chapter.authorization.authorization_id,
                chapter.order.order_id,
                chapter.execution.execution_id,
                chapter.confirmation.confirmation_id,
                chapter.reconciliation.reconciliation_id,
            ],
        )

    def available_records(self, state: GameState) -> dict[str, ResolvedRecord]:
        chapter = self._chapter(state)
        communications = {item.record_id: item for item in state.evidence_log}
        journal_ids = {item.transaction_id for item in state.ledger.entries}
        offset = chapter.position.offset_trade
        approval = chapter.approvals[0] if chapter.approvals else None
        support_id = "final_nomination_additional_10000"
        return {
            chapter.physical_forecast.forecast_id: ResolvedRecord(
                chapter.physical_forecast.forecast_id,
                "PhysicalForecastRecord",
                True,
                None,
                True,
            ),
            chapter.market_brief.brief_id: ResolvedRecord(
                chapter.market_brief.brief_id,
                "MarketBrief",
                True,
                chapter.market_brief.created_at,
                True,
            ),
            chapter.recommendation.recommendation_id: ResolvedRecord(
                chapter.recommendation.recommendation_id,
                "OrderRecommendation",
                True,
                chapter.recommendation.recommended_at,
                True,
            ),
            chapter.authorization.authorization_id: ResolvedRecord(
                chapter.authorization.authorization_id,
                "TradeAuthorization",
                True,
                chapter.authorization.approved_at,
                True,
            ),
            chapter.order.order_id: ResolvedRecord(
                chapter.order.order_id,
                "TradeOrder",
                True,
                chapter.order.submitted_at,
                True,
            ),
            chapter.execution.execution_id: ResolvedRecord(
                chapter.execution.execution_id,
                "ExecutionRecord",
                True,
                chapter.execution.fill_timestamp,
                True,
            ),
            chapter.confirmation.confirmation_id: ResolvedRecord(
                chapter.confirmation.confirmation_id,
                "FCMConfirmation",
                True,
                chapter.confirmation.confirmed_at,
                True,
            ),
            chapter.blotter.blotter_id: ResolvedRecord(
                chapter.blotter.blotter_id,
                "TradeBlotterEntry",
                True,
                chapter.blotter.status_history[0].changed_at,
                True,
            ),
            "txn_eleventh_initial_margin": ResolvedRecord(
                "txn_eleventh_initial_margin",
                "JournalEntry",
                "txn_eleventh_initial_margin" in journal_ids,
                None,
                True,
            ),
            chapter.reconciliation.reconciliation_id: ResolvedRecord(
                chapter.reconciliation.reconciliation_id,
                "TradeReconciliationRecord",
                True,
                chapter.reconciliation.prepared_at,
                True,
            ),
            "comm_ec_formal_exception": ResolvedRecord(
                "comm_ec_formal_exception",
                "CommunicationRecord",
                "comm_ec_formal_exception" in communications,
                (
                    communications["comm_ec_formal_exception"].timestamp
                    if "comm_ec_formal_exception" in communications
                    else None
                ),
                True,
            ),
            "approval_offset_eleventh_contract": ResolvedRecord(
                "approval_offset_eleventh_contract",
                "CorrectiveTradeApprovalRecord",
                approval is not None,
                approval.approved_at if approval else None,
                True,
            ),
            "offset_eleventh_contract": ResolvedRecord(
                "offset_eleventh_contract",
                "OffsetTrade",
                offset is not None,
                offset.executed_at if offset else None,
                True,
            ),
            support_id: ResolvedRecord(
                support_id,
                "PhysicalSupportDocument",
                support_id in chapter.physical_forecast.support_document_ids,
                chapter.physical_forecast.support_obtained_at,
                False,
            ),
            "comm_eleventh_market_brief": ResolvedRecord(
                "comm_eleventh_market_brief",
                "CommunicationRecord",
                "comm_eleventh_market_brief" in communications,
                (
                    communications["comm_eleventh_market_brief"].timestamp
                    if "comm_eleventh_market_brief" in communications
                    else None
                ),
                True,
            ),
            "analyst_case_file_eleventh_contract": ResolvedRecord(
                "analyst_case_file_eleventh_contract",
                "AnalystCaseFile",
                chapter.completed,
                None,
                False,
            ),
        }

    def _resolve_request_item(
        self,
        state: GameState,
        template: RequestedItem,
    ) -> RequestedItem:
        resolved = self.available_records(state).get(template.stable_record_id)
        if resolved is None:
            raise ValueError(f"audit request references unknown record {template.stable_record_id}")
        return template.model_copy(
            deep=True,
            update={
                "available": resolved.available,
                "date_created": resolved.created_at,
                "contemporaneous": resolved.contemporaneous,
                "response_status": "pending" if resolved.available else "missing",
            },
        )

    def _additional_linked_record_ids(self, state: GameState) -> list[str]:
        chapter = self._chapter(state)
        requested = {
            item.stable_record_id for item in self._audit(state).evidence_request.requested_items
        }
        records = [
            *chapter.communication_record_ids,
            *chapter.notification_record_ids,
            *chapter.approval_ids,
            *chapter.position.journal_transaction_ids,
        ]
        return list(dict.fromkeys(item for item in records if item not in requested))

    def _communication_alignment(self, state: GameState) -> str:
        chapter = self._chapter(state)
        records = [
            item
            for item in state.evidence_log
            if item.record_id in chapter.communication_record_ids
        ]
        limited = [item.record_id for item in records if item.accuracy.value != "accurate"]
        if limited:
            return f"These communications require qualification: {', '.join(limited)}."
        return "Preserved contemporaneous communications agree with the record-based chronology."

    def _quantity_severity(self, state: GameState) -> FindingSeverity:
        audit = self._audit(state)
        chapter = self._chapter(state)
        override = any(
            item.category == ExceptionCategory.MANAGEMENT_OVERRIDE for item in audit.exceptions
        )
        inaccurate = audit.audit_flags.get("walkthrough_contradiction", False)
        unresolved = chapter.position.offset_trade is None
        missing_escalation = any(
            item.exception_id == "exc_escalation_missing" for item in audit.exceptions
        )
        if override and inaccurate and unresolved:
            return FindingSeverity.CRITICAL
        if override or inaccurate or (unresolved and missing_escalation):
            return FindingSeverity.HIGH
        if unresolved:
            return FindingSeverity.MODERATE
        return FindingSeverity.MODERATE

    def _root_cause(
        self,
        state: GameState,
        kind: RemediationKind,
    ) -> RootCauseCategory:
        audit = self._audit(state)
        if any(item.category == ExceptionCategory.MANAGEMENT_OVERRIDE for item in audit.exceptions):
            return RootCauseCategory.MANAGEMENT_OVERRIDE
        if kind == RemediationKind.AUTOMATED_THREE_WAY_MATCH:
            return RootCauseCategory.SYSTEM_INTEGRATION_GAP
        if any(
            item.control_objective_id == "ctl_exception_escalation" for item in audit.exceptions
        ):
            return RootCauseCategory.UNTIMELY_ESCALATION
        if self._chapter(state).physical_forecast.outcome == PhysicalVolumeOutcome.ARRIVES:
            return RootCauseCategory.INCOMPLETE_PHYSICAL_INFORMATION
        return RootCauseCategory.MANUAL_PROCESS_ERROR

    def _remediation_terms(
        self,
        kind: RemediationKind,
    ) -> tuple[str, RemediationOwner, int, str, str]:
        controller = RemediationOwner(
            owner_id="rem_owner_controller",
            person_id="evelyn_marsh",
            role="Controller",
        )
        executive = RemediationOwner(
            owner_id="rem_owner_executive",
            person_id="vince_rourke",
            role="Executive sponsor",
        )
        terms = {
            RemediationKind.AUTOMATED_THREE_WAY_MATCH: (
                "Implement an authorization–execution–FCM confirmation match that routes "
                "quantity exceptions and blocks clean certification.",
                executive,
                120,
                "Daily controller review until the match is deployed.",
                "Implementation effort and desk resistance leave temporary manual-process risk.",
            ),
            RemediationKind.DAILY_SUPERVISORY_REVIEW: (
                "Require documented daily supervisory review of positions, approvals, "
                "confirmations, and open exceptions.",
                controller,
                30,
                "Controller signs the existing daily blotter beginning immediately.",
                "Human timeliness and reviewer capacity remain residual risks.",
            ),
            RemediationKind.PHYSICAL_SUPPORT_GATE: (
                "Block hedge quantity above supported physical volume unless a second "
                "documented approver authorizes the incremental exposure.",
                executive,
                75,
                "Controller manually verifies support before every order release.",
                "The gate may slow legitimate rapid commercial response.",
            ),
            RemediationKind.TRAINING_AND_POLICY: (
                "Revise the procedure and train the commercial, scheduling, and finance teams.",
                controller,
                45,
                "Distribute a written reminder at the next desk meeting.",
                "No new preventive or detective mechanism addresses the design gap.",
            ),
            RemediationKind.FORMAL_RISK_ACCEPTANCE: (
                "Document temporary residual-risk acceptance with an expiration and "
                "required reassessment.",
                executive,
                60,
                "Controller performs daily review during the acceptance period.",
                "The authorization-release gap remains until acceptance expires or is remediated.",
            ),
        }
        return terms[kind]

    def _disagreement_evidence(self, state: GameState) -> list[str]:
        chapter = self._chapter(state)
        evidence = []
        if chapter.position.offset_trade:
            evidence.append(chapter.position.offset_trade.trade_id)
        evidence.extend(chapter.physical_forecast.support_document_ids)
        return evidence or [chapter.reconciliation.reconciliation_id]

    def _derive_outcome(self, state: GameState) -> AuditOutcome:
        audit = self._audit(state)
        chapter = self._chapter(state)
        if audit.audit_flags.get("walkthrough_contradiction") or audit.audit_flags.get(
            "unsupported_management_disagreement"
        ):
            return AuditOutcome.TWO_VERSIONS_OF_MONDAY
        if chapter.outcome == EleventhOutcome.QUIET_FILE and audit.audit_flags.get(
            "supplemental_evidence_provided"
        ):
            return AuditOutcome.QUIET_FILE_OPENS
        if any(item.category == ExceptionCategory.MANAGEMENT_OVERRIDE for item in audit.exceptions):
            return AuditOutcome.MANAGEMENT_OVERRIDE
        if audit.remediation_kind == RemediationKind.TRAINING_AND_POLICY:
            return AuditOutcome.POLICY_IS_NOT_A_CONTROL
        if (
            audit.package_strategy == PackageStrategy.COMPLETE
            and audit.walkthrough_posture == WalkthroughPosture.ACCURATE
            and audit.response_agreement == ResponseAgreement.AGREE
            and audit.remediation_kind
            in {
                RemediationKind.AUTOMATED_THREE_WAY_MATCH,
                RemediationKind.PHYSICAL_SUPPORT_GATE,
            }
        ):
            return AuditOutcome.NO_SURPRISES
        if (
            audit.walkthrough_posture in {WalkthroughPosture.ACCURATE, WalkthroughPosture.UNCERTAIN}
            and audit.finding_posture is not None
            and audit.finding_posture.value != "unsupported_dispute"
        ):
            return AuditOutcome.CLEAN_WALKTHROUGH
        if chapter.position.offset_trade is not None:
            return AuditOutcome.CONTROL_WORKED_LATE
        return AuditOutcome.CLEAN_WALKTHROUGH

    def _procedure(self, objective_id: str):
        return next(
            item
            for item in self.scenario.test_procedures
            if item.control_objective_id == objective_id
        )

    @staticmethod
    def _exception(audit: NoSurprisesState, exception_id: str) -> AuditException:
        return next(item for item in audit.exceptions if item.exception_id == exception_id)

    def _at(self, day: int, hour: int, minute: int) -> datetime:
        return datetime.combine(
            self.scenario.day_dates[f"day_{day}"],
            time(hour, minute),
            tzinfo=CHICAGO_TZ,
        )

    @staticmethod
    def _audit(state: GameState) -> NoSurprisesState:
        if state.no_surprises is None:
            raise ValueError("No Surprises has not started")
        return state.no_surprises

    @staticmethod
    def _chapter(state: GameState):
        chapter = state.eleventh_contract
        if chapter is None or not chapter.completed:
            raise ValueError("completed Eleventh Contract state is required")
        required = (
            chapter.market_brief,
            chapter.recommendation,
            chapter.authorization,
            chapter.order,
            chapter.execution,
            chapter.confirmation,
            chapter.reconciliation,
            chapter.blotter,
            chapter.position,
        )
        if any(item is None for item in required):
            raise ValueError("Eleventh Contract record chain is incomplete")
        return chapter

    @staticmethod
    def _protected_records(state: GameState) -> dict[str, object]:
        chapter = state.eleventh_contract
        return {
            "chapter": chapter.model_dump(mode="json") if chapter else None,
            "evidence": [item.model_dump(mode="json") for item in state.evidence_log],
            "ledger": state.ledger.model_dump(mode="json"),
            "cash": (state.corporate_cash, state.personal_cash, state.margin_due),
        }

    @staticmethod
    def _assert_records_unchanged(
        state: GameState,
        protected: dict[str, object],
    ) -> None:
        if InternalAuditEngine._protected_records(state) != protected:
            raise RuntimeError("audit narrative choice changed preserved transaction records")
