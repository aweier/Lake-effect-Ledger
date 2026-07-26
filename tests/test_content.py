from decimal import Decimal

from lake_effect_ledger.narrative.models import ContentBundle


def test_all_yaml_loads_and_cross_references_validate(content_root) -> None:
    bundle = ContentBundle.load(content_root)
    scene = bundle.scene("december_difference")

    assert scene.discrepancy.difference_mmbtu == 2500
    assert scene.discrepancy.exposure == Decimal("12000")
    assert len(scene.choices) == 4
    assert {choice.id for choice in scene.choices} == {
        "book_line_loss",
        "record_temporary_imbalance",
        "request_meter_support",
        "escalate_to_controller",
    }


def test_every_choice_has_immediate_and_scheduled_effects(content) -> None:
    scene = content.scene("december_difference")
    for choice in scene.choices:
        assert len(choice.effects) >= 2
        assert any(effect.type == "schedule_event" for effect in choice.effects)
