from __future__ import annotations

import pandas as pd
import streamlit as st

from mobility_os.ui.charts import make_subsystem_score_chart
from mobility_os.ui.maps import render_city_map, render_hotspot_summary


def render_map_layers_tab(df: pd.DataFrame, latest: dict, hotspots_df: pd.DataFrame, focus_name: str | None, layer_filter: list[str]) -> None:
    st.markdown("## Map & Layers")
    if df.empty:
        st.info("No simulation data yet.")
        return
    top = st.columns([1.7, 1.0])
    with top[0]:
        render_city_map(hotspots_df, latest, layer_filter=layer_filter, focused_name=focus_name, height=700)
    with top[1]:
        render_hotspot_summary(focus_name, hotspots_df, latest.get("scenario_note"), title="Selected hotspot")
        if not hotspots_df.empty:
            layer_counts = hotspots_df[hotspots_df["layer_group"].isin(layer_filter)]["layer_group"].value_counts().reset_index()
            layer_counts.columns = ["Layer", "Count"]
            st.dataframe(layer_counts, use_container_width=True, hide_index=True)
            st.plotly_chart(make_subsystem_score_chart(latest), use_container_width=True)
    catalogue = hotspots_df[["name", "layer_group", "category", "streets", "lat", "lon"]].copy() if not hotspots_df.empty else hotspots_df
    st.dataframe(catalogue, use_container_width=True, height=320, hide_index=True)
