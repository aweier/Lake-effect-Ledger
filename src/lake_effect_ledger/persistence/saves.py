"""Versioned SQLite save slots containing validated JSON state."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from lake_effect_ledger.state import SAVE_SCHEMA_VERSION, GameState

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
                        state.completed
                        and (state.hedge_book is None or state.hedge_book.completed)
                        and (state.treasury is None or state.treasury.completed)
                        and (state.eleventh_contract is None or state.eleventh_contract.completed)
                    ),
                    state.model_dump_json(),
                ),
            )

    def load(self, slot: str = "autosave") -> GameState:
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
        return GameState.model_validate(migrated)

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

    if version != SAVE_SCHEMA_VERSION:
        raise ValueError(f"no migration path to save schema {SAVE_SCHEMA_VERSION}")
    return migrated
