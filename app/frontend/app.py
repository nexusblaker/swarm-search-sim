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
        plans = load_json("/plans")["items"]
        comparisons = load_json("/comparisons")["items"]
        runs = load_json("/runs")["items"]
        experiments = load_json("/experiments")["items"]
        reviews = load_json("/reviews")["items"]
        reports = load_json("/reports")["items"]
    except Exception as exc:  # pragma: no cover - UI runtime
        st.error(f"Backend unavailable: {exc}")
        st.stop()

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Scenarios", len(scenarios))
    col2.metric("Mission Plans", len(plans))
    col3.metric("Comparisons", len(comparisons))
    col4.metric("Runs", len(runs))
    col5.metric("Reviews", len(reviews))
    col6.metric("Reports", len(reports))

    st.markdown("**Backend Health**")
    st.json(health)
    st.info(
        "Use the pages in the sidebar to build mission plans, compare candidate plans, launch monitored runs, review replay and after-action analysis, browse operational templates, and open indexed reports."
    )


if __name__ == "__main__":
    main()
