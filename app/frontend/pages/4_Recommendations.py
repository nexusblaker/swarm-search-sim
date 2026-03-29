"""Recommendation page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.frontend.common import api_error_block, ensure_frontend_state, load_json, post_json


st.title("Recommendations")
ensure_frontend_state()
st.sidebar.text_input("Backend URL", key="api_base_url")

try:
    plans = load_json("/plans")["items"]
    if not plans:
        st.info("Create a mission plan before requesting recommendations.")
        st.stop()
    plan_id = st.selectbox("Mission plan", [item["id"] for item in plans], key="recommend-plan")
    if st.button("Generate Recommendation"):
        recommendation = post_json("/recommend", {"plan_id": plan_id, "num_seeds": 2})
        st.session_state["recommendation_result"] = recommendation

    if "recommendation_result" in st.session_state:
        recommendation = st.session_state["recommendation_result"]
        st.metric("Recommended strategy", recommendation["recommended_strategy"])
        st.metric("Recommended drone count", recommendation["recommended_drone_count"])
        st.metric("Recommended reserve threshold", recommendation["recommended_return_threshold"])
        st.write(recommendation["explanation"])
        st.json(recommendation["risk_summary"])
        st.subheader("Uncertainty Summary")
        st.json(recommendation.get("uncertainty_summary", {}))
        st.subheader("Candidate Plans")
        st.dataframe(pd.DataFrame(recommendation["candidate_plans"]), use_container_width=True)
except Exception as exc:  # pragma: no cover
    api_error_block(exc)
