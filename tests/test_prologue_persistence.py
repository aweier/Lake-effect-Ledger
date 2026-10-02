import json
import sqlite3

from lake_effect_ledger.game import create_new_game
from lake_effect_ledger.learning.engine import LearningEngine
from lake_effect_ledger.learning.models import GameMode
from lake_effect_ledger.persistence.saves import SaveRepository
from lake_effect_ledger.state import Background


def test_guided_mid_check_round_trip_preserves_learning_state(content, tmp_path) -> None:
    state = create_new_game(
        name="Resume",
        background=Background.ACCOUNTING,
        seed=5,
        content=content,
        game_mode=GameMode.GUIDED,
    )
    engine = LearningEngine(content)
    engine.introduce_day(state, content.prologue.prologue.days[0])
    engine.hint(state, "d1_physical_direction")
    state.prologue.current_check_index = 1
    repository = SaveRepository(tmp_path / "guided.db")
    repository.save(state)
    restored = repository.load()
    assert restored == state
    assert restored.learning.checks["d1_physical_direction"].hints_used == 1


def test_v3_save_migrates_to_standard_with_prologue_skipped(content, tmp_path) -> None:
    state = create_new_game(
        name="Legacy",
        background=Background.FINANCE,
        seed=7,
        content=content,
    )
    payload = state.model_dump(mode="json")
    payload["save_schema_version"] = 3
    payload["player"].pop("role")
    for field in (
        "game_mode",
        "show_math",
        "prologue",
        "learning",
        "career_trajectory",
    ):
        payload.pop(field)
    database = tmp_path / "v3.db"
    repository = SaveRepository(database)
    repository.initialize()
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            INSERT INTO save_slots (
                slot, save_schema_version, player_name, game_date,
                completed, state_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "autosave",
                3,
                state.player.name,
                state.current_date.isoformat(),
                0,
                json.dumps(payload),
            ),
        )
    restored = repository.load()
    assert restored.save_schema_version == 11
    assert restored.no_surprises is None
    assert restored.eleventh_contract is None
    assert restored.game_mode == GameMode.STANDARD
    assert restored.prologue.completed
    assert restored.prologue.skipped
    assert restored.player.role == "Northstar Analyst"
