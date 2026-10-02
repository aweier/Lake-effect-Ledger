import json
import sqlite3
from copy import deepcopy

import pytest

from lake_effect_ledger.audit.engine import InternalAuditEngine
from lake_effect_ledger.cli import (
    AUDIT_DAY_SCENES,
    AUDIT_PATH_CHOICES,
    CHAPTER_PATH_CHOICES,
    DILIGENCE_DAY_SCENES,
    DILIGENCE_PATH_CHOICES,
)
from lake_effect_ledger.commodity.engine import CommodityEngine
from lake_effect_ledger.diligence.engine import DiligenceEngine
from lake_effect_ledger.diligence.models import (
    DiligenceOutcome,
    DiligenceRoomState,
    DisclosureStatus,
    RemediationStatus,
)
from lake_effect_ledger.diligence.report import build_diligence_room_report
from lake_effect_ledger.learning.engine import LearningEngine
from lake_effect_ledger.narrative.engine import NarrativeEngine
from lake_effect_ledger.persistence.saves import SaveRepository
from lake_effect_ledger.trading.engine import EleventhContractEngine
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


def _completed_m6(
    content,
    completed_state_factory,
    *,
    m5_path="formal_correction",
    audit_path="full_disclosure",
    seed=1728,
):
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
    _choose_m5(state, content, m5_path, M5_DAY_1)
    trading.assemble_market_brief(state)
    _choose_m5(state, content, m5_path, M5_DAY_2)
    trading.recommend_and_execute_order(state)
    _choose_m5(state, content, m5_path, M5_DAY_3)
    trading.finalize_exception(state)
    _choose_m5(
        state,
        content,
        m5_path,
        ("ec_fish_fry", "eleventh_episode_transition"),
    )
    trading.complete_chapter(state)
    audit = InternalAuditEngine(content)
    audit.initialize(state)
    for scene_id in AUDIT_DAY_SCENES[1]:
        audit.apply_choice(
            state,
            scene_id,
            AUDIT_PATH_CHOICES[audit_path][scene_id],
        )
    audit.prepare_initial_package(state)
    for scene_id in AUDIT_DAY_SCENES[2]:
        audit.apply_choice(
            state,
            scene_id,
            AUDIT_PATH_CHOICES[audit_path][scene_id],
        )
    audit.conduct_walkthrough(state)
    audit.apply_choice(
        state,
        "ns_control_interpretation",
        AUDIT_PATH_CHOICES[audit_path]["ns_control_interpretation"],
    )
    audit.evaluate_controls(state)
    audit.prepare_findings(state)
    audit.apply_choice(
        state,
        "ns_finding_position",
        AUDIT_PATH_CHOICES[audit_path]["ns_finding_position"],
    )
    audit.apply_choice(
        state,
        "ns_supplement_package",
        AUDIT_PATH_CHOICES[audit_path]["ns_supplement_package"],
    )
    audit.prepare_supplement(state)
    for scene_id in ("ns_remediation_choice", "ns_management_response"):
        audit.apply_choice(
            state,
            scene_id,
            AUDIT_PATH_CHOICES[audit_path][scene_id],
        )
    audit.prepare_management_response(state)
    audit.apply_choice(
        state,
        "ns_exit_escalation",
        AUDIT_PATH_CHOICES[audit_path]["ns_exit_escalation"],
    )
    audit.complete(state)
    return state


def _choose_diligence(state, content, engine, path, scene_id):
    engine.apply_choice(
        state,
        scene_id,
        DILIGENCE_PATH_CHOICES[path][scene_id],
    )


def _through_initial(state, content, *, path="full_consistent"):
    engine = DiligenceEngine(content)
    engine.initialize(state)
    engine.advance_request_list(state)
    for scene_id in DILIGENCE_DAY_SCENES[1]:
        _choose_diligence(state, content, engine, path, scene_id)
    engine.prepare_initial_packages(state)
    return engine


def _through_risk(state, content, *, path="full_consistent"):
    engine = _through_initial(state, content, path=path)
    for scene_id in DILIGENCE_DAY_SCENES[2]:
        _choose_diligence(state, content, engine, path, scene_id)
    engine.prepare_risk_schedule(state)
    return engine


def _through_q_and_a(state, content, *, path="full_consistent"):
    engine = _through_risk(state, content, path=path)
    for scene_id in DILIGENCE_DAY_SCENES[3]:
        _choose_diligence(state, content, engine, path, scene_id)
    engine.prepare_q_and_a(state)
    return engine


