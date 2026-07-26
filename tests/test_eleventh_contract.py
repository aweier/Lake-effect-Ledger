import json
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from lake_effect_ledger.cli import CHAPTER_PATH_CHOICES
from lake_effect_ledger.commodity.engine import CommodityEngine
from lake_effect_ledger.narrative.engine import NarrativeEngine
from lake_effect_ledger.persistence.saves import SaveRepository
from lake_effect_ledger.trading.engine import EleventhContractEngine, OrderFillEngine
from lake_effect_ledger.trading.models import (
    EleventhOutcome,
    OrderSide,
    OrderStatus,
    OrderType,
    PhysicalVolumeOutcome,
    ReconciliationStatus,
    TradeOrder,
)
from lake_effect_ledger.trading.report import build_analyst_case_file
from lake_effect_ledger.treasury.engine import TreasuryEngine

DAY_1_SCENES = (
    "ec_volume_language",
    "ec_hedge_recommendation",
    "ec_risk_emphasis",
    "ec_ask_marisol",
)
DAY_2_SCENES = ("ec_order_type", "ec_authorization_review")
DAY_3_SCENES = (
    "ec_record_handling",
    "ec_verification",
    "ec_exception_disposition",
    "ec_position_action",
)


def _prerequisite_state(content, completed_state_factory, seed: int):
    state = completed_state_factory(seed=seed)
    commodity = CommodityEngine(
        content,
        market_path_id="fictional_margin_squeeze_2028",
    )
    commodity.open_hedge(state, "hedge_100")
    NarrativeEngine(content).choose(
        state,
        "hedge_documentation",
        "write_accurate_hedge_memo",
    )
    commodity.settle_next_day(state, defer_margin_call=True)
    commodity.settle_next_day(state, defer_margin_call=True)
    treasury = TreasuryEngine(content, commodity)
    treasury.initialize_crisis(state)
    treasury.record_notification(state, "notify_immediately")
    treasury.resolve_funding(state, "operating_cash")
    commodity.settle_remaining(state)
    treasury.finalize(state)
    assert state.hedge_book.completed
    assert state.treasury.completed
    return state


def _choose_path_scenes(state, content, path: str, scene_ids) -> None:
    narrative = NarrativeEngine(content)
    for scene_id in scene_ids:
        choice_id = CHAPTER_PATH_CHOICES[path][scene_id]
        assert choice_id in {item.id for item in narrative.available_choices(state, scene_id)}
        narrative.choose(state, scene_id, choice_id)


def _run_path(content, completed_state_factory, path: str, seed: int):
    state = _prerequisite_state(content, completed_state_factory, seed)
    engine = EleventhContractEngine(content)
    engine.initialize(state)
    _choose_path_scenes(state, content, path, DAY_1_SCENES)
    engine.assemble_market_brief(state)
    _choose_path_scenes(state, content, path, DAY_2_SCENES)
    engine.recommend_and_execute_order(state)
    _choose_path_scenes(state, content, path, DAY_3_SCENES)
    engine.finalize_exception(state)
    _choose_path_scenes(
        state,
        content,
        path,
        ("ec_fish_fry", "eleventh_episode_transition"),
    )
    engine.complete_chapter(state)
    return state, engine


def _order(
    *,
    order_type: OrderType,
    order_price: Decimal | None = None,
    side: OrderSide = OrderSide.SELL,
) -> TradeOrder:
    return TradeOrder(
        order_id=f"test_{order_type.value}_{side.value}",
        account_id="test_account",
        book_id="test_book",
        contract_id="cme_henry_hub_ng",
        side=side,
        quantity=10,
        order_type=order_type,
        order_price=order_price,
        submitted_at=datetime(2028, 1, 25, 15, 4, tzinfo=UTC),
        authorized_quantity=10,
        authorized_user_id="evelyn_marsh",
        transmitting_user_id="cal_rourke",
        status=OrderStatus.SUBMITTED,
        related_physical_exposure_id="test_physical",
        related_authorization_id="test_authorization",
    )


@pytest.mark.parametrize(
    ("order_type", "order_price", "fill_price", "trigger_price"),
    [
        (OrderType.MARKET, None, Decimal("5.195"), None),
        (OrderType.LIMIT, Decimal("5.205"), Decimal("5.205"), None),
        (
            OrderType.STOP,
            Decimal("5.185"),
            Decimal("5.175"),
            Decimal("5.180"),
        ),
    ],
)
def test_deterministic_intraday_fill_rules(
    content,
    order_type: OrderType,
    order_price: Decimal | None,
    fill_price: Decimal,
    trigger_price: Decimal | None,
) -> None:
    path = content.eleventh_scenario.intraday_path
    filled = OrderFillEngine.execute(
        _order(order_type=order_type, order_price=order_price),
        path,
    )

    assert filled.status == OrderStatus.FILLED
    assert filled.fill_quantity == 10
    assert filled.fill_price == fill_price
    assert filled.trigger_price == trigger_price
    assert isinstance(filled.fill_price, Decimal)
    if order_type == OrderType.STOP:
        assert filled.trigger_timestamp < filled.fill_timestamp


