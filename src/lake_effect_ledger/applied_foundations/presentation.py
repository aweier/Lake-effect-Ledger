"""Rich terminal presentation for Applied Foundations."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lake_effect_ledger.applied_foundations.models import (
    AppliedChoiceDefinition,
    AppliedDayDefinition,
    AppliedFoundationsBlueprint,
)
from lake_effect_ledger.applied_foundations.review import AppliedReviewDiagnostic
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.state import GameState


def render_season_opening(console: Console, blueprint: AppliedFoundationsBlueprint) -> None:
    console.print(
        Panel(
            "A pipeline restriction creates a confirmed Chicago replacement-gas need. "
            "You remain a supervised Junior Commodity Risk Analyst: you reconcile, "
            "calculate, and prepare; supervisors authorize and transmit.\n\n"
            + blueprint.season.supplement_limit,
            title="Applied Foundations · The Supply Gap",
            border_style="cyan",
        )
    )


def render_applied_day(console: Console, day: AppliedDayDefinition) -> None:
    console.print(
        Panel(
            "\n".join(f"• {item}" for item in day.teaching_points),
            title=f"Day {day.day_number} — {day.title} · Milwaukee HQ",
            border_style="blue",
        )
    )


def render_decision_result(console: Console, choice: AppliedChoiceDefinition) -> None:
    console.print(
        Panel(
            choice.text,
            title="Record created",
            border_style="green",
        )
    )


def render_order_tape(
    console: Console,
    state: GameState,
    content: ContentBundle,
) -> None:
    tape = content.applied_foundations.order_tape
    console.print(
        Panel(
            f"Current market ${tape.current_price:.3f}; subsequent authored prices "
            + " → ".join(f"${item:.3f}" for item in tape.subsequent_prices),
            title="Hypothetical authored tape",
            border_style="cyan",
        )
    )
    table = Table(title="Authored order comparison · full-fill training assumption")
    table.add_column("Order")
    table.add_column("Result")
    table.add_column("Price")
    for item in state.applied_foundations.financial.order_results:
        table.add_row(
            item.order_type.title(),
            "Triggered and filled" if item.triggered else ("Filled" if item.filled else "Unfilled"),
            f"${item.fill_price:.3f}" if item.fill_price is not None else "—",
        )
    console.print(table)
    console.print(
        Panel(
            "These outcomes are one fictional authored tape. They do not model depth, "
            "partial fills, slippage, or guaranteed real-market behavior.",
            title="Applicability limit",
            border_style="yellow",
        )
    )


def render_financial_bridge(console: Console, state: GameState) -> None:
    values = state.applied_foundations.financial.calculations
    table = Table(title="Cash Before Gas · engine-backed reconciliation")
    table.add_column("Measure")
    table.add_column("Amount", justify="right")
    rows = (
        ("Initial Chicago price", f"${values['initial_chicago_price']:,.3f}/MMBtu"),
        ("Final Chicago price", f"${values['final_chicago_price']:,.3f}/MMBtu"),
        (
            "Favorable physical purchase-cost variance",
            f"${values['physical_purchase_cost_variance']:,.2f}",
        ),
        ("Long-futures variation loss", f"-${-values['long_futures_result']:,.2f}"),
        ("Favorable buyer basis effect", f"${values['buyer_basis_effect']:,.2f}"),
        ("Combined economic result", f"${values['combined_economic_result']:,.2f} favorable"),
        ("Initial margin", f"${values['initial_margin']:,.2f}"),
        ("Maintenance margin", f"${values['maintenance_margin']:,.2f}"),
        ("Post-settlement margin balance", f"${values['post_settlement_margin']:,.2f}"),
        ("Margin call to restore initial margin", f"${values['margin_call']:,.2f}"),
    )
    for row in rows:
        table.add_row(*row)
    console.print(table)
    console.print(
        Panel(
            "The physical purchase has not occurred, so $44,000 is a favorable "
            "purchase-cost variance—not realized physical P&L. The $36,000 margin "
            "funding transfer restores the FCM asset after the $36,000 variation loss; "
            "it is not a second loss.",
            title="Economic result versus cash timing",
            border_style="magenta",
        )
    )


def render_applied_diagnostic(
    console: Console,
    diagnostic: AppliedReviewDiagnostic,
) -> None:
    console.print(
        Panel(
            (
                f"Required first attempts: {diagnostic.required_first_attempt_correct}/"
                f"{diagnostic.required_questions}\n"
                f"Final required answers: {diagnostic.required_final_correct}/"
                f"{diagnostic.required_questions}\n"
                f"Calculations: {diagnostic.calculation_first_attempt_correct}/"
                f"{diagnostic.calculation_total} first-attempt correct\n"
                f"Concepts: {diagnostic.conceptual_first_attempt_correct}/"
                f"{diagnostic.conceptual_total} first-attempt correct\n"
                f"Hints: {diagnostic.hints_used}; walkthroughs: "
                f"{diagnostic.walkthroughs_used}\n"
                "Targeted remediation: "
                + (
                    ", ".join(diagnostic.recommended_remediation_categories)
                    if diagnostic.recommended_remediation_categories
                    else "none recommended"
                )
            ),
            title="Applied Foundations diagnostic",
            border_style="magenta",
        )
    )


def render_applied_debrief(
    console: Console,
    state: GameState,
    content: ContentBundle,
) -> None:
    chapter = state.applied_foundations
    upgraded = [
        content.curriculum_objective(objective_id).game_concept_label
        for objective_id in content.applied_foundations.season.coverage_upgrades
    ]
    console.print(
        Panel(
            (
                "The Supply Gap is complete. Core results remain historical; this "
                "season's later evidence is reported separately. The historical Core "
                "classification remains six covered, three partially covered, and "
                "four introductory among 13 encountered objectives.\n\n"
                f"Evidence quality: {chapter.evidence_score}; documentation quality: "
                f"{chapter.documentation_score}; communication quality: "
                f"{chapter.communication_score}.\n\n"
                "Applied evidence overlay:\n- " + "\n- ".join(upgraded) + "\n\n"
                "Applied Foundations deepens a narrow group of implemented Series 3 "
                "concepts. Completion does not imply exam readiness and does not cover "
                "most options or regulatory material."
            ),
            title="Applied Foundations Debrief",
            border_style="green",
        )
    )
