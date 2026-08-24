"""Rich terminal rendering, intentionally free of game mutations."""

from __future__ import annotations

from decimal import Decimal

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from lake_effect_ledger.education.report import LearningReport
from lake_effect_ledger.narrative.models import CharacterFile, SceneDefinition
from lake_effect_ledger.state import GameState
from lake_effect_ledger.treasury.models import CharacterDefinition


def _money(value: Decimal) -> str:
    return f"${value:,.2f}"


def render_title(console: Console) -> None:
    title = Text("LAKE EFFECT LEDGER", style="bold cyan", justify="center")
    subtitle = Text(
        "Every number has a story. Which one will you sign?",
        style="italic white",
        justify="center",
    )
    console.print(Panel(Text.assemble(title, "\n", subtitle), border_style="blue"))


def render_character_introduction(
    console: Console,
    character: CharacterDefinition,
) -> None:
    body = (
        f"[bold]{character.name}[/bold]\n"
        f"{character.role}\n"
        f"[cyan]{character.origin}[/cyan]\n\n"
        f"{character.public_detail}\n"
        f"[dim]{character.interaction_reason}[/dim]"
    )
    console.print(Panel(body, title="NEW CONTACT", border_style="bright_blue"))


def render_background_selection(
    console: Console,
    characters: CharacterFile,
) -> None:
    selection = characters.background_selection
    console.print(
        Panel(
            f"{selection.introduction}\n\n{selection.equivalence_note}",
            title="Your path into Northstar",
            border_style="cyan",
        )
    )
    for background in characters.backgrounds:
        skills = background.skills
        body = (
            f"[italic]{background.description}[/italic]\n\n"
            f"[bold]Prior experience:[/bold] {background.prior_experience}\n"
            f"[bold]Strongest starting area:[/bold] {background.starting_strength}\n"
            f"[bold]Learning edge:[/bold] {background.learning_edge}\n"
            f"[bold]Why Northstar hired you:[/bold] {background.hiring_reason}\n"
            f"[bold]Skills:[/bold] Accounting {skills.accounting} · "
            f"Markets {skills.markets} · Analytics {skills.analytics}"
        )
        console.print(Panel(body, title=background.label, border_style="blue"))


def render_dashboard(console: Console, state: GameState) -> None:
    heading = Table.grid(expand=True)
    heading.add_column(justify="left")
    heading.add_column(justify="right")
    heading.add_row(
        f"[bold]{state.current_date:%B %d, %Y}[/bold] · Milwaukee, Wisconsin",
        f"Seed [cyan]{state.seed}[/cyan]",
    )
    heading.add_row(
        f"Corporate cash: [green]{_money(state.corporate_cash)}[/green]",
        f"Personal cash: {_money(state.personal_cash)}",
    )
    heading.add_row(
        f"Margin due: [yellow]{_money(state.margin_due)}[/yellow]",
        f"Player: {state.player.name} · {state.player.background.value.replace('_', ' ').title()}",
    )
    heading.add_row(
        f"Henry Hub: ${state.market.henry_hub_price:.2f}/MMBtu",
        f"Chicago basis: {state.market.chicago_basis:+.2f}/MMBtu",
    )
    heading.add_row(
        f"[dim]{state.market.label} — all prices are fictional[/dim]",
        "",
    )
    console.print(Panel(heading, title="NORTHSTAR MORNING BOOK", border_style="cyan"))

    resources = Table(title="Standing & Risk", box=box.SIMPLE_HEAVY, expand=True)
    for label in ("Reputation", "Family loyalty", "Integrity", "Audit risk", "Regulatory heat"):
        resources.add_column(label, justify="center")
    resources.add_row(
        str(state.resources.reputation),
        str(state.resources.family_loyalty),
        str(state.resources.integrity),
        str(state.resources.audit_risk),
        str(state.resources.regulatory_heat),
    )
    console.print(resources)

    inbox = Table(title="Inbox", box=box.SIMPLE, expand=True)
    inbox.add_column("", width=3)
    inbox.add_column("From")
    inbox.add_column("Subject")
    for item in state.inbox:
        inbox.add_row("[red]![/red]" if item.urgent else "·", item.sender, item.subject)
    console.print(inbox)


