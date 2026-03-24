"""Streamlit frontend for local mission planning and review."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
from matplotlib import pyplot as plt

from app.frontend.api_client import ApiClient, ApiError, DEFAULT_API_BASE_URL
from src.visualisation.renderer import SimulationRenderer


st.set_page_config(
    page_title="Swarm Mission Planner",
    page_icon="S",
    layout="wide",
)


def get_api_client() -> ApiClient:
    return ApiClient(st.session_state.get("api_base_url", DEFAULT_API_BASE_URL))


def load_json(path: str) -> dict:
    return get_api_client().get(path)


def post_json(path: str, payload: dict) -> dict:
    return get_api_client().post(path, payload)


def build_scenario_payload(default: dict | None = None) -> dict:
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

    st.subheader("Scenario Editor")
    with st.form("scenario-editor", clear_on_submit=False):
        name = st.text_input("Scenario name", value=scenario.get("name", "Mission Draft"))
        col1, col2, col3 = st.columns(3)
        map_width = col1.number_input("Map width", min_value=8, max_value=200, value=int(scenario.get("map_size", [18, 14])[0]))
        map_height = col2.number_input("Map height", min_value=8, max_value=200, value=int(scenario.get("map_size", [18, 14])[1]))
        num_drones = col3.number_input("Drone count", min_value=1, max_value=20, value=int(scenario.get("num_drones", 5)))

        col4, col5, col6 = st.columns(3)
        strategy = col4.selectbox(
            "Strategy",
            ["random_sweep", "sector_search", "probability_greedy", "auction_based", "information_gain"],
            index=["random_sweep", "sector_search", "probability_greedy", "auction_based", "information_gain"].index(scenario.get("strategy", "information_gain")),
        )
        weather = col5.selectbox("Weather", ["clear", "windy", "rain", "storm"], index=["clear", "windy", "rain", "storm"].index(scenario.get("weather", "clear")))
        target_behavior = col6.selectbox(
            "Target behavior",
            ["random_walk", "terrain_biased", "trail_biased", "injured_slow", "stationary_intervals"],
            index=["random_walk", "terrain_biased", "trail_biased", "injured_slow", "stationary_intervals"].index(target_assumptions.get("behavior", "terrain_biased")),
        )

        col7, col8, col9 = st.columns(3)
        last_known_x = col7.number_input("Last known X", min_value=0, value=int(scenario.get("last_known_position", [9, 7])[0]))
        last_known_y = col8.number_input("Last known Y", min_value=0, value=int(scenario.get("last_known_position", [9, 7])[1]))
        max_steps = col9.number_input("Max steps", min_value=1, max_value=500, value=int(scenario.get("max_steps", 45)))

        st.markdown("**Drone and Sensor Settings**")
        col10, col11, col12, col13 = st.columns(4)
        drone_battery = col10.number_input("Battery", min_value=10.0, value=float(drone.get("battery", 120.0)))
        drone_speed = col11.number_input("Speed", min_value=1, max_value=5, value=int(drone.get("speed", 1)))
        sensor_range = col12.number_input("Sensor range", min_value=1.0, value=float(drone.get("sensor_range", 5.0)))
        fov = col13.number_input("Field of view", min_value=30.0, max_value=360.0, value=float(drone.get("fov", 130.0)))

        col14, col15, col16 = st.columns(3)
        sensor_mode = col14.selectbox(
            "Sensor mode",
            ["thermal_only", "thermal_visual"],
            index=["thermal_only", "thermal_visual"].index(sensor.get("mode", "thermal_visual")),
        )
        false_positive_rate = col15.number_input("False positive rate", min_value=0.0, max_value=1.0, value=float(sensor.get("false_positive_rate", 0.02)))
        false_negative_rate = col16.number_input("False negative rate", min_value=0.0, max_value=1.0, value=float(sensor.get("false_negative_rate", 0.08)))

        st.markdown("**Comms and Battery Policy**")
        col17, col18, col19, col20 = st.columns(4)
        coordination_mode = col17.selectbox(
            "Coordination mode",
            ["centralized", "decentralized"],
            index=["centralized", "decentralized"].index(communication.get("coordination_mode", "centralized")),
        )
        comms_radius = col18.number_input("Communication radius", min_value=1.0, value=float(communication.get("radius", 12.0)))
        packet_loss = col19.number_input("Packet loss", min_value=0.0, max_value=1.0, value=float(communication.get("packet_loss_probability", 0.08)))
        comms_latency = col20.number_input("Latency (steps)", min_value=0, max_value=10, value=int(communication.get("latency", 1)))
        return_threshold = st.number_input("Return-to-base threshold", min_value=1.0, value=float(battery.get("return_threshold", 28.0)))

        st.markdown("**Map and Layer Settings**")
        col21, col22, col23 = st.columns(3)
        scenario_family = col21.selectbox(
            "Scenario family",
            ["open_terrain", "dense_forest", "mixed_terrain", "obstacle_heavy", "poor_comms", "high_wind", "low_battery_budget", "layered_demo"],
            index=["open_terrain", "dense_forest", "mixed_terrain", "obstacle_heavy", "poor_comms", "high_wind", "low_battery_budget", "layered_demo"].index(scenario.get("scenario_family", "mixed_terrain")),
        )
        use_external_layers = col22.checkbox("Use external layers", value=bool(scenario.get("use_external_layers", False)))
        obstacle_ratio = col23.number_input("Obstacle ratio", min_value=0.0, max_value=0.8, value=float(terrain.get("obstacle_ratio", 0.08)))
        layer_paths = {
            "terrain": st.text_input("Terrain layer path", value=scenario.get("layer_paths", {}).get("terrain", "data/sample_layers/terrain.csv")),
            "obstacle": st.text_input("Obstacle layer path", value=scenario.get("layer_paths", {}).get("obstacle", "data/sample_layers/obstacles.csv")),
            "trail": st.text_input("Trail layer path", value=scenario.get("layer_paths", {}).get("trail", "data/sample_layers/trails.csv")),
            "elevation": st.text_input("Elevation layer path", value=scenario.get("layer_paths", {}).get("elevation", "data/sample_layers/elevation.csv")),
            "wind": st.text_input("Wind layer path", value=scenario.get("layer_paths", {}).get("wind", "data/sample_layers/wind.csv")),
        }

        st.markdown("**Belief and Planner Settings**")
        col24, col25, col26 = st.columns(3)
        belief_motion_strength = col24.number_input("Belief motion strength", min_value=0.0, max_value=1.0, value=float(belief.get("motion_strength", 0.18)))
        belief_positive_gain = col25.number_input("Belief positive gain", min_value=0.1, max_value=5.0, value=float(belief.get("positive_gain", 1.6)))
        confirmation_threshold = col26.number_input("Confirmation threshold", min_value=0.1, max_value=10.0, value=float(belief.get("candidate_confirmation_threshold", 1.2)))
        col27, col28 = st.columns(2)
        hierarchical_enabled = col27.checkbox("Hierarchical planning enabled", value=bool(hierarchical.get("enabled", True)))
        objective_count = col28.number_input("Objective count", min_value=1, max_value=50, value=int(hierarchical.get("objective_count", 6)))

        submitted = st.form_submit_button("Save Scenario")

    payload = {
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
            "battery_policy": {
                "return_threshold": float(return_threshold),
            },
            "terrain": {
                "obstacle_ratio": float(obstacle_ratio),
                "distribution": terrain.get(
                    "distribution",
                    {"plain": 0.42, "forest": 0.24, "hill": 0.16, "urban": 0.12, "water": 0.06},
                ),
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
    if submitted:
        return payload
    return {}


def render_scenarios_page() -> None:
    st.header("Scenarios")
    try:
        scenarios = load_json("/api/scenarios")["items"]
        st.dataframe(pd.DataFrame(scenarios))
        selected = st.selectbox("Open saved scenario", [""] + [item["scenario_id"] for item in scenarios])
        loaded_payload = {}
        if selected:
            loaded_payload = load_json(f"/api/scenarios/{selected}")["payload"]
            st.json(loaded_payload)
        payload = build_scenario_payload(loaded_payload)
        if payload:
            saved = post_json("/api/scenarios", payload)
            st.success(f"Saved scenario {saved['scenario_id']}")
            st.rerun()
    except ApiError as exc:
        st.error(f"Backend error: {exc}")


def render_mission_page() -> None:
    st.header("Mission Run View")
    try:
        scenarios = load_json("/api/scenarios")["items"]
        scenario_id = st.selectbox("Scenario to run", [item["scenario_id"] for item in scenarios])
        seed = st.number_input("Mission seed", min_value=0, max_value=999999, value=7)
        if st.button("Launch Mission"):
            created = post_json("/api/runs", {"scenario_id": scenario_id, "seed": int(seed)})
            st.success(f"Run created: {created['run_id']}")
            st.session_state["selected_run_id"] = created["run_id"]

        runs = load_json("/api/runs")["items"]
        if not runs:
            st.info("No runs yet. Launch a mission to begin.")
            return
        run_id = st.selectbox(
            "Open run",
            [item["run_id"] for item in runs],
            key="selected_run_id",
        )
        run = load_json(f"/api/runs/{run_id}")
        st.write(f"Status: `{run['status']}`")
        st.json(run["summary"])
        st.dataframe(pd.DataFrame([run["metrics"]]))

        latest_snapshot = run.get("latest_snapshot", {})
        if latest_snapshot:
            st.write(f"Latest step: {latest_snapshot.get('step')}")
            drone_ids = [drone["id"] for drone in latest_snapshot.get("drones", [])]
        else:
            drone_ids = []

        col1, col2, col3 = st.columns(3)
        if col1.button("Pause Mission"):
            post_json(f"/api/runs/{run_id}/interventions", {"action": "pause"})
            st.rerun()
        if col2.button("Resume Mission"):
            post_json(f"/api/runs/{run_id}/interventions", {"action": "resume"})
            st.rerun()
        if col3.button("Generate Report"):
            report = post_json(f"/api/runs/{run_id}/report", {})
            st.success(f"Report created at {report['report_path']}")

        with st.expander("Operator Controls", expanded=False):
            target_drone = st.selectbox("Drone", drone_ids or [0], key="intervention_drone")
            waypoint_x = st.number_input("Waypoint X", min_value=0, value=0, key="waypoint_x")
            waypoint_y = st.number_input("Waypoint Y", min_value=0, value=0, key="waypoint_y")
            new_strategy = st.selectbox(
                "Switch strategy",
                ["random_sweep", "sector_search", "probability_greedy", "auction_based", "information_gain"],
                key="switch_strategy",
            )
            zone_center_x = st.number_input("Zone center X", min_value=0, value=0, key="zone_x")
            zone_center_y = st.number_input("Zone center Y", min_value=0, value=0, key="zone_y")
            zone_radius = st.number_input("Zone radius", min_value=1.0, value=2.0, key="zone_radius")

            c1, c2, c3, c4, c5 = st.columns(5)
            if c1.button("Force RTB"):
                post_json(f"/api/runs/{run_id}/interventions", {"action": "force_return", "payload": {"drone_id": int(target_drone)}})
                st.rerun()
            if c2.button("Assign Waypoint"):
                post_json(
                    f"/api/runs/{run_id}/interventions",
                    {"action": "assign_waypoint", "payload": {"drone_id": int(target_drone), "position": [int(waypoint_x), int(waypoint_y)]}},
                )
                st.rerun()
            if c3.button("Priority Zone"):
                post_json(
                    f"/api/runs/{run_id}/interventions",
                    {"action": "set_priority_zone", "payload": {"center": [int(zone_center_x), int(zone_center_y)], "radius": float(zone_radius)}},
                )
                st.rerun()
            if c4.button("Exclusion Zone"):
                post_json(
                    f"/api/runs/{run_id}/interventions",
                    {"action": "set_exclusion_zone", "payload": {"center": [int(zone_center_x), int(zone_center_y)], "radius": float(zone_radius)}},
                )
                st.rerun()
            if c5.button("Switch"):
                post_json(f"/api/runs/{run_id}/interventions", {"action": "switch_strategy", "payload": {"strategy": new_strategy}})
                st.rerun()

        artifact_paths = run.get("artifact_paths", {})
        if artifact_paths.get("final_state") and Path(artifact_paths["final_state"]).exists():
            st.image(artifact_paths["final_state"], caption="Latest final-state artifact")
    except ApiError as exc:
        st.error(f"Backend error: {exc}")


def render_replay_page() -> None:
    st.header("Replay View")
    try:
        runs = load_json("/api/runs")["items"]
        if not runs:
            st.info("No mission runs available yet.")
            return
        run_id = st.selectbox("Run", [item["run_id"] for item in runs], key="replay_run")
        replay = load_json(f"/api/runs/{run_id}/replay")["replay"]
        events = load_json(f"/api/runs/{run_id}/events")["events"]
        if not replay:
            st.info("Replay data is not ready yet.")
            return
        step_index = st.slider("Replay step", min_value=0, max_value=len(replay) - 1, value=min(1, len(replay) - 1))
        snapshot = replay[step_index]
        fig, _ = SimulationRenderer.render_static(snapshot, show=False, close_figure=False)
        st.pyplot(fig)
        plt.close(fig)
        step_events = [event for event in events if event.get("step") == snapshot["step"]]
        st.subheader("Events at this step")
        st.dataframe(pd.DataFrame(step_events))
    except ApiError as exc:
        st.error(f"Backend error: {exc}")


def render_experiments_page() -> None:
    st.header("Experiment Browser")
    try:
        with st.expander("Launch Experiment Batch", expanded=False):
            strategies = st.multiselect(
                "Strategies",
                ["random_sweep", "sector_search", "probability_greedy", "auction_based", "information_gain"],
                default=["auction_based", "information_gain"],
            )
            scenario_families = st.multiselect(
                "Scenario families",
                ["open_terrain", "poor_comms", "layered_demo"],
                default=["open_terrain", "layered_demo"],
            )
            target_behaviors = st.multiselect(
                "Target behaviors",
                ["terrain_biased", "stationary_intervals"],
                default=["terrain_biased"],
            )
            if st.button("Launch Experiments"):
                created = post_json(
                    "/api/experiments",
                    {
                        "strategies": strategies,
                        "scenario_families": scenario_families,
                        "target_behaviors": target_behaviors,
                        "coordination_modes": ["centralized", "decentralized"],
                        "drone_counts": [4],
                        "battery_budgets": [120.0],
                        "sensor_modes": ["thermal_visual"],
                        "benchmark_num_seeds": 3,
                        "experiment_num_seeds": 1,
                    },
                )
                st.success(f"Experiment launched: {created['experiment_id']}")

        experiments = load_json("/api/experiments")["items"]
        if not experiments:
            st.info("No experiments available yet.")
            return
        experiment_id = st.selectbox("Experiment", [item["experiment_id"] for item in experiments], key="experiment_id")
        experiment = load_json(f"/api/experiments/{experiment_id}")
        st.write(f"Status: `{experiment['status']}`")
        summary = load_json(f"/api/experiments/{experiment_id}/summary")["summary"]
        if summary:
            dataframe = pd.DataFrame(summary)
            st.dataframe(dataframe)
            strategy_filter = st.multiselect("Filter strategies", sorted(dataframe["strategy"].unique()), default=sorted(dataframe["strategy"].unique()))
            filtered = dataframe[dataframe["strategy"].isin(strategy_filter)]
            st.dataframe(filtered)
        for image_path in experiment.get("artifact_paths", {}).get("plots", []):
            if Path(image_path).exists():
                st.image(image_path, caption=Path(image_path).name)
    except ApiError as exc:
        st.error(f"Backend error: {exc}")


def main() -> None:
    st.title("Swarm Mission Planner and Review")
    st.caption("Local operator console for scenario management, mission execution, replay, and experiments.")
    st.session_state.setdefault("api_base_url", DEFAULT_API_BASE_URL)
    st.sidebar.text_input("Backend URL", key="api_base_url")
    page = st.sidebar.radio("View", ["Scenarios", "Mission Run", "Replay", "Experiments"])
    if page == "Scenarios":
        render_scenarios_page()
    elif page == "Mission Run":
        render_mission_page()
    elif page == "Replay":
        render_replay_page()
    else:
        render_experiments_page()


if __name__ == "__main__":
    main()
