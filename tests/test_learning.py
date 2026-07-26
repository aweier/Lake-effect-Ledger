from copy import deepcopy
from decimal import Decimal

import pytest
from pydantic import ValidationError

from lake_effect_ledger.game import create_new_game
from lake_effect_ledger.learning.calculations import (
    calculate_answer,
    numeric_answer_matches,
    parse_numeric_answer,
)
from lake_effect_ledger.learning.engine import LearningEngine
from lake_effect_ledger.learning.models import (
    GameMode,
    GlossaryFile,
    KnowledgeCheckDefinition,
    LearningStatus,
    PrologueFile,
    ShowMathMode,
)
from lake_effect_ledger.narrative.engine import NarrativeEngine
from lake_effect_ledger.narrative.models import ChoiceDefinition, ContentBundle
from lake_effect_ledger.state import Background


def guided_state(content, background=Background.DATA_ANALYTICS):
    return create_new_game(
        name="Learner",
        background=background,
        seed=1729,
        content=content,
        game_mode=GameMode.GUIDED,
    )


def rebundle(content, **changes):
    values = {
        "characters": content.characters,
        "scenes": content.scenes,
        "chart": content.chart,
        "journals": content.journals,
        "events": content.events,
        "lessons": content.lessons,
        "markets": content.markets,
        "commodity_contracts": content.commodity_contracts,
        "commodity_price_paths": content.commodity_price_paths,
        "hedge_scenarios": content.hedge_scenarios,
        "hedge_narrative": content.hedge_narrative,
        "treasury_scenarios": content.treasury_scenarios,
        "game_modes": content.game_modes,
        "sources": content.sources,
        "glossary": content.glossary,
        "prologue": content.prologue,
        "first_rotation": content.first_rotation,
        "eleventh_scenario": content.eleventh_scenario,
        "eleventh_learning": content.eleventh_learning,
        "eleventh_narrative": content.eleventh_narrative,
        "audit_scenario": content.audit_scenario,
        "audit_learning": content.audit_learning,
    }
    values.update(changes)
    return ContentBundle(**values)


def protected_state(state):
    return {
        "resources": state.resources.model_dump(),
        "cash": (state.corporate_cash, state.personal_cash, state.margin_due),
        "ledger": state.ledger.model_dump(),
        "flags": deepcopy(state.flags),
        "decisions": list(state.decisions),
        "evidence": [item.model_dump() for item in state.evidence_log],
        "trajectory": state.career_trajectory.model_dump(),
    }


def test_modes_and_prologue_content_are_complete(content) -> None:
    assert {item.id.value for item in content.game_modes.modes} == {"guided", "standard"}
    assert content.game_mode(GameMode.GUIDED).recommended
    assert content.prologue.prologue.estimated_minutes == 25
    assert [item.day_number for item in content.prologue.prologue.days] == [1, 2, 3]
    assert len(content.prologue.checks) == 15


def test_all_required_check_types_are_present(content) -> None:
    assert {item.check_type.value for item in content.prologue.checks} == {
        "multiple_choice",
        "numeric",
        "position_direction",
        "interpretation",
        "prediction",
    }


def test_glossary_has_sources_topics_and_objectives(content) -> None:
    assert len(content.glossary.terms) >= 17
    for term in content.glossary.terms:
        assert term.source_ids
        assert term.series_3_topics
        assert term.learning_objective_ids
        for source_id in term.source_ids:
            assert content.source(source_id).url.startswith("https://")


@pytest.mark.parametrize(
    ("check_id", "expected"),
    [
        ("d1_futures_pnl", Decimal("-200.00")),
        ("d1_tick_value", Decimal("10.00")),
        ("d2_regional_price", Decimal("5.500")),
        ("d2_hedge_ratio", Decimal("1.0000")),
        ("d3_margin_call_amount", Decimal("75000.00")),
    ],
)
def test_numeric_checks_use_shared_commodity_math(content, check_id, expected) -> None:
    assert calculate_answer(content.knowledge_check(check_id), content) == expected


def test_numeric_parser_accepts_currency_commas_negative_and_percent() -> None:
    assert parse_numeric_answer("$75,000.00") == Decimal("75000.00")
    assert parse_numeric_answer("−200") == Decimal("-200")
    assert parse_numeric_answer("100%") == Decimal("1")


