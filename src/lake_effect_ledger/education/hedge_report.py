"""Actual-path Hedge Book educational and reconciliation report."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from lake_effect_ledger.commodity.models import (
    DailySettlementResult,
    DocumentationQuality,
    HedgeOutcome,
    MarginCall,
    money,
)
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.state import GameState


class LiquidityBridge(BaseModel):
    beginning_operating_cash: Decimal
    initial_margin_deposit: Decimal
    daily_variation_margin: Decimal
    additional_margin_deposits: Decimal
    margin_released: Decimal
    other_operating_cash_activity: Decimal
    ending_operating_cash: Decimal
    ending_margin_cash: Decimal
    operating_cash_reconciles: bool
    total_liquidity_reconciles: bool


class HedgeBookReport(BaseModel):
    scenario_id: str
    outcome: HedgeOutcome
    outcome_title: str
    physical_quantity_mmbtu: Decimal
    original_henry_hub_price: Decimal
    original_basis: Decimal
    original_regional_price: Decimal
    hedge_ratio: Decimal
    futures_side: str
    contracts: int
    contract_size_mmbtu: Decimal
    hedged_quantity_mmbtu: Decimal
    speculative_quantity_mmbtu: Decimal
    entry_price: Decimal
    settlements: list[DailySettlementResult]
    total_variation_margin: Decimal
    margin_calls: list[MarginCall]
    physical_economic_pnl: Decimal
    henry_hub_physical_component: Decimal
    basis_effect: Decimal
    futures_pnl: Decimal
    net_economic_pnl: Decimal
    liquidity: LiquidityBridge
    journal_entries: list[str]
    journal_entries_balanced: bool
    hedge_classification: str
    why_it_worked_or_failed: str
    documentation_quality: DocumentationQuality
    series_3_concepts: list[str]
    accounting_concepts: list[str]
    simplified_assumptions: list[str]


OUTCOME_TITLES = {
    HedgeOutcome.UNHEDGED_WINTER: "Unhedged Winter",
    HedgeOutcome.INTENDED_HEDGE: "The Intended Hedge",
    HedgeOutcome.MARGIN_PRESSURE: "Margin Pressure",
    HedgeOutcome.OVERHEDGE: "The Overhedge",
    HedgeOutcome.DE_HEDGED: "De-Hedged",
    HedgeOutcome.LIQUIDITY_FAILURE: "Liquidity Failure",
}


def build_hedge_book_report(
    state: GameState,
    content: ContentBundle,
) -> HedgeBookReport:
    book = state.hedge_book
    if book is None or not book.completed or book.outcome is None:
        raise ValueError("the Hedge Book report requires a completed scenario")
    final = book.settlements[-1]
    operating_cash_expected = money(
        book.beginning_operating_cash
        - book.margin.total_initial_deposit
        - book.margin.total_additional_deposits
        + book.margin.total_released
    )
    margin_cash_expected = money(
        book.margin.total_initial_deposit
        + book.margin.total_variation_margin
        + book.margin.total_additional_deposits
        - book.margin.total_released
    )
    other_operating_cash_activity = money(state.corporate_cash - operating_cash_expected)
    total_liquidity_expected = money(
        book.beginning_operating_cash
        + book.margin.total_variation_margin
        + other_operating_cash_activity
    )
    liquidity = LiquidityBridge(
        beginning_operating_cash=book.beginning_operating_cash,
        initial_margin_deposit=book.margin.total_initial_deposit,
        daily_variation_margin=book.margin.total_variation_margin,
        additional_margin_deposits=book.margin.total_additional_deposits,
        margin_released=book.margin.total_released,
        other_operating_cash_activity=other_operating_cash_activity,
        ending_operating_cash=state.corporate_cash,
        ending_margin_cash=book.margin.balance,
        operating_cash_reconciles=(
            operating_cash_expected + other_operating_cash_activity == money(state.corporate_cash)
        ),
        total_liquidity_reconciles=(
            margin_cash_expected == money(book.margin.balance)
            and total_liquidity_expected == money(state.corporate_cash + book.margin.balance)
        ),
    )
    journal_entries = [
        entry
        for entry in state.ledger.entries
        if entry.transaction_id in book.journal_transaction_ids
    ]
    lessons = [content.lesson(item) for item in book.learning_objectives]
    return HedgeBookReport(
        scenario_id=book.scenario_id,
        outcome=book.outcome,
        outcome_title=OUTCOME_TITLES[book.outcome],
        physical_quantity_mmbtu=book.physical.quantity_mmbtu,
        original_henry_hub_price=book.physical.original_henry_hub_price,
        original_basis=book.physical.original_basis,
        original_regional_price=book.physical.original_regional_price,
        hedge_ratio=book.ticket.hedge_ratio,
        futures_side=book.ticket.side.value,
        contracts=book.ticket.contracts,
        contract_size_mmbtu=book.contract.contract_size_mmbtu,
        hedged_quantity_mmbtu=book.ticket.hedged_quantity_mmbtu,
        speculative_quantity_mmbtu=book.ticket.speculative_quantity_mmbtu,
        entry_price=book.ticket.entry_price,
        settlements=book.settlements,
        total_variation_margin=book.margin.total_variation_margin,
        margin_calls=book.margin.calls,
        physical_economic_pnl=final.physical_economic_pnl,
        henry_hub_physical_component=final.henry_hub_physical_component,
        basis_effect=final.basis_component,
        futures_pnl=final.cumulative_futures_pnl,
        net_economic_pnl=final.net_economic_pnl,
        liquidity=liquidity,
        journal_entries=[
            (
                f"{entry.transaction_id}: {entry.description} "
                f"(debits ${entry.total_debits:,.2f}; credits ${entry.total_credits:,.2f})"
            )
            for entry in journal_entries
        ],
        journal_entries_balanced=all(
            entry.total_debits == entry.total_credits for entry in journal_entries
        ),
        hedge_classification=_classification(book.ticket.hedge_ratio),
        why_it_worked_or_failed=_explain_actual_result(book.outcome, book, final),
        documentation_quality=book.documentation_quality,
        series_3_concepts=[lesson.title for lesson in lessons if lesson.category == "series_3"],
        accounting_concepts=[
            lesson.title for lesson in lessons if lesson.category in {"accounting", "controls"}
        ],
        simplified_assumptions=content.hedge_scenario(book.scenario_id).simplified_assumptions,
    )


def _classification(ratio: Decimal) -> str:
    if ratio == 0:
        return "Unhedged physical exposure"
    if ratio < 1:
        return "Partial economic hedge"
    if ratio == 1:
        return "Full-quantity economic hedge with basis risk"
    return "Overhedge: hedge quantity plus speculative short futures"


def _explain_actual_result(outcome, book, final) -> str:
    ratio = book.ticket.hedge_ratio
    if outcome == HedgeOutcome.UNHEDGED_WINTER:
        return (
            f"No futures were sold, so the full Chicago price move produced "
            f"${final.physical_economic_pnl:,.2f} of physical economic P&L."
        )
    if outcome == HedgeOutcome.OVERHEDGE:
        return (
            f"The short futures earned ${final.cumulative_futures_pnl:,.2f}, including "
            f"exposure on {book.ticket.speculative_quantity_mmbtu:,.0f} MMBtu beyond "
            f"the physical sale. Net economic P&L was ${final.net_economic_pnl:,.2f}; "
            "profit does not convert the excess into an authorized hedge."
        )
    if outcome == HedgeOutcome.LIQUIDITY_FAILURE:
        return (
            f"The position could not fund a margin call even though its final "
            f"economic direction may have been defensible. Ratio: {ratio:.0%}."
        )
    if outcome == HedgeOutcome.DE_HEDGED:
        latest_reduction = book.position_reductions[-1]
        return (
            f"The position was reduced from {latest_reduction.previous_hedge_ratio:.0%} "
            f"to {latest_reduction.new_hedge_ratio:.0%}. Previously settled futures "
            "P&L remained recognized; later settlements used only remaining contracts."
        )
    if ratio == 1:
        return (
            f"Futures P&L of ${final.cumulative_futures_pnl:,.2f} offset the "
            f"Henry Hub physical component of ${final.henry_hub_physical_component:,.2f}. "
            f"The remaining ${final.basis_component:,.2f} basis effect produced net "
            f"economic P&L of ${final.net_economic_pnl:,.2f}."
        )
    return (
        f"The {ratio:.0%} short hedge earned ${final.cumulative_futures_pnl:,.2f}, "
        f"but part of the Henry Hub exposure and all Chicago basis risk remained. "
        f"A margin call required ${book.margin.total_additional_deposits:,.2f} before "
        "the forecast physical sale generated cash."
    )
