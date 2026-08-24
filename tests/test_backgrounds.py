import re
from copy import deepcopy
from decimal import Decimal
from io import StringIO

import pytest
from questionary import Choice
from rich.console import Console
from typer.testing import CliRunner

import lake_effect_ledger.cli as cli
from lake_effect_ledger.cli import app
from lake_effect_ledger.commodity.engine import CommodityEngine
from lake_effect_ledger.game import create_new_game
from lake_effect_ledger.learning.engine import LearningEngine
from lake_effect_ledger.learning.models import CampaignTrack, GameMode, LearningStatus
from lake_effect_ledger.learning.presentation import (
    render_background_orientation,
    render_notebook,
)
from lake_effect_ledger.narrative.engine import NarrativeEngine
from lake_effect_ledger.narrative.models import CharacterFile
from lake_effect_ledger.persistence.saves import SaveRepository
from lake_effect_ledger.presentation import render_background_selection
from lake_effect_ledger.state import Background

runner = CliRunner()

EXPECTED_SKILLS = {
    Background.ACCOUNTING: (8, 4, 5),
    Background.FINANCE: (5, 8, 4),
    Background.DATA_ANALYTICS: (4, 5, 8),
}
EXPECTED_ACKNOWLEDGMENTS = {
    Background.ACCOUNTING: "Futures language and the cash timing behind it",
    Background.FINANCE: "the record, evidence, and controls are part of the work",
    Background.DATA_ANALYTICS: "contract, commercial exposure, and accounting record",
}
CORE_CHECK_IDS = (
    "d1_futures_pnl",
    "d1_tick_value",
    "d2_regional_price",
    "d2_hedge_ratio",
    "d3_margin_call_amount",
)


def _core_state(content, background: Background):
    return create_new_game(
        name="Background Tester",
        background=background,
        seed=1728,
        content=content,
        game_mode=GameMode.GUIDED,
        campaign_track=CampaignTrack.SERIES_3_CORE,
    )


def _normalize(text: str) -> str:
    without_panel_borders = re.sub(r"[\u2500-\u257f]", " ", text)
    return re.sub(r"\s+", " ", without_panel_borders).strip()


def test_backgrounds_keep_canonical_skills_neutral_start_and_shared_access(content) -> None:
    states = {background: _core_state(content, background) for background in Background}

    for background, state in states.items():
        definition = content.background(background)
        assert (
            definition.skills.accounting,
            definition.skills.markets,
            definition.skills.analytics,
        ) == EXPECTED_SKILLS[background]
        assert definition.personal_cash == Decimal("2600")
        assert definition.resource_adjustments == {}
        assert state.personal_cash == Decimal("2600")
        assert state.player.role == "Junior Commodity Risk Analyst"
        assert state.campaign_track == CampaignTrack.SERIES_3_CORE
        assert {progress.status for progress in state.learning.objectives.values()} == {
            LearningStatus.INTRODUCED
        }

    assert len({tuple(state.resources.model_dump().items()) for state in states.values()}) == 1
    assert {
        tuple(content.campaign_track(state.campaign_track).chapter_ids) for state in states.values()
    } == {
        (
            "first_rotation",
            "december_difference",
            "hedge_book",
            "two_oclock_call",
            "eleventh_contract",
        )
    }


def test_selection_screen_is_distinct_complete_and_terminal_sized(content) -> None:
    output = StringIO()
    console = Console(file=output, force_terminal=False, color_system=None, width=80)

    render_background_selection(console, content.characters)

    rendered = output.getvalue()
    normalized = _normalize(rendered)
    selection = content.characters.background_selection
    assert selection.question == "What training did you bring to Northstar?"
    assert "same Junior Commodity Risk Analyst rotation" in normalized
    assert (
        "There is no best background. Your choice changes the perspective and "
        "support used to introduce concepts—not the correct answers or available "
        "story paths."
    ) in normalized
    assert max(map(len, rendered.splitlines())) <= 80
    for background in content.characters.backgrounds:
        for text in (
            background.description,
            background.prior_experience,
            background.starting_strength,
            background.learning_edge,
            background.hiring_reason,
        ):
            assert _normalize(text) in normalized
        skills = background.skills
        assert (
            f"Accounting {skills.accounting} · Markets {skills.markets} · "
            f"Analytics {skills.analytics}"
        ) in normalized


@pytest.mark.parametrize(
    "background",
    list(Background),
)
def test_first_rotation_acknowledges_background_without_changing_state(
    content,
    background: Background,
) -> None:
    state = _core_state(content, background)
    protected_state = deepcopy(state.model_dump(mode="json"))
    protected_checks = [check.model_dump(mode="json") for check in content.prologue.checks]
    protected_answers = {
        check_id: LearningEngine(content).expected_answer(check_id) for check_id in CORE_CHECK_IDS
    }
    output = StringIO()

    render_background_orientation(
        Console(file=output, force_terminal=False, color_system=None, width=90),
        state,
        content,
    )

    rendered = _normalize(output.getvalue())
    definition = content.background(background)
    assert "accounting, markets, operations, treasury, and data systems" in rendered
    assert EXPECTED_ACKNOWLEDGMENTS[background] in rendered
    assert _normalize(definition.first_rotation_acknowledgment) in rendered
    assert _normalize(definition.teaching_frame) in rendered
    assert state.model_dump(mode="json") == protected_state
    assert [check.model_dump(mode="json") for check in content.prologue.checks] == (
        protected_checks
    )
    assert {
        check_id: LearningEngine(content).expected_answer(check_id) for check_id in CORE_CHECK_IDS
    } == protected_answers


