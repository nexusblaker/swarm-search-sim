"""Experiment history page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.frontend.common import api_error_block, artifact_image, ensure_frontend_state, load_json, post_json


st.title("Experiments")
ensure_frontend_state()
st.sidebar.text_input("Backend URL", key="api_base_url")

try:
    with st.expander("Launch Experiment Batch", expanded=False):
        strategies = st.multiselect("Strategies", ["random_sweep", "sector_search", "probability_greedy", "auction_based", "information_gain"], default=["auction_based", "information_gain"])
        scenario_families = st.multiselect("Scenario families", ["open_terrain", "poor_comms", "layered_demo"], default=["open_terrain", "layered_demo"])
        target_behaviors = st.multiselect("Target behaviors", ["terrain_biased", "stationary_intervals"], default=["terrain_biased"])
        if st.button("Launch Experiment Batch"):
            created = post_json("/experiments", {"strategies": strategies, "scenario_families": scenario_families, "target_behaviors": target_behaviors, "coordination_modes": ["centralized", "decentralized"], "drone_counts": [4], "battery_budgets": [120.0], "sensor_modes": ["thermal_visual"], "benchmark_num_seeds": 3, "experiment_num_seeds": 1})
            st.session_state["selected_experiment_id"] = created["id"]
            st.success(f"Experiment created: {created['id']}")

    experiments = load_json("/experiments")["items"]
    if not experiments:
        st.info("No experiments yet.")
        st.stop()
    experiment_id = st.selectbox("Experiment", [item["id"] for item in experiments], key="selected_experiment_id")
    experiment = load_json(f"/experiments/{experiment_id}")
    st.write(f"Status: `{experiment['status']}`")
    summary = load_json(f"/experiments/{experiment_id}/summary")["summary"]
    if summary:
        st.dataframe(pd.DataFrame(summary), use_container_width=True)
    for artifact_type, path in experiment.get("artifact_paths", {}).items():
        if str(path).lower().endswith(".png"):
            artifact_image(path, artifact_type)
except Exception as exc:  # pragma: no cover
    api_error_block(exc)
