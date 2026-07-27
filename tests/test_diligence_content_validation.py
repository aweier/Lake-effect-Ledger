from copy import deepcopy

import pytest
from pydantic import ValidationError

from lake_effect_ledger.diligence.models import (
    DiligenceLearningFile,
    DiligenceScenario,
    DisclosurePackage,
    PackageVersion,
    ScenarioSensitivity,
)
from lake_effect_ledger.narrative.models import ContentBundle


def _rebundle(content, **changes):
    values = {
        "characters": content.characters,
        "scenes": content.scenes,
        "chart": content.chart,
        "journals": content.journals,
        "events": content.events,
        "lessons": content.lessons,
        "markets": content.markets,
        "commodity_contracts": content.commodity_contracts,
        "commodity_price_paths": content.commodity_price_paths,
        "hedge_scenarios": content.hedge_scenarios,
        "hedge_narrative": content.hedge_narrative,
        "treasury_scenarios": content.treasury_scenarios,
        "game_modes": content.game_modes,
        "curriculum": content.curriculum,
        "sources": content.sources,
        "glossary": content.glossary,
        "prologue": content.prologue,
        "first_rotation": content.first_rotation,
        "eleventh_scenario": content.eleventh_scenario,
        "eleventh_learning": content.eleventh_learning,
        "eleventh_narrative": content.eleventh_narrative,
        "audit_scenario": content.audit_scenario,
        "audit_learning": content.audit_learning,
        "diligence_scenario": content.diligence_scenario,
        "diligence_learning": content.diligence_learning,
    }
    values.update(changes)
    return ContentBundle(**values)


def test_diligence_content_has_four_days_twelve_decisions_and_six_checks(content) -> None:
    scenario = content.diligence_scenario

    assert scenario.estimated_minutes == 48
    assert "majority acquisition" in scenario.transaction_structure.lower()
    assert len(scenario.scenes) == 12
    assert {item.day for item in scenario.scenes} == {1, 2, 3, 4}
    assert len(scenario.request_specs) == 14
    assert len(scenario.sensitivities) == 3
    assert len(content.diligence_learning.checks) == 6
    assert (
        max(len(check_ids) for check_ids in content.diligence_learning.day_check_ids.values()) <= 2
    )
    assert all(
        item.retry_policy.value == "until_correct" for item in content.diligence_learning.checks
    )
    committee = next(item for item in scenario.scenes if item.id == "dr_committee_position")
    assert "junior analyst" in committee.text
    assert "Vince" in committee.text


def test_unknown_diligence_source_record_is_rejected_cross_file(content) -> None:
    bad = content.diligence_scenario.model_copy(deep=True)
    bad.request_specs[0].source_record_ids = ["not_a_real_record"]

    with pytest.raises(ValueError, match="nonexistent source"):
        _rebundle(content, diligence_scenario=bad)


def test_unknown_diligence_lesson_and_person_are_rejected(content) -> None:
    bad_lesson = content.diligence_scenario.model_copy(deep=True)
    bad_lesson.scenes[0].choices[0].learning_objective_ids = ["unknown_lesson"]
    with pytest.raises(ValueError, match="unknown lessons"):
        _rebundle(content, diligence_scenario=bad_lesson)

    bad_person = content.diligence_scenario.model_copy(deep=True)
    bad_person.scenes[0].choices[0].effect.relationship_deltas = {"unknown_person": 1}
    with pytest.raises(ValueError, match="unknown people"):
        _rebundle(content, diligence_scenario=bad_person)


