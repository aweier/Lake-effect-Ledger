"""Versioned SQLite save slots containing validated JSON state."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from lake_effect_ledger.learning.models import CampaignTrack
from lake_effect_ledger.state import SAVE_SCHEMA_VERSION, GameState

if TYPE_CHECKING:
    from lake_effect_ledger.narrative.models import ContentBundle

DATABASE_SCHEMA_VERSION = 1
OLDEST_SUPPORTED_SAVE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class SaveSummary:
    slot: str
    player_name: str
    game_date: str
    completed: bool
    saved_at: str


class SaveRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS save_slots (
                    slot TEXT PRIMARY KEY,
                    save_schema_version INTEGER NOT NULL,
                    player_name TEXT NOT NULL,
                    game_date TEXT NOT NULL,
                    completed INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'database_schema_version'"
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO metadata (key, value) VALUES (?, ?)",
                    ("database_schema_version", str(DATABASE_SCHEMA_VERSION)),
                )
            elif int(row["value"]) != DATABASE_SCHEMA_VERSION:
                raise ValueError(
                    f"unsupported database schema version {row['value']}; "
                    f"expected {DATABASE_SCHEMA_VERSION}"
                )

    def save(self, state: GameState, slot: str = "autosave") -> None:
        self.initialize()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO save_slots (
                    slot, save_schema_version, player_name, game_date,
                    completed, state_json, saved_at
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(slot) DO UPDATE SET
                    save_schema_version = excluded.save_schema_version,
                    player_name = excluded.player_name,
                    game_date = excluded.game_date,
                    completed = excluded.completed,
                    state_json = excluded.state_json,
                    saved_at = CURRENT_TIMESTAMP
                """,
                (
                    slot,
                    state.save_schema_version,
                    state.player.name,
                    state.current_date.isoformat(),
                    int(
                        (
                            state.core_campaign_completed
                            if state.campaign_track == CampaignTrack.SERIES_3_CORE
                            else (
                                state.applied_foundations.status.value == "completed"
                                and state.notice_window.status.value == "completed"
                            )
                        )
                        if state.campaign_track != CampaignTrack.EXTENDED_STORY
                        else (
                            state.completed
                            and (state.hedge_book is None or state.hedge_book.completed)
                            and (state.treasury is None or state.treasury.completed)
                            and (
                                state.eleventh_contract is None or state.eleventh_contract.completed
                            )
                            and (state.no_surprises is None or state.no_surprises.completed)
                            and state.notice_window.status.value != "in_progress"
                            and (state.diligence_room is None or state.diligence_room.completed)
                        )
                    ),
                    state.model_dump_json(),
                ),
            )

    def load(
        self,
        slot: str = "autosave",
        *,
        content: ContentBundle | None = None,
    ) -> GameState:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT save_schema_version, state_json FROM save_slots WHERE slot = ?",
                (slot,),
            ).fetchone()
        if row is None:
            raise KeyError(f"save slot not found: {slot}")
        stored_version = row["save_schema_version"]
        if not OLDEST_SUPPORTED_SAVE_SCHEMA_VERSION <= stored_version <= SAVE_SCHEMA_VERSION:
            raise ValueError(
                f"save slot uses unsupported schema {stored_version}; "
                f"supported versions are {OLDEST_SUPPORTED_SAVE_SCHEMA_VERSION}"
                f" through {SAVE_SCHEMA_VERSION}"
            )
        payload = json.loads(row["state_json"])
        migrated = migrate_state_payload(payload)
        state = GameState.model_validate(migrated)
        if (
            stored_version < 10
            and state.core_campaign_completed
            and content is not None
            and not any(
                item.season_id == "series3_core" for item in state.learning.assessment_snapshots
            )
        ):
            from lake_effect_ledger.learning.models import SnapshotProvenance
            from lake_effect_ledger.learning.snapshots import finalize_core_snapshot

            finalize_core_snapshot(
                state,
                content,
                provenance=(
                    SnapshotProvenance.RECONSTRUCTED_FROM_V9
                    if stored_version == 9
                    else SnapshotProvenance.LEGACY_ATTEMPT_HISTORY_UNKNOWN
                ),
            )
        core_snapshot = any(
            item.season_id == "series3_core" for item in state.learning.assessment_snapshots
        )
        applied_snapshot = any(
            item.season_id == "applied_foundations" for item in state.learning.assessment_snapshots
        )
        notice_snapshot = any(
            item.season_id == "notice_window" for item in state.learning.assessment_snapshots
        )
        if stored_version >= 10 and state.core_campaign_completed != core_snapshot:
            raise ValueError("semantically invalid save: Core completion and snapshot disagree")
        if state.applied_foundations.snapshot_finalized != applied_snapshot:
            raise ValueError("semantically invalid save: Applied snapshot state disagrees")
        if state.applied_foundations.status.value == "completed" and not applied_snapshot:
            raise ValueError("semantically invalid save: completed Applied review lacks a snapshot")
        if state.notice_window.snapshot_finalized != notice_snapshot:
            raise ValueError("semantically invalid save: Notice Window snapshot state disagrees")
        if state.notice_window.status.value == "completed" and not notice_snapshot:
            raise ValueError(
                "semantically invalid save: completed Notice Window review lacks a snapshot"
            )
        return state

    def list_saves(self) -> list[SaveSummary]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT slot, player_name, game_date, completed, saved_at
                FROM save_slots
                ORDER BY saved_at DESC, slot
                """
            ).fetchall()
        return [
            SaveSummary(
                slot=row["slot"],
                player_name=row["player_name"],
                game_date=row["game_date"],
                completed=bool(row["completed"]),
                saved_at=row["saved_at"],
            )
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection


def migrate_state_payload(payload: dict[str, object]) -> dict[str, object]:
    """Migrate a decoded save payload without discarding any prior state."""
    migrated = dict(payload)
    version = migrated.get("save_schema_version")
    if not isinstance(version, int):
        raise ValueError("save payload is missing an integer save_schema_version")
    if version < OLDEST_SUPPORTED_SAVE_SCHEMA_VERSION or version > SAVE_SCHEMA_VERSION:
        raise ValueError(f"unsupported save schema version: {version}")

    if version == 1:
        resources = migrated.get("resources")
        if not isinstance(resources, dict):
            raise ValueError("Milestone 1 save has invalid resources")
        migrated_resources = dict(resources)
        migrated_resources.setdefault("evidence_exposure", 10)
        migrated["resources"] = migrated_resources
        migrated.setdefault("hedge_book", None)
        migrated["save_schema_version"] = 2
        version = 2

    if version == 2:
        migrated.setdefault("treasury", None)
        migrated.setdefault("evidence_log", [])
        migrated["save_schema_version"] = 3
        version = 3

    if version == 3:
        player = migrated.get("player")
        if not isinstance(player, dict):
            raise ValueError("Milestone 3 save has invalid player data")
        migrated_player = dict(player)
        migrated_player.setdefault("role", "Northstar Analyst")
        migrated["player"] = migrated_player
        migrated["game_mode"] = "standard"
        migrated["show_math"] = "off"
        migrated["prologue"] = {
            "started": False,
            "completed": True,
            "skipped": True,
            "transitioned_to_episode_1": True,
            "current_day_index": 0,
            "current_check_index": 0,
            "story_choice_id": None,
        }
        migrated["learning"] = {}
        migrated["career_trajectory"] = {}
        migrated["save_schema_version"] = 4
        version = 4

    if version == 4:
        migrated.setdefault("eleventh_contract", None)
        migrated["save_schema_version"] = 5
        version = 5

    if version == 5:
        migrated.setdefault("no_surprises", None)
        migrated["save_schema_version"] = 6
        version = 6

    if version == 6:
        migrated.setdefault("diligence_room", None)
        migrated["save_schema_version"] = 7
        version = 7

    if version == 7:
        migrated["campaign_track"] = "extended_story"
        migrated["core_chapter_debrief_ids"] = []
        migrated["core_debrief_completed"] = True
        migrated["core_campaign_completed"] = True
        learning = migrated.get("learning")
        if not isinstance(learning, dict):
            raise ValueError("Milestone 7 save has invalid learning data")
        migrated_learning = dict(learning)
        checks = migrated_learning.get("checks", {})
        if not isinstance(checks, dict):
            raise ValueError("Milestone 7 save has invalid check progress")
        migrated_checks: dict[str, object] = {}
        for check_id, raw_progress in checks.items():
            if not isinstance(raw_progress, dict):
                raise ValueError(f"Milestone 7 check {check_id} has invalid progress")
            progress = dict(raw_progress)
            # v7 stored only the latest answer, so first-attempt history is unknown.
            progress["first_answer"] = None
            progress["first_attempt_correct"] = None
            progress["final_correct"] = bool(progress.get("completed", False))
            progress["independently_demonstrated"] = False
            progress["review_recommended"] = bool(progress.get("incorrect_attempts", 0) >= 2)
            migrated_checks[str(check_id)] = progress
        migrated_learning["checks"] = migrated_checks
        objectives = migrated_learning.get("objectives", {})
        if not isinstance(objectives, dict):
            raise ValueError("Milestone 7 save has invalid objective progress")
        migrated_objectives: dict[str, object] = {}
        for objective_id, raw_progress in objectives.items():
            if not isinstance(raw_progress, dict):
                raise ValueError(f"Milestone 7 objective {objective_id} has invalid progress")
            progress = dict(raw_progress)
            if progress.get("status") == "demonstrated":
                progress["status"] = "completed_history_unknown"
            progress.setdefault("check_ids", [])
            progress.setdefault("chapter_ids", [])
            progress.setdefault("independent_demonstrations", 0)
            progress.setdefault("retry_demonstrations", 0)
            progress.setdefault("assisted_completions", 0)
            migrated_objectives[str(objective_id)] = progress
        migrated_learning["objectives"] = migrated_objectives
        migrated_learning["core_review"] = {}
        migrated["learning"] = migrated_learning
        migrated["save_schema_version"] = 8
        version = 8

    if version == 8:
        introduced: list[str] = []
        prologue = migrated.get("prologue")
        if isinstance(prologue, dict):
            current_day = int(prologue.get("current_day_index", 0))
            if prologue.get("started") or prologue.get("completed"):
                introduced.extend(["evelyn_marsh", "marisol_vega"])
            if current_day >= 2 or prologue.get("completed"):
                introduced.extend(["darren_cho", "june_halvorsen"])
        if migrated.get("completed"):
            introduced.append("vince_rourke")
        if migrated.get("hedge_book") is not None:
            introduced.extend(["cal_rourke", "evelyn_marsh", "marisol_vega"])
        eleventh = migrated.get("eleventh_contract")
        if isinstance(eleventh, dict):
            introduced.extend(["cal_rourke", "evelyn_marsh", "marisol_vega"])
            if int(eleventh.get("current_day", 1)) >= 3 or eleventh.get("completed"):
                introduced.append("dom_bellini")
        if migrated.get("no_surprises") is not None:
            introduced.append("noah_shah")
        if migrated.get("diligence_room") is not None:
            introduced.extend(["sofia_marin", "ingrid_holtz", "mara_voss"])
        migrated["introduced_character_ids"] = list(dict.fromkeys(introduced))
        migrated["save_schema_version"] = 9
        version = 9

    if version == 9:
        introduced = migrated.get("introduced_character_ids", [])
        if not isinstance(introduced, list):
            raise ValueError("Milestone 9 save has invalid introduced-character data")
        learning = migrated.get("learning")
        if not isinstance(learning, dict):
            raise ValueError("Milestone 9 save has invalid learning data")
        migrated_learning = dict(learning)
        migrated_learning.setdefault("assessment_snapshots", [])
        migrated["learning"] = migrated_learning
        already_in_later_story = (
            migrated.get("no_surprises") is not None or migrated.get("diligence_room") is not None
        )
        migrated["applied_foundations"] = (
            {
                "status": "legacy_skipped",
                "legacy_skip_reason": (
                    "Legacy Extended Story save had already entered No Surprises "
                    "or The Diligence Room."
                ),
            }
            if already_in_later_story
            else {}
        )
        migrated["save_schema_version"] = 10
        version = 10

    if version == 10:
        learning = migrated.get("learning")
        if not isinstance(learning, dict):
            raise ValueError("Milestone 10 save has invalid learning data")
        migrated_learning = dict(learning)
        migrated_learning.setdefault("assessment_snapshots", [])
        migrated["learning"] = migrated_learning
        migrated.setdefault("applied_foundations", {})
        already_in_diligence = migrated.get("diligence_room") is not None
        migrated["notice_window"] = (
            {
                "status": "legacy_skipped",
                "legacy_skip_reason": (
                    "Legacy save had already entered The Diligence Room before "
                    "The Notice Window existed."
                ),
            }
            if already_in_diligence
            else {}
        )
        migrated["save_schema_version"] = 11
        version = 11

    if version == 11:
        learning = migrated.get("learning")
        if not isinstance(learning, dict):
            raise ValueError("Milestone 11 save has invalid learning data")
        migrated_learning = dict(learning)
        migrated_learning.setdefault("assessment_snapshots", [])
        migrated["learning"] = migrated_learning
        migrated.setdefault("applied_foundations", {})
        migrated.setdefault("notice_window", {})

    if version != SAVE_SCHEMA_VERSION:
        raise ValueError(f"no migration path to save schema {SAVE_SCHEMA_VERSION}")
    return migrated
