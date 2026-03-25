"""Built-in scenario templates for the product library."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.utils.config_loader import load_config


def built_in_templates() -> list[dict[str, Any]]:
    """Return the default scenario templates shipped with the product."""

    base = load_config()
    templates: list[tuple[str, str, str, dict[str, Any]]] = [
        (
            "open-terrain-rescue",
            "Open Terrain Rescue",
            "open_terrain",
            {
                "weather": "clear",
                "strategy": "information_gain",
                "num_drones": 4,
            },
        ),
        (
            "dense-forest-poor-comms",
            "Dense Forest Poor Comms",
            "poor_comms",
            {
                "scenario_family": "dense_forest",
                "weather": "windy",
                "strategy": "auction_based",
                "communication": {
                    "radius": 7.0,
                    "packet_loss_probability": 0.25,
                    "latency": 2,
                    "coordination_mode": "decentralized",
                },
            },
        ),
        (
            "windy-ridge-line-search",
            "Windy Ridge-Line Search",
            "high_wind",
            {
                "weather": "storm",
                "strategy": "probability_greedy",
                "use_external_layers": True,
            },
        ),
        (
            "low-battery-mission",
            "Low Battery Mission",
            "low_battery_budget",
            {
                "drone": {"battery": 80.0, "speed": 1, "sensor_range": 5.0, "fov": 130.0},
                "battery_policy": {"return_threshold": 34.0},
                "strategy": "sector_search",
            },
        ),
        (
            "obstacle-heavy-search",
            "Obstacle Heavy Search",
            "obstacle_heavy",
            {
                "terrain": {"obstacle_ratio": 0.16},
                "strategy": "auction_based",
            },
        ),
    ]

    records: list[dict[str, Any]] = []
    for template_id, name, family, overrides in templates:
        payload = deepcopy(base)
        payload["scenario"]["name"] = name
        payload["scenario"]["scenario_family"] = family
        payload["scenario"].update({key: value for key, value in overrides.items() if not isinstance(value, dict)})
        for key, value in overrides.items():
            if isinstance(value, dict):
                payload["scenario"].setdefault(key, {}).update(value)
        records.append(
            {
                "template_id": template_id,
                "name": name,
                "family": family,
                "description": f"Built-in template for {name.lower()}",
                "payload": payload,
            }
        )
    return records
