"""Typer entry point and Questionary interaction layer."""

from __future__ import annotations

import secrets
import sys
from decimal import Decimal
from pathlib import Path
from typing import Annotated

import questionary
import typer
from pydantic import ValidationError
from questionary import Choice
from rich.console import Console
from rich.panel import Panel

from lake_effect_ledger.applied_foundations.engine import AppliedFoundationsEngine
from lake_effect_ledger.applied_foundations.models import AppliedSeasonStatus
from lake_effect_ledger.applied_foundations.presentation import (
    render_applied_day,
    render_applied_debrief,
    render_applied_diagnostic,
    render_decision_result,
    render_financial_bridge,
    render_order_tape,
    render_season_opening,
)
from lake_effect_ledger.applied_foundations.review import AppliedReviewEngine
from lake_effect_ledger.audit.engine import InternalAuditEngine
from lake_effect_ledger.audit.models import AuditStage
from lake_effect_ledger.audit.presentation import (
    render_audit_request_list,
    render_audit_scene,
    render_control_results,
    render_internal_audit_report,
    render_preliminary_findings,
    render_walkthrough_timeline,
)
from lake_effect_ledger.audit.report import build_internal_audit_report
from lake_effect_ledger.commodity.engine import CommodityEngine
from lake_effect_ledger.commodity.models import DocumentationQuality
from lake_effect_ledger.commodity.presentation import (
    render_documentation_scene,
    render_hedge_book_report,
    render_hedge_briefings,
    render_hedge_ticket,
    render_position_book,
    render_settlement_day,
)
from lake_effect_ledger.diligence.engine import DiligenceEngine
from lake_effect_ledger.diligence.models import DiligenceStage
from lake_effect_ledger.diligence.presentation import (
    render_diligence_room_report,
    render_diligence_scene,
    render_package_versions,
    render_q_and_a,
    render_request_list,
    render_risk_schedule,
    render_scenario_analysis,
)
from lake_effect_ledger.diligence.report import build_diligence_room_report
from lake_effect_ledger.education.hedge_report import build_hedge_book_report
from lake_effect_ledger.education.report import build_learning_report
from lake_effect_ledger.game import create_new_game
from lake_effect_ledger.learning.choice_order import ordered_check_options
from lake_effect_ledger.learning.core import (
    CoreReviewEngine,
    build_core_debrief,
    chapter_calculation_lines,
)
from lake_effect_ledger.learning.engine import LearningEngine
from lake_effect_ledger.learning.models import (
    CampaignTrack,
    GameMode,
    KnowledgeCheckType,
    ReviewStyle,
    ShowMathMode,
)
from lake_effect_ledger.learning.presentation import (
    render_background_orientation,
    render_check,
    render_check_math,
    render_core_chapter_debrief,
    render_core_chapter_opening,
    render_core_debrief,
    render_core_review_diagnostic,
    render_day,
    render_notebook,
)
from lake_effect_ledger.learning.snapshots import finalize_core_snapshot
from lake_effect_ledger.narrative.engine import NarrativeEngine
from lake_effect_ledger.narrative.models import ContentBundle
from lake_effect_ledger.notice_window.engine import NoticeWindowEngine
from lake_effect_ledger.notice_window.models import NoticeWindowStatus
from lake_effect_ledger.notice_window.presentation import (
    render_notice_calendar,
    render_notice_curves,
    render_notice_day,
    render_notice_debrief,
    render_notice_decision_result,
    render_notice_diagnostic,
    render_notice_opening,
    render_notice_resolution,
)
from lake_effect_ledger.notice_window.review import NoticeWindowReviewEngine
from lake_effect_ledger.persistence.saves import SaveRepository
from lake_effect_ledger.presentation import (
    NORTHSTAR_HEADQUARTERS,
    render_background_selection,
    render_character_introduction,
    render_dashboard,
    render_debug,
    render_end_of_day,
    render_learning_report,
    render_scene,
    render_title,
)
from lake_effect_ledger.state import Background, GameState
from lake_effect_ledger.trading.engine import EleventhContractEngine
from lake_effect_ledger.trading.presentation import (
    render_case_file,
    render_chapter_scene,
    render_live_week_brief,
    render_order_and_authorization,
    render_trade_blotter,
)
from lake_effect_ledger.trading.report import build_analyst_case_file
from lake_effect_ledger.treasury.engine import TreasuryEngine
from lake_effect_ledger.treasury.models import FundingChoice, NotificationChoice
from lake_effect_ledger.treasury.presentation import (
    render_funding_choices,
    render_treasury_crisis,
    render_treasury_report,
)
from lake_effect_ledger.treasury.report import build_treasury_report

DEFAULT_CONTENT_ROOT = Path(__file__).resolve().parent / "content"
DEFAULT_SAVE_DATABASE = Path("saves") / "lake_ledger.db"
SCENE_ID = "december_difference"
HEDGE_DOCUMENTATION_SCENE_ID = "hedge_documentation"
PROLOGUE_CHARACTER_IDS = {
    "rotation_day_1_board": ("evelyn_marsh", "marisol_vega"),
    "rotation_day_2_basis": ("tj_morrow", "kasia_zielinska"),
    "rotation_day_3_call": ("darren_cho", "june_halvorsen"),
}
CHAPTER_DAY_SCENES = {
    1: (
        "ec_volume_language",
        "ec_hedge_recommendation",
        "ec_risk_emphasis",
        "ec_ask_marisol",
    ),
    2: ("ec_order_type", "ec_authorization_review"),
    3: (
        "ec_record_handling",
        "ec_verification",
        "ec_exception_disposition",
        "ec_position_action",
        "ec_fish_fry",
        "eleventh_episode_transition",
    ),
}
CHAPTER_PATH_CHOICES = {
    "formal_correction": {
        "ec_volume_language": "ec_distinguish_confirmed_volume",
        "ec_hedge_recommendation": "ec_recommend_hold_ten",
        "ec_risk_emphasis": "ec_emphasize_authorization",
        "ec_ask_marisol": "ec_ask_marisol_before_recommendation",
        "ec_order_type": "ec_recommend_sell_limit",
        "ec_authorization_review": "ec_accept_ten_contract_authorization",
        "ec_record_handling": "ec_flag_and_preserve_originals",
        "ec_verification": "ec_verify_with_fcm",
        "ec_exception_disposition": "ec_notify_evelyn_formally",
        "ec_position_action": "ec_offset_with_formal_approval",
        "ec_fish_fry": "ec_tell_evelyn_boundary",
        "eleventh_episode_transition": "ec_close_case_file",
    },
    "marisol_supported": {
        "ec_volume_language": "ec_distinguish_confirmed_volume",
        "ec_hedge_recommendation": "ec_recommend_wait_for_support",
        "ec_risk_emphasis": "ec_emphasize_volume_uncertainty",
        "ec_ask_marisol": "ec_ask_marisol_before_recommendation",
        "ec_order_type": "ec_recommend_market_order",
        "ec_authorization_review": "ec_accept_ten_contract_authorization",
        "ec_record_handling": "ec_create_linked_working_annotation",
        "ec_verification": "ec_validate_with_marisol",
        "ec_exception_disposition": "ec_notify_evelyn_formally",
        "ec_position_action": "ec_leave_open_under_exception",
        "ec_fish_fry": "ec_join_marisol_at_bar",
        "eleventh_episode_transition": "ec_close_case_file",
    },
    "cal_then_correct": {
        "ec_volume_language": "ec_call_extra_volume_probable",
        "ec_hedge_recommendation": "ec_recommend_eleventh_contract",
        "ec_risk_emphasis": "ec_emphasize_volume_uncertainty",
        "ec_ask_marisol": "ec_send_without_marisol_confirmation",
        "ec_order_type": "ec_recommend_market_order",
        "ec_authorization_review": "ec_request_authorization_revision",
        "ec_record_handling": "ec_flag_and_preserve_originals",
        "ec_verification": "ec_call_cal_privately",
        "ec_exception_disposition": "ec_notify_evelyn_formally",
        "ec_position_action": "ec_offset_with_formal_approval",
        "ec_fish_fry": "ec_tell_evelyn_boundary",
        "eleventh_episode_transition": "ec_close_case_file",
    },
    "accept_cal": {
        "ec_volume_language": "ec_call_extra_volume_probable",
        "ec_hedge_recommendation": "ec_recommend_eleventh_contract",
        "ec_risk_emphasis": "ec_emphasize_basis",
        "ec_ask_marisol": "ec_send_without_marisol_confirmation",
        "ec_order_type": "ec_recommend_market_order",
        "ec_authorization_review": "ec_treat_brief_as_quantity_permission",
        "ec_record_handling": "ec_defer_exception_label",
        "ec_verification": "ec_call_cal_privately",
        "ec_exception_disposition": "ec_accept_cal_unsupported_explanation",
        "ec_position_action": "ec_leave_eleventh_open",
        "ec_fish_fry": "ec_accept_cal_introduction",
        "eleventh_episode_transition": "ec_close_case_file",
    },
    "certify_unresolved": {
        "ec_volume_language": "ec_present_full_volume_as_expected",
        "ec_hedge_recommendation": "ec_recommend_eleventh_contract",
        "ec_risk_emphasis": "ec_emphasize_liquidity",
        "ec_ask_marisol": "ec_send_without_marisol_confirmation",
        "ec_order_type": "ec_recommend_market_order",
        "ec_authorization_review": "ec_treat_brief_as_quantity_permission",
        "ec_record_handling": "ec_defer_exception_label",
        "ec_verification": "ec_call_cal_privately",
        "ec_exception_disposition": "ec_certify_unresolved_blotter",
        "ec_position_action": "ec_leave_eleventh_open",
        "ec_fish_fry": "ec_keep_social_distance",
        "eleventh_episode_transition": "ec_close_case_file",
    },
    "offset": {
        "ec_volume_language": "ec_distinguish_confirmed_volume",
        "ec_hedge_recommendation": "ec_recommend_hold_ten",
        "ec_risk_emphasis": "ec_emphasize_authorization",
        "ec_ask_marisol": "ec_ask_marisol_before_recommendation",
        "ec_order_type": "ec_recommend_sell_stop",
        "ec_authorization_review": "ec_accept_ten_contract_authorization",
        "ec_record_handling": "ec_flag_and_preserve_originals",
        "ec_verification": "ec_compare_all_records_first",
        "ec_exception_disposition": "ec_preserve_quiet_file",
        "ec_position_action": "ec_request_and_obtain_offset_approval",
        "ec_fish_fry": "ec_tell_evelyn_boundary",
        "eleventh_episode_transition": "ec_close_case_file",
    },
    "leave_open_fail": {
        "ec_volume_language": "ec_distinguish_confirmed_volume",
        "ec_hedge_recommendation": "ec_recommend_hold_ten",
        "ec_risk_emphasis": "ec_emphasize_basis",
        "ec_ask_marisol": "ec_ask_marisol_before_recommendation",
        "ec_order_type": "ec_recommend_sell_stop",
        "ec_authorization_review": "ec_accept_ten_contract_authorization",
        "ec_record_handling": "ec_flag_and_preserve_originals",
        "ec_verification": "ec_compare_all_records_first",
        "ec_exception_disposition": "ec_preserve_quiet_file",
        "ec_position_action": "ec_leave_eleventh_open",
        "ec_fish_fry": "ec_keep_social_distance",
        "eleventh_episode_transition": "ec_close_case_file",
    },
    "quiet_file": {
        "ec_volume_language": "ec_distinguish_confirmed_volume",
        "ec_hedge_recommendation": "ec_recommend_hold_ten",
        "ec_risk_emphasis": "ec_emphasize_authorization",
        "ec_ask_marisol": "ec_ask_marisol_before_recommendation",
        "ec_order_type": "ec_recommend_market_order",
        "ec_authorization_review": "ec_accept_ten_contract_authorization",
        "ec_record_handling": "ec_create_linked_working_annotation",
        "ec_verification": "ec_compare_all_records_first",
        "ec_exception_disposition": "ec_preserve_quiet_file",
        "ec_position_action": "ec_leave_eleventh_open",
        "ec_fish_fry": "ec_keep_social_distance",
        "eleventh_episode_transition": "ec_close_case_file",
    },
    "lucky_unapproved": {
        "ec_volume_language": "ec_call_extra_volume_probable",
        "ec_hedge_recommendation": "ec_recommend_eleventh_contract",
        "ec_risk_emphasis": "ec_emphasize_liquidity",
        "ec_ask_marisol": "ec_send_without_marisol_confirmation",
        "ec_order_type": "ec_recommend_market_order",
        "ec_authorization_review": "ec_treat_brief_as_quantity_permission",
        "ec_record_handling": "ec_defer_exception_label",
        "ec_verification": "ec_compare_all_records_first",
        "ec_exception_disposition": "ec_preserve_quiet_file",
        "ec_position_action": "ec_leave_eleventh_open",
        "ec_fish_fry": "ec_keep_social_distance",
        "eleventh_episode_transition": "ec_close_case_file",
    },
}
AUDIT_DAY_SCENES = {
    1: ("ns_package_scope", "ns_package_context", "ns_selection_notice"),
    2: ("ns_walkthrough_style", "ns_volume_source", "ns_responsibility"),
    3: ("ns_control_interpretation", "ns_finding_position"),
    4: (
        "ns_supplement_package",
        "ns_remediation_choice",
        "ns_management_response",
        "ns_exit_escalation",
    ),
}
_AUDIT_ACCURATE = {
    "ns_package_scope": "ns_send_complete_chain",
    "ns_package_context": "ns_add_clear_chronology",
    "ns_selection_notice": "ns_tell_evelyn_first",
    "ns_walkthrough_style": "ns_answer_accurately",
    "ns_volume_source": "ns_explain_recorded_volume",
    "ns_responsibility": "ns_accept_own_actions",
    "ns_control_interpretation": "ns_separate_design_operation",
    "ns_finding_position": "ns_agree_preliminary",
    "ns_supplement_package": "ns_confirm_complete_package",
    "ns_remediation_choice": "ns_recommend_three_way_match",
    "ns_management_response": "ns_response_agree",
    "ns_exit_escalation": "ns_elevate_disagreement",
}
AUDIT_PATH_CHOICES = {
    "full_disclosure": dict(_AUDIT_ACCURATE),
    "control_worked_late": {
        **_AUDIT_ACCURATE,
        "ns_package_scope": "ns_send_requested_only",
        "ns_walkthrough_style": "ns_answer_narrowly",
        "ns_remediation_choice": "ns_recommend_daily_review",
    },
    "supported_late": {
        **_AUDIT_ACCURATE,
        "ns_package_scope": "ns_send_requested_only",
        "ns_remediation_choice": "ns_recommend_support_gate",
        "ns_management_response": "ns_response_partial",
    },
    "protect_desk": {
        **_AUDIT_ACCURATE,
        "ns_package_scope": "ns_ask_evelyn_review",
        "ns_package_context": "ns_submit_minimal_context",
        "ns_selection_notice": "ns_inform_cal",
        "ns_walkthrough_style": "ns_answer_narrowly",
        "ns_volume_source": "ns_call_it_my_recommendation",
        "ns_responsibility": "ns_protect_cal",
        "ns_control_interpretation": "ns_call_isolated_error",
        "ns_finding_position": "ns_reject_without_evidence",
        "ns_supplement_package": "ns_keep_initial_scope",
        "ns_remediation_choice": "ns_recommend_daily_review",
        "ns_management_response": "ns_response_partial",
        "ns_exit_escalation": "ns_close_internally",
    },
    "quiet_supplement": {
        **_AUDIT_ACCURATE,
        "ns_package_scope": "ns_ask_evelyn_review",
        "ns_package_context": "ns_submit_minimal_context",
        "ns_walkthrough_style": "ns_acknowledge_uncertainty",
        "ns_responsibility": "ns_dispute_with_evidence",
        "ns_finding_position": "ns_dispute_supported_point",
        "ns_supplement_package": "ns_disclose_supplement",
        "ns_remediation_choice": "ns_recommend_daily_review",
    },
    "lucky_unauthorized": {
        **_AUDIT_ACCURATE,
        "ns_package_scope": "ns_send_requested_only",
        "ns_volume_source": "ns_explain_cal_expectation",
        "ns_remediation_choice": "ns_recommend_support_gate",
    },
    "no_physical_support": {
        **_AUDIT_ACCURATE,
        "ns_package_scope": "ns_send_requested_only",
        "ns_walkthrough_style": "ns_acknowledge_uncertainty",
        "ns_remediation_choice": "ns_recommend_daily_review",
    },
    "inaccurate": {
        **_AUDIT_ACCURATE,
        "ns_package_scope": "ns_ask_evelyn_review",
        "ns_package_context": "ns_submit_minimal_context",
        "ns_selection_notice": "ns_inform_cal",
        "ns_walkthrough_style": "ns_claim_process_followed",
        "ns_volume_source": "ns_call_it_my_recommendation",
        "ns_responsibility": "ns_protect_cal",
        "ns_control_interpretation": "ns_say_policy_sufficient",
        "ns_finding_position": "ns_reject_without_evidence",
        "ns_supplement_package": "ns_keep_initial_scope",
        "ns_remediation_choice": "ns_recommend_training",
        "ns_management_response": "ns_response_disagree",
        "ns_exit_escalation": "ns_close_internally",
    },
    "automated": {
        **_AUDIT_ACCURATE,
        "ns_volume_source": "ns_explain_cal_expectation",
    },
    "policy_only": {
        **_AUDIT_ACCURATE,
        "ns_package_scope": "ns_send_requested_only",
        "ns_package_context": "ns_submit_minimal_context",
        "ns_walkthrough_style": "ns_answer_narrowly",
        "ns_control_interpretation": "ns_say_policy_sufficient",
        "ns_finding_position": "ns_reject_without_evidence",
        "ns_remediation_choice": "ns_recommend_training",
        "ns_exit_escalation": "ns_close_internally",
    },
    "risk_acceptance": {
        **_AUDIT_ACCURATE,
        "ns_package_scope": "ns_send_requested_only",
        "ns_walkthrough_style": "ns_acknowledge_uncertainty",
        "ns_responsibility": "ns_dispute_with_evidence",
        "ns_finding_position": "ns_dispute_supported_point",
        "ns_remediation_choice": "ns_recommend_risk_acceptance",
        "ns_management_response": "ns_response_partial",
    },
}
DILIGENCE_DAY_SCENES = {
    1: ("dr_package_scope", "dr_exception_language", "dr_package_review"),
    2: ("dr_number_source", "dr_scenario_scope", "dr_remediation_status"),
    3: ("dr_buyer_answer", "dr_lender_answer", "dr_management_draft"),
    4: ("dr_inconsistency_action", "dr_committee_position", "dr_final_action"),
}
_DILIGENCE_CONSISTENT = {
    "dr_package_scope": "dr_send_complete_package",
    "dr_exception_language": "dr_include_exception_schedule",
    "dr_package_review": "dr_review_with_evelyn_noah",
    "dr_number_source": "dr_reconcile_all_sources",
    "dr_scenario_scope": "dr_include_full_sensitivities",
    "dr_remediation_status": "dr_label_actual_remediation",
    "dr_buyer_answer": "dr_answer_buyer_completely",
    "dr_lender_answer": "dr_answer_lender_completely",
    "dr_management_draft": "dr_correct_management_draft",
    "dr_inconsistency_action": "dr_issue_correction",
    "dr_committee_position": "dr_support_noah_chronology",
    "dr_final_action": "dr_final_correct_disclosure",
}
DILIGENCE_PATH_CHOICES = {
    "full_consistent": dict(_DILIGENCE_CONSISTENT),
    "limited_then_supplement": {
        **_DILIGENCE_CONSISTENT,
        "dr_package_scope": "dr_send_limited_package",
        "dr_exception_language": "dr_call_corrected_error",
        "dr_scenario_scope": "dr_include_sensitivity_summary",
        "dr_remediation_status": "dr_call_remediation_planned",
        "dr_lender_answer": "dr_refer_lender_to_june",
        "dr_inconsistency_action": "dr_issue_supplement",
    },
    "inconsistent_versions": {
        **_DILIGENCE_CONSISTENT,
        "dr_package_scope": "dr_send_linked_summary",
        "dr_exception_language": "dr_call_eleven_authorized",
        "dr_package_review": "dr_review_with_cal",
        "dr_number_source": "dr_use_later_support_monday",
        "dr_buyer_answer": "dr_answer_buyer_narrowly",
        "dr_inconsistency_action": "dr_leave_versions",
        "dr_final_action": "dr_final_stay_silent",
    },
    "remediation_overstated": {
        **_DILIGENCE_CONSISTENT,
        "dr_package_scope": "dr_send_linked_summary",
        "dr_package_review": "dr_review_with_cal",
        "dr_scenario_scope": "dr_include_sensitivity_summary",
        "dr_remediation_status": "dr_claim_remediation_implemented",
        "dr_buyer_answer": "dr_acknowledge_buyer_uncertainty",
        "dr_lender_answer": "dr_refer_lender_to_june",
    },
    "covenant_concern": {
        **_DILIGENCE_CONSISTENT,
        "dr_scenario_scope": "dr_escalate_scenario_assumptions",
    },
    "cal_aligned": {
        **_DILIGENCE_CONSISTENT,
        "dr_package_scope": "dr_send_limited_package",
        "dr_exception_language": "dr_call_corrected_error",
        "dr_package_review": "dr_review_with_cal",
        "dr_scenario_scope": "dr_include_sensitivity_summary",
        "dr_remediation_status": "dr_call_remediation_planned",
        "dr_buyer_answer": "dr_answer_buyer_narrowly",
        "dr_lender_answer": "dr_answer_lender_narrowly",
        "dr_management_draft": "dr_accept_preferred_draft",
        "dr_inconsistency_action": "dr_issue_supplement",
        "dr_committee_position": "dr_protect_cal_explanation",
    },
    "buyer_walks": {
        **_DILIGENCE_CONSISTENT,
        "dr_package_scope": "dr_send_limited_package",
        "dr_exception_language": "dr_call_eleven_authorized",
        "dr_package_review": "dr_review_with_cal",
        "dr_number_source": "dr_use_later_support_monday",
        "dr_scenario_scope": "dr_include_sensitivity_summary",
        "dr_remediation_status": "dr_claim_remediation_implemented",
        "dr_buyer_answer": "dr_answer_buyer_narrowly",
        "dr_lender_answer": "dr_answer_lender_narrowly",
        "dr_management_draft": "dr_accept_preferred_draft",
        "dr_inconsistency_action": "dr_leave_versions",
        "dr_committee_position": "dr_protect_cal_explanation",
        "dr_final_action": "dr_final_stay_silent",
    },
    "conditional_close": {
        **_DILIGENCE_CONSISTENT,
        "dr_package_scope": "dr_send_linked_summary",
        "dr_management_draft": "dr_escalate_management_draft",
        "dr_committee_position": "dr_acknowledge_incomplete_remediation",
        "dr_final_action": "dr_final_correct_disclosure",
    },
}

