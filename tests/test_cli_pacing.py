from io import StringIO

import pytest
from questionary import Choice
from rich.console import Console
from typer.testing import CliRunner

import lake_effect_ledger.cli as cli
from lake_effect_ledger.cli import app
from lake_effect_ledger.game import create_new_game
from lake_effect_ledger.learning.choice_order import ordered_check_options
from lake_effect_ledger.learning.engine import LearningEngine
from lake_effect_ledger.learning.models import (
    CampaignTrack,
    GameMode,
    LearningStatus,
)
from lake_effect_ledger.persistence.saves import SaveRepository
from lake_effect_ledger.state import Background

runner = CliRunner()


class _FakePrompt:
    def __init__(self, answer):
        self.answer = answer

    def ask(self):
        return self.answer


class _TrackingInput(StringIO):
    def __init__(self, text: str, events: list[str], on_read=None):
        super().__init__(text)
        self.events = events
        self.on_read = on_read

    def readline(self, *args, **kwargs):
        self.events.append("enter")
        if self.on_read is not None:
            self.on_read()
        return super().readline(*args, **kwargs)


def _state(content, *, game_mode=GameMode.GUIDED):
    return create_new_game(
        name="Pacing Tester",
        background=Background.FINANCE,
        seed=1728,
        content=content,
        game_mode=game_mode,
        campaign_track=CampaignTrack.SERIES_3_CORE,
    )


def _values(choices):
    return [item.value if isinstance(item, Choice) else item for item in choices]


def test_numeric_question_uses_beginner_language_without_internal_unsure_label(
    content,
) -> None:
    output = StringIO()
    test_console = Console(file=output, force_terminal=False, color_system=None, width=100)

    cli.render_check(test_console, content.knowledge_check("d1_futures_pnl"))

    rendered = output.getvalue()
    assert "Henry Hub natural gas (NG) futures contract" in rendered
    assert "Settlement" in rendered
    assert "unsure:" not in rendered
    assert "I'm not sure" not in rendered


def test_question_panel_and_selector_share_the_shuffled_order(
    content,
    monkeypatch,
) -> None:
    state = _state(content)
    check = content.knowledge_check("d1_long_hedge_direction")
    expected_order = [item.id for item in ordered_check_options(check, game_seed=state.seed)]
    selected_order = []
    output = StringIO()
    test_console = Console(file=output, force_terminal=False, color_system=None, width=100)

    def fake_select(message, choices, **_kwargs):
        if message == "How do you want to proceed?":
            return _FakePrompt("answer")
        selected_order.extend(_values(choices))
        return _FakePrompt(check.correct_option_id)

    monkeypatch.setattr(cli, "console", test_console)
    monkeypatch.setattr(cli.questionary, "select", fake_select)

    cli._interactive_check(
        state,
        content=content,
        engine=LearningEngine(content),
        check_id=check.id,
    )

    rendered = output.getvalue()
    assert expected_order == selected_order
    assert expected_order.index(check.correct_option_id) == 2
    assert [rendered.index(f"{option_id}:") for option_id in expected_order] == sorted(
        rendered.index(f"{option_id}:") for option_id in expected_order
    )


