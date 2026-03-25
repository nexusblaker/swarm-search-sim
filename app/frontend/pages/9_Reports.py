"""Reports page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.frontend.common import api_error_block, ensure_frontend_state, load_json


st.title("Reports")
ensure_frontend_state()
st.sidebar.text_input("Backend URL", key="api_base_url")

try:
    reports = load_json("/reports")["items"]
    if not reports:
        st.info("No reports indexed yet.")
        st.stop()
    st.dataframe(pd.DataFrame(reports), use_container_width=True)
    report_id = st.selectbox("Report", [item["id"] for item in reports], key="report-id")
    report = load_json(f"/reports/{report_id}")
    st.json(report)
    st.code(report["file_path"])
except Exception as exc:  # pragma: no cover
    api_error_block(exc)
