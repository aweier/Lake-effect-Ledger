import pytest
from typer.testing import CliRunner

from lake_effect_ledger.cli import app

runner = CliRunner()


@pytest.mark.parametrize(
    (
        "market_path",
        "hedge_choice",
        "notification",
        "funding",
        "outcome",
    ),
    [
        (
            "fictional_lake_storm_2028",
            "hedge_100",
            "notify_immediately",
            "operating_cash",
            "Cash-Rich, Payment-Poor",
        ),
        (
            "fictional_margin_squeeze_2028",
            "hedge_100",
            "notify_immediately",
            "revolver",
            "Transparent Draw",
        ),
        (
            "fictional_margin_squeeze_2028",
            "hedge_100",
            "notify_immediately",
            "reduce_position",
            "De-Hedged",
        ),
        (
            "fictional_margin_squeeze_2028",
            "hedge_100",
            "delay_notification",
            "miss_call",
            "Two O'Clock Miss",
        ),
        (
            "fictional_margin_squeeze_2028",
            "no_hedge",
            "notify_immediately",
            "operating_cash",
            "No Position, Same Problem",
        ),
    ],
)
def test_representative_treasury_cli_paths(
    market_path: str,
    hedge_choice: str,
    notification: str,
    funding: str,
    outcome: str,
) -> None:
    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--hedge-choice",
            hedge_choice,
            "--market-path",
            market_path,
            "--notification-choice",
            notification,
            "--funding-choice",
            funding,
            "--no-save",
            "--no-daily-lessons",
        ],
    )

    assert result.exit_code == 0, result.output
    assert f"TREASURY REPORT · {outcome}" in result.output
    assert "Cash and debt bridges" in result.output
    assert "Journal trail · balanced=True" in result.output
    assert "durable event record, not a conclusion about guilt" in result.output


def test_cli_pauses_after_notification_and_resumes_exact_crisis(tmp_path) -> None:
    database = tmp_path / "treasury_resume.db"
    first = runner.invoke(
        app,
        [
            "--quick-start",
            "--hedge-choice",
            "hedge_100",
            "--market-path",
            "fictional_margin_squeeze_2028",
            "--notification-choice",
            "notify_immediately",
            "--pause-after-notification",
            "--save-db",
            str(database),
            "--no-daily-lessons",
        ],
    )
    assert first.exit_code == 0, first.output
    assert "notification is saved" in first.output
    assert "choose funding" in first.output

    resumed = runner.invoke(
        app,
        [
            "--load-autosave",
            "--funding-choice",
            "revolver",
            "--save-db",
            str(database),
            "--no-daily-lessons",
        ],
    )

    assert resumed.exit_code == 0, resumed.output
    assert "TREASURY REPORT · Transparent Draw" in resumed.output
    assert "communication_notify_immediately" in resumed.output


def test_cli_rejects_revolver_without_treasury_approval() -> None:
    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--hedge-choice",
            "hedge_100",
            "--market-path",
            "fictional_margin_squeeze_2028",
            "--notification-choice",
            "notify_cal_only",
            "--funding-choice",
            "revolver",
            "--no-save",
        ],
    )

    assert result.exit_code != 0
    assert "funding choice revolver" in result.output
    assert "available: operating_cash, reduce_position, miss_call" in result.output
