import pytest
from typer.testing import CliRunner

from lake_effect_ledger.cli import DEFAULT_CONTENT_ROOT, app
from lake_effect_ledger.diligence.models import DiligenceOutcome, DiligenceStage
from lake_effect_ledger.diligence.report import build_diligence_room_report
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.persistence.saves import SaveRepository

runner = CliRunner()


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("full_consistent", DiligenceOutcome.CLEAN_ROOM),
        ("limited_then_supplement", DiligenceOutcome.PRICE_OF_CANDOR),
        ("inconsistent_versions", DiligenceOutcome.THREE_VERSIONS_OF_MONDAY),
        ("remediation_overstated", DiligenceOutcome.REMEDIATION_ON_PAPER),
        ("covenant_concern", DiligenceOutcome.COVENANT_CONVERSATION),
        ("cal_aligned", DiligenceOutcome.BELLANDI_CONFIDENCE),
        ("buyer_walks", DiligenceOutcome.BUYER_WALKS),
        ("conditional_close", DiligenceOutcome.CONDITIONAL_CLOSE),
    ],
)
def test_scripted_diligence_acceptance_paths(tmp_path, path, expected) -> None:
    database = tmp_path / f"{path}.db"
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
            "--audit-path",
            "full_disclosure",
            "--diligence-path",
            path,
            "--save-db",
            str(database),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "\ufffd" not in result.output
    state = SaveRepository(database).load()
    report = build_diligence_room_report(
        state,
        ContentBundle.load(DEFAULT_CONTENT_ROOT),
    )
    assert state.diligence_room.outcome == expected
    assert len(state.diligence_room.decisions) == 12
    assert len(state.diligence_room.packages) == 3
    assert len(report.scenario_sensitivities.rows) == 3
    assert report.reconciled_to_source_records
    assert report.original_package_versions_preserved
    assert all(item.total_debits == item.total_credits for item in state.ledger.entries)


def test_guided_help_and_retry_leave_story_state_identical(tmp_path) -> None:
    helped_db = tmp_path / "helped.db"
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
        "--chapter-check-strategy",
        "correct",
        "--audit-path",
        "full_disclosure",
        "--audit-check-strategy",
        "correct",
        "--diligence-path",
        "full_consistent",
    ]
    helped = runner.invoke(
        app,
        common
        + [
            "--diligence-check-strategy",
            "helped",
            "--save-db",
            str(helped_db),
        ],
    )
    retry = runner.invoke(
        app,
        common
        + [
            "--diligence-check-strategy",
            "retry",
            "--save-db",
            str(retry_db),
        ],
    )

    assert helped.exit_code == retry.exit_code == 0
    helped_state = SaveRepository(helped_db).load()
    retry_state = SaveRepository(retry_db).load()
    check_ids = {
        item.id for item in ContentBundle.load(DEFAULT_CONTENT_ROOT).diligence_learning.checks
    }
    assert set(retry_state.diligence_room.learning_check_ids) == check_ids
    assert all(retry_state.learning.checks[item].incorrect_attempts == 1 for item in check_ids)
    assert all(helped_state.learning.checks[item].walkthrough_used for item in check_ids)
    assert retry_state.diligence_room == helped_state.diligence_room
    assert retry_state.no_surprises == helped_state.no_surprises
    assert retry_state.eleventh_contract == helped_state.eleventh_contract
    assert retry_state.ledger == helped_state.ledger
    assert retry_state.resources == helped_state.resources
    assert retry_state.career_trajectory == helped_state.career_trajectory


def test_standard_story_skips_checks_but_reports_practiced_concepts(tmp_path) -> None:
    database = tmp_path / "standard.db"
    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "standard",
            "--seed",
            "1728",
            "--diligence-path",
            "full_consistent",
            "--save-db",
            str(database),
        ],
    )

    assert result.exit_code == 0, result.output
    state = SaveRepository(database).load()
    report = build_diligence_room_report(
        state,
        ContentBundle.load(DEFAULT_CONTENT_ROOT),
    )
    assert not state.diligence_room.learning_check_ids
    assert report.practiced_learning_objectives


@pytest.mark.parametrize(
    ("maximum_stages", "expected_stage"),
    [
        (0, DiligenceStage.REQUEST_LIST),
        (1, DiligenceStage.INITIAL_PACKAGE),
        (2, DiligenceStage.RISK_SCHEDULE),
        (3, DiligenceStage.Q_AND_A),
        (4, DiligenceStage.SUPPLEMENTAL),
        (5, DiligenceStage.BEFORE_COMMITTEE),
    ],
)
def test_every_diligence_stage_pause_resumes_from_saved_path(
    tmp_path,
    maximum_stages,
    expected_stage,
) -> None:
    database = tmp_path / f"stage_{maximum_stages}.db"
    first = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "standard",
            "--seed",
            "1728",
            "--diligence-path",
            "conditional_close",
            "--diligence-stages",
            str(maximum_stages),
            "--save-db",
            str(database),
        ],
    )

    assert first.exit_code == 0, first.output
    paused = SaveRepository(database).load()
    assert paused.diligence_room.current_stage == expected_stage
    assert not paused.diligence_room.completed
    assert paused.diligence_room.selected_story_path_id == "conditional_close"

    resumed = runner.invoke(
        app,
        ["--load-autosave", "--save-db", str(database)],
    )

    assert resumed.exit_code == 0, resumed.output
    restored = SaveRepository(database).load()
    assert restored.diligence_room.completed
    assert restored.diligence_room.selected_story_path_id == "conditional_close"
    assert restored.diligence_room.outcome == DiligenceOutcome.CONDITIONAL_CLOSE


def test_pause_before_committee_resumes_without_replaying_supplement(tmp_path) -> None:
    database = tmp_path / "before_committee.db"
    first = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "standard",
            "--seed",
            "1728",
            "--diligence-path",
            "limited_then_supplement",
            "--pause-before-committee",
            "--save-db",
            str(database),
        ],
    )

    assert first.exit_code == 0, first.output
    paused = SaveRepository(database).load()
    version_counts = [len(item.versions) for item in paused.diligence_room.packages]
    assert paused.diligence_room.current_stage == DiligenceStage.BEFORE_COMMITTEE
    assert paused.diligence_room.diligence_flags["paused_before_committee"]
    assert not paused.diligence_room.completed

    resumed = runner.invoke(
        app,
        ["--load-autosave", "--save-db", str(database)],
    )

    assert resumed.exit_code == 0, resumed.output
    restored = SaveRepository(database).load()
    assert restored.diligence_room.completed
    assert [len(item.versions) for item in restored.diligence_room.packages] == (version_counts)
