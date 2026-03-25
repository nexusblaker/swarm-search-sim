"""Scenario management page."""

from __future__ import annotations

import streamlit as st

from app.frontend.common import api_error_block, build_scenario_payload, ensure_frontend_state, load_json, post_json, scenario_table


st.title("Scenarios")
ensure_frontend_state()
st.sidebar.text_input("Backend URL", key="api_base_url")

try:
    scenarios = load_json("/scenarios")["items"]
    scenario_table(scenarios)
    selected = st.selectbox("Load scenario", [""] + [item["id"] for item in scenarios], index=0)
    loaded = load_json(f"/scenarios/{selected}")["config_json"] if selected else {}
    payload = build_scenario_payload(loaded, key_prefix="scenario-page")
    if payload:
        saved = post_json("/scenarios", payload)
        st.success(f"Saved scenario {saved['id']}")
        st.rerun()
except Exception as exc:  # pragma: no cover - Streamlit runtime
    api_error_block(exc)