def test_unreached_limit_remains_submitted(content) -> None:
    unfilled = OrderFillEngine.execute(
        _order(order_type=OrderType.LIMIT, order_price=Decimal("9.000")),
        content.eleventh_scenario.intraday_path,
    )

    assert unfilled.status == OrderStatus.SUBMITTED
    assert unfilled.fill_quantity == 0
    assert unfilled.fill_price is None


def test_order_validation_rejects_naive_time_and_impossible_fill() -> None:
    payload = _order(order_type=OrderType.MARKET).model_dump()
    payload["submitted_at"] = datetime(2028, 1, 25, 9, 4)
    with pytest.raises(ValidationError, match="UTC offset"):
        TradeOrder.model_validate(payload)

    payload = _order(order_type=OrderType.MARKET).model_dump()
    payload.update(
        {
            "status": OrderStatus.FILLED,
            "fill_quantity": 11,
            "fill_price": Decimal("5.20"),
            "fill_timestamp": datetime(2028, 1, 25, 15, 5, tzinfo=UTC),
        }
    )
    with pytest.raises(ValidationError, match="cannot exceed"):
        TradeOrder.model_validate(payload)


def test_order_model_represents_partial_cancelled_and_rejected_states() -> None:
    base = _order(order_type=OrderType.LIMIT, order_price=Decimal("5.205"))
    partial = TradeOrder.model_validate(
        {
            **base.model_dump(),
            "status": OrderStatus.PARTIALLY_FILLED,
            "fill_quantity": 4,
            "fill_price": Decimal("5.205"),
            "fill_timestamp": datetime(2028, 1, 25, 15, 10, tzinfo=UTC),
        }
    )
    cancelled = TradeOrder.model_validate(
        {
            **base.model_dump(),
            "status": OrderStatus.CANCELLED,
            "cancellation_reason": "day order withdrawn",
        }
    )
    rejected = TradeOrder.model_validate(
        {
            **base.model_dump(),
            "status": OrderStatus.REJECTED,
            "rejection_reason": "quantity control",
        }
    )

    assert partial.fill_quantity == 4
    assert partial.status == OrderStatus.PARTIALLY_FILLED
    assert cancelled.cancellation_reason
    assert rejected.rejection_reason


def test_live_book_distinguishes_instruction_execution_and_confirmation(
    content,
    completed_state_factory,
) -> None:
    state = _prerequisite_state(content, completed_state_factory, 1728)
    engine = EleventhContractEngine(content)
    chapter = engine.initialize(state)
    _choose_path_scenes(state, content, "formal_correction", DAY_1_SCENES)
    brief = engine.assemble_market_brief(state)
    _choose_path_scenes(state, content, "formal_correction", DAY_2_SCENES)
    order = engine.recommend_and_execute_order(state)

    assert brief.confirmed_volume_mmbtu == Decimal("100000")
    assert brief.possible_volume_mmbtu == Decimal("10000")
    assert chapter.authorization.maximum_quantity == 10
    assert order.quantity == order.fill_quantity == 10
    assert chapter.recommendation.recommended_by_id == "player"
    assert order.transmitting_user_id == "cal_rourke"
    assert chapter.execution.quantity == chapter.confirmation.quantity == 11
    assert engine.authorization_exception(state)
    assert engine.confirmation_matches_execution(state)
    assert chapter.position.open_contracts == 11
    assert chapter.position.initial_hedge_ratio == Decimal("1.1000")
    assert chapter.position.margin.initial_requirement == Decimal("165000.00")
    assert chapter.blotter.status == ReconciliationStatus.QUANTITY_EXCEPTION
    assert chapter.reconciliation.authorization_id == chapter.authorization.authorization_id
    assert chapter.reconciliation.order_id == order.order_id
    assert chapter.reconciliation.execution_id == chapter.execution.execution_id
    assert chapter.reconciliation.confirmation_id == chapter.confirmation.confirmation_id
    assert chapter.reconciliation.authorization_exception
    assert chapter.reconciliation.confirmation_matches_execution
    assert chapter.reconciliation.current_status == chapter.blotter.status


