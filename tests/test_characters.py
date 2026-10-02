import re
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

import lake_effect_ledger.cli as cli
from lake_effect_ledger.cli import app
from lake_effect_ledger.commodity.engine import CommodityEngine
from lake_effect_ledger.game import create_new_game
from lake_effect_ledger.learning.engine import LearningEngine
from lake_effect_ledger.learning.models import CampaignTrack, GameMode
from lake_effect_ledger.narrative.engine import NarrativeEngine
from lake_effect_ledger.narrative.models import CharacterFile
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

    assert restored.save_schema_version == 11
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

    assert restored.save_schema_version == 11
    assert {
        "evelyn_marsh",
        "marisol_vega",
        "darren_cho",
        "june_halvorsen",
        "vince_rourke",
    } <= set(restored.introduced_character_ids)
    assert "vince_bellandi" not in restored.introduced_character_ids
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
    assert "Background route: Pasadena → Houston, Texas" in output
    assert "Background route: Gdańsk, Poland → Chicago → Milwaukee" in output
    assert "left a Houston promotion path" not in output
    assert "permanent cleanup staff" not in output
    assert "Story secrets" not in output
    assert "author-only" not in output
    assert "Legacy internal ID retained" not in output
    assert "vince_rourke" not in output
    assert "dom_bellini" not in output


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


def test_day_two_bridges_the_basis_lesson_into_the_first_decision(tmp_path) -> None:
    database = tmp_path / "early-contacts.db"
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
            str(database),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Travis “T.J.” Morrow" in result.output
    assert "Houston, Texas" in result.output
    assert "Katarzyna “Kasia” Zielińska" in result.output
    assert "Gdańsk, Poland" in result.output
    assert "Marisol Vega, Northstar’s Gas Scheduling Manager" in result.output
    assert "Commercial Director and Hedging Supervisor" in result.output
    assert (
        result.output.index("Day 2 — The Basis")
        < result.output.index("From the Board to the Packet")
        < result.output.index("The Line Cal Wants Gone")
    )
    state = SaveRepository(database).load()
    assert state.introduced_character_ids.count("tj_morrow") == 1
    assert state.introduced_character_ids.count("kasia_zielinska") == 1
    assert state.introduced_character_ids.count("marisol_vega") == 1
    assert state.introduced_character_ids.count("cal_rourke") == 1


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


def test_character_bible_and_runtime_registry_have_one_to_one_recurring_cast(
    content,
    content_root,
) -> None:
    bible = (Path(__file__).resolve().parents[1] / "CHARACTER_BIBLE.md").read_text(encoding="utf-8")
    bible_ids = re.findall(r"^- Stable ID: `([a-z0-9_]+)`$", bible, flags=re.MULTILINE)
    runtime_ids = {item.id for item in content.characters.people if item.id != "player"}

    assert len(bible_ids) == len(set(bible_ids))
    assert set(bible_ids) == runtime_ids
    assert "Legacy internal ID retained for save compatibility" in bible
    normalized_bible = re.sub(r"\s+", " ", bible)
    assert "Vince is a Bellandi, Dom's nephew, and is not related to Cal Rourke" in normalized_bible
    assert "Founder and Chairman of Northstar Midstream &" in bible


def test_bellandi_identity_relationships_and_authority_are_canonical(content) -> None:
    dom = content.character("dom_bellini")
    vince = content.character("vince_rourke")
    cal = content.character("cal_rourke")

    assert (dom.name, dom.role) == ("Dominic “Dom” Bellandi", "Founder and Chairman")
    assert dom.family_relationships == {"vince_rourke": "nephew"}
    assert (vince.name, vince.role) == ("Vince Bellandi", "EVP, Operations")
    assert vince.family_relationships == {"dom_bellini": "uncle"}
    assert cal.role == "Commercial Director and Hedging Supervisor"
    assert not ({"dom_bellini", "vince_rourke"} & set(cal.family_relationships))
    assert "not related to Cal Rourke" in vince.legacy_id_note


def test_character_validation_rejects_false_family_and_non_geographic_origin(content) -> None:
    payload = content.characters.model_dump(mode="json")
    by_id = {item["id"]: item for item in payload["people"]}
    by_id["cal_rourke"]["family_relationships"] = {"vince_rourke": "brother"}
    with pytest.raises(ValueError, match="Cal Rourke is not related"):
        CharacterFile.model_validate(payload)

    payload = content.characters.model_dump(mode="json")
    by_id = {item["id"]: item for item in payload["people"]}
    by_id["tj_morrow"]["origin"] = "Houston → Northstar commercial desk"
    with pytest.raises(ValueError, match="geography only"):
        CharacterFile.model_validate(payload)


