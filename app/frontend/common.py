"""Shared helpers for the Streamlit mission decision-support UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from matplotlib import pyplot as plt

from app.frontend.api_client import ApiClient, ApiError, DEFAULT_API_BASE_URL
from src.visualisation.renderer import SimulationRenderer


def get_api_client() -> ApiClient:
    return ApiClient(st.session_state.get("api_base_url", DEFAULT_API_BASE_URL))


def load_json(path: str) -> dict[str, Any]:
    return get_api_client().get(path)


def post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    return get_api_client().post(path, payload)


def ensure_frontend_state() -> None:
    st.session_state.setdefault("api_base_url", DEFAULT_API_BASE_URL)
    st.session_state.setdefault("selected_scenario_id", "")
    st.session_state.setdefault("selected_run_id", "")
    st.session_state.setdefault("selected_experiment_id", "")


def build_scenario_payload(default: dict[str, Any] | None = None, key_prefix: str = "scenario") -> dict[str, Any]:
    default = default or {}
    scenario = default.get("scenario", {})
    drone = scenario.get("drone", {})
    sensor = scenario.get("sensor", {})
    communication = scenario.get("communication", {})
    battery = scenario.get("battery_policy", {})
    terrain = scenario.get("terrain", {})
    target_assumptions = scenario.get("target_assumptions", {})
    belief = scenario.get("belief", {})
    hierarchical = scenario.get("hierarchical_planner", {})
    render = scenario.get("render", {})

    with st.form(f"{key_prefix}-editor", clear_on_submit=False):
        name = st.text_input("Scenario name", value=scenario.get("name", "Mission Draft"), key=f"{key_prefix}-name")
        col1, col2, col3 = st.columns(3)
        map_width = col1.number_input("Map width", min_value=8, max_value=200, value=int(scenario.get("map_size", [18, 14])[0]), key=f"{key_prefix}-width")
        map_height = col2.number_input("Map height", min_value=8, max_value=200, value=int(scenario.get("map_size", [18, 14])[1]), key=f"{key_prefix}-height")
        num_drones = col3.number_input("Drone count", min_value=1, max_value=20, value=int(scenario.get("num_drones", 5)), key=f"{key_prefix}-drones")

        col4, col5, col6 = st.columns(3)
        strategies = ["random_sweep", "sector_search", "probability_greedy", "auction_based", "information_gain"]
        strategy = col4.selectbox("Strategy", strategies, index=strategies.index(scenario.get("strategy", "information_gain")), key=f"{key_prefix}-strategy")
        weathers = ["clear", "windy", "rain", "storm"]
        weather = col5.selectbox("Weather", weathers, index=weathers.index(scenario.get("weather", "clear")), key=f"{key_prefix}-weather")
        behaviors = ["random_walk", "terrain_biased", "trail_biased", "injured_slow", "stationary_intervals"]
        target_behavior = col6.selectbox("Target behavior", behaviors, index=behaviors.index(target_assumptions.get("behavior", "terrain_biased")), key=f"{key_prefix}-behavior")

        col7, col8, col9 = st.columns(3)
        last_known_x = col7.number_input("Last known X", min_value=0, value=int(scenario.get("last_known_position", [9, 7])[0]), key=f"{key_prefix}-lkx")
        last_known_y = col8.number_input("Last known Y", min_value=0, value=int(scenario.get("last_known_position", [9, 7])[1]), key=f"{key_prefix}-lky")
        max_steps = col9.number_input("Max steps", min_value=1, max_value=500, value=int(scenario.get("max_steps", 45)), key=f"{key_prefix}-maxsteps")

        st.markdown("**Mission Controls**")
        col10, col11, col12, col13 = st.columns(4)
        drone_battery = col10.number_input("Battery", min_value=10.0, value=float(drone.get("battery", 120.0)), key=f"{key_prefix}-battery")
        drone_speed = col11.number_input("Speed", min_value=1, max_value=5, value=int(drone.get("speed", 1)), key=f"{key_prefix}-speed")
        sensor_range = col12.number_input("Sensor range", min_value=1.0, value=float(drone.get("sensor_range", 5.0)), key=f"{key_prefix}-range")
        fov = col13.number_input("Field of view", min_value=30.0, max_value=360.0, value=float(drone.get("fov", 130.0)), key=f"{key_prefix}-fov")

        col14, col15, col16 = st.columns(3)
        sensor_mode = col14.selectbox("Sensor mode", ["thermal_only", "thermal_visual"], index=["thermal_only", "thermal_visual"].index(sensor.get("mode", "thermal_visual")), key=f"{key_prefix}-sensor")
        false_positive_rate = col15.number_input("False positive rate", min_value=0.0, max_value=1.0, value=float(sensor.get("false_positive_rate", 0.02)), key=f"{key_prefix}-fpr")
        false_negative_rate = col16.number_input("False negative rate", min_value=0.0, max_value=1.0, value=float(sensor.get("false_negative_rate", 0.08)), key=f"{key_prefix}-fnr")

        st.markdown("**Comms and Reserves**")
        col17, col18, col19, col20 = st.columns(4)
        coordination_mode = col17.selectbox("Coordination mode", ["centralized", "decentralized"], index=["centralized", "decentralized"].index(communication.get("coordination_mode", "centralized")), key=f"{key_prefix}-coord")
        comms_radius = col18.number_input("Communication radius", min_value=1.0, value=float(communication.get("radius", 12.0)), key=f"{key_prefix}-radius")
        packet_loss = col19.number_input("Packet loss", min_value=0.0, max_value=1.0, value=float(communication.get("packet_loss_probability", 0.08)), key=f"{key_prefix}-loss")
        comms_latency = col20.number_input("Latency (steps)", min_value=0, max_value=10, value=int(communication.get("latency", 1)), key=f"{key_prefix}-latency")
        return_threshold = st.number_input("Return-to-base threshold", min_value=1.0, value=float(battery.get("return_threshold", 28.0)), key=f"{key_prefix}-return")

        st.markdown("**Map and Layer Settings**")
        col21, col22, col23 = st.columns(3)
        families = ["open_terrain", "dense_forest", "mixed_terrain", "obstacle_heavy", "poor_comms", "high_wind", "low_battery_budget", "layered_demo"]
        scenario_family = col21.selectbox("Scenario family", families, index=families.index(scenario.get("scenario_family", "mixed_terrain")), key=f"{key_prefix}-family")
        use_external_layers = col22.checkbox("Use external layers", value=bool(scenario.get("use_external_layers", False)), key=f"{key_prefix}-layers")
        obstacle_ratio = col23.number_input("Obstacle ratio", min_value=0.0, max_value=0.8, value=float(terrain.get("obstacle_ratio", 0.08)), key=f"{key_prefix}-obstacles")
        layer_paths = {
            "terrain": st.text_input("Terrain layer path", value=scenario.get("layer_paths", {}).get("terrain", "data/sample_layers/terrain.csv"), key=f"{key_prefix}-terrain"),
            "obstacle": st.text_input("Obstacle layer path", value=scenario.get("layer_paths", {}).get("obstacle", "data/sample_layers/obstacles.csv"), key=f"{key_prefix}-obstacle"),
            "trail": st.text_input("Trail layer path", value=scenario.get("layer_paths", {}).get("trail", "data/sample_layers/trails.csv"), key=f"{key_prefix}-trail"),
            "elevation": st.text_input("Elevation layer path", value=scenario.get("layer_paths", {}).get("elevation", "data/sample_layers/elevation.csv"), key=f"{key_prefix}-elevation"),
            "wind": st.text_input("Wind layer path", value=scenario.get("layer_paths", {}).get("wind", "data/sample_layers/wind.csv"), key=f"{key_prefix}-wind"),
        }

        st.markdown("**Belief and Planner Settings**")
        col24, col25, col26 = st.columns(3)
        belief_motion_strength = col24.number_input("Belief motion strength", min_value=0.0, max_value=1.0, value=float(belief.get("motion_strength", 0.18)), key=f"{key_prefix}-motion")
        belief_positive_gain = col25.number_input("Belief positive gain", min_value=0.1, max_value=5.0, value=float(belief.get("positive_gain", 1.6)), key=f"{key_prefix}-gain")
        confirmation_threshold = col26.number_input("Confirmation threshold", min_value=0.1, max_value=10.0, value=float(belief.get("candidate_confirmation_threshold", 1.2)), key=f"{key_prefix}-confirm")
        col27, col28 = st.columns(2)
        hierarchical_enabled = col27.checkbox("Hierarchical planning enabled", value=bool(hierarchical.get("enabled", True)), key=f"{key_prefix}-hier")
        objective_count = col28.number_input("Objective count", min_value=1, max_value=50, value=int(hierarchical.get("objective_count", 6)), key=f"{key_prefix}-objectives")
        submitted = st.form_submit_button("Save")

    if not submitted:
        return {}

    return {
        "scenario": {
            "name": name,
            "map_size": [int(map_width), int(map_height)],
            "weather": weather,
            "num_drones": int(num_drones),
            "last_known_position": [int(last_known_x), int(last_known_y)],
            "target_assumptions": {
                "behavior": target_behavior,
                "target_move_probability": float(target_assumptions.get("target_move_probability", 0.42)),
                "target_speed": int(target_assumptions.get("target_speed", 1)),
                "drift_sigma": float(target_assumptions.get("drift_sigma", 4.5)),
            },
            "max_steps": int(max_steps),
            "strategy": strategy,
            "scenario_family": scenario_family,
            "use_external_layers": use_external_layers,
            "layer_paths": layer_paths,
            "drone": {
                "battery": float(drone_battery),
                "speed": int(drone_speed),
                "sensor_range": float(sensor_range),
                "fov": float(fov),
            },
            "sensor": {
                "mode": sensor_mode,
                "false_positive_rate": float(false_positive_rate),
                "false_negative_rate": float(false_negative_rate),
                "visual_range_factor": float(sensor.get("visual_range_factor", 0.8)),
                "visual_false_positive_rate": float(sensor.get("visual_false_positive_rate", 0.01)),
                "visual_false_negative_rate": float(sensor.get("visual_false_negative_rate", 0.12)),
            },
            "communication": {
                "radius": float(comms_radius),
                "packet_loss_probability": float(packet_loss),
                "latency": int(comms_latency),
                "coordination_mode": coordination_mode,
            },
            "battery_policy": {"return_threshold": float(return_threshold)},
            "terrain": {
                "obstacle_ratio": float(obstacle_ratio),
                "distribution": terrain.get("distribution", {"plain": 0.42, "forest": 0.24, "hill": 0.16, "urban": 0.12, "water": 0.06}),
            },
            "belief": {
                "motion_strength": float(belief_motion_strength),
                "positive_gain": float(belief_positive_gain),
                "candidate_confirmation_threshold": float(confirmation_threshold),
            },
            "hierarchical_planner": {
                "enabled": hierarchical_enabled,
                "objective_count": int(objective_count),
            },
            "render": {
                "save_frames": bool(render.get("save_frames", True)),
                "frame_stride": int(render.get("frame_stride", 3)),
            },
        }
    }


def render_snapshot(snapshot: dict[str, Any]) -> None:
    fig, _ = SimulationRenderer.render_static(snapshot, show=False, close_figure=False)
    st.pyplot(fig)
    plt.close(fig)


def scenario_table(records: list[dict[str, Any]]) -> None:
    if not records:
        st.info("No scenarios available.")
        return
    dataframe = pd.DataFrame(
        [
            {
                "id": item["id"],
                "name": item["name"],
                "strategy": item["summary_json"].get("strategy"),
                "family": item["summary_json"].get("scenario_family"),
                "drones": item["summary_json"].get("num_drones"),
                "weather": item["summary_json"].get("weather"),
            }
            for item in records
        ]
    )
    st.dataframe(dataframe, use_container_width=True)


def artifact_image(path: str | None, caption: str) -> None:
    if path and Path(path).exists():
        st.image(path, caption=caption)


def api_error_block(exc: Exception) -> None:
    st.error(f"Backend error: {exc}")