@pytest.mark.parametrize(
    ("path", "seed", "expected"),
    [
        ("formal_correction", 1728, EleventhOutcome.CLEAN_CORRECTION),
        ("marisol_supported", 1728, EleventhOutcome.SUPPORTED_BUT_LATE),
        ("accept_cal", 1728, EleventhOutcome.CALS_ANALYST),
        ("quiet_file", 1728, EleventhOutcome.QUIET_FILE),
        ("lucky_unapproved", 1729, EleventhOutcome.LUCKY_NOT_AUTHORIZED),
        ("leave_open_fail", 1729, EleventhOutcome.ELEVEN_AGAINST_TEN),
    ],
)
def test_six_state_derived_outcomes_are_reachable(
    content,
    completed_state_factory,
    path: str,
    seed: int,
    expected: EleventhOutcome,
) -> None:
    state, engine = _run_path(content, completed_state_factory, path, seed)

    assert state.eleventh_contract.outcome == expected
    assert len(state.eleventh_contract.decisions) >= 11
    engine.assert_reconciles(state)
    report = build_analyst_case_file(state, content)
    assert report.outcome == expected
    assert report.authorized_contracts == 10
    assert report.executed_contracts == 11
    assert report.original_blotter_status == ReconciliationStatus.QUANTITY_EXCEPTION
    assert report.accounting_entries_balanced


def test_offset_is_a_real_prospective_trade_and_preserves_history(
    content,
    completed_state_factory,
    tmp_path,
) -> None:
    state = _prerequisite_state(content, completed_state_factory, 1728)
    engine = EleventhContractEngine(content)
    chapter = engine.initialize(state)
    _choose_path_scenes(state, content, "formal_correction", DAY_1_SCENES)
    engine.assemble_market_brief(state)
    _choose_path_scenes(state, content, "formal_correction", DAY_2_SCENES)
    engine.recommend_and_execute_order(state)
    pnl_before_offset = chapter.position.cumulative_pnl
    price_before_offset = chapter.position.current_price
    _choose_path_scenes(state, content, "formal_correction", DAY_3_SCENES)

    offset = engine.offset_extra_contract(state)

    assert chapter.execution.quantity == 11
    assert chapter.confirmation.quantity == 11
    assert offset.side == OrderSide.BUY
    assert offset.quantity == 1
    assert offset.original_execution_id == chapter.execution.execution_id
    assert offset.cumulative_pnl_preserved == pnl_before_offset
    assert chapter.position.open_contracts == 10
    assert chapter.position.current_price == price_before_offset
    assert chapter.position.margin.initial_requirement == Decimal("150000.00")
    assert offset.margin_released == Decimal("17850.00")
    assert chapter.blotter.original_status == ReconciliationStatus.QUANTITY_EXCEPTION
    assert chapter.blotter.status == ReconciliationStatus.CORRECTED
    assert "txn_eleventh_offset_variation" in offset.journal_transaction_ids
    assert chapter.approvals[0].approval_id == offset.authorization_id
    assert chapter.approvals[0].original_execution_id == chapter.execution.execution_id
    assert chapter.approvals[0].reconciliation_id == chapter.reconciliation.reconciliation_id
    assert not chapter.physical_forecast.revealed
    engine.assert_reconciles(state)

    repository = SaveRepository(tmp_path / "after_offset.db")
    repository.save(state)
    restored = repository.load()

    assert restored == state
    assert restored.eleventh_contract.position.offset_trade == offset
    assert not restored.eleventh_contract.physical_forecast.revealed
    engine.finalize_exception(restored)
    assert restored.eleventh_contract.physical_forecast.revealed
    assert restored.eleventh_contract.execution.quantity == 11
    assert restored.eleventh_contract.position.open_contracts == 10
    engine.assert_reconciles(restored)


def test_case_file_uses_story_decisions_and_typed_control_records(
    content,
    completed_state_factory,
) -> None:
    state, _ = _run_path(content, completed_state_factory, "formal_correction", 1728)
    chapter = state.eleventh_contract
    report = build_analyst_case_file(state, content)
    decision_objectives = {
        objective_id
        for scene in content.eleventh_narrative.scenes
        for choice in scene.choices
        if choice.id in chapter.decisions
        for objective_id in choice.learning_objectives
    }

    assert not chapter.learning_check_ids
    assert set(report.series_3_objectives) == {
        content.lesson(item).title for item in decision_objectives
    }
    assert report.reconciliation_record_id == chapter.reconciliation.reconciliation_id
    assert chapter.notifications[0].communication_record_id == "comm_ec_formal_exception"
    assert chapter.notifications[0].reconciliation_id == chapter.reconciliation.reconciliation_id
    assert report.notifications == ["comm_ec_formal_exception"]
    assert chapter.approvals[0].approval_id == "approval_offset_eleventh_contract"
    assert chapter.approvals[0].reconciliation_id == chapter.reconciliation.reconciliation_id
    assert report.approvals == [
        "auth_live_week_ten_short",
        "approval_offset_eleventh_contract",
    ]


