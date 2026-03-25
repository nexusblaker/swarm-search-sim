"""Template browsing page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.frontend.common import api_error_block, ensure_frontend_state, load_json, post_json


st.title("Templates")
ensure_frontend_state()
st.sidebar.text_input("Backend URL", key="api_base_url")

try:
    templates = load_json("/templates")["items"]
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "family": item["family"],
                    "description": item["description"],
                }
                for item in templates
            ]
        ),
        use_container_width=True,
    )
    selected = st.selectbox("Open template", [item["id"] for item in templates])
    template = load_json(f"/templates/{selected}")
    st.json(template["config_json"])
    if st.button("Save Template as Scenario"):
        saved = post_json("/scenarios", template["config_json"])
        st.success(f"Created scenario {saved['id']}")
except Exception as exc:  # pragma: no cover
    api_error_block(exc)
