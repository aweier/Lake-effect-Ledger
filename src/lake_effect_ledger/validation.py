"""Standalone YAML and cross-reference validation command."""

from decimal import Decimal
from pathlib import Path

from lake_effect_ledger.applied_foundations.engine import AppliedFoundationsEngine
from lake_effect_ledger.commodity.engine import (
    buyer_physical_purchase_cost_variance,
    combined_economic_result,
    contract_count,
    contract_month_spread,
    delivery_contract_value,
    futures_daily_pnl,
    margin_call_amount,
    regional_price,
)
from lake_effect_ledger.commodity.models import PositionSide, money
from lake_effect_ledger.learning.calculations import calculate_answer
from lake_effect_ledger.learning.models import KnowledgeCheckType
from lake_effect_ledger.narrative.models import ContentBundle


def main() -> None:
    content_root = Path(__file__).resolve().parent / "content"
    content = ContentBundle.load(content_root)
    milestone_1_choices = sum(len(scene.choices) for scene in content.scenes.scenes)
    documentation_choices = len(content.hedge_narrative.documentation_scene.choices)
    rotation_choices = sum(len(scene.choices) for scene in content.first_rotation.scenes)
    eleventh_choices = sum(len(scene.choices) for scene in content.eleventh_narrative.scenes)
    audit_choices = sum(len(scene.choices) for scene in content.audit_scenario.scenes)
    diligence_choices = sum(len(scene.choices) for scene in content.diligence_scenario.scenes)
    applied_choices = sum(
        len(decision.choices) for decision in content.applied_foundations.decisions
    )
    notice_choices = sum(len(decision.choices) for decision in content.notice_window.decisions)
    applied_checks = [
        item.as_knowledge_check() for item in content.applied_foundations.all_questions
    ]
    notice_checks = [item.as_knowledge_check() for item in content.notice_window.all_questions]
    all_checks = [
        *content.prologue.checks,
        *content.eleventh_learning.checks,
        *content.audit_learning.checks,
        *content.diligence_learning.checks,
        *applied_checks,
        *notice_checks,
    ]
    numeric_checks = [item for item in all_checks if item.check_type == KnowledgeCheckType.NUMERIC]
    decision_scenes = (
        len(content.scenes.scenes)
        + len(content.first_rotation.scenes)
        + 1
        + len(content.eleventh_narrative.scenes)
        + len(content.audit_scenario.scenes)
        + len(content.diligence_scenario.scenes)
        + len(content.applied_foundations.decisions)
        + len(content.notice_window.decisions)
    )
    total_choices = (
        milestone_1_choices
        + documentation_choices
        + rotation_choices
        + eleventh_choices
        + audit_choices
        + diligence_choices
        + applied_choices
        + notice_choices
    )
    applied_question_ids = {item.id for item in content.applied_foundations.all_questions}
    notice_question_ids = {item.id for item in content.notice_window.all_questions}
    for check in numeric_checks:
        answer = calculate_answer(check, content)
        if check.id in applied_question_ids:
            authored = content.applied_foundations.question(check.id)
            if answer != authored.expected_answer:
                raise ValueError(
                    f"Applied question {check.id} expected {authored.expected_answer}, "
                    f"but the shared engine produced {answer}"
                )
        if check.id in notice_question_ids:
            authored = content.notice_window.question(check.id)
            if answer != authored.expected_answer:
                raise ValueError(
                    f"Notice Window question {check.id} expected {authored.expected_answer}, "
                    f"but the shared engine produced {answer}"
                )
    _validate_applied_formulas(content)
    _validate_notice_formulas(content)
    print(  # noqa: T201 - this module is intentionally a command-line validator
        "Content valid: "
        f"{decision_scenes} decision scene(s), "
        f"{total_choices} choice(s), "
        f"{len(content.events.events)} delayed event(s), "
        f"{len(content.lessons.lessons)} lesson(s), "
        f"{len(content.game_modes.modes)} game mode(s), "
        f"{len(content.game_modes.campaign_tracks)} campaign track(s), "
        f"{len(content.characters.people) - 1} recurring character(s), "
        f"{len(content.curriculum.objectives)} mapped objective(s), "
        f"{len(content.curriculum.review_questions)} core review question(s), "
        f"{len(content.applied_foundations.decisions)} Applied decision(s), "
        f"{len(content.applied_foundations.checks)} Applied day check(s), "
        f"{len(content.applied_foundations.review.required)} required Applied review "
        "question(s), "
        f"{len(content.applied_foundations.review.remediation)} Applied remediation "
        "question(s), "
        f"{len(content.applied_foundations.record_chain)} Applied lifecycle record(s), "
        f"{len(content.notice_window.decisions)} Notice Window decision(s), "
        f"{len(content.notice_window.checks)} Notice Window day check(s), "
        f"{len(content.notice_window.review.required)} required Notice review question(s), "
        f"{len(content.notice_window.review.remediation)} Notice remediation question(s), "
        f"{len(content.notice_window.record_chain)} Notice lifecycle record(s), "
        f"{len(content.curriculum.future_topics)} future topic(s), "
        f"{len(all_checks)} knowledge check(s), "
        f"{len(numeric_checks)} validated calculation(s), "
        f"{len(content.glossary.terms)} glossary term(s), "
        f"{len(content.sources.sources)} source(s), "
        f"{len(content.commodity_contracts.contracts)} futures contract(s), "
        f"{len(content.commodity_price_paths.price_paths)} price path(s), "
        f"{len(content.hedge_scenarios.scenarios)} hedge scenario(s), "
        f"{len(content.treasury_scenarios.scenarios)} treasury scenario(s), "
        f"{len(content.eleventh_scenario.possible_outcomes)} Eleventh outcome(s), "
        f"{len(content.audit_scenario.control_objectives)} audit control(s), "
        f"{len(content.audit_scenario.possible_outcomes)} No Surprises outcome(s), "
        f"{len(content.diligence_scenario.possible_outcomes)} "
        "Diligence Room outcome(s)."
    )


