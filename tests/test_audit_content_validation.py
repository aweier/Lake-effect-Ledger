import pytest
from pydantic import ValidationError

from lake_effect_ledger.audit.models import (
    AuditScenario,
    Finding,
    ManagementResponse,
    RemediationRecommendation,
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
        "sources": content.sources,
        "glossary": content.glossary,
        "prologue": content.prologue,
        "first_rotation": content.first_rotation,
        "eleventh_scenario": content.eleventh_scenario,
        "eleventh_learning": content.eleventh_learning,
        "eleventh_narrative": content.eleventh_narrative,
        "audit_scenario": content.audit_scenario,
        "audit_learning": content.audit_learning,
    }
    values.update(changes)
    return ContentBundle(**values)


def test_audit_content_has_four_days_twelve_decisions_and_six_checks(content) -> None:
    scenario = content.audit_scenario

    assert scenario.estimated_minutes == 44
    assert len(scenario.scenes) == 12
    assert {item.day for item in scenario.scenes} == {1, 2, 3, 4}
    assert len(content.audit_learning.checks) == 6
    assert all(item.retry_policy.value == "until_correct" for item in content.audit_learning.checks)


def test_unknown_requested_record_is_rejected_cross_file(content) -> None:
    bad = content.audit_scenario.model_copy(deep=True)
    bad.request_specs[0].stable_record_id = "not_a_real_record"

    with pytest.raises(ValueError, match="nonexistent"):
        _rebundle(content, audit_scenario=bad)


def test_duplicate_request_and_unreachable_outcome_are_rejected(content) -> None:
    payload = content.audit_scenario.model_dump(mode="json")
    payload["request_specs"][1]["request_item_id"] = payload["request_specs"][0]["request_item_id"]
    with pytest.raises(ValidationError, match="duplicate audit request"):
        AuditScenario.model_validate(payload)

    payload = content.audit_scenario.model_dump(mode="json")
    payload["possible_outcomes"][-1] = payload["possible_outcomes"][0]
    with pytest.raises(ValidationError, match="all No Surprises outcomes"):
        AuditScenario.model_validate(payload)


def test_procedure_without_known_control_is_rejected(content) -> None:
    payload = content.audit_scenario.model_dump(mode="json")
    payload["test_procedures"][0]["control_objective_id"] = "unknown_control"

    with pytest.raises(ValidationError, match="every control objective"):
        AuditScenario.model_validate(payload)


def test_finding_requires_exception_or_documented_rationale() -> None:
    with pytest.raises(ValidationError, match="finding requires"):
        Finding.model_validate(
            {
                "finding_id": "finding_test",
                "title": "Unsupported finding",
                "severity": "moderate",
                "evidence_record_ids": ["record_1"],
                "rationale": "No exception supplied.",
            }
        )


def test_management_disagreement_requires_evidence_and_remediation_requires_owner_date() -> None:
    with pytest.raises(ValidationError, match="disagreement requires"):
        ManagementResponse.model_validate(
            {
                "response_id": "response_test",
                "finding_id": "finding_test",
                "agreement": "disagree",
                "root_cause": "manual_process_error",
                "proposed_action": "Review the control.",
                "owner": {
                    "owner_id": "owner_test",
                    "person_id": "evelyn_marsh",
                    "role": "Controller",
                },
                "target_date": "2028-04-01",
                "interim_control": "Daily review.",
                "residual_risk": "Manual timing.",
                "status": "open",
            }
        )
    with pytest.raises(ValidationError):
        RemediationRecommendation.model_validate(
            {
                "remediation_id": "remediation_test",
                "finding_ids": ["finding_test"],
                "kind": "daily_supervisory_review",
                "proposed_action": "Review daily.",
                "interim_control": "Controller review.",
                "residual_risk": "Manual timing.",
                "approved": True,
            }
        )
