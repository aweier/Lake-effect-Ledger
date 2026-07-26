from lake_effect_ledger.game import create_new_game
from lake_effect_ledger.state import Background


def test_game_state_initializes_with_meaningful_background_differences(content) -> None:
    accounting = create_new_game(
        name="Morgan",
        background=Background.ACCOUNTING,
        seed=42,
        content=content,
    )
    analytics = create_new_game(
        name="Morgan",
        background=Background.DATA_ANALYTICS,
        seed=42,
        content=content,
    )

    assert accounting.player.skills.accounting > analytics.player.skills.accounting
    assert analytics.player.skills.analytics > accounting.player.skills.analytics
    assert analytics.resources.audit_risk < accounting.resources.audit_risk
    assert accounting.ledger.entries[0].total_debits == accounting.ledger.entries[0].total_credits


def test_seeded_state_is_deterministic(content) -> None:
    first = create_new_game(
        name="Morgan",
        background=Background.FINANCE,
        seed=8675309,
        content=content,
    )
    second = create_new_game(
        name="Morgan",
        background=Background.FINANCE,
        seed=8675309,
        content=content,
    )
    other = create_new_game(
        name="Morgan",
        background=Background.FINANCE,
        seed=1,
        content=content,
    )

    assert first == second
    assert first.market != other.market
