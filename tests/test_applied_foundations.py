from copy import deepcopy
from decimal import Decimal

import pytest
from pydantic import ValidationError

from lake_effect_ledger.applied_foundations.engine import AppliedFoundationsEngine
from lake_effect_ledger.applied_foundations.models import AppliedSeasonStatus
from lake_effect_ledger.applied_foundations.review import AppliedReviewEngine
from lake_effect_ledger.commodity.engine import CommodityEngine
from lake_effect_ledger.learning.calculations import calculate_answer
from lake_effect_ledger.learning.choice_order import ordered_check_options
from lake_effect_ledger.learning.core import CoreReviewEngine
from lake_effect_ledger.learning.engine import LearningEngine
from lake_effect_ledger.learning.models import (
    CampaignTrack,
    ReviewStyle,
    SnapshotProvenance,
)
from lake_effect_ledger.learning.snapshots import finalize_core_snapshot


def _applied_state(content, completed_state_factory, *, populated_hedge=False):
    state = completed_state_factory(seed=1728)
    state.campaign_track = CampaignTrack.APPLIED_FOUNDATIONS
    state.core_campaign_completed = True
    if populated_hedge:
        CommodityEngine(content).open_hedge(state, "hedge_100")
    return state


def _global_regression_surface(state):
    return deepcopy(
        {
            "cash": (state.corporate_cash, state.personal_cash, state.margin_due),
            "ledger": state.ledger.model_dump(),
            "hedge_book": (state.hedge_book.model_dump() if state.hedge_book is not None else None),
            "resources": state.resources.model_dump(),
            "decisions": state.decisions,
            "relationships_and_career": state.career_trajectory.model_dump(),
            "no_surprises": state.no_surprises,
            "diligence_room": state.diligence_room,
            "completed": state.completed,
        }
    )


def _complete_story(state, content, path_name="evidence_first"):
    engine = AppliedFoundationsEngine(content)
    learning = LearningEngine(content)
    engine.start(state)
    for day_number in range(1, 4):
        engine.begin_day(state, day_number)
        while (decision := engine.current_decision(state)) is not None:
            engine.record_decision(
                state,
                decision.id,
                engine.scripted_choice(state, path_name),
            )
        for check_id in content.applied_foundations.day(day_number).check_ids:
            learning.submit(state, check_id, learning.expected_answer(check_id))
        engine.complete_day(state, require_checks=True)
    engine.complete_chapter(state)
    return engine


def _wrong_answer(question) -> str:
    check = question.as_knowledge_check()
    if question.expected_answer is not None:
        return "999999999"
    return next(item.id for item in check.options if item.id != check.correct_option_id)


def test_blueprint_has_fixed_scope_ownership_and_review_bank(content) -> None:
    blueprint = content.applied_foundations

    assert len(blueprint.days) == 3
    assert len(blueprint.decisions) == 9
    assert all(len(item.choices) == 3 for item in blueprint.decisions)
    assert len(blueprint.checks) == 9
    assert len(blueprint.review.required) == 10
    assert len(blueprint.review.remediation) == 4
    assert len(blueprint.formulas) == 11
    assert [item.owner for item in blueprint.record_chain] == [
        "marisol_vega",
        "player",
        "cal_rourke",
        "cal_rourke",
        "lakefront_fcm",
        "lakefront_fcm",
        "kasia_zielinska",
        "evelyn_marsh",
    ]
    assert set(blueprint.season.coverage_upgrades) == {
        "long_futures_hedge",
        "liquidity_not_profit",
        "order_types",
        "trade_lifecycle",
        "trade_reconciliation",
        "authorization_vs_outcome",
        "records_and_ethical_conduct",
    }


def test_every_applied_numeric_answer_uses_shared_decimal_functions(content) -> None:
    for question in content.applied_foundations.all_questions:
        if question.expected_answer is None:
            continue
        assert calculate_answer(question.as_knowledge_check(), content) == (
            question.expected_answer
        )


