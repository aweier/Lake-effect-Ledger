"""Rich terminal views for the live book, blotter, and Analyst Case File."""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lake_effect_ledger.narrative.engine import NarrativeEngine
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.state import GameState
from lake_effect_ledger.trading.report import AnalystCaseFile


def _money(value) -> str:
    return f"${value:,.2f}"


def render_live_week_brief(console: Console, state: GameState, content: ContentBundle) -> None:
    scenario = content.eleventh_scenario
    table = Table(title="NORTHSTAR LIVE BOOK · Monday morning", box=box.ROUNDED)
    table.add_column("Input")
    table.add_column("Current record", justify="right")
    table.add_row("Henry Hub", f"${scenario.initial_henry_hub_price:.3f}/MMBtu")
    table.add_row("Chicago basis", f"${scenario.chicago_basis:.3f}/MMBtu")
    table.add_row("Supported physical volume", f"{scenario.supported_volume_mmbtu:,.0f} MMBtu")
    table.add_row(
        "Possible additional volume",
        f"{scenario.possible_additional_volume_mmbtu:,.0f} MMBtu · unsupported",
    )
    table.add_row("Current futures position", "0 contracts")
    table.add_row("Existing hedge ratio", "0%")
    table.add_row("Operating cash", _money(state.corporate_cash))
    if state.treasury is not None:
        table.add_row("Prior treasury outcome", state.treasury.outcome.value)
    console.print(table)
    console.print(
        Panel(
            f"Weather: {scenario.weather_information}\n\n"
            f"Pipeline: {scenario.pipeline_information}\n\n"
            f"Available sources:\n- " + "\n- ".join(scenario.data_sources),
            title="Morning note source pack",
            border_style="cyan",
        )
    )


def render_chapter_scene(
    console: Console,
    state: GameState,
    content: ContentBundle,
    scene_id: str,
) -> None:
    scene = content.scene(scene_id)
    text = NarrativeEngine(content).resolved_scene_text(state, scene_id)
    console.print(Panel(text, title=scene.title, subtitle=scene.speaker, border_style="cyan"))


def render_order_and_authorization(
    console: Console,
    state: GameState,
    content: ContentBundle,
    debug: bool = False,
) -> None:
    chapter = state.eleventh_contract
    authorization = chapter.authorization
    order = chapter.order
    execution = chapter.execution
    confirmation = chapter.confirmation
    table = Table(title="Authorization -> Order -> Execution -> Confirmation")
    table.add_column("Record")
    table.add_column("Quantity", justify="right")
    table.add_column("Side")
    table.add_column("Price")
    table.add_column("Owner / status")
    table.add_row(
        authorization.authorization_id,
        str(authorization.maximum_quantity),
        authorization.side.value,
        "—",
        f"{authorization.approver_id} · {authorization.status.value}",
    )
    table.add_row(
        order.order_id,
        str(order.quantity),
        order.side.value,
        f"${order.fill_price:.3f}",
        f"{order.transmitting_user_id} · {order.status.value}",
    )
    table.add_row(
        execution.execution_id,
        str(execution.quantity),
        execution.side.value,
        f"${execution.fill_price:.3f}",
        execution.transmitting_user_id,
    )
    table.add_row(
        confirmation.confirmation_id,
        str(confirmation.quantity),
        confirmation.side.value,
        f"${confirmation.fill_price:.3f}",
        confirmation.fcm_name,
    )
    console.print(table)
    if debug:
        path = content.eleventh_scenario.intraday_path
        console.print(
            Panel(
                f"Selected path: {path.id}\n"
                f"Full path: "
                f"{[(item.timestamp.isoformat(), str(item.price)) for item in path.points]}",
                title="DEBUG · intraday path",
                border_style="yellow",
            )
        )