def test_numeric_comparison_uses_explicit_rounding_and_tolerance() -> None:
    assert numeric_answer_matches(
        "5.4996",
        expected=Decimal("5.500"),
        quantum=Decimal("0.001"),
        tolerance=Decimal("0.001"),
    )


@pytest.mark.parametrize(
    ("background", "objective"),
    [
        (Background.ACCOUNTING, "double_entry"),
        (Background.FINANCE, "physical_financial_exposure"),
        (Background.DATA_ANALYTICS, "reconciliation_evidence"),
    ],
)
def test_background_introduces_but_does_not_demonstrate_objective(
    content, background, objective
) -> None:
    state = guided_state(content, background)
    assert state.learning.objectives[objective].status == LearningStatus.INTRODUCED


def test_standard_mode_preserves_direct_episode_start(content) -> None:
    state = create_new_game(
        name="Standard",
        background=Background.FINANCE,
        seed=1,
        content=content,
    )
    assert state.game_mode == GameMode.STANDARD
    assert state.show_math == ShowMathMode.OFF
    assert state.prologue.completed
    assert state.prologue.transitioned_to_episode_1


def test_guided_mode_uses_junior_role_and_mode_math_default(content) -> None:
    state = guided_state(content)
    assert state.player.role == "Junior Commodity Risk Analyst"
    assert state.show_math == ShowMathMode.ON_REQUEST
    assert not state.prologue.completed


def test_independent_correct_answer_is_demonstrated(content) -> None:
    state = guided_state(content)
    engine = LearningEngine(content)
    engine.introduce_day(state, content.prologue.prologue.days[0])
    result = engine.submit(state, "d1_physical_direction", "long_physical")
    assert result.independent
    assert state.learning.objectives["physical_financial_exposure"].status == (
        LearningStatus.DEMONSTRATED
    )


def test_hint_then_correct_is_practiced_with_help(content) -> None:
    state = guided_state(content)
    engine = LearningEngine(content)
    engine.hint(state, "d1_hedge_direction")
    result = engine.submit(state, "d1_hedge_direction", "short_futures")
    assert not result.independent
    assert state.learning.objectives["short_futures_hedge"].status == (
        LearningStatus.PRACTICED_WITH_HELP
    )


def test_unsure_walkthrough_completes_without_independent_credit(content) -> None:
    state = guided_state(content)
    result = LearningEngine(content).walkthrough(state, "d1_tick_value")
    progress = state.learning.checks["d1_tick_value"]
    assert result.completed and not result.independent
    assert progress.walkthrough_used
    assert "d1_tick_value" in state.learning.notebook.worked_example_ids


def test_incorrect_answer_is_retryable_and_recommends_review(content) -> None:
    state = guided_state(content)
    engine = LearningEngine(content)
    first = engine.submit(state, "d1_physical_direction", "short_physical")
    second = engine.submit(state, "d1_physical_direction", "no_exposure")
    assert not first.correct and not second.correct
    assert state.learning.objectives["physical_financial_exposure"].status == (
        LearningStatus.REVIEW_RECOMMENDED
    )
    corrected = engine.submit(state, "d1_physical_direction", "long_physical")
    assert corrected.correct


@pytest.mark.parametrize("action", ["wrong", "hint", "unsure"])
def test_educational_actions_never_change_story_or_financial_state(content, action) -> None:
    state = guided_state(content)
    engine = LearningEngine(content)
    before = protected_state(state)
    if action == "wrong":
        engine.submit(state, "d1_physical_direction", "short_physical")
    elif action == "hint":
        engine.hint(state, "d1_physical_direction")
    else:
        engine.walkthrough(state, "d1_physical_direction")
    assert protected_state(state) == before


def test_day_completion_requires_every_check(content) -> None:
    state = guided_state(content)
    with pytest.raises(ValueError, match="incomplete checks"):
        LearningEngine(content).complete_day(state, content.prologue.prologue.days[0])


def test_skip_awards_no_fake_progress(content) -> None:
    state = guided_state(content)
    original = deepcopy(state.learning.model_dump())
    LearningEngine(content).skip_prologue(state)
    assert state.prologue.skipped and state.prologue.completed
    assert state.learning.model_dump() == original


