"""SQLite persistence for product metadata and artifact indexing."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any


class MetadataStore:
    """Simple SQLite metadata store with JSON payload columns."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS scenarios (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL DEFAULT 'scenario',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    deleted_at REAL,
                    config_json TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    file_path TEXT
                );

                CREATE TABLE IF NOT EXISTS scenario_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    family TEXT NOT NULL,
                    description TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    config_json TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    file_path TEXT
                );

                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    scenario_id TEXT NOT NULL,
                    plan_id TEXT,
                    comparison_id TEXT,
                    candidate_id TEXT,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    completed_at REAL,
                    config_json TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    latest_snapshot_json TEXT,
                    output_dir TEXT NOT NULL,
                    job_id TEXT,
                    FOREIGN KEY (scenario_id) REFERENCES scenarios(id)
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    owner_type TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress REAL NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    completed_at REAL,
                    error TEXT,
                    summary_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS interventions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(id)
                );

                CREATE TABLE IF NOT EXISTS experiments (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    completed_at REAL,
                    request_json TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    output_dir TEXT NOT NULL,
                    job_id TEXT,
                    error TEXT
                );

                CREATE TABLE IF NOT EXISTS reports (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    owner_type TEXT NOT NULL DEFAULT 'run',
                    owner_id TEXT,
                    report_type TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    summary_json TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(id)
                );

                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_type TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    path TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS mission_plans (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    scenario_id TEXT,
                    template_id TEXT,
                    approval_state TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    deleted_at REAL,
                    plan_json TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    recommendation_json TEXT NOT NULL,
                    operator_notes TEXT NOT NULL,
                    candidate_alternatives_json TEXT NOT NULL,
                    priority_zones_json TEXT NOT NULL,
                    exclusion_zones_json TEXT NOT NULL,
                    latest_comparison_id TEXT,
                    latest_review_id TEXT,
                    linked_run_ids_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS plan_comparisons (
                    id TEXT PRIMARY KEY,
                    plan_id TEXT,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    completed_at REAL,
                    request_json TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    recommendation_json TEXT NOT NULL,
                    uncertainty_json TEXT NOT NULL,
                    sensitivity_json TEXT NOT NULL,
                    linked_run_ids_json TEXT NOT NULL,
                    report_id TEXT,
                    job_id TEXT,
                    FOREIGN KEY (plan_id) REFERENCES mission_plans(id)
                );

                CREATE TABLE IF NOT EXISTS plan_candidates (
                    id TEXT PRIMARY KEY,
                    comparison_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    rank INTEGER NOT NULL,
                    linked_run_id TEXT,
                    config_json TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    FOREIGN KEY (comparison_id) REFERENCES plan_comparisons(id)
                );

                CREATE TABLE IF NOT EXISTS after_action_reviews (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    plan_id TEXT,
                    comparison_id TEXT,
                    name TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    summary_json TEXT NOT NULL,
                    timeline_json TEXT NOT NULL,
                    alternate_plan_json TEXT NOT NULL,
                    report_id TEXT,
                    FOREIGN KEY (run_id) REFERENCES runs(id)
                );

                CREATE TABLE IF NOT EXISTS template_library_entries (
                    id TEXT PRIMARY KEY,
                    template_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    family TEXT NOT NULL,
                    doctrine_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    intended_use TEXT NOT NULL,
                    recommended_strategies_json TEXT NOT NULL,
                    risks_json TEXT NOT NULL,
                    assumptions_json TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    file_path TEXT
                );
                """
            )
            self._ensure_columns(
                connection,
                "runs",
                {
                    "plan_id": "TEXT",
                    "comparison_id": "TEXT",
                    "candidate_id": "TEXT",
                },
            )
            self._ensure_columns(
                connection,
                "reports",
                {
                    "owner_type": "TEXT NOT NULL DEFAULT 'run'",
                    "owner_id": "TEXT",
                },
            )

    @staticmethod
    def _ensure_columns(
        connection: sqlite3.Connection,
        table: str,
        columns: dict[str, str],
    ) -> None:
        existing = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for column_name, column_ddl in columns.items():
            if column_name not in existing:
                connection.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column_name} {column_ddl}"
                )

    def upsert(self, table: str, record_id: str, fields: dict[str, Any]) -> None:
        columns = ["id"] + list(fields.keys())
        placeholders = ", ".join("?" for _ in columns)
        assignments = ", ".join(f"{column}=excluded.{column}" for column in fields.keys())
        values = [record_id] + [self._serialize(value) for value in fields.values()]
        with self._connect() as connection:
            connection.execute(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) "
                f"ON CONFLICT(id) DO UPDATE SET {assignments}",
                values,
            )

    def insert_intervention(self, run_id: str, action: str, payload: dict[str, Any], created_at: float) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO interventions (run_id, action, payload_json, created_at) VALUES (?, ?, ?, ?)",
                [run_id, action, self._serialize(payload), created_at],
            )

    def insert_artifact(
        self,
        owner_type: str,
        owner_id: str,
        artifact_type: str,
        path: str,
        metadata: dict[str, Any],
        created_at: float,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO artifacts (owner_type, owner_id, artifact_type, path, metadata_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [owner_type, owner_id, artifact_type, path, self._serialize(metadata), created_at],
            )

    def delete(self, table: str, record_id: str) -> None:
        with self._connect() as connection:
            connection.execute(f"DELETE FROM {table} WHERE id = ?", [record_id])

    def get(self, table: str, record_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(f"SELECT * FROM {table} WHERE id = ?", [record_id]).fetchone()
        return self._row_to_dict(row) if row is not None else None

    def list(self, table: str, where: str = "", values: list[Any] | None = None) -> list[dict[str, Any]]:
        query = f"SELECT * FROM {table}"
        if where:
            query += f" WHERE {where}"
        with self._connect() as connection:
            rows = connection.execute(query, values or []).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def list_artifacts(self, owner_type: str, owner_id: str) -> list[dict[str, Any]]:
        return self.list("artifacts", "owner_type = ? AND owner_id = ?", [owner_type, owner_id])

    def list_interventions(self, run_id: str) -> list[dict[str, Any]]:
        return self.list("interventions", "run_id = ?", [run_id])

    @staticmethod
    def _serialize(value: Any) -> Any:
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value)
        return value

    @staticmethod
    def _deserialize(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if not stripped:
            return value
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        return {key: self._deserialize(row[key]) for key in row.keys()}
