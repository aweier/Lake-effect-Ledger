"""Rich screens for the Hedge Ticket, Position Book, settlements, and report."""

from __future__ import annotations

from decimal import Decimal

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lake_effect_ledger.commodity.engine import hedge_ratio
from lake_effect_ledger.commodity.models import (
    DailySettlementResult,
    HedgeTicketPreview,
)
from lake_effect_ledger.education.hedge_report import HedgeBookReport
from lake_effect_ledger.narrative.models import ContentBundle, SceneDefinition
from lake_effect_ledger.state import GameState


def _money(value: Decimal) -> str:
    return f"${value:,.2f}"


def _signed_money(value: Decimal) -> str:
    color = "green" if value > 0 else "red" if value < 0 else "white"
    return f"[{color}]{value:+,.2f}[/{color}]"


def render_hedge_briefings(console: Console, content: ContentBundle) -> None:
    console.print("\n[bold cyan]EPISODE 1 · THE HEDGE BOOK[/bold cyan]")
    for scene in content.hedge_narrative.briefings:
        console.print(
            Panel(
                scene.text,
                title=scene.title,
                subtitle=scene.speaker.replace("_", " ").title(),
                border_style="blue",
            )
        )


def render_hedge_ticket(
    console: Console,
    preview: HedgeTicketPreview,
    content: ContentBundle,
) -> None:
    scenario = content.hedge_scenarios.scenarios[0]
    contract = content.commodity_contract(scenario.contract_id)
    table = Table(box=box.ROUNDED, expand=True)
    table.add_column("Ticket field", style="bold cyan", width=28)
    table.add_column("Proposed value")
    table.add_row("Hedge level", preview.label)
    table.add_row("Futures side", preview.side.value.upper())
    table.add_row("Contracts", str(preview.contracts))
    table.add_row("Contract month", scenario.contract_month)
    table.add_row("Contract size", f"{contract.contract_size_mmbtu:,.0f} MMBtu")
    table.add_row("Hedge ratio", f"{preview.hedge_ratio:.0%}")
    table.add_row("Initial margin", _money(preview.initial_margin_required))
    table.add_row("Operating cash after", _money(preview.operating_cash_remaining))
    table.add_row(
        "Cash above minimum reserve",
        _signed_money(preview.liquidity_headroom_remaining),
    )
    table.add_row("Risk reduced", preview.risk_reduced)
    table.add_row("Risk remaining", preview.risk_remaining)
    if preview.overhedge_warning:
        table.add_row("Warning", f"[bold red]{preview.overhedge_warning}[/bold red]")
    console.print(Panel(table, title="HEDGE TICKET · Review before approval"))
    console.print(
        "[dim]Margin assumptions are fictional training values. The 10,000 MMBtu "
        "contract size is based on the locally recorded CME specification source.[/dim]"
    )


def render_documentation_scene(console: Console, scene: SceneDefinition) -> None:
    console.print(
        Panel(
            scene.text,
            title=scene.title,
            subtitle=scene.speaker.replace("_", " ").title(),
            border_style="yellow",
        )
    )


