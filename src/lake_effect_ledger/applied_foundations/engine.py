"""Deterministic story and finance orchestration for The Supply Gap."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from lake_effect_ledger.accounting.models import JournalEntry, JournalLine
from lake_effect_ledger.applied_foundations.models import (
    AppliedChoiceDefinition,
    AppliedFoundationsState,
    AppliedSeasonStatus,
    AuthoredOrderResult,
    choice_effect_payload,
)
from lake_effect_ledger.commodity.engine import (
    buyer_physical_purchase_cost_variance,
    combined_economic_result,
    contract_count,
    futures_daily_pnl,
    margin_call_amount,
    regional_price,
)
from lake_effect_ledger.commodity.models import (
    FuturesPosition,
    MarginAccount,
    MarginCall,
    PositionSide,
    money,
)
from lake_effect_ledger.learning.engine import LearningEngine

if TYPE_CHECKING:
    from lake_effect_ledger.narrative.models import ContentBundle
    from lake_effect_ledger.state import GameState


class AppliedFoundationsEngine:
    """Runs one fixed learning season without touching later-story financial inputs."""

    def __init__(self, content: ContentBundle) -> None:
        self.content = content
        self.blueprint = content.applied_foundations
        self.learning = LearningEngine(content)

    def start(self, state: GameState) -> AppliedFoundationsState:
        chapter = state.applied_foundations
        if chapter.status == AppliedSeasonStatus.LEGACY_SKIPPED:
            raise ValueError(
                "legacy Extended Story saves cannot move back into Applied Foundations"
            )
        if not state.core_campaign_completed:
            raise ValueError("complete Series 3 Core before starting Applied Foundations")
        if state.no_surprises is not None or state.diligence_room is not None:
            raise ValueError("Applied Foundations cannot begin after the audit story has started")
        if chapter.status == AppliedSeasonStatus.NOT_STARTED:
            chapter.status = AppliedSeasonStatus.IN_PROGRESS
            chapter.current_day_index = 0
            chapter.record_chain = [item.id for item in self.blueprint.record_chain]
            chapter.record_statuses = {
                item.id: ("pending" if item.id != "physical_support" else "partially_confirmed")
                for item in self.blueprint.record_chain
            }
        if chapter.current_day_index < 3:
            self.begin_day(state, chapter.current_day_index + 1)
        return chapter

    def begin_day(self, state: GameState, day_number: int) -> None:
        chapter = self._active(state)
        if day_number != chapter.current_day_index + 1:
            raise ValueError("Applied Foundations days must be completed in order")
        day = self.blueprint.day(day_number)
        state.current_date = day.date
        objective_ids = sorted(
            {
                objective
                for check_id in day.check_ids
                for objective in self.blueprint.question(check_id).objectives
            }
        )
        self.learning.introduce_objectives(
            state,
            objective_ids,
            chapter_id="supply_gap",
        )
        if day_number == 3 and not chapter.financial.settled:
            self.settle_case(state)

    def current_decision(self, state: GameState):
        chapter = self._active(state)
        day = self.blueprint.day(chapter.current_day_index + 1)
        if chapter.current_decision_index >= len(day.decision_ids):
            return None
        return self.blueprint.decision(day.decision_ids[chapter.current_decision_index])

    def record_decision(
        self,
        state: GameState,
        decision_id: str,
        choice_id: str,
    ) -> AppliedChoiceDefinition:
        chapter = self._active(state)
        decision = self.current_decision(state)
        if decision is None or decision.id != decision_id:
            raise ValueError(f"decision {decision_id} is not the current Applied decision")
        if choice_id in chapter.decisions:
            raise ValueError(f"Applied choice already recorded: {choice_id}")
        try:
            choice = next(item for item in decision.choices if item.id == choice_id)
        except StopIteration as error:
            raise ValueError(f"choice {choice_id} does not belong to {decision_id}") from error
        if decision.id == "af_recommendation_packet" and not chapter.confirmed_volume:
            raise ValueError("the final recommendation requires Marisol's support")
        for person_id, amount in choice.relationship_deltas.items():
            chapter.relationships[person_id] = chapter.relationships.get(person_id, 0) + amount
        for tag, amount in choice.tendency_tags.items():
            chapter.trajectory.record(choice.id, tag, amount)
        chapter.evidence_score += choice.evidence_delta
        chapter.documentation_score += choice.documentation_delta
        chapter.communication_score += choice.communication_delta
        chapter.decisions.append(choice.id)
        chapter.current_decision_index += 1
        if decision.id == "af_direction_explanation":
            chapter.confirmed_volume = True
            chapter.record_statuses["physical_support"] = "confirmed"
        elif decision.id == "af_recommendation_packet":
            chapter.record_statuses["analyst_recommendation"] = "prepared"
        elif decision.id == "af_supervised_transmission":
            self.initialize_financial_case(state)
            chapter.record_statuses.update(
                {
                    "hedge_authorization": "authorized",
                    "order_transmission": "transmitted_under_supervision",
                    "execution": "filled",
                    "original_confirmation": "preserved",
                }
            )
        elif decision.id == "af_confirmation_exception":
            chapter.record_statuses.update(
                {
                    "reconciliation": "reconciled",
                    "control_review": "reviewed",
                }
            )
        return choice

    def complete_day(self, state: GameState, *, require_checks: bool) -> None:
        chapter = self._active(state)
        day = self.blueprint.day(chapter.current_day_index + 1)
        if chapter.current_decision_index != len(day.decision_ids):
            raise ValueError(f"cannot complete {day.id}; story decisions remain")
        incomplete = [
            check_id
            for check_id in day.check_ids
            if not state.learning.checks.get(check_id)
            or not state.learning.checks[check_id].completed
        ]
        if require_checks and incomplete:
            raise ValueError(f"cannot complete {day.id}; incomplete checks: {incomplete}")
        chapter.current_day_index += 1
        chapter.current_decision_index = 0
        chapter.current_check_index = 0

    def initialize_financial_case(self, state: GameState) -> None:
        chapter = self._active(state)
        financial = chapter.financial
        if financial.initialized:
            return
        if not chapter.confirmed_volume:
            raise ValueError("the full physical requirement must be confirmed before the hedge")
        scenario = self.blueprint.scenario
        contract = self.content.commodity_contract(scenario.contract_id)
        contracts = contract_count(
            physical_quantity_mmbtu=scenario.physical_requirement_mmbtu,
            contract_size_mmbtu=contract.contract_size_mmbtu,
        )
        if int(contracts) != scenario.authorized_contracts:
            raise ValueError("authored contract count disagrees with the confirmed exposure")
        initial_margin = money(
            scenario.initial_margin_per_contract * Decimal(scenario.authorized_contracts)
        )
        maintenance_margin = money(
            scenario.maintenance_margin_per_contract * Decimal(scenario.authorized_contracts)
        )
        financial.opening_operating_cash = state.corporate_cash
        financial.operating_cash = money(state.corporate_cash - initial_margin)
        financial.operating_cash_movement = money(
            financial.operating_cash - financial.opening_operating_cash
        )
        if financial.operating_cash < 0:
            raise ValueError("isolated Supply Gap case cannot fund initial margin")
        financial.margin = MarginAccount(
            balance=initial_margin,
            initial_requirement=initial_margin,
            maintenance_requirement=maintenance_margin,
            total_initial_deposit=initial_margin,
        )
        financial.position = FuturesPosition(
            contract_id=contract.id,
            contract_month=scenario.contract_month,
            side=PositionSide.LONG,
            contracts=scenario.authorized_contracts,
            contract_size_mmbtu=contract.contract_size_mmbtu,
            entry_price=scenario.initial_henry_hub_price,
            current_price=scenario.initial_henry_hub_price,
        )
        self._post(
            financial,
            pattern_key="initial_margin",
            amount=initial_margin,
            transaction_id="txn_supply_gap_initial_margin",
            description="Supply Gap initial margin transfer",
            source_id="supply_gap_buy_ticket",
            entry_date=self.blueprint.day(2).date,
        )
        financial.order_results = self.evaluate_order_tape()
        financial.calculations.update(
            {
                "contract_count": contracts,
                "initial_margin": initial_margin,
                "maintenance_margin": maintenance_margin,
            }
        )
        financial.initialized = True
        self.assert_reconciles(state)

    def settle_case(self, state: GameState) -> None:
        chapter = self._active(state)
        if not chapter.financial.initialized:
            self.initialize_financial_case(state)
        financial = chapter.financial
        if financial.settled:
            return
        scenario = self.blueprint.scenario
        contract = self.content.commodity_contract(scenario.contract_id)
        margin = financial.margin
        position = financial.position
        if margin is None or position is None:
            raise ValueError("Supply Gap margin account or futures position is missing")
        initial_chicago = regional_price(
            scenario.initial_henry_hub_price,
            scenario.initial_chicago_basis,
        )
        final_chicago = regional_price(
            scenario.final_henry_hub_price,
            scenario.final_chicago_basis,
        )
        physical_variance = buyer_physical_purchase_cost_variance(
            initial_regional_price=initial_chicago,
            final_regional_price=final_chicago,
            physical_quantity_mmbtu=scenario.physical_requirement_mmbtu,
        )
        futures_result = futures_daily_pnl(
            side=PositionSide.LONG,
            previous_settlement=scenario.initial_henry_hub_price,
            current_settlement=scenario.final_henry_hub_price,
            contract_size_mmbtu=contract.contract_size_mmbtu,
            contracts=scenario.authorized_contracts,
        )
        position.current_price = scenario.final_henry_hub_price
        position.daily_pnl = futures_result
        position.cumulative_pnl = futures_result
        basis_effect = money(
            (scenario.initial_chicago_basis - scenario.final_chicago_basis)
            * scenario.physical_requirement_mmbtu
        )
        combined = combined_economic_result(
            physical_variance=physical_variance,
            futures_result=futures_result,
        )
        margin.balance = money(margin.balance + futures_result)
        margin.total_variation_margin = money(margin.total_variation_margin + futures_result)
        self._post(
            financial,
            pattern_key="futures_loss",
            amount=-futures_result,
            transaction_id="txn_supply_gap_futures_loss",
            description="Supply Gap long-futures variation loss",
            source_id="supply_gap_day_3_settlement",
            entry_date=self.blueprint.day(3).date,
        )
        call = margin_call_amount(
            balance=margin.balance,
            initial_requirement=margin.initial_requirement,
            maintenance_requirement=margin.maintenance_requirement,
        )
        if call > financial.operating_cash:
            raise ValueError("isolated Supply Gap case cannot fund the margin call")
        financial.operating_cash = money(financial.operating_cash - call)
        financial.operating_cash_movement = money(
            financial.operating_cash - financial.opening_operating_cash
        )
        margin.balance = money(margin.balance + call)
        margin.total_additional_deposits = money(margin.total_additional_deposits + call)
        margin.calls.append(
            MarginCall(
                call_id="supply_gap_margin_call",
                call_date=self.blueprint.day(3).date,
                required_amount=call,
                funded_amount=call,
                shortfall=Decimal("0"),
                met=True,
            )
        )
        self._post(
            financial,
            pattern_key="margin_call",
            amount=call,
            transaction_id="txn_supply_gap_margin_call",
            description="Supply Gap margin-call funding transfer",
            source_id="supply_gap_margin_call",
            entry_date=self.blueprint.day(3).date,
        )
        financial.calculations.update(
            {
                "initial_chicago_price": initial_chicago,
                "final_chicago_price": final_chicago,
                "physical_purchase_cost_variance": physical_variance,
                "long_futures_result": futures_result,
                "buyer_basis_effect": basis_effect,
                "combined_economic_result": combined,
                "post_settlement_margin": money(margin.initial_requirement + futures_result),
                "margin_call": call,
            }
        )
        financial.physical_memorandum = {
            "quantity_mmbtu": scenario.physical_requirement_mmbtu,
            "initial_regional_price": initial_chicago,
            "final_regional_price": final_chicago,
            "purchase_cost_variance": physical_variance,
            "buyer_basis_effect": basis_effect,
            "combined_economic_result": combined,
        }
        financial.settled = True
        self.assert_reconciles(state)

    def evaluate_order_tape(self) -> list[AuthoredOrderResult]:
        tape = self.blueprint.order_tape
        results: list[AuthoredOrderResult] = []
        for example in tape.examples:
            if example.order_type == "market":
                result = AuthoredOrderResult(
                    order_id=example.id,
                    order_type=example.order_type,
                    filled=True,
                    fill_price=tape.subsequent_prices[0],
                )
            elif example.order_type == "limit":
                fill = next(
                    (price for price in tape.subsequent_prices if price <= example.limit_price),
                    None,
                )
                result = AuthoredOrderResult(
                    order_id=example.id,
                    order_type=example.order_type,
                    filled=fill is not None,
                    fill_price=fill,
                )
            else:
                trigger = next(
                    (price for price in tape.subsequent_prices if price >= example.stop_price),
                    None,
                )
                result = AuthoredOrderResult(
                    order_id=example.id,
                    order_type=example.order_type,
                    filled=trigger is not None,
                    triggered=trigger is not None,
                    fill_price=trigger,
                )
            if result.filled != (example.result == "filled") or result.fill_price != (
                example.fill_price
            ):
                raise ValueError(f"authored order result disagrees for {example.id}")
            results.append(result)
        return results

    def complete_chapter(self, state: GameState) -> None:
        chapter = self._active(state)
        if chapter.current_day_index != 3 or not chapter.financial.settled:
            raise ValueError("complete all three Supply Gap days before the review")

    def mark_completed(self, state: GameState) -> None:
        chapter = self._active(state)
        if not chapter.review.completed or not chapter.snapshot_finalized:
            raise ValueError("complete the Applied review and snapshot before the debrief")
        chapter.debrief_completed = True
        chapter.status = AppliedSeasonStatus.COMPLETED

    def assert_reconciles(self, state: GameState) -> None:
        financial = state.applied_foundations.financial
        activity = financial.ledger.account_activity()
        cash_debits, cash_credits = activity.get("1000", (Decimal("0"), Decimal("0")))
        expected_cash = money(financial.opening_operating_cash + cash_debits - cash_credits)
        if expected_cash != money(financial.operating_cash):
            raise ValueError(
                f"Supply Gap operating cash does not reconcile: {expected_cash} "
                f"versus {financial.operating_cash}"
            )
        margin_debits, margin_credits = activity.get("1050", (Decimal("0"), Decimal("0")))
        expected_margin = money(margin_debits - margin_credits)
        actual_margin = financial.margin.balance if financial.margin is not None else Decimal("0")
        if expected_margin != money(actual_margin):
            raise ValueError(
                f"Supply Gap FCM margin does not reconcile: {expected_margin} "
                f"versus {actual_margin}"
            )
        if any(entry.total_debits != entry.total_credits for entry in financial.ledger.entries):
            raise ValueError("Supply Gap ledger contains an unbalanced entry")

    def scripted_choice(self, state: GameState, path_name: str) -> str:
        if path_name not in self.blueprint.scripted_paths:
            valid = ", ".join(sorted(self.blueprint.scripted_paths))
            raise ValueError(f"Applied path must be one of: {valid}")
        chapter = self._active(state)
        completed = len(chapter.decisions)
        return self.blueprint.scripted_paths[path_name][completed]

    def decision_effects(self, choice: AppliedChoiceDefinition) -> dict[str, object]:
        return choice_effect_payload(choice)

    def _post(
        self,
        financial,
        *,
        pattern_key: str,
        amount: Decimal,
        transaction_id: str,
        description: str,
        source_id: str,
        entry_date,
    ) -> None:
        if amount <= 0:
            raise ValueError("Supply Gap journal amount must be positive")
        scenario = self.content.hedge_scenario("episode_01_hedge_book")
        pattern = self.content.journal_pattern(scenario.journal_patterns[pattern_key])
        financial.ledger.post(
            JournalEntry(
                transaction_id=transaction_id,
                entry_date=entry_date,
                description=description,
                source_id=source_id,
                lines=[
                    JournalLine(account=pattern.debit_account, debit=money(amount)),
                    JournalLine(account=pattern.credit_account, credit=money(amount)),
                ],
            ),
            self.content.valid_accounts,
        )

    @staticmethod
    def _active(state: GameState) -> AppliedFoundationsState:
        chapter = state.applied_foundations
        if chapter.status not in {
            AppliedSeasonStatus.IN_PROGRESS,
            AppliedSeasonStatus.NOT_STARTED,
        }:
            raise ValueError(f"Applied Foundations is {chapter.status.value}")
        return chapter
