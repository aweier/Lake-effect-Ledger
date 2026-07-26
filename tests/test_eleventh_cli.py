from typer.testing import CliRunner

from lake_effect_ledger.cli import app
from lake_effect_ledger.persistence.saves import SaveRepository

runner = CliRunner()


def test_guided_retry_completes_seven_checks_without_story_penalty(tmp_path) -> None:
    correct_db = tmp_path / "correct.db"
    retry_db = tmp_path / "retry.db"
    common = [
        "--quick-start",
        "--game-mode",
        "guided",
        "--prologue-strategy",
        "correct",
        "--seed",
        "1728",
        "--eleventh-path",
        "formal_correction",
    ]
    correct = runner.invoke(
        app,
        common
        + [
            "--chapter-check-strategy",
            "correct",
            "--save-db",
            str(correct_db),
        ],
    )
    retry = runner.invoke(
        app,
        common
        + [
            "--chapter-check-strategy",
            "retry",
            "--save-db",
            str(retry_db),
        ],
    )

    assert correct.exit_code == retry.exit_code == 0
    correct_state = SaveRepository(correct_db).load()
    retry_state = SaveRepository(retry_db).load()
    chapter_check_ids = {
        "ec_sell_for_forecast_sale",
        "ec_market_versus_limit",
        "ec_sell_limit_eligibility",
        "ec_eleven_contract_ratio",
        "ec_current_overhedge",
        "ec_offset_preserves_history",
        "ec_profit_not_authorization",
    }
    assert set(retry_state.eleventh_contract.learning_check_ids) == chapter_check_ids
    assert all(
        retry_state.learning.checks[item].incorrect_attempts == 1 for item in chapter_check_ids
    )
    assert retry_state.resources == correct_state.resources
    assert retry_state.corporate_cash == correct_state.corporate_cash
    assert retry_state.ledger == correct_state.ledger
    assert retry_state.decisions == correct_state.decisions
    assert retry_state.evidence_log == correct_state.evidence_log
    assert retry_state.eleventh_contract.model_copy(
        update={"learning_check_ids": []}
    ) == correct_state.eleventh_contract.model_copy(update={"learning_check_ids": []})


def test_standard_story_skips_optional_chapter_checks(tmp_path) -> None:
    database = tmp_path / "standard.db"
    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "standard",
            "--seed",
            "1728",
            "--eleventh-path",
            "formal_correction",
            "--save-db",
            str(database),
        ],
    )

    assert result.exit_code == 0, result.output
    state = SaveRepository(database).load()
    assert state.eleventh_contract.completed
    assert not state.eleventh_contract.learning_check_ids


def test_pause_before_order_resumes_from_saved_market_brief(tmp_path) -> None:
    database = tmp_path / "before_order.db"
    first = runner.invoke(
        app,
        [
            "--quick-start",
            "--seed",
            "1728",
            "--eleventh-path",
            "formal_correction",
            "--chapter-days",
            "1",
            "--save-db",
            str(database),
        ],
    )

    assert first.exit_code == 0, first.output
    paused = SaveRepository(database).load()
    assert paused.eleventh_contract.current_day == 2
    assert paused.eleventh_contract.market_brief is not None
    assert paused.eleventh_contract.authorization is None
    assert paused.eleventh_contract.order is None
    assert paused.eleventh_contract.execution is None
    assert paused.eleventh_contract.confirmation is None

    resumed = runner.invoke(
        app,
        ["--load-autosave", "--save-db", str(database)],
    )

    assert resumed.exit_code == 0, resumed.output
    restored = SaveRepository(database).load()
    assert restored.eleventh_contract.completed
    assert restored.eleventh_contract.reconciliation is not None
    assert restored.eleventh_contract.execution.quantity == 11


def test_chapter_day_pause_and_resume_uses_saved_story_path(tmp_path) -> None:
    database = tmp_path / "day_resume.db"
    first = runner.invoke(
        app,
        [
            "--quick-start",
            "--seed",
            "1729",
            "--eleventh-path",
            "lucky_unapproved",
            "--chapter-days",
            "2",
            "--save-db",
            str(database),
        ],
    )

    assert first.exit_code == 0, first.output
    paused = SaveRepository(database).load()
    assert paused.eleventh_contract.current_day == 3
    assert paused.eleventh_contract.selected_story_path_id == "lucky_unapproved"
    assert not paused.eleventh_contract.completed

    resumed = runner.invoke(
        app,
        ["--load-autosave", "--save-db", str(database)],
    )

    assert resumed.exit_code == 0, resumed.output
    assert "Lucky Is Not Authorized" in resumed.output
    assert SaveRepository(database).load().eleventh_contract.completed


def test_pause_with_open_exception_resumes_before_position_action(tmp_path) -> None:
    database = tmp_path / "exception_resume.db"
    first = runner.invoke(
        app,
        [
            "--quick-start",
            "--seed",
            "1728",
            "--eleventh-path",
            "formal_correction",
            "--pause-with-exception",
            "--save-db",
            str(database),
        ],
    )

    assert first.exit_code == 0, first.output
    paused = SaveRepository(database).load()
    assert paused.eleventh_contract.current_day == 3
    assert paused.eleventh_contract.current_scene_index == 3
    assert paused.eleventh_contract.chapter_flags["formal_escalation"]
    assert paused.eleventh_contract.position.offset_trade is None

    resumed = runner.invoke(
        app,
        ["--load-autosave", "--save-db", str(database)],
    )

    assert resumed.exit_code == 0, resumed.output
    restored = SaveRepository(database).load()
    assert restored.eleventh_contract.completed
    assert restored.eleventh_contract.position.offset_trade is not None
    assert "Clean Correction" in resumed.output


def test_future_intraday_observations_are_debug_only(tmp_path) -> None:
    normal = runner.invoke(
        app,
        [
            "--quick-start",
            "--no-save",
            "--seed",
            "1728",
            "--eleventh-path",
            "formal_correction",
            "--chapter-days",
            "2",
        ],
    )
    debug = runner.invoke(
        app,
        [
            "--quick-start",
            "--no-save",
            "--seed",
            "1728",
            "--eleventh-path",
            "formal_correction",
            "--chapter-days",
            "2",
            "--debug",
        ],
    )

    assert normal.exit_code == debug.exit_code == 0
    assert "2028-01-25T09:20:00-06:00" not in normal.output
    assert "2028-01-25T09:20:00-06:00" in debug.output
