"""Generate feedback from actual posted transactions and encountered objectives."""

from __future__ import annotations

from pydantic import BaseModel

from lake_effect_ledger.accounting.models import AccountDefinition, AccountType
from lake_effect_ledger.game import OPENING_BALANCE_ID
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.state import GameState


class LearningReport(BaseModel):
    accounts_changed: list[str]
    journal_balanced: bool | None
    financial_statement_effects: list[str]
    control_and_evidence_notes: list[str]
    objectives_encountered: list[str]


def _line_effect(account: AccountDefinition, debit: bool) -> str:
    if account.account_type == AccountType.ASSET:
        direction = "increased" if debit else "decreased"
        return f"Balance sheet: {account.name} (asset) {direction}."
    if account.account_type == AccountType.LIABILITY:
        direction = "decreased" if debit else "increased"
        return f"Balance sheet: {account.name} (liability) {direction}."
    if account.account_type == AccountType.EQUITY:
        direction = "decreased" if debit else "increased"
        return f"Balance sheet: {account.name} (equity) {direction}."
    if account.account_type == AccountType.REVENUE:
        direction = "decreased" if debit else "increased"
        return f"Income statement: {account.name} (revenue) {direction}."
    direction = "increased" if debit else "decreased"
    income_direction = "decreased" if debit else "increased"
    return (
        f"Income statement: {account.name} (expense) {direction}; "
        f"pre-tax income {income_direction}."
    )


def build_learning_report(state: GameState, content: ContentBundle) -> LearningReport:
    chart = {account.number: account for account in content.chart.accounts}
    episode_entries = [
        entry for entry in state.ledger.entries if entry.transaction_id != OPENING_BALANCE_ID
    ]
    accounts_changed: list[str] = []
    statement_effects: list[str] = []
    for entry in episode_entries:
        for line in entry.lines:
            account = chart[line.account]
            amount = line.debit if line.debit else line.credit
            side = "debit" if line.debit else "credit"
            accounts_changed.append(f"{account.number} {account.name}: {side} ${amount:,.2f}")
            statement_effects.append(_line_effect(account, debit=bool(line.debit)))

    if not episode_entries:
        accounts_changed.append(
            "No journal entry was posted; the opening trial balance was unchanged."
        )
        statement_effects.append(
            "No income-statement or balance-sheet amount changed pending additional support."
        )

    cash_changed = any(line.account == "1000" for entry in episode_entries for line in entry.lines)
    statement_effects.append(
        "Cash-flow summary: cash changed with the entry."
        if cash_changed
        else "Cash-flow summary: no cash account changed."
    )

    lessons = [content.lesson(item) for item in state.learning_objectives]
    control_notes = [
        lesson.explanation
        for lesson in lessons
        if lesson.category in {"controls", "accounting", "natural_gas"}
    ]
    objectives = [f"{lesson.title} ({lesson.category})" for lesson in lessons]
    return LearningReport(
        accounts_changed=accounts_changed,
        journal_balanced=(
            all(entry.total_debits == entry.total_credits for entry in episode_entries)
            if episode_entries
            else None
        ),
        financial_statement_effects=list(dict.fromkeys(statement_effects)),
        control_and_evidence_notes=control_notes,
        objectives_encountered=objectives,
    )
