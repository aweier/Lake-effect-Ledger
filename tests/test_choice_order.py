from lake_effect_ledger.game import create_new_game
from lake_effect_ledger.learning.choice_order import ordered_check_options
from lake_effect_ledger.persistence.saves import SaveRepository
from lake_effect_ledger.state import Background


def _choice_checks(content):
    return [
        check
        for check in [
            *content.prologue.checks,
            *content.eleventh_learning.checks,
            *content.audit_learning.checks,
            *content.diligence_learning.checks,
            *[item.as_knowledge_check() for item in content.applied_foundations.all_questions],
            *[item.as_knowledge_check() for item in content.notice_window.all_questions],
        ]
        if check.options
    ]


def test_choice_order_is_stable_for_a_save_without_mutating_content(content) -> None:
    check = content.knowledge_check("ec_offset_preserves_history")
    authored_ids = [item.id for item in check.options]

    first = [item.id for item in ordered_check_options(check, game_seed=1728)]
    repeated = [item.id for item in ordered_check_options(check, game_seed=1728)]

    assert first == repeated
    assert first != authored_ids
    assert [item.id for item in check.options] == authored_ids


def test_choice_order_varies_between_new_game_seeds(content) -> None:
    check = content.knowledge_check("ec_current_overhedge")
    orders = {
        tuple(item.id for item in ordered_check_options(check, game_seed=seed))
        for seed in range(12)
    }

    assert len(orders) > 1


def test_choice_order_survives_save_and_reload(content, tmp_path) -> None:
    state = create_new_game(
        name="Order Tester",
        background=Background.FINANCE,
        seed=31415,
        content=content,
    )
    check = content.knowledge_check("ec_records_ethics")
    before = [item.id for item in ordered_check_options(check, game_seed=state.seed)]
    repository = SaveRepository(tmp_path / "choice-order.db")
    repository.save(state)

    restored = repository.load()
    after = [item.id for item in ordered_check_options(check, game_seed=restored.seed)]

    assert after == before


def test_correct_answers_are_distributed_across_positions(content) -> None:
    positions = []
    for check in _choice_checks(content):
        option_ids = [item.id for item in ordered_check_options(check, game_seed=1728)]
        positions.append(option_ids.index(check.correct_option_id))

    assert len(set(positions)) >= 3
    assert positions.count(0) < len(positions)
