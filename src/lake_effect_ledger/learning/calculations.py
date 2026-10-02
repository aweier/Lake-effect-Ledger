"""Knowledge-check calculations routed through the commodity domain functions."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from lake_effect_ledger.commodity.engine import (
    buyer_physical_purchase_cost_variance,
    combined_economic_result,
    contract_count,
    contract_month_spread,
    delivery_contract_value,
    futures_daily_pnl,
    futures_tick_value,
    hedge_ratio,
    margin_call_amount,
    regional_price,
)
from lake_effect_ledger.learning.models import (
    CalculationKind,
    KnowledgeCheckDefinition,
)
from lake_effect_ledger.narrative.models import ContentBundle


def calculate_answer(check: KnowledgeCheckDefinition, content: ContentBundle) -> Decimal:
    calculation = check.calculation
    if calculation is None:
        raise ValueError(f"knowledge check {check.id} is not numeric")
    contract = (
        content.commodity_contract(calculation.contract_id)
        if calculation.contract_id is not None
        else None
    )
    if calculation.kind == CalculationKind.FUTURES_PNL:
        if contract is None:
            raise ValueError("futures P&L calculation requires a contract")
        return futures_daily_pnl(
            side=calculation.side,
            previous_settlement=calculation.previous_price,
            current_settlement=calculation.current_price,
            contract_size_mmbtu=contract.contract_size_mmbtu,
            contracts=calculation.contracts,
        )
    if calculation.kind == CalculationKind.TICK_VALUE:
        if contract is None:
            raise ValueError("tick-value calculation requires a contract")
        return futures_tick_value(
            minimum_tick=contract.minimum_tick,
            contract_size_mmbtu=contract.contract_size_mmbtu,
        )
    if calculation.kind == CalculationKind.REGIONAL_PRICE:
        return regional_price(calculation.henry_hub_price, calculation.regional_basis)
    if calculation.kind == CalculationKind.HEDGE_RATIO:
        if contract is None:
            raise ValueError("hedge-ratio calculation requires a contract")
        return hedge_ratio(
            contracts=calculation.contracts,
            contract_size_mmbtu=contract.contract_size_mmbtu,
            physical_quantity_mmbtu=calculation.physical_quantity_mmbtu,
        )
    if calculation.kind == CalculationKind.MARGIN_CALL:
        return margin_call_amount(
            balance=calculation.margin_balance,
            initial_requirement=calculation.initial_requirement,
            maintenance_requirement=calculation.maintenance_requirement,
        )
    if calculation.kind == CalculationKind.CONTRACT_COUNT:
        if contract is None:
            raise ValueError("contract-count calculation requires a contract")
        return contract_count(
            physical_quantity_mmbtu=calculation.physical_quantity_mmbtu,
            contract_size_mmbtu=contract.contract_size_mmbtu,
        )
    if calculation.kind == CalculationKind.BUYER_PHYSICAL_VARIANCE:
        return buyer_physical_purchase_cost_variance(
            initial_regional_price=calculation.initial_regional_price,
            final_regional_price=calculation.final_regional_price,
            physical_quantity_mmbtu=calculation.physical_quantity_mmbtu,
        )
    if calculation.kind == CalculationKind.COMBINED_ECONOMIC_RESULT:
        return combined_economic_result(
            physical_variance=calculation.physical_variance,
            futures_result=calculation.futures_result,
        )
    if calculation.kind == CalculationKind.CONTRACT_MONTH_SPREAD:
        return contract_month_spread(
            nearby_price=calculation.nearby_price,
            deferred_price=calculation.deferred_price,
        )
    if calculation.kind == CalculationKind.DELIVERY_CONTRACT_VALUE:
        if contract is None:
            raise ValueError("delivery contract value requires a contract")
        return delivery_contract_value(
            settlement_price=calculation.settlement_price,
            contract_size_mmbtu=contract.contract_size_mmbtu,
            contracts=calculation.contracts,
        )
    raise ValueError(f"unsupported calculation kind: {calculation.kind}")


def parse_numeric_answer(raw_answer: str) -> Decimal:
    cleaned = (
        raw_answer.strip().replace("$", "").replace(",", "").replace("−", "-").replace(" ", "")
    )
    percent = cleaned.endswith("%")
    if percent:
        cleaned = cleaned[:-1]
    try:
        parsed = Decimal(cleaned)
    except InvalidOperation as error:
        raise ValueError("enter a number, optionally using $, commas, or %") from error
    return parsed / Decimal("100") if percent else parsed


def numeric_answer_matches(
    raw_answer: str,
    *,
    expected: Decimal,
    quantum: Decimal,
    tolerance: Decimal,
) -> bool:
    actual = parse_numeric_answer(raw_answer).quantize(quantum, rounding=ROUND_HALF_UP)
    rounded_expected = expected.quantize(quantum, rounding=ROUND_HALF_UP)
    return abs(actual - rounded_expected) <= tolerance