app = typer.Typer(
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=False,
    help="Play Lake Effect Ledger through The Diligence Room.",
)
console = Console()


def _configure_windows_utf8_output() -> None:
    """Keep Unicode narrative and Rich borders intact in terminals and pipes."""
    if sys.platform != "win32":
        return
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        encoding = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
        if encoding != "utf8" and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def _ask(prompt: object) -> object:
    result = prompt.ask()
    if result is None:
        raise typer.Exit()
    return result


def _stream_is_tty(stream: object) -> bool:
    isatty = getattr(stream, "isatty", None)
    if not callable(isatty):
        return False
    try:
        return bool(isatty())
    except OSError:
        return False


def _continuation_is_available() -> bool:
    """Return whether waiting and clearing are safe for this terminal."""
    return _stream_is_tty(sys.stdin) and console.is_terminal


def _continue_after_feedback(*, interactive: bool) -> bool:
    """Hold completed feedback on screen, then clear before the next unit."""
    if not interactive or not _continuation_is_available():
        return False
    console.print("[dim]Press Enter to continue...[/dim]", end="")
    try:
        if sys.stdin.readline() == "":
            raise typer.Exit()
    except KeyboardInterrupt as error:
        raise typer.Exit() from error
    console.clear()
    return True


def _introduce_characters(
    state: GameState,
    content: ContentBundle,
    *character_ids: str,
) -> None:
    for character_id in character_ids:
        if character_id in state.introduced_character_ids:
            continue
        render_character_introduction(console, content.character(character_id))
        state.introduced_character_ids.append(character_id)


def _introduce_speaker(
    state: GameState,
    content: ContentBundle,
    speaker: str,
) -> None:
    character = content.character_for_speaker(speaker)
    if character is not None and character.id != "player":
        _introduce_characters(state, content, character.id)


def _select_background(content: ContentBundle) -> Background:
    render_background_selection(console, content.characters)
    value = _ask(
        questionary.select(
            content.characters.background_selection.question,
            choices=[
                Choice(
                    title=item.label,
                    value=item.id.value,
                )
                for item in content.characters.backgrounds
            ],
        )
    )
    return Background(str(value))


def _select_game_mode(content: ContentBundle) -> GameMode:
    value = _ask(
        questionary.select(
            "Choose how to begin:",
            choices=[
                Choice(
                    title=(
                        f"{item.label}{' · Recommended' if item.recommended else ''}"
                        f" — {item.description}"
                    ),
                    value=item.id.value,
                )
                for item in content.game_modes.modes
            ],
        )
    )
    return GameMode(str(value))


def _select_campaign_track(content: ContentBundle) -> CampaignTrack:
    value = _ask(
        questionary.select(
            "Choose a campaign track:",
            choices=[
                Choice(
                    title=(
                        f"{item.label}{' · Recommended' if item.recommended else ''}"
                        f" — {item.description}"
                    ),
                    value=item.id.value,
                )
                for item in content.game_modes.campaign_tracks
            ],
        )
    )
    return CampaignTrack(str(value))


def _apply_requested_campaign_track(
    state: GameState,
    requested_track: CampaignTrack | None,
) -> None:
    """Allow explicit campaign expansion without permitting a saved game to regress."""
    if requested_track is None or requested_track == state.campaign_track:
        return
    rank = {
        CampaignTrack.SERIES_3_CORE: 0,
        CampaignTrack.APPLIED_FOUNDATIONS: 1,
        CampaignTrack.EXTENDED_STORY: 2,
    }
    if rank[requested_track] < rank[state.campaign_track]:
        raise typer.BadParameter(
            f"the autosave already uses the broader {state.campaign_track.value} track",
            param_hint="--campaign-track",
        )
    state.campaign_track = requested_track


def _new_interactive_game(
    content: ContentBundle,
    game_mode: GameMode | None = None,
    campaign_track: CampaignTrack | None = None,
) -> GameState:
    game_mode = game_mode or _select_game_mode(content)
    campaign_track = campaign_track or _select_campaign_track(content)
    name = str(
        _ask(
            questionary.text(
                "Your name:",
                validate=lambda value: bool(value.strip()) or "Enter a name.",
            )
        )
    )
    background = _select_background(content)
    seed = secrets.randbelow(2**31)
    return create_new_game(
        name=name,
        background=background,
        seed=seed,
        content=content,
        game_mode=game_mode,
        campaign_track=campaign_track,
    )


def _choose_prologue_story_interactively(content: ContentBundle) -> str:
    scene = content.scene("first_rotation_qualification")
    return str(
        _ask(
            questionary.select(
                "What record do you create?",
                choices=[Choice(title=item.text, value=item.id) for item in scene.choices],
            )
        )
    )


def _interactive_check(
    state: GameState,
    *,
    content: ContentBundle,
    engine: LearningEngine,
    check_id: str,
) -> None:
    check = content.knowledge_check(check_id)
    option_order = ordered_check_options(check, game_seed=state.seed)
    while not state.learning.checks.get(check_id) or not state.learning.checks[check_id].completed:
        render_check(console, check, options=option_order)
        if state.show_math == ShowMathMode.ALWAYS:
            render_check_math(console, check, content)
        command_choices = [Choice("Answer", value="answer")]
        if state.show_math == ShowMathMode.ON_REQUEST:
            command_choices.append(Choice("Show the math / reasoning frame", value="math"))
        command_choices.extend(
            [
                Choice("Clear screen and ask again", value="repeat"),
                Choice("Give me a hint", value="hint"),
                Choice("Open Learning Notebook", value="notebook"),
                Choice("I'm not sure — walk me through it", value="unsure"),
            ]
        )
        action = str(
            _ask(questionary.select("How do you want to proceed?", choices=command_choices))
        )
        if action == "math":
            render_check_math(console, check, content)
            _continue_after_feedback(interactive=True)
            continue
        if action == "repeat":
            console.clear()
            continue
        if action == "hint":
            console.print(Panel(engine.hint(state, check_id), title="Hint"))
            _continue_after_feedback(interactive=True)
            continue
        if action == "notebook":
            render_notebook(console, state, content)
            _continue_after_feedback(interactive=True)
            continue
        if action == "unsure":
            result = engine.walkthrough(state, check_id)
            console.print(
                Panel(
                    f"{result.explanation}\n\n{result.worked_solution}",
                    title="Worked walkthrough · practiced with help",
                    border_style="yellow",
                )
            )
            return
        if check.check_type == KnowledgeCheckType.NUMERIC:
            answer = str(_ask(questionary.text("Your numeric answer:")))
        else:
            answer = str(
                _ask(
                    questionary.select(
                        "Your answer:",
                        choices=[Choice(title=item.text, value=item.id) for item in option_order],
                    )
                )
            )
        try:
            result = engine.submit(state, check_id, answer)
        except ValueError as error:
            console.print(f"[yellow]{error}[/yellow]")
            continue
        if result.correct:
            label = "demonstrated independently" if result.independent else "practiced"
            console.print(Panel(result.explanation, title=f"Correct · {label}"))
            return
        console.print(
            Panel(
                f"{result.wrong_answer_feedback}\n\n"
                "Try again; no story or financial state changed.",
                title="Not yet",
            )
        )
        _continue_after_feedback(interactive=True)


