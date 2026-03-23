"""YAML configuration loader helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.scenarios.scenario import ScenarioConfig


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs" / "default.yaml"


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load raw YAML configuration data from disk."""

    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as file_handle:
        return yaml.safe_load(file_handle) or {}


def load_scenario_config(path: str | Path = DEFAULT_CONFIG_PATH) -> ScenarioConfig:
    """Load and parse a ScenarioConfig from YAML."""

    return ScenarioConfig.from_dict(load_config(path))
