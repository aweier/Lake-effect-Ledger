from datetime import date
from decimal import Decimal

import pytest

from lake_effect_ledger.accounting.models import JournalEntry, JournalLine
from lake_effect_ledger.commodity.engine import (
    CommodityEngine,
    InsufficientOperatingCashError,
)
from lake_effect_ledger.education.hedge_report import build_hedge_book_report
from lake_effect_ledger.narrative.engine import NarrativeEngine


@pytest.mark.parametrize(
    (
        "level_id",
        "contracts",
        "ratio",
        "expected_outcome",
        "futures_pnl",
        "net_pnl",
        "ending_cash",
    ),
    [
        ("no_hedge", 0, "0", "unhedged_winter", "0", "-140000.00", "4200000"),
        ("hedge_50", 5, "0.5", "margin_pressure", "50000.00", "-90000.00", "4250000.00"),
        ("hedge_100", 10, "1", "intended_hedge", "100000.00", "-40000.00", "4300000.00"),
        ("hedge_150", 15, "1.5", "overhedge", "150000.00", "10000.00", "4350000.00"),
    ],
)
def test_all_hedge_choices_reach_reconciled_outcomes(
    content,
    completed_state_factory,
    level_id: str,
    contracts: int,
    ratio: str,
    expected_outcome: str,
    futures_pnl: str,
    net_pnl: str,
    ending_cash: str,
) -> None:
    state = completed_state_factory()
    engine = CommodityEngine(content)
    preview = engine.preview_hedge(state, level_id)
    assert preview.contracts == contracts
    assert preview.hedge_ratio == Decimal(ratio)

    book = engine.open_hedge(state, level_id)
    NarrativeEngine(content).choose(
        state,
        "hedge_documentation",
        "write_accurate_hedge_memo",
    )
    assert book.margin.total_initial_deposit == Decimal("15000") * contracts

    engine.settle_remaining(state)
    final = book.settlements[-1]

    assert book.outcome.value == expected_outcome
    assert final.cumulative_futures_pnl == Decimal(futures_pnl)
    assert final.net_economic_pnl == Decimal(net_pnl)
    assert state.corporate_cash == Decimal(ending_cash)
    assert book.margin.balance == 0
    assert all(entry.total_debits == entry.total_credits for entry in state.ledger.entries)
    engine.assert_cash_and_margin_reconcile(state)
    report = build_hedge_book_report(state, content)
    assert report.liquidity.operating_cash_reconciles
    assert report.liquidity.total_liquidity_reconciles


def test_daily_settlement_and_cumulative_pnl(content, completed_state_factory) -> None:
    state = completed_state_factory()
    engine = CommodityEngine(content)
    book = engine.open_hedge(state, "hedge_100")

    first = engine.settle_next_day(state)
    second = engine.settle_next_day(state)

    assert first.daily_futures_pnl == Decimal("-30000.00")
    assert first.cumulative_futures_pnl == Decimal("-30000.00")
    assert second.daily_futures_pnl == Decimal("-45000.00")
    assert second.cumulative_futures_pnl == Decimal("-75000.00")
    assert book.position.cumulative_pnl == Decimal("-75000.00")


def test_initial_margin_funding_moves_cash_into_fcm(
    content,
    completed_state_factory,
) -> None:
    state = completed_state_factory()
    engine = CommodityEngine(content)
    beginning_cash = state.corporate_cash

    book = engine.open_hedge(state, "hedge_100")

    assert state.corporate_cash == beginning_cash - Decimal("150000")
    assert book.margin.balance == Decimal("150000")
    assert state.ledger.entries[-1].lines == [
        JournalLine(account="1050", debit=Decimal("150000")),
        JournalLine(account="1000", credit=Decimal("150000")),
    ]
    engine.assert_cash_and_margin_reconcile(state)


