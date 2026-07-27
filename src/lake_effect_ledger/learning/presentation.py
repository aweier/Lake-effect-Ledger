"""Rich presentation for First Rotation and the Learning Notebook."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lake_effect_ledger.learning.calculations import calculate_answer
from lake_effect_ledger.learning.core import CoreDebrief, CoreReviewDiagnostic
from lake_effect_ledger.learning.models import (
    CalculationKind,
    KnowledgeCheckDefinition,
    NotebookSection,
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


def render_check_math(
    console: Console,
    check: KnowledgeCheckDefinition,
    content: ContentBundle,
) -> None:
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
    if check.calculation is not None:
        answer = calculate_answer(check, content)
        text = (
            f"{formulas[check.calculation.kind]}\n"
            f"Shared-engine result: {answer} {check.numeric_rule.answer_unit}"
        )
    else:
        text = "Compare the position direction, timing, exposure, and stated purpose."
    console.print(Panel(text, title="Math / reasoning frame", border_style="magenta"))


def render_notebook(console: Console, state: GameState, content: ContentBundle) -> None:
    console.print(
        Panel(
            "Series 3 Core concepts and business context are separated below. "
            "Progress records first-attempt evidence, assistance, and review needs.",
            title="Learning progress",
            border_style="cyan",
        )
    )
    terms_by_section: dict[NotebookSection, list] = {
        section: [] for section in NotebookSection if section != NotebookSection.NOT_YET_COVERED
    }
    for term in content.glossary.terms:
        objective = content.curriculum_objective(term.learning_objective_ids[0])
        terms_by_section[objective.notebook_section].append(term)

    for section in NotebookSection:
        if section == NotebookSection.NOT_YET_COVERED:
            future = Table(title=section.value)
            future.add_column("Official topic")
            future.add_column("Outline section")
            future.add_column("Status")
            for topic in content.curriculum.future_topics:
                future.add_row(
                    topic.official_topic_label,
                    topic.official_outline_section,
                    "not yet covered",
                )
            console.print(future)
            continue
        table = Table(title=section.value)
        table.add_column("Concept")
        table.add_column("Definition / formula / example")
        table.add_column("Progress / chapter / source")
        terms = terms_by_section[section]
        for term in terms:
            curriculum = content.curriculum_objective(term.learning_objective_ids[0])
            progress = state.learning.objectives.get(curriculum.id)
            status = progress.status.value if progress is not None else "unseen"
            chapters = ", ".join(progress.chapter_ids) if progress else "not encountered"
            mapped_checks = [
                content.knowledge_check(check_id)
                for check_id in curriculum.check_ids
                if check_id in state.learning.checks and state.learning.checks[check_id].completed
            ]
            formulas = [
                FORMULAS_BY_KIND[item.calculation.kind]
                for item in mapped_checks
                if item.calculation is not None
            ]
            examples = [
                item.worked_solution
                for item in mapped_checks
                if item.id in state.learning.notebook.worked_example_ids
            ]
            detail = term.definition
            if formulas:
                detail += "\nFormula: " + "; ".join(dict.fromkeys(formulas))
            if examples:
                detail += "\nExample: " + examples[-1]
            sources = ", ".join(content.source(item).title for item in term.source_ids)
            needs_review = progress is not None and progress.status.value in {
                "review_recommended",
                "practiced_with_help",
                "demonstrated_after_retry",
            }
            table.add_row(
                term.term,
                detail,
                (
                    f"{status}; chapter: {chapters}; "
                    f"core={'yes' if curriculum.counts_toward_core else 'no'}; "
                    f"review={'yes' if needs_review else 'no'}\n"
                    f"Source: {sources}"
                ),
            )
        if not terms:
            table.add_row("No concepts encountered", "—", "—")
        console.print(table)

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


FORMULAS_BY_KIND = {
    CalculationKind.FUTURES_PNL: "signed price change × contract size × contracts",
    CalculationKind.TICK_VALUE: "minimum tick × contract size",
    CalculationKind.REGIONAL_PRICE: "Henry Hub + regional basis",
    CalculationKind.HEDGE_RATIO: "futures quantity ÷ physical quantity",
    CalculationKind.MARGIN_CALL: ("initial requirement - balance, when balance < maintenance"),
}


def render_core_chapter_opening(
    console: Console,
    content: ContentBundle,
    chapter_id: str,
) -> None:
    chapter = content.core_chapter(chapter_id)
    introduced = [
        content.curriculum_objective(item).game_concept_label
        for item in chapter.introduced_objective_ids
    ]
    practiced = [
        content.curriculum_objective(item).game_concept_label
        for item in chapter.practiced_objective_ids
    ]
    context = [
        content.curriculum_objective(item).game_concept_label
        for item in chapter.business_context_objective_ids
    ]
    text = (
        "SERIES 3 FOCUS\n"
        f"Concepts introduced: {', '.join(introduced) or 'None'}\n"
        f"Concepts practiced: {', '.join(practiced) or 'None'}\n"
        f"Business context: {', '.join(context) or 'None'}\n"
        f"Estimated playtime: {chapter.estimated_minutes} minutes"
    )
    console.print(Panel(text, title=chapter.title, border_style="cyan"))
    for note in chapter.teaching_notes:
        console.print(Panel(note, title="Before you apply it", border_style="blue"))


def render_core_chapter_debrief(
    console: Console,
    state: GameState,
    content: ContentBundle,
    chapter_id: str,
    calculation_lines: list[str],
) -> None:
    chapter = content.core_chapter(chapter_id)
    relevant_checks = {
        check_id
        for objective_id in [
            *chapter.introduced_objective_ids,
            *chapter.practiced_objective_ids,
        ]
        for check_id in content.curriculum_objective(objective_id).check_ids
    }
    progress = [
        state.learning.checks[item]
        for item in relevant_checks
        if item in state.learning.checks and state.learning.checks[item].completed
    ]
    first_correct = sum(item.first_attempt_correct is True for item in progress)
    first_unknown = sum(item.first_attempt_correct is None for item in progress)
    hints = sum(item.hints_used for item in progress)
    reviews = [
        item.check_id
        for item in progress
        if item.review_recommended
        or item.first_attempt_correct is not True
        or item.hints_used
        or item.walkthrough_used
    ]
    practiced = [
        content.curriculum_objective(item).game_concept_label
        for item in chapter.practiced_objective_ids
    ]
    context = [
        content.curriculum_objective(item).game_concept_label
        for item in chapter.business_context_objective_ids
    ]
    body = (
        f"What happened in the story: {chapter.title} reached its saved chapter boundary.\n"
        f"Series 3 concepts practiced: {', '.join(practiced) or 'None'}\n"
        f"Business context encountered: {', '.join(context) or 'None'}\n"
        "Actual calculations performed:\n"
        + ("\n".join(f"- {item}" for item in calculation_lines) or "- None")
        + f"\nFirst-attempt results: {first_correct}/{len(progress)} correct"
        + (f"; {first_unknown} legacy unknown" if first_unknown else "")
        + f"\nHints used: {hints}\n"
        f"Review recommendations: {', '.join(reviews) or 'None'}\n"
        f"Notebook updates: {len(state.learning.notebook.unlocked_glossary_ids)} terms, "
        f"{len(state.learning.notebook.worked_example_ids)} worked examples."
    )
    console.print(Panel(body, title=f"{chapter.title} · Chapter debrief", border_style="green"))


def render_core_review_diagnostic(
    console: Console,
    diagnostic: CoreReviewDiagnostic,
) -> None:
    console.print(
        Panel(
            f"Style: {diagnostic.style.value}\n"
            f"First attempts correct: {diagnostic.first_attempt_correct}/"
            f"{diagnostic.total_questions}\n"
            f"First attempts unknown: {diagnostic.first_attempt_unknown}\n"
            f"Final correct: {diagnostic.final_correct}/{diagnostic.total_questions}\n"
            f"Hints used: {diagnostic.hints_used}\n"
            f"Walkthroughs used: {diagnostic.walkthroughs_used}\n"
            f"Review recommended: "
            f"{', '.join(diagnostic.review_recommended_ids) or 'None'}\n\n"
            "This is a diagnostic on implemented Core material, not a full "
            "Series 3 mock exam.",
            title="Cumulative Core Review",
            border_style="magenta",
        )
    )


def render_core_debrief(console: Console, debrief: CoreDebrief) -> None:
    def joined(values: list[str]) -> str:
        return "\n".join(f"- {item}" for item in values) or "- None"

    console.print(
        Panel(
            "Objectives introduced:\n"
            + joined(debrief.objectives_introduced)
            + "\n\nIndependently demonstrated:\n"
            + joined(debrief.objectives_independently_demonstrated)
            + "\n\nCompleted with help:\n"
            + joined(debrief.objectives_completed_with_help)
            + "\n\nRecommended for review:\n"
            + joined(debrief.objectives_recommended_for_review)
            + "\n\nCore topics not encountered:\n"
            + joined(debrief.core_topics_not_encountered),
            title="SERIES 3 CORE DEBRIEF · Actual progress",
            border_style="bold cyan",
        )
    )
    console.print(
        Panel(
            f"Calculation accuracy: {debrief.calculation_accuracy}\n"
            f"Concept accuracy: {debrief.concept_accuracy}\n"
            f"Strengths:\n{joined(debrief.strengths)}\n"
            f"Suggested next study area: {debrief.suggested_next_study_area}",
            title="Diagnostic summary",
        )
    )
    console.print(
        Panel(
            joined(debrief.future_curriculum_topics),
            title="Official Series 3 topics not yet implemented",
            border_style="yellow",
        )
    )
    console.print(
        Panel(
            joined(debrief.source_titles) + f"\n\n{debrief.disclaimer}",
            title="Sources and scope",
        )
    )
