import json
import sqlite3

import pytest
from questionary import Choice
from rich.console import Console
from typer.testing import CliRunner

import lake_effect_ledger.cli as cli
from lake_effect_ledger.cli import app
from lake_effect_ledger.game import create_new_game
from lake_effect_ledger.learning.core import (
    CoreReviewEngine,
    build_core_debrief,
)
from lake_effect_ledger.learning.engine import LearningEngine
from lake_effect_ledger.learning.models import (
    CampaignTrack,
    CurriculumClassification,
    CurriculumMapFile,
    KnowledgeCheckDefinition,
    LearningStatus,
    ReviewStyle,
)
from lake_effect_ledger.learning.presentation import render_notebook
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.persistence.saves import SaveRepository
from lake_effect_ledger.state import Background

runner = CliRunner()


def _guided_state(content):
    return create_new_game(
        name="Core Learner",
        background=Background.FINANCE,
        seed=1728,
        content=content,
        game_mode=cli.GameMode.GUIDED,
        campaign_track=CampaignTrack.SERIES_3_CORE,
    )


def _rebuild_content(content, **overrides):
    values = {
        name: getattr(content, name)
        for name in (
            "characters",
            "scenes",
            "chart",
            "journals",
            "events",
            "lessons",
            "markets",
            "commodity_contracts",
            "commodity_price_paths",
            "hedge_scenarios",
            "hedge_narrative",
            "treasury_scenarios",
            "game_modes",
            "curriculum",
            "sources",
            "glossary",
            "prologue",
            "first_rotation",
            "eleventh_scenario",
            "eleventh_learning",
            "eleventh_narrative",
            "audit_scenario",
            "audit_learning",
            "diligence_scenario",
            "diligence_learning",
        )
    }
    values.update(overrides)
    return ContentBundle(**values)


def test_campaign_tracks_separate_scope_from_game_mode(content) -> None:
    core = content.campaign_track(CampaignTrack.SERIES_3_CORE)
    extended = content.campaign_track(CampaignTrack.EXTENDED_STORY)
    assert core.chapter_ids == [
        "first_rotation",
        "december_difference",
        "hedge_book",
        "two_oclock_call",
        "eleventh_contract",
    ]
    assert extended.chapter_ids[:5] == core.chapter_ids
    assert extended.chapter_ids[-2:] == ["no_surprises", "diligence_room"]


def test_new_guided_game_defaults_to_recommended_core_track(content) -> None:
    state = _guided_state(content)
    assert state.campaign_track == CampaignTrack.SERIES_3_CORE
    assert not state.prologue.completed