def _complete_diligence(state, content, *, path="full_consistent"):
    engine = _through_q_and_a(state, content, path=path)
    _choose_diligence(
        state,
        content,
        engine,
        path,
        "dr_inconsistency_action",
    )
    engine.prepare_supplement(state)
    for scene_id in ("dr_committee_position", "dr_final_action"):
        _choose_diligence(state, content, engine, path, scene_id)
    engine.complete(state)
    return engine


def test_requests_overlap_without_being_identical(content, completed_state_factory) -> None:
    state = _completed_m6(content, completed_state_factory)
    diligence = DiligenceEngine(content).initialize(state)
    request_sets = [{item.item_id for item in request.items} for request in diligence.requests]

    assert len(diligence.requests) == 3
    assert len({frozenset(items) for items in request_sets}) == 3
    assert set.intersection(*request_sets) >= {
        "req_audit_report",
        "req_open_findings",
        "req_remediation",
        "req_exceptions",
    }
    assert {request.stakeholder_id for request in diligence.requests} == {
        "sofia_marin",
        "mara_voss",
        "ingrid_holtz",
    }


def test_complete_package_includes_every_available_request(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    _through_initial(state, content)
    diligence = state.diligence_room

    for package in diligence.packages:
        request = next(item for item in diligence.requests if item.request_id == package.request_id)
        available_ids = {item.item_id for item in request.items if item.available}
        assert set(package.versions[0].included_item_ids) == available_ids
        assert all(package.versions[0].source_record_ids)


def test_limited_package_records_relevant_omissions(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    _through_initial(state, content, path="limited_then_supplement")
    buyer = next(
        item for item in state.diligence_room.packages if item.package_id == "package_buyer"
    )

    assert "req_audit_report" in buyer.versions[0].omitted_requested_item_ids
    request = next(
        item for item in state.diligence_room.requests if item.request_id == buyer.request_id
    )
    assert next(item for item in request.items if item.item_id == "req_audit_report").status == (
        DisclosureStatus.OMITTED
    )


def test_supplement_preserves_limited_delivery(content, completed_state_factory) -> None:
    state = _completed_m6(content, completed_state_factory)
    _through_q_and_a(state, content, path="limited_then_supplement")
    buyer = next(
        item for item in state.diligence_room.packages if item.package_id == "package_buyer"
    )
    original = buyer.versions[0].model_dump(mode="json")
    engine = DiligenceEngine(content)
    _choose_diligence(
        state,
        content,
        engine,
        "limited_then_supplement",
        "dr_inconsistency_action",
    )
    engine.prepare_supplement(state)

    assert buyer.versions[0].model_dump(mode="json") == original
    assert len(buyer.versions) >= 3
    assert buyer.versions[-1].change_kind == "supplement"
    assert "req_audit_report" in buyer.versions[-1].included_item_ids


def test_source_references_resolve_supported_authorized_and_executed_values(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    diligence = DiligenceEngine(content).initialize(state)
    facts = {item.fact_key: item for item in diligence.source_references}

    assert facts["supported_volume_trade_date"].value_text == "100000"
    assert facts["authorized_contracts"].value_text == "10"
    assert facts["executed_contracts"].value_text == "11"
    assert facts["authorized_contracts"].record_id == "auth_live_week_ten_short"
    assert facts["executed_contracts"].record_id == "blotter_eleventh_contract"


def test_later_supported_volume_keeps_earlier_value_and_date(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory, seed=1728)
    diligence = DiligenceEngine(content).initialize(state)
    facts = {item.fact_key: item for item in diligence.source_references}

    assert facts["supported_volume_trade_date"].value_text == "100000"
    assert facts["eventual_supported_volume"].value_text == "110000"
    assert facts["eventual_supported_volume"].as_of is not None


def test_margin_omission_is_preserved_and_flagged(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    engine = _through_initial(state, content)
    engine.apply_choice(state, "dr_number_source", "dr_omit_margin_history")
    engine.apply_choice(
        state,
        "dr_scenario_scope",
        "dr_include_full_sensitivities",
    )
    engine.apply_choice(
        state,
        "dr_remediation_status",
        "dr_label_actual_remediation",
    )
    engine.prepare_risk_schedule(state)
    lender = next(
        item for item in state.diligence_room.packages if item.package_id == "package_lender"
    )

    assert "episode_01_hedge_book" in lender.versions[0].source_record_ids
    assert "episode_01_hedge_book" not in lender.versions[1].source_record_ids
    assert "req_margin_history" in lender.versions[1].omitted_requested_item_ids
    assert lender.versions[1].fact_values["margin_call_disclosed"] == "no"
    assert state.diligence_room.risk_schedule is not None
    assert engine.available_source_record_ids(state) >= {
        "episode_01_hedge_book",
        "great_lakes_revolver",
    }


def test_margin_correction_restores_source_without_overwriting_prior_delivery(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    engine = _through_initial(state, content)
    engine.apply_choice(state, "dr_number_source", "dr_omit_margin_history")
    engine.apply_choice(
        state,
        "dr_scenario_scope",
        "dr_include_full_sensitivities",
    )
    engine.apply_choice(
        state,
        "dr_remediation_status",
        "dr_label_actual_remediation",
    )
    engine.prepare_risk_schedule(state)
    for scene_id in DILIGENCE_DAY_SCENES[3]:
        _choose_diligence(state, content, engine, "full_consistent", scene_id)
    engine.prepare_q_and_a(state)
    lender = next(
        item for item in state.diligence_room.packages if item.package_id == "package_lender"
    )
    omitted_version = lender.versions[-1].model_dump(mode="json")

    engine.apply_choice(
        state,
        "dr_inconsistency_action",
        "dr_issue_correction",
    )
    engine.prepare_supplement(state)

    assert lender.versions[-2].model_dump(mode="json") == omitted_version
    assert lender.versions[-1].change_kind == "correction"
    assert "req_margin_history" in lender.versions[-1].included_item_ids
    assert "req_margin_history" not in lender.versions[-1].omitted_requested_item_ids
    assert "episode_01_hedge_book" in lender.versions[-1].source_record_ids
    assert lender.versions[-1].fact_values["margin_call_disclosed"] == "yes"


def test_revolver_and_covenant_schedule_resolve_treasury_state(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    _through_risk(state, content)
    metrics = {item.metric_id: item for item in state.diligence_room.risk_schedule.metrics}
    treasury = state.treasury

    assert metrics["revolver"].numeric_value == treasury.facility.outstanding
    assert metrics["undrawn"].numeric_value == treasury.facility.undrawn_availability
    assert metrics["covenant_headroom"].numeric_value == (
        treasury.covenant_result.available_liquidity - treasury.covenant_result.minimum_required
    )


def test_scenario_analysis_math_reconciles(content, completed_state_factory) -> None:
    state = _completed_m6(content, completed_state_factory)
    _through_risk(state, content)

    for row in state.diligence_room.scenario_analysis.rows:
        assert row.physical_economic_effect + row.futures_effect == row.net_economic_effect
        quantity = state.eleventh_contract.physical_forecast.eventual_supported_volume_mmbtu
        assert row.basis_effect == row.chicago_basis_change * quantity


def test_scenario_analysis_never_mutates_real_state(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    engine = DiligenceEngine(content)
    engine.initialize(state)
    before = engine._protected_records(state)

    first = engine.build_scenario_analysis(state)
    second = engine.build_scenario_analysis(state)

    assert first == second
    assert engine._protected_records(state) == before
    assert not first.alters_game_state
    assert not first.creates_accounting_entries


def test_remediation_approval_is_not_implementation_or_testing(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    engine = DiligenceEngine(content)

    assert engine.actual_remediation_status(state) == RemediationStatus.APPROVED
    assert engine.actual_remediation_status(state) not in {
        RemediationStatus.IMPLEMENTED,
        RemediationStatus.TESTED,
        RemediationStatus.CLOSED,
    }


def test_risk_acceptance_remains_distinct_from_implementation(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(
        content,
        completed_state_factory,
        audit_path="risk_acceptance",
    )

    assert DiligenceEngine(content).actual_remediation_status(state) == (
        RemediationStatus.RISK_ACCEPTED
    )


def test_consistent_packages_share_canonical_values(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    _through_risk(state, content)
    latest = [item.versions[-1] for item in state.diligence_room.packages]

    for key in set.intersection(*(set(item.fact_values) for item in latest)):
        assert len({item.fact_values[key] for item in latest}) == 1
    assert state.diligence_room.inconsistencies == []


def test_inconsistent_packages_create_typed_records(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    _through_risk(state, content, path="inconsistent_versions")

    assert state.diligence_room.inconsistencies
    assert {item.fact_key for item in state.diligence_room.inconsistencies} >= {
        "authorized_contracts",
        "supported_volume_trade_date",
    }
    assert all(
        item.first_package_id != item.second_package_id
        for item in state.diligence_room.inconsistencies
    )
    assert {
        item.first_version
        for item in state.diligence_room.inconsistencies
        if item.fact_key == "authorized_contracts"
    } | {
        item.second_version
        for item in state.diligence_room.inconsistencies
        if item.fact_key == "authorized_contracts"
    } >= {1, 2}


def test_correction_preserves_original_version_and_marks_conflict(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    engine = _through_q_and_a(state, content, path="remediation_overstated")
    buyer = next(
        item for item in state.diligence_room.packages if item.package_id == "package_buyer"
    )
    before = [item.model_dump(mode="json") for item in buyer.versions]
    _choose_diligence(
        state,
        content,
        engine,
        "remediation_overstated",
        "dr_inconsistency_action",
    )
    engine.prepare_supplement(state)

    assert [item.model_dump(mode="json") for item in buyer.versions[: len(before)]] == before
    assert buyer.versions[-1].change_kind == "correction"
    assert any(item.corrected_by_package_id for item in state.diligence_room.inconsistencies)


def test_q_and_a_records_are_timestamped_and_linked(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    _through_q_and_a(state, content)
    diligence = state.diligence_room

    assert len(diligence.questions) == 8
    assert len(diligence.responses) == 8
    assert {item.question_id for item in diligence.responses} == {
        item.question_id for item in diligence.questions
    }
    assert all(item.responded_at and item.source_record_ids for item in diligence.responses)


def test_state_rejects_missing_stakeholder_and_unknown_q_and_a_links(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    _through_q_and_a(state, content)
    payload = state.diligence_room.model_dump(mode="json")
    payload["stakeholders"] = [
        item for item in payload["stakeholders"] if item["stakeholder_id"] != "sofia_marin"
    ]
    with pytest.raises(ValueError, match="stakeholder identities"):
        DiligenceRoomState.model_validate(payload)

    payload = state.diligence_room.model_dump(mode="json")
    payload["responses"][0]["question_id"] = "missing_question"
    with pytest.raises(ValueError, match="unknown question"):
        DiligenceRoomState.model_validate(payload)


def test_narrow_answer_gets_supplement_without_overwrite(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    engine = _through_q_and_a(state, content, path="cal_aligned")
    response = next(item for item in state.diligence_room.responses if not item.complete)
    original = response.model_dump(mode="json")
    _choose_diligence(
        state,
        content,
        engine,
        "cal_aligned",
        "dr_inconsistency_action",
    )
    engine.prepare_supplement(state)

    assert response.model_dump(mode="json") == original
    assert state.diligence_room.supplemental_responses
    assert state.diligence_room.supplemental_responses[0].original_response_id == (
        response.response_id
    )


def test_management_representation_is_source_checked(
    content,
    completed_state_factory,
) -> None:
    accurate = _completed_m6(content, completed_state_factory)
    preferred = _completed_m6(content, completed_state_factory)
    _through_q_and_a(accurate, content)
    _through_q_and_a(preferred, content, path="cal_aligned")

    assert accurate.diligence_room.management_representations[0].consistent_with_sources
    assert not preferred.diligence_room.management_representations[0].consistent_with_sources
    assert (
        "Remediation is complete."
        in (preferred.diligence_room.management_representations[0].statements["remediation"])
    )


def test_qualitative_significance_is_not_hidden_by_threshold(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    _through_risk(state, content)
    assessment = state.diligence_room.risk_schedule.significance

    assert assessment.qualitative_factors
    assert assessment.significant_for_diligence
    assert assessment.accounting_materiality_conclusion == "not_concluded"
    assert assessment.legal_conclusion == "not_concluded"
    assert "fictional" in assessment.caveat.lower()


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
def test_outcomes_derive_from_conduct(
    content,
    completed_state_factory,
    path,
    expected,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    _complete_diligence(state, content, path=path)

    assert state.diligence_room.outcome == expected
    assert state.diligence_room.transaction_status is not None
    assert len(state.diligence_room.decisions) == 12


def test_stakeholder_reactions_differ_by_actual_conduct(
    content,
    completed_state_factory,
) -> None:
    clean = _completed_m6(content, completed_state_factory)
    walk = _completed_m6(content, completed_state_factory)
    _complete_diligence(clean, content, path="full_consistent")
    _complete_diligence(walk, content, path="buyer_walks")

    clean_reactions = {
        item.stakeholder_id: item.trust_delta for item in clean.diligence_room.stakeholder_reactions
    }
    walk_reactions = {
        item.stakeholder_id: item.trust_delta for item in walk.diligence_room.stakeholder_reactions
    }
    assert clean_reactions["sofia_marin"] > walk_reactions["sofia_marin"]
    assert clean_reactions["ingrid_holtz"] > walk_reactions["ingrid_holtz"]


def test_standard_story_concepts_come_from_decisions(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    _complete_diligence(state, content)
    report = build_diligence_room_report(state, content)

    assert state.diligence_room.learning_check_ids == []
    assert "Sensitivity analysis is not a forecast" in report.practiced_learning_objectives
    assert "Consistent facts for different stakeholders" in (report.practiced_learning_objectives)


def test_guided_retry_changes_learning_only(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    engine = DiligenceEngine(content)
    engine.initialize(state)
    protected = engine._protected_records(state)
    diligence_before = state.diligence_room.model_dump(mode="json")
    trajectory_before = deepcopy(state.career_trajectory)
    learning = LearningEngine(content)
    check_id = "diligence_supported_volume"

    learning.submit(state, check_id, "__wrong__")
    learning.submit(state, check_id, learning.expected_answer(check_id))

    assert engine._protected_records(state) == protected
    assert state.diligence_room.model_dump(mode="json") == diligence_before
    assert state.career_trajectory == trajectory_before
    assert state.learning.checks[check_id].incorrect_attempts == 1


def test_career_effects_come_only_from_story_decisions(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    engine = DiligenceEngine(content)
    engine.initialize(state)
    before = deepcopy(state.career_trajectory)
    LearningEngine(content).walkthrough(state, "diligence_significance")

    assert state.career_trajectory == before
    engine.advance_request_list(state)
    _choose_diligence(
        state,
        content,
        engine,
        "full_consistent",
        "dr_package_scope",
    )
    assert state.career_trajectory != before


def test_report_reconciles_sources_and_preserves_versions(
    content,
    completed_state_factory,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    _complete_diligence(state, content, path="conditional_close")
    report = build_diligence_room_report(state, content)

    assert report.reconciled_to_source_records
    assert report.original_package_versions_preserved
    assert report.risk_schedule.metrics
    assert len(report.scenario_sensitivities.rows) == 3
    assert report.audit_findings_referenced
    assert report.career_consequences
    assert report.prior_choice_effects


def test_v6_save_migrates_to_v8_with_empty_diligence(
    content,
    completed_state_factory,
    tmp_path,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    payload = state.model_dump(mode="json")
    payload["save_schema_version"] = 6
    payload.pop("diligence_room")
    database = tmp_path / "v6.db"
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
                6,
                state.player.name,
                state.current_date.isoformat(),
                1,
                json.dumps(payload),
            ),
        )

    restored = repository.load()

    assert restored.save_schema_version == 11
    assert restored.no_surprises == state.no_surprises
    assert restored.diligence_room is None


def test_diligence_state_round_trip_at_each_engine_boundary(
    content,
    completed_state_factory,
    tmp_path,
) -> None:
    state = _completed_m6(content, completed_state_factory)
    engine = DiligenceEngine(content)
    engine.initialize(state)
    repository = SaveRepository(tmp_path / "boundaries.db")
    stages = []

    repository.save(state)
    stages.append(repository.load().diligence_room.current_stage.value)
    engine.advance_request_list(state)
    repository.save(state)
    stages.append(repository.load().diligence_room.current_stage.value)
    for scene_id in DILIGENCE_DAY_SCENES[1]:
        _choose_diligence(state, content, engine, "full_consistent", scene_id)
    engine.prepare_initial_packages(state)
    repository.save(state)
    stages.append(repository.load().diligence_room.current_stage.value)
    for scene_id in DILIGENCE_DAY_SCENES[2]:
        _choose_diligence(state, content, engine, "full_consistent", scene_id)
    engine.prepare_risk_schedule(state)
    repository.save(state)
    stages.append(repository.load().diligence_room.current_stage.value)
    for scene_id in DILIGENCE_DAY_SCENES[3]:
        _choose_diligence(state, content, engine, "full_consistent", scene_id)
    engine.prepare_q_and_a(state)
    repository.save(state)
    stages.append(repository.load().diligence_room.current_stage.value)
    _choose_diligence(
        state,
        content,
        engine,
        "full_consistent",
        "dr_inconsistency_action",
    )
    engine.prepare_supplement(state)
    repository.save(state)
    stages.append(repository.load().diligence_room.current_stage.value)

    assert stages == [
        "request_list",
        "initial_package",
        "risk_schedule",
        "q_and_a",
        "supplemental",
        "before_committee",
    ]
    assert all(entry.total_debits == entry.total_credits for entry in state.ledger.entries)