def _play_prologue(
    state: GameState,
    *,
    content: ContentBundle,
    repository: SaveRepository,
    strategy: str,
    story_choice_id: str | None,
    maximum_days: int | None,
    skip: bool,
    interactive: bool,
    debug: bool,
    save_enabled: bool,
) -> bool:
    engine = LearningEngine(content)
    if skip:
        engine.skip_prologue(state)
        if save_enabled:
            repository.save(state)
        console.print("[dim]First Rotation skipped; no learning credit was awarded.[/dim]")
        return True
    if state.prologue.completed:
        return True
    if strategy not in {"auto", "correct", "helped", "retry"}:
        raise typer.BadParameter(
            "prologue strategy must be auto, correct, helped, or retry",
            param_hint="--prologue-strategy",
        )
    if state.prologue.current_day_index == 0:
        prologue = content.prologue.prologue
        render_core_chapter_opening(console, content, "first_rotation")
        chapter = content.core_chapter("first_rotation")
        LearningEngine(content).introduce_objectives(
            state,
            [
                *chapter.introduced_objective_ids,
                *chapter.practiced_objective_ids,
                *chapter.business_context_objective_ids,
            ],
            chapter_id="first_rotation",
        )
        console.print(
            Panel(
                f"Role: {state.player.role}\n"
                f"Location: {NORTHSTAR_HEADQUARTERS}\n"
                f"Three training days · about {prologue.estimated_minutes} minutes\n"
                "Your exercises affect learning progress only. Authored story choices "
                "remain durable.",
                title=prologue.title,
                border_style="cyan",
            )
        )
    completed_this_run = 0
    days = content.prologue.prologue.days
    while state.prologue.current_day_index < len(days):
        if maximum_days is not None and completed_this_run >= maximum_days:
            break
        day = days[state.prologue.current_day_index]
        engine.introduce_day(state, day)
        _introduce_characters(
            state,
            content,
            *PROLOGUE_CHARACTER_IDS[day.id],
        )
        if day.day_number == 1:
            render_background_orientation(console, state, content)
        render_day(console, day)
        run_checks = state.game_mode == GameMode.GUIDED or strategy != "auto"
        if interactive and state.game_mode == GameMode.STANDARD and strategy == "auto":
            run_checks = bool(
                _ask(
                    questionary.confirm(
                        "Open this day's optional learning checks?",
                        default=False,
                    )
                )
            )
        if not run_checks:
            state.prologue.current_check_index = len(day.check_ids)
        while state.prologue.current_check_index < len(day.check_ids):
            check_id = day.check_ids[state.prologue.current_check_index]
            progress = state.learning.checks.get(check_id)
            if progress is not None and progress.completed:
                state.prologue.current_check_index += 1
                continue
            if interactive:
                _interactive_check(state, content=content, engine=engine, check_id=check_id)
            elif strategy == "helped":
                if state.show_math == ShowMathMode.ALWAYS:
                    render_check_math(
                        console,
                        content.knowledge_check(check_id),
                        content,
                    )
                engine.walkthrough(state, check_id)
            else:
                if state.show_math == ShowMathMode.ALWAYS:
                    render_check_math(
                        console,
                        content.knowledge_check(check_id),
                        content,
                    )
                effective_strategy = "correct" if strategy == "auto" else strategy
                if effective_strategy == "retry":
                    engine.submit(state, check_id, "999999999")
                engine.submit(state, check_id, engine.expected_answer(check_id))
            state.prologue.current_check_index += 1
            if save_enabled:
                repository.save(state)
            _continue_after_feedback(interactive=interactive)
        if day.story_scene_id and state.prologue.story_choice_id is None:
            scene = content.scene(day.story_scene_id)
            if scene.setup is not None:
                _introduce_characters(state, content, *scene.setup.character_ids)
                _introduce_speaker(state, content, scene.setup.speaker)
            _introduce_speaker(state, content, scene.speaker)
            render_scene(console, scene)
            selected = story_choice_id or (
                _choose_prologue_story_interactively(content)
                if interactive
                else "preserve_scheduling_qualification"
            )
            valid = {item.id for item in scene.choices}
            if selected not in valid:
                raise typer.BadParameter(
                    f"prologue choice must be one of: {', '.join(sorted(valid))}",
                    param_hint="--prologue-choice",
                )
            NarrativeEngine(content).choose(state, scene.id, selected)
            state.prologue.story_choice_id = selected
        engine.complete_day(state, day, require_checks=run_checks)
        completed_this_run += 1
        console.print(Panel(day.end_note, title=f"{day.title} complete", border_style="green"))
        if save_enabled:
            repository.save(state)
        _continue_after_feedback(interactive=interactive)
    if state.prologue.current_day_index == len(days):
        engine.complete_prologue(state)
        transition = content.scene(content.prologue.prologue.episode_1_transition_scene_id)
        console.print(
            Panel(
                f"{transition.text}\n\n{content.prologue.prologue.transition_text}",
                title=transition.title,
                border_style="green",
            )
        )
        if save_enabled:
            repository.save(state)
        _finish_core_chapter(state, content, "first_rotation")
        return True
    console.print(
        Panel(
            f"Completed {state.prologue.current_day_index} of 3 rotation days. "
            "Load the autosave to resume.",
            title="First Rotation paused",
            border_style="yellow",
        )
    )
    if debug:
        render_debug(console, state)
    return False


def _choose_interactively(content: ContentBundle) -> str:
    scene = content.scene(SCENE_ID)
    return str(
        _ask(
            questionary.select(
                "What do you put your name to?",
                choices=[Choice(title=item.text, value=item.id) for item in scene.choices],
            )
        )
    )


def _begin_core_chapter(
    state: GameState,
    content: ContentBundle,
    chapter_id: str,
) -> None:
    chapter = content.core_chapter(chapter_id)
    render_core_chapter_opening(console, content, chapter_id)
    LearningEngine(content).introduce_objectives(
        state,
        [
            *chapter.introduced_objective_ids,
            *chapter.practiced_objective_ids,
            *chapter.business_context_objective_ids,
        ],
        chapter_id=chapter_id,
    )


def _render_shared_engine_math(title: str, lines: list[str]) -> None:
    console.print(
        Panel(
            "\n".join(lines),
            title=f"SHOW THE MATH · {title}",
            border_style="magenta",
        )
    )


def _finish_core_chapter(
    state: GameState,
    content: ContentBundle,
    chapter_id: str,
) -> None:
    if chapter_id in state.core_chapter_debrief_ids:
        return
    render_core_chapter_debrief(
        console,
        state,
        content,
        chapter_id,
        chapter_calculation_lines(state, content, chapter_id),
    )
    state.core_chapter_debrief_ids.append(chapter_id)


def _choose_hedge_interactively(content: ContentBundle) -> str:
    scenario = content.hedge_scenarios.scenarios[0]
    return str(
        _ask(
            questionary.select(
                "How much of the 100,000 MMBtu exposure will you hedge?",
                choices=[
                    Choice(
                        title=f"{item.label} — {item.description}",
                        value=item.id,
                    )
                    for item in scenario.hedge_levels
                ],
            )
        )
    )


def _choose_documentation_interactively(content: ContentBundle) -> str:
    scene = content.scene(HEDGE_DOCUMENTATION_SCENE_ID)
    return str(
        _ask(
            questionary.select(
                "What goes in the approval record?",
                choices=[Choice(title=item.text, value=item.id) for item in scene.choices],
            )
        )
    )


def _choose_notification_interactively(content: ContentBundle) -> str:
    scenario = content.treasury_scenarios.scenarios[0]
    return str(
        _ask(
            questionary.select(
                "Who gets the two o'clock call, and what do they get?",
                choices=[
                    Choice(title=f"{item.label} — {item.narrative}", value=item.id.value)
                    for item in scenario.notification_options
                ],
            )
        )
    )


def _choose_funding_interactively(feasible: list[FundingChoice]) -> str:
    labels = {
        FundingChoice.OPERATING_CASH: "Use operating cash",
        FundingChoice.REVOLVER: "Draw the approved revolver",
        FundingChoice.REDUCE_POSITION: "Reduce the futures position",
        FundingChoice.MISS_CALL: "Do not meet the call",
    }
    return str(
        _ask(
            questionary.select(
                "How will Northstar handle the call and obligations?",
                choices=[Choice(title=labels[item], value=item.value) for item in feasible],
            )
        )
    )


def _play(
    state: GameState,
    *,
    content: ContentBundle,
    repository: SaveRepository,
    choice_id: str | None,
    debug: bool,
    save_enabled: bool,
) -> None:
    render_dashboard(console, state)
    if state.completed:
        render_end_of_day(console, state)
        render_learning_report(console, build_learning_report(state, content))
        if debug:
            render_debug(console, state)
        return

    _begin_core_chapter(state, content, "december_difference")
    scene = content.scene(SCENE_ID)
    _introduce_speaker(state, content, scene.speaker)
    render_scene(console, scene)
    selected_choice = choice_id or _choose_interactively(content)
    valid_choices = {choice.id for choice in scene.choices}
    if selected_choice not in valid_choices:
        raise typer.BadParameter(
            f"choice must be one of: {', '.join(sorted(valid_choices))}",
            param_hint="--choice",
        )

    if save_enabled:
        repository.save(state)
    engine = NarrativeEngine(content)
    engine.choose(state, SCENE_ID, selected_choice)
    engine.process_end_of_day(state)
    if save_enabled:
        repository.save(state)

    render_end_of_day(console, state)
    render_learning_report(console, build_learning_report(state, content))
    _finish_core_chapter(state, content, "december_difference")
    if debug:
        render_debug(console, state)
    if save_enabled:
        console.print(f"[dim]Autosaved to {repository.path.resolve()}[/dim]")


def _play_hedge_book(
    state: GameState,
    *,
    content: ContentBundle,
    repository: SaveRepository,
    hedge_level_id: str | None,
    documentation_choice_id: str | None,
    maximum_days: int | None,
    debug: bool,
    save_enabled: bool,
    interactive: bool,
    show_daily_lessons: bool,
    market_path_id: str | None,
    notification_choice_id: str | None,
    funding_choice_id: str | None,
    draw_amount: Decimal | None,
    reduce_contracts: int | None,
    pause_after_notification: bool,
) -> None:
    starting_new_treasury = state.treasury is None
    try:
        engine = CommodityEngine(content, market_path_id=market_path_id)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="--market-path") from error
    treasury_engine = TreasuryEngine(content, engine)
    narrative = NarrativeEngine(content)
    treasury_mode = (
        interactive
        or market_path_id is not None
        or notification_choice_id is not None
        or funding_choice_id is not None
        or state.treasury is not None
    )
    if state.hedge_book is None:
        _begin_core_chapter(state, content, "hedge_book")
        _introduce_characters(
            state,
            content,
            "cal_rourke",
            "tj_morrow",
            "marisol_vega",
            "kasia_zielinska",
            "evelyn_marsh",
        )
        render_hedge_briefings(console, content)
        while True:
            selected_level = hedge_level_id or _choose_hedge_interactively(content)
            try:
                preview = engine.preview_hedge(state, selected_level)
            except ValueError as error:
                raise typer.BadParameter(str(error), param_hint="--hedge-choice") from error
            render_hedge_ticket(console, preview, content)
            if state.show_math == ShowMathMode.ALWAYS:
                contract = content.commodity_contract(engine.scenario.contract_id)
                _render_shared_engine_math(
                    "Hedge ticket",
                    [
                        (
                            f"{preview.contracts} contracts × "
                            f"{contract.contract_size_mmbtu:,.0f} "
                            f"MMBtu = {preview.hedged_quantity_mmbtu:,.0f} MMBtu"
                        ),
                        f"Shared-engine hedge ratio: {preview.hedge_ratio:.4f}",
                        (f"Shared-engine initial margin: ${preview.initial_margin_required:,.2f}"),
                    ],
                )
            if not interactive or bool(
                _ask(questionary.confirm("Approve this hedge ticket?", default=True))
            ):
                break
            if hedge_level_id is not None:
                return
        engine.open_hedge(state, selected_level)
        render_position_book(console, state)
        if save_enabled:
            repository.save(state)

    book = state.hedge_book
    if book is None:  # pragma: no cover - guarded by open_hedge
        raise RuntimeError("Hedge Book initialization failed")
    if book.completed:
        render_hedge_book_report(console, build_hedge_book_report(state, content))
        if state.treasury is not None and state.treasury.completed:
            render_treasury_report(console, build_treasury_report(state, content))
        if debug:
            render_debug(console, state)
        return

    if book.documentation_quality == DocumentationQuality.NOT_PREPARED:
        documentation_scene = content.scene(HEDGE_DOCUMENTATION_SCENE_ID)
        render_documentation_scene(console, documentation_scene)
        selected_documentation = documentation_choice_id or (
            _choose_documentation_interactively(content)
            if interactive
            else "write_accurate_hedge_memo"
        )
        valid_choices = {item.id for item in documentation_scene.choices}
        if selected_documentation not in valid_choices:
            raise typer.BadParameter(
                f"memo choice must be one of: {', '.join(sorted(valid_choices))}",
                param_hint="--memo-choice",
            )
        narrative.choose(
            state,
            HEDGE_DOCUMENTATION_SCENE_ID,
            selected_documentation,
        )
        if save_enabled:
            repository.save(state)

    processed = 0
    paused = False
    while not book.completed and (maximum_days is None or processed < maximum_days):
        if treasury_mode and state.treasury is None:
            result = engine.settle_next_day(state, defer_margin_call=True)
            render_settlement_day(
                console,
                result,
                show_explanation=show_daily_lessons,
            )
            render_position_book(console, state)
            processed += 1
            if book.next_settlement_index >= treasury_engine.scenario.trigger_settlement_day:
                treasury_engine.initialize_crisis(state)
                if starting_new_treasury:
                    _begin_core_chapter(state, content, "two_oclock_call")
                    starting_new_treasury = False
                render_treasury_crisis(console, state, content)
            if save_enabled:
                repository.save(state)
            continue

        if treasury_mode and state.treasury is not None:
            treasury = state.treasury
            if treasury.notification_choice is None:
                render_treasury_crisis(console, state, content)
                selected_notification = notification_choice_id or (
                    _choose_notification_interactively(content)
                    if interactive
                    else NotificationChoice.NOTIFY_IMMEDIATELY.value
                )
                try:
                    treasury_engine.record_notification(state, selected_notification)
                except ValueError as error:
                    raise typer.BadParameter(
                        str(error), param_hint="--notification-choice"
                    ) from error
                if save_enabled:
                    repository.save(state)
                if pause_after_notification:
                    paused = True
                    break

            if treasury.funding_decision is None:
                feasible = treasury_engine.feasible_funding_choices(state)
                render_funding_choices(console, state, feasible)
                selected_funding = funding_choice_id or (
                    _choose_funding_interactively(feasible)
                    if interactive
                    else FundingChoice.OPERATING_CASH.value
                )
                try:
                    treasury_engine.resolve_funding(
                        state,
                        selected_funding,
                        draw_amount=draw_amount,
                        reduce_contracts=reduce_contracts,
                    )
                except ValueError as error:
                    raise typer.BadParameter(str(error), param_hint="--funding-choice") from error
                render_treasury_crisis(console, state, content)
                if save_enabled:
                    repository.save(state)

        result = engine.settle_next_day(state)
        render_settlement_day(console, result, show_explanation=show_daily_lessons)
        if state.show_math == ShowMathMode.ALWAYS:
            _render_shared_engine_math(
                f"Settlement day {result.day_number}",
                [
                    (
                        f"Henry Hub: ${result.previous_henry_hub_price:.3f}/MMBtu "
                        f"→ ${result.henry_hub_price:.3f}/MMBtu"
                    ),
                    (f"Chicago = Henry Hub + basis = ${result.chicago_price:.3f}/MMBtu"),
                    f"Shared-engine futures P&L: ${result.daily_futures_pnl:+,.2f}",
                    f"Shared-engine margin call: ${result.margin_call_amount:,.2f}",
                    (
                        f"Operating cash ${result.operating_cash_end:,.2f}; "
                        f"FCM cash ${result.margin_balance_end:,.2f}"
                    ),
                ],
            )
        render_position_book(console, state)
        processed += 1
        if save_enabled:
            repository.save(state)
        if interactive and not book.completed:
            while True:
                action_choices = [
                    Choice("Continue to next settlement", value="continue"),
                    Choice("Save and return to menu", value="save"),
                ]
                if state.show_math == ShowMathMode.ON_REQUEST:
                    action_choices.insert(
                        1,
                        Choice("Show the Math for this settlement", value="math"),
                    )
                action = _ask(questionary.select("Next action:", choices=action_choices))
                if action == "math":
                    _render_shared_engine_math(
                        f"Settlement day {result.day_number}",
                        [
                            (
                                f"${result.previous_henry_hub_price:.3f}/MMBtu "
                                f"→ ${result.henry_hub_price:.3f}/MMBtu"
                            ),
                            f"Chicago price: ${result.chicago_price:.3f}/MMBtu",
                            f"Futures P&L: ${result.daily_futures_pnl:+,.2f}",
                            f"Margin call: ${result.margin_call_amount:,.2f}",
                        ],
                    )
                    continue
                if action == "save":
                    paused = True
                break
            if paused:
                break

    if book.completed:
        if state.treasury is not None and not state.treasury.completed:
            treasury_engine.finalize(state)
        report = build_hedge_book_report(state, content)
        render_hedge_book_report(console, report)
        if state.treasury is not None:
            render_treasury_report(console, build_treasury_report(state, content))
        _finish_core_chapter(state, content, "hedge_book")
        if state.treasury is not None and state.treasury.completed:
            _finish_core_chapter(state, content, "two_oclock_call")
    else:
        pause_reason = (
            "The notification is saved; load the autosave to choose funding."
            if paused
            and state.treasury is not None
            and state.treasury.notification_choice is not None
            and state.treasury.funding_decision is None
            else "Load the autosave to resume the embedded price path."
        )
        console.print(
            Panel(
                f"Completed {book.next_settlement_index} of "
                f"{len(book.price_path.settlements)} settlement days. " + pause_reason,
                title="Hedge Book paused",
                border_style="yellow",
            )
        )
    if debug:
        render_debug(console, state)
    if save_enabled:
        repository.save(state)
        console.print(f"[dim]Autosaved to {repository.path.resolve()}[/dim]")