def test_core_cli_stops_before_optional_chapters(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "guided",
            "--campaign-track",
            "series3_core",
            "--seed",
            "1728",
            "--save-db",
            str(tmp_path / "core.db"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "SERIES 3 CORE DEBRIEF" in result.output
    assert "Core Campaign complete" in result.output
    assert "Internal Audit Walkthrough Report" not in result.output
    assert "Diligence Room Report" not in result.output
    state = SaveRepository(tmp_path / "core.db").load()
    assert state.core_campaign_completed
    assert state.no_surprises is None
    assert state.diligence_room is None


def test_extended_cli_preserves_optional_chapters(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "standard",
            "--campaign-track",
            "extended_story",
            "--seed",
            "1728",
            "--save-db",
            str(tmp_path / "extended.db"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "SERIES 3 CORE DEBRIEF" in result.output
    assert "Internal Audit Walkthrough Report" in result.output
    assert "Diligence Room Report" in result.output
    state = SaveRepository(tmp_path / "extended.db").load()
    assert state.no_surprises.completed
    assert state.diligence_room.completed


def test_curriculum_maps_every_objective_and_excludes_context(content) -> None:
    assert {item.id for item in content.curriculum.objectives} == {
        item.id for item in content.lessons.lessons
    }
    context = [
        item
        for item in content.curriculum.objectives
        if item.classification == CurriculumClassification.BUSINESS_CONTEXT
    ]
    assert context
    assert all(not item.counts_toward_core for item in context)
    assert all(item.coverage_status.value == "context_only" for item in context)


def test_curriculum_review_uses_only_implemented_core_material(content) -> None:
    for reference in content.curriculum.review_questions:
        check = content.knowledge_check(reference.check_id)
        assert any(
            content.curriculum_objective(item).counts_toward_core
            for item in check.learning_objective_ids
        )
    future_ids = {item.id for item in content.curriculum.future_topics}
    assert "options_terminology" in future_ids
    assert "registration_categories" in future_ids


def test_validation_rejects_missing_curriculum_mapping(content) -> None:
    payload = content.curriculum.model_dump(mode="json")
    payload["objectives"].pop()
    curriculum = CurriculumMapFile.model_validate(payload)
    with pytest.raises(ValueError, match="classify every learning objective"):
        _rebuild_content(content, curriculum=curriculum)


def test_validation_rejects_context_as_core_and_covered_without_practice(
    content,
) -> None:
    payload = content.curriculum.model_dump(mode="json")
    context = next(
        item for item in payload["objectives"] if item["classification"] == "business_context"
    )
    context["counts_toward_core"] = True
    with pytest.raises(ValueError, match="cannot count toward core"):
        CurriculumMapFile.model_validate(payload)

    payload = content.curriculum.model_dump(mode="json")
    covered = next(item for item in payload["objectives"] if item["coverage_status"] == "covered")
    covered["check_ids"] = []
    with pytest.raises(ValueError, match="needs meaningful practice"):
        CurriculumMapFile.model_validate(payload)


def test_validation_rejects_formula_mapping_drift(content) -> None:
    payload = content.curriculum.model_dump(mode="json")
    calculated = next(item for item in payload["objectives"] if item["calculation_kinds"])
    calculated["calculation_kinds"] = []
    curriculum = CurriculumMapFile.model_validate(payload)
    with pytest.raises(ValueError, match="shared engine checks"):
        _rebuild_content(content, curriculum=curriculum)


def test_validation_rejects_checks_before_concept_introduction(content) -> None:
    payload = content.curriculum.model_dump(mode="json")
    first_check = content.prologue.checks[0]
    objective_id = first_check.learning_objective_ids[0]
    first_chapter = payload["core_chapters"][0]
    for field in (
        "introduced_objective_ids",
        "practiced_objective_ids",
        "business_context_objective_ids",
    ):
        first_chapter[field] = [item for item in first_chapter[field] if item != objective_id]
    curriculum = CurriculumMapFile.model_validate(payload)
    with pytest.raises(ValueError, match="tests concepts before introduction"):
        _rebuild_content(content, curriculum=curriculum)


def test_validation_rejects_review_of_context_only_material(content) -> None:
    context_ids = {
        item.id
        for item in content.curriculum.objectives
        if item.classification == CurriculumClassification.BUSINESS_CONTEXT
    }
    context_check = next(
        check
        for check in [
            *content.audit_learning.checks,
            *content.diligence_learning.checks,
        ]
        if set(check.learning_objective_ids) <= context_ids
    )
    payload = content.curriculum.model_dump(mode="json")
    payload["review_questions"][0]["check_id"] = context_check.id
    curriculum = CurriculumMapFile.model_validate(payload)
    with pytest.raises(ValueError, match="covers only business context"):
        _rebuild_content(content, curriculum=curriculum)


def test_validation_rejects_missing_feedback_and_numeric_units(content) -> None:
    choice_payload = next(
        check for check in content.prologue.checks if check.calculation is None
    ).model_dump(mode="json")
    choice_payload["wrong_answer_feedback"] = {}
    with pytest.raises(ValueError, match="feedback for every wrong option"):
        KnowledgeCheckDefinition.model_validate(choice_payload)

    numeric_payload = next(
        check for check in content.prologue.checks if check.calculation is not None
    ).model_dump(mode="json")
    numeric_payload["numeric_rule"]["answer_unit"] = ""
    with pytest.raises(ValueError, match="at least 1 character"):
        KnowledgeCheckDefinition.model_validate(numeric_payload)


def test_first_attempt_and_retry_are_distinct(content) -> None:
    state = _guided_state(content)
    engine = LearningEngine(content)
    engine.introduce_day(state, content.prologue.prologue.days[0])
    engine.submit(state, "d1_physical_direction", "short_physical")
    result = engine.submit(state, "d1_physical_direction", "long_physical")
    progress = state.learning.checks["d1_physical_direction"]
    assert result.correct and not result.independent
    assert progress.first_answer == "short_physical"
    assert progress.first_attempt_correct is False
    assert progress.attempts == 2
    assert progress.final_correct
    assert (
        state.learning.objectives["physical_financial_exposure"].status
        == LearningStatus.DEMONSTRATED_AFTER_RETRY
    )


def test_hint_and_walkthrough_tracking_do_not_create_mastery(content) -> None:
    state = _guided_state(content)
    engine = LearningEngine(content)
    engine.hint(state, "d1_hedge_direction")
    engine.submit(state, "d1_hedge_direction", "short_futures")
    engine.walkthrough(state, "d1_tick_value")
    hinted = state.learning.checks["d1_hedge_direction"]
    walked = state.learning.checks["d1_tick_value"]
    assert hinted.hints_used == 1 and not hinted.independently_demonstrated
    assert walked.walkthrough_used and walked.first_attempt_correct is None
    assert walked.final_correct and not walked.independently_demonstrated


def test_repeated_errors_remain_review_recommended_after_correction(content) -> None:
    state = _guided_state(content)
    engine = LearningEngine(content)
    engine.submit(state, "d1_physical_direction", "short_physical")
    engine.submit(state, "d1_physical_direction", "no_exposure")
    engine.submit(state, "d1_physical_direction", "long_physical")
    progress = state.learning.checks["d1_physical_direction"]
    assert progress.review_recommended
    assert (
        state.learning.objectives["physical_financial_exposure"].status
        == LearningStatus.REVIEW_RECOMMENDED
    )


def test_wrong_answer_feedback_and_numeric_units_are_validated(content) -> None:
    for check in [
        *content.prologue.checks,
        *content.eleventh_learning.checks,
        *content.audit_learning.checks,
        *content.diligence_learning.checks,
    ]:
        if check.calculation is None:
            wrong_ids = {item.id for item in check.options} - {check.correct_option_id}
            assert set(check.wrong_answer_feedback) == wrong_ids
        else:
            assert check.numeric_rule.answer_unit
            assert check.numeric_wrong_answer_feedback


def test_worked_examples_do_not_give_away_numeric_check_inputs(content) -> None:
    panels = {
        panel.id: panel.text
        for day in content.prologue.prologue.days
        for panel in day.concept_panels
    }
    assert "$5.80 + (-$0.30)" not in panels["d2_regional_basis"]
    assert "10 × 10,000 ÷ 100,000" not in panels["d2_ratio_roles"]
    assert "$140,000 - $90,000" not in panels["d3_margin_mechanics"]
    assert LearningEngine(content).expected_answer("d2_regional_price") == "5.500"
    assert LearningEngine(content).expected_answer("d2_hedge_ratio") == "1.0000"
    assert LearningEngine(content).expected_answer("d3_margin_call_amount") == "50000.00"


def test_show_math_uses_shared_engine_result(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "guided",
            "--campaign-track",
            "series3_core",
            "--show-math",
            "always",
            "--seed",
            "1728",
            "--save-db",
            str(tmp_path / "math.db"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Shared-engine result" in result.output
    assert "SHOW THE MATH · Settlement day" in result.output
    assert "Operating cash" in result.output
    assert "FCM cash" in result.output


def test_notebook_uses_required_sections_and_future_boundary(content) -> None:
    state = _guided_state(content)
    LearningEngine(content).introduce_day(state, content.prologue.prologue.days[0])
    console = Console(record=True, width=140)
    render_notebook(console, state, content)
    output = console.export_text()
    for heading in (
        "Futures Foundations",
        "Hedging and Basis",
        "Margin and Settlement",
        "Orders and Positions",
        "Regulations and Ethics",
        "Business Context",
        "Not Yet Covered",
    ):
        assert heading in output
    assert "core=yes" in output
    assert "core=no" in output


def test_chapter_openings_and_debriefs_are_present(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "standard",
            "--campaign-track",
            "series3_core",
            "--seed",
            "1728",
            "--save-db",
            str(tmp_path / "chapters.db"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert result.output.count("SERIES 3 FOCUS") == 5
    for chapter in (
        "First Rotation",
        "The December Difference",
        "The Hedge Book",
        "The Two O'Clock Call",
        "The Eleventh Contract",
    ):
        assert f"{chapter} · Chapter debrief" in result.output


def test_learning_review_supports_help_without_erasing_history(content) -> None:
    state = _guided_state(content)
    engine = CoreReviewEngine(content)
    engine.start(state, ReviewStyle.LEARNING)
    engine.hint(state)
    reference = engine.current_reference(state)
    engine.submit(
        state,
        LearningEngine(content).expected_answer(reference.check_id),
    )
    response = state.learning.core_review.responses["review_long_short"]
    assert response.first_attempt_correct is True
    assert response.hints_used == 1
    assert not response.independently_demonstrated


def test_checkpoint_review_is_one_answer_and_hides_hints(content) -> None:
    state = _guided_state(content)
    engine = CoreReviewEngine(content)
    engine.start(state, ReviewStyle.CHECKPOINT)
    with pytest.raises(ValueError, match="does not reveal hints"):
        engine.hint(state)
    result = engine.submit(state, "short_physical")
    assert not result.correct and result.completed
    assert state.learning.core_review.current_question_index == 1


def test_core_debrief_is_honest_about_missing_topics(content) -> None:
    state = _guided_state(content)
    debrief = build_core_debrief(state, content)
    assert "Clearinghouse function" in debrief.future_curriculum_topics
    assert "Calls, puts, writers, buyers, and assignment" in (debrief.future_curriculum_topics)
    assert "not a complete Series 3 mock exam" in debrief.disclaimer
    assert "100% Series 3 ready" not in debrief.model_dump_json()


def test_v7_migration_defaults_extended_and_marks_history_unknown(
    content,
    tmp_path,
) -> None:
    state = _guided_state(content)
    engine = LearningEngine(content)
    engine.submit(state, "d1_physical_direction", "long_physical")
    payload = state.model_dump(mode="json")
    payload["save_schema_version"] = 7
    for field in (
        "campaign_track",
        "core_chapter_debrief_ids",
        "core_debrief_completed",
        "core_campaign_completed",
    ):
        payload.pop(field)
    payload["learning"].pop("core_review")
    progress = payload["learning"]["checks"]["d1_physical_direction"]
    for field in (
        "first_answer",
        "first_attempt_correct",
        "final_correct",
        "review_recommended",
    ):
        progress.pop(field)
    progress["independently_demonstrated"] = True
    objective = payload["learning"]["objectives"]["physical_financial_exposure"]
    objective["status"] = "demonstrated"
    for field in (
        "check_ids",
        "chapter_ids",
        "independent_demonstrations",
        "retry_demonstrations",
        "assisted_completions",
    ):
        objective.pop(field)

    database = tmp_path / "v7.db"
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
                7,
                state.player.name,
                state.current_date.isoformat(),
                0,
                json.dumps(payload),
            ),
        )
    restored = repository.load()
    restored_progress = restored.learning.checks["d1_physical_direction"]
    assert restored.save_schema_version == 9
    assert restored.campaign_track == CampaignTrack.EXTENDED_STORY
    assert restored_progress.completed
    assert restored_progress.first_attempt_correct is None
    assert not restored_progress.independently_demonstrated
    assert restored.core_campaign_completed


def test_core_save_resumes_across_four_playtest_sessions(tmp_path) -> None:
    database = tmp_path / "sessions.db"
    session_1 = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "guided",
            "--campaign-track",
            "series3_core",
            "--settlement-days",
            "0",
            "--save-db",
            str(database),
        ],
    )
    assert session_1.exit_code == 0, session_1.output
    assert "Hedge Book paused" in session_1.output

    session_2 = runner.invoke(
        app,
        [
            "--load-autosave",
            "--pause-after-notification",
            "--save-db",
            str(database),
        ],
    )
    assert session_2.exit_code == 0, session_2.output
    assert "notification is saved" in session_2.output

    session_3 = runner.invoke(
        app,
        [
            "--load-autosave",
            "--chapter-days",
            "0",
            "--save-db",
            str(database),
        ],
    )
    assert session_3.exit_code == 0, session_3.output
    assert "The Eleventh Contract paused" in session_3.output

    session_4 = runner.invoke(
        app,
        ["--load-autosave", "--save-db", str(database)],
    )
    assert session_4.exit_code == 0, session_4.output
    assert "SERIES 3 CORE DEBRIEF" in session_4.output
    assert SaveRepository(database).load().core_campaign_completed


class _FakePrompt:
    def __init__(self, answer):
        self.answer = answer

    def ask(self):
        return self.answer


def test_fully_interactive_menu_path_reaches_core_boundary(
    content,
    monkeypatch,
    tmp_path,
) -> None:
    seen_messages: set[str] = set()
    repeated_question = False
    clear_count = 0
    numeric_answers = iter(
        [
            "-200",
            "10",
            "5.5",
            "1",
            "50000",
            "1.1",
            "10",
            "-200",
            "5.5",
            "1",
            "50000",
        ]
    )
    correct_by_option_set = {
        frozenset(option.id for option in check.options): check.correct_option_id
        for check in [
            *content.prologue.checks,
            *content.eleventh_learning.checks,
            *content.audit_learning.checks,
            *content.diligence_learning.checks,
        ]
        if check.options
    }

    def fake_select(message, choices, **_kwargs):
        nonlocal repeated_question
        seen_messages.add(message)
        values = [item.value if isinstance(item, Choice) else item for item in choices]
        if message == "Northstar morning book:":
            answer = "new"
        elif message == "Choose how to begin:":
            answer = "guided"
        elif message == "Choose a campaign track:":
            answer = "series3_core"
        elif message == "What training did you bring to Northstar?":
            answer = "finance"
        elif message == "What record do you create?":
            answer = values[0]
        elif message == "How do you want to proceed?":
            if not repeated_question:
                answer = "repeat"
                repeated_question = True
            else:
                answer = "answer"
        elif message == "Your answer:":
            answer = correct_by_option_set[frozenset(values)]
        elif message == "Choose a hedge level:":
            answer = "hedge_100"
        elif message == "How will Northstar handle the call and obligations?":
            answer = values[0]
        elif message == "Next action:":
            answer = "continue"
        elif message == "What do you put your name to?":
            answer = values[0]
        elif message == "What do you do?":
            answer = values[0]
        elif message == "Choose the cumulative review style:":
            answer = "learning"
        elif message == "Review action:":
            answer = "answer"
        else:
            answer = values[0]
        assert answer in values
        return _FakePrompt(answer)

    def fake_text(message, **_kwargs):
        return _FakePrompt(
            "Interactive Learner" if message == "Your name:" else next(numeric_answers)
        )

    def fake_clear():
        nonlocal clear_count
        clear_count += 1

    monkeypatch.setattr(cli.questionary, "select", fake_select)
    monkeypatch.setattr(cli.questionary, "text", fake_text)
    monkeypatch.setattr(cli.console, "clear", fake_clear)
    monkeypatch.setattr(
        cli.questionary,
        "confirm",
        lambda _message, **_kwargs: _FakePrompt(True),
    )
    result = runner.invoke(
        app,
        [
            "--save-db",
            str(tmp_path / "interactive.db"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Core Campaign complete" in result.output
    state = SaveRepository(tmp_path / "interactive.db").load()
    assert state.core_campaign_completed
    assert state.no_surprises is None
    assert repeated_question
    assert clear_count == 1
    assert state.learning.checks["d1_physical_direction"].attempts == 1
    assert {
        "Northstar morning book:",
        "Choose how to begin:",
        "Choose a campaign track:",
        "What training did you bring to Northstar?",
    } <= seen_messages
