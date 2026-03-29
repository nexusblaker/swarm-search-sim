"""After-action review workspace."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.frontend.common import api_error_block, ensure_frontend_state, load_json, post_json


st.title("After-Action Review")
ensure_frontend_state()
st.sidebar.text_input("Backend URL", key="api_base_url")

try:
    runs = load_json("/runs")["items"]
    reviews = load_json("/reviews")["items"]

    completed_runs = [item for item in runs if item["status"] == "completed"]
    if completed_runs:
        source_run = st.selectbox("Create review from completed run", [item["id"] for item in completed_runs])
        if st.button("Generate After-Action Review"):
            created = post_json(f"/reviews/from-run/{source_run}", {})
            st.session_state["selected_review_id"] = created["id"]
            st.success(f"Created review {created['id']}")
            st.rerun()

    if not reviews:
        st.info("No after-action reviews available yet.")
        st.stop()

    review_id = st.selectbox("Open review", [item["id"] for item in reviews], key="selected_review_id")
    review = load_json(f"/reviews/{review_id}")
    st.subheader(review["name"])
    st.caption(
        f"Run: {review['run_id']} | Plan: {review.get('plan_id') or 'n/a'} | Comparison: {review.get('comparison_id') or 'n/a'}"
    )
    st.subheader("Outcome Summary")
    st.json(review["summary_json"]["actual_outcome"])
    st.subheader("Deviation From Recommendation")
    st.json(review["summary_json"]["deviation_from_recommendation"])
    st.subheader("Asset Utilization and Risk")
    st.json(
        {
            "asset_utilization": review["summary_json"]["asset_utilization"],
            "battery_comms_risk_summary": review["summary_json"]["battery_comms_risk_summary"],
            "alternate_plan_summary": review["summary_json"]["alternate_plan_summary"],
        }
    )
    st.subheader("Timeline")
    st.dataframe(pd.DataFrame(review["timeline_json"]["key_events"]), use_container_width=True)
    if review.get("report"):
        st.subheader("Linked Report")
        st.json(review["report"])
except Exception as exc:  # pragma: no cover
    api_error_block(exc)
