"""Validated content and runtime state for the treasury crisis."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ObligationPriority(StrEnum):
    CRITICAL = "critical"
    PROTECTED = "protected"
    DISCRETIONARY = "discretionary"


class ObligationStatus(StrEnum):
    PROTECTED = "protected"
    PAID = "paid"
    DEFERRED = "deferred"
    OVERDUE = "overdue"


class FundingChoice(StrEnum):
    OPERATING_CASH = "operating_cash"
    REVOLVER = "revolver"
    REDUCE_POSITION = "reduce_position"
    MISS_CALL = "miss_call"


class NotificationChoice(StrEnum):
    NOTIFY_IMMEDIATELY = "notify_immediately"
    NOTIFY_CAL_ONLY = "notify_cal_only"
    SEND_VAGUE_UPDATE = "send_vague_update"
    DELAY_NOTIFICATION = "delay_notification"


class CommunicationAccuracy(StrEnum):
    ACCURATE = "accurate"
    LIMITED = "limited"
    VAGUE = "vague"
    DELAYED = "delayed"


class TreasuryOutcome(StrEnum):
    TRANSPARENT_DRAW = "transparent_draw"
    CASH_RICH_PAYMENT_POOR = "cash_rich_payment_poor"
    DE_HEDGED = "de_hedged"
    TWO_OCLOCK_MISS = "two_oclock_miss"
    NO_POSITION_SAME_PROBLEM = "no_position_same_problem"
    CLEAN_CASH_FUNDING = "clean_cash_funding"


class CharacterDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1)
    role: str = Field(min_length=1)
    origin: str = Field(min_length=1)
    public_detail: str = Field(min_length=1, max_length=180)
    interaction_reason: str = Field(min_length=1, max_length=180)


class ObligationDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    payee: str = Field(min_length=1)
    description: str = Field(min_length=1)
    amount: Decimal = Field(gt=0)
    due_date: date
    priority: ObligationPriority
    protected: bool
    journal_pattern_id: str = Field(pattern=r"^[a-z0-9_]+$")


class FacilityDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    lender_name: str = Field(min_length=1)
    commitment: Decimal = Field(gt=0)
    beginning_outstanding: Decimal = Field(ge=0)
    annual_interest_rate: Decimal = Field(gt=0, lt=1)
    minimum_draw_increment: Decimal = Field(gt=0)
    covenant_minimum_available_liquidity: Decimal = Field(ge=0)
    maturity_date: date
    default_draw_amount: Decimal = Field(gt=0)
    interest_accrual_days: int = Field(gt=0)
    required_approver_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_capacity(self) -> FacilityDefinition:
        if self.beginning_outstanding > self.commitment:
            raise ValueError("facility beginning balance exceeds commitment")
        if self.default_draw_amount > self.commitment - self.beginning_outstanding:
            raise ValueError("default draw exceeds undrawn facility capacity")
        for amount, label in (
            (self.commitment, "commitment"),
            (self.default_draw_amount, "default draw"),
        ):
            if amount % self.minimum_draw_increment:
                raise ValueError(f"facility {label} must use the minimum draw increment")
        return self


class NotificationOptionDefinition(BaseModel):
    id: NotificationChoice
    label: str = Field(min_length=1)
    narrative: str = Field(min_length=1)
    timestamp: datetime
    channel: Literal["email", "phone", "teams", "none"]
    sender_id: str = Field(pattern=r"^[a-z0-9_]+$")
    recipient_ids: list[str]
    subject: str = Field(min_length=1)
    body_summary: str = Field(min_length=1)
    accuracy: CommunicationAccuracy
    grants_facility_approval: bool
    resource_deltas: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_timestamp(self) -> NotificationOptionDefinition:
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("notification timestamps must be timezone-aware")
        if self.channel == "none" and self.recipient_ids:
            raise ValueError("a delayed non-communication cannot have recipients")
        return self


class TreasuryScenarioDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    trigger_settlement_day: int = Field(ge=1)
    crisis_title: str = Field(min_length=1)
    crisis_text: str = Field(min_length=1)
    no_position_crisis_text: str = Field(min_length=1)
    margin_deadline: datetime
    minimum_operating_reserve: Decimal = Field(ge=0)
    facility: FacilityDefinition
    obligations: list[ObligationDefinition] = Field(min_length=1)
    notification_options: list[NotificationOptionDefinition] = Field(min_length=4)
    default_reduction_contracts: int = Field(gt=0)
    journal_patterns: dict[
        Literal[
            "revolver_draw",
            "interest_accrual",
            "revolver_repayment",
        ],
        str,
    ]
    learning_objectives: list[str] = Field(min_length=1)
    simplified_assumptions: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scenario(self) -> TreasuryScenarioDefinition:
        if self.margin_deadline.tzinfo is None or self.margin_deadline.utcoffset() is None:
            raise ValueError("margin deadline must be timezone-aware")
        notification_ids = [item.id for item in self.notification_options]
        if len(notification_ids) != len(set(notification_ids)):
            raise ValueError("duplicate treasury notification option")
        if set(notification_ids) != set(NotificationChoice):
            raise ValueError("treasury scenario must define all notification choices")
        obligation_ids = [item.id for item in self.obligations]
        if len(obligation_ids) != len(set(obligation_ids)):
            raise ValueError("duplicate treasury obligation ID")
        return self


class ScheduledCashObligation(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: str
    payee: str
    description: str
    amount: Decimal = Field(gt=0)
    due_date: date
    priority: ObligationPriority
    protected: bool
    journal_pattern_id: str
    status: ObligationStatus = ObligationStatus.PROTECTED
    paid_date: date | None = None
    journal_transaction_id: str | None = None


class RevolvingCreditState(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    facility_id: str
    lender_name: str
    commitment: Decimal = Field(gt=0)
    beginning_outstanding: Decimal = Field(ge=0)
    outstanding: Decimal = Field(ge=0)
    annual_interest_rate: Decimal = Field(gt=0, lt=1)
    accrued_interest: Decimal = Field(default=Decimal("0"), ge=0)
    minimum_draw_increment: Decimal = Field(gt=0)
    covenant_minimum_available_liquidity: Decimal = Field(ge=0)
    maturity_date: date
    total_draws: Decimal = Field(default=Decimal("0"), ge=0)
    total_repayments: Decimal = Field(default=Decimal("0"), ge=0)

    @property
    def undrawn_availability(self) -> Decimal:
        return self.commitment - self.outstanding

    @model_validator(mode="after")
    def validate_balances(self) -> RevolvingCreditState:
        if self.outstanding > self.commitment:
            raise ValueError("revolver outstanding exceeds commitment")
        if (
            self.beginning_outstanding + self.total_draws - self.total_repayments
            != self.outstanding
        ):
            raise ValueError("revolver debt bridge does not reconcile")
        return self


class LiquiditySnapshot(BaseModel):
    timestamp: datetime
    label: str
    operating_cash: Decimal = Field(ge=0)
    fcm_margin_cash: Decimal = Field(ge=0)
    undrawn_revolver: Decimal = Field(ge=0)
    protected_obligations: Decimal = Field(ge=0)
    available_liquidity: Decimal


class CovenantResult(BaseModel):
    tested_at: datetime
    available_liquidity: Decimal
    minimum_required: Decimal
    passed: bool


class ApprovalRecord(BaseModel):
    approval_id: str
    timestamp: datetime
    decision_id: str
    requested_from_ids: list[str]
    approved_by_ids: list[str]
    approved: bool


class BorrowingRequest(BaseModel):
    request_id: str
    timestamp: datetime
    amount: Decimal = Field(gt=0)
    requested_by_id: str
    approver_ids: list[str]
    approved: bool
    journal_transaction_id: str | None = None


class FundingDecision(BaseModel):
    decision_id: str
    timestamp: datetime
    choice: FundingChoice
    margin_call_id: str | None
    original_call_amount: Decimal = Field(ge=0)
    funded_amount: Decimal = Field(ge=0)
    revolver_draw_amount: Decimal = Field(ge=0)
    contracts_reduced: int = Field(ge=0)
    margin_released: Decimal = Field(ge=0)
    revised_call_amount: Decimal = Field(ge=0)
    missed: bool


class CommunicationRecord(BaseModel):
    record_id: str = Field(pattern=r"^[a-z0-9_]+$")
    timestamp: datetime
    channel: Literal["email", "phone", "teams", "none"]
    sender_id: str
    recipient_ids: list[str]
    subject: str
    body_summary: str
    accuracy: CommunicationAccuracy
    linked_decision_ids: list[str] = Field(default_factory=list)
    linked_journal_transaction_ids: list[str] = Field(default_factory=list)


class TreasuryState(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    scenario_id: str
    started_at: datetime
    margin_deadline: datetime
    beginning_operating_cash: Decimal = Field(ge=0)
    beginning_fcm_margin_cash: Decimal = Field(ge=0)
    beginning_ledger_entry_count: int = Field(ge=0)
    margin_call_id: str | None
    original_margin_call_amount: Decimal = Field(ge=0)
    obligations: list[ScheduledCashObligation]
    facility: RevolvingCreditState
    notification_choice: NotificationChoice | None = None
    communication_record_id: str | None = None
    approval: ApprovalRecord | None = None
    borrowing_request: BorrowingRequest | None = None
    funding_decision: FundingDecision | None = None
    liquidity_snapshots: list[LiquiditySnapshot] = Field(default_factory=list)
    covenant_result: CovenantResult | None = None
    journal_transaction_ids: list[str] = Field(default_factory=list)
    projected_lowest_cash: Decimal | None = None
    outcome: TreasuryOutcome | None = None
    completed: bool = False

    @property
    def remaining_protected_obligations(self) -> Decimal:
        return sum(
            (
                item.amount
                for item in self.obligations
                if item.protected and item.status != ObligationStatus.PAID
            ),
            Decimal("0"),
        )
