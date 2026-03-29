"""Built-in scenario templates for the product library."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.utils.config_loader import load_config


def built_in_templates() -> list[dict[str, Any]]:
    """Return the default scenario templates shipped with the product."""

    base = load_config()
    templates: list[dict[str, Any]] = [
        {
            "template_id": "open-terrain-rescue",
            "name": "Open Terrain Rescue",
            "family": "open_terrain",
            "doctrine_type": "wide-area sweep",
            "description": "Baseline open-area rescue doctrine with strong line-of-sight and moderate coverage pressure.",
            "intended_use": "Use for broad daytime searches where communications are reliable and terrain is permissive.",
            "recommended_strategies": ["information_gain", "auction_based"],
            "risks": ["over-coverage near base", "faster battery draw if drone count is low"],
            "assumptions": ["clear weather", "good comms", "moderate target mobility"],
            "tags": ["baseline", "open", "rescue"],
            "overrides": {
                "weather": "clear",
                "strategy": "information_gain",
                "num_drones": 4,
            },
        },
        {
            "template_id": "dense-canopy-poor-comms",
            "name": "Dense Canopy Poor Comms",
            "family": "dense_forest",
            "doctrine_type": "resilient decentralized search",
            "description": "Forest search preset designed for degraded communications and low line-of-sight sensing.",
            "intended_use": "Use for canopy-heavy searches where centralized coordination is fragile.",
            "recommended_strategies": ["auction_based", "sector_search"],
            "risks": ["stale local information", "higher false negatives under canopy"],
            "assumptions": ["windy weather", "packet loss", "decentralized coordination"],
            "tags": ["forest", "poor-comms", "decentralized"],
            "overrides": {
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
        },
        {
            "template_id": "windy-ridge-line-search",
            "name": "Windy Ridge-Line Search",
            "family": "high_wind",
            "doctrine_type": "terrain-following search",
            "description": "Ridge-line search preset using layered terrain with wind-aware energy penalties.",
            "intended_use": "Use when teams expect movement along trails or ridge features in exposed terrain.",
            "recommended_strategies": ["probability_greedy", "information_gain"],
            "risks": ["battery drain from wind", "sensor degradation in exposed cells"],
            "assumptions": ["external layers available", "wind effects are significant"],
            "tags": ["ridge", "wind", "terrain-layer"],
            "overrides": {
                "weather": "storm",
                "strategy": "probability_greedy",
                "use_external_layers": True,
            },
        },
        {
            "template_id": "low-battery-contingency",
            "name": "Low Battery Contingency",
            "family": "low_battery_budget",
            "doctrine_type": "conservative reserve doctrine",
            "description": "Preset for missions where assets are constrained and safe return margins dominate.",
            "intended_use": "Use for long transits, degraded charging logistics, or reserve-sensitive missions.",
            "recommended_strategies": ["sector_search", "auction_based"],
            "risks": ["reduced coverage depth", "early returns limiting detection opportunities"],
            "assumptions": ["battery budget is constrained", "return threshold should stay high"],
            "tags": ["battery", "reserve", "contingency"],
            "overrides": {
                "drone": {"battery": 80.0, "speed": 1, "sensor_range": 5.0, "fov": 130.0},
                "battery_policy": {"return_threshold": 34.0},
                "strategy": "sector_search",
            },
        },
        {
            "template_id": "staged-sector-sweep",
            "name": "Staged Sector Sweep",
            "family": "mixed_terrain",
            "doctrine_type": "structured containment search",
            "description": "Operational sector sweep preset emphasizing orderly coverage and moderate deconfliction.",
            "intended_use": "Use for staged SAR operations where teams want predictable sector ownership.",
            "recommended_strategies": ["sector_search", "auction_based"],
            "risks": ["slower convergence if belief is sharply peaked", "handoff friction at sector edges"],
            "assumptions": ["moderate comms", "structured search doctrine"],
            "tags": ["sector", "structured", "containment"],
            "overrides": {
                "strategy": "sector_search",
                "num_drones": 5,
                "weather": "clear",
            },
        },
        {
            "template_id": "rapid-containment",
            "name": "Rapid Containment",
            "family": "obstacle_heavy",
            "doctrine_type": "high-priority containment",
            "description": "Fast containment preset for narrowing movement corridors around likely escape routes.",
            "intended_use": "Use when the search team needs rapid perimeter coverage before detailed sweep behavior.",
            "recommended_strategies": ["auction_based", "probability_greedy"],
            "risks": ["higher overlap at choke points", "battery burn from aggressive repositioning"],
            "assumptions": ["high urgency", "belief mass is locally concentrated"],
            "tags": ["containment", "rapid", "priority"],
            "overrides": {
                "terrain": {"obstacle_ratio": 0.16},
                "strategy": "auction_based",
                "num_drones": 6,
            },
        },
        {
            "template_id": "obstacle-heavy-search",
            "name": "Obstacle Heavy Search",
            "family": "obstacle_heavy",
            "doctrine_type": "obstacle navigation",
            "description": "Dense-obstacle search doctrine for cluttered terrain with routing pressure.",
            "intended_use": "Use where obstacles strongly constrain pathing and search progression.",
            "recommended_strategies": ["auction_based", "information_gain"],
            "risks": ["reroutes", "path inefficiency", "sector fragmentation"],
            "assumptions": ["obstacle fields dominate movement cost"],
            "tags": ["obstacles", "routing", "cluttered"],
            "overrides": {
                "terrain": {"obstacle_ratio": 0.16},
                "strategy": "auction_based",
            },
        },
    ]

    records: list[dict[str, Any]] = []
    for template in templates:
        template_id = template["template_id"]
        name = template["name"]
        family = template["family"]
        overrides = template["overrides"]
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
                "doctrine_type": template["doctrine_type"],
                "description": template["description"],
                "intended_use": template["intended_use"],
                "recommended_strategies": list(template["recommended_strategies"]),
                "risks": list(template["risks"]),
                "assumptions": list(template["assumptions"]),
                "tags": list(template["tags"]),
                "payload": payload,
            }
        )
    return records