def _run_chapter_checks(
    state: GameState,
    *,
    content: ContentBundle,
    day: int,
    strategy: str,
    interactive: bool,
) -> None:
    if strategy not in {"auto", "correct", "helped", "retry"}:
        raise typer.BadParameter(
            "chapter check strategy must be auto, correct, helped, or retry",
            param_hint="--chapter-check-strategy",
        )
    should_run = state.game_mode == GameMode.GUIDED or strategy != "auto"
    if interactive and state.game_mode == GameMode.STANDARD and strategy == "auto":
        should_run = bool(
            _ask(
                questionary.confirm(
                    "Open this day's optional Series 3 checks?",
                    default=False,
                )
            )
        )
    if not should_run:
        return
    effective_strategy = "correct" if strategy == "auto" else strategy
    learning = LearningEngine(content)
    for check_id in content.eleventh_learning.day_check_ids[f"day_{day}"]:
        progress = state.learning.checks.get(check_id)
        if progress is not None and progress.completed:
            if check_id not in state.eleventh_contract.learning_check_ids:
                state.eleventh_contract.learning_check_ids.append(check_id)
            continue
        if interactive:
            _interactive_check(
                state,
                content=content,
                engine=learning,
                check_id=check_id,
            )
        elif effective_strategy == "helped":
            learning.walkthrough(state, check_id)
        else:
            if effective_strategy == "retry":
                wrong_answer = (
                    "999999999"
                    if content.knowledge_check(check_id).check_type == KnowledgeCheckType.NUMERIC
                    else "__wrong__"
                )
                learning.submit(state, check_id, wrong_answer)
            learning.submit(state, check_id, learning.expected_answer(check_id))
        if check_id not in state.eleventh_contract.learning_check_ids:
            state.eleventh_contract.learning_check_ids.append(check_id)
        _continue_after_feedback(interactive=interactive)


def _choose_chapter_choice_interactively(
    state: GameState,
    content: ContentBundle,
    scene_id: str,
) -> str:
    narrative = NarrativeEngine(content)
    available = narrative.available_choices(state, scene_id)
    return str(
        _ask(
            questionary.select(
                "What do you do?",
                choices=[Choice(title=item.text, value=item.id) for item in available],
            )
        )
    )


def _run_chapter_scene(
    state: GameState,
    *,
    content: ContentBundle,
    scene_id: str,
    chapter_path: str,
    interactive: bool,
) -> None:
    narrative = NarrativeEngine(content)
    _introduce_speaker(state, content, content.scene(scene_id).speaker)
    render_chapter_scene(console, state, content, scene_id)
    selected = (
        _choose_chapter_choice_interactively(state, content, scene_id)
        if interactive
        else CHAPTER_PATH_CHOICES[chapter_path][scene_id]
    )
    available_ids = {item.id for item in narrative.available_choices(state, scene_id)}
    if selected not in available_ids:
        raise typer.BadParameter(
            f"chapter path {chapter_path!r} cannot select {selected!r} in {scene_id}; "
            f"available choices: {', '.join(sorted(available_ids))}",
            param_hint="--eleventh-path",
        )
    narrative.choose(state, scene_id, selected)


def _chapter_pause(
    state: GameState,
    *,
    repository: SaveRepository,
    save_enabled: bool,
    message: str,
) -> None:
    if save_enabled:
        repository.save(state)
    console.print(
        Panel(
            f"{message} Load the autosave to resume from the preserved record.",
            title="The Eleventh Contract paused",
            border_style="yellow",
        )
    )


def _play_eleventh_contract(
    state: GameState,
    *,
    content: ContentBundle,
    repository: SaveRepository,
    chapter_path: str | None,
    check_strategy: str,
    maximum_days: int | None,
    pause_with_exception: bool,
    interactive: bool,
    debug: bool,
    save_enabled: bool,
) -> bool:
    if chapter_path is not None and chapter_path not in CHAPTER_PATH_CHOICES:
        raise typer.BadParameter(
            "eleventh path must be one of: " + ", ".join(sorted(CHAPTER_PATH_CHOICES)),
            param_hint="--eleventh-path",
        )
    starting_new_chapter = state.eleventh_contract is None
    engine = EleventhContractEngine(content)
    chapter = engine.initialize(state)
    if starting_new_chapter:
        _begin_core_chapter(state, content, "eleventh_contract")
    requested_path = chapter_path
    if chapter.selected_story_path_id is None:
        chapter.selected_story_path_id = (
            "interactive" if interactive else requested_path or "formal_correction"
        )
    elif (
        requested_path is not None
        and chapter.selected_story_path_id != requested_path
        and chapter.selected_story_path_id != "interactive"
    ):
        raise typer.BadParameter(
            f"the saved chapter is already using story path {chapter.selected_story_path_id!r}",
            param_hint="--eleventh-path",
        )
    chapter_path = requested_path or (
        chapter.selected_story_path_id
        if chapter.selected_story_path_id != "interactive"
        else "formal_correction"
    )
    if chapter.completed:
        render_case_file(console, build_analyst_case_file(state, content))
        return True
    console.print(
        Panel(
            "Three working days · about "
            f"{content.eleventh_scenario.estimated_minutes} minutes\n"
            "You prepare recommendations and records. Cal transmits; Evelyn approves.",
            title=content.eleventh_scenario.title,
            border_style="cyan",
        )
    )
    completed_this_run = 0
    while not chapter.completed:
        if maximum_days is not None and completed_this_run >= maximum_days:
            _chapter_pause(
                state,
                repository=repository,
                save_enabled=save_enabled,
                message=f"Completed {completed_this_run} chapter day(s) in this run.",
            )
            return False
        day = chapter.current_day
        _run_chapter_checks(
            state,
            content=content,
            day=day,
            strategy=check_strategy,
            interactive=interactive,
        )
        if day == 1:
            if chapter.current_scene_index == 0:
                render_live_week_brief(console, state, content)
            scenes = CHAPTER_DAY_SCENES[1]
            while chapter.current_scene_index < len(scenes):
                scene_id = scenes[chapter.current_scene_index]
                _run_chapter_scene(
                    state,
                    content=content,
                    scene_id=scene_id,
                    chapter_path=chapter_path,
                    interactive=interactive,
                )
                chapter.current_scene_index += 1
                if save_enabled:
                    repository.save(state)
            engine.assemble_market_brief(state)
            completed_this_run += 1
            if save_enabled:
                repository.save(state)
            continue
        if day == 2:
            scenes = CHAPTER_DAY_SCENES[2]
            while chapter.current_scene_index < len(scenes):
                scene_id = scenes[chapter.current_scene_index]
                _run_chapter_scene(
                    state,
                    content=content,
                    scene_id=scene_id,
                    chapter_path=chapter_path,
                    interactive=interactive,
                )
                chapter.current_scene_index += 1
                if save_enabled:
                    repository.save(state)
            engine.recommend_and_execute_order(state)
            render_order_and_authorization(console, state, content, debug=debug)
            render_trade_blotter(console, state)
            if state.show_math == ShowMathMode.ALWAYS:
                _render_shared_engine_math(
                    "Eleventh Contract position",
                    chapter_calculation_lines(
                        state,
                        content,
                        "eleventh_contract",
                    ),
                )
            completed_this_run += 1
            if save_enabled:
                repository.save(state)
            continue

        scenes = CHAPTER_DAY_SCENES[3]
        while chapter.current_scene_index < len(scenes):
            if chapter.current_scene_index == 3 and pause_with_exception:
                _chapter_pause(
                    state,
                    repository=repository,
                    save_enabled=save_enabled,
                    message="The quantity exception request is saved before position action.",
                )
                return False
            if chapter.current_scene_index == 4 and not chapter.physical_forecast.revealed:
                engine.finalize_exception(state)
                render_trade_blotter(console, state)
            scene_id = scenes[chapter.current_scene_index]
            _run_chapter_scene(
                state,
                content=content,
                scene_id=scene_id,
                chapter_path=chapter_path,
                interactive=interactive,
            )
            chapter.current_scene_index += 1
            if save_enabled:
                repository.save(state)
        engine.complete_chapter(state)
        report = build_analyst_case_file(state, content)
        render_case_file(console, report)
        _finish_core_chapter(state, content, "eleventh_contract")
        completed_this_run += 1
        if save_enabled:
            repository.save(state)
            console.print(f"[dim]Autosaved to {repository.path.resolve()}[/dim]")
    if debug:
        render_debug(console, state)
    return True


def _play_core_review(
    state: GameState,
    *,
    content: ContentBundle,
    repository: SaveRepository,
    style_name: str | None,
    strategy: str,
    interactive: bool,
    save_enabled: bool,
) -> bool:
    if state.core_campaign_completed:
        return True
    if strategy not in {"correct", "helped", "retry"}:
        raise typer.BadParameter(
            "review strategy must be correct, helped, or retry",
            param_hint="--review-strategy",
        )
    review_engine = CoreReviewEngine(content)
    review = state.learning.core_review
    if review.style is None:
        if style_name is not None:
            try:
                selected_style = ReviewStyle(style_name)
            except ValueError as error:
                raise typer.BadParameter(
                    "review style must be learning or checkpoint",
                    param_hint="--review-style",
                ) from error
        elif interactive:
            selected_style = ReviewStyle(
                str(
                    _ask(
                        questionary.select(
                            "Choose the cumulative review style:",
                            choices=[
                                Choice(
                                    "Learning Review — hints, walkthroughs, retry",
                                    value=ReviewStyle.LEARNING.value,
                                ),
                                Choice(
                                    "Checkpoint Review — one answer, explanations after",
                                    value=ReviewStyle.CHECKPOINT.value,
                                ),
                            ],
                        )
                    )
                )
            )
        else:
            selected_style = (
                ReviewStyle.LEARNING
                if state.game_mode == GameMode.GUIDED
                else ReviewStyle.CHECKPOINT
            )
        review_engine.start(state, selected_style)
    elif style_name is not None and review.style.value != style_name:
        raise typer.BadParameter(
            f"the saved review already uses {review.style.value}",
            param_hint="--review-style",
        )

    console.print(
        Panel(
            "Fifteen questions drawn only from concepts taught in the five core "
            "chapters. First attempts remain visible even when Learning Review "
            "allows a retry.",
            title=f"Cumulative Core Review · {review.style.value}",
            border_style="magenta",
        )
    )
    while not review.completed:
        reference = review_engine.current_reference(state)
        check = content.knowledge_check(reference.check_id)
        option_order = ordered_check_options(check, game_seed=state.seed)
        render_check(console, check, options=option_order)
        if interactive:
            choices = [
                Choice("Answer", value="answer"),
                Choice("Clear screen and ask again", value="repeat"),
            ]
            if review.style == ReviewStyle.LEARNING:
                if state.show_math == ShowMathMode.ON_REQUEST:
                    choices.append(Choice("Show the Math", value="math"))
                choices.extend(
                    [
                        Choice("Give me a hint", value="hint"),
                        Choice("Open Learning Notebook", value="notebook"),
                        Choice("Walk me through it", value="walkthrough"),
                        Choice("Save and return to menu", value="save"),
                    ]
                )
            action = str(_ask(questionary.select("Review action:", choices=choices)))
            if action == "save":
                if save_enabled:
                    repository.save(state)
                console.print(
                    Panel(
                        "Review progress saved. Load this game to resume.",
                        title="Core Review paused",
                        border_style="yellow",
                    )
                )
                return False
            if action == "repeat":
                console.clear()
                continue
            if action == "math":
                render_check_math(console, check, content)
                _continue_after_feedback(interactive=True)
                continue
            if action == "hint":
                console.print(Panel(review_engine.hint(state), title="Hint"))
                _continue_after_feedback(interactive=True)
                continue
            if action == "notebook":
                render_notebook(console, state, content)
                _continue_after_feedback(interactive=True)
                continue
            if action == "walkthrough":
                result = review_engine.walkthrough(state)
                console.print(
                    Panel(
                        f"{result.explanation}\n\n{result.feedback}",
                        title="Worked walkthrough · completed with help",
                        border_style="yellow",
                    )
                )
                if save_enabled:
                    repository.save(state)
                _continue_after_feedback(interactive=True)
                continue
            if check.check_type == KnowledgeCheckType.NUMERIC:
                answer = str(_ask(questionary.text("Your numeric answer:")))
            else:
                answer = str(
                    _ask(
                        questionary.select(
                            "Your answer:",
                            choices=[Choice(item.text, value=item.id) for item in option_order],
                        )
                    )
                )
            result = review_engine.submit(state, answer)
            if review.style == ReviewStyle.LEARNING:
                if result.correct:
                    console.print(Panel(result.explanation, title="Correct"))
                else:
                    console.print(
                        Panel(
                            f"{result.feedback}\n\nTry again; the first attempt "
                            "remains in your diagnostic.",
                            title="Not yet",
                        )
                    )
            else:
                console.print("[dim]Answer recorded. Explanations follow completion.[/dim]")
        else:
            expected = LearningEngine(content).expected_answer(reference.check_id)
            if review.style == ReviewStyle.LEARNING and strategy == "helped":
                if review.current_question_index == 0:
                    review_engine.walkthrough(state)
                else:
                    review_engine.hint(state)
                    review_engine.submit(state, expected)
            elif strategy == "retry":
                wrong = (
                    "999999999"
                    if check.check_type == KnowledgeCheckType.NUMERIC
                    else next(
                        item.id for item in check.options if item.id != check.correct_option_id
                    )
                )
                review_engine.submit(state, wrong)
                if review.style == ReviewStyle.LEARNING:
                    review_engine.submit(state, expected)
            else:
                review_engine.submit(state, expected)
        if save_enabled:
            repository.save(state)
        _continue_after_feedback(interactive=interactive)

    if review.style == ReviewStyle.CHECKPOINT:
        explanation_lines = []
        for reference in content.curriculum.review_questions:
            check = content.knowledge_check(reference.check_id)
            explanation_lines.append(f"{reference.id}: {check.explanation} {check.worked_solution}")
        console.print(
            Panel(
                "\n".join(explanation_lines),
                title="Checkpoint explanations",
                border_style="blue",
            )
        )
        _continue_after_feedback(interactive=interactive)
    render_core_review_diagnostic(console, review_engine.diagnostic(state))
    if not state.core_debrief_completed:
        render_core_debrief(console, build_core_debrief(state, content))
        state.core_debrief_completed = True
    state.core_campaign_completed = True
    state.record(
        phase="system",
        event_type="series3_core_completed",
        source_id="series3_core_debrief",
        message="Series 3 Core Campaign completed and returned to the menu boundary.",
    )
    if not any(item.season_id == "series3_core" for item in state.learning.assessment_snapshots):
        finalize_core_snapshot(state, content)
    if save_enabled:
        repository.save(state)
    return True