def test_authored_tape_is_deterministic_and_deliberately_narrow(content) -> None:
    results = AppliedFoundationsEngine(content).evaluate_order_tape()

    assert [(item.order_type, item.filled, item.fill_price) for item in results] == [
        ("market", True, Decimal("5.400")),
        ("limit", False, None),
        ("stop", True, Decimal("5.420")),
    ]
    assert results[-1].triggered
    assert content.applied_foundations.order_tape.actual_order.authorized_by == ("cal_rourke")
    assert content.applied_foundations.order_tape.actual_order.prepared_by == "player"


@pytest.mark.parametrize(
    "path_name",
    ["evidence_first", "concise_operator", "escalation_first"],
)
def test_all_paths_keep_finance_authority_and_global_story_inputs_fixed(
    content,
    completed_state_factory,
    path_name,
) -> None:
    state = _applied_state(
        content,
        completed_state_factory,
        populated_hedge=True,
    )
    before = _global_regression_surface(state)

    _complete_story(state, content, path_name)

    assert _global_regression_surface(state) == before
    assert len(state.applied_foundations.decisions) == 9
    assert state.applied_foundations.confirmed_volume
    assert state.applied_foundations.record_statuses["hedge_authorization"] == ("authorized")
    assert state.applied_foundations.record_statuses["order_transmission"] == (
        "transmitted_under_supervision"
    )
    assert state.applied_foundations.record_statuses["original_confirmation"] == ("preserved")
    assert state.applied_foundations.financial.calculations == {
        "contract_count": Decimal("8"),
        "initial_margin": Decimal("120000.00"),
        "maintenance_margin": Decimal("88000.00"),
        "initial_chicago_price": Decimal("5.200"),
        "final_chicago_price": Decimal("4.650"),
        "physical_purchase_cost_variance": Decimal("44000.00"),
        "long_futures_result": Decimal("-36000.00"),
        "buyer_basis_effect": Decimal("8000.00"),
        "combined_economic_result": Decimal("8000.00"),
        "post_settlement_margin": Decimal("84000.00"),
        "margin_call": Decimal("36000.00"),
    }
    position = state.applied_foundations.financial.position
    assert position.side.value == "long"
    assert position.contracts == 8
    assert position.current_price == Decimal("4.950")
    assert position.cumulative_pnl == Decimal("-36000.00")
    assert state.applied_foundations.record_chain == [
        item.id for item in content.applied_foundations.record_chain
    ]
    assert state.applied_foundations.financial.physical_memorandum[
        "purchase_cost_variance"
    ] == Decimal("44000.00")
    assert state.applied_foundations.financial.operating_cash_movement == Decimal("-156000.00")
    AppliedFoundationsEngine(content).assert_reconciles(state)


def test_paths_cover_each_authored_choice_once(content) -> None:
    blueprint = content.applied_foundations
    flattened = [choice_id for path in blueprint.scripted_paths.values() for choice_id in path]
    authored = [choice.id for decision in blueprint.decisions for choice in decision.choices]

    assert len(flattened) == 27
    assert len(set(flattened)) == 27
    assert set(flattened) == set(authored)


def test_support_precedes_recommendation_and_player_never_transmits(
    content,
    completed_state_factory,
) -> None:
    state = _applied_state(content, completed_state_factory)
    engine = AppliedFoundationsEngine(content)
    engine.start(state)
    first = engine.current_decision(state)
    engine.record_decision(state, first.id, first.choices[0].id)
    second = engine.current_decision(state)
    engine.record_decision(state, second.id, second.choices[0].id)

    assert state.applied_foundations.confirmed_volume
    assert state.applied_foundations.record_statuses["physical_support"] == "confirmed"
    assert engine.current_decision(state).id == "af_recommendation_packet"
    assert content.applied_foundations.order_tape.actual_order.prepared_by == "player"
    assert content.applied_foundations.order_tape.actual_order.transmitting_user == ("cal_rourke")


