import json
import sqlite3
from datetime import UTC, date, datetime, timedelta

import pytest

from lake_effect_ledger.audit.models import (
    AuditEngagement,
    AuditScope,
    EvidenceRequest,
    NoSurprisesState,
    RequestedItem,
)
from lake_effect_ledger.game import create_new_game
from lake_effect_ledger.learning.core import CoreReviewEngine
from lake_effect_ledger.learning.engine import LearningEngine
from lake_effect_ledger.learning.models import (
    CampaignTrack,
    QuestionCategory,
    ReviewStyle,
    SnapshotProvenance,
)
from lake_effect_ledger.persistence.saves import SaveRepository, migrate_state_payload
from lake_effect_ledger.state import Background
from lake_effect_ledger.trading.models import EleventhOutcome


def _state(content):
    return create_new_game(
        name="Migration Learner",
        background=Background.FINANCE,
        seed=1728,
        content=content,
        campaign_track=CampaignTrack.SERIES_3_CORE,
    )


def _complete_core_review(state, content) -> None:
    review = CoreReviewEngine(content)
    learning = LearningEngine(content)
    review.start(state, ReviewStyle.LEARNING)
    while (reference := review.current_reference(state)) is not None:
        review.submit(state, learning.expected_answer(reference.check_id))
    state.core_debrief_completed = True
    state.core_campaign_completed = True


def _legacy_payload(state, version: int) -> dict[str, object]:
    payload = state.model_dump(mode="json")
    payload["save_schema_version"] = version
    payload.pop("applied_foundations")
    payload.pop("notice_window")
    learning = payload["learning"]
    learning.pop("assessment_snapshots")
    for response in learning["core_review"]["responses"].values():
        response.pop("final_answer", None)
    if version == 8:
        payload.pop("introduced_character_ids")
    return payload