def test_maintenance_breach_creates_and_funds_margin_call(
    content,
    completed_state_factory,
) -> None:
    state = completed_state_factory()
    engine = CommodityEngine(content)
    book = engine.open_hedge(state, "hedge_100")

    engine.settle_next_day(state)
    second = engine.settle_next_day(state)

    assert second.margin_balance_after_settlement == Decimal("75000.00")
    assert second.margin_call_amount == Decimal("75000.00")
    assert second.margin_funded == Decimal("75000.00")
    assert second.margin_balance_end == Decimal("150000.00")
    assert book.margin.calls[0].met
    assert book.margin.total_additional_deposits == Decimal("75000.00")


def test_insufficient_initial_operating_cash_is_rejected(
    content,
    completed_state_factory,
) -> None:
    state = completed_state_factory()
    state.corporate_cash = Decimal("100")

    with pytest.raises(InsufficientOperatingCashError):
        CommodityEngine(content).open_hedge(state, "hedge_100")


def test_unmet_margin_call_creates_liquidity_failure(
    content,
    completed_state_factory,
) -> None:
    state = completed_state_factory()
    engine = CommodityEngine(content)
    book = engine.open_hedge(state, "hedge_100")
    # A fictional emergency operating payment leaves only $10 available.
    payment = state.corporate_cash - Decimal("10")
    state.ledger.post(
        JournalEntry(
            transaction_id="txn_emergency_operating_payment",
            entry_date=date(2028, 1, 17),
            description="Emergency operating payment for test",
            source_id="test",
            lines=[
                JournalLine(account="5100", debit=payment),
                JournalLine(account="1000", credit=payment),
            ],
        ),
        content.valid_accounts,
    )
    state.corporate_cash = Decimal("10")
    engine.assert_cash_and_margin_reconcile(state)

    engine.settle_next_day(state)
    second = engine.settle_next_day(state)

    assert second.margin_call_amount == Decimal("75000.00")
    assert second.margin_funded == Decimal("10")
    assert book.margin.calls[0].shortfall == Decimal("74990.00")
    assert book.liquidity_crisis
    assert book.outcome.value == "liquidity_failure"
    assert book.completed
    engine.assert_cash_and_margin_reconcile(state)


def test_documentation_does_not_change_market_pnl(
    content,
    completed_state_factory,
) -> None:
    results = []
    for choice in (
        "write_accurate_hedge_memo",
        "copy_cal_vague_description",
        "escalate_basis_mismatch",
    ):
        state = completed_state_factory()
        engine = CommodityEngine(content)
        engine.open_hedge(state, "hedge_100")
        NarrativeEngine(content).choose(state, "hedge_documentation", choice)
        engine.settle_remaining(state)
        final = state.hedge_book.settlements[-1]
        results.append(
            (
                final.cumulative_futures_pnl,
                final.physical_economic_pnl,
                final.net_economic_pnl,
            )
        )
    assert len(set(results)) == 1


def test_learning_report_reconciles_to_engine_results(
    content,
    completed_state_factory,
) -> None:
    state = completed_state_factory()
    engine = CommodityEngine(content)
    engine.open_hedge(state, "hedge_100")
    NarrativeEngine(content).choose(
        state,
        "hedge_documentation",
        "write_accurate_hedge_memo",
    )
    engine.settle_remaining(state)

    report = build_hedge_book_report(state, content)

    assert report.physical_economic_pnl == Decimal("-140000.00")
    assert report.henry_hub_physical_component == Decimal("-100000.00")
    assert report.basis_effect == Decimal("-40000.00")
    assert report.futures_pnl == Decimal("100000.00")
    assert report.net_economic_pnl == Decimal("-40000.00")
    assert report.total_variation_margin == report.futures_pnl
    assert sum(call.funded_amount for call in report.margin_calls) == Decimal("75000.00")
    assert report.journal_entries_balanced
    assert report.liquidity.ending_operating_cash == state.corporate_cash


def test_deterministic_hedge_replay(content, completed_state_factory) -> None:
    states = []
    for _ in range(2):
        state = completed_state_factory(seed=2028)
        engine = CommodityEngine(content)
        engine.open_hedge(state, "hedge_100")
        NarrativeEngine(content).choose(
            state,
            "hedge_documentation",
            "write_accurate_hedge_memo",
        )
        engine.settle_remaining(state)
        states.append(state)

    assert states[0].hedge_book.seed == 2028
    assert states[0] == states[1]
