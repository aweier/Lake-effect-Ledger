from typer.testing import CliRunner

from lake_effect_ledger.cli import app
from lake_effect_ledger.learning.models import LearningStatus
from lake_effect_ledger.persistence.saves import SaveRepository

runner = CliRunner()


def test_guided_correct_path_reaches_episode_one(tmp_path) -> None:
    database = tmp_path / "guided.db"
    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "guided",
            "--prologue-strategy",
            "correct",
            "--save-db",
            str(database),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Day 3 — The Call complete" in result.output
    assert "The December Difference" in result.output
    state = SaveRepository(database).load()
    assert state.prologue.completed
    assert all(item.independently_demonstrated for item in state.learning.checks.values())


def test_guided_helped_path_marks_practiced_not_independent(tmp_path) -> None:
    database = tmp_path / "helped.db"
    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "guided",
            "--prologue-strategy",
            "helped",
            "--save-db",
            str(database),
        ],
    )
    assert result.exit_code == 0, result.output
    state = SaveRepository(database).load()
    assert all(not item.independently_demonstrated for item in state.learning.checks.values())
    statuses = {item.status for item in state.learning.objectives.values()}
    assert LearningStatus.PRACTICED_WITH_HELP in statuses


def test_guided_retry_path_completes_without_moral_penalty(tmp_path) -> None:
    database = tmp_path / "retry.db"
    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "guided",
            "--prologue-strategy",
            "retry",
            "--save-db",
            str(database),
        ],
    )
    assert result.exit_code == 0, result.output
    state = SaveRepository(database).load()
    assert all(item.incorrect_attempts == 1 for item in state.learning.checks.values())
    assert state.resources.integrity == 63


def test_skip_prologue_transitions_without_check_progress(tmp_path) -> None:
    database = tmp_path / "skip.db"
    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "guided",
            "--skip-prologue",
            "--save-db",
            str(database),
        ],
    )
    assert result.exit_code == 0, result.output
    state = SaveRepository(database).load()
    assert state.prologue.skipped
    assert not state.learning.checks


def test_pause_after_day_two_and_resume(tmp_path) -> None:
    database = tmp_path / "pause.db"
    first = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "guided",
            "--prologue-days",
            "2",
            "--save-db",
            str(database),
        ],
    )
    assert first.exit_code == 0, first.output
    assert "Completed 2 of 3 rotation days" in first.output
    paused = SaveRepository(database).load()
    assert paused.prologue.current_day_index == 2
    assert not paused.prologue.completed

    resumed = runner.invoke(
        app,
        ["--load-autosave", "--save-db", str(database)],
    )
    assert resumed.exit_code == 0, resumed.output
    assert "Day 3 — The Call complete" in resumed.output
    assert SaveRepository(database).load().prologue.completed


def test_standard_mode_keeps_rotation_with_optional_checks(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "standard",
            "--save-db",
            str(tmp_path / "standard.db"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Day 1 — The Board" in result.output
    assert "The December Difference" in result.output
    state = SaveRepository(tmp_path / "standard.db").load()
    assert state.prologue.completed
    assert not any(item.completed for item in state.learning.checks.values())


def test_saved_notebook_can_be_opened_without_advancing_story(tmp_path) -> None:
    database = tmp_path / "notebook.db"
    created = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "guided",
            "--prologue-strategy",
            "helped",
            "--save-db",
            str(database),
        ],
    )
    assert created.exit_code == 0, created.output
    before = SaveRepository(database).load()
    result = runner.invoke(
        app,
        [
            "--load-autosave",
            "--show-notebook",
            "--save-db",
            str(database),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Learning progress" in result.output
    assert "Glossary" in result.output
    assert "Formula reference" in result.output
    assert "Worked examples" in result.output
    assert SaveRepository(database).load() == before


def test_show_math_always_renders_reasoning_frames_in_scripted_mode(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "guided",
            "--show-math",
            "always",
            "--prologue-days",
            "1",
            "--save-db",
            str(tmp_path / "math.db"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Math / reasoning frame" in result.output
    assert "Short P&L" in result.output
