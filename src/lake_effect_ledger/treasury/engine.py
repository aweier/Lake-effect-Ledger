"""Treasury crisis orchestration over the existing cash, ledger, and hedge state."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from lake_effect_ledger.accounting.models import JournalEntry, JournalLine
from lake_effect_ledger.commodity.engine import CommodityEngine
from lake_effect_ledger.commodity.models import money
from lake_effect_ledger.learning.models import TrajectoryTag
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.state import GameState
from lake_effect_ledger.treasury.models import (
    ApprovalRecord,
    BorrowingRequest,
    CommunicationRecord,
    CovenantResult,
    FundingChoice,
    FundingDecision,
    LiquiditySnapshot,
    NotificationChoice,
    ObligationStatus,
    RevolvingCreditState,
    ScheduledCashObligation,
    TreasuryOutcome,
    TreasuryState,
)

DEFAULT_TREASURY_SCENARIO_ID = "episode_01_two_oclock_call"


class TreasuryEngine:
    def __init__(
        self,
        content: ContentBundle,
        commodity_engine: CommodityEngine,
        scenario_id: str = DEFAULT_TREASURY_SCENARIO_ID,
    ) -> None:
        self.content = content
        self.commodity = commodity_engine
        self.scenario = content.treasury_scenario(scenario_id)

    def initialize_crisis(self, state: GameState) -> TreasuryState:
        if state.treasury is not None:
            return state.treasury
        book = state.hedge_book
        if book is None:
            raise ValueError("the treasury crisis requires an open Hedge Book")
        if book.next_settlement_index < self.scenario.trigger_settlement_day:
            raise ValueError("the treasury crisis has not reached its trigger day")
        call = (
            next(item for item in book.margin.calls if item.call_id == book.pending_margin_call_id)
            if book.pending_margin_call_id is not None
            else None
        )
        facility = self.scenario.facility
        started_at = self.scenario.margin_deadline.replace(hour=9, minute=15)
        treasury = TreasuryState(
            scenario_id=self.scenario.id,
            started_at=started_at,
            margin_deadline=self.scenario.margin_deadline,
            beginning_operating_cash=state.corporate_cash,
            beginning_fcm_margin_cash=book.margin.balance,
            beginning_ledger_entry_count=len(state.ledger.entries),
            margin_call_id=call.call_id if call is not None else None,
            original_margin_call_amount=(
                call.required_amount if call is not None else Decimal("0")
            ),
            obligations=[
                ScheduledCashObligation(
                    id=item.id,
                    payee=item.payee,
                    description=item.description,
                    amount=item.amount,
                    due_date=item.due_date,
                    priority=item.priority,
                    protected=item.protected,
                    journal_pattern_id=item.journal_pattern_id,
                )
                for item in self.scenario.obligations
            ],
            facility=RevolvingCreditState(
                facility_id=facility.id,
                lender_name=facility.lender_name,
                commitment=facility.commitment,
                beginning_outstanding=facility.beginning_outstanding,
                outstanding=facility.beginning_outstanding,
                annual_interest_rate=facility.annual_interest_rate,
                minimum_draw_increment=facility.minimum_draw_increment,
                covenant_minimum_available_liquidity=(
                    facility.covenant_minimum_available_liquidity
                ),
                maturity_date=facility.maturity_date,
            ),
        )
        state.treasury = treasury
        for objective in self.scenario.learning_objectives:
            if objective not in state.learning_objectives:
                state.learning_objectives.append(objective)
        self._capture_snapshot(state, started_at, "Call received")
        state.record(
            phase="system",
            event_type="treasury_crisis_started",
            source_id=self.scenario.id,
            message=self.scenario.crisis_title,
            changes={
                "margin_call": str(treasury.original_margin_call_amount),
                "deadline": treasury.margin_deadline.isoformat(),
                "protected_obligations": str(treasury.remaining_protected_obligations),
                "available_liquidity": str(treasury.liquidity_snapshots[-1].available_liquidity),
            },
        )
        return treasury

    def record_notification(
        self,
        state: GameState,
        choice: NotificationChoice | str,
    ) -> CommunicationRecord:
        treasury = self._require_treasury(state)
        if treasury.notification_choice is not None:
            raise ValueError("the treasury notification decision is already recorded")
        selected = NotificationChoice(choice)
        definition = next(
            item for item in self.scenario.notification_options if item.id == selected
        )
        record = CommunicationRecord(
            record_id=f"communication_{selected.value}",
            timestamp=definition.timestamp,
            channel=definition.channel,
            sender_id=definition.sender_id,
            recipient_ids=list(definition.recipient_ids),
            subject=definition.subject,
            body_summary=definition.body_summary,
            accuracy=definition.accuracy,
            linked_decision_ids=[f"notification_{selected.value}"],
        )
        state.evidence_log.append(record)
        treasury.notification_choice = selected
        treasury.communication_record_id = record.record_id
        required = set(self.scenario.facility.required_approver_ids)
        approved_by = sorted(required) if definition.grants_facility_approval else []
        treasury.approval = ApprovalRecord(
            approval_id=f"approval_{selected.value}",
            timestamp=definition.timestamp + timedelta(minutes=4),
            decision_id=f"notification_{selected.value}",
            requested_from_ids=sorted(required & set(definition.recipient_ids)),
            approved_by_ids=approved_by,
            approved=definition.grants_facility_approval,
        )
        for resource_name, amount in definition.resource_deltas.items():
            self._change_resource(state, resource_name, amount, record.record_id)
        notification_tags = {
            NotificationChoice.NOTIFY_IMMEDIATELY: (
                TrajectoryTag.PRINCIPLED,
                TrajectoryTag.COOPERATIVE,
            ),
            NotificationChoice.NOTIFY_CAL_ONLY: (
                TrajectoryTag.COMPANY_LOYAL,
                TrajectoryTag.SELF_PROTECTIVE,
                TrajectoryTag.AMBITIOUS,
            ),
            NotificationChoice.SEND_VAGUE_UPDATE: (
                TrajectoryTag.CONFLICTED,
                TrajectoryTag.SELF_PROTECTIVE,
            ),
            NotificationChoice.DELAY_NOTIFICATION: (
                TrajectoryTag.SELF_PROTECTIVE,
                TrajectoryTag.CONFLICTED,
            ),
        }
        for tag in notification_tags[selected]:
            state.career_trajectory.record(f"notification_{selected.value}", tag, 1)
        state.record(
            phase="decision",
            event_type="treasury_notification",
            source_id=record.record_id,
            message=definition.narrative,
            changes={
                "choice": selected.value,
                "timestamp": definition.timestamp.isoformat(),
                "recipients": list(definition.recipient_ids),
                "accuracy": definition.accuracy.value,
                "facility_approved": definition.grants_facility_approval,
            },
        )
        return record

    def feasible_funding_choices(self, state: GameState) -> list[FundingChoice]:
        treasury = self._require_treasury(state)
        if treasury.notification_choice is None:
            return []
        if treasury.funding_decision is not None:
            return []
        call_amount = treasury.original_margin_call_amount
        choices: list[FundingChoice] = []
        if state.corporate_cash >= call_amount:
            choices.append(FundingChoice.OPERATING_CASH)
        approved = treasury.approval is not None and treasury.approval.approved
        if (
            approved
            and self.scenario.facility.default_draw_amount <= treasury.facility.undrawn_availability
        ):
            choices.append(FundingChoice.REVOLVER)
        book = state.hedge_book
        if (
            call_amount > 0
            and book is not None
            and book.pending_margin_call_id is not None
            and book.position is not None
            and book.position.contracts > 0
        ):
            choices.append(FundingChoice.REDUCE_POSITION)
            choices.append(FundingChoice.MISS_CALL)
        return choices

    def resolve_funding(
        self,
        state: GameState,
        choice: FundingChoice | str,
        *,
        draw_amount: Decimal | None = None,
        reduce_contracts: int | None = None,
    ) -> FundingDecision:
        treasury = self._require_treasury(state)
        if treasury.funding_decision is not None:
            raise ValueError("the treasury funding decision is already complete")
        selected = FundingChoice(choice)
        feasible = self.feasible_funding_choices(state)
        if selected not in feasible:
            valid = ", ".join(item.value for item in feasible) or "none"
            raise ValueError(f"funding choice {selected.value} is not feasible; available: {valid}")
        communication = next(
            item
            for item in state.evidence_log
            if item.record_id == treasury.communication_record_id
        )
        timestamp = max(
            treasury.started_at + timedelta(minutes=25),
            communication.timestamp,
        )
        before_transaction_ids = {item.transaction_id for item in state.ledger.entries}
        funded = Decimal("0")
        draw = Decimal("0")
        contracts_reduced = 0
        margin_released = Decimal("0")
        revised_call = treasury.original_margin_call_amount
        missed = False

        if selected == FundingChoice.REVOLVER:
            draw = money(draw_amount or self.scenario.facility.default_draw_amount)
            self._validate_draw(treasury, draw)
            approved_by = treasury.approval.approved_by_ids if treasury.approval else []
            request = BorrowingRequest(
                request_id="borrowing_request_margin_call",
                timestamp=timestamp,
                amount=draw,
                requested_by_id="player",
                approver_ids=list(approved_by),
                approved=True,
                journal_transaction_id="txn_treasury_revolver_draw",
            )
            state.corporate_cash = money(state.corporate_cash + draw)
            treasury.facility = treasury.facility.model_copy(
                update={
                    "outstanding": money(treasury.facility.outstanding + draw),
                    "total_draws": money(treasury.facility.total_draws + draw),
                }
            )
            self._post_pattern(
                state,
                pattern_id=self.scenario.journal_patterns["revolver_draw"],
                amount=draw,
                transaction_id="txn_treasury_revolver_draw",
                description=f"Draw {treasury.facility.facility_id} for margin liquidity",
                source_id=request.request_id,
            )
            treasury.borrowing_request = request
            if treasury.margin_call_id is not None:
                funded = self.commodity.fund_pending_margin_call(state)
                revised_call = Decimal("0")
        elif selected == FundingChoice.OPERATING_CASH:
            if treasury.margin_call_id is not None:
                funded = self.commodity.fund_pending_margin_call(state)
            revised_call = Decimal("0")
        elif selected == FundingChoice.REDUCE_POSITION:
            count = reduce_contracts or self.scenario.default_reduction_contracts
            trade = self.commodity.reduce_position(state, count)
            contracts_reduced = trade.contracts_closed
            margin_released = trade.margin_released
            revised_call = trade.revised_margin_call
            if revised_call:
                funded = self.commodity.fund_pending_margin_call(state)
                revised_call = Decimal("0")
        elif selected == FundingChoice.MISS_CALL:
            trade = self.commodity.miss_pending_margin_call(state)
            contracts_reduced = trade.contracts_closed
            margin_released = trade.margin_released
            revised_call = treasury.original_margin_call_amount
            missed = True

        decision = FundingDecision(
            decision_id=f"funding_{selected.value}",
            timestamp=timestamp,
            choice=selected,
            margin_call_id=treasury.margin_call_id,
            original_call_amount=treasury.original_margin_call_amount,
            funded_amount=funded,
            revolver_draw_amount=draw,
            contracts_reduced=contracts_reduced,
            margin_released=margin_released,
            revised_call_amount=revised_call,
            missed=missed,
        )
        treasury.funding_decision = decision
        funding_tags = {
            FundingChoice.OPERATING_CASH: (TrajectoryTag.COMPANY_LOYAL,),
            FundingChoice.REVOLVER: (
                TrajectoryTag.PRINCIPLED,
                TrajectoryTag.COOPERATIVE,
            ),
            FundingChoice.REDUCE_POSITION: (
                TrajectoryTag.SELF_PROTECTIVE,
                TrajectoryTag.CONFLICTED,
            ),
            FundingChoice.MISS_CALL: (
                TrajectoryTag.SELF_PROTECTIVE,
                TrajectoryTag.CONFLICTED,
            ),
        }
        for tag in funding_tags[selected]:
            state.career_trajectory.record(decision.decision_id, tag, 1)
        treasury.projected_lowest_cash = money(
            state.corporate_cash - treasury.remaining_protected_obligations
        )
        self._capture_snapshot(state, timestamp, f"Funding decision: {selected.value}")
        new_transaction_ids = [
            item.transaction_id
            for item in state.ledger.entries
            if item.transaction_id not in before_transaction_ids
        ]
        self._link_evidence(state, decision.decision_id, new_transaction_ids)
        state.record(
            phase="decision",
            event_type="treasury_funding",
            source_id=decision.decision_id,
            message=f"Treasury funding decision: {selected.value}.",
            changes={
                "call_funded": str(funded),
                "revolver_draw": str(draw),
                "contracts_reduced": contracts_reduced,
                "margin_released": str(margin_released),
                "projected_lowest_cash": str(treasury.projected_lowest_cash),
            },
        )
        self.assert_treasury_reconciles(state)
        return decision

    def finalize(self, state: GameState) -> TreasuryState:
        treasury = self._require_treasury(state)
        if treasury.completed:
            return treasury
        if treasury.funding_decision is None:
            raise ValueError("resolve treasury funding before finalization")
        book = state.hedge_book
        if book is None or not book.completed:
            raise ValueError("finish the market path before treasury finalization")

        self._accrue_interest(state)
        self._pay_due_obligations(state)
        tested_at = treasury.margin_deadline + timedelta(days=3)
        available = self.available_liquidity(state)
        treasury.covenant_result = CovenantResult(
            tested_at=tested_at,
            available_liquidity=available,
            minimum_required=treasury.facility.covenant_minimum_available_liquidity,
            passed=available >= treasury.facility.covenant_minimum_available_liquidity,
        )
        self._capture_snapshot(state, tested_at, "Scenario close")
        treasury.outcome = self._derive_outcome(state)
        treasury.completed = True
        self._link_evidence(
            state,
            f"outcome_{treasury.outcome.value}",
            list(treasury.journal_transaction_ids),
        )
        state.record(
            phase="system",
            event_type="treasury_crisis_completed",
            source_id=treasury.scenario_id,
            message=f"Treasury outcome: {treasury.outcome.value}.",
            changes={
                "outcome": treasury.outcome.value,
                "ending_cash": str(state.corporate_cash),
                "ending_debt": str(treasury.facility.outstanding),
                "accrued_interest": str(treasury.facility.accrued_interest),
                "covenant_passed": treasury.covenant_result.passed,
            },
        )
        self.assert_treasury_reconciles(state)
        return treasury

    def available_liquidity(self, state: GameState) -> Decimal:
        treasury = self._require_treasury(state)
        return money(
            state.corporate_cash
            + treasury.facility.undrawn_availability
            - treasury.remaining_protected_obligations
        )

    def assert_treasury_reconciles(self, state: GameState) -> None:
        treasury = self._require_treasury(state)
        self.commodity.assert_cash_and_margin_reconcile(state)
        activity = state.ledger.account_activity()
        debt_debits, debt_credits = activity.get("2300", (Decimal("0"), Decimal("0")))
        ledger_debt = money(debt_credits - debt_debits)
        if ledger_debt != money(treasury.facility.outstanding):
            raise ValueError(
                f"revolver debt does not reconcile: ledger {ledger_debt}, "
                f"state {treasury.facility.outstanding}"
            )
        interest_debits, interest_credits = activity.get("2150", (Decimal("0"), Decimal("0")))
        ledger_accrued_interest = money(interest_credits - interest_debits)
        if ledger_accrued_interest != money(treasury.facility.accrued_interest):
            raise ValueError(
                "accrued interest does not reconcile: "
                f"ledger {ledger_accrued_interest}, "
                f"state {treasury.facility.accrued_interest}"
            )

    def _accrue_interest(self, state: GameState) -> None:
        treasury = self._require_treasury(state)
        if treasury.facility.outstanding == 0:
            return
        interest = money(
            treasury.facility.outstanding
            * treasury.facility.annual_interest_rate
            * Decimal(self.scenario.facility.interest_accrual_days)
            / Decimal("365")
        )
        treasury.facility = treasury.facility.model_copy(update={"accrued_interest": interest})
        self._post_pattern(
            state,
            pattern_id=self.scenario.journal_patterns["interest_accrual"],
            amount=interest,
            transaction_id="txn_treasury_interest_accrual",
            description=(
                f"Accrue {self.scenario.facility.interest_accrual_days} days of revolver interest"
            ),
            source_id=treasury.facility.facility_id,
        )

    def _pay_due_obligations(self, state: GameState) -> None:
        treasury = self._require_treasury(state)
        priority_order = {"critical": 0, "protected": 1, "discretionary": 2}
        for obligation in sorted(
            treasury.obligations,
            key=lambda item: (
                priority_order[item.priority.value],
                item.due_date,
                item.id,
            ),
        ):
            if obligation.due_date > state.current_date:
                continue
            if state.corporate_cash >= obligation.amount:
                transaction_id = f"txn_obligation_{obligation.id}"
                state.corporate_cash = money(state.corporate_cash - obligation.amount)
                self._post_pattern(
                    state,
                    pattern_id=obligation.journal_pattern_id,
                    amount=obligation.amount,
                    transaction_id=transaction_id,
                    description=f"Pay {obligation.description}",
                    source_id=obligation.id,
                )
                obligation.status = ObligationStatus.PAID
                obligation.paid_date = state.current_date
                obligation.journal_transaction_id = transaction_id
            else:
                obligation.status = ObligationStatus.OVERDUE

    def _capture_snapshot(self, state: GameState, timestamp, label: str) -> None:
        treasury = self._require_treasury(state)
        treasury.liquidity_snapshots.append(
            LiquiditySnapshot(
                timestamp=timestamp,
                label=label,
                operating_cash=state.corporate_cash,
                fcm_margin_cash=(
                    state.hedge_book.margin.balance if state.hedge_book is not None else 0
                ),
                undrawn_revolver=treasury.facility.undrawn_availability,
                protected_obligations=treasury.remaining_protected_obligations,
                available_liquidity=self.available_liquidity(state),
            )
        )

    def _post_pattern(
        self,
        state: GameState,
        *,
        pattern_id: str,
        amount: Decimal,
        transaction_id: str,
        description: str,
        source_id: str,
    ) -> None:
        if amount <= 0:
            raise ValueError("treasury journal amount must be positive")
        pattern = self.content.journal_pattern(pattern_id)
        entry = JournalEntry(
            transaction_id=transaction_id,
            entry_date=state.current_date,
            description=description,
            source_id=source_id,
            lines=[
                JournalLine(account=pattern.debit_account, debit=money(amount)),
                JournalLine(account=pattern.credit_account, credit=money(amount)),
            ],
        )
        state.ledger.post(entry, self.content.valid_accounts)
        treasury = self._require_treasury(state)
        treasury.journal_transaction_ids.append(transaction_id)
        state.record(
            phase="system",
            event_type="treasury_journal_posted",
            source_id=source_id,
            message=description,
            changes={
                "transaction_id": transaction_id,
                "amount": str(amount),
                "pattern": pattern_id,
            },
        )

    def _validate_draw(self, treasury: TreasuryState, amount: Decimal) -> None:
        if amount <= 0:
            raise ValueError("revolver draw must be positive")
        if amount > treasury.facility.undrawn_availability:
            raise ValueError("revolver draw exceeds undrawn availability")
        if amount % treasury.facility.minimum_draw_increment:
            raise ValueError("revolver draw violates the minimum increment")
        if treasury.approval is None or not treasury.approval.approved:
            raise ValueError("revolver draw lacks required approval")

    def _derive_outcome(self, state: GameState) -> TreasuryOutcome:
        treasury = self._require_treasury(state)
        decision = treasury.funding_decision
        if decision is None:
            raise ValueError("treasury funding decision is missing")
        book = state.hedge_book
        if book is not None and book.ticket.contracts == 0:
            return TreasuryOutcome.NO_POSITION_SAME_PROBLEM
        if decision.choice == FundingChoice.MISS_CALL:
            return TreasuryOutcome.TWO_OCLOCK_MISS
        if decision.choice == FundingChoice.REDUCE_POSITION:
            return TreasuryOutcome.DE_HEDGED
        if (
            decision.choice == FundingChoice.REVOLVER
            and treasury.projected_lowest_cash is not None
            and treasury.projected_lowest_cash >= self.scenario.minimum_operating_reserve
            and treasury.covenant_result is not None
            and treasury.covenant_result.passed
        ):
            return TreasuryOutcome.TRANSPARENT_DRAW
        if (
            treasury.projected_lowest_cash is not None
            and treasury.projected_lowest_cash < self.scenario.minimum_operating_reserve
        ):
            return TreasuryOutcome.CASH_RICH_PAYMENT_POOR
        return TreasuryOutcome.CLEAN_CASH_FUNDING

    def _link_evidence(
        self,
        state: GameState,
        decision_id: str,
        transaction_ids: list[str],
    ) -> None:
        treasury = self._require_treasury(state)
        if treasury.communication_record_id is None:
            return
        record = next(
            item
            for item in state.evidence_log
            if item.record_id == treasury.communication_record_id
        )
        decisions = list(dict.fromkeys([*record.linked_decision_ids, decision_id]))
        journals = list(dict.fromkeys([*record.linked_journal_transaction_ids, *transaction_ids]))
        index = state.evidence_log.index(record)
        state.evidence_log[index] = record.model_copy(
            update={
                "linked_decision_ids": decisions,
                "linked_journal_transaction_ids": journals,
            }
        )

    @staticmethod
    def _change_resource(
        state: GameState,
        resource_name: str,
        amount: int,
        source_id: str,
    ) -> None:
        old = getattr(state.resources, resource_name)
        new = old + amount
        if not 0 <= new <= 100:
            raise ValueError(f"treasury resource effect exceeds bounds: {resource_name}")
        setattr(state.resources, resource_name, new)
        state.record(
            phase="immediate",
            event_type="treasury_resource_delta",
            source_id=source_id,
            message=f"{resource_name} changed by {amount:+d}.",
            changes={"resource": resource_name, "old": old, "new": new},
        )

    @staticmethod
    def _require_treasury(state: GameState) -> TreasuryState:
        if state.treasury is None:
            raise ValueError("the treasury crisis has not started")
        return state.treasury