def render_trade_blotter(console: Console, state: GameState) -> None:
    chapter = state.eleventh_contract
    blotter = chapter.blotter
    position = chapter.position
    table = Table(title="TRADE BLOTTER · The Eleventh Contract", box=box.ROUNDED)
    table.add_column("Field")
    table.add_column("Recorded value", justify="right")
    table.add_row("Internal order", f"{blotter.internal_quantity} {blotter.side.value}")
    table.add_row("Authorization", f"{chapter.authorization.maximum_quantity} maximum")
    table.add_row("FCM confirmation", f"{blotter.confirmed_quantity} contracts")
    table.add_row("Fill price", f"${blotter.fill_price:.3f}")
    table.add_row("Current settlement", f"${blotter.current_settlement_price:.3f}")
    table.add_row("Latest daily P&L", _money(blotter.daily_pnl))
    table.add_row("Margin requirement", _money(blotter.margin_requirement))
    table.add_row("FCM margin balance", _money(position.margin.balance))
    table.add_row(
        "Supported physical volume",
        f"{blotter.supported_physical_volume_mmbtu:,.0f} MMBtu",
    )
    table.add_row("Hedge ratio", f"{blotter.hedge_ratio:.0%}")
    table.add_row("Exception", f"+{blotter.exception_contracts} contract")
    table.add_row("Reviewer", blotter.reviewer_id or "Pending")
    table.add_row("Status", blotter.status.value.replace("_", " ").title())
    console.print(table)


def render_case_file(console: Console, report: AnalystCaseFile) -> None:
    console.print(
        Panel(
            report.outcome_summary,
            title=f"ANALYST CASE FILE · {report.outcome_title}",
            border_style="green",
        )
    )
    trade = Table(title="Trade and exposure reconciliation", box=box.ROUNDED)
    trade.add_column("Measure")
    trade.add_column("Result", justify="right")
    trade.add_row(
        "Original supported physical",
        f"{report.original_physical_exposure_mmbtu:,.0f} MMBtu",
    )
    trade.add_row(
        "Possible additional physical",
        f"{report.possible_additional_volume_mmbtu:,.0f} MMBtu",
    )
    trade.add_row(
        "Eventually supported",
        f"{report.eventual_supported_volume_mmbtu:,.0f} MMBtu",
    )
    trade.add_row(
        "Authorized / executed",
        f"{report.authorized_contracts} / {report.executed_contracts}",
    )
    trade.add_row("Order / fill", f"{report.order_type} / ${report.fill_price:.3f}")
    trade.add_row(
        "Initial / final hedge ratio",
        f"{report.initial_hedge_ratio:.0%} / {report.final_hedge_ratio:.0%}",
    )
    trade.add_row("Physical economic P&L", _money(report.physical_economic_pnl))
    trade.add_row("Total futures P&L", _money(report.total_futures_pnl))
    trade.add_row("Extra-contract P&L", _money(report.extra_contract_pnl))
    trade.add_row(
        "Extra-contract initial margin",
        _money(report.extra_contract_initial_margin),
    )
    trade.add_row(
        "Operating cash movement",
        f"{_money(report.beginning_operating_cash)} -> "
        f"{_money(report.ending_operating_cash)} "
        f"({_money(report.net_operating_cash_movement)})",
    )
    trade.add_row("Ending FCM margin", _money(report.ending_margin_balance))
    trade.add_row(
        "Offset",
        (
            f"Yes · ${report.offset_price:.3f} · P&L {_money(report.offset_pnl)}"
            if report.extra_contract_offset
            else "No"
        ),
    )
    trade.add_row(
        "Blotter status",
        f"{report.original_blotter_status.value} -> {report.final_blotter_status.value}",
    )
    console.print(trade)

    evidence = Table(title="Evidence, controls, and development")
    evidence.add_column("Area")
    evidence.add_column("State-derived record")
    evidence.add_row(
        "Reconciliation",
        report.reconciliation_record_id or "Legacy blotter record",
    )
    evidence.add_row("Notifications", "\n".join(report.notifications) or "None")
    evidence.add_row("Approvals", "\n".join(report.approvals) or "None")
    evidence.add_row(
        "Physical support",
        "\n".join(report.physical_support_documents) or "No additional support",
    )
    evidence.add_row("Communications", "\n".join(report.communications) or "None")
    evidence.add_row(
        "Certification",
        (
            f"Certified · {report.certification_record_id}"
            if report.reconciliation_certified
            else "Not certified"
        ),
    )
    evidence.add_row("Accounting entries", "\n".join(report.accounting_entries))
    evidence.add_row(
        "Balanced",
        str(report.accounting_entries_balanced),
    )
    evidence.add_row("Career development", "\n".join(report.career_development))
    evidence.add_row("Relationships", "\n".join(report.relationships_affected))
    evidence.add_row("Series 3", "\n".join(report.series_3_objectives) or "On request")
    console.print(evidence)
    console.print(
        Panel(
            "\n".join(f"- {item}" for item in report.simplifying_assumptions),
            title="Simplified fictional fill assumptions",
            border_style="dim",
        )
    )