def test_learning_review_preserves_first_attempt_and_targets_only_needed_categories(
    content,
    completed_state_factory,
) -> None:
    state = _applied_state(content, completed_state_factory)
    story = _complete_story(state, content)
    review = AppliedReviewEngine(content)
    learning = LearningEngine(content)
    review.start(state, ReviewStyle.LEARNING)

    first = review.current_question(state)
    wrong = review.submit(state, _wrong_answer(first))
    assert not wrong.correct and not wrong.completed
    review.submit(state, learning.expected_answer(first.id))

    second = review.current_question(state)
    review.hint(state)
    review.submit(state, learning.expected_answer(second.id))

    review.walkthrough(state)

    while (question := review.current_question(state)) is not None:
        review.submit(state, learning.expected_answer(question.id))

    assert state.applied_foundations.review.recommended_remediation_categories == [
        "long_hedge",
        "economics_liquidity",
    ]
    selected = review.prepare_remediation(state, take_remediation=True)
    assert selected == [
        "afr_remediate_long_90k",
        "afr_remediate_basis_economics",
    ]
    while (question := review.current_question(state)) is not None:
        review.submit(state, learning.expected_answer(question.id))

    snapshot = review.finalize_snapshot(state)
    story.mark_completed(state)
    first_result = snapshot.questions[0]

    assert snapshot.provenance == SnapshotProvenance.NATIVE_V10
    assert snapshot.completed_story_date == content.applied_foundations.season.end_date
    assert len(snapshot.questions) == 12
    assert first_result.first_attempt_correct is False
    assert first_result.final_correct is True
    assert snapshot.questions[-1].remediation
    assert state.applied_foundations.status == AppliedSeasonStatus.COMPLETED
    with pytest.raises(ValueError, match="append-only"):
        review.finalize_snapshot(state)
    with pytest.raises(ValidationError):
        snapshot.provenance = SnapshotProvenance.RECONSTRUCTED_FROM_V9


def test_checkpoint_records_wrong_required_answer_without_rewriting_it(
    content,
    completed_state_factory,
) -> None:
    state = _applied_state(content, completed_state_factory)
    _complete_story(state, content)
    review = AppliedReviewEngine(content)
    learning = LearningEngine(content)
    review.start(state, ReviewStyle.CHECKPOINT)

    first = review.current_question(state)
    result = review.submit(state, _wrong_answer(first))
    assert result.completed and not result.correct
    while (question := review.current_question(state)) is not None:
        review.submit(state, learning.expected_answer(question.id))
    review.prepare_remediation(state, take_remediation=False)
    snapshot = review.finalize_snapshot(state)

    assert snapshot.questions[0].first_attempt_correct is False
    assert snapshot.questions[0].final_correct is False
    assert state.applied_foundations.review.remediation_declined


def test_applied_learning_cannot_rewrite_frozen_core_snapshot(
    content,
    completed_state_factory,
) -> None:
    state = _applied_state(content, completed_state_factory)
    core = CoreReviewEngine(content)
    learning = LearningEngine(content)
    core.start(state, ReviewStyle.LEARNING)
    while (reference := core.current_reference(state)) is not None:
        core.submit(state, learning.expected_answer(reference.check_id))
    state.core_campaign_completed = True
    frozen_core = finalize_core_snapshot(state, content)
    before = frozen_core.model_dump()

    _complete_story(state, content)
    applied = AppliedReviewEngine(content)
    applied.start(state, ReviewStyle.LEARNING)
    while (question := applied.current_question(state)) is not None:
        applied.submit(state, learning.expected_answer(question.id))
    applied.prepare_remediation(state, take_remediation=False)
    applied.finalize_snapshot(state)

    assert frozen_core.model_dump() == before
    assert [item.season_id for item in state.learning.assessment_snapshots] == [
        "series3_core",
        "applied_foundations",
    ]


def test_applied_choice_order_is_deterministic_per_save(content) -> None:
    check = content.knowledge_check("afr_authority_records")
    authored = [item.id for item in check.options]
    first = [item.id for item in ordered_check_options(check, game_seed=1728)]

    assert first == [item.id for item in ordered_check_options(check, game_seed=1728)]
    assert [item.id for item in check.options] == authored
    assert (
        len(
            {
                tuple(item.id for item in ordered_check_options(check, game_seed=seed))
                for seed in range(12)
            }
        )
        > 1
    )
