"""Rich views for the treasury crisis, funding decision, and report."""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.state import GameState
from lake_effect_ledger.treasury.models import FundingChoice
from lake_effect_ledger.treasury.report import TreasuryReport


def _money(value) -> str:
    return f"${value:,.2f}"


def render_treasury_crisis(
    console: Console,
    state: GameState,
    content: ContentBundle,
) -> None:
    treasury = state.treasury
    if treasury is None:
        raise ValueError("treasury crisis is not active")
    scenario = content.treasury_scenario(treasury.scenario_id)
    crisis_text = (
        scenario.crisis_text
        if treasury.original_margin_call_amount
        else scenario.no_position_crisis_text
    )
    subtitle = (
        "Collected funds due " + treasury.margin_deadline.strftime("%I:%M %p").lstrip("0")
        if treasury.original_margin_call_amount
        else "No FCM call; scheduled cash obligations remain"
    )
    console.print(
        Panel(
            crisis_text,
            title=scenario.crisis_title.upper(),
            subtitle=subtitle,
            border_style="bold red",
        )
    )
    render_treasury_dashboard(console, state)


def render_treasury_dashboard(console: Console, state: GameState) -> None:
    treasury = state.treasury
    book = state.hedge_book
    if treasury is None or book is None:
        raise ValueError("treasury dashboard requires active treasury and hedge state")
    latest = treasury.liquidity_snapshots[-1]
    dashboard = Table(title="Treasury dashboard", box=box.ROUNDED, expand=True)
    dashboard.add_column("Measure")
    dashboard.add_column("Actual", justify="right")
    dashboard.add_row("Operating cash", _money(state.corporate_cash))
    dashboard.add_row("FCM margin cash", _money(book.margin.balance))
    dashboard.add_row("Pending margin call", _money(treasury.original_margin_call_amount))
    dashboard.add_row("Protected obligations", _money(treasury.remaining_protected_obligations))
    dashboard.add_row("Revolver commitment", _money(treasury.facility.commitment))
    dashboard.add_row("Revolver outstanding", _money(treasury.facility.outstanding))
    dashboard.add_row("Undrawn availability", _money(treasury.facility.undrawn_availability))
    dashboard.add_row("Available liquidity", _money(latest.available_liquidity))
    dashboard.caption = (
        "Available liquidity = operating cash + undrawn revolver - unpaid protected obligations."
    )
    console.print(dashboard)

    obligations = Table(title="Scheduled cash obligations", box=box.SIMPLE_HEAVY, expand=True)
    obligations.add_column("Due")
    obligations.add_column("Priority")
    obligations.add_column("Payee")
    obligations.add_column("Amount", justify="right")
    obligations.add_column("Status")
    for item in treasury.obligations:
        obligations.add_row(
            str(item.due_date),
            item.priority.value,
            item.payee,
            _money(item.amount),
            item.status.value,
        )
    console.print(obligations)


def render_funding_choices(
    console: Console,
    state: GameState,
    feasible: list[FundingChoice],
) -> None:
    treasury = state.treasury
    if treasury is None:
        raise ValueError("treasury funding choices require active state")
    labels = {
        FundingChoice.OPERATING_CASH: (
            "Use operating cash for the call"
            if treasury.original_margin_call_amount
            else "Protect scheduled obligations with operating cash"
        ),
        FundingChoice.REVOLVER: "Draw the approved revolver, then fund the call",
        FundingChoice.REDUCE_POSITION: "Reduce futures and recalculate margin",
        FundingChoice.MISS_CALL: "Do not meet the call before 2:00 p.m.",
    }
    table = Table(title="Feasible funding actions", box=box.SIMPLE, expand=True)
    table.add_column("ID")
    table.add_column("Action")
    for item in feasible:
        table.add_row(item.value, labels[item])
    console.print(table)


