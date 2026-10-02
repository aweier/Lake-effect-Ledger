from copy import deepcopy
from decimal import Decimal

import pytest
from pydantic import ValidationError

from lake_effect_ledger.applied_foundations.engine import AppliedFoundationsEngine
from lake_effect_ledger.applied_foundations.models import AppliedSeasonStatus
from lake_effect_ledger.applied_foundations.review import AppliedReviewEngine
from lake_effect_ledger.learning.calculations import calculate_answer
from lake_effect_ledger.learning.engine import LearningEngine
from lake_effect_ledger.learning.models import (
    CampaignTrack,
    ReviewStyle,
    SnapshotProvenance,
)
from lake_effect_ledger.notice_window.engine import NoticeWindowEngine
from lake_effect_ledger.notice_window.models import NoticeWindowStatus
from lake_effect_ledger.notice_window.review import NoticeWindowReviewEngine


def _complete_supply_gap(state, content) -> None:
    state.campaign_track = CampaignTrack.APPLIED_FOUNDATIONS
    state.core_campaign_completed = True
    story = AppliedFoundationsEngine(content)
    learning = LearningEngine(content)
    story.start(state)
    for day_number in range(1, 4):
        story.begin_day(state, day_number)
        while (decision := story.current_decision(state)) is not None:
            story.record_decision(
                state,
                decision.id,
                story.scripted_choice(state, "evidence_first"),
            )
        for check_id in content.applied_foundations.day(day_number).check_ids:
            learning.submit(state, check_id, learning.expected_answer(check_id))
        story.complete_day(state, require_checks=True)
    review = AppliedReviewEngine(content)
    review.start(state, ReviewStyle.LEARNING)
    while (question := review.current_question(state)) is not None:
        review.submit(state, learning.expected_answer(question.id))
    review.prepare_remediation(state, take_remediation=False)
    review.finalize_snapshot(state)
    story.mark_completed(state)


def _notice_state(content, completed_state_factory):
    state = completed_state_factory(seed=1728)
    _complete_supply_gap(state, content)
    assert state.applied_foundations.status == AppliedSeasonStatus.COMPLETED
    return state


def _complete_notice_story(state, content, path_name="evidence_first"):
    story = NoticeWindowEngine(content)
    learning = LearningEngine(content)
    story.start(state)
    for day_number in range(1, 4):
        story.begin_day(state, day_number)
        while (decision := story.current_decision(state)) is not None:
            story.record_decision(
                state,
                decision.id,
                story.scripted_choice(state, path_name),
            )
        for check_id in content.notice_window.day(day_number).check_ids:
            learning.submit(state, check_id, learning.expected_answer(check_id))
        story.complete_day(state, require_checks=True)
    story.complete_chapter(state)
    return story


def _business_regression_surface(state):
    return deepcopy(
        {
            "cash": (state.corporate_cash, state.personal_cash, state.margin_due),
            "ledger": state.ledger.model_dump(),
            "hedge_book": (state.hedge_book.model_dump() if state.hedge_book is not None else None),
            "resources": state.resources.model_dump(),
            "decisions": state.decisions,
            "career": state.career_trajectory.model_dump(),
            "applied": state.applied_foundations.model_dump(),
            "no_surprises": state.no_surprises,
            "diligence_room": state.diligence_room,
            "completed": state.completed,
        }
    )


def _wrong_answer(question) -> str:
    check = question.as_knowledge_check()
    if question.expected_answer is not None:
        return "999999999"
    return next(item.id for item in check.options if item.id != check.correct_option_id)


def test_notice_blueprint_has_fixed_scope_calendar_and_ownership(content) -> None:
    blueprint = content.notice_window
    scenario = blueprint.scenario

    assert len(blueprint.days) == 3
    assert len(blueprint.decisions) == 9
    assert all(len(item.choices) == 3 for item in blueprint.decisions)
    assert len(blueprint.checks) == 9
    assert len(blueprint.review.required) == 10
    assert len(blueprint.review.remediation) == 4
    assert len(blueprint.formulas) == 6
    assert len(blueprint.record_chain) == 11
    assert scenario.northstar_internal_action_deadline.isoformat() == "2028-02-18"
    assert scenario.exchange_last_trading_day.isoformat() == "2028-02-25"
    assert scenario.exchange_notice_day.isoformat() == "2028-02-28"
    assert scenario.delivery_month_start.isoformat() == "2028-03-01"
    assert scenario.open_contracts == scenario.offset_contracts == 2
    assert scenario.final_open_contracts == 0
    assert not scenario.delivery_intended


