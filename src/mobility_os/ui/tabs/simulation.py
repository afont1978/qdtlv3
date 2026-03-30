from __future__ import annotations

import pandas as pd
import streamlit as st

from mobility_os.ui.charts import make_delta_bar, make_scatter_compare
from mobility_os.ui.components import render_summary_table
from mobility_os.ui.maps import render_hotspot_summary
from mobility_os.ui.simulation import metric_delta_rows, project_what_if


def render_simulation_tab(df: pd.DataFrame, latest: dict, hotspots_df: pd.DataFrame, focus_name: str | None) -> None:
    st.markdown("## What-if & Simulation")
    if df.empty:
        st.info("Run at least one step before launching a contextual what-if analysis.")
        return

    left, right = st.columns([0.95, 1.25])
    with left:
        render_hotspot_summary(focus_name, hotspots_df, latest.get("scenario_note"), title="Simulation focus")
        with st.form("what_if_form"):
            shock = st.selectbox(
                "Stress or context change",
                ["None", "Rain event", "Incident on corridor", "Delivery wave", "Gateway surge", "Event release", "School peak"],
                index=0,
            )
            bus_priority = st.slider("Increase bus priority", 0, 2, 1)
            enforcement = st.slider("Increase curbside enforcement", 0, 2, 0)
            ped_protection = st.checkbox("Activate pedestrian protection", value=False)
            diversion = st.checkbox("Activate diversion / re-routing", value=False)
            simulate = st.form_submit_button("Run what-if on focused hotspot", use_container_width=True)

    ss = st.session_state
    if "what_if_controls" not in ss:
        ss["what_if_controls"] = {
            "shock": "None",
            "bus_priority": 1,
            "enforcement": 0,
            "ped_protection": False,
            "diversion": False,
        }
    if simulate:
        ss["what_if_controls"] = {
            "shock": shock,
            "bus_priority": bus_priority,
            "enforcement": enforcement,
            "ped_protection": ped_protection,
            "diversion": diversion,
        }

    projected = project_what_if(latest, focus_name, ss["what_if_controls"])
    with right:
        delta_df = metric_delta_rows(
            latest,
            projected,
            [
                "network_speed_index", "corridor_reliability_index", "corridor_delay_s",
                "bus_bunching_index", "bus_commercial_speed_kmh",
                "curb_occupancy_rate", "illegal_curb_occupancy_rate", "delivery_queue",
                "risk_score", "near_miss_index", "pedestrian_exposure",
                "gateway_delay_index", "step_operational_score",
            ],
        )
        top = st.columns(3)
        with top[0]:
            st.metric("Projected route", projected.get("what_if_route", "CLASSICAL"))
        with top[1]:
            delta_score = projected.get("step_operational_score", latest.get("step_operational_score", 0.0)) - latest.get("step_operational_score", 0.0)
            st.metric("Δ operational score", f"{delta_score:+.3f}")
        with top[2]:
            st.metric("Subproblem", projected.get("what_if_subproblem", "—"))

        g1, g2 = st.columns(2)
        with g1:
            st.plotly_chart(make_scatter_compare(latest, projected, ["step_operational_score", "network_speed_index", "risk_score", "bus_bunching_index"], "Scenario comparison"), use_container_width=True)
        with g2:
            st.plotly_chart(make_delta_bar(delta_df), use_container_width=True)

        rec_cols = st.columns(2)
        with rec_cols[0]:
            render_summary_table([
                ("Action", projected.get("recommended_action", "—")),
                ("Priority", projected.get("recommended_priority", "—")),
                ("Responsible layer", projected.get("recommended_owner", "—")),
            ], "Action package")
        with rec_cols[1]:
            render_summary_table([
                ("Projected route", projected.get("what_if_route", "Classical")),
                ("Subproblem", projected.get("what_if_subproblem", "—")),
                ("Expected impact", projected.get("recommended_expected_impact", "—")),
            ], "Operational expectation")

        st.dataframe(delta_df, use_container_width=True, hide_index=True, height=380)
