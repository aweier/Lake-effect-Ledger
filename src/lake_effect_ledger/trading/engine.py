"""Small deterministic trade lifecycle for the Eleventh Contract."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from lake_effect_ledger.accounting.models import JournalEntry, JournalLine
from lake_effect_ledger.commodity.engine import (
    futures_daily_pnl,
    hedge_ratio,
    margin_call_amount,
)
from lake_effect_ledger.commodity.models import MarginAccount, PositionSide, money
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.state import GameState
from lake_effect_ledger.trading.models import (
    AuthorizationStatus,
    BlotterStatusChange,
    ChapterSettlement,
    CorrectiveTradeApprovalRecord,
    EleventhContractState,
    EleventhOutcome,
    ExecutionRecord,
    FCMConfirmation,
    LiveTradingPosition,
    MarketBrief,
    OffsetTrade,
    OrderRecommendation,
    OrderSide,
    OrderStatus,
    OrderType,
    PhysicalForecastRecord,
    PhysicalVolumeOutcome,
    ReconciliationStatus,
    TradeAuthorization,
    TradeBlotterEntry,
    TradeOrder,
    TradeReconciliationRecord,
)
from lake_effect_ledger.treasury.models import CommunicationAccuracy, CommunicationRecord

CHICAGO_TZ = timezone(timedelta(hours=-6), name="CST")


class OrderFillEngine:
    """Execute one order against a fictional timestamped price path."""

    @staticmethod
    def execute(order: TradeOrder, path) -> TradeOrder:
        if order.status not in {OrderStatus.DRAFT, OrderStatus.SUBMITTED}:
            raise ValueError("only a draft or submitted order can be executed")
        executable = [item for item in path.points if item.timestamp > order.submitted_at]
        if not executable:
            return order.model_copy(update={"status": OrderStatus.SUBMITTED})

        fill_point = None
        trigger_point = None
        if order.order_type == OrderType.MARKET:
            fill_point = executable[0]
        elif order.order_type == OrderType.LIMIT:
            for point in executable:
                eligible = (
                    point.price <= order.order_price
                    if order.side == OrderSide.BUY
                    else point.price >= order.order_price
                )
                if eligible:
                    fill_point = point
                    break
        else:
            for index, point in enumerate(executable):
                triggered = (
                    point.price >= order.order_price
                    if order.side == OrderSide.BUY
                    else point.price <= order.order_price
                )
                if triggered:
                    trigger_point = point
                    if index + 1 < len(executable):
                        fill_point = executable[index + 1]
                    break

        if fill_point is None:
            update: dict[str, object] = {
                "status": (
                    OrderStatus.TRIGGERED if trigger_point is not None else OrderStatus.SUBMITTED
                )
            }
            if trigger_point is not None:
                update.update(
                    {
                        "trigger_price": trigger_point.price,
                        "trigger_timestamp": trigger_point.timestamp,
                    }
                )
            return order.model_copy(update=update)

        update = {
            "status": OrderStatus.FILLED,
            "fill_quantity": order.quantity,
            "fill_price": fill_point.price,
            "fill_timestamp": fill_point.timestamp,
        }
        if trigger_point is not None:
            update.update(
                {
                    "trigger_price": trigger_point.price,
                    "trigger_timestamp": trigger_point.timestamp,
                }
            )
        return order.model_copy(update=update)


class EleventhContractEngine:
    def __init__(self, content: ContentBundle) -> None:
        self.content = content
        self.scenario = content.eleventh_scenario
        self.contract = content.commodity_contract(self.scenario.contract_id)
        self.journal_patterns = content.hedge_scenarios.scenarios[0].journal_patterns

    def initialize(self, state: GameState) -> EleventhContractState:
        if state.eleventh_contract is not None:
            return state.eleventh_contract
        if not state.completed:
            raise ValueError("complete the December Difference before the new chapter")
        if state.hedge_book is None or not state.hedge_book.completed:
            raise ValueError("complete the Hedge Book before the new chapter")
        if state.treasury is not None and not state.treasury.completed:
            raise ValueError("complete the Two O'Clock Call before the new chapter")
        outcome = (
            PhysicalVolumeOutcome.ARRIVES if state.seed % 2 == 0 else PhysicalVolumeOutcome.FAILS
        )
        relationships = {
            "cal_rourke": 0,
            "evelyn_marsh": 0,
            "marisol_vega": 0,
            "dom_bellini": 0,
        }
        self._apply_prior_relationships(state, relationships)
        chapter = EleventhContractState(
            scenario_id=self.scenario.id,
            selected_intraday_path_id=self.scenario.intraday_path.id,
            physical_forecast=PhysicalForecastRecord(
                forecast_id="forecast_live_week_2028",
                supported_volume_mmbtu=self.scenario.supported_volume_mmbtu,
                possible_additional_volume_mmbtu=(self.scenario.possible_additional_volume_mmbtu),
                outcome=outcome,
            ),
            relationships=relationships,
            beginning_relationships=dict(relationships),
            beginning_ledger_entry_count=len(state.ledger.entries),
            beginning_operating_cash=state.corporate_cash,
            beginning_career_weights={
                tag.value: weight for tag, weight in state.career_trajectory.tag_weights.items()
            },
        )
        state.eleventh_contract = chapter
        state.current_date = self.scenario.day_1_date
        state.record(
            phase="system",
            event_type="eleventh_contract_started",
            source_id=self.scenario.id,
            message="The Eleventh Contract live-book week started.",
            changes={"physical_outcome_selected": "hidden", "seed": state.seed},
        )
        return chapter

    def assemble_market_brief(self, state: GameState) -> MarketBrief:
        chapter = self._chapter(state)
        if chapter.market_brief is not None:
            return chapter.market_brief
        required = (
            chapter.brief_volume_treatment,
            chapter.brief_hedge_recommendation,
            chapter.brief_risk_emphasis,
            chapter.brief_asked_marisol,
        )
        if any(item is None for item in required):
            raise ValueError("complete all structured morning-note selections first")
        timestamp = datetime.combine(
            self.scenario.day_1_date,
            time(10, 15),
            tzinfo=CHICAGO_TZ,
        )
        volume_text = {
            "confirmed_and_possible_separate": (
                "100,000 MMBtu is supported; another 10,000 MMBtu remains possible and unconfirmed."
            ),
            "probable_but_unconfirmed": (
                "The brief describes 110,000 MMBtu as probable but identifies the "
                "last 10,000 MMBtu as unsupported."
            ),
            "treat_possible_as_committed": (
                "The brief presents 110,000 MMBtu as expected even though the final "
                "10,000 MMBtu lacks nomination or amendment support."
            ),
        }[chapter.brief_volume_treatment.value]
        body = (
            f"{volume_text} Recommendation: {chapter.brief_hedge_recommendation.value}. "
            f"Primary risk: {chapter.brief_risk_emphasis.value}. "
            f"Marisol confirmation requested: {chapter.brief_asked_marisol}."
        )
        communication = CommunicationRecord(
            record_id="comm_eleventh_market_brief",
            timestamp=timestamp,
            channel="email",
            sender_id="player",
            recipient_ids=["evelyn_marsh", "cal_rourke", "marisol_vega"],
            subject="Morning natural-gas market and exposure note",
            body_summary=body,
            accuracy=(
                CommunicationAccuracy.LIMITED
                if chapter.brief_volume_treatment.value == "treat_possible_as_committed"
                else CommunicationAccuracy.ACCURATE
            ),
            linked_decision_ids=list(chapter.decisions),
        )
        state.evidence_log.append(communication)
        brief = MarketBrief(
            brief_id="brief_live_week_2028",
            created_at=timestamp,
            author_id="player",
            confirmed_volume_mmbtu=self.scenario.supported_volume_mmbtu,
            possible_volume_mmbtu=self.scenario.possible_additional_volume_mmbtu,
            volume_treatment=chapter.brief_volume_treatment,
            hedge_recommendation=chapter.brief_hedge_recommendation,
            risk_emphasis=chapter.brief_risk_emphasis,
            asked_marisol=chapter.brief_asked_marisol,
            body_summary=body,
            source_labels=list(self.scenario.data_sources),
            communication_record_id=communication.record_id,
        )
        chapter.market_brief = brief
        chapter.communication_record_ids.append(communication.record_id)
        chapter.current_day = 2
        chapter.current_scene_index = 0
        state.current_date = self.scenario.day_2_date
        state.record(
            phase="system",
            event_type="market_brief_created",
            source_id=brief.brief_id,
            message="The structured morning note was preserved as evidence.",
            changes={"communication_record_id": communication.record_id},
        )
        return brief

    def create_authorization(self, state: GameState) -> TradeAuthorization:
        chapter = self._chapter(state)
        if chapter.market_brief is None:
            raise ValueError("market brief must exist before authorization")
        if chapter.authorization is not None:
            return chapter.authorization
        approved_at = datetime.combine(
            self.scenario.day_2_date,
            time(9, 0),
            tzinfo=CHICAGO_TZ,
        )
        authorization = TradeAuthorization(
            authorization_id="auth_live_week_ten_short",
            contract_id=self.scenario.contract_id,
            side=OrderSide.SELL,
            maximum_quantity=self.scenario.approved_contracts,
            commercial_purpose=self.scenario.authorization_purpose,
            supported_physical_quantity_mmbtu=self.scenario.supported_volume_mmbtu,
            minimum_hedge_ratio=Decimal("0.9"),
            maximum_hedge_ratio=Decimal("1.0"),
            approver_id=self.scenario.approver_id,
            approved_at=approved_at,
            expires_at=datetime.combine(
                self.scenario.day_2_date,
                time(16, 0),
                tzinfo=CHICAGO_TZ,
            ),
            related_market_brief_id=chapter.market_brief.brief_id,
            related_hedge_memo_id=self.scenario.hedge_memo_id,
            status=AuthorizationStatus.ACTIVE,
        )
        chapter.authorization = authorization
        chapter.approval_ids.append(authorization.authorization_id)
        return authorization

    def recommend_and_execute_order(self, state: GameState) -> TradeOrder:
        chapter = self._chapter(state)
        if chapter.recommended_order_type is None:
            raise ValueError("select an order type before preparing the order")
        authorization = self.create_authorization(state)
        if chapter.order is not None:
            return chapter.order
        order_price = {
            OrderType.MARKET: None,
            OrderType.LIMIT: Decimal("5.205"),
            OrderType.STOP: Decimal("5.185"),
        }[chapter.recommended_order_type]
        submitted_at = datetime.combine(
            self.scenario.day_2_date,
            time(9, 4),
            tzinfo=CHICAGO_TZ,
        )
        chapter.recommendation = OrderRecommendation(
            recommendation_id="recommendation_live_week",
            recommended_at=submitted_at,
            recommended_by_id="player",
            contract_id=self.scenario.contract_id,
            side=OrderSide.SELL,
            quantity=self.scenario.approved_contracts,
            order_type=chapter.recommended_order_type,
            order_price=order_price,
            rationale=(
                "Reduce benchmark price risk on the supported 100,000 MMBtu "
                "forecast sale; do not rely on unsupported additional volume."
            ),
            related_market_brief_id=chapter.market_brief.brief_id,
        )
        submitted = TradeOrder(
            order_id="order_live_week_ten_short",
            account_id=self.scenario.account_id,
            book_id=self.scenario.book_id,
            contract_id=self.scenario.contract_id,
            side=OrderSide.SELL,
            quantity=self.scenario.approved_contracts,
            order_type=chapter.recommended_order_type,
            order_price=order_price,
            submitted_at=submitted_at,
            authorized_quantity=authorization.maximum_quantity,
            authorized_user_id=authorization.approver_id,
            transmitting_user_id=self.scenario.transmitting_user_id,
            status=OrderStatus.SUBMITTED,
            related_physical_exposure_id=self.scenario.physical_exposure_id,
            related_hedge_memo_id=self.scenario.hedge_memo_id,
            related_authorization_id=authorization.authorization_id,
        )
        order = OrderFillEngine.execute(submitted, self.scenario.intraday_path)
        if order.status != OrderStatus.FILLED:
            raise ValueError("the configured live-book order did not fill")
        chapter.order = order
        chapter.execution = ExecutionRecord(
            execution_id="execution_live_week_eleven",
            order_id=order.order_id,
            contract_id=order.contract_id,
            side=order.side,
            quantity=self.scenario.confirmed_contracts,
            fill_price=order.fill_price,
            fill_timestamp=order.fill_timestamp,
            transmitting_user_id=self.scenario.transmitting_user_id,
        )
        chapter.confirmation = FCMConfirmation(
            confirmation_id="fcm_confirmation_live_week_eleven",
            order_id=order.order_id,
            execution_id=chapter.execution.execution_id,
            account_id=order.account_id,
            contract_id=order.contract_id,
            side=order.side,
            quantity=self.scenario.confirmed_contracts,
            fill_price=order.fill_price,
            confirmed_at=order.fill_timestamp,
            fcm_name="Lakefront FCM",
        )
        self._open_position_and_blotter(state)
        self._settle(
            state,
            settlement_id="eleventh_day_2_settlement",
            settlement_date=self.scenario.day_2_date,
            settlement_price=self.scenario.day_2_settlement_price,
        )
        chapter.current_day = 3
        chapter.current_scene_index = 0
        state.current_date = self.scenario.day_3_date
        return order

    def offset_extra_contract(self, state: GameState) -> OffsetTrade:
        chapter = self._chapter(state)
        position = self._position(chapter)
        if position.offset_trade is not None:
            return position.offset_trade
        if not chapter.chapter_flags.get("offset_approved"):
            raise ValueError("the junior analyst needs approval before an offset")
        if position.open_contracts < 1:
            raise ValueError("there is no extra contract to offset")
        reconciliation = self._ensure_reconciliation(chapter)
        approval_id = "approval_offset_eleventh_contract"
        approval_decision_id = next(
            (
                item
                for item in reversed(chapter.decisions)
                if item
                in {
                    "ec_offset_with_formal_approval",
                    "ec_request_and_obtain_offset_approval",
                }
            ),
            "ec_offset_with_formal_approval",
        )
        if not any(item.approval_id == approval_id for item in chapter.approvals):
            chapter.approvals.append(
                CorrectiveTradeApprovalRecord(
                    approval_id=approval_id,
                    approved_at=datetime.combine(
                        self.scenario.day_3_date,
                        time(10, 25),
                        tzinfo=CHICAGO_TZ,
                    ),
                    decision_id=approval_decision_id,
                    approver_id=self.scenario.approver_id,
                    reconciliation_id=reconciliation.reconciliation_id,
                    original_execution_id=chapter.execution.execution_id,
                    side=OrderSide.BUY,
                    quantity=1,
                    approved=True,
                )
            )
        if approval_id not in chapter.approval_ids:
            chapter.approval_ids.append(approval_id)
        preserved = position.cumulative_pnl
        pnl = futures_daily_pnl(
            side=PositionSide.SHORT,
            previous_settlement=position.current_price,
            current_settlement=self.scenario.offset_price,
            contract_size_mmbtu=position.contract_size_mmbtu,
            contracts=1,
        )
        self._apply_variation(
            state,
            pnl,
            "eleventh_offset_variation",
            "Variation settlement on the one-contract corrective offset",
        )
        position.cumulative_pnl = money(position.cumulative_pnl + pnl)
        position.extra_contract_pnl = money(position.extra_contract_pnl + pnl)
        position.open_contracts -= 1
        position.margin.initial_requirement = money(
            self.scenario.initial_margin_per_contract * Decimal(position.open_contracts)
        )
        position.margin.maintenance_requirement = money(
            self.scenario.maintenance_margin_per_contract * Decimal(position.open_contracts)
        )
        releasable = max(
            Decimal("0"),
            money(position.margin.balance - position.margin.initial_requirement),
        )
        journal_ids = ["txn_eleventh_offset_variation"]
        if releasable:
            state.corporate_cash = money(state.corporate_cash + releasable)
            position.margin.balance = money(position.margin.balance - releasable)
            position.margin.total_released = money(position.margin.total_released + releasable)
            self._post_pattern(
                state,
                "margin_release",
                releasable,
                "txn_eleventh_margin_release_offset",
                "Release eligible FCM margin after the approved one-contract offset",
                "offset_eleventh_contract",
            )
            journal_ids.append("txn_eleventh_margin_release_offset")
        position.current_hedge_ratio = hedge_ratio(
            contracts=position.open_contracts,
            contract_size_mmbtu=position.contract_size_mmbtu,
            physical_quantity_mmbtu=chapter.physical_forecast.supported_volume_mmbtu,
        )
        offset = OffsetTrade(
            trade_id="offset_eleventh_contract",
            original_execution_id=chapter.execution.execution_id,
            authorization_id=approval_id,
            side=OrderSide.BUY,
            quantity=1,
            price=self.scenario.offset_price,
            executed_at=datetime.combine(
                self.scenario.day_3_date,
                time(10, 30),
                tzinfo=CHICAGO_TZ,
            ),
            pnl_since_last_settlement=pnl,
            cumulative_pnl_preserved=preserved,
            contracts_remaining=position.open_contracts,
            margin_released=releasable,
            journal_transaction_ids=journal_ids,
        )
        position.offset_trade = offset
        chapter.chapter_flags["extra_contract_offset"] = True
        self._set_blotter_status(
            chapter,
            ReconciliationStatus.CORRECTED,
            "evelyn_marsh",
            "Approved offset recorded prospectively; original execution retained.",
        )
        self.assert_reconciles(state)
        return offset

    def finalize_exception(self, state: GameState) -> None:
        chapter = self._chapter(state)
        if chapter.physical_forecast.revealed:
            return
        if chapter.chapter_flags.get("offset_requested"):
            self.offset_extra_contract(state)
        elif chapter.chapter_flags.get("formal_escalation"):
            self._set_blotter_status(
                chapter,
                ReconciliationStatus.ESCALATED,
                "evelyn_marsh",
                "Formal quantity exception opened; the eleven-contract position remains.",
            )
        elif chapter.chapter_flags.get("certified_unresolved"):
            chapter.blotter.certification_record_id = "comm_ec_unresolved_certification"
            self._set_blotter_status(
                chapter,
                ReconciliationStatus.CERTIFIED_WITH_EXCEPTION,
                "player",
                "Player certified the blotter while the quantity exception remained open.",
            )
        elif chapter.chapter_flags.get("accepted_cal_explanation"):
            self._set_blotter_status(
                chapter,
                ReconciliationStatus.AWAITING_PHYSICAL_SUPPORT,
                "player",
                "Cal's additional-volume explanation is not yet supported.",
            )
        else:
            self._set_blotter_status(
                chapter,
                ReconciliationStatus.UNRESOLVED,
                "player",
                "Original records retained privately; no formal resolution was completed.",
            )
        self._reveal_physical_outcome(state)
        if (
            chapter.chapter_flags.get("accepted_cal_explanation")
            and chapter.physical_forecast.outcome == PhysicalVolumeOutcome.ARRIVES
        ):
            self._set_blotter_status(
                chapter,
                ReconciliationStatus.UNRESOLVED,
                "player",
                "Later physical support matched the open volume but did not cure "
                "the original authorization exception.",
                changed_at=datetime.combine(
                    self.scenario.day_3_date,
                    time(14, 5),
                    tzinfo=CHICAGO_TZ,
                ),
            )
        final_price = (
            self.scenario.day_3_arrives_settlement_price
            if chapter.physical_forecast.outcome == PhysicalVolumeOutcome.ARRIVES
            else self.scenario.day_3_fails_settlement_price
        )
        self._settle(
            state,
            settlement_id="eleventh_day_3_settlement",
            settlement_date=self.scenario.day_3_date,
            settlement_price=final_price,
        )
        position = self._position(chapter)
        eventual_volume = chapter.physical_forecast.eventual_supported_volume_mmbtu
        position.current_hedge_ratio = hedge_ratio(
            contracts=position.open_contracts,
            contract_size_mmbtu=position.contract_size_mmbtu,
            physical_quantity_mmbtu=eventual_volume,
        )
        chapter.blotter.supported_physical_volume_mmbtu = eventual_volume
        chapter.blotter.hedge_ratio = position.current_hedge_ratio
        self.assert_reconciles(state)

    def complete_chapter(self, state: GameState) -> EleventhOutcome:
        chapter = self._chapter(state)
        if not chapter.physical_forecast.revealed:
            raise ValueError("resolve the physical outcome before completing the chapter")
        outcome = self._derive_outcome(chapter)
        chapter.outcome = outcome
        chapter.completed = True
        chapter.current_scene_index = 0
        state.record(
            phase="system",
            event_type="eleventh_contract_completed",
            source_id=self.scenario.id,
            message=f"Analyst Case File outcome: {outcome.value}.",
            changes={"outcome": outcome.value},
        )
        self.assert_reconciles(state)
        return outcome

    def authorization_exception(self, state: GameState) -> bool:
        chapter = self._chapter(state)
        if chapter.authorization is None or chapter.execution is None:
            raise ValueError("authorization and execution are required")
        return (
            chapter.execution.quantity > chapter.authorization.maximum_quantity
            or chapter.execution.side != chapter.authorization.side
            or chapter.execution.contract_id != chapter.authorization.contract_id
        )

    def confirmation_matches_execution(self, state: GameState) -> bool:
        chapter = self._chapter(state)
        if chapter.execution is None or chapter.confirmation is None:
            raise ValueError("execution and confirmation are required")
        execution = chapter.execution
        confirmation = chapter.confirmation
        return (
            execution.order_id == confirmation.order_id
            and execution.execution_id == confirmation.execution_id
            and execution.contract_id == confirmation.contract_id
            and execution.side == confirmation.side
            and execution.quantity == confirmation.quantity
            and execution.fill_price == confirmation.fill_price
        )

    def ensure_reconciliation(self, state: GameState) -> TradeReconciliationRecord:
        """Rebuild the typed link for an early v5 save that predates the record."""
        return self._ensure_reconciliation(self._chapter(state))

    def assert_reconciles(self, state: GameState) -> None:
        chapter = self._chapter(state)
        position = self._position(chapter)
        reconciliation = self._ensure_reconciliation(chapter)
        activity = state.ledger.account_activity()
        cash_debits, cash_credits = activity.get("1000", (Decimal("0"), Decimal("0")))
        ledger_cash = money(cash_debits - cash_credits)
        if ledger_cash != money(state.corporate_cash):
            raise ValueError(
                f"Eleventh Contract operating cash does not reconcile: "
                f"{ledger_cash} != {state.corporate_cash}"
            )
        margin_debits, margin_credits = activity.get("1050", (Decimal("0"), Decimal("0")))
        ledger_margin = money(margin_debits - margin_credits)
        if ledger_margin != money(position.margin.balance):
            raise ValueError(
                f"Eleventh Contract FCM margin does not reconcile: "
                f"{ledger_margin} != {position.margin.balance}"
            )
        expected_open = chapter.confirmation.quantity - (
            position.offset_trade.quantity if position.offset_trade else 0
        )
        if position.open_contracts != expected_open:
            raise ValueError("open position does not reconcile to confirmation and offsets")
        expected_initial = money(
            self.scenario.initial_margin_per_contract * Decimal(position.open_contracts)
        )
        if position.margin.initial_requirement != expected_initial:
            raise ValueError("initial margin requirement does not reconcile to open contracts")
        if reconciliation.authorization_id != chapter.authorization.authorization_id:
            raise ValueError("reconciliation does not link to the authorization")
        if reconciliation.order_id != chapter.order.order_id:
            raise ValueError("reconciliation does not link to the order")
        if reconciliation.execution_id != chapter.execution.execution_id:
            raise ValueError("reconciliation does not link to the execution")
        if reconciliation.confirmation_id != chapter.confirmation.confirmation_id:
            raise ValueError("reconciliation does not link to the FCM confirmation")
        if reconciliation.current_status != chapter.blotter.status:
            raise ValueError("reconciliation status does not agree with the blotter")
        if any(
            item.communication_record_id not in chapter.notification_record_ids
            or item.reconciliation_id != reconciliation.reconciliation_id
            for item in chapter.notifications
        ):
            raise ValueError("exception notification does not reconcile to its evidence")
        if any(
            item.approval_id not in chapter.approval_ids
            or item.reconciliation_id != reconciliation.reconciliation_id
            or item.original_execution_id != chapter.execution.execution_id
            for item in chapter.approvals
        ):
            raise ValueError("corrective approval does not reconcile to the original execution")
        if any(entry.total_debits != entry.total_credits for entry in state.ledger.entries):
            raise ValueError("an unbalanced journal entry reached the ledger")

    def _open_position_and_blotter(self, state: GameState) -> None:
        chapter = self._chapter(state)
        execution = chapter.execution
        confirmation = chapter.confirmation
        authorization = chapter.authorization
        margin_deposit = money(
            self.scenario.initial_margin_per_contract * Decimal(execution.quantity)
        )
        if state.corporate_cash < margin_deposit:
            raise ValueError("operating cash cannot fund the live-book initial margin")
        state.corporate_cash = money(state.corporate_cash - margin_deposit)
        self._post_pattern(
            state,
            "initial_margin",
            margin_deposit,
            "txn_eleventh_initial_margin",
            "Deposit initial margin for eleven confirmed NG contracts",
            execution.execution_id,
        )
        ratio = hedge_ratio(
            contracts=execution.quantity,
            contract_size_mmbtu=self.contract.contract_size_mmbtu,
            physical_quantity_mmbtu=self.scenario.supported_volume_mmbtu,
        )
        position = LiveTradingPosition(
            contract_id=self.scenario.contract_id,
            contract_month=self.scenario.contract_month,
            side=PositionSide.SHORT,
            original_contracts=execution.quantity,
            open_contracts=execution.quantity,
            contract_size_mmbtu=self.contract.contract_size_mmbtu,
            entry_price=execution.fill_price,
            current_price=execution.fill_price,
            initial_hedge_ratio=ratio,
            current_hedge_ratio=ratio,
            margin=MarginAccount(
                balance=margin_deposit,
                initial_requirement=margin_deposit,
                maintenance_requirement=money(
                    self.scenario.maintenance_margin_per_contract * Decimal(execution.quantity)
                ),
                total_initial_deposit=margin_deposit,
            ),
            journal_transaction_ids=["txn_eleventh_initial_margin"],
        )
        chapter.position = position
        original_status = (
            ReconciliationStatus.QUANTITY_EXCEPTION
            if execution.quantity > authorization.maximum_quantity
            else ReconciliationStatus.MATCHED
        )
        timestamp = confirmation.confirmed_at
        chapter.blotter = TradeBlotterEntry(
            blotter_id="blotter_eleventh_contract",
            order_id=chapter.order.order_id,
            authorization_id=authorization.authorization_id,
            execution_id=execution.execution_id,
            confirmation_id=confirmation.confirmation_id,
            side=execution.side,
            internal_quantity=chapter.order.fill_quantity,
            confirmed_quantity=confirmation.quantity,
            fill_price=confirmation.fill_price,
            current_settlement_price=confirmation.fill_price,
            margin_requirement=margin_deposit,
            supported_physical_volume_mmbtu=self.scenario.supported_volume_mmbtu,
            hedge_ratio=ratio,
            exception_contracts=max(0, confirmation.quantity - authorization.maximum_quantity),
            original_status=original_status,
            status=original_status,
            status_history=[
                BlotterStatusChange(
                    changed_at=timestamp,
                    status=original_status,
                    changed_by_id="system",
                    note=(
                        "FCM confirmation shows eleven contracts against a ten-contract "
                        "authorization and internal order."
                    ),
                )
            ],
        )
        chapter.original_blotter_status = original_status
        reconciliation = TradeReconciliationRecord(
            reconciliation_id="reconciliation_eleventh_contract",
            prepared_at=timestamp,
            prepared_by_id="player",
            authorization_id=authorization.authorization_id,
            order_id=chapter.order.order_id,
            execution_id=execution.execution_id,
            confirmation_id=confirmation.confirmation_id,
            authorized_quantity=authorization.maximum_quantity,
            ordered_quantity=chapter.order.fill_quantity,
            executed_quantity=execution.quantity,
            confirmed_quantity=confirmation.quantity,
            exception_contracts=max(
                0,
                confirmation.quantity - authorization.maximum_quantity,
            ),
            authorization_exception=self.authorization_exception(state),
            confirmation_matches_execution=self.confirmation_matches_execution(state),
            original_status=original_status,
            current_status=original_status,
            related_evidence_record_ids=[chapter.market_brief.communication_record_id],
        )
        chapter.blotter.reconciliation_id = reconciliation.reconciliation_id
        chapter.reconciliation = reconciliation
        self.assert_reconciles(state)

    def _settle(
        self,
        state: GameState,
        *,
        settlement_id: str,
        settlement_date,
        settlement_price: Decimal,
    ) -> ChapterSettlement:
        chapter = self._chapter(state)
        position = self._position(chapter)
        if any(item.settlement_id == settlement_id for item in position.settlements):
            return next(
                item for item in position.settlements if item.settlement_id == settlement_id
            )
        previous = position.current_price
        contracts = position.open_contracts
        total_pnl = futures_daily_pnl(
            side=position.side,
            previous_settlement=previous,
            current_settlement=settlement_price,
            contract_size_mmbtu=position.contract_size_mmbtu,
            contracts=contracts,
        )
        extra_pnl = (
            futures_daily_pnl(
                side=position.side,
                previous_settlement=previous,
                current_settlement=settlement_price,
                contract_size_mmbtu=position.contract_size_mmbtu,
                contracts=1,
            )
            if position.offset_trade is None and contracts == 11
            else Decimal("0")
        )
        self._apply_variation(
            state,
            total_pnl,
            settlement_id,
            f"Daily variation settlement for {contracts} live-book contracts",
        )
        position.margin.total_variation_margin = money(
            position.margin.total_variation_margin + total_pnl
        )
        position.cumulative_pnl = money(position.cumulative_pnl + total_pnl)
        position.extra_contract_pnl = money(position.extra_contract_pnl + extra_pnl)
        position.current_price = settlement_price
        call = margin_call_amount(
            balance=position.margin.balance,
            initial_requirement=position.margin.initial_requirement,
            maintenance_requirement=position.margin.maintenance_requirement,
        )
        if call:
            if state.corporate_cash < call:
                raise ValueError("operating cash cannot fund the live-book margin call")
            state.corporate_cash = money(state.corporate_cash - call)
            position.margin.balance = money(position.margin.balance + call)
            position.margin.total_additional_deposits = money(
                position.margin.total_additional_deposits + call
            )
            self._post_pattern(
                state,
                "margin_call",
                call,
                f"txn_{settlement_id}_margin_call",
                "Fund live-book maintenance-margin call",
                settlement_id,
            )
        result = ChapterSettlement(
            settlement_id=settlement_id,
            settlement_date=settlement_date,
            previous_price=previous,
            settlement_price=settlement_price,
            contracts=contracts,
            total_pnl=total_pnl,
            extra_contract_pnl=extra_pnl,
            margin_balance_after=position.margin.balance,
        )
        position.settlements.append(result)
        chapter.blotter.current_settlement_price = settlement_price
        chapter.blotter.daily_pnl = total_pnl
        chapter.blotter.margin_requirement = position.margin.initial_requirement
        self.assert_reconciles(state)
        return result

    def _apply_variation(
        self,
        state: GameState,
        pnl: Decimal,
        source_id: str,
        description: str,
    ) -> None:
        if pnl == 0:
            return
        position = self._position(self._chapter(state))
        position.margin.balance = money(position.margin.balance + pnl)
        pattern = "futures_gain" if pnl > 0 else "futures_loss"
        transaction_id = f"txn_{source_id}"
        self._post_pattern(
            state,
            pattern,
            abs(pnl),
            transaction_id,
            description,
            source_id,
        )
        position.journal_transaction_ids.append(transaction_id)

    def _post_pattern(
        self,
        state: GameState,
        pattern_key: str,
        amount: Decimal,
        transaction_id: str,
        description: str,
        source_id: str,
    ) -> None:
        pattern = self.content.journal_pattern(self.journal_patterns[pattern_key])
        entry = JournalEntry(
            transaction_id=transaction_id,
            entry_date=state.current_date,
            description=description,
            source_id=source_id,
            lines=[
                JournalLine(account=pattern.debit_account, debit=money(amount)),
                JournalLine(account=pattern.credit_account, credit=money(amount)),
            ],
        )
        state.ledger.post(entry, self.content.valid_accounts)

    def _reveal_physical_outcome(self, state: GameState) -> None:
        chapter = self._chapter(state)
        forecast = chapter.physical_forecast
        forecast.revealed = True
        forecast.outcome_resolved_at = datetime.combine(
            self.scenario.day_3_date,
            time(14, 0),
            tzinfo=CHICAGO_TZ,
        )
        if forecast.outcome == PhysicalVolumeOutcome.ARRIVES:
            forecast.support_obtained_at = forecast.outcome_resolved_at
            forecast.eventual_supported_volume_mmbtu = (
                forecast.supported_volume_mmbtu + forecast.possible_additional_volume_mmbtu
            )
            forecast.support_document_ids.append("final_nomination_additional_10000")
            final_henry = self.scenario.day_3_arrives_settlement_price
            final_basis = self.scenario.day_3_arrives_basis
        else:
            forecast.eventual_supported_volume_mmbtu = forecast.supported_volume_mmbtu
            final_henry = self.scenario.day_3_fails_settlement_price
            final_basis = self.scenario.day_3_fails_basis
        initial_regional = self.scenario.initial_henry_hub_price + self.scenario.chicago_basis
        final_regional = final_henry + final_basis
        chapter.physical_economic_pnl = money(
            (final_regional - initial_regional) * forecast.eventual_supported_volume_mmbtu
        )

    def _set_blotter_status(
        self,
        chapter: EleventhContractState,
        status: ReconciliationStatus,
        reviewer_id: str,
        note: str,
        *,
        changed_at: datetime | None = None,
    ) -> None:
        blotter = chapter.blotter
        reconciliation = self._ensure_reconciliation(chapter)
        blotter.status = status
        blotter.reviewer_id = reviewer_id
        blotter.status_history.append(
            BlotterStatusChange(
                changed_at=changed_at
                or datetime.combine(
                    self.scenario.day_3_date,
                    time(12, 0),
                    tzinfo=CHICAGO_TZ,
                ),
                status=status,
                changed_by_id=reviewer_id,
                note=note,
            )
        )
        reconciliation.current_status = status
        reconciliation.certification_record_id = blotter.certification_record_id
        if (
            blotter.certification_record_id is not None
            and blotter.certification_record_id not in reconciliation.related_evidence_record_ids
        ):
            reconciliation.related_evidence_record_ids.append(blotter.certification_record_id)

    @staticmethod
    def _ensure_reconciliation(
        chapter: EleventhContractState,
    ) -> TradeReconciliationRecord:
        if chapter.reconciliation is not None:
            return chapter.reconciliation
        if any(
            item is None
            for item in (
                chapter.authorization,
                chapter.order,
                chapter.execution,
                chapter.confirmation,
                chapter.blotter,
            )
        ):
            raise ValueError("the complete trade lifecycle is required for reconciliation")
        authorization = chapter.authorization
        order = chapter.order
        execution = chapter.execution
        confirmation = chapter.confirmation
        blotter = chapter.blotter
        reconciliation = TradeReconciliationRecord(
            reconciliation_id=blotter.reconciliation_id or "reconciliation_eleventh_contract",
            prepared_at=blotter.status_history[0].changed_at,
            prepared_by_id="player",
            authorization_id=authorization.authorization_id,
            order_id=order.order_id,
            execution_id=execution.execution_id,
            confirmation_id=confirmation.confirmation_id,
            authorized_quantity=authorization.maximum_quantity,
            ordered_quantity=order.fill_quantity,
            executed_quantity=execution.quantity,
            confirmed_quantity=confirmation.quantity,
            exception_contracts=max(
                0,
                confirmation.quantity - authorization.maximum_quantity,
            ),
            authorization_exception=execution.quantity > authorization.maximum_quantity,
            confirmation_matches_execution=(
                execution.order_id == confirmation.order_id
                and execution.execution_id == confirmation.execution_id
                and execution.contract_id == confirmation.contract_id
                and execution.side == confirmation.side
                and execution.quantity == confirmation.quantity
                and execution.fill_price == confirmation.fill_price
            ),
            original_status=blotter.original_status,
            current_status=blotter.status,
            certification_record_id=blotter.certification_record_id,
            related_evidence_record_ids=[
                item
                for item in (
                    (
                        chapter.market_brief.communication_record_id
                        if chapter.market_brief is not None
                        else None
                    ),
                    blotter.certification_record_id,
                )
                if item is not None
            ],
        )
        blotter.reconciliation_id = reconciliation.reconciliation_id
        chapter.reconciliation = reconciliation
        return reconciliation

    @staticmethod
    def _derive_outcome(chapter: EleventhContractState) -> EleventhOutcome:
        flags = chapter.chapter_flags
        position = chapter.position
        if position.offset_trade is not None and flags.get("formal_escalation"):
            return EleventhOutcome.CLEAN_CORRECTION
        if flags.get("accepted_cal_explanation") or flags.get("certified_unresolved"):
            return EleventhOutcome.CALS_ANALYST
        if (
            flags.get("quiet_file")
            and chapter.physical_forecast.outcome == PhysicalVolumeOutcome.ARRIVES
        ):
            return EleventhOutcome.QUIET_FILE
        if chapter.physical_forecast.outcome == PhysicalVolumeOutcome.ARRIVES:
            return EleventhOutcome.SUPPORTED_BUT_LATE
        if position.extra_contract_pnl > 0:
            return EleventhOutcome.LUCKY_NOT_AUTHORIZED
        return EleventhOutcome.ELEVEN_AGAINST_TEN

    @staticmethod
    def _apply_prior_relationships(state: GameState, relationships: dict[str, int]) -> None:
        decisions = set(state.decisions)
        if "preserve_scheduling_qualification" in decisions:
            relationships["marisol_vega"] += 1
            relationships["evelyn_marsh"] += 1
        if "remove_qualification_for_cal" in decisions:
            relationships["cal_rourke"] += 1
            relationships["marisol_vega"] -= 1
        if "request_meter_support" in decisions:
            relationships["marisol_vega"] += 1
        if "escalate_to_controller" in decisions:
            relationships["evelyn_marsh"] += 1
        if "write_accurate_hedge_memo" in decisions:
            relationships["evelyn_marsh"] += 1
        if "copy_cal_vague_description" in decisions:
            relationships["cal_rourke"] += 1
            relationships["evelyn_marsh"] -= 1
        if state.treasury is not None:
            notification = state.treasury.notification_choice
            if notification is not None and notification.value == "notify_immediately":
                relationships["evelyn_marsh"] += 1
            if notification is not None and notification.value == "delay_notification":
                relationships["evelyn_marsh"] -= 1
            funding = state.treasury.funding_decision
            if funding is not None and funding.missed:
                relationships["evelyn_marsh"] -= 1

    @staticmethod
    def _chapter(state: GameState) -> EleventhContractState:
        if state.eleventh_contract is None:
            raise ValueError("the Eleventh Contract chapter has not started")
        return state.eleventh_contract

    @staticmethod
    def _position(chapter: EleventhContractState) -> LiveTradingPosition:
        if chapter.position is None:
            raise ValueError("the live trading position has not been opened")
        return chapter.position
