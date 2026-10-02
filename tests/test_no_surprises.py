import json
import sqlite3
from copy import deepcopy
from datetime import timedelta
from io import StringIO

import pytest
from rich.console import Console

from lake_effect_ledger.audit.engine import InternalAuditEngine
from lake_effect_ledger.audit.models import (
    AuditOutcome,
    AuditStage,
    ControlExecution,
    ControlNature,
    FindingSeverity,
    FindingStatus,
    PackageStrategy,
    RemediationKind,
)
from lake_effect_ledger.audit.models import TestResultRating as ResultRating
from lake_effect_ledger.audit.presentation import (
    render_audit_scene,
    render_walkthrough_timeline,
)
from lake_effect_ledger.audit.report import build_internal_audit_report
from lake_effect_ledger.cli import (
    AUDIT_DAY_SCENES,
    AUDIT_PATH_CHOICES,
    CHAPTER_PATH_CHOICES,
)
from lake_effect_ledger.commodity.engine import CommodityEngine
from lake_effect_ledger.learning.engine import LearningEngine
from lake_effect_ledger.narrative.engine import NarrativeEngine
from lake_effect_ledger.persistence.saves import SaveRepository
from lake_effect_ledger.trading.engine import EleventhContractEngine
from lake_effect_ledger.trading.models import EleventhOutcome
from lake_effect_ledger.treasury.engine import TreasuryEngine

M5_DAY_1 = (
    "ec_volume_language",
    "ec_hedge_recommendation",
    "ec_risk_emphasis",
    "ec_ask_marisol",
)
M5_DAY_2 = ("ec_order_type", "ec_authorization_review")
M5_DAY_3 = (
    "ec_record_handling",
    "ec_verification",
    "ec_exception_disposition",
    "ec_position_action",
)


def _choose_m5(state, content, path, scenes):
    narrative = NarrativeEngine(content)
    for scene_id in scenes:
        narrative.choose(state, scene_id, CHAPTER_PATH_CHOICES[path][scene_id])


def _completed_m5(content, completed_state_factory, *, path="formal_correction", seed=1728):
    state = completed_state_factory(seed=seed)
    commodity = CommodityEngine(content, market_path_id="fictional_margin_squeeze_2028")
    commodity.open_hedge(state, "hedge_100")
    NarrativeEngine(content).choose(
        state,
        "hedge_documentation",
        "write_accurate_hedge_memo",
    )
    commodity.settle_next_day(state, defer_margin_call=True)
    commodity.settle_next_day(state, defer_margin_call=True)
    treasury = TreasuryEngine(content, commodity)
    treasury.initialize_crisis(state)
    treasury.record_notification(state, "notify_immediately")
    treasury.resolve_funding(state, "operating_cash")
    commodity.settle_remaining(state)
    treasury.finalize(state)
    trading = EleventhContractEngine(content)
    trading.initialize(state)
    _choose_m5(state, content, path, M5_DAY_1)
    trading.assemble_market_brief(state)
    _choose_m5(state, content, path, M5_DAY_2)
    trading.recommend_and_execute_order(state)
    _choose_m5(state, content, path, M5_DAY_3)
    trading.finalize_exception(state)
    _choose_m5(
        state,
        content,
        path,
        ("ec_fish_fry", "eleventh_episode_transition"),
    )
    trading.complete_chapter(state)
    return state


def _choose_audit(state, content, engine, audit_path, scene_id):
    engine.apply_choice(
        state,
        scene_id,
        AUDIT_PATH_CHOICES[audit_path][scene_id],
    )


def _complete_audit(state, content, *, audit_path="full_disclosure"):
    engine = InternalAuditEngine(content)
    engine.initialize(state)
    for scene_id in AUDIT_DAY_SCENES[1]:
        _choose_audit(state, content, engine, audit_path, scene_id)
    engine.prepare_initial_package(state)
    for scene_id in AUDIT_DAY_SCENES[2]:
        _choose_audit(state, content, engine, audit_path, scene_id)
    engine.conduct_walkthrough(state)
    _choose_audit(state, content, engine, audit_path, "ns_control_interpretation")
    engine.evaluate_controls(state)
    engine.prepare_findings(state)
    _choose_audit(state, content, engine, audit_path, "ns_finding_position")
    _choose_audit(state, content, engine, audit_path, "ns_supplement_package")
    engine.prepare_supplement(state)
    _choose_audit(state, content, engine, audit_path, "ns_remediation_choice")
    _choose_audit(state, content, engine, audit_path, "ns_management_response")
    engine.prepare_management_response(state)
    _choose_audit(state, content, engine, audit_path, "ns_exit_escalation")
    engine.complete(state)
    return engine


