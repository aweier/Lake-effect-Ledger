"""Serializable orders, authorizations, confirmations, blotters, and chapter state."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lake_effect_ledger.commodity.models import MarginAccount, PositionSide
from lake_effect_ledger.learning.models import KnowledgeCheckDefinition


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    TRIGGERED = "triggered"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class AuthorizationStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class ReconciliationStatus(StrEnum):
    PENDING = "pending"
    MATCHED = "matched"
    QUANTITY_EXCEPTION = "quantity_exception"
    PRICE_EXCEPTION = "price_exception"
    MISSING_AUTHORIZATION = "missing_authorization"
    AWAITING_PHYSICAL_SUPPORT = "awaiting_physical_support"
    ESCALATED = "escalated"
    CORRECTED = "corrected"
    UNRESOLVED = "unresolved"
    CERTIFIED_WITH_EXCEPTION = "certified_with_exception"


class PhysicalVolumeOutcome(StrEnum):
    ARRIVES = "additional_volume_arrives"
    FAILS = "additional_volume_fails"


class EleventhOutcome(StrEnum):
    CLEAN_CORRECTION = "clean_correction"
    SUPPORTED_BUT_LATE = "supported_but_late"
    CALS_ANALYST = "cals_analyst"
    QUIET_FILE = "quiet_file"
    LUCKY_NOT_AUTHORIZED = "lucky_is_not_authorized"
    ELEVEN_AGAINST_TEN = "eleven_against_ten"


class VolumeTreatment(StrEnum):
    DISTINGUISH = "confirmed_and_possible_separate"
    PROBABLE = "probable_but_unconfirmed"
    CERTAIN = "treat_possible_as_committed"


class HedgeRecommendation(StrEnum):
    HOLD_TEN = "hold_ten"
    ADD_ONE = "recommend_eleventh"
    WAIT_FOR_SUPPORT = "wait_for_physical_support"


class RiskEmphasis(StrEnum):
    VOLUME = "volume_uncertainty"
    BASIS = "basis_risk"
    LIQUIDITY = "liquidity"
    AUTHORIZATION = "authorization_control"


class IntradayPricePoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    price: Decimal = Field(gt=0)

    @model_validator(mode="after")
    def require_aware_time(self) -> IntradayPricePoint:
        if not _is_aware(self.timestamp):
            raise ValueError("intraday timestamps must include a UTC offset")
        return self


class IntradayPricePath(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z0-9_]+$")
    label: str = Field(min_length=1)
    fictional: Literal[True]
    points: list[IntradayPricePoint] = Field(min_length=3)

    @model_validator(mode="after")
    def validate_points(self) -> IntradayPricePath:
        timestamps = [item.timestamp for item in self.points]
        if timestamps != sorted(timestamps) or len(timestamps) != len(set(timestamps)):
            raise ValueError("intraday prices require unique ascending timestamps")
        return self


class MarketBrief(BaseModel):
    brief_id: str = Field(pattern=r"^[a-z0-9_]+$")
    created_at: datetime
    author_id: str
    confirmed_volume_mmbtu: Decimal = Field(gt=0)
    possible_volume_mmbtu: Decimal = Field(ge=0)
    volume_treatment: VolumeTreatment
    hedge_recommendation: HedgeRecommendation
    risk_emphasis: RiskEmphasis
    asked_marisol: bool
    body_summary: str = Field(min_length=1)
    source_labels: list[str] = Field(min_length=1)
    communication_record_id: str

    @model_validator(mode="after")
    def validate_timestamp(self) -> MarketBrief:
        if not _is_aware(self.created_at):
            raise ValueError("market brief timestamp must include a UTC offset")
        return self


class PhysicalForecastRecord(BaseModel):
    forecast_id: str = Field(pattern=r"^[a-z0-9_]+$")
    supported_volume_mmbtu: Decimal = Field(gt=0)
    possible_additional_volume_mmbtu: Decimal = Field(ge=0)
    support_document_ids: list[str] = Field(default_factory=list)
    eventual_supported_volume_mmbtu: Decimal | None = Field(default=None, gt=0)
    support_obtained_at: datetime | None = None
    outcome_resolved_at: datetime | None = None
    outcome: PhysicalVolumeOutcome
    revealed: bool = False

    @model_validator(mode="after")
    def validate_support(self) -> PhysicalForecastRecord:
        if self.support_obtained_at is not None and not _is_aware(self.support_obtained_at):
            raise ValueError("physical support timestamp must include a UTC offset")
        if self.outcome_resolved_at is not None and not _is_aware(self.outcome_resolved_at):
            raise ValueError("physical outcome timestamp must include a UTC offset")
        if self.revealed and self.eventual_supported_volume_mmbtu is None:
            raise ValueError("revealed physical outcomes require eventual supported volume")
        if self.revealed and self.outcome_resolved_at is None:
            raise ValueError("revealed physical outcomes require a resolution timestamp")
        return self


class TradeAuthorization(BaseModel):
    authorization_id: str = Field(pattern=r"^[a-z0-9_]+$")
    contract_id: str
    side: OrderSide
    maximum_quantity: int = Field(gt=0)
    commercial_purpose: str = Field(min_length=1)
    supported_physical_quantity_mmbtu: Decimal = Field(gt=0)
    minimum_hedge_ratio: Decimal = Field(ge=0)
    maximum_hedge_ratio: Decimal = Field(gt=0)
    approver_id: str
    approved_at: datetime
    expires_at: datetime
    related_market_brief_id: str | None = None
    related_hedge_memo_id: str | None = None
    status: AuthorizationStatus = AuthorizationStatus.ACTIVE

    @model_validator(mode="after")
    def validate_authorization(self) -> TradeAuthorization:
        if not _is_aware(self.approved_at) or not _is_aware(self.expires_at):
            raise ValueError("authorization timestamps must include UTC offsets")
        if self.expires_at <= self.approved_at:
            raise ValueError("authorization expiration must follow approval")
        if self.maximum_hedge_ratio < self.minimum_hedge_ratio:
            raise ValueError("authorization hedge-ratio range is inverted")
        return self


class OrderRecommendation(BaseModel):
    recommendation_id: str = Field(pattern=r"^[a-z0-9_]+$")
    recommended_at: datetime
    recommended_by_id: str
    contract_id: str
    side: OrderSide
    quantity: int = Field(gt=0)
    order_type: OrderType
    order_price: Decimal | None = Field(default=None, gt=0)
    rationale: str = Field(min_length=1)
    related_market_brief_id: str

    @model_validator(mode="after")
    def validate_price(self) -> OrderRecommendation:
        if not _is_aware(self.recommended_at):
            raise ValueError("recommendation timestamp must include a UTC offset")
        if self.order_type == OrderType.MARKET and self.order_price is not None:
            raise ValueError("market recommendations cannot specify an order price")
        if self.order_type != OrderType.MARKET and self.order_price is None:
            raise ValueError("limit and stop recommendations require an order price")
        return self


class TradeOrder(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    order_id: str = Field(pattern=r"^[a-z0-9_]+$")
    account_id: str = Field(min_length=1)
    book_id: str = Field(min_length=1)
    contract_id: str
    side: OrderSide
    quantity: int = Field(gt=0)
    order_type: OrderType
    order_price: Decimal | None = Field(default=None, gt=0)
    submitted_at: datetime
    authorized_quantity: int = Field(gt=0)
    authorized_user_id: str
    transmitting_user_id: str
    status: OrderStatus
    fill_quantity: int = Field(default=0, ge=0)
    fill_price: Decimal | None = Field(default=None, gt=0)
    fill_timestamp: datetime | None = None
    trigger_price: Decimal | None = Field(default=None, gt=0)
    trigger_timestamp: datetime | None = None
    cancellation_reason: str | None = None
    rejection_reason: str | None = None
    related_physical_exposure_id: str
    related_hedge_memo_id: str | None = None
    related_authorization_id: str

    @model_validator(mode="after")
    def validate_order(self) -> TradeOrder:
        if not _is_aware(self.submitted_at):
            raise ValueError("order submission timestamp must include a UTC offset")
        if self.order_type == OrderType.MARKET and self.order_price is not None:
            raise ValueError("market orders cannot specify an order price")
        if self.order_type != OrderType.MARKET and self.order_price is None:
            raise ValueError("limit and stop orders require an order price")
        if self.fill_quantity > self.quantity:
            raise ValueError("internal fill quantity cannot exceed the submitted order")
        filled = self.status in {OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED}
        if filled and (
            self.fill_quantity == 0 or self.fill_price is None or self.fill_timestamp is None
        ):
            raise ValueError("filled orders require fill quantity, price, and timestamp")
        if self.fill_timestamp is not None:
            if not _is_aware(self.fill_timestamp) or self.fill_timestamp <= self.submitted_at:
                raise ValueError("fill timestamp must be aware and follow submission")
        if (self.trigger_price is None) != (self.trigger_timestamp is None):
            raise ValueError("trigger price and timestamp must be recorded together")
        if self.trigger_timestamp is not None:
            if not _is_aware(self.trigger_timestamp):
                raise ValueError("trigger timestamp must include a UTC offset")
            if self.trigger_timestamp <= self.submitted_at:
                raise ValueError("trigger timestamp must follow submission")
        if self.status == OrderStatus.FILLED and self.fill_quantity != self.quantity:
            raise ValueError("filled order quantity must equal submitted quantity")
        if self.status == OrderStatus.PARTIALLY_FILLED and self.fill_quantity >= self.quantity:
            raise ValueError("partial fill quantity must be below submitted quantity")
        if not filled and self.fill_quantity:
            raise ValueError("unfilled order statuses cannot carry fill quantity")
        if self.status == OrderStatus.CANCELLED and not self.cancellation_reason:
            raise ValueError("cancelled orders require a reason")
        if self.status == OrderStatus.REJECTED and not self.rejection_reason:
            raise ValueError("rejected orders require a reason")
        return self


class ExecutionRecord(BaseModel):
    execution_id: str = Field(pattern=r"^[a-z0-9_]+$")
    order_id: str
    contract_id: str
    side: OrderSide
    quantity: int = Field(gt=0)
    fill_price: Decimal = Field(gt=0)
    fill_timestamp: datetime
    transmitting_user_id: str

    @model_validator(mode="after")
    def validate_timestamp(self) -> ExecutionRecord:
        if not _is_aware(self.fill_timestamp):
            raise ValueError("execution timestamp must include a UTC offset")
        return self


class FCMConfirmation(BaseModel):
    confirmation_id: str = Field(pattern=r"^[a-z0-9_]+$")
    order_id: str
    execution_id: str
    account_id: str
    contract_id: str
    side: OrderSide
    quantity: int = Field(gt=0)
    fill_price: Decimal = Field(gt=0)
    confirmed_at: datetime
    fcm_name: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_timestamp(self) -> FCMConfirmation:
        if not _is_aware(self.confirmed_at):
            raise ValueError("confirmation timestamp must include a UTC offset")
        return self


class TradeReconciliationRecord(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    reconciliation_id: str = Field(pattern=r"^[a-z0-9_]+$")
    prepared_at: datetime
    prepared_by_id: str
    authorization_id: str
    order_id: str
    execution_id: str
    confirmation_id: str
    authorized_quantity: int = Field(gt=0)
    ordered_quantity: int = Field(gt=0)
    executed_quantity: int = Field(gt=0)
    confirmed_quantity: int = Field(gt=0)
    exception_contracts: int = Field(ge=0)
    authorization_exception: bool
    confirmation_matches_execution: bool
    original_status: ReconciliationStatus
    current_status: ReconciliationStatus
    certification_record_id: str | None = None
    related_evidence_record_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_reconciliation(self) -> TradeReconciliationRecord:
        if not _is_aware(self.prepared_at):
            raise ValueError("reconciliation timestamp must include a UTC offset")
        expected_exception = max(0, self.confirmed_quantity - self.authorized_quantity)
        if self.exception_contracts != expected_exception:
            raise ValueError("reconciliation exception quantity does not tie to its records")
        if self.authorization_exception != (self.exception_contracts > 0):
            raise ValueError("reconciliation authorization status does not tie to quantity")
        return self


class ExceptionNotificationRecord(BaseModel):
    notification_id: str = Field(pattern=r"^[a-z0-9_]+$")
    notified_at: datetime
    decision_id: str
    recipient_ids: list[str] = Field(min_length=1)
    communication_record_id: str
    reconciliation_id: str
    status_at_notification: ReconciliationStatus

    @model_validator(mode="after")
    def validate_timestamp(self) -> ExceptionNotificationRecord:
        if not _is_aware(self.notified_at):
            raise ValueError("notification timestamp must include a UTC offset")
        return self


class CorrectiveTradeApprovalRecord(BaseModel):
    approval_id: str = Field(pattern=r"^[a-z0-9_]+$")
    approved_at: datetime
    decision_id: str
    approver_id: str
    reconciliation_id: str
    original_execution_id: str
    side: OrderSide
    quantity: int = Field(gt=0)
    approved: bool

    @model_validator(mode="after")
    def validate_timestamp(self) -> CorrectiveTradeApprovalRecord:
        if not _is_aware(self.approved_at):
            raise ValueError("corrective approval timestamp must include a UTC offset")
        return self


class BlotterStatusChange(BaseModel):
    changed_at: datetime
    status: ReconciliationStatus
    changed_by_id: str
    note: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_timestamp(self) -> BlotterStatusChange:
        if not _is_aware(self.changed_at):
            raise ValueError("blotter status timestamp must include a UTC offset")
        return self


class TradeBlotterEntry(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    blotter_id: str = Field(pattern=r"^[a-z0-9_]+$")
    order_id: str
    authorization_id: str
    execution_id: str
    confirmation_id: str
    reconciliation_id: str | None = None
    side: OrderSide
    internal_quantity: int = Field(gt=0)
    confirmed_quantity: int = Field(gt=0)
    fill_price: Decimal = Field(gt=0)
    current_settlement_price: Decimal = Field(gt=0)
    daily_pnl: Decimal = Decimal("0")
    margin_requirement: Decimal = Field(ge=0)
    supported_physical_volume_mmbtu: Decimal = Field(gt=0)
    hedge_ratio: Decimal = Field(ge=0)
    exception_contracts: int = Field(ge=0)
    reviewer_id: str | None = None
    original_status: ReconciliationStatus
    status: ReconciliationStatus
    status_history: list[BlotterStatusChange] = Field(min_length=1)
    certification_record_id: str | None = None


class ChapterSettlement(BaseModel):
    settlement_id: str = Field(pattern=r"^[a-z0-9_]+$")
    settlement_date: date
    previous_price: Decimal = Field(gt=0)
    settlement_price: Decimal = Field(gt=0)
    contracts: int = Field(ge=0)
    total_pnl: Decimal
    extra_contract_pnl: Decimal
    margin_balance_after: Decimal = Field(ge=0)


class OffsetTrade(BaseModel):
    trade_id: str = Field(pattern=r"^[a-z0-9_]+$")
    original_execution_id: str
    authorization_id: str
    side: OrderSide
    quantity: int = Field(gt=0)
    price: Decimal = Field(gt=0)
    executed_at: datetime
    pnl_since_last_settlement: Decimal
    cumulative_pnl_preserved: Decimal
    contracts_remaining: int = Field(ge=0)
    margin_released: Decimal = Field(ge=0)
    journal_transaction_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_offset(self) -> OffsetTrade:
        if not _is_aware(self.executed_at):
            raise ValueError("offset timestamp must include a UTC offset")
        return self


class LiveTradingPosition(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    contract_id: str
    contract_month: str
    side: PositionSide
    original_contracts: int = Field(gt=0)
    open_contracts: int = Field(ge=0)
    contract_size_mmbtu: Decimal = Field(gt=0)
    entry_price: Decimal = Field(gt=0)
    current_price: Decimal = Field(gt=0)
    cumulative_pnl: Decimal = Decimal("0")
    extra_contract_pnl: Decimal = Decimal("0")
    initial_hedge_ratio: Decimal = Field(gt=0)
    current_hedge_ratio: Decimal = Field(gt=0)
    margin: MarginAccount
    settlements: list[ChapterSettlement] = Field(default_factory=list)
    offset_trade: OffsetTrade | None = None
    journal_transaction_ids: list[str] = Field(default_factory=list)


class EleventhContractState(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    scenario_id: str
    started: bool = True
    completed: bool = False
    current_day: int = Field(default=1, ge=1, le=3)
    current_scene_index: int = Field(default=0, ge=0)
    selected_story_path_id: str | None = None
    selected_intraday_path_id: str
    physical_forecast: PhysicalForecastRecord
    brief_volume_treatment: VolumeTreatment | None = None
    brief_hedge_recommendation: HedgeRecommendation | None = None
    brief_risk_emphasis: RiskEmphasis | None = None
    brief_asked_marisol: bool | None = None
    recommended_order_type: OrderType | None = None
    market_brief: MarketBrief | None = None
    authorization: TradeAuthorization | None = None
    recommendation: OrderRecommendation | None = None
    order: TradeOrder | None = None
    execution: ExecutionRecord | None = None
    confirmation: FCMConfirmation | None = None
    reconciliation: TradeReconciliationRecord | None = None
    blotter: TradeBlotterEntry | None = None
    position: LiveTradingPosition | None = None
    decisions: list[str] = Field(default_factory=list)
    chapter_flags: dict[str, bool] = Field(default_factory=dict)
    relationships: dict[str, int] = Field(
        default_factory=lambda: {
            "cal_rourke": 0,
            "evelyn_marsh": 0,
            "marisol_vega": 0,
            "dom_bellini": 0,
        }
    )
    beginning_relationships: dict[str, int] = Field(default_factory=dict)
    communication_record_ids: list[str] = Field(default_factory=list)
    notification_record_ids: list[str] = Field(default_factory=list)
    approval_ids: list[str] = Field(default_factory=list)
    notifications: list[ExceptionNotificationRecord] = Field(default_factory=list)
    approvals: list[CorrectiveTradeApprovalRecord] = Field(default_factory=list)
    learning_check_ids: list[str] = Field(default_factory=list)
    beginning_ledger_entry_count: int = Field(ge=0)
    beginning_operating_cash: Decimal = Field(ge=0)
    beginning_career_weights: dict[str, int] = Field(default_factory=dict)
    original_blotter_status: ReconciliationStatus | None = None
    outcome: EleventhOutcome | None = None
    physical_economic_pnl: Decimal = Decimal("0")

    @model_validator(mode="after")
    def validate_record_links(self) -> EleventhContractState:
        if self.confirmation is not None:
            if self.order is None or self.execution is None:
                raise ValueError("confirmation requires its original order and execution")
            if self.confirmation.order_id != self.order.order_id:
                raise ValueError("confirmation references an unknown order")
            if self.confirmation.execution_id != self.execution.execution_id:
                raise ValueError("confirmation references an unknown execution")
        if self.blotter is not None:
            required = (
                self.authorization,
                self.order,
                self.execution,
                self.confirmation,
            )
            if any(item is None for item in required):
                raise ValueError("blotter requires authorization, order, execution, confirmation")
            expected = {
                self.blotter.authorization_id: self.authorization.authorization_id,
                self.blotter.order_id: self.order.order_id,
                self.blotter.execution_id: self.execution.execution_id,
                self.blotter.confirmation_id: self.confirmation.confirmation_id,
            }
            if any(left != right for left, right in expected.items()):
                raise ValueError("blotter references missing trade records")
        if self.reconciliation is not None:
            required = (
                self.authorization,
                self.order,
                self.execution,
                self.confirmation,
                self.blotter,
            )
            if any(item is None for item in required):
                raise ValueError("reconciliation requires the complete trade lifecycle")
            expected = {
                self.reconciliation.authorization_id: self.authorization.authorization_id,
                self.reconciliation.order_id: self.order.order_id,
                self.reconciliation.execution_id: self.execution.execution_id,
                self.reconciliation.confirmation_id: self.confirmation.confirmation_id,
                self.blotter.reconciliation_id: self.reconciliation.reconciliation_id,
            }
            if any(left != right for left, right in expected.items()):
                raise ValueError("reconciliation references missing trade records")
        if len({item.notification_id for item in self.notifications}) != len(self.notifications):
            raise ValueError("duplicate exception notification record")
        if any(
            item.communication_record_id not in self.notification_record_ids
            for item in self.notifications
        ):
            raise ValueError("typed exception notification is missing its evidence link")
        if len({item.approval_id for item in self.approvals}) != len(self.approvals):
            raise ValueError("duplicate corrective approval record")
        if any(item.approval_id not in self.approval_ids for item in self.approvals):
            raise ValueError("typed corrective approval is missing its approval link")
        return self


class EleventhContractScenario(BaseModel):
    schema_version: Literal[1]
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    title: str = Field(min_length=1)
    estimated_minutes: int = Field(ge=30, le=45)
    account_id: str
    book_id: str
    contract_id: str
    contract_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    physical_exposure_id: str
    hedge_memo_id: str
    day_1_date: date
    day_2_date: date
    day_3_date: date
    supported_volume_mmbtu: Decimal = Field(gt=0)
    possible_additional_volume_mmbtu: Decimal = Field(gt=0)
    approved_contracts: int = Field(gt=0)
    confirmed_contracts: int = Field(gt=0)
    initial_henry_hub_price: Decimal = Field(gt=0)
    chicago_basis: Decimal
    day_2_settlement_price: Decimal = Field(gt=0)
    day_3_arrives_settlement_price: Decimal = Field(gt=0)
    day_3_fails_settlement_price: Decimal = Field(gt=0)
    day_3_arrives_basis: Decimal
    day_3_fails_basis: Decimal
    offset_price: Decimal = Field(gt=0)
    initial_margin_per_contract: Decimal = Field(gt=0)
    maintenance_margin_per_contract: Decimal = Field(gt=0)
    approver_id: str
    transmitting_user_id: str
    authorization_purpose: str = Field(min_length=1)
    weather_information: str = Field(min_length=1)
    pipeline_information: str = Field(min_length=1)
    data_sources: list[str] = Field(min_length=3)
    intraday_path: IntradayPricePath
    fill_assumptions: list[str] = Field(min_length=1)
    possible_outcomes: list[EleventhOutcome] = Field(min_length=6)

    @model_validator(mode="after")
    def validate_scenario(self) -> EleventhContractScenario:
        if not self.day_1_date < self.day_2_date < self.day_3_date:
            raise ValueError("chapter dates must be ordered")
        if self.confirmed_contracts <= self.approved_contracts:
            raise ValueError("scenario requires an executed quantity exception")
        if self.maintenance_margin_per_contract >= self.initial_margin_per_contract:
            raise ValueError("maintenance margin must be below initial margin")
        if set(self.possible_outcomes) != set(EleventhOutcome):
            raise ValueError("all Eleventh Contract outcomes must be reachable")
        return self


class ChapterLearningFile(BaseModel):
    schema_version: Literal[1]
    checks: list[KnowledgeCheckDefinition] = Field(min_length=7, max_length=10)
    day_check_ids: dict[Literal["day_1", "day_2", "day_3"], list[str]]

    @model_validator(mode="after")
    def validate_checks(self) -> ChapterLearningFile:
        check_ids = [item.id for item in self.checks]
        assigned = [
            check_id for day_checks in self.day_check_ids.values() for check_id in day_checks
        ]
        if len(check_ids) != len(set(check_ids)):
            raise ValueError("duplicate Eleventh Contract check ID")
        if len(assigned) != len(set(assigned)) or set(assigned) != set(check_ids):
            raise ValueError("each Eleventh Contract check must appear in exactly one day")
        return self
