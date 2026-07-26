"""Serializable commodity, futures-position, settlement, and margin models."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MONEY_QUANTUM = Decimal("0.01")
PRICE_QUANTUM = Decimal("0.001")
QUANTITY_QUANTUM = Decimal("0.001")


def money(value: Decimal) -> Decimal:
    """Round monetary results to cents using an explicit commercial convention."""
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def price(value: Decimal) -> Decimal:
    return value.quantize(PRICE_QUANTUM, rounding=ROUND_HALF_UP)


class PositionSide(StrEnum):
    LONG = "long"
    SHORT = "short"


class PhysicalDirection(StrEnum):
    LONG = "long"


class HedgeOutcome(StrEnum):
    UNHEDGED_WINTER = "unhedged_winter"
    INTENDED_HEDGE = "intended_hedge"
    MARGIN_PRESSURE = "margin_pressure"
    OVERHEDGE = "overhedge"
    DE_HEDGED = "de_hedged"
    LIQUIDITY_FAILURE = "liquidity_failure"


class DocumentationQuality(StrEnum):
    NOT_PREPARED = "not_prepared"
    ACCURATE = "accurate"
    VAGUE = "vague"
    ESCALATED = "escalated"


class FuturesContractSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z0-9_]+$")
    product_code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    exchange: str = Field(min_length=1)
    contract_size_mmbtu: Decimal = Field(gt=0)
    minimum_tick: Decimal = Field(gt=0)
    settlement_type: Literal["physical", "financial"]
    specification_source_name: str
    specification_source_url: str


class DailyMarketPrice(BaseModel):
    model_config = ConfigDict(frozen=True)

    settlement_date: date
    henry_hub_price: Decimal = Field(gt=0)
    chicago_basis: Decimal
    event_title: str = Field(min_length=1)
    event_text: str = Field(min_length=1)
    communication_from: str | None = None
    communication_subject: str | None = None

    @property
    def regional_price(self) -> Decimal:
        return price(self.henry_hub_price + self.chicago_basis)


class MarketPricePath(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z0-9_]+$")
    label: str
    fictional: Literal[True]
    initial_market: DailyMarketPrice
    settlements: list[DailyMarketPrice] = Field(min_length=5)

    @model_validator(mode="after")
    def validate_dates(self) -> MarketPricePath:
        dates = [item.settlement_date for item in self.settlements]
        if len(dates) != len(set(dates)):
            raise ValueError("price path contains duplicate settlement dates")
        if dates != sorted(dates):
            raise ValueError("settlement dates must be in ascending order")
        if self.initial_market.settlement_date >= dates[0]:
            raise ValueError("initial market date must precede every settlement date")
        return self


class PhysicalExposure(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z0-9_]+$")
    quantity_mmbtu: Decimal = Field(gt=0)
    direction: PhysicalDirection = PhysicalDirection.LONG
    regional_hub: str
    settlement_date: date
    original_henry_hub_price: Decimal = Field(gt=0)
    original_basis: Decimal

    @property
    def original_regional_price(self) -> Decimal:
        return price(self.original_henry_hub_price + self.original_basis)


class HedgeTicket(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z0-9_]+$")
    hedge_level_id: str
    contract_id: str
    contract_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    side: PositionSide
    contracts: int = Field(ge=0)
    hedge_ratio: Decimal = Field(ge=0)
    entry_price: Decimal = Field(gt=0)
    initial_margin_required: Decimal = Field(ge=0)
    physical_quantity_mmbtu: Decimal = Field(gt=0)
    hedged_quantity_mmbtu: Decimal = Field(ge=0)
    speculative_quantity_mmbtu: Decimal = Field(ge=0)

    @property
    def is_overhedged(self) -> bool:
        return self.hedge_ratio > Decimal("1")


class HedgeTicketPreview(BaseModel):
    hedge_level_id: str
    label: str
    side: PositionSide
    contracts: int = Field(ge=0)
    hedge_ratio: Decimal = Field(ge=0)
    hedged_quantity_mmbtu: Decimal = Field(ge=0)
    speculative_quantity_mmbtu: Decimal = Field(ge=0)
    initial_margin_required: Decimal = Field(ge=0)
    operating_cash_remaining: Decimal
    liquidity_headroom_remaining: Decimal
    risk_reduced: str
    risk_remaining: str
    overhedge_warning: str | None = None


class FuturesPosition(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    contract_id: str
    contract_month: str
    side: PositionSide
    contracts: int = Field(ge=0)
    contract_size_mmbtu: Decimal = Field(gt=0)
    entry_price: Decimal = Field(gt=0)
    current_price: Decimal = Field(gt=0)
    daily_pnl: Decimal = Decimal("0")
    cumulative_pnl: Decimal = Decimal("0")
    closed: bool = False

    @property
    def quantity_mmbtu(self) -> Decimal:
        return self.contract_size_mmbtu * self.contracts


class MarginCall(BaseModel):
    call_id: str = Field(pattern=r"^[a-z0-9_]+$")
    call_date: date
    required_amount: Decimal = Field(ge=0)
    funded_amount: Decimal = Field(ge=0)
    shortfall: Decimal = Field(ge=0)
    met: bool


class PositionReductionTrade(BaseModel):
    trade_id: str = Field(pattern=r"^[a-z0-9_]+$")
    trade_date: date
    contracts_closed: int = Field(gt=0)
    contracts_remaining: int = Field(ge=0)
    previous_hedge_ratio: Decimal = Field(ge=0)
    new_hedge_ratio: Decimal = Field(ge=0)
    cumulative_futures_pnl_preserved: Decimal
    margin_released: Decimal = Field(ge=0)
    revised_margin_call: Decimal = Field(ge=0)


class MarginAccount(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    balance: Decimal = Field(ge=0)
    initial_requirement: Decimal = Field(ge=0)
    maintenance_requirement: Decimal = Field(ge=0)
    total_initial_deposit: Decimal = Field(ge=0)
    total_variation_margin: Decimal = Decimal("0")
    total_additional_deposits: Decimal = Field(default=Decimal("0"), ge=0)
    total_released: Decimal = Field(default=Decimal("0"), ge=0)
    calls: list[MarginCall] = Field(default_factory=list)

    @model_validator(mode="after")
    def maintenance_not_above_initial(self) -> MarginAccount:
        if self.maintenance_requirement > self.initial_requirement:
            raise ValueError("maintenance margin cannot exceed initial margin")
        return self


class DailySettlementResult(BaseModel):
    day_number: int = Field(ge=1)
    settlement_date: date
    event_title: str
    event_text: str
    communication_from: str | None = None
    communication_subject: str | None = None
    previous_henry_hub_price: Decimal = Field(gt=0)
    henry_hub_price: Decimal = Field(gt=0)
    chicago_basis: Decimal
    chicago_price: Decimal = Field(gt=0)
    daily_futures_pnl: Decimal
    cumulative_futures_pnl: Decimal
    henry_hub_physical_component: Decimal
    basis_component: Decimal
    physical_economic_pnl: Decimal
    net_economic_pnl: Decimal
    margin_balance_before: Decimal = Field(ge=0)
    margin_balance_after_settlement: Decimal = Field(ge=0)
    margin_call_amount: Decimal = Field(ge=0)
    margin_funded: Decimal = Field(ge=0)
    margin_balance_end: Decimal = Field(ge=0)
    operating_cash_end: Decimal = Field(ge=0)
    liquidity_headroom: Decimal


class HedgeBookState(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    scenario_id: str
    seed: int = Field(ge=0)
    price_path: MarketPricePath
    contract: FuturesContractSpec
    ticket: HedgeTicket
    physical: PhysicalExposure
    position: FuturesPosition | None
    initial_margin_per_contract: Decimal = Field(gt=0)
    maintenance_margin_per_contract: Decimal = Field(gt=0)
    minimum_operating_reserve: Decimal = Field(ge=0)
    margin: MarginAccount
    beginning_operating_cash: Decimal = Field(ge=0)
    next_settlement_index: int = Field(default=0, ge=0)
    settlements: list[DailySettlementResult] = Field(default_factory=list)
    pending_margin_call_id: str | None = None
    position_reductions: list[PositionReductionTrade] = Field(default_factory=list)
    journal_transaction_ids: list[str] = Field(default_factory=list)
    documentation_quality: DocumentationQuality = DocumentationQuality.NOT_PREPARED
    learning_objectives: list[str] = Field(default_factory=list)
    liquidity_crisis: bool = False
    position_closed: bool = False
    outcome: HedgeOutcome | None = None
    completed: bool = False

    @model_validator(mode="after")
    def validate_progress(self) -> HedgeBookState:
        if self.next_settlement_index > len(self.price_path.settlements):
            raise ValueError("settlement progress exceeds configured price path")
        if self.maintenance_margin_per_contract >= self.initial_margin_per_contract:
            raise ValueError("maintenance margin must be below initial margin")
        return self