def render_scene(console: Console, scene: SceneDefinition) -> None:
    console.print(Panel(scene.text, title=scene.title, subtitle=scene.speaker.replace("_", " ")))
    if scene.discrepancy is None:
        return
    values = Table(title="December volume reconciliation", box=box.ROUNDED)
    values.add_column("Measure")
    values.add_column("Amount", justify="right")
    values.add_row("Metered gas received", f"{scene.discrepancy.metered_mmbtu:,} MMBtu")
    values.add_row(
        "Contract settlement volume",
        f"{scene.discrepancy.settlement_mmbtu:,} MMBtu",
    )
    values.add_row(
        "Unexplained difference",
        f"[bold yellow]{scene.discrepancy.difference_mmbtu:,} MMBtu[/bold yellow]",
    )
    values.add_row("December index", f"${scene.discrepancy.index_price:.2f}/MMBtu")
    values.add_row(
        "Potential exposure",
        f"[bold]{_money(scene.discrepancy.exposure)}[/bold]",
    )
    console.print(values)


def render_end_of_day(console: Console, state: GameState) -> None:
    for message in state.end_of_day_messages:
        console.print(Panel(message, title="End-of-day consequence", border_style="magenta"))


def render_learning_report(console: Console, report: LearningReport) -> None:
    table = Table(title="End-of-day learning report", box=box.ROUNDED, expand=True)
    table.add_column("Area", style="bold cyan", width=24)
    table.add_column("What happened")
    table.add_row("Accounts changed", "\n".join(report.accounts_changed))
    if report.journal_balanced is None:
        journal_status = "No journal entry posted."
    else:
        journal_status = "Balanced: yes" if report.journal_balanced else "Balanced: no"
    table.add_row("Journal validation", journal_status)
    table.add_row("Financial statements", "\n".join(report.financial_statement_effects))
    table.add_row("Control / evidence", "\n".join(report.control_and_evidence_notes))
    table.add_row("Objectives", "\n".join(report.objectives_encountered))
    console.print(table)
    console.print(
        "[dim]Educational fiction only—not legal, tax, accounting, trading, "
        "or investment advice.[/dim]"
    )


def render_debug(console: Console, state: GameState) -> None:
    debug = Table(title="DEBUG · state transitions", box=box.MINIMAL_DOUBLE_HEAD, expand=True)
    debug.add_column("#", justify="right", width=4)
    debug.add_column("Phase")
    debug.add_column("Type")
    debug.add_column("Source")
    debug.add_column("Changes")
    for record in state.event_log:
        debug.add_row(
            str(record.sequence),
            record.phase,
            record.event_type,
            record.source_id,
            repr(record.changes),
        )
    console.print(debug)
    market_path_debug = ""
    if state.hedge_book is not None:
        path = state.hedge_book.price_path
        prices = [
            (
                path.initial_market.settlement_date,
                path.initial_market.henry_hub_price,
                path.initial_market.chicago_basis,
            ),
            *[
                (item.settlement_date, item.henry_hub_price, item.chicago_basis)
                for item in path.settlements
            ],
        ]
        market_path_debug = f"\nSelected market path: {path.id}\nFull embedded path: {prices}"
    diligence_debug = ""
    if state.diligence_room is not None:
        diligence_debug = (
            f"\nDiligence path: {state.diligence_room.selected_story_path_id}"
            f"\nDiligence stage: {state.diligence_room.current_stage.value}"
            f"\nDiligence flags: {state.diligence_room.diligence_flags}"
            f"\nDiligence outcome: "
            f"{state.diligence_room.outcome.value if state.diligence_room.outcome else None}"
        )
    console.print(
        Panel(
            f"Seed: {state.seed}\n"
            f"Flags: {state.flags}\n"
            f"Pending events: {[item.model_dump() for item in state.scheduled_events]}\n"
            f"Career tag weights: {state.career_trajectory.tag_weights}\n"
            f"Career tendencies: {state.career_trajectory.tendencies}"
            f"{market_path_debug}"
            f"{diligence_debug}",
            title="DEBUG · reproducibility",
            border_style="yellow",
        )
    )
