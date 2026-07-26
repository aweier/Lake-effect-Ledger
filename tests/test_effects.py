import pytest

from lake_effect_ledger.game import create_new_game
from lake_effect_ledger.narrative.engine import NarrativeEngine
from lake_effect_ledger.state import Background


@pytest.mark.parametrize(
    "choice_id",
    [
        "book_line_loss",
        "record_temporary_imbalance",
        "request_meter_support",
        "escalate_to_controller",
    ],
)
def test_every_choice_applies_and_reaches_end_of_day(content, choice_id: str) -> None:
    state = create_new_game(
        name="Taylor",
        background=Background.ACCOUNTING,
        seed=100,
        content=content,
    )
    engine = NarrativeEngine(content)

    engine.choose(state, "december_difference", choice_id)
    assert state.scheduled_events
    assert any(record.phase == "immediate" for record in state.event_log)

    engine.process_end_of_day(state)
    assert state.completed
    assert not state.scheduled_events
    assert state.end_of_day_messages
    assert any(record.phase == "end_of_day" for record in state.event_log)
    assert all(entry.total_debits == entry.total_credits for entry in state.ledger.entries)


def test_line_loss_posts_balanced_entry_and_raises_audit_risk(content) -> None:
    state = create_new_game(
        name="Taylor",
        background=Background.ACCOUNTING,
        seed=100,
        content=content,
    )
    engine = NarrativeEngine(content)
    starting_risk = state.resources.audit_risk

    engine.choose(state, "december_difference", "book_line_loss")
    assert state.ledger.entries[-1].transaction_id == "txn_december_variance_line_loss"
    assert state.resources.audit_risk == starting_risk + 2

    engine.process_end_of_day(state)
    assert state.resources.audit_risk == starting_risk + 5
    assert state.flags["unsupported_classification_posted"] is True


def test_requesting_support_defers_the_journal_entry(content) -> None:
    state = create_new_game(
        name="Taylor",
        background=Background.DATA_ANALYTICS,
        seed=100,
        content=content,
    )
    engine = NarrativeEngine(content)

    engine.choose(state, "december_difference", "request_meter_support")
    engine.process_end_of_day(state)

    assert len(state.ledger.entries) == 1
    assert state.flags["raw_meter_support_received"] is True