def test_notebook_labels_starting_perspective_as_familiarity_not_mastery(content) -> None:
    state = _core_state(content, Background.ACCOUNTING)
    output = StringIO()

    render_notebook(
        Console(file=output, force_terminal=False, color_system=None, width=100),
        state,
        content,
    )

    rendered = _normalize(output.getvalue())
    assert "Your Starting Perspective" in rendered
    assert "Accounting" in rendered
    assert "Familiarity is not demonstrated mastery" in rendered
    assert state.learning.objectives["double_entry"].status == LearningStatus.INTRODUCED


def test_same_seed_and_decisions_have_identical_financial_results(content) -> None:
    results = []
    for background in Background:
        state = create_new_game(
            name="Equivalent Analyst",
            background=background,
            seed=1728,
            content=content,
            campaign_track=CampaignTrack.SERIES_3_CORE,
            skip_prologue=True,
        )
        narrative = NarrativeEngine(content)
        narrative.choose(state, "december_difference", "request_meter_support")
        narrative.process_end_of_day(state)
        commodity = CommodityEngine(content)
        commodity.open_hedge(state, "hedge_100")
        narrative.choose(
            state,
            "hedge_documentation",
            "write_accurate_hedge_memo",
        )
        commodity.settle_remaining(state)
        results.append(
            {
                "corporate_cash": state.corporate_cash,
                "personal_cash": state.personal_cash,
                "margin_due": state.margin_due,
                "ledger": state.ledger.model_dump(mode="json"),
                "market": state.market.model_dump(mode="json"),
                "resources": state.resources.model_dump(mode="json"),
                "decisions": state.decisions,
                "hedge_book": state.hedge_book.model_dump(mode="json"),
            }
        )

    assert results[1:] == results[:-1]


def test_background_copy_validation_rejects_comparative_framing(content) -> None:
    payload = content.characters.model_dump(mode="json")
    payload["backgrounds"][0]["learning_edge"] = "This is the easy route."

    with pytest.raises(ValueError, match="comparative framing"):
        CharacterFile.model_validate(payload)


def test_existing_v9_save_loads_without_background_metadata_in_state(
    content,
    tmp_path,
) -> None:
    state = _core_state(content, Background.FINANCE)
    repository = SaveRepository(tmp_path / "background-v9.db")
    repository.save(state)

    restored = repository.load()

    assert restored.save_schema_version == 9
    assert restored.player == state.player
    assert restored.resources == state.resources
    assert restored.personal_cash == state.personal_cash
    assert "starting_strength" not in restored.model_dump(mode="json")


@pytest.mark.parametrize("background", list(Background))
def test_scripted_character_creation_preserves_each_background(
    content,
    tmp_path,
    background: Background,
) -> None:
    database = tmp_path / f"{background.value}.db"

    result = runner.invoke(
        app,
        [
            "--quick-start",
            "--name",
            "Scripted Analyst",
            "--background",
            background.value,
            "--game-mode",
            "guided",
            "--campaign-track",
            "series3_core",
            "--prologue-strategy",
            "correct",
            "--prologue-days",
            "1",
            "--save-db",
            str(database),
        ],
    )

    assert result.exit_code == 0, result.output
    assert EXPECTED_ACKNOWLEDGMENTS[background] in _normalize(result.output)
    restored = SaveRepository(database).load()
    assert restored.player.background == background
    assert restored.player.role == "Junior Commodity Risk Analyst"


def test_interactive_background_selection_uses_natural_prompt(
    content,
    monkeypatch,
) -> None:
    captured = {}
    output = StringIO()

    class FakePrompt:
        def ask(self):
            return Background.FINANCE.value

    def fake_select(message, choices):
        captured["message"] = message
        captured["choices"] = choices
        return FakePrompt()

    monkeypatch.setattr(cli, "console", Console(file=output, force_terminal=False, width=80))
    monkeypatch.setattr(cli.questionary, "select", fake_select)

    selected = cli._select_background(content)

    assert selected == Background.FINANCE
    assert captured["message"] == "What training did you bring to Northstar?"
    assert [
        (choice.title, choice.value) for choice in captured["choices"] if isinstance(choice, Choice)
    ] == [
        ("Accounting", "accounting"),
        ("Finance", "finance"),
        ("Data analytics", "data_analytics"),
    ]
    assert "There is no best background" in output.getvalue()


def test_background_rendering_is_clean_when_output_is_redirected(content) -> None:
    output = StringIO()
    console = Console(file=output, force_terminal=False, color_system=None, width=80)
    render_background_selection(console, content.characters)
    for background in Background:
        render_background_orientation(console, _core_state(content, background), content)

    rendered = output.getvalue()
    assert "\ufffd" not in rendered
    assert "\x1b" not in rendered
