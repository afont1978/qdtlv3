from __future__ import annotations

import pandas as pd
import streamlit as st

from mobility_os.ui.charts import make_line, make_route_mix_chart, make_subsystem_score_chart
from mobility_os.ui.components import render_chip_row
from mobility_os.ui.maps import render_city_map, render_hotspot_summary


def render_overview_tab(df: pd.DataFrame, latest: dict, spec, hotspots_df: pd.DataFrame, focus_name: str | None, window: int, layer_filter: list[str]) -> None:
    if df.empty:
        st.info("No simulation data yet.")
        return
    live_df = df.tail(int(window)).copy()
    left, right = st.columns([1.7, 1.0])
    with left:
        render_city_map(hotspots_df, latest, layer_filter=layer_filter, focused_name=focus_name, height=560)
    with right:
        render_hotspot_summary(focus_name, hotspots_df, latest.get("scenario_note"), title="Focused hotspot")
        render_chip_row([
            (f"Scenario · {spec.title}", "neutral"),
            (f"Complexity · {spec.complexity}", "warn"),
            (f"Event · {latest.get('active_event') or 'none'}", "alert" if latest.get("active_event") else "dim"),
        ])
        st.plotly_chart(make_route_mix_chart(df.tail(max(int(window), 12))), use_container_width=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.plotly_chart(make_line(live_df, ["network_speed_index", "corridor_reliability_index"], "Network dynamics"), use_container_width=True)
    with c2:
        st.plotly_chart(make_line(live_df, ["bus_bunching_index", "bus_commercial_speed_kmh"], "Transit dynamics"), use_container_width=True)
    with c3:
        st.plotly_chart(make_line(live_df, ["risk_score", "gateway_delay_index", "curb_occupancy_rate"], "Pressure dynamics"), use_container_width=True)
    st.plotly_chart(make_subsystem_score_chart(latest), use_container_width=True)
