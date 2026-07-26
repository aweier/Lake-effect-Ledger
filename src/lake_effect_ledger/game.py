"""Game-state construction for the Episode 1 vertical slice."""

from __future__ import annotations

from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from lake_effect_ledger.accounting.models import JournalEntry, JournalLine, Ledger
from lake_effect_ledger.learning.models import (
    GameMode,
    LearningProfile,
    LearningStatus,
    ObjectiveProgress,
    PrologueState,
    ShowMathMode,
)
from lake_effect_ledger.markets import generate_market_snapshot
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.state import (
    Background,
    GameState,
    InboxItem,
    Player,
    Resources,
)

OPENING_BALANCE_ID = "txn_opening_balance"


def create_new_game(
    *,
    name: str,
    background: Background,
    seed: int,
    content: ContentBundle,
    game_mode: GameMode = GameMode.STANDARD,
    show_math: ShowMathMode | None = None,
    skip_prologue: bool = False,
) -> GameState:
    """Create a fully deterministic initial state for a supplied seed."""
    background_definition = content.background(background)
    market_scenario = content.markets.scenarios[0]
    resources = Resources(
        reputation=50,
        family_loyalty=50,
        integrity=60,
        audit_risk=15,
        regulatory_heat=5,
        evidence_exposure=10,
    )
    for resource_name, adjustment in background_definition.resource_adjustments.items():
        current = getattr(resources, resource_name.value)
        updated = current + adjustment
        if not 0 <= updated <= 100:
            raise ValueError(f"background adjustment exceeds bounds for {resource_name.value}")
        setattr(resources, resource_name.value, updated)

    game_id = str(
        uuid5(
            NAMESPACE_URL,
            (f"lake-effect-ledger:{seed}:{name.strip()}:{background.value}:{game_mode.value}"),
        )
    )
    ledger = Ledger()
    opening_entry = JournalEntry(
        transaction_id=OPENING_BALANCE_ID,
        entry_date=market_scenario.game_date,
        description="Northstar opening trial balance for Episode 1",
        source_id="game_setup",
        lines=[
            JournalLine(account="1000", debit=Decimal("4200000")),
            JournalLine(account="1200", debit=Decimal("350000")),
            JournalLine(account="1500", debit=Decimal("3000000")),
            JournalLine(account="2000", credit=Decimal("400000")),
            JournalLine(account="2500", credit=Decimal("2500000")),
            JournalLine(account="3000", credit=Decimal("4650000")),
        ],
    )
    ledger.post(opening_entry, content.valid_accounts)
    guided = game_mode == GameMode.GUIDED and not skip_prologue
    mode_definition = content.game_mode(game_mode)
    starting_objective = {
        Background.ACCOUNTING: "double_entry",
        Background.FINANCE: "physical_financial_exposure",
        Background.DATA_ANALYTICS: "reconciliation_evidence",
    }[background]
    learning = LearningProfile(
        objectives={starting_objective: ObjectiveProgress(status=LearningStatus.INTRODUCED)}
    )

    state = GameState(
        game_id=game_id,
        seed=seed,
        current_date=(
            content.prologue.prologue.start_date if guided else market_scenario.game_date
        ),
        player=Player(
            name=name.strip(),
            background=background,
            skills=background_definition.skills,
            role=(
                content.prologue.prologue.role_title
                if game_mode == GameMode.GUIDED
                else "Northstar Analyst"
            ),
        ),
        game_mode=game_mode,
        show_math=show_math or mode_definition.default_show_math,
        prologue=PrologueState(
            started=guided,
            completed=not guided,
            skipped=game_mode == GameMode.GUIDED and skip_prologue,
            transitioned_to_episode_1=not guided,
        ),
        learning=learning,
        resources=resources,
        corporate_cash=Decimal("4200000"),
        personal_cash=background_definition.personal_cash,
        margin_due=market_scenario.margin_due,
        market=generate_market_snapshot(market_scenario, seed),
        inbox=[
            InboxItem(
                item_id="inbox_december_variance",
                sender="Evelyn Marsh, Controller",
                subject="December close variance — review before noon",
                urgent=True,
            ),
            InboxItem(
                item_id="inbox_margin_call",
                sender="Lakefront FCM",
                subject="Fictional variation margin due by 2:00 PM",
                urgent=True,
            ),
            InboxItem(
                item_id="inbox_meter_mismatch",
                sender="Marisol Vega, Gas Scheduling",
                subject="ANR meter and settlement volumes do not agree",
            ),
        ],
        ledger=ledger,
        flags={"variance_discovered": True},
    )
    state.record(
        phase="setup",
        event_type="game_started",
        source_id="episode_01",
        message="Episode 1 initialized from validated content.",
        changes={
            "seed": seed,
            "background": background.value,
            "game_mode": game_mode.value,
            "prologue_skipped": skip_prologue,
            "market_scenario": market_scenario.id,
        },
    )
    return state
