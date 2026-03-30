from __future__ import annotations

import pandas as pd
import streamlit as st

from mobility_os.ui.charts import make_line
from mobility_os.ui.components import render_chip_row, render_summary_table
from mobility_os.ui.maps import render_hotspot_summary


def _twin_snapshot_fields(snapshot: dict) -> list[tuple[str, object]]:
    rows = []
    for k, v in snapshot.items():
        if k in {"metadata", "alarms", "name", "ts", "twin_id", "asset_type", "enabled"}:
            continue
        if isinstance(v, (int, float, bool)):
            rows.append((k, v))
    return rows[:12]



def render_twins_tab(df: pd.DataFrame, latest: dict, hotspots_df: pd.DataFrame, snapshots: dict[str, dict], window: int) -> None:
    st.markdown("## Mobility Twins")
    if df.empty:
        st.info("No simulation data yet.")
        return

    twin_options = ["intersection", "road_corridor", "bus_corridor", "curb_zone", "risk_hotspot"]
    default_twin = st.session_state.get("twin_sel", "intersection")
    st.session_state["twin_sel"] = st.selectbox("Select twin", twin_options, index=twin_options.index(default_twin) if default_twin in twin_options else 0)
    twin_sel = st.session_state["twin_sel"]
    snap = snapshots.get(twin_sel, {})
    md = snap.get("metadata", {}) if isinstance(snap, dict) else {}
    live_df = df.tail(int(window)).copy()

    metric_map = {
        "intersection": [["corridor_delay_s", "risk_score"], ["near_miss_index", "pedestrian_exposure"]],
        "road_corridor": [["network_speed_index", "corridor_reliability_index"], ["corridor_delay_s", "gateway_delay_index"]],
        "bus_corridor": [["bus_bunching_index", "bus_commercial_speed_kmh"], ["bus_priority_requests", "corridor_reliability_index"]],
        "curb_zone": [["curb_occupancy_rate", "illegal_curb_occupancy_rate"], ["delivery_queue", "risk_score"]],
        "risk_hotspot": [["risk_score", "near_miss_index"], ["pedestrian_exposure", "bike_conflict_index"]],
    }

    grid = st.columns([1.45, 1.45, 1.0])
    with grid[0]:
        st.plotly_chart(make_line(live_df, metric_map[twin_sel][0], "Twin trend A"), use_container_width=True)
    with grid[1]:
        st.plotly_chart(make_line(live_df, metric_map[twin_sel][1], "Twin trend B"), use_container_width=True)
    with grid[2]:
        render_hotspot_summary(md.get("hotspot_name") or latest.get("primary_hotspot_name"), hotspots_df, md.get("scenario_note") or latest.get("scenario_note"), title="Twin hotspot")
        render_chip_row([
            (f"Twin · {twin_sel}", "neutral"),
            (f"Scenario hotspot · {md.get('scenario_hotspot_name', '—')}", "dim"),
        ])
        render_summary_table(_twin_snapshot_fields(snap)[:8], "Key metrics")
