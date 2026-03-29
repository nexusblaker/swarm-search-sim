"""Saved plan comparison workspace."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.frontend.common import api_error_block, comparison_table, ensure_frontend_state, load_json, post_json


st.title("Plan Comparison")
ensure_frontend_state()
st.sidebar.text_input("Backend URL", key="api_base_url")

try:
    plans = load_json("/plans")["items"]
    comparisons = load_json("/comparisons")["items"]
    comparison_table(comparisons)
    if not plans:
        st.info("Create a mission plan before saving comparison workspaces.")
        st.stop()
    plan_id = st.selectbox("Mission plan", [item["id"] for item in plans], key="compare-plan")
    strategies = st.multiselect(
        "Strategies",
        ["random_sweep", "sector_search", "probability_greedy", "auction_based", "information_gain"],
        default=["auction_based", "information_gain", "probability_greedy"],
    )
    drone_counts = st.multiselect("Drone counts", [2, 3, 4, 5, 6], default=[3, 5])
    coordination_modes = st.multiselect("Coordination modes", ["centralized", "decentralized"], default=["centralized", "decentralized"])
    thresholds = st.multiselect("Reserve thresholds", [20.0, 24.0, 28.0, 32.0, 36.0], default=[24.0, 28.0, 32.0])
    seeds = st.slider("Comparison seeds", min_value=1, max_value=4, value=2)

    if st.button("Save Comparison Workspace"):
        created = post_json(
            "/comparisons",
            {
                "plan_id": plan_id,
                "strategies": strategies,
                "drone_counts": drone_counts,
                "coordination_modes": coordination_modes,
                "return_thresholds": thresholds,
                "num_seeds": seeds,
            },
        )
        st.session_state["selected_comparison_id"] = created["id"]
        st.success(f"Saved comparison {created['id']}")
        st.rerun()

    if comparisons:
        selected_comparison = st.selectbox(
            "Open saved comparison",
            [item["id"] for item in comparisons],
            key="selected_comparison_id",
        )
        comparison = load_json(f"/comparisons/{selected_comparison}")
        st.subheader("Top Recommendation")
        st.json(comparison["recommendation_json"])
        st.subheader("Uncertainty and Sensitivity")
        st.json(
            {
                "uncertainty": comparison["uncertainty_json"],
                "sensitivity": comparison["sensitivity_json"],
            }
        )
        st.subheader("Ranked Candidate Plans")
        st.dataframe(pd.DataFrame(comparison["summary_json"]), use_container_width=True)
        candidate_options = [""] + [item["id"] for item in comparison.get("candidates", [])]
        candidate_id = st.selectbox("Launch candidate run", candidate_options)
        if st.button("Launch Run From Saved Comparison", disabled=not selected_comparison):
            payload = {"candidate_id": candidate_id or None, "seed": 7}
            created = post_json(f"/comparisons/{selected_comparison}/run", payload)
            st.session_state["selected_run_id"] = created["id"]
            st.success(f"Launched run {created['id']}")
except Exception as exc:  # pragma: no cover
    api_error_block(exc)
