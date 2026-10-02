"""Rich terminal views for The Notice Window."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lake_effect_ledger.applied_foundations.models import (
    AppliedChoiceDefinition,
    AppliedDayDefinition,
)
from lake_effect_ledger.applied_foundations.review import AppliedReviewDiagnostic
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.notice_window.models import NoticeWindowBlueprint
from lake_effect_ledger.state import GameState


def render_notice_opening(console: Console, blueprint: NoticeWindowBlueprint) -> None:
    console.print(
        Panel(
            "The FCM expiration report shows two open March Henry Hub contracts. "
            "Northstar does not intend delivery, and its internal action deadline is "
            "approaching. You must separate the exchange calendar from the internal "
            "calendar, explain what the curve says, and preserve the offset record.\n\n"
            + blueprint.season.supplement_limit,
            title="Market Structure · The Notice Window",
            border_style="cyan",
        )
    )


def render_notice_day(console: Console, day: AppliedDayDefinition) -> None:
    console.print(
        Panel(
            "\n".join(f"• {item}" for item in day.teaching_points),
            title=f"Day {day.day_number} — {day.title} · Milwaukee HQ",
            border_style="blue",
        )
    )


def render_notice_decision_result(console: Console, choice: AppliedChoiceDefinition) -> None:
    console.print(Panel(choice.text, title="Record created", border_style="green"))


def render_notice_calendar(console: Console, blueprint: NoticeWindowBlueprint) -> None:
    scenario = blueprint.scenario
    table = Table(title="March NG · contract and internal calendar")
    table.add_column("Date")
    table.add_column("Boundary")
    table.add_row(
        scenario.northstar_internal_action_deadline.isoformat(),
        "Northstar fictional action deadline",
    )
    table.add_row(
        scenario.exchange_last_trading_day.isoformat(),
        "Authored Chapter 220 last trading day",
    )
    table.add_row(scenario.exchange_notice_day.isoformat(), "Authored Notice Day")
    table.add_row(scenario.delivery_month_start.isoformat(), "Delivery month begins")
    console.print(table)
    console.print(
        Panel(
            "The internal deadline is an earlier Northstar control. It does not alter "
            "the exchange rule or guarantee that an order can be filled.",
            title="Calendar boundary",
            border_style="yellow",
        )
    )


def render_notice_curves(console: Console, state: GameState, content: ContentBundle) -> None:
    scenario = content.notice_window.scenario
    values = state.notice_window.curve_calculations
    table = Table(title="Two-month fictional curve · deferred minus nearby")
    table.add_column("State")
    table.add_column("Nearby", justify="right")
    table.add_column("Deferred", justify="right")
    table.add_column("Spread", justify="right")
    table.add_row(
        "Normal / contango",
        f"${scenario.normal_curve.nearby_price:.3f}",
        f"${scenario.normal_curve.deferred_price:.3f}",
        f"${values['normal_spread']:.3f}",
    )
    table.add_row(
        "Inverted / backwardation",
        f"${scenario.inverted_curve.nearby_price:.3f}",
        f"${scenario.inverted_curve.deferred_price:.3f}",
        f"${values['inverted_spread']:.3f}",
    )
    console.print(table)
    console.print(
        Panel(
            f"Authored carry estimate: ${scenario.authored_carry_estimate:.3f}/MMBtu. "
            "Normal-curve residual after that estimate: "
            f"${values['normal_residual_after_carry']:.3f}/MMBtu. Curve shape is "
            "not a guaranteed forecast and does not prove a single cause.",
            title="Interpretation limit",
            border_style="yellow",
        )
    )


def render_notice_resolution(console: Console, state: GameState) -> None:
    console.print(
        Panel(
            "Two sell contracts offset the two season-local March longs under Cal's "
            "authorization and supervised transmission. Open contracts after the "
            f"offset: {state.notice_window.remaining_contracts}. The original "
            "position, authorization, execution, confirmation, and reconciliation "
            "records remain preserved.",
            title="Offset before the internal deadline",
            border_style="green",
        )
    )


def render_notice_diagnostic(
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
                f"{diagnostic.walkthroughs_used}\nTargeted remediation: "
                + (
                    ", ".join(diagnostic.recommended_remediation_categories)
                    if diagnostic.recommended_remediation_categories
                    else "none recommended"
                )
            ),
            title="Notice Window diagnostic",
            border_style="magenta",
        )
    )


def render_notice_debrief(
    console: Console,
    state: GameState,
    content: ContentBundle,
) -> None:
    chapter = state.notice_window
    additions = [
        content.curriculum_objective(objective_id).game_concept_label
        for objective_id in content.notice_window.season.coverage_additions
    ]
    console.print(
        Panel(
            (
                "The Notice Window is complete. Its assessment is frozen separately "
                "from Core and Supply Gap results. The local March position is zero; "
                "no global Hedge Book, cash, audit finding, or diligence input changed.\n\n"
                f"Evidence quality: {chapter.evidence_score}; documentation quality: "
                f"{chapter.documentation_score}; communication quality: "
                f"{chapter.communication_score}.\n\nMarket-structure evidence:\n- "
                + "\n- ".join(additions)
                + "\n\nThis focused supplement does not simulate delivery operations, "
                "exchange matching, Rule 589 thresholds, spreads, options, or the "
                "remaining regulatory curriculum."
            ),
            title="The Notice Window Debrief",
            border_style="green",
        )
    )
