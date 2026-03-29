"""Run history page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.frontend.common import api_error_block, ensure_frontend_state, load_json


st.title("Run History")
ensure_frontend_state()
st.sidebar.text_input("Backend URL", key="api_base_url")

try:
    runs = load_json("/runs")["items"]
    jobs = {job["id"]: job for job in load_json("/jobs")["items"]}
    status_filter = st.selectbox("Filter by status", ["all"] + sorted({item["status"] for item in runs}))
    filtered_runs = [item for item in runs if status_filter == "all" or item["status"] == status_filter]
    dataframe = pd.DataFrame(
        [
            {
                "run_id": item["id"],
                "status": item["status"],
                "plan_id": item.get("plan_id"),
                "comparison_id": item.get("comparison_id"),
                "strategy": item["summary_json"].get("strategy"),
                "family": item["summary_json"].get("scenario_family"),
                "job_status": jobs.get(item.get("job_id"), {}).get("status"),
                "job_progress": jobs.get(item.get("job_id"), {}).get("progress"),
            }
            for item in filtered_runs
        ]
    )
    st.dataframe(dataframe, use_container_width=True)
except Exception as exc:  # pragma: no cover
    api_error_block(exc)
