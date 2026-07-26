import pytest
from typer.testing import CliRunner

from lake_effect_ledger.audit.models import AuditOutcome, AuditStage
from lake_effect_ledger.audit.report import build_internal_audit_report
from lake_effect_ledger.cli import DEFAULT_CONTENT_ROOT, app
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.persistence.saves import SaveRepository

runner = CliRunner()


@pytest.mark.parametrize(
    ("m5_path", "seed", "audit_path", "expected_prior", "expected_audit"),
    [
        (
            "formal_correction",
            1728,
            "full_disclosure",
            "clean_correction",
            AuditOutcome.NO_SURPRISES,
        ),
        (
            "formal_correction",
            1728,
            "control_worked_late",
            "clean_correction",
            AuditOutcome.CONTROL_WORKED_LATE,
        ),
        (
            "marisol_supported",
            1728,
            "supported_late",
            "supported_but_late",
            AuditOutcome.CLEAN_WALKTHROUGH,
        ),
        (
            "accept_cal",
            1729,
            "protect_desk",
            "cals_analyst",
            AuditOutcome.MANAGEMENT_OVERRIDE,
        ),
        (
            "quiet_file",
            1728,
            "quiet_supplement",
            "quiet_file",
            AuditOutcome.QUIET_FILE_OPENS,
        ),
        (
            "lucky_unapproved",
            1729,
            "lucky_unauthorized",
            "lucky_is_not_authorized",
            AuditOutcome.CLEAN_WALKTHROUGH,
        ),
        (
            "leave_open_fail",
            1729,
            "no_physical_support",
            "eleven_against_ten",
            AuditOutcome.CLEAN_WALKTHROUGH,
        ),
        (
            "formal_correction",
            1728,
            "inaccurate",
            "clean_correction",
            AuditOutcome.TWO_VERSIONS_OF_MONDAY,
        ),
        (
            "formal_correction",
            1728,
            "automated",
            "clean_correction",
            AuditOutcome.NO_SURPRISES,
        ),
        (
            "formal_correction",
            1728,
            "policy_only",
            "clean_correction",
            AuditOutcome.POLICY_IS_NOT_A_CONTROL,
        ),
        (
            "formal_correction",
            1728,
            "risk_acceptance",
            "clean_correction",
            AuditOutcome.CLEAN_WALKTHROUGH,
        ),
    ],
)
def test_scripted_audit_acceptance_paths(
    tmp_path,
    m5_path,
    seed,
    audit_path,
    expected_prior,
    expected_audit,
) -> None:
    database = tmp_path / f"{m5_path}_{audit_path}.db"
    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--seed",
            str(seed),
            "--eleventh-path",
            m5_path,
            "--audit-path",
            audit_path,
            "--save-db",
            str(database),
        ],
    )

    assert result.exit_code == 0, result.output
    state = SaveRepository(database).load()
    report = build_internal_audit_report(state, ContentBundle.load(DEFAULT_CONTENT_ROOT))
    assert state.eleventh_contract.outcome.value == expected_prior
    assert state.no_surprises.outcome == expected_audit
    assert report.reconciled_to_preserved_records
    assert report.findings
    assert all(item.evidence_record_ids for item in report.findings)
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
    ]
    helped = runner.invoke(
        app,
        common
        + [
            "--audit-check-strategy",
            "helped",
            "--save-db",
            str(helped_db),
        ],
    )
    retry = runner.invoke(
        app,
        common
        + [
            "--audit-check-strategy",
            "retry",
            "--save-db",
            str(retry_db),
        ],
    )

    assert helped.exit_code == retry.exit_code == 0
    helped_state = SaveRepository(helped_db).load()
    retry_state = SaveRepository(retry_db).load()
    check_ids = {item.id for item in ContentBundle.load(DEFAULT_CONTENT_ROOT).audit_learning.checks}
    assert set(retry_state.no_surprises.learning_check_ids) == check_ids
    assert all(retry_state.learning.checks[item].incorrect_attempts == 1 for item in check_ids)
    assert all(helped_state.learning.checks[item].walkthrough_used for item in check_ids)
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
            "--eleventh-path",
            "formal_correction",
            "--audit-path",
            "full_disclosure",
            "--save-db",
            str(database),
        ],
    )

    assert result.exit_code == 0, result.output
    state = SaveRepository(database).load()
    report = build_internal_audit_report(state, ContentBundle.load(DEFAULT_CONTENT_ROOT))
    assert not state.no_surprises.learning_check_ids
    assert report.practiced_learning_objectives


def test_pause_before_exit_resumes_using_saved_audit_path(tmp_path) -> None:
    database = tmp_path / "before_exit.db"
    first = runner.invoke(
        app,
        [
            "--quick-start",
            "--seed",
            "1728",
            "--eleventh-path",
            "formal_correction",
            "--audit-path",
            "full_disclosure",
            "--pause-before-exit",
            "--save-db",
            str(database),
        ],
    )

    assert first.exit_code == 0, first.output
    paused = SaveRepository(database).load()
    assert paused.no_surprises.current_stage == AuditStage.BEFORE_EXIT
    assert paused.no_surprises.audit_flags["paused_before_exit"]
    assert paused.no_surprises.management_responses
    assert not paused.no_surprises.completed

    resumed = runner.invoke(
        app,
        ["--load-autosave", "--save-db", str(database)],
    )

    assert resumed.exit_code == 0, resumed.output
    restored = SaveRepository(database).load()
    assert restored.no_surprises.completed
    assert restored.no_surprises.selected_story_path_id == "full_disclosure"
    assert restored.no_surprises.outcome == AuditOutcome.NO_SURPRISES