def _run_applied_checks(
    state: GameState,
    *,
    content: ContentBundle,
    repository: SaveRepository,
    day: int,
    strategy: str,
    interactive: bool,
    save_enabled: bool,
) -> None:
    if strategy not in {"auto", "correct", "helped", "retry"}:
        raise typer.BadParameter(
            "chapter check strategy must be auto, correct, helped, or retry",
            param_hint="--chapter-check-strategy",
        )
    should_run = state.game_mode == GameMode.GUIDED or strategy != "auto"
    if interactive and state.game_mode == GameMode.STANDARD and strategy == "auto":
        should_run = bool(
            _ask(
                questionary.confirm(
                    "Open this day's optional Applied Foundations checks?",
                    default=False,
                )
            )
        )
    if not should_run:
        return
    effective_strategy = "correct" if strategy == "auto" else strategy
    learning = LearningEngine(content)
    for check_id in content.applied_foundations.day(day).check_ids:
        progress = state.learning.checks.get(check_id)
        if progress is not None and progress.completed:
            continue
        if interactive:
            _interactive_check(
                state,
                content=content,
                engine=learning,
                check_id=check_id,
            )
        elif effective_strategy == "helped":
            learning.walkthrough(state, check_id)
        else:
            if effective_strategy == "retry":
                check = content.knowledge_check(check_id)
                wrong = (
                    "999999999"
                    if check.check_type == KnowledgeCheckType.NUMERIC
                    else next(
                        item.id for item in check.options if item.id != check.correct_option_id
                    )
                )
                learning.submit(state, check_id, wrong)
            learning.submit(state, check_id, learning.expected_answer(check_id))
        if save_enabled:
            repository.save(state)
        _continue_after_feedback(interactive=interactive)


def _play_applied_review(
    state: GameState,
    *,
    content: ContentBundle,
    repository: SaveRepository,
    style_name: str | None,
    strategy: str,
    remediation_strategy: str,
    interactive: bool,
    save_enabled: bool,
    season_id: str = "applied_foundations",
) -> bool:
    is_notice = season_id == "notice_window"
    season_label = "Notice Window" if is_notice else "Applied Foundations"
    review_option = "--notice-review-strategy" if is_notice else "--applied-review-strategy"
    style_option = "--notice-review-style" if is_notice else "--applied-review-style"
    if strategy not in {"correct", "helped", "retry"}:
        raise typer.BadParameter(
            f"{season_label} review strategy must be correct, helped, or retry",
            param_hint=review_option,
        )
    if remediation_strategy not in {"auto", "complete", "skip"}:
        raise typer.BadParameter(
            "remediation strategy must be auto, complete, or skip",
            param_hint="--remediation-strategy",
        )
    engine = NoticeWindowReviewEngine(content) if is_notice else AppliedReviewEngine(content)
    blueprint = content.notice_window if is_notice else content.applied_foundations
    chapter = state.notice_window if is_notice else state.applied_foundations
    review = chapter.review
    if review.style is None:
        if style_name is not None:
            try:
                selected_style = ReviewStyle(style_name)
            except ValueError as error:
                raise typer.BadParameter(
                    f"{season_label} review style must be learning or checkpoint",
                    param_hint=style_option,
                ) from error
        elif interactive:
            selected_style = ReviewStyle(
                str(
                    _ask(
                        questionary.select(
                            f"Choose the {season_label} review style:",
                            choices=[
                                Choice(
                                    "Learning Review — hints, walkthroughs, retry",
                                    value=ReviewStyle.LEARNING.value,
                                ),
                                Choice(
                                    "Checkpoint Review — one answer, explanations after",
                                    value=ReviewStyle.CHECKPOINT.value,
                                ),
                            ],
                        )
                    )
                )
            )
        else:
            selected_style = (
                ReviewStyle.LEARNING
                if state.game_mode == GameMode.GUIDED
                else ReviewStyle.CHECKPOINT
            )
        engine.start(state, selected_style)
    elif style_name is not None and review.style.value != style_name:
        raise typer.BadParameter(
            f"the saved {season_label} review already uses {review.style.value}",
            param_hint=style_option,
        )

    console.print(
        Panel(
            "Ten required questions use new values and scenarios. First attempts "
            "remain historical even when Learning Review permits retry. Up to four "
            "separate questions are available only for targeted remediation.",
            title=f"{season_label} Review · {review.style.value}",
            border_style="magenta",
        )
    )

    def answer_current_questions() -> bool:
        while True:
            question = engine.current_question(state)
            if question is None:
                return True
            check = question.as_knowledge_check()
            option_order = ordered_check_options(check, game_seed=state.seed)
            render_check(console, check, options=option_order)
            if interactive:
                actions = []
                if check.check_type == KnowledgeCheckType.NUMERIC:
                    actions.append(Choice("Answer", value="answer"))
                else:
                    actions.extend(
                        Choice(item.text, value=f"answer:{item.id}") for item in option_order
                    )
                actions.append(Choice("Clear screen and ask again", value="repeat"))
                if review.style == ReviewStyle.LEARNING:
                    if state.show_math == ShowMathMode.ON_REQUEST:
                        actions.append(Choice("Show the Math", value="math"))
                    actions.extend(
                        [
                            Choice("Give me a hint", value="hint"),
                            Choice("Open Learning Notebook", value="notebook"),
                            Choice("Walk me through it", value="walkthrough"),
                        ]
                    )
                actions.append(Choice("Save and return to menu", value="save"))
                action = str(_ask(questionary.select("Review action:", choices=actions)))
                if action == "save":
                    if save_enabled:
                        repository.save(state)
                    console.print(
                        Panel(
                            f"{season_label} review progress saved. Load this game to resume.",
                            title=f"{season_label} Review paused",
                            border_style="yellow",
                        )
                    )
                    return False
                if action == "repeat":
                    console.clear()
                    continue
                if action == "math":
                    render_check_math(console, check, content)
                    _continue_after_feedback(interactive=True)
                    continue
                if action == "hint":
                    console.print(Panel(engine.hint(state), title="Hint"))
                    if save_enabled:
                        repository.save(state)
                    _continue_after_feedback(interactive=True)
                    continue
                if action == "notebook":
                    render_notebook(console, state, content)
                    _continue_after_feedback(interactive=True)
                    continue
                if action == "walkthrough":
                    result = engine.walkthrough(state)
                    console.print(
                        Panel(
                            f"{result.explanation}\n\n{result.feedback}",
                            title="Worked walkthrough · completed with help",
                            border_style="yellow",
                        )
                    )
                    if save_enabled:
                        repository.save(state)
                    _continue_after_feedback(interactive=True)
                    continue
                answer = (
                    str(_ask(questionary.text("Your numeric answer:")))
                    if action == "answer"
                    else action.removeprefix("answer:")
                )
                result = engine.submit(state, answer)
                if review.style == ReviewStyle.LEARNING:
                    if result.correct:
                        console.print(Panel(result.explanation, title="Correct"))
                    else:
                        console.print(
                            Panel(
                                f"{result.feedback}\n\nTry again; the first attempt "
                                "remains in the assessment snapshot.",
                                title="Not yet",
                            )
                        )
                else:
                    console.print("[dim]Answer recorded for the checkpoint.[/dim]")
            else:
                expected = LearningEngine(content).expected_answer(question.id)
                if review.style == ReviewStyle.LEARNING and strategy == "helped":
                    engine.walkthrough(state)
                elif strategy == "retry":
                    wrong = (
                        "999999999"
                        if check.check_type == KnowledgeCheckType.NUMERIC
                        else next(
                            item.id for item in check.options if item.id != check.correct_option_id
                        )
                    )
                    engine.submit(state, wrong)
                    if review.style == ReviewStyle.LEARNING:
                        engine.submit(state, expected)
                else:
                    engine.submit(state, expected)
            if save_enabled:
                repository.save(state)
            _continue_after_feedback(interactive=interactive)

    if not answer_current_questions():
        return False
    if review.style == ReviewStyle.CHECKPOINT and review.required_completed:
        console.print(
            Panel(
                "\n\n".join(
                    f"{item.id}: {item.as_knowledge_check().explanation}"
                    for item in blueprint.review.required
                ),
                title=f"{season_label} checkpoint explanations",
                border_style="blue",
            )
        )
        _continue_after_feedback(interactive=interactive)
    diagnostic_renderer = render_notice_diagnostic if is_notice else render_applied_diagnostic
    diagnostic_renderer(console, engine.diagnostic(state))
    if not review.completed and not review.selected_remediation_ids:
        if interactive:
            take_remediation = bool(
                _ask(
                    questionary.confirm(
                        "Complete the targeted remediation questions now?",
                        default=True,
                    )
                )
            )
        else:
            take_remediation = remediation_strategy == "complete" or (
                remediation_strategy == "auto" and state.game_mode == GameMode.GUIDED
            )
        selected = engine.prepare_remediation(
            state,
            take_remediation=take_remediation,
        )
        if selected:
            console.print(
                Panel(
                    f"{len(selected)} targeted question(s) will record later "
                    "demonstration separately from the original checkpoint.",
                    title="Targeted remediation",
                    border_style="yellow",
                )
            )
    if not answer_current_questions():
        return False
    if save_enabled:
        repository.save(state)
    engine.finalize_snapshot(state)
    diagnostic_renderer(console, engine.diagnostic(state))
    return True


def _play_applied_foundations(
    state: GameState,
    *,
    content: ContentBundle,
    repository: SaveRepository,
    applied_path: str | None,
    check_strategy: str,
    maximum_days: int | None,
    pause_before_review: bool,
    review_style_name: str | None,
    review_strategy: str,
    remediation_strategy: str,
    interactive: bool,
    debug: bool,
    save_enabled: bool,
) -> bool:
    if state.applied_foundations.status == AppliedSeasonStatus.LEGACY_SKIPPED:
        return True
    if state.applied_foundations.status == AppliedSeasonStatus.COMPLETED:
        return True
    engine = AppliedFoundationsEngine(content)
    starting = state.applied_foundations.status == AppliedSeasonStatus.NOT_STARTED
    chapter = engine.start(state)
    if starting:
        render_season_opening(console, content.applied_foundations)
    path_name = applied_path or "evidence_first"
    if path_name not in content.applied_foundations.scripted_paths:
        raise typer.BadParameter(
            "Applied path must be evidence_first, concise_operator, or escalation_first",
            param_hint="--applied-path",
        )
    if maximum_days == 0:
        if save_enabled:
            repository.save(state)
        return False
    completed_this_run = 0
    while chapter.current_day_index < 3 and (
        maximum_days is None or completed_this_run < maximum_days
    ):
        day_number = chapter.current_day_index + 1
        engine.begin_day(state, day_number)
        day = content.applied_foundations.day(day_number)
        if day_number == 3 and save_enabled:
            repository.save(state)
        _introduce_characters(state, content, *day.lead_characters)
        render_applied_day(console, day)
        if day_number == 3:
            render_financial_bridge(console, state)
        while (decision := engine.current_decision(state)) is not None:
            console.print(Panel(decision.prompt, title=decision.title, border_style="cyan"))
            selected = (
                str(
                    _ask(
                        questionary.select(
                            "What record do you create?",
                            choices=[Choice(item.text, value=item.id) for item in decision.choices],
                        )
                    )
                )
                if interactive
                else engine.scripted_choice(state, path_name)
            )
            choice = engine.record_decision(state, decision.id, selected)
            render_decision_result(console, choice)
            if save_enabled:
                repository.save(state)
            _continue_after_feedback(interactive=interactive)
        _run_applied_checks(
            state,
            content=content,
            repository=repository,
            day=day_number,
            strategy=check_strategy,
            interactive=interactive,
            save_enabled=save_enabled,
        )
        engine.complete_day(
            state,
            require_checks=state.game_mode == GameMode.GUIDED,
        )
        completed_this_run += 1
        if day_number == 2:
            render_order_tape(console, state, content)
        if save_enabled:
            repository.save(state)
            console.print(f"[dim]Autosaved to {repository.path.resolve()}[/dim]")
        boundary_text = day.boundary.retention_message or day.boundary.message
        console.print(
            Panel(
                boundary_text,
                title=f"Day {day_number} saved",
                border_style="yellow" if day_number == 3 else "green",
            )
        )
        if maximum_days is not None and completed_this_run >= maximum_days:
            return False
        if day_number < 3 and interactive:
            action = str(
                _ask(
                    questionary.select(
                        "Continue the Applied Foundations case?",
                        choices=[
                            Choice("Continue", value="continue"),
                            Choice("Save and return to menu", value="save"),
                        ],
                    )
                )
            )
            if action == "save":
                return False
    if chapter.current_day_index < 3:
        return False
    engine.complete_chapter(state)
    if pause_before_review:
        return False
    if interactive:
        action = str(
            _ask(
                questionary.select(
                    "The case is saved. Review now or take a retention break?",
                    choices=[
                        Choice("Continue to the review", value="continue"),
                        Choice("Save and return to menu", value="save"),
                    ],
                )
            )
        )
        if action == "save":
            return False
    if not chapter.snapshot_finalized:
        finished = _play_applied_review(
            state,
            content=content,
            repository=repository,
            style_name=review_style_name,
            strategy=review_strategy,
            remediation_strategy=remediation_strategy,
            interactive=interactive,
            save_enabled=save_enabled,
        )
        if not finished:
            return False
    render_applied_debrief(console, state, content)
    engine.mark_completed(state)
    if save_enabled:
        repository.save(state)
    if debug:
        render_debug(console, state)
    return True


def _run_notice_checks(
    state: GameState,
    *,
    content: ContentBundle,
    repository: SaveRepository,
    day: int,
    strategy: str,
    interactive: bool,
    save_enabled: bool,
) -> None:
    if strategy not in {"auto", "correct", "helped", "retry"}:
        raise typer.BadParameter(
            "notice check strategy must be auto, correct, helped, or retry",
            param_hint="--notice-check-strategy",
        )
    should_run = state.game_mode == GameMode.GUIDED or strategy != "auto"
    if interactive and state.game_mode == GameMode.STANDARD and strategy == "auto":
        should_run = bool(
            _ask(
                questionary.confirm(
                    "Open this day's optional Notice Window checks?",
                    default=False,
                )
            )
        )
    if not should_run:
        return
    effective_strategy = "correct" if strategy == "auto" else strategy
    learning = LearningEngine(content)
    for check_id in content.notice_window.day(day).check_ids:
        progress = state.learning.checks.get(check_id)
        if progress is not None and progress.completed:
            continue
        if interactive:
            _interactive_check(state, content=content, engine=learning, check_id=check_id)
        elif effective_strategy == "helped":
            learning.walkthrough(state, check_id)
        else:
            if effective_strategy == "retry":
                check = content.knowledge_check(check_id)
                wrong = (
                    "999999999"
                    if check.check_type == KnowledgeCheckType.NUMERIC
                    else next(
                        item.id for item in check.options if item.id != check.correct_option_id
                    )
                )
                learning.submit(state, check_id, wrong)
            learning.submit(state, check_id, learning.expected_answer(check_id))
        if save_enabled:
            repository.save(state)
        _continue_after_feedback(interactive=interactive)


