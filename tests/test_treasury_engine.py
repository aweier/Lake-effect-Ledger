from decimal import Decimal

import pytest

from lake_effect_ledger.treasury.models import FundingChoice, TreasuryOutcome
from lake_effect_ledger.treasury.report import build_treasury_report


def _finish(state, commodity, treasury) -> None:
    commodity.settle_remaining(state)
    treasury.finalize(state)


@pytest.mark.parametrize(
    ("hedge_level", "notification", "funding", "expected_outcome"),
    [
        (
            "hedge_100",
            "notify_immediately",
            "revolver",
            TreasuryOutcome.TRANSPARENT_DRAW,
        ),
        (
            "hedge_100",
            "notify_immediately",
            "operating_cash",
            TreasuryOutcome.CASH_RICH_PAYMENT_POOR,
        ),
        (
            "hedge_100",
            "notify_immediately",
            "reduce_position",
            TreasuryOutcome.DE_HEDGED,
        ),
        (
            "hedge_100",
            "delay_notification",
            "miss_call",
            TreasuryOutcome.TWO_OCLOCK_MISS,
        ),
        (
            "no_hedge",
            "notify_immediately",
            "operating_cash",
            TreasuryOutcome.NO_POSITION_SAME_PROBLEM,
        ),
    ],
)
def test_state_driven_treasury_outcomes(
    treasury_state_factory,
    hedge_level: str,
    notification: str,
    funding: str,
    expected_outcome: TreasuryOutcome,
) -> None:
    state, commodity, treasury = treasury_state_factory(hedge_level=hedge_level)
    treasury.record_notification(state, notification)
    treasury.resolve_funding(state, funding)

    _finish(state, commodity, treasury)

    assert state.treasury.outcome == expected_outcome
    treasury.assert_treasury_reconciles(state)


def test_immediate_accurate_notice_enables_all_call_actions(
    treasury_state_factory,
) -> None:
    state, _, treasury = treasury_state_factory()
    treasury.record_notification(state, "notify_immediately")

    assert treasury.feasible_funding_choices(state) == [
        FundingChoice.OPERATING_CASH,
        FundingChoice.REVOLVER,
        FundingChoice.REDUCE_POSITION,
        FundingChoice.MISS_CALL,
    ]


@pytest.mark.parametrize(
    "notification",
    ["notify_cal_only", "send_vague_update", "delay_notification"],
)
def test_incomplete_notification_does_not_authorize_revolver(
    treasury_state_factory,
    notification: str,
) -> None:
    state, _, treasury = treasury_state_factory()
    treasury.record_notification(state, notification)

    assert FundingChoice.REVOLVER not in treasury.feasible_funding_choices(state)


def test_notification_does_not_change_market_pnl(treasury_state_factory) -> None:
    results = []
    for notification in (
        "notify_immediately",
        "notify_cal_only",
        "send_vague_update",
        "delay_notification",
    ):
        state, _, treasury = treasury_state_factory()
        before = state.hedge_book.position.cumulative_pnl
        treasury.record_notification(state, notification)
        after = state.hedge_book.position.cumulative_pnl
        results.append((before, after))

    assert set(results) == {(Decimal("-70000.00"), Decimal("-70000.00"))}


def test_operating_cash_funds_call_without_creating_debt(
    treasury_state_factory,
) -> None:
    state, _, treasury = treasury_state_factory()
    treasury.record_notification(state, "notify_immediately")
    decision = treasury.resolve_funding(state, "operating_cash")

    assert decision.funded_amount == Decimal("70000.00")
    assert state.treasury.facility.outstanding == 0
    assert state.hedge_book.margin.calls[-1].met
    assert state.hedge_book.margin.balance == Decimal("150000.00")


def test_revolver_draw_and_interest_use_balanced_entries(
    content,
    treasury_state_factory,
) -> None:
    state, commodity, treasury = treasury_state_factory()
    treasury.record_notification(state, "notify_immediately")
    treasury.resolve_funding(state, "revolver")
    _finish(state, commodity, treasury)

    draw = next(
        item for item in state.ledger.entries if item.transaction_id == "txn_treasury_revolver_draw"
    )
    interest = next(
        item
        for item in state.ledger.entries
        if item.transaction_id == "txn_treasury_interest_accrual"
    )
    assert draw.lines[0].account == "1000"
    assert draw.lines[1].account == "2300"
    assert interest.lines[0].account == "5600"
    assert interest.lines[1].account == "2150"
    assert state.treasury.facility.accrued_interest == Decimal("279.45")
    report = build_treasury_report(state, content)
    assert report.journal_entries_balanced
    assert report.reconciliation.revolver_debt_reconciles


def test_position_reduction_is_prospective_and_releases_only_eligible_margin(
    treasury_state_factory,
) -> None:
    state, commodity, treasury = treasury_state_factory()
    treasury.record_notification(state, "notify_immediately")
    decision = treasury.resolve_funding(state, "reduce_position")
    trade = state.hedge_book.position_reductions[-1]

    assert decision.contracts_reduced == 5
    assert trade.contracts_remaining == 5
    assert trade.previous_hedge_ratio == Decimal("1.0000")
    assert trade.new_hedge_ratio == Decimal("0.5000")
    assert trade.cumulative_futures_pnl_preserved == Decimal("-70000.00")
    assert trade.margin_released == Decimal("5000.00")
    assert trade.revised_margin_call == 0

    _finish(state, commodity, treasury)
    assert state.hedge_book.settlements[-1].cumulative_futures_pnl == Decimal("-85000.00")


