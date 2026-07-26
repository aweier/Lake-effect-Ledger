"""Actual-path treasury report and cash/debt reconciliations."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from lake_effect_ledger.commodity.models import PositionReductionTrade, money
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.state import GameState
from lake_effect_ledger.treasury.models import (
    CommunicationRecord,
    CovenantResult,
    FundingDecision,
    ScheduledCashObligation,
    TreasuryOutcome,
)


class TreasuryReconciliation(BaseModel):
    beginning_operating_cash: Decimal
    operating_cash_debits: Decimal
    operating_cash_credits: Decimal
    ending_operating_cash: Decimal
    operating_cash_reconciles: bool
    beginning_fcm_cash: Decimal
    fcm_cash_debits: Decimal
    fcm_cash_credits: Decimal
    ending_fcm_cash: Decimal
    fcm_cash_reconciles: bool
    beginning_revolver_debt: Decimal
    revolver_draws: Decimal
    revolver_repayments: Decimal
    ending_revolver_debt: Decimal
    revolver_debt_reconciles: bool


class TreasuryReport(BaseModel):
    scenario_id: str
    outcome: TreasuryOutcome
    outcome_title: str
    explanation: str
    market_path_id: str
    margin_call_amount: Decimal
    margin_deadline: str
    notification: CommunicationRecord
    funding_decision: FundingDecision
    obligations: list[ScheduledCashObligation]
    position_reductions: list[PositionReductionTrade]
    projected_lowest_cash: Decimal
    minimum_operating_reserve: Decimal
    ending_available_liquidity: Decimal
    covenant: CovenantResult
    accrued_interest: Decimal
    reconciliation: TreasuryReconciliation
    journal_entries: list[str]
    journal_entries_balanced: bool
    evidence_record_ids: list[str]
    concepts: list[str]
    simplified_assumptions: list[str]


OUTCOME_TITLES = {
    TreasuryOutcome.TRANSPARENT_DRAW: "Transparent Draw",
    TreasuryOutcome.CASH_RICH_PAYMENT_POOR: "Cash-Rich, Payment-Poor",
    TreasuryOutcome.DE_HEDGED: "De-Hedged",
    TreasuryOutcome.TWO_OCLOCK_MISS: "Two O'Clock Miss",
    TreasuryOutcome.NO_POSITION_SAME_PROBLEM: "No Position, Same Problem",
    TreasuryOutcome.CLEAN_CASH_FUNDING: "Call Funded Cleanly",
}


def build_treasury_report(state: GameState, content: ContentBundle) -> TreasuryReport:
    treasury = state.treasury
    book = state.hedge_book
    if (
        treasury is None
        or not treasury.completed
        or treasury.outcome is None
        or treasury.funding_decision is None
        or treasury.covenant_result is None
        or book is None
    ):
        raise ValueError("the treasury report requires a completed crisis")
    if treasury.communication_record_id is None:
        raise ValueError("the treasury report requires a communication record")
    notification = next(
        item for item in state.evidence_log if item.record_id == treasury.communication_record_id
    )
    later_entries = state.ledger.entries[treasury.beginning_ledger_entry_count :]
    cash_debits, cash_credits = _account_activity(later_entries, "1000")
    fcm_debits, fcm_credits = _account_activity(later_entries, "1050")
    operating_expected = money(treasury.beginning_operating_cash + cash_debits - cash_credits)
    fcm_expected = money(treasury.beginning_fcm_margin_cash + fcm_debits - fcm_credits)
    reconciliation = TreasuryReconciliation(
        beginning_operating_cash=treasury.beginning_operating_cash,
        operating_cash_debits=cash_debits,
        operating_cash_credits=cash_credits,
        ending_operating_cash=state.corporate_cash,
        operating_cash_reconciles=operating_expected == money(state.corporate_cash),
        beginning_fcm_cash=treasury.beginning_fcm_margin_cash,
        fcm_cash_debits=fcm_debits,
        fcm_cash_credits=fcm_credits,
        ending_fcm_cash=book.margin.balance,
        fcm_cash_reconciles=fcm_expected == money(book.margin.balance),
        beginning_revolver_debt=treasury.facility.beginning_outstanding,
        revolver_draws=treasury.facility.total_draws,
        revolver_repayments=treasury.facility.total_repayments,
        ending_revolver_debt=treasury.facility.outstanding,
        revolver_debt_reconciles=(
            treasury.facility.beginning_outstanding
            + treasury.facility.total_draws
            - treasury.facility.total_repayments
            == treasury.facility.outstanding
        ),
    )
    scenario = content.treasury_scenario(treasury.scenario_id)
    lessons = [content.lesson(item) for item in scenario.learning_objectives]
    ending_available = treasury.liquidity_snapshots[-1].available_liquidity
    return TreasuryReport(
        scenario_id=treasury.scenario_id,
        outcome=treasury.outcome,
        outcome_title=OUTCOME_TITLES[treasury.outcome],
        explanation=_explain_outcome(state),
        market_path_id=book.price_path.id,
        margin_call_amount=treasury.original_margin_call_amount,
        margin_deadline=treasury.margin_deadline.isoformat(),
        notification=notification,
        funding_decision=treasury.funding_decision,
        obligations=treasury.obligations,
        position_reductions=book.position_reductions,
        projected_lowest_cash=treasury.projected_lowest_cash or state.corporate_cash,
        minimum_operating_reserve=scenario.minimum_operating_reserve,
        ending_available_liquidity=ending_available,
        covenant=treasury.covenant_result,
        accrued_interest=treasury.facility.accrued_interest,
        reconciliation=reconciliation,
        journal_entries=[
            (
                f"{entry.transaction_id}: {entry.description} "
                f"(debits ${entry.total_debits:,.2f}; credits ${entry.total_credits:,.2f})"
            )
            for entry in later_entries
        ],
        journal_entries_balanced=all(
            entry.total_debits == entry.total_credits for entry in later_entries
        ),
        evidence_record_ids=[item.record_id for item in state.evidence_log],
        concepts=[item.title for item in lessons],
        simplified_assumptions=scenario.simplified_assumptions,
    )


def _account_activity(entries, account: str) -> tuple[Decimal, Decimal]:
    debits = Decimal("0")
    credits = Decimal("0")
    for entry in entries:
        for line in entry.lines:
            if line.account == account:
                debits += line.debit
                credits += line.credit
    return money(debits), money(credits)


def _explain_outcome(state: GameState) -> str:
    treasury = state.treasury
    if treasury is None or treasury.outcome is None or treasury.funding_decision is None:
        raise ValueError("treasury outcome is unavailable")
    if treasury.outcome == TreasuryOutcome.TRANSPARENT_DRAW:
        return (
            f"Required approvers received an accurate notice, the facility supplied "
            f"${treasury.funding_decision.revolver_draw_amount:,.2f}, and the ending "
            "liquidity covenant passed. The draw created debt, not income."
        )
    if treasury.outcome == TreasuryOutcome.CASH_RICH_PAYMENT_POOR:
        return (
            f"The call was paid from operating cash, but projected cash fell to "
            f"${treasury.projected_lowest_cash:,.2f} after protected obligations—below "
            "the operating reserve despite a positive bank balance."
        )
    if treasury.outcome == TreasuryOutcome.DE_HEDGED:
        return (
            f"The position was reduced by "
            f"{treasury.funding_decision.contracts_reduced} contract(s). Prior settled "
            "P&L stayed recognized; only future hedge coverage changed."
        )
    if treasury.outcome == TreasuryOutcome.TWO_OCLOCK_MISS:
        return (
            "The call remained unpaid at the deadline and the fictional FCM liquidated "
            "the remaining futures position. The record reports the event and timing; "
            "it does not assign guilt."
        )
    if treasury.outcome == TreasuryOutcome.NO_POSITION_SAME_PROBLEM:
        return (
            "No futures position created a margin call, but scheduled payroll, pipeline, "
            "supply, interest, and field payments still pushed cash below the operating "
            "reserve."
        )
    return (
        "Operating cash funded the call and the eventual market path restored enough "
        "cash to finish above the configured operating reserve."
    )
