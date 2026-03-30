from __future__ import annotations

import pandas as pd
import streamlit as st

from mobility_os.ui.charts import make_alert_level_chart, make_line
from mobility_os.ui.maps import build_hotspot_signals, render_signals_map
from mobility_os.ui.components import render_summary_table


def render_signals_tab(df: pd.DataFrame, latest: dict, hotspots_df: pd.DataFrame, focus_name: str | None, window: int) -> None:
    st.markdown("## Signals & Alerts Map")
    if df.empty:
        st.info("No simulation data yet.")
        return
    signals_df = build_hotspot_signals(hotspots_df, df, latest, focus_name)
    if signals_df.empty:
        st.info("No signal layer available.")
        return
    left, right = st.columns([1.8, 1.0])
    with left:
        render_signals_map(signals_df, height=760)
    with right:
        top_alerts = signals_df.sort_values(["severity", "name"], ascending=[False, True]).head(6).copy()
        top_alerts["severity"] = top_alerts["severity"].round(3)
        render_summary_table([
            ("Scenario", latest.get("scenario", "—")),
            ("Active event", latest.get("active_event", "none") or "none"),
            ("Focused hotspot", focus_name or "—"),
            ("Primary route", latest.get("decision_route", "—")),
        ], "Operational context")
        st.plotly_chart(make_alert_level_chart(signals_df), use_container_width=True)
        st.dataframe(top_alerts[["name", "alert_level", "phase", "signal_type", "active_event", "severity"]], use_container_width=True, hide_index=True, height=260)
    live_df = df.tail(int(window))
    info_cols = st.columns(3)
    with info_cols[0]:
        st.plotly_chart(make_line(live_df, ["risk_score", "near_miss_index"], "Risk signal trend"), use_container_width=True)
    with info_cols[1]:
        st.plotly_chart(make_line(live_df, ["bus_bunching_index", "corridor_reliability_index"], "Transit signal trend"), use_container_width=True)
    with info_cols[2]:
        st.plotly_chart(make_line(live_df, ["curb_occupancy_rate", "illegal_curb_occupancy_rate", "gateway_delay_index"], "Curb / gateway trend"), use_container_width=True)