def test_early_native_v5_after_confirmation_rebuilds_typed_reconciliation(
    content,
    completed_state_factory,
    tmp_path,
) -> None:
    state = _prerequisite_state(content, completed_state_factory, 1728)
    engine = EleventhContractEngine(content)
    engine.initialize(state)
    _choose_path_scenes(state, content, "formal_correction", DAY_1_SCENES)
    engine.assemble_market_brief(state)
    _choose_path_scenes(state, content, "formal_correction", DAY_2_SCENES)
    engine.recommend_and_execute_order(state)
    database = tmp_path / "early_v5.db"
    repository = SaveRepository(database)
    repository.save(state)
    with sqlite3.connect(database) as connection:
        encoded = connection.execute(
            "SELECT state_json FROM save_slots WHERE slot = 'autosave'"
        ).fetchone()[0]
        payload = json.loads(encoded)
        chapter = payload["eleventh_contract"]
        chapter.pop("reconciliation")
        chapter.pop("notifications")
        chapter.pop("approvals")
        chapter["blotter"].pop("reconciliation_id")
        connection.execute(
            "UPDATE save_slots SET state_json = ? WHERE slot = 'autosave'",
            (json.dumps(payload),),
        )

    restored = repository.load()

    assert restored.save_schema_version == 5
    assert restored.eleventh_contract.reconciliation is None
    _choose_path_scenes(
        restored,
        content,
        "formal_correction",
        DAY_3_SCENES[:3],
    )
    chapter = restored.eleventh_contract
    assert chapter.reconciliation is not None
    assert chapter.blotter.reconciliation_id == chapter.reconciliation.reconciliation_id
    assert chapter.notifications[0].reconciliation_id == chapter.reconciliation.reconciliation_id


def test_prior_conduct_and_physical_result_change_conditional_dialogue(
    content,
    completed_state_factory,
) -> None:
    prior_state = _prerequisite_state(content, completed_state_factory, 1728)
    EleventhContractEngine(content).initialize(prior_state)
    prior_text = NarrativeEngine(content).resolved_scene_text(prior_state, "ec_order_type")

    arrives, _ = _run_path(content, completed_state_factory, "formal_correction", 1728)
    fails, _ = _run_path(content, completed_state_factory, "leave_open_fail", 1729)
    arrives_text = NarrativeEngine(content).resolved_scene_text(arrives, "ec_fish_fry")
    fails_text = NarrativeEngine(content).resolved_scene_text(fails, "ec_fish_fry")

    assert "documented the last one before it made money" in prior_text
    assert "The gas arrived" in arrives_text
    assert "extra gas never cleared" not in arrives_text
    assert "extra gas never cleared" in fails_text
    assert "The gas arrived" not in fails_text


def test_later_physical_support_never_rewrites_prior_authorization(
    content,
    completed_state_factory,
) -> None:
    state, _ = _run_path(content, completed_state_factory, "marisol_supported", 1728)
    chapter = state.eleventh_contract

    assert chapter.physical_forecast.outcome == PhysicalVolumeOutcome.ARRIVES
    assert chapter.physical_forecast.eventual_supported_volume_mmbtu == Decimal("110000")
    assert chapter.authorization.maximum_quantity == 10
    assert chapter.execution.quantity == 11
    assert chapter.original_blotter_status == ReconciliationStatus.QUANTITY_EXCEPTION
    assert chapter.authorization.approved_at < chapter.physical_forecast.support_obtained_at
    assert chapter.order.related_authorization_id == chapter.authorization.authorization_id


def test_unresolved_certification_is_preserved_as_a_linked_record(
    content,
    completed_state_factory,
) -> None:
    state, _ = _run_path(content, completed_state_factory, "certify_unresolved", 1729)
    chapter = state.eleventh_contract
    report = build_analyst_case_file(state, content)

    assert chapter.blotter.status == ReconciliationStatus.CERTIFIED_WITH_EXCEPTION
    assert chapter.blotter.certification_record_id == "comm_ec_unresolved_certification"
    assert report.reconciliation_certified
    assert report.certification_record_id == chapter.blotter.certification_record_id
    assert chapter.physical_forecast.support_obtained_at is None
    assert chapter.physical_forecast.outcome_resolved_at is not None


def test_seed_selects_hidden_physical_outcome_deterministically(
    content,
    completed_state_factory,
) -> None:
    even = _prerequisite_state(content, completed_state_factory, 1728)
    odd = _prerequisite_state(content, completed_state_factory, 1729)

    even_chapter = EleventhContractEngine(content).initialize(even)
    odd_chapter = EleventhContractEngine(content).initialize(odd)

    assert even_chapter.physical_forecast.outcome == PhysicalVolumeOutcome.ARRIVES
    assert odd_chapter.physical_forecast.outcome == PhysicalVolumeOutcome.FAILS
    assert not even_chapter.physical_forecast.revealed
    assert not odd_chapter.physical_forecast.revealed