def test_story_choice_is_durable_nonretryable_and_market_neutral(content) -> None:
    state = guided_state(content)
    market_before = state.market.model_dump()
    cash_before = state.corporate_cash
    narrative = NarrativeEngine(content)
    narrative.choose(
        state,
        "first_rotation_qualification",
        "preserve_scheduling_qualification",
    )
    assert state.market.model_dump() == market_before
    assert state.corporate_cash == cash_before
    assert state.evidence_log[-1].record_id == "comm_rotation_preserve"
    assert state.career_trajectory.tendencies == ["Still forming"]
    with pytest.raises(ValueError, match="already been applied"):
        narrative.choose(
            state,
            "first_rotation_qualification",
            "preserve_scheduling_qualification",
        )
    with pytest.raises(ValueError, match="already has a durable choice"):
        narrative.choose(
            state,
            "first_rotation_qualification",
            "soften_qualification_truthfully",
        )


def test_tendency_requires_accumulation_across_multiple_decisions(content) -> None:
    state = guided_state(content)
    narrative = NarrativeEngine(content)
    narrative.choose(
        state,
        "first_rotation_qualification",
        "preserve_scheduling_qualification",
    )
    narrative.choose(state, "december_difference", "request_meter_support")
    assert state.career_trajectory.tendencies == ["Still forming"]
    narrative.process_end_of_day(state)
    from lake_effect_ledger.commodity.engine import CommodityEngine

    CommodityEngine(content).open_hedge(state, "hedge_100")
    narrative.choose(state, "hedge_documentation", "write_accurate_hedge_memo")
    assert "Principled professional" in state.career_trajectory.tendencies


def test_broken_correct_option_is_rejected(content) -> None:
    payload = content.prologue.model_dump(mode="python")
    payload["checks"][0]["correct_option_id"] = "missing"
    with pytest.raises(ValidationError, match="valid correct answer"):
        PrologueFile.model_validate(payload)


def test_numeric_check_missing_required_calculation_input_is_rejected(content) -> None:
    payload = content.knowledge_check("d1_futures_pnl").model_dump(mode="python")
    payload["calculation"]["current_price"] = None
    with pytest.raises(ValidationError, match="missing"):
        KnowledgeCheckDefinition.model_validate(payload)


def test_invalid_retry_policy_is_rejected(content) -> None:
    payload = content.knowledge_check("d1_physical_direction").model_dump(mode="python")
    payload["retry_policy"] = "single_attempt"
    with pytest.raises(ValidationError, match="until_correct"):
        KnowledgeCheckDefinition.model_validate(payload)


def test_retryable_story_wrapper_is_rejected(content) -> None:
    payload = content.scene("first_rotation_qualification").choices[0].model_dump(mode="python")
    payload["retryable"] = True
    with pytest.raises(ValidationError):
        ChoiceDefinition.model_validate(payload)


def test_glossary_minimum_is_enforced(content) -> None:
    payload = content.glossary.model_dump(mode="python")
    payload["terms"] = payload["terms"][:16]
    with pytest.raises(ValidationError):
        GlossaryFile.model_validate(payload)


def test_unknown_source_reference_is_rejected_across_content(content) -> None:
    bad_glossary = content.glossary.model_copy(deep=True)
    bad_glossary.terms[0].source_ids = ["missing_source"]
    with pytest.raises(ValueError, match="invalid references"):
        rebundle(content, glossary=bad_glossary)


def test_unknown_check_source_is_rejected_across_content(content) -> None:
    bad_prologue = content.prologue.model_copy(deep=True)
    bad_prologue.checks[0].source_id = "missing_source"
    with pytest.raises(ValueError, match="invalid learning/source references"):
        rebundle(content, prologue=bad_prologue)


def test_unknown_story_communication_recipient_is_rejected(content) -> None:
    bad_rotation = content.first_rotation.model_copy(deep=True)
    communication = next(
        effect
        for effect in bad_rotation.scenes[0].choices[0].effects
        if effect.type == "record_communication"
    )
    communication.recipient_ids = ["unknown_person"]
    with pytest.raises(ValueError, match="references people"):
        rebundle(content, first_rotation=bad_rotation)