def _play_notice_window(
    state: GameState,
    *,
    content: ContentBundle,
    repository: SaveRepository,
    notice_path: str | None,
    check_strategy: str,
    maximum_days: int | None,
    pause_before_review: bool,
    review_style_name: str | None,
    review_strategy: str,
    remediation_strategy: str,
    interactive: bool,
    debug: bool,
    save_enabled: bool,
) -> bool:
    if state.notice_window.status == NoticeWindowStatus.LEGACY_SKIPPED:
        return True
    if state.notice_window.status == NoticeWindowStatus.COMPLETED:
        return True
    engine = NoticeWindowEngine(content)
    starting = state.notice_window.status == NoticeWindowStatus.NOT_STARTED
    chapter = engine.start(state)
    if starting:
        render_notice_opening(console, content.notice_window)
    path_name = notice_path or "evidence_first"
    if path_name not in content.notice_window.scripted_paths:
        raise typer.BadParameter(
            "Notice path must be evidence_first, concise_operator, or escalation_first",
            param_hint="--notice-path",
        )
    if maximum_days == 0:
        if save_enabled:
            repository.save(state)
        return False
    completed_this_run = 0
    while chapter.current_day_index < 3 and (
        maximum_days is None or completed_this_run < maximum_days
    ):
        day_number = chapter.current_day_index + 1
        engine.begin_day(state, day_number)
        day = content.notice_window.day(day_number)
        if day_number == 3 and save_enabled:
            repository.save(state)
        _introduce_characters(state, content, *day.lead_characters)
        render_notice_day(console, day)
        if day_number == 1:
            render_notice_calendar(console, content.notice_window)
        elif day_number == 2:
            render_notice_curves(console, state, content)
        while (decision := engine.current_decision(state)) is not None:
            console.print(Panel(decision.prompt, title=decision.title, border_style="cyan"))
            selected = (
                str(
                    _ask(
                        questionary.select(
                            "What record do you create?",
                            choices=[Choice(item.text, value=item.id) for item in decision.choices],
                        )
                    )
                )
                if interactive
                else engine.scripted_choice(state, path_name)
            )
            choice = engine.record_decision(state, decision.id, selected)
            render_notice_decision_result(console, choice)
            if save_enabled:
                repository.save(state)
            _continue_after_feedback(interactive=interactive)
        _run_notice_checks(
            state,
            content=content,
            repository=repository,
            day=day_number,
            strategy=check_strategy,
            interactive=interactive,
            save_enabled=save_enabled,
        )
        engine.complete_day(state, require_checks=state.game_mode == GameMode.GUIDED)
        completed_this_run += 1
        if day_number == 3:
            render_notice_resolution(console, state)
        if save_enabled:
            repository.save(state)
            console.print(f"[dim]Autosaved to {repository.path.resolve()}[/dim]")
        boundary_text = day.boundary.retention_message or day.boundary.message
        console.print(
            Panel(
                boundary_text,
                title=f"Notice Window Day {day_number} saved",
                border_style="yellow" if day_number == 3 else "green",
            )
        )
        if maximum_days is not None and completed_this_run >= maximum_days:
            return False
        if day_number < 3 and interactive:
            action = str(
                _ask(
                    questionary.select(
                        "Continue The Notice Window?",
                        choices=[
                            Choice("Continue", value="continue"),
                            Choice("Save and return to menu", value="save"),
                        ],
                    )
                )
            )
            if action == "save":
                return False
    if chapter.current_day_index < 3:
        return False
    engine.complete_chapter(state)
    if pause_before_review:
        return False
    if interactive:
        action = str(
            _ask(
                questionary.select(
                    "The expiry file is saved. Review now or take a retention break?",
                    choices=[
                        Choice("Continue to the review", value="continue"),
                        Choice("Save and return to menu", value="save"),
                    ],
                )
            )
        )
        if action == "save":
            return False
    if not chapter.snapshot_finalized:
        finished = _play_applied_review(
            state,
            content=content,
            repository=repository,
            style_name=review_style_name,
            strategy=review_strategy,
            remediation_strategy=remediation_strategy,
            interactive=interactive,
            save_enabled=save_enabled,
            season_id="notice_window",
        )
        if not finished:
            return False
    render_notice_debrief(console, state, content)
    engine.mark_completed(state)
    if save_enabled:
        repository.save(state)
    if debug:
        render_debug(console, state)
    return True


def _run_audit_checks(
    state: GameState,
    *,
    content: ContentBundle,
    day: int,
    strategy: str,
    interactive: bool,
) -> None:
    if strategy not in {"auto", "correct", "helped", "retry"}:
        raise typer.BadParameter(
            "audit check strategy must be auto, correct, helped, or retry",
            param_hint="--audit-check-strategy",
        )
    should_run = state.game_mode == GameMode.GUIDED or strategy != "auto"
    if interactive and state.game_mode == GameMode.STANDARD and strategy == "auto":
        should_run = bool(
            _ask(
                questionary.confirm(
                    "Open this day's optional control and evidence checks?",
                    default=False,
                )
            )
        )
    if not should_run:
        return
    effective_strategy = "correct" if strategy == "auto" else strategy
    learning = LearningEngine(content)
    audit = state.no_surprises
    for check_id in content.audit_learning.day_check_ids[f"day_{day}"]:
        progress = state.learning.checks.get(check_id)
        if progress is not None and progress.completed:
            if check_id not in audit.learning_check_ids:
                audit.learning_check_ids.append(check_id)
            continue
        if interactive:
            _interactive_check(
                state,
                content=content,
                engine=learning,
                check_id=check_id,
            )
        elif effective_strategy == "helped":
            learning.walkthrough(state, check_id)
        else:
            if effective_strategy == "retry":
                learning.submit(state, check_id, "__wrong__")
            learning.submit(state, check_id, learning.expected_answer(check_id))
        if check_id not in audit.learning_check_ids:
            audit.learning_check_ids.append(check_id)
        _continue_after_feedback(interactive=interactive)


def _choose_audit_choice_interactively(
    content: ContentBundle,
    scene_id: str,
) -> str:
    scene = content.audit_scene(scene_id)
    return str(
        _ask(
            questionary.select(
                "What do you do?",
                choices=[Choice(title=item.text, value=item.id) for item in scene.choices],
            )
        )
    )


def _run_audit_scene(
    state: GameState,
    *,
    content: ContentBundle,
    scene_id: str,
    audit_path: str,
    interactive: bool,
) -> None:
    engine = InternalAuditEngine(content)
    scene = content.audit_scene(scene_id)
    _introduce_speaker(state, content, scene.speaker)
    render_audit_scene(console, state, scene)
    selected = (
        _choose_audit_choice_interactively(content, scene_id)
        if interactive
        else AUDIT_PATH_CHOICES[audit_path][scene_id]
    )
    valid_ids = {item.id for item in scene.choices}
    if selected not in valid_ids:
        raise typer.BadParameter(
            f"audit path {audit_path!r} cannot select {selected!r} in {scene_id}",
            param_hint="--audit-path",
        )
    engine.apply_choice(state, scene_id, selected)


def _audit_pause(
    state: GameState,
    *,
    repository: SaveRepository,
    save_enabled: bool,
    message: str,
) -> None:
    if save_enabled:
        repository.save(state)
    console.print(
        Panel(
            f"{message} Load the autosave to resume from the preserved audit state.",
            title="No Surprises paused",
            border_style="yellow",
        )
    )


def _play_no_surprises(
    state: GameState,
    *,
    content: ContentBundle,
    repository: SaveRepository,
    audit_path: str | None,
    check_strategy: str,
    maximum_stages: int | None,
    pause_before_exit: bool,
    interactive: bool,
    debug: bool,
    save_enabled: bool,
) -> bool:
    if audit_path is not None and audit_path not in AUDIT_PATH_CHOICES:
        raise typer.BadParameter(
            "audit path must be one of: " + ", ".join(sorted(AUDIT_PATH_CHOICES)),
            param_hint="--audit-path",
        )
    engine = InternalAuditEngine(content)
    audit = engine.initialize(state)
    requested_path = audit_path
    if audit.selected_story_path_id is None:
        audit.selected_story_path_id = (
            "interactive" if interactive else requested_path or "full_disclosure"
        )
    elif (
        requested_path is not None
        and audit.selected_story_path_id != requested_path
        and audit.selected_story_path_id != "interactive"
    ):
        raise typer.BadParameter(
            f"the saved audit is already using story path {audit.selected_story_path_id!r}",
            param_hint="--audit-path",
        )
    audit_path = requested_path or (
        audit.selected_story_path_id
        if audit.selected_story_path_id != "interactive"
        else "full_disclosure"
    )
    if audit.completed:
        render_internal_audit_report(
            console,
            build_internal_audit_report(state, content),
            content,
        )
        return True
    console.print(
        Panel(
            "Four working days · about "
            f"{content.audit_scenario.estimated_minutes} minutes\n"
            "You retrieve and explain records. Noah tests controls; management owns the response.",
            title=content.audit_scenario.title,
            border_style="cyan",
        )
    )
    completed_this_run = 0
    while not audit.completed:
        if maximum_stages is not None and completed_this_run >= maximum_stages:
            _audit_pause(
                state,
                repository=repository,
                save_enabled=save_enabled,
                message=f"Completed {completed_this_run} audit stage(s) in this run.",
            )
            return False
        stage = audit.current_stage
        if stage == AuditStage.REQUEST_LIST:
            _run_audit_checks(
                state,
                content=content,
                day=1,
                strategy=check_strategy,
                interactive=interactive,
            )
            for scene_id in AUDIT_DAY_SCENES[1]:
                _run_audit_scene(
                    state,
                    content=content,
                    scene_id=scene_id,
                    audit_path=audit_path,
                    interactive=interactive,
                )
                if save_enabled:
                    repository.save(state)
            engine.prepare_initial_package(state)
            render_audit_request_list(console, state)
        elif stage == AuditStage.WALKTHROUGH:
            _run_audit_checks(
                state,
                content=content,
                day=2,
                strategy=check_strategy,
                interactive=interactive,
            )
            render_walkthrough_timeline(console, state, debug=debug)
            for scene_id in AUDIT_DAY_SCENES[2]:
                _run_audit_scene(
                    state,
                    content=content,
                    scene_id=scene_id,
                    audit_path=audit_path,
                    interactive=interactive,
                )
                if save_enabled:
                    repository.save(state)
            engine.conduct_walkthrough(state)
        elif stage == AuditStage.CONTROL_TESTING:
            _run_audit_checks(
                state,
                content=content,
                day=3,
                strategy=check_strategy,
                interactive=interactive,
            )
            _run_audit_scene(
                state,
                content=content,
                scene_id="ns_control_interpretation",
                audit_path=audit_path,
                interactive=interactive,
            )
            engine.evaluate_controls(state)
            render_control_results(console, state)
        elif stage == AuditStage.PRELIMINARY_FINDINGS:
            engine.prepare_findings(state)
            render_preliminary_findings(console, state)
            _run_audit_scene(
                state,
                content=content,
                scene_id="ns_finding_position",
                audit_path=audit_path,
                interactive=interactive,
            )
        elif stage == AuditStage.MANAGEMENT_RESPONSE:
            _run_audit_checks(
                state,
                content=content,
                day=4,
                strategy=check_strategy,
                interactive=interactive,
            )
            _run_audit_scene(
                state,
                content=content,
                scene_id="ns_supplement_package",
                audit_path=audit_path,
                interactive=interactive,
            )
            engine.prepare_supplement(state)
            render_audit_request_list(console, state)
            for scene_id in ("ns_remediation_choice", "ns_management_response"):
                _run_audit_scene(
                    state,
                    content=content,
                    scene_id=scene_id,
                    audit_path=audit_path,
                    interactive=interactive,
                )
            engine.prepare_management_response(state)
        elif stage == AuditStage.BEFORE_EXIT:
            if pause_before_exit and not audit.audit_flags.get("paused_before_exit"):
                audit.audit_flags["paused_before_exit"] = True
                _audit_pause(
                    state,
                    repository=repository,
                    save_enabled=save_enabled,
                    message="The management response is saved before the exit meeting.",
                )
                return False
            _run_audit_scene(
                state,
                content=content,
                scene_id="ns_exit_escalation",
                audit_path=audit_path,
                interactive=interactive,
            )
            engine.complete(state)
            render_internal_audit_report(
                console,
                build_internal_audit_report(state, content),
                content,
            )
        else:
            raise ValueError(f"unsupported audit stage: {stage}")
        completed_this_run += 1
        if save_enabled:
            repository.save(state)
    if debug:
        render_debug(console, state)
    return True


def _run_diligence_checks(
    state: GameState,
    *,
    content: ContentBundle,
    day: int,
    strategy: str,
    interactive: bool,
) -> None:
    if strategy not in {"auto", "correct", "helped", "retry"}:
        raise typer.BadParameter(
            "diligence check strategy must be auto, correct, helped, or retry",
            param_hint="--diligence-check-strategy",
        )
    should_run = state.game_mode == GameMode.GUIDED or strategy != "auto"
    if interactive and state.game_mode == GameMode.STANDARD and strategy == "auto":
        should_run = bool(
            _ask(
                questionary.confirm(
                    "Open this day's optional diligence checks?",
                    default=False,
                )
            )
        )
    if not should_run:
        return
    effective_strategy = "correct" if strategy == "auto" else strategy
    learning = LearningEngine(content)
    diligence = state.diligence_room
    for check_id in content.diligence_learning.day_check_ids[f"day_{day}"]:
        progress = state.learning.checks.get(check_id)
        if progress is not None and progress.completed:
            if check_id not in diligence.learning_check_ids:
                diligence.learning_check_ids.append(check_id)
            continue
        if interactive:
            _interactive_check(
                state,
                content=content,
                engine=learning,
                check_id=check_id,
            )
        elif effective_strategy == "helped":
            learning.walkthrough(state, check_id)
        else:
            if effective_strategy == "retry":
                learning.submit(state, check_id, "__wrong__")
            learning.submit(state, check_id, learning.expected_answer(check_id))
        if check_id not in diligence.learning_check_ids:
            diligence.learning_check_ids.append(check_id)
        _continue_after_feedback(interactive=interactive)


def _choose_diligence_choice_interactively(
    content: ContentBundle,
    scene_id: str,
) -> str:
    scene = content.diligence_scene(scene_id)
    return str(
        _ask(
            questionary.select(
                "What do you do?",
                choices=[Choice(title=item.text, value=item.id) for item in scene.choices],
            )
        )
    )


def _run_diligence_scene(
    state: GameState,
    *,
    content: ContentBundle,
    scene_id: str,
    diligence_path: str,
    interactive: bool,
) -> None:
    engine = DiligenceEngine(content)
    scene = content.diligence_scene(scene_id)
    _introduce_speaker(state, content, scene.speaker)
    render_diligence_scene(console, state, scene)
    selected = (
        _choose_diligence_choice_interactively(content, scene_id)
        if interactive
        else DILIGENCE_PATH_CHOICES[diligence_path][scene_id]
    )
    valid_ids = {item.id for item in scene.choices}
    if selected not in valid_ids:
        raise typer.BadParameter(
            f"diligence path {diligence_path!r} cannot select {selected!r} in {scene_id}",
            param_hint="--diligence-path",
        )
    engine.apply_choice(state, scene_id, selected)


def _diligence_pause(
    state: GameState,
    *,
    repository: SaveRepository,
    save_enabled: bool,
    message: str,
) -> None:
    if save_enabled:
        repository.save(state)
    console.print(
        Panel(
            f"{message} Load the autosave to resume from the preserved diligence state.",
            title="The Diligence Room paused",
            border_style="yellow",
        )
    )


