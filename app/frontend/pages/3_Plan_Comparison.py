"""Pre-mission plan comparison page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.frontend.common import api_error_block, ensure_frontend_state, load_json, post_json


st.title("Plan Comparison")
ensure_frontend_state()
st.sidebar.text_input("Backend URL", key="api_base_url")

try:
    scenarios = load_json("/scenarios")["items"]
    scenario_id = st.selectbox("Scenario", [item["id"] for item in scenarios], key="compare-scenario")
    strategies = st.multiselect(
        "Strategies",
        ["random_sweep", "sector_search", "probability_greedy", "auction_based", "information_gain"],
        default=["auction_based", "information_gain", "probability_greedy"],
    )
    drone_counts = st.multiselect("Drone counts", [2, 3, 4, 5, 6], default=[3, 5])
    coordination_modes = st.multiselect("Coordination modes", ["centralized", "decentralized"], default=["centralized", "decentralized"])
    thresholds = st.multiselect("Reserve thresholds", [20.0, 24.0, 28.0, 32.0, 36.0], default=[24.0, 28.0, 32.0])
    seeds = st.slider("Comparison seeds", min_value=1, max_value=4, value=2)

    if st.button("Compare Plans"):
        result = post_json(
            "/compare-plans",
            {
                "scenario_id": scenario_id,
                "strategies": strategies,
                "drone_counts": drone_counts,
                "coordination_modes": coordination_modes,
                "return_thresholds": thresholds,
                "num_seeds": seeds,
            },
        )
        st.session_state["comparison_result"] = result

    if "comparison_result" in st.session_state:
        comparison = st.session_state["comparison_result"]
        st.subheader("Top Recommendation")
        st.json(comparison["top_recommendation"])
        st.subheader("Ranked Plans")
        st.dataframe(pd.DataFrame(comparison["ranked_plans"]), use_container_width=True)
except Exception as exc:  # pragma: no cover
    api_error_block(exc)
