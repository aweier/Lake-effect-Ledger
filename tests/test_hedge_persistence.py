import json
import sqlite3

from lake_effect_ledger.commodity.engine import CommodityEngine
from lake_effect_ledger.narrative.engine import NarrativeEngine
from lake_effect_ledger.persistence.saves import SaveRepository


def test_save_load_mid_scenario_resumes_exact_path(
    content,
    completed_state_factory,
    tmp_path,
) -> None:
    state = completed_state_factory(seed=404)
    engine = CommodityEngine(content)
    engine.open_hedge(state, "hedge_100")
    NarrativeEngine(content).choose(
        state,
        "hedge_documentation",
        "write_accurate_hedge_memo",
    )
    engine.settle_remaining(state, maximum_days=2)
    repository = SaveRepository(tmp_path / "hedge.db")
    repository.save(state)

    restored = repository.load()

    assert restored == state
    assert restored.hedge_book.next_settlement_index == 2
    assert restored.hedge_book.price_path == state.hedge_book.price_path
    assert restored.corporate_cash == state.corporate_cash
    assert restored.hedge_book.margin == state.hedge_book.margin

    CommodityEngine(content).settle_remaining(state)
    CommodityEngine(content).settle_remaining(restored)

    assert restored == state
    assert restored.hedge_book.completed


def test_milestone_1_save_migrates_through_full_chain_to_schema_6(
    content,
    completed_state_factory,
    tmp_path,
) -> None:
    legacy_state = completed_state_factory(seed=123)
    payload = legacy_state.model_dump(mode="json")
    payload["save_schema_version"] = 1
    payload["resources"].pop("evidence_exposure")
    payload.pop("hedge_book")

    database = tmp_path / "legacy.db"
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
                1,
                legacy_state.player.name,
                legacy_state.current_date.isoformat(),
                1,
                json.dumps(payload),
            ),
        )

    migrated = repository.load()

    assert migrated.save_schema_version == 9
    assert migrated.no_surprises is None
    assert migrated.eleventh_contract is None
    assert migrated.game_mode.value == "standard"
    assert migrated.prologue.completed
    assert migrated.prologue.skipped
    assert migrated.treasury is None
    assert migrated.evidence_log == []
    assert migrated.resources.evidence_exposure == 10
    assert migrated.hedge_book is None
    assert migrated.decisions == legacy_state.decisions
    assert migrated.ledger == legacy_state.ledger