def test_correct_feedback_waits_then_clears_before_next_question(
    content,
    monkeypatch,
    tmp_path,
) -> None:
    state = _state(content)
    repository = SaveRepository(tmp_path / "interactive-first-day.db")
    events: list[str] = []
    output = StringIO()
    test_console = Console(file=output, force_terminal=False, color_system=None, width=120)
    expected_choice_answers = {
        LearningEngine(content).expected_answer(check_id)
        for check_id in content.prologue.prologue.days[0].check_ids
        if content.knowledge_check(check_id).options
    }
    numeric_answers = iter(
        LearningEngine(content).expected_answer(check_id)
        for check_id in content.prologue.prologue.days[0].check_ids
        if not content.knowledge_check(check_id).options
    )

    def fake_select(message, choices, **_kwargs):
        events.append(message)
        values = _values(choices)
        if message == "How do you want to proceed?":
            answer = "answer"
        elif message == "Your answer:":
            answer = next(value for value in values if value in expected_choice_answers)
        else:
            answer = values[0]
        return _FakePrompt(answer)

    def verify_saved_before_wait() -> None:
        if events.count("enter") != 1:
            return
        saved = repository.load()
        assert saved.prologue.current_check_index == 1
        assert saved.learning.checks["d1_physical_direction"].completed

    def fake_clear():
        events.append("clear")
        output.write("\n<CLEAR>\n")

    monkeypatch.setattr(cli, "console", test_console)
    monkeypatch.setattr(cli, "_continuation_is_available", lambda: True)
    monkeypatch.setattr(
        cli.sys, "stdin", _TrackingInput("\n" * 6, events, verify_saved_before_wait)
    )
    monkeypatch.setattr(cli.questionary, "select", fake_select)
    monkeypatch.setattr(
        cli.questionary,
        "text",
        lambda _message, **_kwargs: _FakePrompt(next(numeric_answers)),
    )
    monkeypatch.setattr(test_console, "clear", fake_clear)

    completed = cli._play_prologue(
        state,
        content=content,
        repository=repository,
        strategy="auto",
        story_choice_id=None,
        maximum_days=1,
        skip=False,
        interactive=True,
        debug=False,
        save_enabled=True,
    )

    rendered = output.getvalue()
    assert not completed
    assert (
        rendered.index("Correct · demonstrated independently")
        < rendered.index("Press Enter to continue...")
        < rendered.index("<CLEAR>")
        < rendered.index("Knowledge check · d1_hedge_direction")
    )
    assert events.index("enter") < events.index("clear")


def test_incorrect_until_correct_pauses_before_retry_without_changing_classification(
    content,
    monkeypatch,
) -> None:
    state = _state(content)
    engine = LearningEngine(content)
    events: list[str] = []
    output = StringIO()
    test_console = Console(file=output, force_terminal=False, color_system=None, width=100)
    answers = iter(("short_physical", "long_physical"))

    def fake_select(message, choices, **_kwargs):
        events.append(message)
        return _FakePrompt("answer" if message == "How do you want to proceed?" else next(answers))

    def fake_clear():
        events.append("clear")
        output.write("\n<CLEAR>\n")

    monkeypatch.setattr(cli, "console", test_console)
    monkeypatch.setattr(cli, "_continuation_is_available", lambda: True)
    monkeypatch.setattr(cli.sys, "stdin", _TrackingInput("\n", events))
    monkeypatch.setattr(cli.questionary, "select", fake_select)
    monkeypatch.setattr(test_console, "clear", fake_clear)

    cli._interactive_check(
        state,
        content=content,
        engine=engine,
        check_id="d1_physical_direction",
    )

    rendered = output.getvalue()
    assert (
        rendered.index("Not yet")
        < rendered.index("Press Enter to continue...")
        < rendered.index("<CLEAR>")
        < rendered.rindex("Knowledge check · d1_physical_direction")
    )
    assert events[:3] == ["How do you want to proceed?", "Your answer:", "enter"]
    assert events.count("enter") == 1
    progress = state.learning.checks["d1_physical_direction"]
    assert progress.attempts == 2
    assert progress.first_attempt_correct is False
    assert (
        state.learning.objectives["physical_financial_exposure"].status
        == LearningStatus.DEMONSTRATED_AFTER_RETRY
    )


def test_show_math_pauses_before_returning_to_answer_flow(content, monkeypatch) -> None:
    state = _state(content)
    engine = LearningEngine(content)
    events: list[str] = []
    output = StringIO()
    test_console = Console(file=output, force_terminal=False, color_system=None, width=100)
    actions = iter(("math", "answer"))

    def fake_select(message, choices, **_kwargs):
        events.append(message)
        if message == "How do you want to proceed?":
            return _FakePrompt(next(actions))
        return _FakePrompt("long_physical")

    def fake_clear():
        events.append("clear")
        output.write("\n<CLEAR>\n")

    monkeypatch.setattr(cli, "console", test_console)
    monkeypatch.setattr(cli, "_continuation_is_available", lambda: True)
    monkeypatch.setattr(cli.sys, "stdin", _TrackingInput("\n", events))
    monkeypatch.setattr(cli.questionary, "select", fake_select)
    monkeypatch.setattr(test_console, "clear", fake_clear)

    cli._interactive_check(
        state,
        content=content,
        engine=engine,
        check_id="d1_physical_direction",
    )

    rendered = output.getvalue()
    assert (
        rendered.index("Math / reasoning frame")
        < rendered.index("Press Enter to continue...")
        < rendered.index("<CLEAR>")
        < rendered.rindex("Knowledge check · d1_physical_direction")
    )
    assert events.count("enter") == 1
    assert state.learning.checks["d1_physical_direction"].independently_demonstrated


