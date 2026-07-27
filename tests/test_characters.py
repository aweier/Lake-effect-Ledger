import re
from copy import deepcopy

from rich.console import Console
from typer.testing import CliRunner

import lake_effect_ledger.cli as cli
from lake_effect_ledger.cli import app
from lake_effect_ledger.commodity.engine import CommodityEngine
from lake_effect_ledger.game import create_new_game
from lake_effect_ledger.learning.engine import LearningEngine
from lake_effect_ledger.learning.models import CampaignTrack, GameMode
from lake_effect_ledger.narrative.engine import NarrativeEngine
from lake_effect_ledger.persistence.saves import (
    SaveRepository,
    migrate_state_payload,
)
from lake_effect_ledger.state import Background, GameState
from lake_effect_ledger.trading.engine import EleventhContractEngine

runner = CliRunner()


def _state(content):
    return create_new_game(
        name="Character Tester",
        background=Background.DATA_ANALYTICS,
        seed=1728,
        content=content,
        game_mode=GameMode.GUIDED,
        campaign_track=CampaignTrack.SERIES_3_CORE,
    )


def test_introduction_is_shown_once_and_does_not_change_financial_state(
    content,
    monkeypatch,
) -> None:
    state = _state(content)
    before = {
        "resources": state.resources.model_dump(),
        "cash": (state.corporate_cash, state.personal_cash, state.margin_due),
        "ledger": state.ledger.model_dump(),
        "decisions": list(state.decisions),
    }
    console = Console(record=True, width=100)
    monkeypatch.setattr(cli, "console", console)

    cli._introduce_characters(state, content, "tj_morrow")
    cli._introduce_characters(state, content, "tj_morrow")

    output = console.export_text()
    assert output.count("NEW CONTACT") == 1
    assert output.count("Travis “T.J.” Morrow") == 1
    assert state.introduced_character_ids == ["tj_morrow"]
    assert before == {
        "resources": state.resources.model_dump(),
        "cash": (state.corporate_cash, state.personal_cash, state.margin_due),
        "ledger": state.ledger.model_dump(),
        "decisions": list(state.decisions),
    }


def test_introduction_state_survives_save_and_load(
    content,
    monkeypatch,
    tmp_path,
) -> None:
    state = _state(content)
    first_console = Console(record=True, width=100)
    monkeypatch.setattr(cli, "console", first_console)
    cli._introduce_characters(state, content, "kasia_zielinska")

    repository = SaveRepository(tmp_path / "characters.db")
    repository.save(state)
    restored = repository.load()
    second_console = Console(record=True, width=100)
    monkeypatch.setattr(cli, "console", second_console)
    cli._introduce_characters(restored, content, "kasia_zielinska")

    assert restored.save_schema_version == 9
    assert restored.introduced_character_ids == ["kasia_zielinska"]
    assert "NEW CONTACT" not in second_console.export_text()


def test_v8_migration_infers_existing_contacts_without_inventing_new_ones(
    content,
) -> None:
    state = _state(content)
    state.prologue.started = True
    state.prologue.completed = True
    state.prologue.current_day_index = 3
    state.completed = True
    payload = state.model_dump(mode="json")
    payload["save_schema_version"] = 8
    payload.pop("introduced_character_ids")

    restored = GameState.model_validate(migrate_state_payload(payload))

    assert restored.save_schema_version == 9
    assert {
        "evelyn_marsh",
        "marisol_vega",
        "darren_cho",
        "june_halvorsen",
        "vince_bellandi",
    } <= set(restored.introduced_character_ids)
    assert "tj_morrow" not in restored.introduced_character_ids
    assert "kasia_zielinska" not in restored.introduced_character_ids


def test_public_cards_do_not_render_character_bible_secrets(
    content,
    monkeypatch,
) -> None:
    state = _state(content)
    console = Console(record=True, width=100)
    monkeypatch.setattr(cli, "console", console)

    cli._introduce_characters(
        state,
        content,
        "tj_morrow",
        "kasia_zielinska",
    )

    output = console.export_text()
    assert "left a Houston promotion path" not in output
    assert "permanent cleanup staff" not in output
    assert "Story secrets" not in output
    assert "author-only" not in output


def test_conditional_reveals_require_their_actual_prior_choices(content) -> None:
    state = _state(content)
    narrative = NarrativeEngine(content)
    tj_text = "I just don't like pretending it makes the pipe wider."
    kasia_text = "she trusts paper because institutions change faster than pipes."

    assert tj_text not in narrative.resolved_scene_text(
        state,
        "ec_hedge_recommendation",
    )
    narrative.choose(
        state,
        "first_rotation_qualification",
        "preserve_scheduling_qualification",
    )
    assert tj_text in narrative.resolved_scene_text(
        state,
        "ec_hedge_recommendation",
    )

    assert kasia_text not in narrative.resolved_scene_text(state, "ec_verification")
    state.completed = True
    commodity = CommodityEngine(content)
    commodity.open_hedge(state, "no_hedge")
    commodity.settle_remaining(state)
    EleventhContractEngine(content).initialize(state)
    narrative.choose(
        state,
        "ec_ask_marisol",
        "ec_ask_marisol_before_recommendation",
    )
    assert kasia_text in narrative.resolved_scene_text(state, "ec_verification")


def test_houston_and_polish_contacts_appear_early_in_core(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--game-mode",
            "guided",
            "--campaign-track",
            "series3_core",
            "--prologue-days",
            "2",
            "--save-db",
            str(tmp_path / "early-contacts.db"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Travis “T.J.” Morrow" in result.output
    assert "Houston, Texas" in result.output
    assert "Katarzyna “Kasia” Zielińska" in result.output
    assert "Gdańsk, Poland" in result.output
    state = SaveRepository(tmp_path / "early-contacts.db").load()
    assert state.introduced_character_ids.count("tj_morrow") == 1
    assert state.introduced_character_ids.count("kasia_zielinska") == 1


def test_character_ids_are_ascii_safe_and_unicode_renders_cleanly(
    content,
    monkeypatch,
) -> None:
    for character in content.characters.people:
        assert re.fullmatch(r"[a-z0-9_]+", character.id)
        character.id.encode("ascii")

    state = _state(content)
    console = Console(record=True, width=100)
    monkeypatch.setattr(cli, "console", console)
    cli._introduce_characters(state, content, "kasia_zielinska")
    output = console.export_text()
    assert "Katarzyna “Kasia” Zielińska" in output
    assert "Gdańsk" in output
    assert "\ufffd" not in output


def test_character_introductions_preserve_core_calculation_answers(
    content,
    monkeypatch,
) -> None:
    state = _state(content)
    before = {
        check_id: LearningEngine(content).expected_answer(check_id)
        for check_id in (
            "d1_futures_pnl",
            "d1_tick_value",
            "d2_regional_price",
            "d2_hedge_ratio",
            "d3_margin_call_amount",
        )
    }
    protected = deepcopy(state.model_dump())
    console = Console(record=True, width=100)
    monkeypatch.setattr(cli, "console", console)

    cli._introduce_characters(
        state,
        content,
        "evelyn_marsh",
        "marisol_vega",
        "tj_morrow",
        "kasia_zielinska",
    )

    after = {check_id: LearningEngine(content).expected_answer(check_id) for check_id in before}
    assert after == before
    current = state.model_dump()
    protected["introduced_character_ids"] = current["introduced_character_ids"]
    assert current == protected
