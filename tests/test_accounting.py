from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from lake_effect_ledger.accounting.models import JournalEntry, JournalLine


def test_balanced_journal_entry_is_accepted() -> None:
    entry = JournalEntry(
        transaction_id="txn_test_balanced",
        entry_date=date(2028, 1, 16),
        description="Test entry",
        source_id="test",
        lines=[
            JournalLine(account="1200", debit=Decimal("100")),
            JournalLine(account="2100", credit=Decimal("100")),
        ],
    )
    assert entry.total_debits == entry.total_credits == Decimal("100")


def test_unbalanced_journal_entry_is_rejected() -> None:
    with pytest.raises(ValidationError, match="unbalanced journal entry"):
        JournalEntry(
            transaction_id="txn_test_unbalanced",
            entry_date=date(2028, 1, 16),
            description="Bad test entry",
            source_id="test",
            lines=[
                JournalLine(account="1200", debit=Decimal("100")),
                JournalLine(account="2100", credit=Decimal("99")),
            ],
        )
