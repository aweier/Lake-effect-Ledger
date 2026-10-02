"""Exact domain logic for hedging, daily settlement, margin, and liquidity."""

from __future__ import annotations

from decimal import Decimal

from lake_effect_ledger.accounting.models import JournalEntry, JournalLine
from lake_effect_ledger.commodity.models import (
    DailyMarketPrice,
    DailySettlementResult,
    FuturesPosition,
    HedgeBookState,
    HedgeOutcome,
    HedgeTicket,
    HedgeTicketPreview,
    MarginAccount,
    MarginCall,
    PhysicalDirection,
    PhysicalExposure,
    PositionReductionTrade,
    PositionSide,
    money,
    price,
)
from lake_effect_ledger.learning.models import TrajectoryTag
from lake_effect_ledger.narrative.models import (
    ContentBundle,
    HedgeLevelDefinition,
)
from lake_effect_ledger.state import GameState

DEFAULT_HEDGE_SCENARIO_ID = "episode_01_hedge_book"


class InsufficientOperatingCashError(ValueError):
    """Raised when even the initial margin deposit cannot be funded."""


def regional_price(henry_hub_price: Decimal, regional_basis: Decimal) -> Decimal:
    return price(henry_hub_price + regional_basis)


def futures_daily_pnl(
    *,
    side: PositionSide,
    previous_settlement: Decimal,
    current_settlement: Decimal,
    contract_size_mmbtu: Decimal,
    contracts: int,
) -> Decimal:
    if contracts < 0:
        raise ValueError("contract count cannot be negative")
    movement = current_settlement - previous_settlement
    signed_movement = movement if side == PositionSide.LONG else -movement
    return money(signed_movement * contract_size_mmbtu * contracts)


def futures_tick_value(*, minimum_tick: Decimal, contract_size_mmbtu: Decimal) -> Decimal:
    if minimum_tick <= 0 or contract_size_mmbtu <= 0:
        raise ValueError("tick and contract size must be positive")
    return money(minimum_tick * contract_size_mmbtu)


def hedge_ratio(
    *,
    contracts: int,
    contract_size_mmbtu: Decimal,
    physical_quantity_mmbtu: Decimal,
) -> Decimal:
    if contracts < 0 or contract_size_mmbtu <= 0 or physical_quantity_mmbtu <= 0:
        raise ValueError("hedge-ratio inputs must be positive, except contracts may be zero")
    return (Decimal(contracts) * contract_size_mmbtu / physical_quantity_mmbtu).quantize(
        Decimal("0.0001")
    )


def contract_count(
    *,
    physical_quantity_mmbtu: Decimal,
    contract_size_mmbtu: Decimal,
) -> Decimal:
    if physical_quantity_mmbtu <= 0 or contract_size_mmbtu <= 0:
        raise ValueError("contract-count inputs must be positive")
    count = physical_quantity_mmbtu / contract_size_mmbtu
    if count != count.to_integral_value():
        raise ValueError("physical quantity does not map to a whole contract count")
    return count


def buyer_physical_purchase_cost_variance(
    *,
    initial_regional_price: Decimal,
    final_regional_price: Decimal,
    physical_quantity_mmbtu: Decimal,
) -> Decimal:
    if initial_regional_price <= 0 or final_regional_price <= 0:
        raise ValueError("regional prices must be positive")
    if physical_quantity_mmbtu <= 0:
        raise ValueError("physical quantity must be positive")
    return money((initial_regional_price - final_regional_price) * physical_quantity_mmbtu)


def combined_economic_result(
    *,
    physical_variance: Decimal,
    futures_result: Decimal,
) -> Decimal:
    return money(physical_variance + futures_result)


def contract_month_spread(*, nearby_price: Decimal, deferred_price: Decimal) -> Decimal:
    """Return deferred minus nearby for a two-month futures curve."""

    return price(deferred_price - nearby_price)


def delivery_contract_value(
    *,
    settlement_price: Decimal,
    contract_size_mmbtu: Decimal,
    contracts: int,
) -> Decimal:
    """Return the simplified contract value used by the Chapter 220 delivery example."""

    if settlement_price <= 0 or contract_size_mmbtu <= 0 or contracts < 0:
        raise ValueError("delivery contract value inputs must be positive")
    return money(settlement_price * contract_size_mmbtu * Decimal(contracts))


