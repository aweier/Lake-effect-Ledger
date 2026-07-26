from lake_effect_ledger.education.report import build_learning_report
from lake_effect_ledger.game import create_new_game
from lake_effect_ledger.narrative.engine import NarrativeEngine
from lake_effect_ledger.state import Background


def _completed_state(content, choice_id: str):
    state = create_new_game(
        name="Riley",
        background=Background.DATA_ANALYTICS,
        seed=9,
        content=content,
    )
    engine = NarrativeEngine(content)
    engine.choose(state, "december_difference", choice_id)
    engine.process_end_of_day(state)
    return state


def test_learning_report_distinguishes_no_entry_from_balanced_entry(content) -> None:
    no_entry = build_learning_report(
        _completed_state(content, "request_meter_support"),
        content,
    )
    balanced_entry = build_learning_report(
        _completed_state(content, "book_line_loss"),
        content,
    )

    assert no_entry.journal_balanced is None
    assert balanced_entry.journal_balanced is True
