"""Scenario and scenario-library services."""

from __future__ import annotations

from pathlib import Path
import time
from typing import Any

import yaml

from app.backend.core.templates import built_in_templates
from app.backend.db.sqlite import MetadataStore
from app.backend.domain.shared import scenario_summary, to_jsonable
from app.backend.storage import LocalProductPaths, slugify
from src.scenarios.scenario import ScenarioConfig
from src.utils.config_loader import DEFAULT_CONFIG_PATH, load_config, load_scenario_config


class ScenarioService:
    """Persist and retrieve product-facing scenarios."""

    def __init__(self, paths: LocalProductPaths, store: MetadataStore) -> None:
        self.paths = paths
        self.store = store
        self._bootstrap_default()

    def list_scenarios(self) -> list[dict[str, Any]]:
        rows = self.store.list("scenarios", "deleted_at IS NULL")
        return sorted(rows, key=lambda item: item["updated_at"], reverse=True)

    def load_scenario(self, scenario_id: str) -> dict[str, Any]:
        record = self.store.get("scenarios", scenario_id)
        if record is None or record.get("deleted_at") is not None:
            raise FileNotFoundError(f"Unknown scenario: {scenario_id}")
        return record

    def create_scenario(
        self,
        payload: dict[str, Any],
        scenario_id: str | None = None,
    ) -> dict[str, Any]:
        scenario_name = payload.get("scenario", {}).get("name") or scenario_id or f"scenario-{int(time.time())}"
        safe_id = slugify(scenario_id or scenario_name)
        return self._persist_scenario(safe_id, payload, existing=self.store.get("scenarios", safe_id))

    def update_scenario(self, scenario_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._persist_scenario(scenario_id, payload, existing=self.store.get("scenarios", scenario_id))

    def delete_scenario(self, scenario_id: str) -> None:
        record = self.load_scenario(scenario_id)
        now = time.time()
        self.store.upsert(
            "scenarios",
            scenario_id,
            {
                "name": record["name"],
                "type": record.get("type", "scenario"),
                "created_at": record["created_at"],
                "updated_at": now,
                "deleted_at": now,
                "config_json": record["config_json"],
                "summary_json": record["summary_json"],
                "file_path": record.get("file_path"),
            },
        )
        file_path = Path(record["file_path"])
        if file_path.exists():
            file_path.unlink()

    def get_presets(self) -> dict[str, Any]:
        default_raw = load_config(DEFAULT_CONFIG_PATH)
        config = load_scenario_config(DEFAULT_CONFIG_PATH)
        return {
            "default": to_jsonable(default_raw),
            "scenario_families": [
                "open_terrain",
                "dense_forest",
                "mixed_terrain",
                "obstacle_heavy",
                "poor_comms",
                "high_wind",
                "low_battery_budget",
                "layered_demo",
            ],
            "strategies": config.benchmark_strategies,
            "target_behaviors": [
                "random_walk",
                "terrain_biased",
                "trail_biased",
                "injured_slow",
                "stationary_intervals",
            ],
            "coordination_modes": list(config.benchmark_coordination_modes),
            "sensor_modes": list(config.benchmark_sensor_modes),
        }

    @staticmethod
    def scenario_to_config(payload: dict[str, Any]) -> ScenarioConfig:
        return ScenarioConfig.from_dict(payload)

    def _bootstrap_default(self) -> None:
        self.create_scenario(load_config(DEFAULT_CONFIG_PATH), scenario_id="default")

    def _persist_scenario(
        self,
        scenario_id: str,
        payload: dict[str, Any],
        existing: dict[str, Any] | None,
    ) -> dict[str, Any]:
        config = self.scenario_to_config(payload)
        file_path = self.paths.scenarios_dir / f"{scenario_id}.yaml"
        file_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        now = time.time()
        self.store.upsert(
            "scenarios",
            scenario_id,
            {
                "name": payload.get("scenario", {}).get("name", scenario_id),
                "type": "scenario",
                "created_at": existing["created_at"] if existing else now,
                "updated_at": now,
                "deleted_at": None,
                "config_json": to_jsonable(payload),
                "summary_json": scenario_summary(config),
                "file_path": str(file_path.resolve()),
            },
        )
        return self.load_scenario(scenario_id)


class TemplateService:
    """Manage built-in templates and their library metadata."""

    def __init__(self, paths: LocalProductPaths, store: MetadataStore) -> None:
        self.paths = paths
        self.store = store
        self._bootstrap_templates()

    def list_templates(self) -> list[dict[str, Any]]:
        rows = self.store.list("scenario_templates")
        return sorted(rows, key=lambda item: item["name"])

    def get_template(self, template_id: str) -> dict[str, Any]:
        record = self.store.get("scenario_templates", template_id)
        if record is None:
            raise FileNotFoundError(f"Unknown template: {template_id}")
        return record

    def list_library_entries(self) -> list[dict[str, Any]]:
        rows = self.store.list("template_library_entries")
        return sorted(rows, key=lambda item: (item["family"], item["name"]))

    def get_library_entry(self, entry_id: str) -> dict[str, Any]:
        record = self.store.get("template_library_entries", entry_id)
        if record is None:
            raise FileNotFoundError(f"Unknown library template: {entry_id}")
        return record

    def _bootstrap_templates(self) -> None:
        now = time.time()
        for template in built_in_templates():
            template_id = template["template_id"]
            file_path = self.paths.templates_dir / f"{template_id}.yaml"
            file_path.write_text(
                yaml.safe_dump(template["payload"], sort_keys=False),
                encoding="utf-8",
            )
            config = ScenarioService.scenario_to_config(template["payload"])
            existing = self.store.get("scenario_templates", template_id)
            common_fields = {
                "name": template["name"],
                "family": template["family"],
                "description": template["description"],
                "created_at": existing["created_at"] if existing else now,
                "updated_at": now,
                "config_json": to_jsonable(template["payload"]),
                "summary_json": scenario_summary(config),
                "file_path": str(file_path.resolve()),
            }
            self.store.upsert("scenario_templates", template_id, common_fields)
            self.store.upsert(
                "template_library_entries",
                template_id,
                {
                    "template_id": template_id,
                    "name": template["name"],
                    "family": template["family"],
                    "doctrine_type": template["doctrine_type"],
                    "description": template["description"],
                    "intended_use": template["intended_use"],
                    "recommended_strategies_json": list(template["recommended_strategies"]),
                    "risks_json": list(template["risks"]),
                    "assumptions_json": list(template["assumptions"]),
                    "tags_json": list(template["tags"]),
                    "config_json": to_jsonable(template["payload"]),
                    "summary_json": scenario_summary(config),
                    "file_path": str(file_path.resolve()),
                },
            )
