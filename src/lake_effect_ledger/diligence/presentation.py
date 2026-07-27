"""Rich terminal views for The Diligence Room."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lake_effect_ledger.diligence.models import (
    DiligenceOutcome,
    DiligenceSceneDefinition,
)
from lake_effect_ledger.diligence.report import DiligenceRoomReport
from lake_effect_ledger.state import GameState

OUTCOME_TITLES = {
    DiligenceOutcome.CLEAN_ROOM: "Clean Room",
    DiligenceOutcome.PRICE_OF_CANDOR: "The Price of Candor",
    DiligenceOutcome.THREE_VERSIONS_OF_MONDAY: "Three Versions of Monday",
    DiligenceOutcome.REMEDIATION_ON_PAPER: "Remediation on Paper",
    DiligenceOutcome.COVENANT_CONVERSATION: "The Covenant Conversation",
    DiligenceOutcome.BELLANDI_CONFIDENCE: "Bellandi Confidence",
    DiligenceOutcome.BUYER_WALKS: "Buyer Walks",
    DiligenceOutcome.CONDITIONAL_CLOSE: "Conditional Close",
}


def render_diligence_scene(
    console: Console,
    state: GameState,
    scene: DiligenceSceneDefinition,
) -> None:
    diligence = state.diligence_room
    prior = ""
    if scene.id == "dr_committee_position" and diligence is not None:
        open_inconsistencies = sum(
            1 for item in diligence.inconsistencies if item.corrected_by_package_id is None
        )
        prior = (
            "\n\n[dim]Prior conduct: "
            f"Noah trust {diligence.relationships.get('noah_shah', 0):+d}; "
            f"Evelyn trust {diligence.relationships.get('evelyn_marsh', 0):+d}; "
            f"open inconsistencies {open_inconsistencies}."
            "[/dim]"
        )
    console.print(
        Panel(
            f"[bold]{scene.speaker}[/bold]\n\n{scene.text}{prior}",
            title=f"Day {scene.day}: {scene.title}",
            border_style="cyan",
        )
    )


def render_request_list(console: Console, state: GameState) -> None:
    diligence = state.diligence_room
    if diligence is None:
        return
    table = Table(title="Diligence Request Lists", show_lines=False)
    table.add_column("Stakeholder")
    table.add_column("Requested item")
    table.add_column("Status")
    table.add_column("Source records")
    for request in diligence.requests:
        stakeholder = next(
            item for item in diligence.stakeholders if item.stakeholder_id == request.stakeholder_id
        )
        for item in request.items:
            table.add_row(
                stakeholder.name,
                item.label,
                item.status.value.replace("_", " "),
                ", ".join(item.source_record_ids) or "none",
            )
    console.print(table)


def render_package_versions(console: Console, state: GameState) -> None:
    diligence = state.diligence_room
    if diligence is None:
        return
    table = Table(title="Delivered Package Versions")
    table.add_column("Package")
    table.add_column("Audience")
    table.add_column("Version", justify="right")
    table.add_column("Kind")
    table.add_column("Included / omitted")
    table.add_column("Delivered")
    table.add_column("Reviewed by")
    for package in diligence.packages:
        for version in package.versions:
            table.add_row(
                package.package_id,
                package.intended_stakeholder_id,
                str(version.version),
                version.change_kind,
                f"{len(version.included_item_ids)} / {len(version.omitted_requested_item_ids)}",
                version.delivered_at.isoformat() if version.delivered_at else "not delivered",
                ", ".join(version.reviewed_by_ids) or "unreviewed",
            )
    console.print(table)


def render_risk_schedule(console: Console, state: GameState) -> None:
    diligence = state.diligence_room
    if diligence is None or diligence.risk_schedule is None:
        return
    table = Table(title="Commodity, Liquidity, and Control Schedule")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_column("Source")
    for metric in diligence.risk_schedule.metrics:
        value = metric.value_text
        if metric.unit:
            value = f"{value} {metric.unit}"
        table.add_row(metric.label, value, ", ".join(metric.source_record_ids))
    console.print(table)
    significance = diligence.risk_schedule.significance
    console.print(
        Panel(
            f"Fictional review threshold: ${significance.review_threshold:,.2f}\n"
            f"Amount considered: ${significance.amount_considered:,.2f}\n"
            f"Qualitative factors: {', '.join(significance.qualitative_factors)}\n\n"
            f"[dim]{significance.caveat}[/dim]",
            title="Significance — Amount and Context",
            border_style="yellow",
        )
    )


def render_scenario_analysis(console: Console, state: GameState) -> None:
    diligence = state.diligence_room
    if diligence is None or diligence.scenario_analysis is None:
        return
    table = Table(title="Fictional Commodity Sensitivities — Not a Forecast")
    table.add_column("Case")
    table.add_column("Physical", justify="right")
    table.add_column("Futures", justify="right")
    table.add_column("Basis component", justify="right")
    table.add_column("Net", justify="right")
    table.add_column("VM cash", justify="right")
    table.add_column("Headroom", justify="right")
    for row in diligence.scenario_analysis.rows:
        table.add_row(
            row.label,
            f"${row.physical_economic_effect:,.2f}",
            f"${row.futures_effect:,.2f}",
            f"${row.basis_effect:,.2f}",
            f"${row.net_economic_effect:,.2f}",
            f"${row.estimated_variation_margin_cash_movement:,.2f}",
            f"${row.resulting_liquidity_headroom:,.2f}",
        )
    console.print(table)
    console.print(
        "[dim]No probabilities assigned. Assumptions are fictional. Results do not "
        "alter game state and are not accounting entries.[/dim]"
    )


def render_q_and_a(console: Console, state: GameState) -> None:
    diligence = state.diligence_room
    if diligence is None:
        return
    responses = {item.question_id: item for item in diligence.responses}
    table = Table(title="Timestamped Diligence Q&A", show_lines=True)
    table.add_column("Stakeholder")
    table.add_column("Question / response")
    table.add_column("Posture")
    table.add_column("Sources")
    for question in diligence.questions:
        response = responses.get(question.question_id)
        if response is None:
            continue
        table.add_row(
            question.stakeholder_id,
            f"{question.text}\n[dim]{response.text}[/dim]",
            response.posture.value.replace("_", " "),
            ", ".join(response.source_record_ids),
        )
    console.print(table)


def render_diligence_room_report(
    console: Console,
    report: DiligenceRoomReport,
) -> None:
    console.print(
        Panel(
            f"[bold]{OUTCOME_TITLES[report.outcome]}[/bold]\n"
            f"Transaction status: {report.transaction_status.value.replace('_', ' ')}\n"
            f"Structure: {report.transaction_structure}\n"
            f"Package versions: "
            f"{sum(len(item.versions) for item in report.package_versions)}\n"
            f"Unresolved issues: {len(report.unresolved_issues)}\n"
            "Source reconciliation: "
            f"{'passed' if report.reconciled_to_source_records else 'failed'}\n"
            f"Original deliveries preserved: "
            f"{'yes' if report.original_package_versions_preserved else 'no'}",
            title=report.title,
            border_style="green" if report.outcome != DiligenceOutcome.BUYER_WALKS else "red",
        )
    )
    reactions = Table(title="Stakeholder Reactions")
    reactions.add_column("Stakeholder")
    reactions.add_column("Trust", justify="right")
    reactions.add_column("Reaction")
    reactions.add_column("Follow-up")
    for item in report.stakeholder_reactions:
        reactions.add_row(
            item.stakeholder_id,
            f"{item.trust_delta:+d}",
            item.reaction,
            item.requested_follow_up or "none",
        )
    console.print(reactions)
    console.print("[bold]Career consequences[/bold]")
    for item in report.career_consequences:
        console.print(f"  - {item}")
    console.print("[bold]Practiced concepts[/bold]")
    for item in report.practiced_learning_objectives:
        console.print(f"  - {item}")