def render_position_book(console: Console, state: GameState) -> None:
    book = state.hedge_book
    if book is None:
        raise ValueError("Position Book requires an active hedge scenario")
    latest = book.settlements[-1] if book.settlements else None
    current_henry = (
        latest.henry_hub_price if latest else book.price_path.initial_market.henry_hub_price
    )
    current_basis = latest.chicago_basis if latest else book.price_path.initial_market.chicago_basis
    current_regional = (
        latest.chicago_price if latest else book.price_path.initial_market.regional_price
    )
    daily_futures = latest.daily_futures_pnl if latest else Decimal("0")
    cumulative_futures = latest.cumulative_futures_pnl if latest else Decimal("0")
    physical_pnl = latest.physical_economic_pnl if latest else Decimal("0")
    basis_effect = latest.basis_component if latest else Decimal("0")
    net_pnl = latest.net_economic_pnl if latest else Decimal("0")

    physical = Table(title="Physical exposure", box=box.SIMPLE, expand=True)
    physical.add_column("Field", width=25)
    physical.add_column("Value")
    physical.add_row("Quantity", f"{book.physical.quantity_mmbtu:,.0f} MMBtu")
    physical.add_row("Direction", "LONG physical / benefits from higher Chicago price")
    physical.add_row("Regional hub", book.physical.regional_hub)
    physical.add_row("Settlement date", str(book.physical.settlement_date))
    physical.add_row("Original regional price", f"${book.physical.original_regional_price:.3f}")
    physical.add_row("Current regional price", f"${current_regional:.3f}")

    futures = Table(title="Henry Hub futures", box=box.SIMPLE, expand=True)
    futures.add_column("Field", width=25)
    futures.add_column("Value")
    if book.position is None:
        futures.add_row("Position", "No futures position")
        futures.add_row("Hedge ratio", "0%")
    else:
        futures.add_row(
            "Position",
            f"{book.position.contracts} {book.position.side.value.upper()} contract(s)",
        )
        futures.add_row("Contract month", book.position.contract_month)
        futures.add_row(
            "Contract size",
            f"{book.position.contract_size_mmbtu:,.0f} MMBtu",
        )
        current_ratio = hedge_ratio(
            contracts=book.position.contracts,
            contract_size_mmbtu=book.position.contract_size_mmbtu,
            physical_quantity_mmbtu=book.physical.quantity_mmbtu,
        )
        futures.add_row(
            "Original / current hedge ratio", f"{book.ticket.hedge_ratio:.0%} / {current_ratio:.0%}"
        )
        futures.add_row("Entry price", f"${book.position.entry_price:.3f}")
        futures.add_row("Current price", f"${current_henry:.3f}")
    futures.add_row("Current Chicago basis", f"{current_basis:+.3f}")
    futures.add_row("Daily futures P&L", _signed_money(daily_futures))
    futures.add_row("Cumulative futures P&L", _signed_money(cumulative_futures))

    economics = Table(title="Economics & liquidity", box=box.SIMPLE, expand=True)
    economics.add_column("Field", width=25)
    economics.add_column("Value")
    economics.add_row("Physical economic P&L", _signed_money(physical_pnl))
    economics.add_row("Basis contribution", _signed_money(basis_effect))
    economics.add_row("Net economic P&L", _signed_money(net_pnl))
    economics.add_row("Operating cash", _money(state.corporate_cash))
    economics.add_row("FCM margin balance", _money(book.margin.balance))
    economics.add_row(
        "Initial / maintenance",
        f"{_money(book.margin.initial_requirement)} / "
        f"{_money(book.margin.maintenance_requirement)}",
    )
    call_status = (
        "None"
        if not book.margin.calls
        else (
            f"{len(book.margin.calls)} call(s); "
            f"{'all met' if all(item.met for item in book.margin.calls) else 'UNMET'}"
        )
    )
    economics.add_row("Margin-call status", call_status)
    console.print(Panel.fit(physical, title="POSITION BOOK"))
    console.print(futures)
    console.print(economics)


def render_settlement_day(
    console: Console,
    result: DailySettlementResult,
    *,
    show_explanation: bool = True,
) -> None:
    summary = Table(box=box.ROUNDED, expand=True)
    summary.add_column("Measure", width=28)
    summary.add_column("Result")
    summary.add_row(
        "Henry Hub move",
        f"${result.previous_henry_hub_price:.3f} to ${result.henry_hub_price:.3f}",
    )
    summary.add_row("Chicago basis", f"{result.chicago_basis:+.3f}")
    summary.add_row("Chicago price", f"${result.chicago_price:.3f}")
    summary.add_row("Daily futures P&L", _signed_money(result.daily_futures_pnl))
    summary.add_row(
        "Cumulative futures P&L",
        _signed_money(result.cumulative_futures_pnl),
    )
    summary.add_row("Physical economic P&L", _signed_money(result.physical_economic_pnl))
    summary.add_row("Basis contribution", _signed_money(result.basis_component))
    summary.add_row("Net economic P&L", _signed_money(result.net_economic_pnl))
    summary.add_row("Margin call", _money(result.margin_call_amount))
    summary.add_row("Operating cash", _money(result.operating_cash_end))
    summary.add_row("FCM margin after funding", _money(result.margin_balance_end))
    console.print(
        Panel(
            summary,
            title=f"SETTLEMENT DAY {result.day_number} · {result.settlement_date}",
            subtitle=result.event_title,
            border_style="magenta",
        )
    )
    console.print(result.event_text)
    if result.communication_from and result.margin_call_amount:
        console.print(
            Panel(
                result.communication_subject or "",
                title=f"INBOX · {result.communication_from}",
                border_style="red",
            )
        )
    if show_explanation:
        console.print(
            "[dim]Daily futures P&L is recognized cash settlement in the FCM "
            "account. Physical P&L is an economic mark only. The basis contribution "
            "shows the location risk Henry Hub futures do not remove.[/dim]"
        )


