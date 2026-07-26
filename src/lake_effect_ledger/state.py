"""Versioned, serializable game-state models."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from lake_effect_ledger.accounting.models import Ledger
from lake_effect_ledger.commodity.models import HedgeBookState
from lake_effect_ledger.learning.models import (
    CareerTrajectory,
    GameMode,
    LearningProfile,
    PrologueState,
    ShowMathMode,
)
from lake_effect_ledger.trading.models import EleventhContractState
from lake_effect_ledger.treasury.models import CommunicationRecord, TreasuryState

SAVE_SCHEMA_VERSION = 5
CONTENT_SCHEMA_VERSION = 1


class Background(StrEnum):
    ACCOUNTING = "accounting"
    FINANCE = "finance"
    DATA_ANALYTICS = "data_analytics"


class ResourceName(StrEnum):
    REPUTATION = "reputation"
    FAMILY_LOYALTY = "family_loyalty"
    INTEGRITY = "integrity"
    AUDIT_RISK = "audit_risk"
    REGULATORY_HEAT = "regulatory_heat"
    EVIDENCE_EXPOSURE = "evidence_exposure"


class SkillProfile(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    accounting: int = Field(ge=0, le=10)
    markets: int = Field(ge=0, le=10)
    analytics: int = Field(ge=0, le=10)


class Resources(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    reputation: int = Field(ge=0, le=100)
    family_loyalty: int = Field(ge=0, le=100)
    integrity: int = Field(ge=0, le=100)
    audit_risk: int = Field(ge=0, le=100)
    regulatory_heat: int = Field(ge=0, le=100)
    evidence_exposure: int = Field(ge=0, le=100)


class Player(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    background: Background
    skills: SkillProfile
    role: str = Field(default="Northstar Analyst", min_length=1)


class MarketSnapshot(BaseModel):
    scenario_id: str
    label: str
    fictional: bool
    henry_hub_price: Decimal
    chicago_basis: Decimal


class InboxItem(BaseModel):
    item_id: str
    sender: str
    subject: str
    urgent: bool = False


class EventRecord(BaseModel):
    sequence: int = Field(ge=1)
    phase: Literal["setup", "decision", "immediate", "end_of_day", "system"]
    event_type: str
    source_id: str
    message: str
    changes: dict[str, Any] = Field(default_factory=dict)


class ScheduledEvent(BaseModel):
    event_id: str
    due_day: int = Field(ge=1)
    scheduled_by: str


class GameState(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    save_schema_version: Literal[5] = SAVE_SCHEMA_VERSION
    content_schema_version: Literal[1] = CONTENT_SCHEMA_VERSION
    game_id: str
    seed: int = Field(ge=0)
    current_date: date
    day_number: int = Field(default=1, ge=1)
    player: Player
    game_mode: GameMode = GameMode.STANDARD
    show_math: ShowMathMode = ShowMathMode.ON_REQUEST
    prologue: PrologueState = Field(default_factory=PrologueState)
    learning: LearningProfile = Field(default_factory=LearningProfile)
    career_trajectory: CareerTrajectory = Field(default_factory=CareerTrajectory)
    resources: Resources
    corporate_cash: Decimal = Field(ge=0)
    personal_cash: Decimal = Field(ge=0)
    margin_due: Decimal = Field(ge=0)
    market: MarketSnapshot
    inbox: list[InboxItem]
    ledger: Ledger = Field(default_factory=Ledger)
    flags: dict[str, bool] = Field(default_factory=dict)
    decisions: list[str] = Field(default_factory=list)
    scheduled_events: list[ScheduledEvent] = Field(default_factory=list)
    event_log: list[EventRecord] = Field(default_factory=list)
    learning_objectives: list[str] = Field(default_factory=list)
    end_of_day_messages: list[str] = Field(default_factory=list)
    hedge_book: HedgeBookState | None = None
    treasury: TreasuryState | None = None
    evidence_log: list[CommunicationRecord] = Field(default_factory=list)
    eleventh_contract: EleventhContractState | None = None
    completed: bool = False

    def record(
        self,
        *,
        phase: Literal["setup", "decision", "immediate", "end_of_day", "system"],
        event_type: str,
        source_id: str,
        message: str,
        changes: dict[str, Any] | None = None,
    ) -> None:
        self.event_log.append(
            EventRecord(
                sequence=len(self.event_log) + 1,
                phase=phase,
                event_type=event_type,
                source_id=source_id,
                message=message,
                changes=changes or {},
            )
        )
