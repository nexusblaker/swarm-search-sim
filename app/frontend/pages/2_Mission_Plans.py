"""Mission plan workspace page."""

from __future__ import annotations

import streamlit as st

from app.frontend.common import (
    api_error_block,
    build_plan_request,
    ensure_frontend_state,
    load_json,
    plan_table,
    post_json,
    put_json,
)


st.title("Mission Plans")
ensure_frontend_state()
st.sidebar.text_input("Backend URL", key="api_base_url")

try:
    plans = load_json("/plans")["items"]
    scenarios = load_json("/scenarios")["items"]
    templates = load_json("/library/templates")["items"]
    plan_table(plans)

    selected = st.selectbox("Open mission plan", [""] + [item["id"] for item in plans], key="selected_plan_id")
    loaded = load_json(f"/plans/{selected}") if selected else {}

    st.subheader("Plan Workspace")
    payload = build_plan_request(default=loaded, scenarios=scenarios, templates=templates, key_prefix="mission-plan")
    col1, col2 = st.columns(2)
    if col1.button("Save Mission Plan"):
        if selected:
            saved = put_json(f"/plans/{selected}", payload)
        else:
            saved = post_json("/plans", payload)
        st.session_state["selected_plan_id"] = saved["id"]
        st.success(f"Saved mission plan {saved['id']}")
        st.rerun()
    if col2.button("Launch Run From Plan", disabled=not selected):
        created = post_json("/runs", {"plan_id": selected, "seed": 7})
        st.session_state["selected_run_id"] = created["id"]
        st.success(f"Launched run {created['id']}")

    if loaded:
        st.subheader("Recommendation Snapshot")
        st.json(loaded.get("recommendation_json", {}))
        st.subheader("Plan Notes and Zones")
        st.write(loaded.get("operator_notes") or "No operator notes recorded.")
        st.json(
            {
                "priority_zones": loaded.get("priority_zones_json", []),
                "exclusion_zones": loaded.get("exclusion_zones_json", []),
                "candidate_alternatives": loaded.get("candidate_alternatives_json", []),
            }
        )
except Exception as exc:  # pragma: no cover
    api_error_block(exc)