def render_hedge_book_report(console: Console, report: HedgeBookReport) -> None:
    console.print(
        Panel(
            report.why_it_worked_or_failed,
            title=f"HEDGE BOOK REPORT · {report.outcome_title}",
            border_style="bold cyan",
        )
    )
    position = Table(title="Position and final economics", box=box.ROUNDED, expand=True)
    position.add_column("Measure", width=31)
    position.add_column("Actual result")
    position.add_row(
        "Original physical exposure",
        f"{report.physical_quantity_mmbtu:,.0f} MMBtu at "
        f"${report.original_regional_price:.3f} Chicago",
    )
    position.add_row("Selected hedge ratio", f"{report.hedge_ratio:.0%}")
    position.add_row(
        "Futures position",
        f"{report.contracts} {report.futures_side.upper()} × "
        f"{report.contract_size_mmbtu:,.0f} MMBtu",
    )
    position.add_row("Classification", report.hedge_classification)
    position.add_row("Documentation", report.documentation_quality.value)
    position.add_row("Physical economic P&L", _signed_money(report.physical_economic_pnl))
    position.add_row(
        "Henry Hub physical component",
        _signed_money(report.henry_hub_physical_component),
    )
    position.add_row("Chicago basis effect", _signed_money(report.basis_effect))
    position.add_row("Futures P&L / variation", _signed_money(report.futures_pnl))
    position.add_row("Net economic P&L", _signed_money(report.net_economic_pnl))
    console.print(position)

    daily = Table(title="Daily settlement history", box=box.SIMPLE_HEAVY, expand=True)
    daily.add_column("Date")
    daily.add_column("HH", justify="right")
    daily.add_column("Basis", justify="right")
    daily.add_column("Chicago", justify="right")
    daily.add_column("Daily VM", justify="right")
    daily.add_column("Call", justify="right")
    for item in report.settlements:
        daily.add_row(
            str(item.settlement_date),
            f"{item.henry_hub_price:.2f}",
            f"{item.chicago_basis:+.2f}",
            f"{item.chicago_price:.2f}",
            f"{item.daily_futures_pnl:+,.0f}",
            f"{item.margin_call_amount:,.0f}",
        )
    console.print(daily)

    bridge = report.liquidity
    liquidity = Table(title="Liquidity bridge", box=box.ROUNDED, expand=True)
    liquidity.add_column("Movement")
    liquidity.add_column("Operating cash", justify="right")
    liquidity.add_column("FCM margin cash", justify="right")
    liquidity.add_column("Total liquidity", justify="right")
    liquidity.add_row(
        "Beginning balances",
        _money(bridge.beginning_operating_cash),
        "$0.00",
        _money(bridge.beginning_operating_cash),
    )
    liquidity.add_row(
        "Initial margin deposit",
        _signed_money(-bridge.initial_margin_deposit),
        _signed_money(bridge.initial_margin_deposit),
        "$0.00",
    )
    liquidity.add_row(
        "Daily variation settlement",
        "$0.00",
        _signed_money(bridge.daily_variation_margin),
        _signed_money(bridge.daily_variation_margin),
    )
    liquidity.add_row(
        "Additional margin deposits",
        _signed_money(-bridge.additional_margin_deposits),
        _signed_money(bridge.additional_margin_deposits),
        "$0.00",
    )
    liquidity.add_row(
        "Final margin release",
        _signed_money(bridge.margin_released),
        _signed_money(-bridge.margin_released),
        "$0.00",
    )
    if bridge.other_operating_cash_activity:
        liquidity.add_row(
            "Treasury / other cash activity",
            _signed_money(bridge.other_operating_cash_activity),
            "$0.00",
            _signed_money(bridge.other_operating_cash_activity),
        )
    liquidity.add_row(
        "Ending balances",
        _money(bridge.ending_operating_cash),
        _money(bridge.ending_margin_cash),
        _money(bridge.ending_operating_cash + bridge.ending_margin_cash),
    )
    liquidity.caption = (
        "Operating cash reconciles: "
        f"{bridge.operating_cash_reconciles}; total liquidity reconciles: "
        f"{bridge.total_liquidity_reconciles}"
    )
    console.print(liquidity)

    journal_text = (
        "\n".join(report.journal_entries)
        if report.journal_entries
        else "No futures or margin journal entries were required."
    )
    console.print(
        Panel(
            journal_text,
            title=(
                "Simplified recognized journal entries · "
                f"balanced={report.journal_entries_balanced}"
            ),
        )
    )
    console.print(
        Panel(
            "The forecast physical sale was economically marked but not recognized "
            "in the simplified ledger. Futures variation was recognized in earnings "
            "and FCM cash. Margin deposits and releases were balance-sheet transfers.",
            title="Economic value versus accounting recognition",
        )
    )
    console.print(
        Panel(
            "Series 3: "
            + ", ".join(report.series_3_concepts)
            + "\nAccounting / controls: "
            + ", ".join(report.accounting_concepts),
            title="Concepts encountered",
        )
    )
    console.print(
        Panel(
            "\n".join(f"• {item}" for item in report.simplified_assumptions),
            title="Simplified fictional assumptions",
        )
    )
    console.print(
        "[dim]Educational fiction only—not legal, tax, accounting, trading, "
        "or investment advice.[/dim]"
    )
