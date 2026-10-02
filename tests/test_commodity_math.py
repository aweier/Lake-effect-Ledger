from decimal import Decimal

import pytest

from lake_effect_ledger.commodity.engine import (
    contract_month_spread,
    delivery_contract_value,
    futures_daily_pnl,
    hedge_ratio,
    margin_call_amount,
    physical_pnl_components,
    regional_price,
)
from lake_effect_ledger.commodity.models import (
    DailyMarketPrice,
    PhysicalDirection,
    PhysicalExposure,
    PositionSide,
)


def test_regional_price_is_henry_hub_plus_basis() -> None:
    assert regional_price(Decimal("5.80"), Decimal("-0.30")) == Decimal("5.500")


def test_long_futures_daily_pnl() -> None:
    result = futures_daily_pnl(
        side=PositionSide.LONG,
        previous_settlement=Decimal("5.80"),
        current_settlement=Decimal("6.10"),
        contract_size_mmbtu=Decimal("10000"),
        contracts=3,
    )
    assert result == Decimal("9000.00")


def test_short_futures_daily_pnl() -> None:
    result = futures_daily_pnl(
        side=PositionSide.SHORT,
        previous_settlement=Decimal("5.80"),
        current_settlement=Decimal("6.10"),
        contract_size_mmbtu=Decimal("10000"),
        contracts=3,
    )
    assert result == Decimal("-9000.00")


def test_decimal_rounding_is_explicit_and_exact() -> None:
    result = futures_daily_pnl(
        side=PositionSide.LONG,
        previous_settlement=Decimal("1.0000"),
        current_settlement=Decimal("1.0050"),
        contract_size_mmbtu=Decimal("1"),
        contracts=1,
    )
    assert result == Decimal("0.01")
    assert isinstance(result, Decimal)


def test_contract_month_spread_preserves_direction() -> None:
    assert contract_month_spread(
        nearby_price=Decimal("5.120"), deferred_price=Decimal("5.280")
    ) == Decimal("0.160")
    assert contract_month_spread(
        nearby_price=Decimal("5.460"), deferred_price=Decimal("5.310")
    ) == Decimal("-0.150")


def test_delivery_contract_value_uses_settlement_quantity_and_contracts() -> None:
    assert delivery_contract_value(
        settlement_price=Decimal("4.875"),
        contract_size_mmbtu=Decimal("10000"),
        contracts=3,
    ) == Decimal("146250.00")


@pytest.mark.parametrize(
    ("contracts", "expected"),
    [(0, "0.0000"), (5, "0.5000"), (10, "1.0000"), (15, "1.5000")],
)
def test_hedge_ratio_calculation(contracts: int, expected: str) -> None:
    assert hedge_ratio(
        contracts=contracts,
        contract_size_mmbtu=Decimal("10000"),
        physical_quantity_mmbtu=Decimal("100000"),
    ) == Decimal(expected)


@pytest.mark.parametrize(
    ("balance", "expected"),
    [("120000", "0"), ("109999.99", "40000.01"), ("75000", "75000.00")],
)
def test_margin_call_restores_initial_after_breach(
    balance: str,
    expected: str,
) -> None:
    assert margin_call_amount(
        balance=Decimal(balance),
        initial_requirement=Decimal("150000"),
        maintenance_requirement=Decimal("110000"),
    ) == Decimal(expected)


def test_basis_risk_decomposition_reconciles_physical_pnl() -> None:
    exposure = PhysicalExposure(
        id="test_sale",
        quantity_mmbtu=Decimal("100000"),
        direction=PhysicalDirection.LONG,
        regional_hub="Chicago",
        settlement_date="2028-01-22",
        original_henry_hub_price=Decimal("5.80"),
        original_basis=Decimal("-0.30"),
    )
    market = DailyMarketPrice(
        settlement_date="2028-01-22",
        henry_hub_price=Decimal("4.80"),
        chicago_basis=Decimal("-0.70"),
        event_title="Test",
        event_text="Test",
    )

    henry, basis, physical = physical_pnl_components(exposure, market)

    assert henry == Decimal("-100000.00")
    assert basis == Decimal("-40000.00")
    assert physical == Decimal("-140000.00")
    assert henry + basis == physical


def test_economically_short_buyer_reverses_physical_price_signs() -> None:
    exposure = PhysicalExposure(
        id="test_purchase",
        quantity_mmbtu=Decimal("80000"),
        direction=PhysicalDirection.SHORT,
        regional_hub="Chicago",
        settlement_date="2028-01-31",
        original_henry_hub_price=Decimal("5.40"),
        original_basis=Decimal("-0.20"),
    )
    market = DailyMarketPrice(
        settlement_date="2028-01-31",
        henry_hub_price=Decimal("4.95"),
        chicago_basis=Decimal("-0.30"),
        event_title="Test",
        event_text="Test",
    )

    henry, basis, physical = physical_pnl_components(exposure, market)

    assert henry == Decimal("36000.00")
    assert basis == Decimal("8000.00")
    assert physical == Decimal("44000.00")