def render_treasury_report(console: Console, report: TreasuryReport) -> None:
    console.print(
        Panel(
            report.explanation,
            title=f"TREASURY REPORT · {report.outcome_title}",
            border_style="bold cyan",
        )
    )
    decision = Table(title="Decision and communication", box=box.ROUNDED, expand=True)
    decision.add_column("Field")
    decision.add_column("Actual result")
    decision.add_row("Market path", report.market_path_id)
    decision.add_row("Margin call", _money(report.margin_call_amount))
    decision.add_row("Deadline", report.margin_deadline)
    decision.add_row("Notification", report.notification.accuracy.value)
    decision.add_row("Recipients", ", ".join(report.notification.recipient_ids) or "none")
    decision.add_row("Funding", report.funding_decision.choice.value)
    decision.add_row("Call funded", _money(report.funding_decision.funded_amount))
    decision.add_row("Revolver draw", _money(report.funding_decision.revolver_draw_amount))
    decision.add_row("Contracts reduced", str(report.funding_decision.contracts_reduced))
    decision.add_row("Margin released", _money(report.funding_decision.margin_released))
    console.print(decision)

    if report.position_reductions:
        reductions = Table(title="Position-reduction history", box=box.SIMPLE, expand=True)
        reductions.add_column("Date")
        reductions.add_column("Closed", justify="right")
        reductions.add_column("Remaining", justify="right")
        reductions.add_column("Ratio")
        reductions.add_column("Prior P&L preserved", justify="right")
        reductions.add_column("Margin released", justify="right")
        for item in report.position_reductions:
            reductions.add_row(
                str(item.trade_date),
                str(item.contracts_closed),
                str(item.contracts_remaining),
                f"{item.previous_hedge_ratio:.0%} -> {item.new_hedge_ratio:.0%}",
                _money(item.cumulative_futures_pnl_preserved),
                _money(item.margin_released),
            )
        console.print(reductions)

    obligations = Table(title="Obligation results", box=box.SIMPLE_HEAVY, expand=True)
    obligations.add_column("Due")
    obligations.add_column("Obligation")
    obligations.add_column("Amount", justify="right")
    obligations.add_column("Result")
    for item in report.obligations:
        obligations.add_row(
            str(item.due_date),
            item.description,
            _money(item.amount),
            item.status.value,
        )
    console.print(obligations)

    reconciliation = report.reconciliation
    bridge = Table(title="Cash and debt bridges", box=box.ROUNDED, expand=True)
    bridge.add_column("Bridge")
    bridge.add_column("Beginning", justify="right")
    bridge.add_column("Debits / draws", justify="right")
    bridge.add_column("Credits / repayments", justify="right")
    bridge.add_column("Ending", justify="right")
    bridge.add_column("Reconciles")
    bridge.add_row(
        "Operating cash",
        _money(reconciliation.beginning_operating_cash),
        _money(reconciliation.operating_cash_debits),
        _money(reconciliation.operating_cash_credits),
        _money(reconciliation.ending_operating_cash),
        str(reconciliation.operating_cash_reconciles),
    )
    bridge.add_row(
        "FCM cash",
        _money(reconciliation.beginning_fcm_cash),
        _money(reconciliation.fcm_cash_debits),
        _money(reconciliation.fcm_cash_credits),
        _money(reconciliation.ending_fcm_cash),
        str(reconciliation.fcm_cash_reconciles),
    )
    bridge.add_row(
        "Revolver debt",
        _money(reconciliation.beginning_revolver_debt),
        _money(reconciliation.revolver_draws),
        _money(reconciliation.revolver_repayments),
        _money(reconciliation.ending_revolver_debt),
        str(reconciliation.revolver_debt_reconciles),
    )
    console.print(bridge)

    liquidity = Table(title="Liquidity and covenant", box=box.SIMPLE, expand=True)
    liquidity.add_column("Measure")
    liquidity.add_column("Actual", justify="right")
    liquidity.add_row("Projected lowest operating cash", _money(report.projected_lowest_cash))
    liquidity.add_row("Minimum operating reserve", _money(report.minimum_operating_reserve))
    liquidity.add_row("Ending available liquidity", _money(report.ending_available_liquidity))
    liquidity.add_row("Covenant minimum", _money(report.covenant.minimum_required))
    liquidity.add_row("Covenant passed", str(report.covenant.passed))
    liquidity.add_row("Accrued revolver interest", _money(report.accrued_interest))
    console.print(liquidity)

    console.print(
        Panel(
            "\n".join(report.journal_entries) or "No crisis-period entries.",
            title=f"Journal trail · balanced={report.journal_entries_balanced}",
        )
    )
    console.print(
        Panel(
            (
                f"Evidence records: {', '.join(report.evidence_record_ids)}\n"
                f"Linked decisions: {', '.join(report.notification.linked_decision_ids)}\n"
                "This is a durable event record, not a conclusion about guilt."
            ),
            title="Communication evidence",
        )
    )
    console.print(
        Panel(
            "Concepts: "
            + ", ".join(report.concepts)
            + "\n\nSimplified assumptions:\n"
            + "\n".join(f"• {item}" for item in report.simplified_assumptions),
            title="Learning and scope",
        )
    )
    console.print(
        "[dim]Educational fiction only—not legal, tax, accounting, trading, "
        "or investment advice.[/dim]"
    )
