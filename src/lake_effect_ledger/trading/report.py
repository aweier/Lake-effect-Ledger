"""State-derived Analyst Case File for The Eleventh Contract."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from lake_effect_ledger.learning.models import TRAJECTORY_LABELS
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.state import GameState
from lake_effect_ledger.trading.models import EleventhOutcome, ReconciliationStatus

OUTCOME_TITLES = {
    EleventhOutcome.CLEAN_CORRECTION: "Clean Correction",
    EleventhOutcome.SUPPORTED_BUT_LATE: "Supported, but Late",
    EleventhOutcome.CALS_ANALYST: "Cal's Analyst",
    EleventhOutcome.QUIET_FILE: "The Quiet File",
    EleventhOutcome.LUCKY_NOT_AUTHORIZED: "Lucky Is Not Authorized",
    EleventhOutcome.ELEVEN_AGAINST_TEN: "Eleven Against Ten",
}


class AnalystCaseFile(BaseModel):
    case_file_id: str
    outcome: EleventhOutcome
    outcome_title: str
    outcome_summary: str
    original_physical_exposure_mmbtu: Decimal
    possible_additional_volume_mmbtu: Decimal
    eventual_supported_volume_mmbtu: Decimal
    authorized_contracts: int
    executed_contracts: int
    fill_price: Decimal
    order_type: str
    initial_hedge_ratio: Decimal
    final_hedge_ratio: Decimal
    physical_economic_pnl: Decimal
    total_futures_pnl: Decimal
    extra_contract_pnl: Decimal
    extra_contract_initial_margin: Decimal
    beginning_operating_cash: Decimal
    ending_operating_cash: Decimal
    net_operating_cash_movement: Decimal
    ending_margin_balance: Decimal
    extra_contract_offset: bool
    offset_price: Decimal | None
    offset_pnl: Decimal | None
    original_blotter_status: ReconciliationStatus
    final_blotter_status: ReconciliationStatus
    reconciliation_record_id: str | None
    notifications: list[str]
    approvals: list[str]
    physical_support_documents: list[str]
    communications: list[str]
    reconciliation_certified: bool
    certification_record_id: str | None
    accounting_entries: list[str]
    accounting_entries_balanced: bool
    career_development: list[str]
    relationships_affected: list[str]
    series_3_objectives: list[str]
    simplifying_assumptions: list[str]


def build_analyst_case_file(state: GameState, content: ContentBundle) -> AnalystCaseFile:
    chapter = state.eleventh_contract
    if chapter is None or not chapter.completed or chapter.outcome is None:
        raise ValueError("complete The Eleventh Contract before building its case file")
    position = chapter.position
    scenario = content.eleventh_scenario
    offset = position.offset_trade
    entries = state.ledger.entries[chapter.beginning_ledger_entry_count :]
    career_development: list[str] = []
    beginning = chapter.beginning_career_weights
    for tag, current in state.career_trajectory.tag_weights.items():
        change = current - beginning.get(tag.value, 0)
        if change > 0:
            career_development.append(
                f"Your week reinforced a {TRAJECTORY_LABELS[tag].lower()} pattern."
            )
    if not career_development:
        career_development.append("Your professional pattern remains difficult to classify.")
    relationship_names = {
        "cal_rourke": "Cal",
        "evelyn_marsh": "Evelyn",
        "marisol_vega": "Marisol",
        "dom_bellini": "Dom",
    }
    relationships: list[str] = []
    for person_id, current in chapter.relationships.items():
        change = current - chapter.beginning_relationships.get(person_id, 0)
        if change > 0:
            relationships.append(
                f"{relationship_names.get(person_id, person_id)} showed more trust or access."
            )
        elif change < 0:
            relationships.append(
                f"{relationship_names.get(person_id, person_id)} became more guarded."
            )
    if not relationships:
        relationships.append("No relationship shifted clearly during the week.")
    check_objective_ids = {
        objective_id
        for check_id in chapter.learning_check_ids
        for objective_id in content.knowledge_check(check_id).learning_objective_ids
    }
    decision_objective_ids = {
        objective_id
        for scene in content.eleventh_narrative.scenes
        for choice in scene.choices
        if choice.id in chapter.decisions
        for objective_id in choice.learning_objectives
    }
    objective_ids = check_objective_ids | decision_objective_ids
    objectives = [content.lesson(item).title for item in sorted(objective_ids)]
    summaries = {
        EleventhOutcome.CLEAN_CORRECTION: (
            "The exception was preserved, escalated, and corrected with a new linked "
            "offset. Historical records and settled P&L remain intact."
        ),
        EleventhOutcome.SUPPORTED_BUT_LATE: (
            "The additional gas eventually arrived. It changed the final economics, "
            "not the original ten-contract authorization."
        ),
        EleventhOutcome.CALS_ANALYST: (
            "You gave Cal room to define the record and gained access, while the "
            "control exception remained visible in the evidence."
        ),
        EleventhOutcome.QUIET_FILE: (
            "You preserved evidence privately but left the formal process incomplete."
        ),
        EleventhOutcome.LUCKY_NOT_AUTHORIZED: (
            "The extra contract helped economically, but favorable hindsight did not "
            "authorize Tuesday's eleventh fill."
        ),
        EleventhOutcome.ELEVEN_AGAINST_TEN: (
            "The additional gas failed to arrive and the uncorrected eleventh contract "
            "remained an overhedge against supported volume."
        ),
    }
    communications = [
        record.record_id
        for record in state.evidence_log
        if record.record_id in chapter.communication_record_ids
    ]
    notifications = list(
        dict.fromkeys(
            [
                *chapter.notification_record_ids,
                *(item.communication_record_id for item in chapter.notifications),
            ]
        )
    )
    approvals = list(
        dict.fromkeys(
            [
                *chapter.approval_ids,
                *(item.approval_id for item in chapter.approvals),
            ]
        )
    )
    reconciliation_record_id = (
        chapter.reconciliation.reconciliation_id
        if chapter.reconciliation is not None
        else chapter.blotter.reconciliation_id
    )
    certification_record_id = (
        chapter.reconciliation.certification_record_id
        if chapter.reconciliation is not None
        else chapter.blotter.certification_record_id
    )
    return AnalystCaseFile(
        case_file_id="analyst_case_file_eleventh_contract",
        outcome=chapter.outcome,
        outcome_title=OUTCOME_TITLES[chapter.outcome],
        outcome_summary=summaries[chapter.outcome],
        original_physical_exposure_mmbtu=scenario.supported_volume_mmbtu,
        possible_additional_volume_mmbtu=scenario.possible_additional_volume_mmbtu,
        eventual_supported_volume_mmbtu=(chapter.physical_forecast.eventual_supported_volume_mmbtu),
        authorized_contracts=chapter.authorization.maximum_quantity,
        executed_contracts=chapter.execution.quantity,
        fill_price=chapter.execution.fill_price,
        order_type=chapter.order.order_type.value,
        initial_hedge_ratio=position.initial_hedge_ratio,
        final_hedge_ratio=position.current_hedge_ratio,
        physical_economic_pnl=chapter.physical_economic_pnl,
        total_futures_pnl=position.cumulative_pnl,
        extra_contract_pnl=position.extra_contract_pnl,
        extra_contract_initial_margin=scenario.initial_margin_per_contract,
        beginning_operating_cash=chapter.beginning_operating_cash,
        ending_operating_cash=state.corporate_cash,
        net_operating_cash_movement=(state.corporate_cash - chapter.beginning_operating_cash),
        ending_margin_balance=position.margin.balance,
        extra_contract_offset=offset is not None,
        offset_price=offset.price if offset else None,
        offset_pnl=offset.pnl_since_last_settlement if offset else None,
        original_blotter_status=chapter.original_blotter_status,
        final_blotter_status=chapter.blotter.status,
        reconciliation_record_id=reconciliation_record_id,
        notifications=notifications,
        approvals=approvals,
        physical_support_documents=list(chapter.physical_forecast.support_document_ids),
        communications=communications,
        reconciliation_certified=certification_record_id is not None
        or chapter.chapter_flags.get("certified_unresolved", False),
        certification_record_id=certification_record_id,
        accounting_entries=[item.transaction_id for item in entries],
        accounting_entries_balanced=all(
            item.total_debits == item.total_credits for item in entries
        ),
        career_development=career_development,
        relationships_affected=relationships,
        series_3_objectives=objectives,
        simplifying_assumptions=list(scenario.fill_assumptions),
    )
