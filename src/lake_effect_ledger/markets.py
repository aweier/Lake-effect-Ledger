"""Deterministic fictional market snapshots."""

from decimal import Decimal
from random import Random

from lake_effect_ledger.narrative.models import MarketScenario
from lake_effect_ledger.state import MarketSnapshot

CENT = Decimal("0.01")


def generate_market_snapshot(scenario: MarketScenario, seed: int) -> MarketSnapshot:
    """Generate reproducible cent-based price noise without global RNG state."""
    randomizer = Random(seed)
    henry_move = (
        Decimal(
            randomizer.randint(
                -scenario.henry_hub_jitter_cents,
                scenario.henry_hub_jitter_cents,
            )
        )
        * CENT
    )
    basis_move = (
        Decimal(
            randomizer.randint(
                -scenario.chicago_basis_jitter_cents,
                scenario.chicago_basis_jitter_cents,
            )
        )
        * CENT
    )
    return MarketSnapshot(
        scenario_id=scenario.id,
        label=scenario.label,
        fictional=scenario.fictional,
        henry_hub_price=(scenario.henry_hub_base + henry_move).quantize(CENT),
        chicago_basis=(scenario.chicago_basis_base + basis_move).quantize(CENT),
    )
