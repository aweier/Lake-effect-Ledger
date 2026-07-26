import shutil
from decimal import Decimal

import pytest
import yaml
from pydantic import ValidationError

from lake_effect_ledger.narrative.models import ContentBundle


def test_commodity_content_has_required_scenario_properties(content) -> None:
    scenario = content.hedge_scenario("episode_01_hedge_book")
    contract = content.commodity_contract(scenario.contract_id)
    path = content.commodity_price_path(scenario.price_path_id)

    assert contract.contract_size_mmbtu == Decimal("10000")
    assert contract.minimum_tick == Decimal("0.001")
    assert scenario.physical_quantity_mmbtu == Decimal("100000")
    assert len(path.settlements) == 5
    assert any(item.communication_from for item in path.settlements)
    assert any(
        (current.henry_hub_price - previous.henry_hub_price)
        * (current.chicago_basis - previous.chicago_basis)
        < 0
        for previous, current in zip(
            [path.initial_market, *path.settlements[:-1]],
            path.settlements,
            strict=True,
        )
    )


@pytest.mark.parametrize(
    "case",
    [
        "unknown_contract",
        "unknown_price_path",
        "unknown_journal_pattern",
        "mismatched_scenario_date",
        "missing_settlement_price",
        "duplicate_settlement_date",
        "negative_contract_size",
        "invalid_margin_relationship",
        "impossible_hedge_choice",
        "invalid_position_side",
        "unknown_commodity_field",
        "missing_learning_objective",
    ],
)
def test_invalid_commodity_content_is_rejected(
    content_root,
    tmp_path,
    case: str,
) -> None:
    root = tmp_path / "content"
    shutil.copytree(content_root, root)
    scenario_path = root / "commodity" / "hedge_scenarios.yaml"
    contracts_path = root / "commodity" / "contracts.yaml"
    prices_path = root / "commodity" / "price_paths.yaml"
    narrative_path = root / "chapters" / "hedge_book.yaml"

    scenario_doc = _read_yaml(scenario_path)
    contract_doc = _read_yaml(contracts_path)
    price_doc = _read_yaml(prices_path)
    narrative_doc = _read_yaml(narrative_path)
    scenario = scenario_doc["scenarios"][0]

    if case == "unknown_contract":
        scenario["contract_id"] = "missing_contract"
        _write_yaml(scenario_path, scenario_doc)
    elif case == "unknown_price_path":
        scenario["price_path_id"] = "missing_path"
        _write_yaml(scenario_path, scenario_doc)
    elif case == "unknown_journal_pattern":
        scenario["journal_patterns"]["futures_gain"] = "missing_pattern"
        _write_yaml(scenario_path, scenario_doc)
    elif case == "mismatched_scenario_date":
        scenario["trade_date"] = "2028-01-16"
        _write_yaml(scenario_path, scenario_doc)
    elif case == "missing_settlement_price":
        price_doc["price_paths"][0]["settlements"][1].pop("henry_hub_price")
        _write_yaml(prices_path, price_doc)
    elif case == "duplicate_settlement_date":
        settlements = price_doc["price_paths"][0]["settlements"]
        settlements[1]["settlement_date"] = settlements[0]["settlement_date"]
        _write_yaml(prices_path, price_doc)
    elif case == "negative_contract_size":
        contract_doc["contracts"][0]["contract_size_mmbtu"] = -10000
        _write_yaml(contracts_path, contract_doc)
    elif case == "invalid_margin_relationship":
        scenario["maintenance_margin_per_contract"] = scenario["initial_margin_per_contract"]
        _write_yaml(scenario_path, scenario_doc)
    elif case == "impossible_hedge_choice":
        scenario["hedge_levels"][1]["hedge_ratio"] = 0.75
        _write_yaml(scenario_path, scenario_doc)
    elif case == "invalid_position_side":
        scenario["futures_side"] = "flat"
        _write_yaml(scenario_path, scenario_doc)
    elif case == "unknown_commodity_field":
        effects = narrative_doc["documentation_scene"]["choices"][0]["effects"]
        effects[0]["target"] = "nonexistent_field"
        _write_yaml(narrative_path, narrative_doc)
    elif case == "missing_learning_objective":
        scenario["learning_objectives"].append("missing_lesson")
        _write_yaml(scenario_path, scenario_doc)
    else:  # pragma: no cover
        raise AssertionError(f"unhandled test case {case}")

    with pytest.raises((ValidationError, ValueError)):
        ContentBundle.load(root)


def _read_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path, document) -> None:
    path.write_text(
        yaml.safe_dump(document, sort_keys=False),
        encoding="utf-8",
    )
