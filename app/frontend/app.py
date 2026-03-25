"""Streamlit home page for the mission decision-support product."""

from __future__ import annotations

import streamlit as st

from app.frontend.common import ensure_frontend_state, load_json


st.set_page_config(
    page_title="Swarm Mission Decision Support",
    page_icon="S",
    layout="wide",
)


def main() -> None:
    ensure_frontend_state()
    st.title("Swarm Mission Decision Support")
    st.caption("Local decision-support console for scenario planning, mission execution, replay, experiments, and reports.")
    st.sidebar.text_input("Backend URL", key="api_base_url")

    try:
        health = load_json("/health")
        scenarios = load_json("/scenarios")["items"]
        runs = load_json("/runs")["items"]
        experiments = load_json("/experiments")["items"]
        reports = load_json("/reports")["items"]
    except Exception as exc:  # pragma: no cover - UI runtime
        st.error(f"Backend unavailable: {exc}")
        st.stop()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Scenarios", len(scenarios))
    col2.metric("Runs", len(runs))
    col3.metric("Experiments", len(experiments))
    col4.metric("Reports", len(reports))

    st.markdown("**Backend Health**")
    st.json(health)
    st.info(
        "Use the Streamlit pages in the sidebar to browse templates, compare plans, launch missions and experiments, review replay, and open indexed reports."
    )


if __name__ == "__main__":
    main()