def test_missed_call_preserves_unmet_record_and_liquidates_position(
    treasury_state_factory,
) -> None:
    state, _, treasury = treasury_state_factory()
    treasury.record_notification(state, "delay_notification")
    treasury.resolve_funding(state, "miss_call")

    call = state.hedge_book.margin.calls[-1]
    assert not call.met
    assert call.shortfall == Decimal("70000.00")
    assert state.hedge_book.position.contracts == 0
    assert state.hedge_book.liquidity_crisis
    assert (
        state.treasury.funding_decision.timestamp
        >= state.evidence_log[0].timestamp
        > state.treasury.margin_deadline
    )


def test_available_liquidity_formula_is_consistent(treasury_state_factory) -> None:
    state, _, treasury = treasury_state_factory()

    assert treasury.available_liquidity(state) == Decimal("3800000.00")
    snapshot = state.treasury.liquidity_snapshots[-1]
    assert snapshot.available_liquidity == (
        snapshot.operating_cash + snapshot.undrawn_revolver - snapshot.protected_obligations
    )


def test_due_obligations_are_paid_in_priority_order(treasury_state_factory) -> None:
    state, commodity, treasury = treasury_state_factory()
    treasury.record_notification(state, "notify_immediately")
    treasury.resolve_funding(state, "revolver")
    _finish(state, commodity, treasury)

    assert all(item.status.value == "paid" for item in state.treasury.obligations)
    paid_ids = [
        item.source_id
        for item in state.ledger.entries
        if item.transaction_id.startswith("txn_obligation_")
    ]
    assert paid_ids[:2] == ["payroll_jan_19", "pipeline_reservation_jan_20"]


def test_covenant_failure_is_reported_from_actual_values(treasury_state_factory) -> None:
    state, commodity, treasury = treasury_state_factory()
    treasury.record_notification(state, "notify_immediately")
    treasury.resolve_funding(state, "revolver")
    state.treasury.facility = state.treasury.facility.model_copy(
        update={"covenant_minimum_available_liquidity": Decimal("4000000")}
    )
    _finish(state, commodity, treasury)

    assert not state.treasury.covenant_result.passed
    assert state.treasury.covenant_result.available_liquidity == Decimal("3850000.00")


def test_communication_evidence_links_decisions_and_journals(
    treasury_state_factory,
) -> None:
    state, commodity, treasury = treasury_state_factory()
    treasury.record_notification(state, "notify_immediately")
    treasury.resolve_funding(state, "revolver")
    _finish(state, commodity, treasury)
    evidence = state.evidence_log[0]

    assert "notification_notify_immediately" in evidence.linked_decision_ids
    assert "funding_revolver" in evidence.linked_decision_ids
    assert "outcome_transparent_draw" in evidence.linked_decision_ids
    assert "txn_treasury_revolver_draw" in evidence.linked_journal_transaction_ids
    assert evidence.recipient_ids == ["evelyn_marsh", "june_halvorsen"]


def test_zero_hedge_gets_obligations_problem_without_reduction_actions(
    treasury_state_factory,
) -> None:
    state, _, treasury = treasury_state_factory(hedge_level="no_hedge")
    treasury.record_notification(state, "notify_immediately")
    feasible = treasury.feasible_funding_choices(state)

    assert FundingChoice.OPERATING_CASH in feasible
    assert FundingChoice.REVOLVER in feasible
    assert FundingChoice.REDUCE_POSITION not in feasible
    assert FundingChoice.MISS_CALL not in feasible


def test_unapproved_revolver_choice_is_rejected(treasury_state_factory) -> None:
    state, _, treasury = treasury_state_factory()
    treasury.record_notification(state, "notify_cal_only")

    with pytest.raises(ValueError, match="not feasible"):
        treasury.resolve_funding(state, "revolver")


def test_invalid_draw_increment_is_rejected(treasury_state_factory) -> None:
    state, _, treasury = treasury_state_factory()
    treasury.record_notification(state, "notify_immediately")

    with pytest.raises(ValueError, match="minimum increment"):
        treasury.resolve_funding(state, "revolver", draw_amount=Decimal("125000"))


def test_next_settlement_is_blocked_until_call_is_resolved(
    treasury_state_factory,
) -> None:
    state, commodity, _ = treasury_state_factory()

    with pytest.raises(ValueError, match="pending margin call"):
        commodity.settle_next_day(state)


def test_duplicate_notification_and_funding_decisions_are_rejected(
    treasury_state_factory,
) -> None:
    state, _, treasury = treasury_state_factory()
    treasury.record_notification(state, "notify_immediately")
    with pytest.raises(ValueError, match="already recorded"):
        treasury.record_notification(state, "notify_immediately")

    treasury.resolve_funding(state, "operating_cash")
    with pytest.raises(ValueError, match="already complete"):
        treasury.resolve_funding(state, "operating_cash")
