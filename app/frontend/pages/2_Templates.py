"""Operational scenario library page."""

from __future__ import annotations

import streamlit as st

from app.frontend.common import api_error_block, ensure_frontend_state, load_json, post_json


st.title("Scenario Library")
ensure_frontend_state()
st.sidebar.text_input("Backend URL", key="api_base_url")

try:
    templates = load_json("/library/templates")["items"]
    family_filter = st.selectbox(
        "Filter by family",
        ["all"] + sorted({item["family"] for item in templates}),
    )
    filtered = [
        item for item in templates
        if family_filter == "all" or item["family"] == family_filter
    ]
    st.dataframe(filtered, use_container_width=True)
    selected = st.selectbox("Open library entry", [item["id"] for item in filtered])
    template = load_json(f"/library/templates/{selected}")
    st.subheader(template["name"])
    st.caption(template["doctrine_type"])
    st.write(template["description"])
    st.write(template["intended_use"])
    st.json(
        {
            "recommended_strategies": template["recommended_strategies_json"],
            "risks": template["risks_json"],
            "assumptions": template["assumptions_json"],
            "tags": template["tags_json"],
        }
    )
    if st.button("Save Library Entry as Scenario"):
        saved = post_json("/scenarios", template["config_json"])
        st.success(f"Created scenario {saved['id']}")
except Exception as exc:  # pragma: no cover
    api_error_block(exc)
