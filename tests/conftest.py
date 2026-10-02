from pathlib import Path

import pytest

from lake_effect_ledger.commodity.engine import CommodityEngine
from lake_effect_ledger.game import create_new_game
from lake_effect_ledger.narrative.engine import NarrativeEngine
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.state import Background
from lake_effect_ledger.treasury.engine import TreasuryEngine


@pytest.fixture(scope="session")
def content_root() -> Path:
    return Path(__file__).resolve().parents[1] / "src" / "lake_effect_ledger" / "content"


@pytest.fixture(scope="session")
def content(content_root: Path) -> ContentBundle:
    return ContentBundle.load(content_root)


@pytest.fixture
def completed_state_factory(content: ContentBundle):
    def factory(
        *,
        seed: int = 1729,
        background: Background = Background.DATA_ANALYTICS,
    ):
        state = create_new_game(
            name="Test Player",
            background=background,
            seed=seed,
            content=content,
        )
        narrative = NarrativeEngine(content)
        narrative.choose(
            state,
            "december_difference",
            "request_meter_support",
        )
        narrative.process_end_of_day(state)
        return state

    return factory


@pytest.fixture
def treasury_state_factory(content: ContentBundle, completed_state_factory):
    def factory(
        *,
        path_id: str = "fictional_margin_squeeze_2028",
        hedge_level: str = "hedge_100",
        seed: int = 1728,
    ):
        state = completed_state_factory(seed=seed)
        commodity = CommodityEngine(content, market_path_id=path_id)
        commodity.open_hedge(state, hedge_level)
        NarrativeEngine(content).choose(
            state,
            "hedge_documentation",
            "write_accurate_hedge_memo",
        )
        commodity.settle_next_day(state, defer_margin_call=True)
        commodity.settle_next_day(state, defer_margin_call=True)
        treasury = TreasuryEngine(content, commodity)
        treasury.initialize_crisis(state)
        return state, commodity, treasury

    return factory