def _write_legacy(repository, payload, version) -> None:
    repository.initialize()
    with sqlite3.connect(repository.path) as connection:
        connection.execute(
            """
            INSERT INTO save_slots (
                slot, save_schema_version, player_name, game_date,
                completed, state_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "autosave",
                version,
                payload["player"]["name"],
                payload["current_date"],
                1,
                json.dumps(payload),
            ),
        )


def _minimal_audit_state() -> NoSurprisesState:
    opened = datetime(2028, 2, 1, 9, tzinfo=UTC)
    item = RequestedItem(
        request_item_id="request_one",
        requested_record="One record",
        stable_record_id="record_one",
        record_type="memo",
        available=True,
        date_created=opened - timedelta(days=1),
        related_transaction="transaction_one",
    )
    engagement = AuditEngagement(
        engagement_id="engagement_one",
        title="Test engagement",
        objective="Test legacy skip",
        lead_auditor_id="noah_shah",
        opened_at=opened,
        scope=AuditScope(
            transaction_reference="transaction_one",
            period_start=date(2028, 1, 1),
            period_end=date(2028, 1, 31),
            included_processes=["hedging"],
            excluded_processes=["delivery"],
        ),
    )
    request = EvidenceRequest(
        request_id="request_one",
        engagement_id=engagement.engagement_id,
        issued_at=opened,
        due_at=opened + timedelta(days=1),
        requested_items=[item],
    )
    return NoSurprisesState(
        scenario_id="no_surprises",
        prior_eleventh_outcome=EleventhOutcome.CLEAN_CORRECTION,
        engagement=engagement,
        evidence_request=request,
    )


def test_completed_v9_review_reconstructs_authoritative_snapshot(content, tmp_path) -> None:
    state = _state(content)
    _complete_core_review(state, content)
    payload = _legacy_payload(state, 9)
    repository = SaveRepository(tmp_path / "v9-complete.db")
    _write_legacy(repository, payload, 9)

    restored = repository.load(content=content)
    snapshot = restored.learning.assessment_snapshots[0]

    assert snapshot.season_id == "series3_core"
    assert snapshot.provenance == SnapshotProvenance.RECONSTRUCTED_FROM_V9
    assert snapshot.completed_story_date == content.eleventh_scenario.day_3_date
    assert len(snapshot.questions) == len(content.curriculum.review_questions)
    assert {item.category for item in snapshot.questions} == {
        QuestionCategory.CALCULATION,
        QuestionCategory.CONCEPTUAL,
    }
    assert all(item.first_attempt_correct for item in snapshot.questions)
    assert restored.applied_foundations.status.value == "not_started"
    assert restored.notice_window.status.value == "not_started"


def test_older_completed_core_without_attempts_records_unknown_history(
    content,
    tmp_path,
) -> None:
    state = _state(content)
    state.learning.core_review.completed = True
    state.learning.core_review.current_question_index = len(content.curriculum.review_questions)
    state.core_campaign_completed = True
    payload = _legacy_payload(state, 8)
    repository = SaveRepository(tmp_path / "v8-unknown.db")
    _write_legacy(repository, payload, 8)

    restored = repository.load(content=content)
    snapshot = restored.learning.assessment_snapshots[0]

    assert snapshot.provenance == SnapshotProvenance.LEGACY_ATTEMPT_HISTORY_UNKNOWN
    assert snapshot.calculation_first_attempt_correct is None
    assert snapshot.conceptual_first_attempt_correct is None
    assert all(item.first_answer is None for item in snapshot.questions)
    assert all(item.first_attempt_correct is None for item in snapshot.questions)
    assert all(item.final_correct is None for item in snapshot.questions)


def test_incomplete_v9_core_does_not_receive_completed_snapshot(content, tmp_path) -> None:
    state = _state(content)
    payload = _legacy_payload(state, 9)
    repository = SaveRepository(tmp_path / "v9-incomplete.db")
    _write_legacy(repository, payload, 9)

    restored = repository.load(content=content)

    assert restored.learning.assessment_snapshots == []


def test_v9_later_story_state_is_marked_legacy_skipped(content, tmp_path) -> None:
    state = _state(content)
    _complete_core_review(state, content)
    state.campaign_track = CampaignTrack.EXTENDED_STORY
    state.no_surprises = _minimal_audit_state()
    payload = _legacy_payload(state, 9)
    repository = SaveRepository(tmp_path / "v9-later-story.db")
    _write_legacy(repository, payload, 9)

    restored = repository.load(content=content)

    assert restored.applied_foundations.status.value == "legacy_skipped"
    assert "already entered No Surprises" in (restored.applied_foundations.legacy_skip_reason)


def test_v9_migration_preserves_existing_state_outside_new_v10_fields(
    content,
    tmp_path,
) -> None:
    state = _state(content)
    _complete_core_review(state, content)
    payload = _legacy_payload(state, 9)
    repository = SaveRepository(tmp_path / "v9-preservation.db")
    _write_legacy(repository, payload, 9)

    restored = repository.load(content=content).model_dump(mode="json")

    for key, value in payload.items():
        if key in {"save_schema_version", "learning"}:
            continue
        assert restored[key] == value
    for key, value in payload["learning"].items():
        if key == "core_review":
            continue
        assert restored["learning"][key] == value


def test_unsupported_and_semantically_invalid_saves_fail_explicitly(
    content,
    tmp_path,
) -> None:
    state = _state(content)
    invalid_repository = SaveRepository(tmp_path / "invalid-v10.db")
    payload = state.model_dump(mode="json")
    payload["applied_foundations"]["status"] = "legacy_skipped"
    _write_legacy(invalid_repository, payload, 10)
    with pytest.raises(ValueError, match="legacy-skipped"):
        invalid_repository.load(content=content)

    missing_snapshot = SaveRepository(tmp_path / "missing-snapshot.db")
    payload = state.model_dump(mode="json")
    payload["core_campaign_completed"] = True
    _write_legacy(missing_snapshot, payload, 10)
    with pytest.raises(ValueError, match="Core completion and snapshot disagree"):
        missing_snapshot.load(content=content)

    future_repository = SaveRepository(tmp_path / "future.db")
    payload = state.model_dump(mode="json")
    payload["save_schema_version"] = 12
    _write_legacy(future_repository, payload, 12)
    with pytest.raises(ValueError, match="unsupported schema 12"):
        future_repository.load(content=content)


def test_v10_to_v11_adds_notice_state_and_never_moves_diligence_backward(
    content,
) -> None:
    state = _state(content)
    payload = state.model_dump(mode="json")
    payload["save_schema_version"] = 10
    payload.pop("notice_window")

    migrated = migrate_state_payload(payload)

    assert migrated["save_schema_version"] == 11
    assert migrated["notice_window"] == {}

    payload["diligence_room"] = {"legacy_marker": True}
    skipped = migrate_state_payload(payload)
    assert skipped["notice_window"]["status"] == "legacy_skipped"
    assert "Diligence Room" in skipped["notice_window"]["legacy_skip_reason"]
