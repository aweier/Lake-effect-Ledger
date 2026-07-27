import json
import sqlite3

from lake_effect_ledger.commodity.engine import CommodityEngine
from lake_effect_ledger.persistence.saves import SaveRepository


def test_milestone_2_save_migrates_through_schema_3_to_schema_6(
    content,
    completed_state_factory,
    tmp_path,
) -> None:
    state = completed_state_factory(seed=1729)
    commodity = CommodityEngine(content)
    commodity.open_hedge(state, "hedge_100")
    commodity.settle_remaining(state)
    payload = state.model_dump(mode="json")
    payload["save_schema_version"] = 2
    payload.pop("treasury")
    payload.pop("evidence_log")

    database = tmp_path / "milestone_2.db"
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
                2,
                state.player.name,
                state.current_date.isoformat(),
                1,
                json.dumps(payload),
            ),
        )

    restored = repository.load()

    assert restored.save_schema_version == 9
    assert restored.no_surprises is None
    assert restored.eleventh_contract is None
    assert restored.game_mode.value == "standard"
    assert restored.prologue.transitioned_to_episode_1
    assert restored.hedge_book == state.hedge_book
    assert restored.treasury is None
    assert restored.evidence_log == []


def test_mid_crisis_notification_round_trips_exactly(
    treasury_state_factory,
    tmp_path,
) -> None:
    state, _, treasury = treasury_state_factory()
    treasury.record_notification(state, "notify_immediately")
    repository = SaveRepository(tmp_path / "mid_crisis.db")

    repository.save(state)
    restored = repository.load()

    assert restored == state
    assert restored.treasury.notification_choice.value == "notify_immediately"
    assert restored.treasury.funding_decision is None
    assert restored.hedge_book.pending_margin_call_id == "margin_call_day_2"
    assert restored.evidence_log[0].record_id == "communication_notify_immediately"


def test_incomplete_treasury_save_is_not_marked_complete(
    treasury_state_factory,
    tmp_path,
) -> None:
    state, _, treasury = treasury_state_factory()
    treasury.record_notification(state, "notify_immediately")
    repository = SaveRepository(tmp_path / "completion.db")

    repository.save(state)

    assert not repository.list_saves()[0].completed


def test_reduced_position_with_revised_zero_call_round_trips(
    treasury_state_factory,
    tmp_path,
) -> None:
    state, _, treasury = treasury_state_factory()
    treasury.record_notification(state, "notify_immediately")
    treasury.resolve_funding(state, "reduce_position")
    repository = SaveRepository(tmp_path / "reduction.db")

    repository.save(state)
    restored = repository.load()

    assert restored == state
    assert restored.hedge_book.margin.calls[-1].required_amount == 0
    assert restored.hedge_book.position.contracts == 5


def test_completed_treasury_save_is_marked_complete(
    treasury_state_factory,
    tmp_path,
) -> None:
    state, commodity, treasury = treasury_state_factory()
    treasury.record_notification(state, "notify_immediately")
    treasury.resolve_funding(state, "revolver")
    commodity.settle_remaining(state)
    treasury.finalize(state)
    repository = SaveRepository(tmp_path / "complete.db")

    repository.save(state)

    assert repository.list_saves()[0].completed
    assert repository.load() == state