def _play_diligence_room(
    state: GameState,
    *,
    content: ContentBundle,
    repository: SaveRepository,
    diligence_path: str | None,
    check_strategy: str,
    maximum_stages: int | None,
    pause_before_committee: bool,
    interactive: bool,
    debug: bool,
    save_enabled: bool,
) -> bool:
    if diligence_path is not None and diligence_path not in DILIGENCE_PATH_CHOICES:
        raise typer.BadParameter(
            "diligence path must be one of: " + ", ".join(sorted(DILIGENCE_PATH_CHOICES)),
            param_hint="--diligence-path",
        )
    engine = DiligenceEngine(content)
    diligence = engine.initialize(state)
    requested_path = diligence_path
    if diligence.selected_story_path_id is None:
        diligence.selected_story_path_id = (
            "interactive" if interactive else requested_path or "full_consistent"
        )
    elif (
        requested_path is not None
        and diligence.selected_story_path_id != requested_path
        and diligence.selected_story_path_id != "interactive"
    ):
        raise typer.BadParameter(
            f"the saved diligence chapter is already using path "
            f"{diligence.selected_story_path_id!r}",
            param_hint="--diligence-path",
        )
    diligence_path = requested_path or (
        diligence.selected_story_path_id
        if diligence.selected_story_path_id != "interactive"
        else "full_consistent"
    )
    if diligence.completed:
        render_diligence_room_report(
            console,
            build_diligence_room_report(state, content),
        )
        return True
    console.print(
        Panel(
            "Four working days · about "
            f"{content.diligence_scenario.estimated_minutes} minutes\n"
            "Proposed majority acquisition by "
            f"{content.diligence_scenario.buyer_name}.\n"
            "You assemble and reconcile records; owners retain approval, legal, "
            "accounting-materiality, and executive representations.",
            title=content.diligence_scenario.title,
            border_style="cyan",
        )
    )
    completed_this_run = 0
    while not diligence.completed:
        if maximum_stages is not None and completed_this_run >= maximum_stages:
            _diligence_pause(
                state,
                repository=repository,
                save_enabled=save_enabled,
                message=f"Completed {completed_this_run} diligence stage(s) in this run.",
            )
            return False
        stage = diligence.current_stage
        if stage == DiligenceStage.REQUEST_LIST:
            render_request_list(console, state)
            engine.advance_request_list(state)
        elif stage == DiligenceStage.INITIAL_PACKAGE:
            _run_diligence_checks(
                state,
                content=content,
                day=1,
                strategy=check_strategy,
                interactive=interactive,
            )
            for scene_id in DILIGENCE_DAY_SCENES[1]:
                _run_diligence_scene(
                    state,
                    content=content,
                    scene_id=scene_id,
                    diligence_path=diligence_path,
                    interactive=interactive,
                )
                if save_enabled:
                    repository.save(state)
            engine.prepare_initial_packages(state)
            render_package_versions(console, state)
        elif stage == DiligenceStage.RISK_SCHEDULE:
            _run_diligence_checks(
                state,
                content=content,
                day=2,
                strategy=check_strategy,
                interactive=interactive,
            )
            for scene_id in DILIGENCE_DAY_SCENES[2]:
                _run_diligence_scene(
                    state,
                    content=content,
                    scene_id=scene_id,
                    diligence_path=diligence_path,
                    interactive=interactive,
                )
                if save_enabled:
                    repository.save(state)
            engine.prepare_risk_schedule(state)
            render_risk_schedule(console, state)
            render_scenario_analysis(console, state)
        elif stage == DiligenceStage.Q_AND_A:
            _run_diligence_checks(
                state,
                content=content,
                day=3,
                strategy=check_strategy,
                interactive=interactive,
            )
            for scene_id in DILIGENCE_DAY_SCENES[3]:
                _run_diligence_scene(
                    state,
                    content=content,
                    scene_id=scene_id,
                    diligence_path=diligence_path,
                    interactive=interactive,
                )
                if save_enabled:
                    repository.save(state)
            engine.prepare_q_and_a(state)
            render_q_and_a(console, state)
        elif stage == DiligenceStage.SUPPLEMENTAL:
            _run_diligence_checks(
                state,
                content=content,
                day=4,
                strategy=check_strategy,
                interactive=interactive,
            )
            _run_diligence_scene(
                state,
                content=content,
                scene_id="dr_inconsistency_action",
                diligence_path=diligence_path,
                interactive=interactive,
            )
            engine.prepare_supplement(state)
            render_package_versions(console, state)
        elif stage == DiligenceStage.BEFORE_COMMITTEE:
            if pause_before_committee and not diligence.diligence_flags.get(
                "paused_before_committee"
            ):
                diligence.diligence_flags["paused_before_committee"] = True
                _diligence_pause(
                    state,
                    repository=repository,
                    save_enabled=save_enabled,
                    message="The supplemented record is saved before the committee meeting.",
                )
                return False
            for scene_id in ("dr_committee_position", "dr_final_action"):
                _run_diligence_scene(
                    state,
                    content=content,
                    scene_id=scene_id,
                    diligence_path=diligence_path,
                    interactive=interactive,
                )
                if save_enabled:
                    repository.save(state)
            engine.complete(state)
            render_diligence_room_report(
                console,
                build_diligence_room_report(state, content),
            )
        else:
            raise ValueError(f"unsupported diligence stage: {stage}")
        completed_this_run += 1
        if save_enabled:
            repository.save(state)
    if debug:
        render_debug(console, state)
    return True


def _load_interactive(
    repository: SaveRepository,
    content: ContentBundle,
) -> GameState | None:
    saves = repository.list_saves()
    if not saves:
        console.print("[yellow]No save games found.[/yellow]")
        return None
    slot = str(
        _ask(
            questionary.select(
                "Load which save?",
                choices=[
                    Choice(
                        title=(
                            f"{item.slot}: {item.player_name} · {item.game_date} · "
                            f"{'complete' if item.completed else 'in progress'}"
                        ),
                        value=item.slot,
                    )
                    for item in saves
                ],
            )
        )
    )
    return repository.load(slot, content=content)


