from __future__ import annotations

import pandas as pd
import streamlit as st

from mobility_os.ui.charts import make_story_disturbance_chart, make_story_event_track, make_subsystem_score_chart
from mobility_os.ui.components import render_chip_row, render_summary_table
from mobility_os.ui.maps import render_hotspot_summary


def render_storyboard_tab(df: pd.DataFrame, latest: dict, spec, hotspots_df: pd.DataFrame, focus_name: str | None) -> None:
    st.markdown("## Scenario Storyboard")
    if df.empty:
        st.info("No simulation data yet.")
        return

    top = st.columns([1.1, 0.9])
    with top[0]:
        render_summary_table([
            ("Scenario", spec.title),
            ("Mode", spec.mode),
            ("Complexity", spec.complexity),
            ("Active event", latest.get("active_event", "none") or "none"),
            ("Primary hotspot", latest.get("primary_hotspot_name", "—")),
            ("Focused hotspot", focus_name or "—"),
            ("Decision route", latest.get("decision_route", "—")),
        ], "Scenario profile")
        render_chip_row([
            (f"Subproblems · {len(spec.expected_subproblems)}", "warn"),
            (f"Interventions · {len(spec.recommended_interventions)}", "alert"),
            (f"KPIs · {len(spec.kpis)}", "neutral"),
        ])
        st.write(spec.note or "No scenario note available.")
    with top[1]:
        render_hotspot_summary(focus_name or latest.get("primary_hotspot_name"), hotspots_df, latest.get("scenario_note"), title="Scenario anchor")

    charts = st.columns(3)
    with charts[0]:
        st.plotly_chart(make_story_event_track(spec, latest.get("active_event"), int(latest.get("step_id", 0) or 0)), use_container_width=True)
    with charts[1]:
        st.plotly_chart(make_story_disturbance_chart(spec), use_container_width=True)
    with charts[2]:
        st.plotly_chart(make_subsystem_score_chart(latest), use_container_width=True)

    bottom = st.columns(3)
    with bottom[0]:
        st.subheader("Primary hotspots")
        for item in spec.primary_hotspots or []:
            st.caption(item)
    with bottom[1]:
        st.subheader("Expected subproblems")
        for item in spec.expected_subproblems or []:
            st.caption(str(item).replace("_", " ").title())
    with bottom[2]:
        st.subheader("Recommended interventions")
        for item in spec.recommended_interventions or []:
            st.caption(str(item).replace("_", " ").title())

    if spec.kpis:
        render_summary_table([(k, latest.get(k, "—")) for k in spec.kpis[:8]], "Scenario KPI watchlist")
