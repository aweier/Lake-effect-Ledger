from lake_effect_ledger.game import create_new_game
from lake_effect_ledger.narrative.engine import NarrativeEngine
from lake_effect_ledger.persistence.saves import SaveRepository
from lake_effect_ledger.state import Background


def test_save_load_round_trip_preserves_state(content, tmp_path) -> None:
    state = create_new_game(
        name="Casey",
        background=Background.FINANCE,
        seed=73,
        content=content,
    )
    engine = NarrativeEngine(content)
    engine.choose(state, "december_difference", "record_temporary_imbalance")

    repository = SaveRepository(tmp_path / "save.db")
    repository.save(state, "test_slot")
    restored = repository.load("test_slot")

    assert restored == state
    assert repository.list_saves()[0].slot == "test_slot"