@app.callback()
def main(
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Reveal conditions and state changes."),
    ] = False,
    quick_start: Annotated[
        bool,
        typer.Option("--quick-start", help="Bypass prompts for scripted verification."),
    ] = False,
    player_name: Annotated[
        str,
        typer.Option("--name", help="Quick-start player name."),
    ] = "Alex Mercer",
    background: Annotated[
        str,
        typer.Option(
            "--background",
            help="Quick-start background: accounting, finance, or data_analytics.",
        ),
    ] = Background.DATA_ANALYTICS.value,
    seed: Annotated[
        int,
        typer.Option("--seed", min=0, help="Quick-start deterministic seed."),
    ] = 1729,
    choice: Annotated[
        str | None,
        typer.Option("--choice", help="Quick-start scene choice ID."),
    ] = None,
    save_db: Annotated[
        Path,
        typer.Option("--save-db", help="SQLite save database path."),
    ] = DEFAULT_SAVE_DATABASE,
    no_save: Annotated[
        bool,
        typer.Option("--no-save", help="Do not write an autosave."),
    ] = False,
    hedge_choice: Annotated[
        str | None,
        typer.Option(
            "--hedge-choice",
            help="Run Milestone 2 with no_hedge, hedge_50, hedge_100, or hedge_150.",
        ),
    ] = None,
    memo_choice: Annotated[
        str | None,
        typer.Option("--memo-choice", help="Script the hedge-documentation decision."),
    ] = None,
    settlement_days: Annotated[
        int | None,
        typer.Option(
            "--settlement-days",
            min=0,
            help="Process at most this many Hedge Book days, then autosave.",
        ),
    ] = None,
    load_autosave: Annotated[
        bool,
        typer.Option(
            "--load-autosave",
            help="Bypass the menu and resume the autosave.",
        ),
    ] = False,
    daily_lessons: Annotated[
        bool,
        typer.Option(
            "--daily-lessons/--no-daily-lessons",
            help="Show or hide the short explanation after each settlement.",
        ),
    ] = True,
    market_path: Annotated[
        str | None,
        typer.Option(
            "--market-path",
            help="Override the deterministic market path by content ID.",
        ),
    ] = None,
    notification_choice: Annotated[
        str | None,
        typer.Option(
            "--notification-choice",
            help="Script the separate treasury-notification decision.",
        ),
    ] = None,
    funding_choice: Annotated[
        str | None,
        typer.Option(
            "--funding-choice",
            help="Use operating_cash, revolver, reduce_position, or miss_call.",
        ),
    ] = None,
    draw_amount: Annotated[
        float | None,
        typer.Option("--draw-amount", min=0, help="Override the revolver draw amount."),
    ] = None,
    reduce_contracts: Annotated[
        int | None,
        typer.Option(
            "--reduce-contracts",
            min=1,
            help="Contracts to close when choosing reduce_position.",
        ),
    ] = None,
    pause_after_notification: Annotated[
        bool,
        typer.Option(
            "--pause-after-notification",
            help="Autosave immediately after the treasury notification.",
        ),
    ] = False,
    game_mode: Annotated[
        str | None,
        typer.Option(
            "--game-mode",
            help="Start a new game in guided or standard mode.",
        ),
    ] = None,
    campaign_track: Annotated[
        str | None,
        typer.Option(
            "--campaign-track",
            help=("Campaign scope: series3_core, applied_foundations, or extended_story."),
        ),
    ] = None,
    show_math: Annotated[
        str | None,
        typer.Option(
            "--show-math",
            help="Tutorial math display: always, on_request, or off.",
        ),
    ] = None,
    skip_prologue: Annotated[
        bool,
        typer.Option(
            "--skip-prologue",
            help="Skip First Rotation without awarding learning progress.",
        ),
    ] = False,
    prologue_strategy: Annotated[
        str,
        typer.Option(
            "--prologue-strategy",
            help="Script checks as auto, correct, helped, or retry.",
        ),
    ] = "auto",
    prologue_choice: Annotated[
        str | None,
        typer.Option(
            "--prologue-choice",
            help="Script the durable First Rotation story choice.",
        ),
    ] = None,
    prologue_days: Annotated[
        int | None,
        typer.Option(
            "--prologue-days",
            min=0,
            max=3,
            help="Complete at most this many First Rotation days, then autosave.",
        ),
    ] = None,
    show_notebook: Annotated[
        bool,
        typer.Option(
            "--show-notebook",
            help="Open the saved Learning Notebook and exit.",
        ),
    ] = False,
    eleventh_path: Annotated[
        str | None,
        typer.Option(
            "--eleventh-path",
            help=(
                "Run Milestone 5 with formal_correction, marisol_supported, "
                "cal_then_correct, accept_cal, certify_unresolved, offset, "
                "quiet_file, lucky_unapproved, or leave_open_fail."
            ),
        ),
    ] = None,
    chapter_check_strategy: Annotated[
        str,
        typer.Option(
            "--chapter-check-strategy",
            help="Run chapter checks as auto, correct, helped, or retry.",
        ),
    ] = "auto",
    review_style: Annotated[
        str | None,
        typer.Option(
            "--review-style",
            help="Cumulative Core Review: learning or checkpoint.",
        ),
    ] = None,
    review_strategy: Annotated[
        str,
        typer.Option(
            "--review-strategy",
            help="Script the Core Review as correct, helped, or retry.",
        ),
    ] = "correct",
    applied_path: Annotated[
        str | None,
        typer.Option(
            "--applied-path",
            help=(
                "Script The Supply Gap as evidence_first, concise_operator, or escalation_first."
            ),
        ),
    ] = None,
    applied_days: Annotated[
        int | None,
        typer.Option(
            "--applied-days",
            min=0,
            max=3,
            help="Complete at most this many Supply Gap days, then autosave.",
        ),
    ] = None,
    pause_before_applied_review: Annotated[
        bool,
        typer.Option(
            "--pause-before-applied-review",
            help="Autosave after Supply Gap Day 3 and stop before its review.",
        ),
    ] = False,
    applied_review_style: Annotated[
        str | None,
        typer.Option(
            "--applied-review-style",
            help="Applied Foundations Review: learning or checkpoint.",
        ),
    ] = None,
    applied_review_strategy: Annotated[
        str,
        typer.Option(
            "--applied-review-strategy",
            help="Script the Applied review as correct, helped, or retry.",
        ),
    ] = "correct",
    remediation_strategy: Annotated[
        str,
        typer.Option(
            "--remediation-strategy",
            help="Applied remediation: auto, complete, or skip.",
        ),
    ] = "auto",
    notice_path: Annotated[
        str | None,
        typer.Option(
            "--notice-path",
            help=(
                "Script The Notice Window as evidence_first, concise_operator, or escalation_first."
            ),
        ),
    ] = None,
    notice_days: Annotated[
        int | None,
        typer.Option(
            "--notice-days",
            min=0,
            max=3,
            help="Complete at most this many Notice Window days, then autosave.",
        ),
    ] = None,
    pause_before_notice_review: Annotated[
        bool,
        typer.Option(
            "--pause-before-notice-review",
            help="Autosave after Notice Window Day 3 and stop before its review.",
        ),
    ] = False,
    notice_check_strategy: Annotated[
        str,
        typer.Option(
            "--notice-check-strategy",
            help="Run Notice Window checks as auto, correct, helped, or retry.",
        ),
    ] = "auto",
    notice_review_style: Annotated[
        str | None,
        typer.Option(
            "--notice-review-style",
            help="Notice Window Review: learning or checkpoint.",
        ),
    ] = None,
    notice_review_strategy: Annotated[
        str,
        typer.Option(
            "--notice-review-strategy",
            help="Script the Notice Window review as correct, helped, or retry.",
        ),
    ] = "correct",
    notice_remediation_strategy: Annotated[
        str,
        typer.Option(
            "--notice-remediation-strategy",
            help="Notice Window remediation: auto, complete, or skip.",
        ),
    ] = "auto",
    chapter_days: Annotated[
        int | None,
        typer.Option(
            "--chapter-days",
            min=0,
            max=3,
            help="Complete at most this many Eleventh Contract days, then autosave.",
        ),
    ] = None,
    pause_with_exception: Annotated[
        bool,
        typer.Option(
            "--pause-with-exception",
            help="Autosave after the Day 3 exception decision, before position action.",
        ),
    ] = False,
    audit_path: Annotated[
        str | None,
        typer.Option(
            "--audit-path",
            help=(
                "Run No Surprises with full_disclosure, supported_late, protect_desk, "
                "quiet_supplement, lucky_unauthorized, no_physical_support, inaccurate, "
                "automated, control_worked_late, policy_only, or risk_acceptance."
            ),
        ),
    ] = None,
    audit_check_strategy: Annotated[
        str,
        typer.Option(
            "--audit-check-strategy",
            help="Run audit checks as auto, correct, helped, or retry.",
        ),
    ] = "auto",
    audit_stages: Annotated[
        int | None,
        typer.Option(
            "--audit-stages",
            min=0,
            max=6,
            help="Complete at most this many No Surprises stages, then autosave.",
        ),
    ] = None,
    pause_before_exit: Annotated[
        bool,
        typer.Option(
            "--pause-before-exit",
            help="Autosave the management response before the audit exit meeting.",
        ),
    ] = False,
    diligence_path: Annotated[
        str | None,
        typer.Option(
            "--diligence-path",
            help=(
                "Run The Diligence Room with full_consistent, limited_then_supplement, "
                "inconsistent_versions, remediation_overstated, covenant_concern, "
                "cal_aligned, buyer_walks, or conditional_close."
            ),
        ),
    ] = None,
    diligence_check_strategy: Annotated[
        str,
        typer.Option(
            "--diligence-check-strategy",
            help="Run diligence checks as auto, correct, helped, or retry.",
        ),
    ] = "auto",
    diligence_stages: Annotated[
        int | None,
        typer.Option(
            "--diligence-stages",
            min=0,
            max=6,
            help="Complete at most this many Diligence Room stages, then autosave.",
        ),
    ] = None,
    pause_before_committee: Annotated[
        bool,
        typer.Option(
            "--pause-before-committee",
            help="Autosave the supplemented record before the committee meeting.",
        ),
    ] = False,
) -> None:
    """Play Lake Effect Ledger through The Diligence Room."""
    _configure_windows_utf8_output()
    render_title(console)
    try:
        content = ContentBundle.load(DEFAULT_CONTENT_ROOT)
    except (OSError, ValidationError, ValueError) as error:
        console.print(f"[bold red]Content validation failed:[/bold red] {error}")
        raise typer.Exit(code=2) from error
    repository = SaveRepository(save_db)

    if quick_start or load_autosave:
        try:
            selected_background = Background(background)
        except ValueError as error:
            raise typer.BadParameter(
                "background must be accounting, finance, or data_analytics",
                param_hint="--background",
            ) from error
        try:
            selected_mode = GameMode(game_mode or GameMode.STANDARD.value)
        except ValueError as error:
            raise typer.BadParameter(
                "game mode must be guided or standard",
                param_hint="--game-mode",
            ) from error
        try:
            selected_track = (
                CampaignTrack(campaign_track)
                if campaign_track is not None
                else (
                    CampaignTrack.EXTENDED_STORY
                    if audit_path is not None or diligence_path is not None
                    else (CampaignTrack.APPLIED_FOUNDATIONS if notice_path is not None else None)
                )
            )
        except ValueError as error:
            raise typer.BadParameter(
                "campaign track must be series3_core, applied_foundations, or extended_story",
                param_hint="--campaign-track",
            ) from error
        try:
            selected_math = ShowMathMode(show_math) if show_math is not None else None
        except ValueError as error:
            raise typer.BadParameter(
                "show math must be always, on_request, or off",
                param_hint="--show-math",
            ) from error
        if load_autosave:
            try:
                state = repository.load(content=content)
            except (KeyError, ValueError) as error:
                console.print(f"[bold red]Could not load autosave:[/bold red] {error}")
                raise typer.Exit(code=2) from error
            _apply_requested_campaign_track(state, selected_track)
        else:
            state = create_new_game(
                name=player_name,
                background=selected_background,
                seed=seed,
                content=content,
                game_mode=selected_mode,
                campaign_track=selected_track,
                show_math=selected_math,
                skip_prologue=skip_prologue,
            )
        if show_notebook:
            render_notebook(console, state, content)
            return
        if not state.prologue.completed:
            finished_prologue = _play_prologue(
                state,
                content=content,
                repository=repository,
                strategy=prologue_strategy,
                story_choice_id=prologue_choice,
                maximum_days=prologue_days,
                skip=skip_prologue,
                interactive=False,
                debug=debug,
                save_enabled=not no_save,
            )
            if not finished_prologue:
                return
        if state.hedge_book is None:
            _play(
                state,
                content=content,
                repository=repository,
                choice_id=choice or "request_meter_support",
                debug=debug and hedge_choice is None,
                save_enabled=not no_save,
            )
        explicit_campaign = campaign_track is not None
        resume_campaign = load_autosave and (
            state.learning.core_review.started
            or not state.core_campaign_completed
            or state.applied_foundations.status == AppliedSeasonStatus.IN_PROGRESS
            or state.notice_window.status == NoticeWindowStatus.IN_PROGRESS
            or (
                state.core_campaign_completed
                and state.campaign_track
                in {
                    CampaignTrack.APPLIED_FOUNDATIONS,
                    CampaignTrack.EXTENDED_STORY,
                }
                and state.applied_foundations.status
                not in {
                    AppliedSeasonStatus.COMPLETED,
                    AppliedSeasonStatus.LEGACY_SKIPPED,
                }
            )
            or (
                state.campaign_track
                in {
                    CampaignTrack.APPLIED_FOUNDATIONS,
                    CampaignTrack.EXTENDED_STORY,
                }
                and state.applied_foundations.status == AppliedSeasonStatus.COMPLETED
                and state.notice_window.status
                not in {
                    NoticeWindowStatus.COMPLETED,
                    NoticeWindowStatus.LEGACY_SKIPPED,
                }
            )
        )
        extended_track_requested = (
            explicit_campaign or resume_campaign
        ) and state.campaign_track == CampaignTrack.EXTENDED_STORY
        diligence_requested = (
            diligence_path is not None
            or state.diligence_room is not None
            or extended_track_requested
        )
        audit_requested = (
            audit_path is not None or state.no_surprises is not None or diligence_requested
        )
        applied_requested = state.campaign_track in {
            CampaignTrack.APPLIED_FOUNDATIONS,
            CampaignTrack.EXTENDED_STORY,
        } and (explicit_campaign or resume_campaign or audit_requested)
        chapter_requested = (
            eleventh_path is not None
            or state.eleventh_contract is not None
            or audit_requested
            or explicit_campaign
            or resume_campaign
        )
        if hedge_choice is not None or state.hedge_book is not None or chapter_requested:
            _play_hedge_book(
                state,
                content=content,
                repository=repository,
                hedge_level_id=hedge_choice or ("hedge_100" if chapter_requested else None),
                documentation_choice_id=memo_choice,
                maximum_days=settlement_days,
                debug=debug,
                save_enabled=not no_save,
                interactive=False,
                show_daily_lessons=daily_lessons,
                market_path_id=(
                    market_path
                    or (
                        content.hedge_scenarios.scenarios[0].price_path_ids[0]
                        if chapter_requested
                        else None
                    )
                ),
                notification_choice_id=notification_choice,
                funding_choice_id=funding_choice,
                draw_amount=Decimal(str(draw_amount)) if draw_amount is not None else None,
                reduce_contracts=reduce_contracts,
                pause_after_notification=pause_after_notification,
            )
        if chapter_requested:
            if state.hedge_book is None or not state.hedge_book.completed:
                return
            if state.treasury is not None and not state.treasury.completed:
                return
            chapter_finished = _play_eleventh_contract(
                state,
                content=content,
                repository=repository,
                chapter_path=eleventh_path,
                check_strategy=chapter_check_strategy,
                maximum_days=chapter_days,
                pause_with_exception=pause_with_exception,
                interactive=False,
                debug=debug,
                save_enabled=not no_save,
            )
            if not chapter_finished:
                return
            if not state.core_campaign_completed:
                review_finished = _play_core_review(
                    state,
                    content=content,
                    repository=repository,
                    style_name=review_style,
                    strategy=review_strategy,
                    interactive=False,
                    save_enabled=not no_save,
                )
                if not review_finished:
                    return
            if state.campaign_track == CampaignTrack.SERIES_3_CORE:
                console.print(
                    Panel(
                        "Series 3 Core is complete. No Surprises and The Diligence "
                        "Room remain available only in Extended Story. Returning to "
                        "the main-menu boundary.",
                        title="Core Campaign complete",
                        border_style="green",
                    )
                )
                return
        if applied_requested:
            if not state.core_campaign_completed:
                return
            applied_finished = _play_applied_foundations(
                state,
                content=content,
                repository=repository,
                applied_path=applied_path,
                check_strategy=chapter_check_strategy,
                maximum_days=applied_days,
                pause_before_review=pause_before_applied_review,
                review_style_name=applied_review_style,
                review_strategy=applied_review_strategy,
                remediation_strategy=remediation_strategy,
                interactive=False,
                debug=debug,
                save_enabled=not no_save,
            )
            if not applied_finished:
                return
            if state.campaign_track == CampaignTrack.APPLIED_FOUNDATIONS:
                notice_finished = _play_notice_window(
                    state,
                    content=content,
                    repository=repository,
                    notice_path=notice_path,
                    check_strategy=notice_check_strategy,
                    maximum_days=notice_days,
                    pause_before_review=pause_before_notice_review,
                    review_style_name=notice_review_style,
                    review_strategy=notice_review_strategy,
                    remediation_strategy=notice_remediation_strategy,
                    interactive=False,
                    debug=debug,
                    save_enabled=not no_save,
                )
                if not notice_finished:
                    return
                console.print(
                    Panel(
                        "Applied Foundations is complete through The Notice Window. "
                        "No Surprises and The Diligence Room remain available only "
                        "in Extended Story.",
                        title="Applied Foundations complete",
                        border_style="green",
                    )
                )
                return
        if audit_requested:
            if state.applied_foundations.status not in {
                AppliedSeasonStatus.COMPLETED,
                AppliedSeasonStatus.LEGACY_SKIPPED,
            }:
                return
            audit_finished = _play_no_surprises(
                state,
                content=content,
                repository=repository,
                audit_path=audit_path,
                check_strategy=audit_check_strategy,
                maximum_stages=audit_stages,
                pause_before_exit=pause_before_exit,
                interactive=False,
                debug=debug,
                save_enabled=not no_save,
            )
            if not audit_finished:
                return
            notice_finished = _play_notice_window(
                state,
                content=content,
                repository=repository,
                notice_path=notice_path,
                check_strategy=notice_check_strategy,
                maximum_days=notice_days,
                pause_before_review=pause_before_notice_review,
                review_style_name=notice_review_style,
                review_strategy=notice_review_strategy,
                remediation_strategy=notice_remediation_strategy,
                interactive=False,
                debug=debug,
                save_enabled=not no_save,
            )
            if not notice_finished:
                return
        if diligence_requested:
            if (
                state.no_surprises is None
                or not state.no_surprises.completed
                or state.notice_window.status
                not in {NoticeWindowStatus.COMPLETED, NoticeWindowStatus.LEGACY_SKIPPED}
            ):
                return
            _play_diligence_room(
                state,
                content=content,
                repository=repository,
                diligence_path=diligence_path,
                check_strategy=diligence_check_strategy,
                maximum_stages=diligence_stages,
                pause_before_committee=pause_before_committee,
                interactive=False,
                debug=debug,
                save_enabled=not no_save,
            )
        return

    action = _ask(
        questionary.select(
            "Northstar morning book:",
            choices=[
                Choice("New Game", value="new"),
                Choice("Load Game", value="load"),
                Choice("Quit", value="quit"),
            ],
        )
    )
    if action == "quit":
        return
    if action == "new":
        try:
            selected_mode = GameMode(game_mode) if game_mode is not None else None
        except ValueError as error:
            raise typer.BadParameter(
                "game mode must be guided or standard",
                param_hint="--game-mode",
            ) from error
        try:
            selected_track = CampaignTrack(campaign_track) if campaign_track is not None else None
        except ValueError as error:
            raise typer.BadParameter(
                "campaign track must be series3_core, applied_foundations, or extended_story",
                param_hint="--campaign-track",
            ) from error
        state = _new_interactive_game(content, selected_mode, selected_track)
    else:
        state = _load_interactive(repository, content)
    if state is None:
        return
    if action == "load" and campaign_track is not None:
        try:
            _apply_requested_campaign_track(state, CampaignTrack(campaign_track))
        except ValueError as error:
            raise typer.BadParameter(
                "campaign track must be series3_core, applied_foundations, or extended_story",
                param_hint="--campaign-track",
            ) from error
    if show_math is not None:
        try:
            state.show_math = ShowMathMode(show_math)
        except ValueError as error:
            raise typer.BadParameter(
                "show math must be always, on_request, or off",
                param_hint="--show-math",
            ) from error
    if show_notebook:
        render_notebook(console, state, content)
        return
    if not state.prologue.completed:
        finished_prologue = _play_prologue(
            state,
            content=content,
            repository=repository,
            strategy="auto",
            story_choice_id=None,
            maximum_days=None,
            skip=skip_prologue,
            interactive=True,
            debug=debug,
            save_enabled=not no_save,
        )
        if not finished_prologue:
            return
    if state.hedge_book is None:
        _play(
            state,
            content=content,
            repository=repository,
            choice_id=None,
            debug=debug,
            save_enabled=not no_save,
        )
        continue_to_hedge = bool(
            _ask(
                questionary.confirm(
                    "Continue to Episode 1: The Hedge Book?",
                    default=True,
                )
            )
        )
        if not continue_to_hedge:
            return
    _play_hedge_book(
        state,
        content=content,
        repository=repository,
        hedge_level_id=None,
        documentation_choice_id=None,
        maximum_days=None,
        debug=debug,
        save_enabled=not no_save,
        interactive=True,
        show_daily_lessons=daily_lessons,
        market_path_id=None,
        notification_choice_id=None,
        funding_choice_id=None,
        draw_amount=None,
        reduce_contracts=None,
        pause_after_notification=False,
    )
    if state.hedge_book is None or not state.hedge_book.completed:
        return
    if state.treasury is not None and not state.treasury.completed:
        return
    continue_to_chapter = state.eleventh_contract is not None or bool(
        _ask(
            questionary.confirm(
                "Continue to The Eleventh Contract?",
                default=True,
            )
        )
    )
    if continue_to_chapter:
        chapter_finished = _play_eleventh_contract(
            state,
            content=content,
            repository=repository,
            chapter_path=eleventh_path,
            check_strategy=chapter_check_strategy,
            maximum_days=chapter_days,
            pause_with_exception=pause_with_exception,
            interactive=True,
            debug=debug,
            save_enabled=not no_save,
        )
        if not chapter_finished:
            return
        if not state.core_campaign_completed:
            review_finished = _play_core_review(
                state,
                content=content,
                repository=repository,
                style_name=review_style,
                strategy=review_strategy,
                interactive=True,
                save_enabled=not no_save,
            )
            if not review_finished:
                return
        if state.campaign_track == CampaignTrack.SERIES_3_CORE:
            console.print(
                Panel(
                    "The Series 3 Core Campaign stops here. No Surprises and "
                    "The Diligence Room were not entered. Returning to the "
                    "main-menu boundary.",
                    title="Core Campaign complete",
                    border_style="green",
                )
            )
            return
        applied_finished = _play_applied_foundations(
            state,
            content=content,
            repository=repository,
            applied_path=applied_path,
            check_strategy=chapter_check_strategy,
            maximum_days=applied_days,
            pause_before_review=pause_before_applied_review,
            review_style_name=applied_review_style,
            review_strategy=applied_review_strategy,
            remediation_strategy=remediation_strategy,
            interactive=True,
            debug=debug,
            save_enabled=not no_save,
        )
        if not applied_finished:
            return
        if state.campaign_track == CampaignTrack.APPLIED_FOUNDATIONS:
            notice_finished = _play_notice_window(
                state,
                content=content,
                repository=repository,
                notice_path=notice_path,
                check_strategy=notice_check_strategy,
                maximum_days=notice_days,
                pause_before_review=pause_before_notice_review,
                review_style_name=notice_review_style,
                review_strategy=notice_review_strategy,
                remediation_strategy=notice_remediation_strategy,
                interactive=True,
                debug=debug,
                save_enabled=not no_save,
            )
            if not notice_finished:
                return
            console.print(
                Panel(
                    "The Applied Foundations campaign stops after The Notice Window. "
                    "No Surprises and The Diligence Room were not entered.",
                    title="Applied Foundations complete",
                    border_style="green",
                )
            )
            return
        continue_to_audit = state.no_surprises is not None or bool(
            _ask(
                questionary.confirm(
                    "Continue to No Surprises?",
                    default=True,
                )
            )
        )
        if continue_to_audit:
            audit_finished = _play_no_surprises(
                state,
                content=content,
                repository=repository,
                audit_path=audit_path,
                check_strategy=audit_check_strategy,
                maximum_stages=audit_stages,
                pause_before_exit=pause_before_exit,
                interactive=True,
                debug=debug,
                save_enabled=not no_save,
            )
            if not audit_finished:
                return
            continue_to_notice = state.notice_window.status in {
                NoticeWindowStatus.IN_PROGRESS,
                NoticeWindowStatus.COMPLETED,
                NoticeWindowStatus.LEGACY_SKIPPED,
            } or bool(
                _ask(
                    questionary.confirm(
                        "Continue to The Notice Window?",
                        default=True,
                    )
                )
            )
            if not continue_to_notice:
                return
            notice_finished = _play_notice_window(
                state,
                content=content,
                repository=repository,
                notice_path=notice_path,
                check_strategy=notice_check_strategy,
                maximum_days=notice_days,
                pause_before_review=pause_before_notice_review,
                review_style_name=notice_review_style,
                review_strategy=notice_review_strategy,
                remediation_strategy=notice_remediation_strategy,
                interactive=True,
                debug=debug,
                save_enabled=not no_save,
            )
            if not notice_finished:
                return
            continue_to_diligence = state.diligence_room is not None or bool(
                _ask(
                    questionary.confirm(
                        "Continue to The Diligence Room?",
                        default=True,
                    )
                )
            )
            if continue_to_diligence:
                _play_diligence_room(
                    state,
                    content=content,
                    repository=repository,
                    diligence_path=diligence_path,
                    check_strategy=diligence_check_strategy,
                    maximum_stages=diligence_stages,
                    pause_before_committee=pause_before_committee,
                    interactive=True,
                    debug=debug,
                    save_enabled=not no_save,
                )


if __name__ == "__main__":  # pragma: no cover
    app()
