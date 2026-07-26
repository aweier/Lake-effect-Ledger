"""Validated double-entry accounting primitives."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AccountType(StrEnum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class AccountDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    number: str = Field(pattern=r"^\d{4}$")
    name: str = Field(min_length=1)
    account_type: AccountType


class JournalLine(BaseModel):
    model_config = ConfigDict(frozen=True)

    account: str = Field(pattern=r"^\d{4}$")
    debit: Decimal = Field(default=Decimal("0"), ge=0)
    credit: Decimal = Field(default=Decimal("0"), ge=0)

    @model_validator(mode="after")
    def require_exactly_one_side(self) -> JournalLine:
        has_debit = self.debit > 0
        has_credit = self.credit > 0
        if has_debit == has_credit:
            raise ValueError("journal line must contain either a debit or a credit")
        return self


class JournalEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    transaction_id: str = Field(min_length=1, pattern=r"^[a-z0-9_]+$")
    entry_date: date
    description: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    lines: list[JournalLine] = Field(min_length=2)

    @property
    def total_debits(self) -> Decimal:
        return sum((line.debit for line in self.lines), Decimal("0"))

    @property
    def total_credits(self) -> Decimal:
        return sum((line.credit for line in self.lines), Decimal("0"))

    @model_validator(mode="after")
    def require_balance(self) -> JournalEntry:
        if self.total_debits != self.total_credits:
            raise ValueError(
                f"unbalanced journal entry: debits {self.total_debits} "
                f"do not equal credits {self.total_credits}"
            )
        return self


class Ledger(BaseModel):
    entries: list[JournalEntry] = Field(default_factory=list)

    def post(self, entry: JournalEntry, valid_accounts: set[str]) -> None:
        unknown = {line.account for line in entry.lines} - valid_accounts
        if unknown:
            raise ValueError(f"unknown account(s): {', '.join(sorted(unknown))}")
        if any(existing.transaction_id == entry.transaction_id for existing in self.entries):
            raise ValueError(f"duplicate transaction ID: {entry.transaction_id}")
        # JournalEntry validation is the engine-level balance gate.
        self.entries.append(entry)

    def account_activity(self) -> dict[str, tuple[Decimal, Decimal]]:
        activity: dict[str, tuple[Decimal, Decimal]] = {}
        for entry in self.entries:
            for line in entry.lines:
                debit, credit = activity.get(line.account, (Decimal("0"), Decimal("0")))
                activity[line.account] = (debit + line.debit, credit + line.credit)
        return activity
