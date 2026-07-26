import shutil
from decimal import Decimal

import pytest
import yaml
from pydantic import ValidationError

from lake_effect_ledger.narrative.models import ContentBundle


def test_treasury_content_exposes_required_operational_terms(content) -> None:
    scenario = content.treasury_scenario("episode_01_two_oclock_call")

    assert scenario.facility.commitment == 500000
    assert scenario.facility.beginning_outstanding == 0
    assert scenario.facility.annual_interest_rate == Decimal("0.085")
    assert scenario.facility.covenant_minimum_available_liquidity == 3600000
    assert sum(item.amount for item in scenario.obligations) == 750000
    assert len(scenario.notification_options) == 4


@pytest.mark.parametrize(
    "case",
    [
        "outstanding_over_commitment",
        "default_draw_over_capacity",
        "invalid_draw_increment",
        "naive_deadline",
        "missing_notification_option",
        "duplicate_obligation",
        "unknown_journal_pattern",
        "unknown_recipient",
        "negative_obligation",
        "invalid_interest_rate",
    ],
)
def test_invalid_treasury_content_is_rejected(
    content_root,
    tmp_path,
    case: str,
) -> None:
    root = tmp_path / "content"
    shutil.copytree(content_root, root)
    treasury_path = root / "treasury" / "episode_01.yaml"
    document = yaml.safe_load(treasury_path.read_text(encoding="utf-8"))
    scenario = document["scenarios"][0]
    facility = scenario["facility"]

    if case == "outstanding_over_commitment":
        facility["beginning_outstanding"] = 600000
    elif case == "default_draw_over_capacity":
        facility["default_draw_amount"] = 550000
    elif case == "invalid_draw_increment":
        facility["default_draw_amount"] = 425000
    elif case == "naive_deadline":
        scenario["margin_deadline"] = "2028-01-19T14:00:00"
    elif case == "missing_notification_option":
        scenario["notification_options"].pop()
    elif case == "duplicate_obligation":
        scenario["obligations"].append(dict(scenario["obligations"][0]))
    elif case == "unknown_journal_pattern":
        scenario["journal_patterns"]["revolver_draw"] = "missing_pattern"
    elif case == "unknown_recipient":
        scenario["notification_options"][0]["recipient_ids"][0] = "nobody_here"
    elif case == "negative_obligation":
        scenario["obligations"][0]["amount"] = -1
    elif case == "invalid_interest_rate":
        facility["annual_interest_rate"] = 1.5
    else:  # pragma: no cover
        raise AssertionError(case)

    treasury_path.write_text(
        yaml.safe_dump(document, sort_keys=False),
        encoding="utf-8",
    )
    with pytest.raises((ValidationError, ValueError)):
        ContentBundle.load(root)
