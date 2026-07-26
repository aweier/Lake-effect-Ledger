"""Standalone YAML and cross-reference validation command."""

from pathlib import Path

from lake_effect_ledger.learning.calculations import calculate_answer
from lake_effect_ledger.learning.models import KnowledgeCheckType
from lake_effect_ledger.narrative.models import ContentBundle


def main() -> None:
    content_root = Path(__file__).resolve().parents[2] / "content"
    content = ContentBundle.load(content_root)
    milestone_1_choices = sum(len(scene.choices) for scene in content.scenes.scenes)
    documentation_choices = len(content.hedge_narrative.documentation_scene.choices)
    rotation_choices = sum(len(scene.choices) for scene in content.first_rotation.scenes)
    eleventh_choices = sum(len(scene.choices) for scene in content.eleventh_narrative.scenes)
    all_checks = [*content.prologue.checks, *content.eleventh_learning.checks]
    numeric_checks = [item for item in all_checks if item.check_type == KnowledgeCheckType.NUMERIC]
    decision_scenes = (
        len(content.scenes.scenes)
        + len(content.first_rotation.scenes)
        + 1
        + len(content.eleventh_narrative.scenes)
    )
    for check in numeric_checks:
        calculate_answer(check, content)
    print(  # noqa: T201 - this module is intentionally a command-line validator
        "Content valid: "
        f"{decision_scenes} decision scene(s), "
        f"{milestone_1_choices + documentation_choices + rotation_choices + eleventh_choices} "
        "choice(s), "
        f"{len(content.events.events)} delayed event(s), "
        f"{len(content.lessons.lessons)} lesson(s), "
        f"{len(content.game_modes.modes)} game mode(s), "
        f"{len(all_checks)} knowledge check(s), "
        f"{len(numeric_checks)} validated calculation(s), "
        f"{len(content.glossary.terms)} glossary term(s), "
        f"{len(content.sources.sources)} source(s), "
        f"{len(content.commodity_contracts.contracts)} futures contract(s), "
        f"{len(content.commodity_price_paths.price_paths)} price path(s), "
        f"{len(content.hedge_scenarios.scenarios)} hedge scenario(s), "
        f"{len(content.treasury_scenarios.scenarios)} treasury scenario(s), "
        f"{len(content.eleventh_scenario.possible_outcomes)} Eleventh outcome(s)."
    )


if __name__ == "__main__":
    main()