def physical_pnl_components(
    exposure: PhysicalExposure,
    market: DailyMarketPrice,
) -> tuple[Decimal, Decimal, Decimal]:
    direction_sign = Decimal("1") if exposure.direction == PhysicalDirection.LONG else Decimal("-1")
    henry_component = money(
        direction_sign
        * (market.henry_hub_price - exposure.original_henry_hub_price)
        * exposure.quantity_mmbtu
    )
    basis_component = money(
        direction_sign * (market.chicago_basis - exposure.original_basis) * exposure.quantity_mmbtu
    )
    physical_pnl = money(henry_component + basis_component)
    return henry_component, basis_component, physical_pnl


def margin_call_amount(
    *,
    balance: Decimal,
    initial_requirement: Decimal,
    maintenance_requirement: Decimal,
) -> Decimal:
    if min(balance, initial_requirement, maintenance_requirement) < 0:
        raise ValueError("margin values cannot be negative")
    if maintenance_requirement > initial_requirement:
        raise ValueError("maintenance margin cannot exceed initial margin")
    return (
        money(initial_requirement - balance) if balance < maintenance_requirement else Decimal("0")
    )


class CommodityEngine:
    def __init__(
        self,
        content: ContentBundle,
        scenario_id: str = DEFAULT_HEDGE_SCENARIO_ID,
        market_path_id: str | None = None,
    ) -> None:
        self.content = content
        self.scenario = content.hedge_scenario(scenario_id)
        self.contract = content.commodity_contract(self.scenario.contract_id)
        if (
            market_path_id is not None
            and market_path_id not in self.scenario.selectable_price_path_ids
        ):
            valid = ", ".join(self.scenario.selectable_price_path_ids)
            raise ValueError(f"market path must be one of: {valid}")
        self.market_path_override = market_path_id
        self.price_path = content.commodity_price_path(
            market_path_id or self.scenario.price_path_id
        )

    def hedge_level(self, hedge_level_id: str) -> HedgeLevelDefinition:
        try:
            return next(item for item in self.scenario.hedge_levels if item.id == hedge_level_id)
        except StopIteration as error:
            valid = ", ".join(item.id for item in self.scenario.hedge_levels)
            raise ValueError(f"unknown hedge level {hedge_level_id}; expected {valid}") from error

    def preview_hedge(self, state: GameState, hedge_level_id: str) -> HedgeTicketPreview:
        level = self.hedge_level(hedge_level_id)
        contracts = self._contract_count(level)
        hedged_quantity = self.contract.contract_size_mmbtu * contracts
        speculative_quantity = max(
            Decimal("0"),
            hedged_quantity - self.scenario.physical_quantity_mmbtu,
        )
        initial_margin = money(self.scenario.initial_margin_per_contract * Decimal(contracts))
        remaining_cash = money(state.corporate_cash - initial_margin)
        if level.hedge_ratio == 0:
            risk_reduced = "No Henry Hub price risk is reduced."
        else:
            risk_reduced = (
                f"Short futures offset Henry Hub price movement on {hedged_quantity:,.0f} MMBtu."
            )
        unhedged_quantity = self.scenario.physical_quantity_mmbtu - min(
            hedged_quantity,
            self.scenario.physical_quantity_mmbtu,
        )
        risk_remaining = (
            "Chicago basis remains unhedged. "
            f"{unhedged_quantity:,.0f} "
            "MMBtu of Henry Hub exposure also remains unhedged."
        )
        warning = None
        if speculative_quantity > 0:
            warning = (
                f"OVERHEDGE: {speculative_quantity:,.0f} MMBtu exceeds the documented "
                "physical exposure and is speculative."
            )
        return HedgeTicketPreview(
            hedge_level_id=level.id,
            label=level.label,
            side=self.scenario.futures_side,
            contracts=contracts,
            hedge_ratio=level.hedge_ratio,
            hedged_quantity_mmbtu=hedged_quantity,
            speculative_quantity_mmbtu=speculative_quantity,
            initial_margin_required=initial_margin,
            operating_cash_remaining=remaining_cash,
            liquidity_headroom_remaining=money(
                remaining_cash - self.scenario.minimum_operating_reserve
            ),
            risk_reduced=risk_reduced,
            risk_remaining=risk_remaining,
            overhedge_warning=warning,
        )

    def open_hedge(self, state: GameState, hedge_level_id: str) -> HedgeBookState:
        if not state.completed:
            raise ValueError("complete the December Difference before opening the Hedge Book")
        if state.hedge_book is not None:
            raise ValueError("the Hedge Book has already been opened")
        preview = self.preview_hedge(state, hedge_level_id)
        if preview.operating_cash_remaining < 0:
            raise InsufficientOperatingCashError(
                f"initial margin requires {preview.initial_margin_required}, "
                f"but operating cash is {state.corporate_cash}"
            )
        self.price_path = self._select_price_path(state.seed)
        initial_market = self.price_path.initial_market
        physical = PhysicalExposure(
            id=self.scenario.physical_exposure_id,
            quantity_mmbtu=self.scenario.physical_quantity_mmbtu,
            direction=PhysicalDirection.LONG,
            regional_hub=self.scenario.regional_hub,
            settlement_date=self.scenario.physical_settlement_date,
            original_henry_hub_price=initial_market.henry_hub_price,
            original_basis=initial_market.chicago_basis,
        )
        ticket = HedgeTicket(
            id=f"ticket_{hedge_level_id}",
            hedge_level_id=hedge_level_id,
            contract_id=self.contract.id,
            contract_month=self.scenario.contract_month,
            side=self.scenario.futures_side,
            contracts=preview.contracts,
            hedge_ratio=preview.hedge_ratio,
            entry_price=initial_market.henry_hub_price,
            initial_margin_required=preview.initial_margin_required,
            physical_quantity_mmbtu=self.scenario.physical_quantity_mmbtu,
            hedged_quantity_mmbtu=preview.hedged_quantity_mmbtu,
            speculative_quantity_mmbtu=preview.speculative_quantity_mmbtu,
        )
        position = (
            FuturesPosition(
                contract_id=self.contract.id,
                contract_month=self.scenario.contract_month,
                side=self.scenario.futures_side,
                contracts=preview.contracts,
                contract_size_mmbtu=self.contract.contract_size_mmbtu,
                entry_price=initial_market.henry_hub_price,
                current_price=initial_market.henry_hub_price,
            )
            if preview.contracts
            else None
        )
        initial_requirement = preview.initial_margin_required
        maintenance_requirement = money(
            self.scenario.maintenance_margin_per_contract * Decimal(preview.contracts)
        )
        book = HedgeBookState(
            scenario_id=self.scenario.id,
            seed=state.seed,
            price_path=self.price_path,
            contract=self.contract,
            ticket=ticket,
            physical=physical,
            position=position,
            initial_margin_per_contract=self.scenario.initial_margin_per_contract,
            maintenance_margin_per_contract=self.scenario.maintenance_margin_per_contract,
            minimum_operating_reserve=self.scenario.minimum_operating_reserve,
            margin=MarginAccount(
                balance=initial_requirement,
                initial_requirement=initial_requirement,
                maintenance_requirement=maintenance_requirement,
                total_initial_deposit=initial_requirement,
            ),
            beginning_operating_cash=state.corporate_cash,
            learning_objectives=list(self.scenario.learning_objectives),
        )
        state.hedge_book = book
        state.current_date = initial_market.settlement_date
        if initial_requirement:
            state.corporate_cash = money(state.corporate_cash - initial_requirement)
            self._post_pattern(
                state,
                pattern_key="initial_margin",
                amount=initial_requirement,
                transaction_id=f"txn_hedge_initial_margin_{hedge_level_id}",
                description=(
                    f"Initial margin for {preview.contracts} "
                    f"{self.contract.product_code} contract(s)"
                ),
                source_id=ticket.id,
            )
        if ticket.is_overhedged:
            self._change_resource(state, "audit_risk", 3, ticket.id)
            self._change_resource(state, "evidence_exposure", 2, ticket.id)
            state.career_trajectory.record(
                f"hedge_level_{hedge_level_id}",
                TrajectoryTag.AMBITIOUS,
                1,
            )
        state.record(
            phase="system",
            event_type="hedge_opened",
            source_id=ticket.id,
            message=(
                f"Opened {ticket.contracts} {ticket.side.value} futures contract(s) "
                f"at a {ticket.hedge_ratio:.0%} hedge ratio."
            ),
            changes={
                "contracts": ticket.contracts,
                "ratio": str(ticket.hedge_ratio),
                "initial_margin": str(initial_requirement),
                "cash_after": str(state.corporate_cash),
                "speculative_mmbtu": str(ticket.speculative_quantity_mmbtu),
                "market_path_id": self.price_path.id,
            },
        )
        self.assert_cash_and_margin_reconcile(state)
        return book

    def settle_next_day(
        self,
        state: GameState,
        *,
        defer_margin_call: bool = False,
    ) -> DailySettlementResult:
        book = self._require_open_book(state)
        if book.completed:
            raise ValueError("the Hedge Book scenario is already complete")
        if book.pending_margin_call_id is not None:
            raise ValueError("resolve the pending margin call before the next settlement")
        market = book.price_path.settlements[book.next_settlement_index]
        state.current_date = market.settlement_date
        previous_price = (
            book.price_path.initial_market.henry_hub_price
            if book.next_settlement_index == 0
            else book.price_path.settlements[book.next_settlement_index - 1].henry_hub_price
        )
        daily_pnl = (
            futures_daily_pnl(
                side=book.position.side,
                previous_settlement=previous_price,
                current_settlement=market.henry_hub_price,
                contract_size_mmbtu=book.position.contract_size_mmbtu,
                contracts=book.position.contracts,
            )
            if book.position is not None
            else Decimal("0")
        )
        margin_before = book.margin.balance
        margin_after_settlement = money(margin_before + daily_pnl)
        if margin_after_settlement < 0:
            raise ValueError(
                "configured daily loss exceeds margin equity; forced liquidation "
                "accounting is outside this milestone"
            )
        book.margin.balance = margin_after_settlement
        book.margin.total_variation_margin = money(book.margin.total_variation_margin + daily_pnl)
        if book.position is not None:
            book.position.current_price = market.henry_hub_price
            book.position.daily_pnl = daily_pnl
            book.position.cumulative_pnl = money(book.position.cumulative_pnl + daily_pnl)
        if daily_pnl > 0:
            self._post_pattern(
                state,
                pattern_key="futures_gain",
                amount=daily_pnl,
                transaction_id=f"txn_futures_gain_day_{book.next_settlement_index + 1}",
                description=f"Futures settlement gain for {market.settlement_date}",
                source_id=f"settlement_day_{book.next_settlement_index + 1}",
            )
        elif daily_pnl < 0:
            self._post_pattern(
                state,
                pattern_key="futures_loss",
                amount=-daily_pnl,
                transaction_id=f"txn_futures_loss_day_{book.next_settlement_index + 1}",
                description=f"Futures settlement loss for {market.settlement_date}",
                source_id=f"settlement_day_{book.next_settlement_index + 1}",
            )

        call_amount = margin_call_amount(
            balance=book.margin.balance,
            initial_requirement=book.margin.initial_requirement,
            maintenance_requirement=book.margin.maintenance_requirement,
        )
        funded = Decimal("0") if defer_margin_call else min(call_amount, state.corporate_cash)
        shortfall = money(call_amount - funded)
        if call_amount:
            if funded:
                state.corporate_cash = money(state.corporate_cash - funded)
                book.margin.balance = money(book.margin.balance + funded)
                book.margin.total_additional_deposits = money(
                    book.margin.total_additional_deposits + funded
                )
                self._post_pattern(
                    state,
                    pattern_key="margin_call",
                    amount=funded,
                    transaction_id=f"txn_margin_call_day_{book.next_settlement_index + 1}",
                    description=f"Fund margin call for {market.settlement_date}",
                    source_id=f"margin_call_day_{book.next_settlement_index + 1}",
                )
            margin_call = MarginCall(
                call_id=f"margin_call_day_{book.next_settlement_index + 1}",
                call_date=market.settlement_date,
                required_amount=call_amount,
                funded_amount=funded,
                shortfall=shortfall,
                met=shortfall == 0,
            )
            book.margin.calls.append(margin_call)
            if defer_margin_call:
                book.pending_margin_call_id = margin_call.call_id
            elif shortfall:
                book.liquidity_crisis = True
        henry_component, basis_component, physical_pnl = physical_pnl_components(
            book.physical, market
        )
        cumulative_futures = (
            book.position.cumulative_pnl if book.position is not None else Decimal("0")
        )
        net_pnl = money(physical_pnl + cumulative_futures)
        result = DailySettlementResult(
            day_number=book.next_settlement_index + 1,
            settlement_date=market.settlement_date,
            event_title=market.event_title,
            event_text=market.event_text,
            communication_from=market.communication_from,
            communication_subject=market.communication_subject,
            previous_henry_hub_price=previous_price,
            henry_hub_price=market.henry_hub_price,
            chicago_basis=market.chicago_basis,
            chicago_price=market.regional_price,
            daily_futures_pnl=daily_pnl,
            cumulative_futures_pnl=cumulative_futures,
            henry_hub_physical_component=henry_component,
            basis_component=basis_component,
            physical_economic_pnl=physical_pnl,
            net_economic_pnl=net_pnl,
            margin_balance_before=margin_before,
            margin_balance_after_settlement=margin_after_settlement,
            margin_call_amount=call_amount,
            margin_funded=funded,
            margin_balance_end=book.margin.balance,
            operating_cash_end=state.corporate_cash,
            liquidity_headroom=money(state.corporate_cash - book.minimum_operating_reserve),
        )
        book.settlements.append(result)
        book.next_settlement_index += 1
        state.record(
            phase="system",
            event_type="futures_settlement",
            source_id=f"settlement_day_{result.day_number}",
            message=market.event_title,
            changes={
                "daily_futures_pnl": str(daily_pnl),
                "cumulative_futures_pnl": str(cumulative_futures),
                "physical_economic_pnl": str(physical_pnl),
                "basis_component": str(basis_component),
                "net_economic_pnl": str(net_pnl),
                "margin_call": str(call_amount),
                "margin_shortfall": str(shortfall),
            },
        )
        if (shortfall and not defer_margin_call) or (
            book.next_settlement_index == len(book.price_path.settlements)
        ):
            self._close_and_release(state)
        self.assert_cash_and_margin_reconcile(state)
        return result

    def fund_pending_margin_call(
        self,
        state: GameState,
        amount: Decimal | None = None,
    ) -> Decimal:
        """Move operating cash into FCM cash for a previously deferred call."""
        book = self._require_open_book(state)
        call = self._pending_call(book)
        funding = call.shortfall if amount is None else money(amount)
        if funding <= 0:
            raise ValueError("margin-call funding must be positive")
        if funding > call.shortfall:
            raise ValueError("margin-call funding exceeds the remaining call")
        if funding > state.corporate_cash:
            raise InsufficientOperatingCashError("operating cash cannot fund the margin call")
        state.corporate_cash = money(state.corporate_cash - funding)
        book.margin.balance = money(book.margin.balance + funding)
        book.margin.total_additional_deposits = money(
            book.margin.total_additional_deposits + funding
        )
        call.funded_amount = money(call.funded_amount + funding)
        call.shortfall = money(call.required_amount - call.funded_amount)
        call.met = call.shortfall == 0
        if call.met:
            book.pending_margin_call_id = None
        self._post_pattern(
            state,
            pattern_key="margin_call",
            amount=funding,
            transaction_id=f"txn_treasury_fund_{call.call_id}",
            description=f"Fund deferred margin call dated {call.call_date}",
            source_id=call.call_id,
        )
        self._refresh_latest_settlement_cash(state)
        state.record(
            phase="system",
            event_type="margin_call_funded",
            source_id=call.call_id,
            message=f"Funded ${funding:,.2f} of the deferred margin call.",
            changes={
                "funded": str(funding),
                "shortfall": str(call.shortfall),
                "cash_after": str(state.corporate_cash),
            },
        )
        self.assert_cash_and_margin_reconcile(state)
        return funding

    def reduce_position(
        self,
        state: GameState,
        contracts_to_close: int,
    ) -> PositionReductionTrade:
        """Reduce only future exposure and recalculate prospective margin needs."""
        book = self._require_open_book(state)
        if book.pending_margin_call_id is None:
            raise ValueError("position reduction is available only while a call is pending")
        if book.position is None or book.position.contracts == 0:
            raise ValueError("there is no futures position to reduce")
        if not 0 < contracts_to_close <= book.position.contracts:
            raise ValueError("contracts_to_close must be within the open position")

        call = self._pending_call(book)
        previous_contracts = book.position.contracts
        remaining = previous_contracts - contracts_to_close
        previous_ratio = hedge_ratio(
            contracts=previous_contracts,
            contract_size_mmbtu=book.position.contract_size_mmbtu,
            physical_quantity_mmbtu=book.physical.quantity_mmbtu,
        )
        new_ratio = hedge_ratio(
            contracts=remaining,
            contract_size_mmbtu=book.position.contract_size_mmbtu,
            physical_quantity_mmbtu=book.physical.quantity_mmbtu,
        )
        book.position.contracts = remaining
        if remaining == 0:
            book.position.closed = True
            book.position_closed = True

        book.margin = book.margin.model_copy(
            update={
                "initial_requirement": money(book.initial_margin_per_contract * Decimal(remaining)),
                "maintenance_requirement": money(
                    book.maintenance_margin_per_contract * Decimal(remaining)
                ),
            }
        )
        releasable = max(
            Decimal("0"),
            money(book.margin.balance - book.margin.initial_requirement),
        )
        if releasable:
            state.corporate_cash = money(state.corporate_cash + releasable)
            book.margin.balance = money(book.margin.balance - releasable)
            book.margin.total_released = money(book.margin.total_released + releasable)
            self._post_pattern(
                state,
                pattern_key="margin_release",
                amount=releasable,
                transaction_id=f"txn_margin_release_reduction_{len(book.position_reductions) + 1}",
                description=(
                    f"Release eligible margin after closing {contracts_to_close} contract(s)"
                ),
                source_id=call.call_id,
            )
        revised_call = margin_call_amount(
            balance=book.margin.balance,
            initial_requirement=book.margin.initial_requirement,
            maintenance_requirement=book.margin.maintenance_requirement,
        )
        call.required_amount = revised_call
        call.funded_amount = Decimal("0")
        call.shortfall = revised_call
        call.met = revised_call == 0
        if call.met:
            book.pending_margin_call_id = None
        trade = PositionReductionTrade(
            trade_id=f"position_reduction_{len(book.position_reductions) + 1}",
            trade_date=state.current_date,
            contracts_closed=contracts_to_close,
            contracts_remaining=remaining,
            previous_hedge_ratio=previous_ratio,
            new_hedge_ratio=new_ratio,
            cumulative_futures_pnl_preserved=book.position.cumulative_pnl,
            margin_released=releasable,
            revised_margin_call=revised_call,
        )
        book.position_reductions.append(trade)
        self._refresh_latest_settlement_cash(state, revised_call=revised_call)
        state.record(
            phase="decision",
            event_type="futures_position_reduced",
            source_id=trade.trade_id,
            message=(
                f"Closed {contracts_to_close} contract(s); {remaining} remain. "
                "Prior settled P&L was preserved."
            ),
            changes={
                "previous_ratio": str(previous_ratio),
                "new_ratio": str(new_ratio),
                "margin_released": str(releasable),
                "revised_call": str(revised_call),
            },
        )
        self.assert_cash_and_margin_reconcile(state)
        return trade

    def miss_pending_margin_call(self, state: GameState) -> PositionReductionTrade:
        """Record an unmet call and deterministic FCM liquidation of the open position."""
        book = self._require_open_book(state)
        call = self._pending_call(book)
        if book.position is None or book.position.contracts == 0:
            raise ValueError("there is no open position for the FCM to liquidate")
        original_required = call.required_amount
        original_shortfall = call.shortfall
        original_contracts = book.position.contracts
        previous_ratio = hedge_ratio(
            contracts=original_contracts,
            contract_size_mmbtu=book.position.contract_size_mmbtu,
            physical_quantity_mmbtu=book.physical.quantity_mmbtu,
        )
        released = book.margin.balance
        if released:
            state.corporate_cash = money(state.corporate_cash + released)
            book.margin.balance = Decimal("0")
            book.margin.total_released = money(book.margin.total_released + released)
            self._post_pattern(
                state,
                pattern_key="margin_release",
                amount=released,
                transaction_id="txn_margin_release_forced_liquidation",
                description="Release residual margin after FCM liquidation",
                source_id=call.call_id,
            )
        book.position.contracts = 0
        book.position.closed = True
        book.position_closed = True
        book.margin = book.margin.model_copy(
            update={
                "initial_requirement": Decimal("0"),
                "maintenance_requirement": Decimal("0"),
            }
        )
        call.required_amount = original_required
        call.shortfall = original_shortfall
        call.met = False
        book.pending_margin_call_id = None
        book.liquidity_crisis = True
        trade = PositionReductionTrade(
            trade_id=f"position_reduction_{len(book.position_reductions) + 1}",
            trade_date=state.current_date,
            contracts_closed=original_contracts,
            contracts_remaining=0,
            previous_hedge_ratio=previous_ratio,
            new_hedge_ratio=Decimal("0"),
            cumulative_futures_pnl_preserved=book.position.cumulative_pnl,
            margin_released=released,
            revised_margin_call=original_required,
        )
        book.position_reductions.append(trade)
        self._refresh_latest_settlement_cash(state)
        state.record(
            phase="system",
            event_type="margin_call_missed",
            source_id=call.call_id,
            message="The 2:00 p.m. call was not met; the FCM liquidated the open contracts.",
            changes={
                "unmet_amount": str(original_shortfall),
                "contracts_liquidated": original_contracts,
                "margin_released": str(released),
            },
        )
        self.assert_cash_and_margin_reconcile(state)
        return trade

    def settle_remaining(self, state: GameState, maximum_days: int | None = None) -> int:
        if maximum_days is not None and maximum_days < 0:
            raise ValueError("maximum_days cannot be negative")
        processed = 0
        while (
            state.hedge_book is not None
            and not state.hedge_book.completed
            and (maximum_days is None or processed < maximum_days)
        ):
            self.settle_next_day(state)
            processed += 1
        return processed

    def _select_price_path(self, seed: int):
        path_ids = self.scenario.selectable_price_path_ids
        selected_id = self.market_path_override or path_ids[seed % len(path_ids)]
        return self.content.commodity_price_path(selected_id)

    def assert_cash_and_margin_reconcile(self, state: GameState) -> None:
        book = self._require_open_book(state)
        activity = state.ledger.account_activity()
        cash_debits, cash_credits = activity.get("1000", (Decimal("0"), Decimal("0")))
        ledger_cash = money(cash_debits - cash_credits)
        if ledger_cash != money(state.corporate_cash):
            raise ValueError(
                f"operating cash does not reconcile: ledger {ledger_cash}, "
                f"state {state.corporate_cash}"
            )
        margin_debits, margin_credits = activity.get("1050", (Decimal("0"), Decimal("0")))
        ledger_margin = money(margin_debits - margin_credits)
        if ledger_margin != money(book.margin.balance):
            raise ValueError(
                f"FCM margin does not reconcile: ledger {ledger_margin}, "
                f"state {book.margin.balance}"
            )

    def _close_and_release(self, state: GameState) -> None:
        book = self._require_open_book(state)
        release = book.margin.balance
        if release:
            state.corporate_cash = money(state.corporate_cash + release)
            book.margin.total_released = money(book.margin.total_released + release)
            self._post_pattern(
                state,
                pattern_key="margin_release",
                amount=release,
                transaction_id="txn_futures_margin_final_release",
                description="Release FCM margin after futures position is closed",
                source_id="hedge_book_close",
            )
            book.margin.balance = Decimal("0")
        if book.position is not None:
            book.position.closed = True
        book.position_closed = True
        book.completed = True
        book.outcome = self._derive_outcome(book)
        state.record(
            phase="system",
            event_type="hedge_book_completed",
            source_id=book.scenario_id,
            message=f"Hedge Book outcome: {book.outcome.value}.",
            changes={
                "outcome": book.outcome.value,
                "ending_cash": str(state.corporate_cash),
                "margin_released": str(release),
            },
        )

    @staticmethod
    def _derive_outcome(book: HedgeBookState) -> HedgeOutcome:
        if book.liquidity_crisis:
            return HedgeOutcome.LIQUIDITY_FAILURE
        if book.position_reductions:
            return HedgeOutcome.DE_HEDGED
        if book.ticket.hedge_ratio == 0:
            return HedgeOutcome.UNHEDGED_WINTER
        if book.ticket.speculative_quantity_mmbtu > 0:
            return HedgeOutcome.OVERHEDGE
        final = book.settlements[-1]
        if book.ticket.hedge_ratio == Decimal("1") and abs(final.net_economic_pnl) < abs(
            final.physical_economic_pnl
        ):
            return HedgeOutcome.INTENDED_HEDGE
        if book.margin.calls:
            return HedgeOutcome.MARGIN_PRESSURE
        return HedgeOutcome.INTENDED_HEDGE

    def _post_pattern(
        self,
        state: GameState,
        *,
        pattern_key: str,
        amount: Decimal,
        transaction_id: str,
        description: str,
        source_id: str,
    ) -> None:
        if amount <= 0:
            raise ValueError("journal pattern amount must be positive")
        pattern_id = self.scenario.journal_patterns[pattern_key]
        pattern = self.content.journal_pattern(pattern_id)
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
        if state.hedge_book is not None:
            state.hedge_book.journal_transaction_ids.append(entry.transaction_id)
        state.record(
            phase="system",
            event_type="commodity_journal_posted",
            source_id=source_id,
            message=entry.description,
            changes={
                "transaction_id": entry.transaction_id,
                "amount": str(amount),
                "pattern": pattern_id,
            },
        )

    def _contract_count(self, level: HedgeLevelDefinition) -> int:
        exact = (
            self.scenario.physical_quantity_mmbtu
            * level.hedge_ratio
            / self.contract.contract_size_mmbtu
        )
        if exact != exact.to_integral_value():
            raise ValueError(f"hedge level {level.id} does not map to whole contracts")
        return int(exact)

    @staticmethod
    def _pending_call(book: HedgeBookState) -> MarginCall:
        if book.pending_margin_call_id is None:
            raise ValueError("there is no pending margin call")
        return next(
            item for item in book.margin.calls if item.call_id == book.pending_margin_call_id
        )

    @staticmethod
    def _refresh_latest_settlement_cash(
        state: GameState,
        *,
        revised_call: Decimal | None = None,
    ) -> None:
        book = state.hedge_book
        if book is None or not book.settlements:
            return
        latest = book.settlements[-1]
        call = book.margin.calls[-1] if book.margin.calls else None
        book.settlements[-1] = latest.model_copy(
            update={
                "margin_call_amount": (
                    revised_call
                    if revised_call is not None
                    else (call.required_amount if call is not None else Decimal("0"))
                ),
                "margin_funded": call.funded_amount if call is not None else Decimal("0"),
                "margin_balance_end": book.margin.balance,
                "operating_cash_end": state.corporate_cash,
                "liquidity_headroom": money(state.corporate_cash - book.minimum_operating_reserve),
            }
        )

    @staticmethod
    def _change_resource(
        state: GameState,
        resource_name: str,
        amount: int,
        source_id: str,
    ) -> None:
        old_value = getattr(state.resources, resource_name)
        new_value = old_value + amount
        if not 0 <= new_value <= 100:
            raise ValueError(f"resource change exceeds bounds: {resource_name}")
        setattr(state.resources, resource_name, new_value)
        state.record(
            phase="immediate",
            event_type="commodity_resource_delta",
            source_id=source_id,
            message=f"{resource_name} changed by {amount:+d}.",
            changes={"resource": resource_name, "old": old_value, "new": new_value},
        )

    @staticmethod
    def _require_open_book(state: GameState) -> HedgeBookState:
        if state.hedge_book is None:
            raise ValueError("the Hedge Book has not been opened")
        return state.hedge_book
