"""Review wrapper for The Notice Window's reusable assessment behavior."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lake_effect_ledger.applied_foundations.review import AppliedReviewEngine
from lake_effect_ledger.learning.models import SnapshotProvenance

if TYPE_CHECKING:
    from lake_effect_ledger.narrative.models import ContentBundle


class NoticeWindowReviewEngine(AppliedReviewEngine):
    state_attribute = "notice_window"
    season_id = "notice_window"
    season_label = "Notice Window"
    story_label = "The Notice Window"
    review_chapter_id = "notice_window_review"
    snapshot_provenance = SnapshotProvenance.NATIVE_V11

    def __init__(self, content: ContentBundle) -> None:
        super().__init__(content, blueprint=content.notice_window)
