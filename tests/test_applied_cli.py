from typer.testing import CliRunner

from lake_effect_ledger.applied_foundations.models import AppliedSeasonStatus
from lake_effect_ledger.cli import app
from lake_effect_ledger.learning.models import CampaignTrack
from lake_effect_ledger.notice_window.models import NoticeWindowStatus
from lake_effect_ledger.persistence.saves import SaveRepository

runner = CliRunner()


def test_applied_campaign_resumes_across_two_days_day_three_and_review(
    content,
    tmp_path,
) -> None:
    database = tmp_path / "applied-sessions.db"
    common = [
        "--campaign-track",
        "applied_foundations",
        "--show-math",
        "on_request",
        "--chapter-check-strategy",
        "correct",
        "--save-db",
        str(database),
    ]

    session_1 = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "guided",
            *common,
            "--applied-path",
            "evidence_first",
            "--applied-days",
            "2",
        ],
    )
    assert session_1.exit_code == 0, session_1.output
    assert "Day 2 saved" in session_1.output
    after_day_2 = SaveRepository(database).load(content=content)
    assert after_day_2.campaign_track == CampaignTrack.APPLIED_FOUNDATIONS
    assert after_day_2.applied_foundations.current_day_index == 2
    assert after_day_2.applied_foundations.status == AppliedSeasonStatus.IN_PROGRESS
    assert len(after_day_2.applied_foundations.decisions) == 6

    session_2 = runner.invoke(
        app,
        [
            "--load-autosave",
            *common,
            "--pause-before-applied-review",
        ],
    )
    assert session_2.exit_code == 0, session_2.output
    assert "Day 3 saved" in session_2.output
    assert "Economic result versus cash timing" in session_2.output
    before_review = SaveRepository(database).load(content=content)
    assert before_review.applied_foundations.current_day_index == 3
    assert not before_review.applied_foundations.review.started
    assert SaveRepository(database).list_saves()[0].completed is False

    session_3 = runner.invoke(
        app,
        [
            "--load-autosave",
            *common,
            "--applied-review-style",
            "learning",
            "--applied-review-strategy",
            "correct",
            "--remediation-strategy",
            "skip",
        ],
    )
    assert session_3.exit_code == 0, session_3.output
    assert "Applied Foundations Debrief" in session_3.output
    assert "Applied Foundations complete" in session_3.output
    completed = SaveRepository(database).load(content=content)
    assert completed.applied_foundations.status == AppliedSeasonStatus.COMPLETED
    assert completed.applied_foundations.snapshot_finalized
    assert completed.notice_window.status == NoticeWindowStatus.COMPLETED
    assert [item.season_id for item in completed.learning.assessment_snapshots] == [
        "series3_core",
        "applied_foundations",
        "notice_window",
    ]
    assert SaveRepository(database).list_saves()[0].completed is True


def test_extended_campaign_places_applied_before_audit(content, tmp_path) -> None:
    database = tmp_path / "extended-order.db"
    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "guided",
            "--campaign-track",
            "extended_story",
            "--chapter-check-strategy",
            "correct",
            "--applied-days",
            "0",
            "--save-db",
            str(database),
        ],
    )

    assert result.exit_code == 0, result.output
    state = SaveRepository(database).load(content=content)
    assert state.core_campaign_completed
    assert state.applied_foundations.status == AppliedSeasonStatus.IN_PROGRESS
    assert state.no_surprises is None
    assert state.diligence_room is None
