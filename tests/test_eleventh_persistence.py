import json
import sqlite3

from lake_effect_ledger.persistence.saves import SaveRepository


def test_v4_save_migrates_to_v5_without_losing_prior_state(
    completed_state_factory,
    tmp_path,
) -> None:
    state = completed_state_factory(seed=44)
    payload = state.model_dump(mode="json")
    payload["save_schema_version"] = 4
    payload.pop("eleventh_contract")
    database = tmp_path / "v4.db"
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
                4,
                state.player.name,
                state.current_date.isoformat(),
                1,
                json.dumps(payload),
            ),
        )

    restored = repository.load()

    assert restored.save_schema_version == 5
    assert restored.eleventh_contract is None
    assert restored.player == state.player
    assert restored.resources == state.resources
    assert restored.ledger == state.ledger
    assert restored.decisions == state.decisions


def test_in_progress_eleventh_contract_is_not_listed_as_complete(
    content,
    completed_state_factory,
    tmp_path,
) -> None:
    from lake_effect_ledger.commodity.engine import CommodityEngine
    from lake_effect_ledger.narrative.engine import NarrativeEngine
    from lake_effect_ledger.trading.engine import EleventhContractEngine

    state = completed_state_factory(seed=1728)
    commodity = CommodityEngine(content)
    commodity.open_hedge(state, "hedge_100")
    NarrativeEngine(content).choose(
        state,
        "hedge_documentation",
        "write_accurate_hedge_memo",
    )
    commodity.settle_remaining(state)
    EleventhContractEngine(content).initialize(state)
    repository = SaveRepository(tmp_path / "active.db")

    repository.save(state)

    assert not repository.list_saves()[0].completed
