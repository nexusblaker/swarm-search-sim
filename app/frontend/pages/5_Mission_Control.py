"""Mission control page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.frontend.common import api_error_block, artifact_image, ensure_frontend_state, load_json, post_json, render_snapshot


st.title("Mission Control")
ensure_frontend_state()
st.sidebar.text_input("Backend URL", key="api_base_url")

try:
    scenarios = load_json("/scenarios")["items"]
    scenario_id = st.selectbox("Scenario to run", [item["id"] for item in scenarios], key="mission-scenario")
    seed = st.number_input("Mission seed", min_value=0, max_value=999999, value=7)
    if st.button("Launch Mission"):
        created = post_json("/runs", {"scenario_id": scenario_id, "seed": int(seed)})
        st.session_state["selected_run_id"] = created["id"]
        st.success(f"Run created: {created['id']}")

    runs = load_json("/runs")["items"]
    if not runs:
        st.info("No runs yet.")
        st.stop()
    run_id = st.selectbox("Open run", [item["id"] for item in runs], key="selected_run_id")
    run = load_json(f"/runs/{run_id}")
    st.write(f"Status: `{run['status']}`")
    st.dataframe(pd.DataFrame([run["summary_json"]]), use_container_width=True)
    latest_snapshot = run.get("latest_snapshot_json") or {}
    if latest_snapshot:
        render_snapshot(latest_snapshot)
        drone_ids = [drone["id"] for drone in latest_snapshot.get("drones", [])]
    else:
        drone_ids = []

    col1, col2, col3 = st.columns(3)
    if col1.button("Pause"):
        post_json(f"/runs/{run_id}/interventions", {"action": "pause"})
        st.rerun()
    if col2.button("Resume"):
        post_json(f"/runs/{run_id}/interventions", {"action": "resume"})
        st.rerun()
    if col3.button("Generate Report"):
        post_json(f"/reports/{run_id}", {})
        st.success("Report generated")

    with st.expander("Operator Controls"):
        target_drone = st.selectbox("Drone", drone_ids or [0], key="mission-drone")
        waypoint_x = st.number_input("Waypoint X", min_value=0, value=0, key="mission-waypoint-x")
        waypoint_y = st.number_input("Waypoint Y", min_value=0, value=0, key="mission-waypoint-y")
        new_strategy = st.selectbox("Strategy", ["random_sweep", "sector_search", "probability_greedy", "auction_based", "information_gain"], key="mission-strategy")
        zone_center_x = st.number_input("Zone center X", min_value=0, value=0, key="mission-zone-x")
        zone_center_y = st.number_input("Zone center Y", min_value=0, value=0, key="mission-zone-y")
        zone_radius = st.number_input("Zone radius", min_value=1.0, value=2.0, key="mission-zone-radius")
        a1, a2, a3, a4, a5 = st.columns(5)
        if a1.button("Force RTB"):
            post_json(f"/runs/{run_id}/interventions", {"action": "force_return", "payload": {"drone_id": int(target_drone)}})
            st.rerun()
        if a2.button("Assign Waypoint"):
            post_json(f"/runs/{run_id}/interventions", {"action": "assign_waypoint", "payload": {"drone_id": int(target_drone), "position": [int(waypoint_x), int(waypoint_y)]}})
            st.rerun()
        if a3.button("Priority Zone"):
            post_json(f"/runs/{run_id}/interventions", {"action": "set_priority_zone", "payload": {"center": [int(zone_center_x), int(zone_center_y)], "radius": float(zone_radius)}})
            st.rerun()
        if a4.button("Exclusion Zone"):
            post_json(f"/runs/{run_id}/interventions", {"action": "set_exclusion_zone", "payload": {"center": [int(zone_center_x), int(zone_center_y)], "radius": float(zone_radius)}})
            st.rerun()
        if a5.button("Switch Strategy"):
            post_json(f"/runs/{run_id}/interventions", {"action": "switch_strategy", "payload": {"strategy": new_strategy}})
            st.rerun()

    artifact_image(run.get("artifact_paths", {}).get("final_state"), "Final state")
except Exception as exc:  # pragma: no cover
    api_error_block(exc)
