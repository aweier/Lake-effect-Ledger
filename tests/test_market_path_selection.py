from decimal import Decimal

import pytest

from lake_effect_ledger.commodity.engine import CommodityEngine


@pytest.mark.parametrize(
    ("seed", "expected_path"),
    [
        (1728, "fictional_margin_squeeze_2028"),
        (1729, "fictional_lake_storm_2028"),
    ],
)
def test_seed_selects_stable_authored_path(
    content,
    completed_state_factory,
    seed: int,
    expected_path: str,
) -> None:
    state = completed_state_factory(seed=seed)
    CommodityEngine(content).open_hedge(state, "hedge_100")

    assert state.hedge_book.price_path.id == expected_path


def test_same_seed_replays_same_path(content, completed_state_factory) -> None:
    selected = []
    for _ in range(2):
        state = completed_state_factory(seed=42)
        CommodityEngine(content).open_hedge(state, "hedge_100")
        selected.append(state.hedge_book.price_path)

    assert selected[0] == selected[1]


def test_market_path_override_is_stored(content, completed_state_factory) -> None:
    state = completed_state_factory(seed=1729)
    CommodityEngine(
        content,
        market_path_id="fictional_margin_squeeze_2028",
    ).open_hedge(state, "hedge_100")

    assert state.hedge_book.price_path.id == "fictional_margin_squeeze_2028"


def test_unknown_market_path_override_is_rejected(content) -> None:
    with pytest.raises(ValueError, match="market path must be one of"):
        CommodityEngine(content, market_path_id="future_prices_from_the_internet")


def test_rally_path_creates_material_deferred_call(
    content,
    completed_state_factory,
) -> None:
    state = completed_state_factory(seed=1728)
    engine = CommodityEngine(
        content,
        market_path_id="fictional_margin_squeeze_2028",
    )
    book = engine.open_hedge(state, "hedge_100")

    first = engine.settle_next_day(state, defer_margin_call=True)
    second = engine.settle_next_day(state, defer_margin_call=True)

    assert first.margin_call_amount == 0
    assert second.margin_call_amount == Decimal("70000.00")
    assert second.margin_funded == 0
    assert second.cumulative_futures_pnl == Decimal("-70000.00")
    assert second.physical_economic_pnl == Decimal("55000.00")
    assert book.pending_margin_call_id == "margin_call_day_2"


def test_rally_basis_moves_independently_of_henry_hub(content) -> None:
    path = content.commodity_price_path("fictional_margin_squeeze_2028")
    pairs = zip(
        [path.initial_market, *path.settlements[:-1]],
        path.settlements,
        strict=True,
    )

    assert any(
        (current.henry_hub_price - previous.henry_hub_price)
        * (current.chicago_basis - previous.chicago_basis)
        < 0
        for previous, current in pairs
    )


def test_legacy_auto_funding_behavior_remains_available(
    content,
    completed_state_factory,
) -> None:
    state = completed_state_factory(seed=1728)
    engine = CommodityEngine(
        content,
        market_path_id="fictional_margin_squeeze_2028",
    )
    book = engine.open_hedge(state, "hedge_100")
    engine.settle_next_day(state)
    second = engine.settle_next_day(state)

    assert second.margin_funded == Decimal("70000.00")
    assert book.pending_margin_call_id is None
    assert book.margin.calls[0].met