def test_notice_numeric_questions_use_shared_decimal_functions(content) -> None:
    for question in content.notice_window.all_questions:
        if question.expected_answer is None:
            continue
        assert calculate_answer(question.as_knowledge_check(), content) == (
            question.expected_answer
        )


@pytest.mark.parametrize(
    "path_name",
    ["evidence_first", "concise_operator", "escalation_first"],
)
def test_notice_paths_preserve_global_story_and_close_identical_local_position(
    content,
    completed_state_factory,
    path_name,
) -> None:
    state = _notice_state(content, completed_state_factory)
    before = _business_regression_surface(state)

    _complete_notice_story(state, content, path_name)

    assert _business_regression_surface(state) == before
    assert len(state.notice_window.decisions) == 9
    assert state.notice_window.remaining_contracts == 0
    assert state.notice_window.offset_completed
    assert state.notice_window.curve_calculations == {
        "normal_spread": Decimal("0.160"),
        "inverted_spread": Decimal("-0.150"),
        "normal_residual_after_carry": Decimal("0.050"),
        "two_contract_delivery_value_at_normal_nearby": Decimal("102400.00"),
    }
    assert state.notice_window.record_statuses == {
        item.id: item.status for item in content.notice_window.record_chain
    }


def test_notice_paths_cover_every_choice_once(content) -> None:
    blueprint = content.notice_window
    selected = [choice for path in blueprint.scripted_paths.values() for choice in path]
    authored = [choice.id for decision in blueprint.decisions for choice in decision.choices]

    assert len(selected) == len(set(selected)) == 27
    assert set(selected) == set(authored)


def test_notice_learning_review_freezes_separate_snapshot(
    content,
    completed_state_factory,
) -> None:
    state = _notice_state(content, completed_state_factory)
    story = _complete_notice_story(state, content)
    frozen_applied = state.learning.assessment_snapshots[0].model_dump()
    review = NoticeWindowReviewEngine(content)
    learning = LearningEngine(content)
    review.start(state, ReviewStyle.LEARNING)

    first = review.current_question(state)
    review.submit(state, _wrong_answer(first))
    review.submit(state, learning.expected_answer(first.id))
    while (question := review.current_question(state)) is not None:
        review.submit(state, learning.expected_answer(question.id))
    selected = review.prepare_remediation(state, take_remediation=True)
    assert selected == ["nwr_remediate_clearing"]
    while (question := review.current_question(state)) is not None:
        review.submit(state, learning.expected_answer(question.id))

    snapshot = review.finalize_snapshot(state)
    story.mark_completed(state)

    assert snapshot.provenance == SnapshotProvenance.NATIVE_V11
    assert snapshot.season_id == "notice_window"
    assert snapshot.completed_story_date == content.notice_window.season.end_date
    assert snapshot.questions[0].first_attempt_correct is False
    assert snapshot.questions[0].final_correct is True
    assert snapshot.questions[-1].remediation
    assert state.learning.assessment_snapshots[0].model_dump() == frozen_applied
    assert state.notice_window.status == NoticeWindowStatus.COMPLETED
    with pytest.raises(ValueError, match="append-only"):
        review.finalize_snapshot(state)
    with pytest.raises(ValidationError):
        snapshot.provenance = SnapshotProvenance.NATIVE_V10


def test_extended_notice_requires_completed_audit(content, completed_state_factory) -> None:
    state = _notice_state(content, completed_state_factory)
    state.campaign_track = CampaignTrack.EXTENDED_STORY

    with pytest.raises(ValueError, match="No Surprises"):
        NoticeWindowEngine(content).start(state)