def test_evidence_request_resolves_actual_record_availability(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m5(content, completed_state_factory)
    audit = InternalAuditEngine(content).initialize(state)
    by_id = {item.request_item_id: item for item in audit.evidence_request.requested_items}

    assert len(by_id) == 16
    assert by_id["req_authorization"].stable_record_id == "auth_live_week_ten_short"
    assert by_id["req_authorization"].available
    assert by_id["req_corrective_approval"].available
    assert by_id["req_offset"].available
    assert by_id["req_physical_support"].available
    assert by_id["req_physical_support"].contemporaneous is False


def test_complete_package_includes_every_available_request_and_linked_record(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m5(content, completed_state_factory)
    engine = InternalAuditEngine(content)
    audit = engine.initialize(state)
    audit.package_strategy = PackageStrategy.COMPLETE

    response = engine.prepare_initial_package(state)

    available = {
        item.request_item_id for item in audit.evidence_request.requested_items if item.available
    }
    assert set(response.included_request_item_ids) == available
    assert response.additional_record_ids
    assert all(
        item.included_initially for item in audit.evidence_request.requested_items if item.available
    )


def test_limited_package_preserves_initial_response_and_adds_supplement(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m5(content, completed_state_factory, path="quiet_file")
    engine = InternalAuditEngine(content)
    audit = engine.initialize(state)
    audit.package_strategy = PackageStrategy.EVELYN_REVIEW
    initial = engine.prepare_initial_package(state)
    before = deepcopy(initial.model_dump(mode="json"))
    audit.supplement_choice = "disclose_omitted"

    supplement = engine.prepare_supplement(state)

    assert supplement is not None and supplement.supplemental
    assert initial.model_dump(mode="json") == before
    assert set(initial.included_request_item_ids).isdisjoint(supplement.included_request_item_ids)
    assert all(
        item.response_status == "supplemented"
        for item in audit.evidence_request.requested_items
        if item.request_item_id in supplement.included_request_item_ids
    )


def test_audit_choices_never_delete_or_change_existing_records(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m5(content, completed_state_factory, path="quiet_file")
    chapter_before = state.eleventh_contract.model_dump(mode="json")
    evidence_before = [item.model_dump(mode="json") for item in state.evidence_log]
    ledger_before = state.ledger.model_dump(mode="json")

    _complete_audit(state, content, audit_path="quiet_supplement")

    assert state.eleventh_contract.model_dump(mode="json") == chapter_before
    assert [item.model_dump(mode="json") for item in state.evidence_log] == evidence_before
    assert state.ledger.model_dump(mode="json") == ledger_before


def test_chronology_uses_record_timestamps_and_orders_authorization_before_execution(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m5(content, completed_state_factory)
    engine = InternalAuditEngine(content)
    engine.initialize(state)
    chronology = engine.build_chronology(state)
    by_id = {item.record_id: item for item in chronology.entries}

    assert (
        by_id["auth_live_week_ten_short"].timestamp
        == state.eleventh_contract.authorization.approved_at
    )
    assert (
        by_id["execution_live_week_eleven"].timestamp
        == state.eleventh_contract.execution.fill_timestamp
    )
    assert (
        by_id["auth_live_week_ten_short"].timestamp < by_id["execution_live_week_eleven"].timestamp
    )
    assert any("allowed 10" in item for item in chronology.contradictions)


def test_control_testing_finds_ten_versus_eleven_and_late_escalation(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m5(content, completed_state_factory)
    engine = InternalAuditEngine(content)
    engine.initialize(state)
    results = engine.evaluate_controls(state)
    by_objective = {item.control_objective_id: item for item in results}

    assert by_objective["ctl_authorization_limit"].rating == (
        ResultRating.REMEDIATED_AFTER_DISCOVERY
    )
    assert not by_objective["ctl_authorization_limit"].operating_effective
    assert by_objective["ctl_exception_escalation"].rating == (ResultRating.PASSED_WITH_EXCEPTION)
    assert any(item.exception_id == "exc_escalation_late" for item in state.no_surprises.exceptions)


def test_notification_can_test_timely_when_timestamp_is_prompt(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m5(content, completed_state_factory)
    chapter = state.eleventh_contract
    chapter.notifications[0] = chapter.notifications[0].model_copy(
        update={"notified_at": chapter.reconciliation.prepared_at + timedelta(hours=1)}
    )
    engine = InternalAuditEngine(content)
    engine.initialize(state)

    results = engine.evaluate_controls(state)
    escalation = next(
        item for item in results if item.control_objective_id == "ctl_exception_escalation"
    )

    assert escalation.rating == ResultRating.PASSED
    assert escalation.operating_effective


def test_late_physical_support_does_not_change_authorization_result(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m5(
        content,
        completed_state_factory,
        path="marisol_supported",
        seed=1728,
    )
    chapter = state.eleventh_contract
    assert chapter.physical_forecast.support_obtained_at > chapter.execution.fill_timestamp
    engine = InternalAuditEngine(content)
    engine.initialize(state)
    results = engine.evaluate_controls(state)

    authorization = next(
        item for item in results if item.control_objective_id == "ctl_authorization_limit"
    )
    assert authorization.rating == ResultRating.FAILED


def test_corrective_approval_precedes_offset_and_original_history_remains(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m5(content, completed_state_factory)
    chapter = state.eleventh_contract
    original_execution = chapter.execution.model_dump(mode="json")
    approval = chapter.approvals[0]
    offset = chapter.position.offset_trade

    assert approval.approved_at < offset.executed_at
    assert approval.original_execution_id == chapter.execution.execution_id
    assert offset.original_execution_id == chapter.execution.execution_id
    InternalAuditEngine(content).initialize(state)
    InternalAuditEngine(content).evaluate_controls(state)
    assert chapter.execution.model_dump(mode="json") == original_execution


def test_control_classifications_and_design_operation_are_explicit(content) -> None:
    activities = {item.objective_id: item for item in content.audit_scenario.control_activities}

    assert activities["ctl_authorization_limit"].nature == ControlNature.PREVENTIVE
    assert activities["ctl_prompt_match"].nature == ControlNature.DETECTIVE
    assert activities["ctl_record_preservation"].execution == ControlExecution.AUTOMATED
    assert activities["ctl_exception_escalation"].execution == ControlExecution.MANUAL


def test_segregation_evaluates_distinct_actual_owners(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m5(content, completed_state_factory)
    engine = InternalAuditEngine(content)
    engine.initialize(state)
    result = next(
        item
        for item in engine.evaluate_controls(state)
        if item.control_objective_id == "ctl_segregation"
    )

    assert result.rating == ResultRating.PASSED
    assert result.design_effective and result.operating_effective


def test_profit_or_loss_does_not_change_corrected_authorization_severity(
    content,
    completed_state_factory,
) -> None:
    profitable = _completed_m5(content, completed_state_factory, seed=1728)
    losing = _completed_m5(content, completed_state_factory, seed=1729)
    severities = []
    pnl_values = []
    for state in (profitable, losing):
        engine = InternalAuditEngine(content)
        engine.initialize(state)
        engine.evaluate_controls(state)
        severities.append(engine.prepare_findings(state)[0].severity)
        pnl_values.append(state.eleventh_contract.position.cumulative_pnl)

    assert pnl_values[0] != pnl_values[1]
    assert severities == [FindingSeverity.MODERATE, FindingSeverity.MODERATE]


def test_evidence_supported_dispute_is_not_marked_as_a_contradiction(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m5(content, completed_state_factory)
    engine = _complete_audit(state, content, audit_path="risk_acceptance")

    assert not state.no_surprises.audit_flags.get("walkthrough_contradiction", False)
    assert state.no_surprises.finding_posture.value == "evidence_dispute"
    assert state.no_surprises.relationships["noah_shah"] > 0
    assert engine.population(state).record_ids


def test_unsupported_management_disagreement_is_challenged(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m5(content, completed_state_factory)
    _complete_audit(state, content, audit_path="inaccurate")

    assert state.no_surprises.audit_flags["unsupported_management_disagreement"]
    assert state.no_surprises.outcome == AuditOutcome.TWO_VERSIONS_OF_MONDAY
    assert any(
        item.finding_id == "finding_inconsistent_walkthrough"
        for item in state.no_surprises.findings
    )


@pytest.mark.parametrize(
    "audit_path",
    ["full_disclosure", "policy_only", "risk_acceptance"],
)
def test_remediation_has_owner_date_interim_and_residual_risk(
    content,
    completed_state_factory,
    audit_path,
) -> None:
    state = _completed_m5(content, completed_state_factory)
    _complete_audit(state, content, audit_path=audit_path)
    remediation = state.no_surprises.remediations[0]

    assert remediation.owner.person_id
    assert remediation.target_date > content.audit_scenario.day_dates["day_4"]
    assert remediation.interim_control
    assert remediation.residual_risk
    if remediation.kind == RemediationKind.FORMAL_RISK_ACCEPTANCE:
        assert all(
            item.status == FindingStatus.RISK_ACCEPTED
            for item in state.no_surprises.management_responses
        )


def test_reports_vary_materially_by_prior_path(
    content,
    completed_state_factory,
) -> None:
    clean = _completed_m5(content, completed_state_factory, path="formal_correction")
    quiet = _completed_m5(content, completed_state_factory, path="quiet_file")
    _complete_audit(clean, content, audit_path="full_disclosure")
    _complete_audit(quiet, content, audit_path="quiet_supplement")
    clean_report = build_internal_audit_report(clean, content)
    quiet_report = build_internal_audit_report(quiet, content)

    assert clean_report.prior_transaction_outcome == EleventhOutcome.CLEAN_CORRECTION
    assert quiet_report.prior_transaction_outcome == EleventhOutcome.QUIET_FILE
    assert clean_report.outcome == AuditOutcome.NO_SURPRISES
    assert quiet_report.outcome == AuditOutcome.QUIET_FILE_OPENS
    assert clean_report.records_received_initially != quiet_report.records_received_initially
    assert clean_report.reconciled_to_preserved_records
    assert quiet_report.reconciled_to_preserved_records


def test_noah_and_marisol_dialogue_follows_available_audit_and_trade_evidence(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m5(content, completed_state_factory, path="quiet_file", seed=1728)
    audit = InternalAuditEngine(content).initialize(state)
    audit.package_strategy = PackageStrategy.EVELYN_REVIEW
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=120)

    render_audit_scene(console, state, content.audit_scene("ns_walkthrough_style"))
    render_audit_scene(console, state, content.audit_scene("ns_volume_source"))

    rendered = output.getvalue()
    assert "initial response omitted conditional records" in rendered
    assert "Friday support was not Monday support" in rendered


def test_normal_timeline_hides_unreceived_record_while_debug_resolves_it(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m5(content, completed_state_factory, path="quiet_file", seed=1728)
    engine = InternalAuditEngine(content)
    audit = engine.initialize(state)
    audit.package_strategy = PackageStrategy.EVELYN_REVIEW
    engine.prepare_initial_package(state)
    normal_output = StringIO()
    debug_output = StringIO()

    render_walkthrough_timeline(
        Console(file=normal_output, force_terminal=False, width=300),
        state,
    )
    render_walkthrough_timeline(
        Console(file=debug_output, force_terminal=False, width=300),
        state,
        debug=True,
    )

    assert "final_nomination_additional_10000" not in normal_output.getvalue()
    assert "final_nomination_additional_10000" in debug_output.getvalue()


def test_standard_story_practiced_concepts_come_from_story_decisions(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m5(content, completed_state_factory)
    _complete_audit(state, content, audit_path="policy_only")
    report = build_internal_audit_report(state, content)

    assert not state.no_surprises.learning_check_ids
    assert "Control design and operation" in report.practiced_learning_objectives
    assert "Remediation does not rewrite history" in report.practiced_learning_objectives


def test_guided_retry_changes_learning_only(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m5(content, completed_state_factory)
    engine = InternalAuditEngine(content)
    audit = engine.initialize(state)
    check_id = "audit_preventive_detective"
    protected = {
        "audit": audit.model_dump(mode="json"),
        "chapter": state.eleventh_contract.model_dump(mode="json"),
        "trajectory": state.career_trajectory.model_dump(mode="json"),
        "resources": state.resources.model_dump(mode="json"),
        "ledger": state.ledger.model_dump(mode="json"),
    }
    learning = LearningEngine(content)

    wrong = learning.submit(state, check_id, "__wrong__")
    correct = learning.submit(state, check_id, learning.expected_answer(check_id))

    assert not wrong.correct and correct.correct
    assert audit.model_dump(mode="json") == protected["audit"]
    assert state.eleventh_contract.model_dump(mode="json") == protected["chapter"]
    assert state.career_trajectory.model_dump(mode="json") == protected["trajectory"]
    assert state.resources.model_dump(mode="json") == protected["resources"]
    assert state.ledger.model_dump(mode="json") == protected["ledger"]


def test_career_changes_only_when_story_choice_is_applied(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m5(content, completed_state_factory)
    before = state.career_trajectory.model_dump(mode="json")
    engine = InternalAuditEngine(content)
    engine.initialize(state)
    engine.build_chronology(state)
    engine.prepare_initial_package(state)

    assert state.career_trajectory.model_dump(mode="json") == before
    engine.apply_choice(state, "ns_walkthrough_style", "ns_answer_accurately")
    assert state.career_trajectory.model_dump(mode="json") != before


def test_prior_conduct_drives_remediation_inclusion_and_external_interest(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m5(content, completed_state_factory)
    _complete_audit(state, content, audit_path="full_disclosure")

    assert state.no_surprises.audit_flags["player_included_in_remediation"]
    assert state.no_surprises.audit_flags["final_report_requested_by_potential_buyer_diligence"]


def test_v5_save_migrates_to_v8_with_empty_audit_and_diligence_state(
    content,
    completed_state_factory,
    tmp_path,
) -> None:
    state = _completed_m5(content, completed_state_factory)
    payload = state.model_dump(mode="json")
    payload["save_schema_version"] = 5
    payload.pop("no_surprises")
    database = tmp_path / "v5.db"
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
                5,
                state.player.name,
                state.current_date.isoformat(),
                1,
                json.dumps(payload),
            ),
        )

    restored = repository.load()

    assert restored.save_schema_version == 11
    assert restored.no_surprises is None
    assert restored.diligence_room is None
    assert restored.eleventh_contract == state.eleventh_contract


@pytest.mark.parametrize(
    ("stage_count", "expected_stage"),
    [
        (1, AuditStage.WALKTHROUGH),
        (2, AuditStage.CONTROL_TESTING),
        (3, AuditStage.PRELIMINARY_FINDINGS),
        (4, AuditStage.MANAGEMENT_RESPONSE),
        (5, AuditStage.BEFORE_EXIT),
    ],
)
def test_audit_stage_models_round_trip(
    content,
    completed_state_factory,
    tmp_path,
    stage_count,
    expected_stage,
) -> None:
    state = _completed_m5(content, completed_state_factory)
    engine = InternalAuditEngine(content)
    audit = engine.initialize(state)
    for scene_id in AUDIT_DAY_SCENES[1]:
        _choose_audit(state, content, engine, "full_disclosure", scene_id)
    engine.prepare_initial_package(state)
    if stage_count >= 2:
        for scene_id in AUDIT_DAY_SCENES[2]:
            _choose_audit(state, content, engine, "full_disclosure", scene_id)
        engine.conduct_walkthrough(state)
    if stage_count >= 3:
        _choose_audit(
            state,
            content,
            engine,
            "full_disclosure",
            "ns_control_interpretation",
        )
        engine.evaluate_controls(state)
    if stage_count >= 4:
        engine.prepare_findings(state)
        _choose_audit(state, content, engine, "full_disclosure", "ns_finding_position")
    if stage_count >= 5:
        _choose_audit(state, content, engine, "full_disclosure", "ns_supplement_package")
        engine.prepare_supplement(state)
        _choose_audit(state, content, engine, "full_disclosure", "ns_remediation_choice")
        _choose_audit(state, content, engine, "full_disclosure", "ns_management_response")
        engine.prepare_management_response(state)
    database = tmp_path / f"stage_{stage_count}.db"
    repository = SaveRepository(database)
    repository.save(state)

    restored = repository.load()

    assert audit.current_stage == expected_stage
    assert restored.no_surprises.current_stage == expected_stage
    assert restored.no_surprises.model_dump(mode="json") == audit.model_dump(mode="json")