def test_duplicate_choice_unordered_days_and_missing_outcome_are_rejected(content) -> None:
    payload = content.diligence_scenario.model_dump(mode="json")
    payload["scenes"][1]["choices"][0]["id"] = payload["scenes"][0]["choices"][0]["id"]
    with pytest.raises(ValidationError, match="duplicate diligence choice"):
        DiligenceScenario.model_validate(payload)

    payload = content.diligence_scenario.model_dump(mode="json")
    payload["day_dates"]["day_2"] = payload["day_dates"]["day_1"]
    with pytest.raises(ValidationError, match="unique and ordered"):
        DiligenceScenario.model_validate(payload)

    payload = content.diligence_scenario.model_dump(mode="json")
    payload["possible_outcomes"].pop()
    with pytest.raises(ValidationError, match="all Diligence Room outcomes"):
        DiligenceScenario.model_validate(payload)


def test_each_diligence_check_must_have_one_day(content) -> None:
    payload = content.diligence_learning.model_dump(mode="json")
    payload["day_check_ids"]["day_4"].append(payload["day_check_ids"]["day_1"][0])

    with pytest.raises(ValidationError, match="exactly one day"):
        DiligenceLearningFile.model_validate(payload)


def test_sensitivity_rejects_non_reconciling_net() -> None:
    with pytest.raises(ValidationError, match="net economic effect"):
        ScenarioSensitivity.model_validate(
            {
                "scenario_id": "bad_math",
                "label": "Bad math",
                "henry_hub_change": "0.10",
                "chicago_basis_change": "-0.05",
                "physical_economic_effect": "100",
                "futures_effect": "-80",
                "basis_effect": "-50",
                "net_economic_effect": "30",
                "estimated_variation_margin_cash_movement": "-80",
                "resulting_liquidity_headroom": "1000",
            }
        )


def _package_version_payload(*, version=1, supersedes=None, change_kind="initial"):
    return {
        "package_id": "package_test",
        "version": version,
        "intended_stakeholder_id": "sofia_marin",
        "included_item_ids": ["req_audit_report"],
        "omitted_requested_item_ids": [],
        "source_record_ids": ["internal_audit_walkthrough_no_surprises"],
        "fact_values": {"audit_outcome": "no_surprises"},
        "created_at": "2028-02-14T09:00:00-06:00",
        "delivered_at": "2028-02-14T09:05:00-06:00",
        "prepared_by_id": "player",
        "reviewed_by_ids": ["evelyn_marsh"],
        "supersedes_version": supersedes,
        "change_kind": change_kind,
    }


def test_package_versions_are_frozen_and_append_only() -> None:
    original = PackageVersion.model_validate(_package_version_payload())
    with pytest.raises(ValidationError, match="frozen"):
        original.change_note = "overwrite the delivered record"
    with pytest.raises(TypeError, match="immutable"):
        original.fact_values["audit_outcome"] = "rewritten"
    with pytest.raises(AttributeError):
        original.included_item_ids.append("req_rewritten")

    second = _package_version_payload(
        version=2,
        supersedes=1,
        change_kind="supplement",
    )
    duplicate = deepcopy(_package_version_payload())
    with pytest.raises(ValidationError, match="complete, ordered, and unique"):
        DisclosurePackage.model_validate(
            {
                "package_id": "package_test",
                "request_id": "request_test",
                "intended_stakeholder_id": "sofia_marin",
                "versions": [_package_version_payload(), duplicate],
            }
        )

    second["supersedes_version"] = 99
    with pytest.raises(ValidationError, match="supersede"):
        DisclosurePackage.model_validate(
            {
                "package_id": "package_test",
                "request_id": "request_test",
                "intended_stakeholder_id": "sofia_marin",
                "versions": [_package_version_payload(), second],
            }
        )


def test_package_rejects_delivery_before_creation_and_item_overlap() -> None:
    payload = _package_version_payload()
    payload["delivered_at"] = "2028-02-14T08:59:00-06:00"
    with pytest.raises(ValidationError, match="before it is created"):
        PackageVersion.model_validate(payload)

    payload = _package_version_payload()
    payload["omitted_requested_item_ids"] = ["req_audit_report"]
    with pytest.raises(ValidationError, match="both included and omitted"):
        PackageVersion.model_validate(payload)