def test_backgrounds_are_balanced_and_new_players_start_neutral(content) -> None:
    expected_skills = {
        Background.ACCOUNTING: (8, 4, 5),
        Background.FINANCE: (5, 8, 4),
        Background.DATA_ANALYTICS: (4, 5, 8),
    }
    states = {}
    for background, skill_values in expected_skills.items():
        definition = content.background(background)
        state = create_new_game(
            name=f"{background.value} tester",
            background=background,
            seed=1728,
            content=content,
            skip_prologue=True,
        )
        states[background] = state
        assert (
            definition.skills.accounting,
            definition.skills.markets,
            definition.skills.analytics,
        ) == skill_values
        assert sum(skill_values) == 17
        assert definition.resource_adjustments == {}
        assert state.personal_cash == Decimal("2600")
        assert state.player.role == "Junior Commodity Risk Analyst"

    resource_profiles = {tuple(state.resources.model_dump().items()) for state in states.values()}
    assert len(resource_profiles) == 1


def test_background_validation_rejects_moral_adjustments_and_unequal_skills(content) -> None:
    payload = content.characters.model_dump(mode="json")
    payload["backgrounds"][0]["resource_adjustments"] = {"integrity": 1}
    with pytest.raises(ValueError, match="cannot modify moral or risk resources"):
        CharacterFile.model_validate(payload)

    payload = content.characters.model_dump(mode="json")
    payload["backgrounds"][2]["skills"]["analytics"] = 9
    with pytest.raises(ValueError, match="must total 17 skill points"):
        CharacterFile.model_validate(payload)


def test_native_v11_save_keeps_resources_and_existing_character_ids(
    content,
    tmp_path,
) -> None:
    state = _state(content)
    state.personal_cash = Decimal("987.65")
    state.resources.integrity = 37
    state.resources.family_loyalty = 81
    state.resources.audit_risk = 44
    state.introduced_character_ids = ["vince_bellandi", "evelyn_marsh"]
    repository = SaveRepository(tmp_path / "legacy-v9.db")
    repository.save(state)

    restored = repository.load()

    assert restored.save_schema_version == 11
    assert restored.personal_cash == Decimal("987.65")
    assert restored.resources.integrity == 37
    assert restored.resources.family_loyalty == 81
    assert restored.resources.audit_risk == 44
    assert restored.introduced_character_ids == ["vince_bellandi", "evelyn_marsh"]


def test_player_facing_character_content_never_uses_legacy_names_or_ids(content) -> None:
    public_fragments = []
    for character in content.characters.people:
        public_fragments.extend(
            [
                character.name,
                character.role,
                character.origin,
                character.public_detail,
                character.interaction_reason,
            ]
        )
    for scene in [
        *content.scenes.scenes,
        *content.first_rotation.scenes,
        *content.eleventh_narrative.scenes,
    ]:
        public_fragments.extend(
            [
                scene.speaker,
                scene.title,
                scene.text,
                *(item.text for item in scene.conditional_paragraphs),
            ]
        )
        if scene.setup is not None:
            public_fragments.extend([scene.setup.speaker, scene.setup.title, scene.setup.text])
    public_fragments.extend(item.text for item in content.hedge_narrative.briefings)
    public_fragments.extend(
        [
            content.treasury_scenarios.scenarios[0].crisis_text,
            content.treasury_scenarios.scenarios[0].no_position_crisis_text,
            *(item.text for item in content.audit_scenario.scenes),
            *(item.text for item in content.diligence_scenario.scenes),
        ]
    )
    player_facing = "\n".join(public_fragments)

    for forbidden in (
        "Dom Bellini",
        "Vince Rourke",
        "dom_bellini",
        "vince_rourke",
        "commercial counterparty",
        "his supply relationship",
        "Dom wants his supply payment",
    ):
        assert forbidden not in player_facing
    assert "Dominic “Dom” Bellandi" in player_facing
    assert "founder and chairman" in player_facing.casefold()
    assert "Dom's nephew" in player_facing


def test_additional_personal_reveals_require_their_intended_prior_choices(
    content,
) -> None:
    state = _state(content)
    narrative = NarrativeEngine(content)
    evelyn_text = "Evelyn stayed in Milwaukee partly to help an aging aunt"
    cal_text = "A score update from his nephew's hockey game"

    assert evelyn_text not in narrative.resolved_scene_text(state, "ec_risk_emphasis")
    state.completed = True
    commodity = CommodityEngine(content)
    commodity.open_hedge(state, "no_hedge")
    narrative.choose(state, "hedge_documentation", "write_accurate_hedge_memo")
    assert evelyn_text in narrative.resolved_scene_text(state, "ec_risk_emphasis")

    commodity.settle_remaining(state)
    EleventhContractEngine(content).initialize(state)
    assert cal_text not in narrative.resolved_scene_text(
        state,
        "ec_exception_disposition",
    )
    narrative.choose(state, "ec_verification", "ec_call_cal_privately")
    assert cal_text in narrative.resolved_scene_text(
        state,
        "ec_exception_disposition",
    )
