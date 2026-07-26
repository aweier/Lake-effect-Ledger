import pytest
from typer.testing import CliRunner

from lake_effect_ledger.cli import app

runner = CliRunner()


def test_scripted_cli_completes_playable_day(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--name",
            "Jordan",
            "--background",
            "data_analytics",
            "--seed",
            "1729",
            "--choice",
            "escalate_to_controller",
            "--save-db",
            str(tmp_path / "cli.db"),
            "--debug",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "LAKE EFFECT LEDGER" in result.output
    assert "December Difference" in result.output
    assert "End-of-day learning report" in result.output
    assert "state transitions" in result.output


@pytest.mark.parametrize(
    ("hedge_choice", "outcome"),
    [
        ("no_hedge", "Unhedged Winter"),
        ("hedge_50", "Margin Pressure"),
        ("hedge_100", "The Intended Hedge"),
        ("hedge_150", "The Overhedge"),
    ],
)
def test_all_scripted_hedge_paths_complete(
    tmp_path,
    hedge_choice: str,
    outcome: str,
) -> None:
    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--choice",
            "request_meter_support",
            "--hedge-choice",
            hedge_choice,
            "--memo-choice",
            "write_accurate_hedge_memo",
            "--seed",
            "1729",
            "--save-db",
            str(tmp_path / f"{hedge_choice}.db"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert f"HEDGE BOOK REPORT · {outcome}" in result.output
    assert "Operating cash reconciles: True" in result.output
    assert "total liquidity reconciles: True" in result.output
    assert "balanced=True" in result.output


def test_cli_can_pause_and_resume_market_sequence(tmp_path) -> None:
    database = tmp_path / "resume.db"
    first = runner.invoke(
        app,
        [
            "--quick-start",
            "--hedge-choice",
            "hedge_100",
            "--settlement-days",
            "2",
            "--save-db",
            str(database),
        ],
    )
    assert first.exit_code == 0, first.output
    assert "Completed 2 of 5 settlement days" in first.output

    resumed = runner.invoke(
        app,
        [
            "--load-autosave",
            "--save-db",
            str(database),
        ],
    )
    assert resumed.exit_code == 0, resumed.output
    assert "HEDGE BOOK REPORT · The Intended Hedge" in resumed.output
    assert "Operating cash reconciles: True" in resumed.output