def test_noninteractive_and_redirected_output_never_wait_or_clear(monkeypatch) -> None:
    class ExplodingInput:
        def isatty(self):
            return False

        def readline(self):  # pragma: no cover - a call is the failure
            raise AssertionError("redirected input must not be read")

    output = StringIO()
    redirected_console = Console(
        file=output,
        force_terminal=False,
        color_system=None,
        width=80,
    )
    monkeypatch.setattr(cli, "console", redirected_console)
    monkeypatch.setattr(cli.sys, "stdin", ExplodingInput())
    monkeypatch.setattr(
        redirected_console,
        "clear",
        lambda: (_ for _ in ()).throw(AssertionError("redirected output must not clear")),
    )

    assert not cli._continue_after_feedback(interactive=True)
    monkeypatch.setattr(
        cli,
        "_continuation_is_available",
        lambda: (_ for _ in ()).throw(AssertionError("scripted runs must short-circuit")),
    )
    assert not cli._continue_after_feedback(interactive=False)
    assert "Press Enter" not in output.getvalue()
    assert "\ufffd" not in output.getvalue()
    assert "\x1b" not in output.getvalue()


def test_core_review_uses_gate_and_matches_scripted_durable_state(
    content,
    monkeypatch,
    tmp_path,
) -> None:
    interactive_state = _state(content)
    scripted_state = _state(content)
    repository = SaveRepository(tmp_path / "interactive-review.db")
    events: list[str] = []
    output = StringIO()
    test_console = Console(file=output, force_terminal=False, color_system=None, width=120)
    learning = LearningEngine(content)

    def current_answer():
        review = interactive_state.learning.core_review
        reference = content.curriculum.review_questions[review.current_question_index]
        return learning.expected_answer(reference.check_id)

    def fake_select(message, choices, **_kwargs):
        if message == "Review action:":
            return _FakePrompt("answer")
        if message == "Your answer:":
            return _FakePrompt(current_answer())
        return _FakePrompt(_values(choices)[0])

    def fake_clear():
        events.append("clear")
        output.write("\n<CLEAR>\n")

    monkeypatch.setattr(cli, "console", test_console)
    monkeypatch.setattr(cli, "_continuation_is_available", lambda: True)
    monkeypatch.setattr(cli.sys, "stdin", _TrackingInput("\n" * 15, events))
    monkeypatch.setattr(cli.questionary, "select", fake_select)
    monkeypatch.setattr(
        cli.questionary,
        "text",
        lambda _message, **_kwargs: _FakePrompt(current_answer()),
    )
    monkeypatch.setattr(test_console, "clear", fake_clear)

    assert cli._play_core_review(
        interactive_state,
        content=content,
        repository=repository,
        style_name="learning",
        strategy="correct",
        interactive=True,
        save_enabled=True,
    )
    assert cli._play_core_review(
        scripted_state,
        content=content,
        repository=SaveRepository(tmp_path / "scripted-review.db"),
        style_name="learning",
        strategy="correct",
        interactive=False,
        save_enabled=False,
    )

    rendered = output.getvalue()
    assert events.count("enter") == 15
    assert events.count("clear") == 15
    assert rendered.rindex("Press Enter to continue...") < rendered.index("SERIES 3 CORE DEBRIEF")
    assert SaveRepository(repository.path).load().model_dump(mode="json") == (
        interactive_state.model_dump(mode="json")
    )
    assert interactive_state.model_dump(mode="json") == scripted_state.model_dump(mode="json")


@pytest.mark.parametrize(
    ("game_mode", "campaign_track"),
    [
        ("guided", "series3_core"),
        ("standard", "series3_core"),
        ("standard", "extended_story"),
    ],
)
def test_scripted_representative_paths_never_request_continuation(
    tmp_path,
    monkeypatch,
    game_mode: str,
    campaign_track: str,
) -> None:
    monkeypatch.setattr(
        cli,
        "_continuation_is_available",
        lambda: (_ for _ in ()).throw(AssertionError("scripted run checked terminal input")),
    )

    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            game_mode,
            "--campaign-track",
            campaign_track,
            "--seed",
            "1728",
            "--save-db",
            str(tmp_path / f"{game_mode}-{campaign_track}.db"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Press Enter to continue..." not in result.output
    assert "\ufffd" not in result.output
    assert "\x1b" not in result.output
