from typer.testing import CliRunner

from lake_effect_ledger.cli import app
from lake_effect_ledger.learning.models import SnapshotProvenance
from lake_effect_ledger.notice_window.models import NoticeWindowStatus
from lake_effect_ledger.persistence.saves import SaveRepository

runner = CliRunner()


def test_notice_window_resumes_at_each_authored_boundary(content, tmp_path) -> None:
    database = tmp_path / "notice-sessions.db"
    common = [
        "--campaign-track",
        "applied_foundations",
        "--show-math",
        "on_request",
        "--chapter-check-strategy",
        "correct",
        "--applied-review-strategy",
        "correct",
        "--remediation-strategy",
        "skip",
        "--notice-check-strategy",
        "correct",
        "--notice-path",
        "evidence_first",
        "--save-db",
        str(database),
    ]

    first = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "guided",
            *common,
            "--notice-days",
            "2",
        ],
    )
    assert first.exit_code == 0, first.output
    assert "Notice Window Day 2 saved" in first.output
    after_day_2 = SaveRepository(database).load(content=content)
    assert after_day_2.notice_window.status == NoticeWindowStatus.IN_PROGRESS
    assert after_day_2.notice_window.current_day_index == 2
    assert len(after_day_2.notice_window.decisions) == 6
    assert after_day_2.current_date.isoformat() == "2028-02-06"

    second = runner.invoke(
        app,
        [
            "--load-autosave",
            *common,
            "--pause-before-notice-review",
        ],
    )
    assert second.exit_code == 0, second.output
    assert "Notice Window Day 3 saved" in second.output
    assert "Offset before the internal deadline" in second.output
    before_review = SaveRepository(database).load(content=content)
    assert before_review.notice_window.current_day_index == 3
    assert before_review.notice_window.remaining_contracts == 0
    assert not before_review.notice_window.review.started
    assert SaveRepository(database).list_saves()[0].completed is False

    third = runner.invoke(
        app,
        [
            "--load-autosave",
            *common,
            "--notice-review-style",
            "learning",
            "--notice-review-strategy",
            "correct",
            "--notice-remediation-strategy",
            "skip",
        ],
    )
    assert third.exit_code == 0, third.output
    assert "The Notice Window Debrief" in third.output
    completed = SaveRepository(database).load(content=content)
    snapshot = completed.learning.assessment_snapshots[-1]
    assert completed.notice_window.status == NoticeWindowStatus.COMPLETED
    assert snapshot.season_id == "notice_window"
    assert snapshot.provenance == SnapshotProvenance.NATIVE_V11
    assert SaveRepository(database).list_saves()[0].completed is True