def _validate_applied_formulas(content: ContentBundle) -> None:
    blueprint = content.applied_foundations
    scenario = blueprint.scenario
    contract = content.commodity_contract(scenario.contract_id)
    if scenario.contract_size_mmbtu != contract.contract_size_mmbtu:
        raise ValueError("Applied contract size disagrees with the authoritative contract")
    initial_chicago = regional_price(
        scenario.initial_henry_hub_price,
        scenario.initial_chicago_basis,
    )
    final_chicago = regional_price(
        scenario.final_henry_hub_price,
        scenario.final_chicago_basis,
    )
    physical = buyer_physical_purchase_cost_variance(
        initial_regional_price=initial_chicago,
        final_regional_price=final_chicago,
        physical_quantity_mmbtu=scenario.physical_requirement_mmbtu,
    )
    futures = futures_daily_pnl(
        side=PositionSide.LONG,
        previous_settlement=scenario.initial_henry_hub_price,
        current_settlement=scenario.final_henry_hub_price,
        contract_size_mmbtu=contract.contract_size_mmbtu,
        contracts=scenario.authorized_contracts,
    )
    initial_margin = money(scenario.initial_margin_per_contract * scenario.authorized_contracts)
    maintenance = money(scenario.maintenance_margin_per_contract * scenario.authorized_contracts)
    post_settlement = money(initial_margin + futures)
    calculated = {
        "contract_count": contract_count(
            physical_quantity_mmbtu=scenario.physical_requirement_mmbtu,
            contract_size_mmbtu=contract.contract_size_mmbtu,
        ),
        "initial_chicago_price": initial_chicago,
        "final_chicago_price": final_chicago,
        "physical_purchase_cost_variance": physical,
        "long_futures_result": futures,
        "buyer_basis_effect": money(
            (scenario.initial_chicago_basis - scenario.final_chicago_basis)
            * scenario.physical_requirement_mmbtu
        ),
        "combined_economic_result": combined_economic_result(
            physical_variance=physical,
            futures_result=futures,
        ),
        "initial_margin": initial_margin,
        "maintenance_margin": maintenance,
        "post_settlement_margin": post_settlement,
        "margin_call": margin_call_amount(
            balance=post_settlement,
            initial_requirement=initial_margin,
            maintenance_requirement=maintenance,
        ),
    }
    authored = {item.id: item.expected for item in blueprint.formulas}
    if authored != calculated:
        raise ValueError(
            f"Applied formula blueprint disagrees with shared Decimal results: "
            f"authored={authored}, calculated={calculated}"
        )
    AppliedFoundationsEngine(content).evaluate_order_tape()


def _validate_notice_formulas(content: ContentBundle) -> None:
    blueprint = content.notice_window
    scenario = blueprint.scenario
    contract = content.commodity_contract(scenario.contract_id)
    if scenario.contract_size_mmbtu != contract.contract_size_mmbtu:
        raise ValueError("Notice Window contract size disagrees with the authoritative contract")
    normal_spread = contract_month_spread(
        nearby_price=scenario.normal_curve.nearby_price,
        deferred_price=scenario.normal_curve.deferred_price,
    )
    inverted_spread = contract_month_spread(
        nearby_price=scenario.inverted_curve.nearby_price,
        deferred_price=scenario.inverted_curve.deferred_price,
    )
    calculated = {
        "normal_curve_spread": normal_spread,
        "carry_residual": normal_spread - scenario.authored_carry_estimate,
        "inverted_curve_spread": inverted_spread,
        "local_position_quantity": (
            Decimal(scenario.open_contracts) * scenario.contract_size_mmbtu
        ),
        "final_open_contracts": Decimal(scenario.open_contracts - scenario.offset_contracts),
        "sample_delivery_value": delivery_contract_value(
            settlement_price=Decimal("4.875"),
            contract_size_mmbtu=scenario.contract_size_mmbtu,
            contracts=3,
        ),
    }
    authored = {item.id: item.expected for item in blueprint.formulas}
    if authored != calculated:
        raise ValueError(
            "Notice Window formula blueprint disagrees with shared Decimal results: "
            f"authored={authored}, calculated={calculated}"
        )


if __name__ == "__main__":
    main()
