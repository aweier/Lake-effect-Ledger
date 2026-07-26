"""Rich presentation for First Rotation and the Learning Notebook."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lake_effect_ledger.learning.models import (
    CalculationKind,
    KnowledgeCheckDefinition,
    TutorialDayDefinition,
)
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.state import GameState

FORMULAS = (
    ("Regional price", "Henry Hub + regional basis"),
    ("Futures P&L", "signed price change × contract size × contracts"),
    ("Tick value", "minimum tick × contract size"),
    ("Hedge ratio", "futures quantity ÷ physical quantity"),
    ("Margin call", "initial requirement - balance, when balance < maintenance"),
)


def render_day(console: Console, day: TutorialDayDefinition) -> None:
    console.print(Panel(day.subtitle, title=day.title, border_style="cyan"))
    for panel in day.concept_panels:
        console.print(
            Panel(panel.text, title=f"{panel.speaker} · {panel.title}", border_style="blue")
        )


def render_check(console: Console, check: KnowledgeCheckDefinition) -> None:
    lines = [check.prompt]
    if check.options:
        lines.extend(f"  {item.id}: {item.text}" for item in check.options)
    lines.append("  unsure: I'm not sure—walk me through it.")
    console.print(Panel("\n".join(lines), title=f"Knowledge check · {check.id}"))


def render_check_math(console: Console, check: KnowledgeCheckDefinition) -> None:
    formulas = {
        CalculationKind.FUTURES_PNL: "Short P&L = (previous - current) × contract size × contracts",
        CalculationKind.TICK_VALUE: "Tick value = minimum tick × contract size",
        CalculationKind.REGIONAL_PRICE: "Regional price = Henry Hub + basis",
        CalculationKind.HEDGE_RATIO: (
            "Hedge ratio = (contracts × contract size) ÷ physical quantity"
        ),
        CalculationKind.MARGIN_CALL: (
            "If balance < maintenance: call = initial requirement - balance"
        ),
    }
    text = (
        formulas[check.calculation.kind]
        if check.calculation is not None
        else "Compare the position direction, timing, exposure, and stated purpose."
    )
    console.print(Panel(text, title="Math / reasoning frame", border_style="magenta"))


def render_notebook(console: Console, state: GameState, content: ContentBundle) -> None:
    progress = Table(title="Learning progress")
    progress.add_column("Objective")
    progress.add_column("Status")
    for objective_id, objective in sorted(state.learning.objectives.items()):
        progress.add_row(content.lesson(objective_id).title, objective.status.value)
    if not state.learning.objectives:
        progress.add_row("No objectives introduced", "unseen")
    console.print(progress)

    glossary = Table(title="Glossary")
    glossary.add_column("Term")
    glossary.add_column("Definition")
    glossary.add_column("Topic / source")
    for term_id in state.learning.notebook.unlocked_glossary_ids:
        term = content.glossary_term(term_id)
        sources = ", ".join(content.source(item).organization for item in term.source_ids)
        glossary.add_row(
            term.term,
            term.definition,
            f"{', '.join(term.series_3_topics)} · {sources}",
        )
    if not state.learning.notebook.unlocked_glossary_ids:
        glossary.add_row("No terms unlocked", "Complete a concept panel.", "—")
    console.print(glossary)

    formulas = Table(title="Formula reference")
    formulas.add_column("Use")
    formulas.add_column("Formula")
    for label, formula in FORMULAS:
        formulas.add_row(label, formula)
    console.print(formulas)

    examples = Table(title="Worked examples")
    examples.add_column("Check")
    examples.add_column("Worked solution")
    examples.add_column("Source")
    for check_id in state.learning.notebook.worked_example_ids:
        check = content.knowledge_check(check_id)
        examples.add_row(check_id, check.worked_solution, content.source(check.source_id).title)
    if not state.learning.notebook.worked_example_ids:
        examples.add_row("None yet", "Use a walkthrough to save an example.", "—")
    console.print(examples)
