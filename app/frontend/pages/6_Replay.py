"""Replay page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.frontend.common import api_error_block, ensure_frontend_state, load_json, render_snapshot


st.title("Replay")
ensure_frontend_state()
st.sidebar.text_input("Backend URL", key="api_base_url")

try:
    runs = load_json("/runs")["items"]
    if not runs:
        st.info("No runs available.")
        st.stop()
    run_id = st.selectbox("Run", [item["id"] for item in runs], key="replay-run")
    replay = load_json(f"/runs/{run_id}/replay")["replay"]
    events = load_json(f"/runs/{run_id}/events")["events"]
    step_index = st.slider("Replay step", 0, len(replay) - 1, value=min(1, len(replay) - 1))
    snapshot = replay[step_index]
    render_snapshot(snapshot)
    step_events = [event for event in events if event.get("step") == snapshot["step"]]
    st.dataframe(pd.DataFrame(step_events), use_container_width=True)
except Exception as exc:  # pragma: no cover
    api_error_block(exc)
