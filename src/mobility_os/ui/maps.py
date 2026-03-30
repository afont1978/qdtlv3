from __future__ import annotations

from typing import Any

import pandas as pd
import pydeck as pdk
import streamlit as st

LAYER_COLORS = {
    "Intermodal / public transport": [55, 126, 184, 170],
    "Urban core / tourism": [77, 175, 74, 170],
    "Logistics / curb / port": [255, 127, 0, 170],
    "Airport / gateway": [152, 78, 163, 170],
}


def layer_group(category: str) -> str:
    cat = str(category).lower()
    if "aeropuerto" in cat or "gateway" in cat:
        return "Airport / gateway"
    if "port" in cat or "logístic" in cat or "logistic" in cat or "mercanc" in cat or "curb" in cat or "cruceros" in cat:
        return "Logistics / curb / port"
    if "intermodal" in cat or "bus" in cat or "metro" in cat or "tranv" in cat or "intercambiador" in cat:
        return "Intermodal / public transport"
    return "Urban core / tourism"


def hotspots_dataframe(hotspots: dict[str, Any]) -> pd.DataFrame:
    if not hotspots:
        return pd.DataFrame(columns=["name", "lat", "lon", "category", "streets", "why", "layer_group"])
    df = pd.DataFrame([h.to_dict() for h in hotspots.values()])
    df["layer_group"] = df["category"].apply(layer_group)
    return df


def selected_hotspot_name(latest: dict[str, Any], focus_mode: str) -> str | None:
    if focus_mode == "Auto (scenario hotspot)":
        return latest.get("primary_hotspot_name") if latest else None
    return focus_mode


def build_map_data(hotspots_df: pd.DataFrame, latest: dict[str, Any], layer_filter: list[str], focused_name: str | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    if hotspots_df.empty:
        return pd.DataFrame(), pd.DataFrame()
    base = hotspots_df[hotspots_df["layer_group"].isin(layer_filter)].copy()
    if base.empty:
        return pd.DataFrame(), pd.DataFrame()
    base["color"] = base["layer_group"].map(LAYER_COLORS)
    base["radius"] = 140
    focus_name = focused_name or (latest.get("primary_hotspot_name") if latest else None)
    current = base[base["name"] == focus_name].copy() if focus_name else pd.DataFrame(columns=base.columns)
    if not current.empty:
        current["color"] = [[230, 60, 60, 220]] * len(current)
        current["radius"] = 320
    return base, current


def render_city_map(hotspots_df: pd.DataFrame, latest: dict[str, Any], layer_filter: list[str], focused_name: str | None, height: int = 520) -> None:
    base, current = build_map_data(hotspots_df, latest, layer_filter, focused_name)
    if base.empty:
        st.info("No hotspot data available for the selected layers.")
        return
    center_lat, center_lon, zoom = 41.3851, 2.1734, 11.8
    if not current.empty:
        row = current.iloc[0]
        center_lat, center_lon, zoom = float(row["lat"]), float(row["lon"]), 12.7
    layers = [pdk.Layer("ScatterplotLayer", data=base, get_position='[lon, lat]', get_fill_color="color", get_radius="radius", pickable=True, auto_highlight=True)]
    if not current.empty:
        layers.append(pdk.Layer("ScatterplotLayer", data=current, get_position='[lon, lat]', get_fill_color="color", get_radius="radius", pickable=True, auto_highlight=True))
    deck = pdk.Deck(
        map_provider="carto",
        map_style="dark",
        initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=zoom, pitch=0),
        layers=layers,
        tooltip={"html": "<b>{name}</b><br/>{category}<br/>{streets}"},
    )
    try:
        st.pydeck_chart(deck, use_container_width=True, height=height)
    except Exception:
        st.dataframe(base[["name", "layer_group", "category", "streets", "lat", "lon"]], use_container_width=True, hide_index=True)


def hotspot_details(name: str | None, hotspots_df: pd.DataFrame) -> dict[str, Any] | None:
    if not name or hotspots_df.empty:
        return None
    row = hotspots_df[hotspots_df["name"] == name]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def render_hotspot_summary(name: str | None, hotspots_df: pd.DataFrame, scenario_note: str | None = None, title: str = "Hotspot") -> None:
    details = hotspot_details(name, hotspots_df)
    if not details:
        st.info("No hotspot information available.")
        return
    st.subheader(title)
    st.write(f"**{details['name']}**")
    st.caption(str(details.get("streets", "—")))
    st.write(str(details.get("why", "No additional note available.")))
    if scenario_note:
        st.caption(scenario_note)


def _signal_value_from_metrics(layer: str, metrics: dict[str, float]) -> tuple[float, str, str, str]:
    if layer == "Intermodal / public transport":
        relevant_value = max(metrics["bus_bunching_index"], 1.0 - min(metrics["corridor_reliability_index"], 1.0))
        return relevant_value, "Transit and corridor stress", "BUS", f"Bus bunching {metrics['bus_bunching_index']:.2f}; corridor reliability {metrics['corridor_reliability_index']:.2f}."
    if layer == "Logistics / curb / port":
        relevant_value = max(0.55 * metrics["curb_occupancy_rate"] + 0.45 * metrics["illegal_curb_occupancy_rate"], min(metrics["delivery_queue"] / 15.0, 1.0), metrics["gateway_delay_index"] * 0.9)
        return relevant_value, "Logistics and curbside pressure", "LOG", f"Curb occupancy {metrics['curb_occupancy_rate']:.2f}; illegal use {metrics['illegal_curb_occupancy_rate']:.2f}; queue {metrics['delivery_queue']:.1f}."
    if layer == "Airport / gateway":
        relevant_value = max(metrics["gateway_delay_index"], 0.7 * (1.0 - min(metrics["network_speed_index"], 1.0)))
        return relevant_value, "Gateway access pressure", "GTW", f"Gateway delay {metrics['gateway_delay_index']:.2f}; network speed {metrics['network_speed_index']:.2f}."
    relevant_value = max(metrics["risk_score"], metrics["near_miss_index"], 0.9 * metrics["pedestrian_exposure"])
    return relevant_value, "Urban safety and pedestrian pressure", "RSK", f"Risk {metrics['risk_score']:.2f}; near-miss {metrics['near_miss_index']:.2f}; pedestrian exposure {metrics['pedestrian_exposure']:.2f}."


def build_hotspot_signals(hotspots_df: pd.DataFrame, history_df: pd.DataFrame, latest: dict[str, Any], focused_name: str | None) -> pd.DataFrame:
    if hotspots_df.empty:
        return pd.DataFrame()
    records = []
    primary = (latest or {}).get("primary_hotspot_name")
    active_event = (latest or {}).get("active_event") or "none"
    latest_metrics = {
        "network_speed_index": float((latest or {}).get("network_speed_index", 0.0) or 0.0),
        "corridor_reliability_index": float((latest or {}).get("corridor_reliability_index", 0.0) or 0.0),
        "bus_bunching_index": float((latest or {}).get("bus_bunching_index", 0.0) or 0.0),
        "curb_occupancy_rate": float((latest or {}).get("curb_occupancy_rate", 0.0) or 0.0),
        "illegal_curb_occupancy_rate": float((latest or {}).get("illegal_curb_occupancy_rate", 0.0) or 0.0),
        "delivery_queue": float((latest or {}).get("delivery_queue", 0.0) or 0.0),
        "risk_score": float((latest or {}).get("risk_score", 0.0) or 0.0),
        "near_miss_index": float((latest or {}).get("near_miss_index", 0.0) or 0.0),
        "pedestrian_exposure": float((latest or {}).get("pedestrian_exposure", 0.0) or 0.0),
        "gateway_delay_index": float((latest or {}).get("gateway_delay_index", 0.0) or 0.0),
    }
    previous_metrics = latest_metrics.copy()
    if history_df is not None and not history_df.empty and len(history_df) >= 2:
        prev = history_df.iloc[:-1].tail(4)
        for k in previous_metrics.keys():
            if k in prev.columns:
                previous_metrics[k] = float(prev[k].mean())

    def classify(level: float) -> str:
        if level >= 0.78:
            return "Critical"
        if level >= 0.58:
            return "Alert"
        if level >= 0.38:
            return "Watch"
        return "Normal"

    def phase(cur: float, prev: float) -> str:
        if cur >= 0.38 and prev < 0.38:
            return "Emerging"
        if cur >= 0.38:
            return "Active"
        if prev >= 0.38 and cur >= 0.18:
            return "Clearing"
        return "Hidden"

    for _, row in hotspots_df.iterrows():
        name = row["name"]
        layer = row.get("layer_group", "Urban core / tourism")
        is_primary = name == primary
        is_focused = name == focused_name
        cur_value, signal_type, short_label, message = _signal_value_from_metrics(layer, latest_metrics)
        prev_value, _, _, _ = _signal_value_from_metrics(layer, previous_metrics)
        emphasis = 1.0 + (0.22 if is_primary else 0.0) + (0.12 if is_focused else 0.0)
        severity = max(0.0, min(1.0, cur_value * emphasis))
        prev_severity = max(0.0, min(1.0, prev_value * emphasis))
        p = phase(severity, prev_severity)
        visible = is_primary or is_focused or p != "Hidden"
        if not visible:
            continue
        level = classify(severity)
        color = {
            "Normal": [70, 160, 80, 170],
            "Watch": [245, 190, 50, 190],
            "Alert": [245, 120, 35, 210],
            "Critical": [215, 50, 50, 230],
        }[level]
        records.append({
            "name": name,
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
            "category": row.get("category", ""),
            "streets": row.get("streets", ""),
            "layer_group": layer,
            "signal_type": signal_type,
            "short_label": short_label,
            "severity": severity,
            "alert_level": level,
            "phase": p,
            "color": color,
            "radius": 150 + 240 * severity + (80 if is_primary else 0) + (45 if is_focused else 0),
            "active_event": active_event,
            "message": message,
            "is_primary": is_primary,
            "is_focused": is_focused,
        })
    out = pd.DataFrame(records)
    if out.empty:
        return out
    return out.sort_values(["severity", "is_primary", "is_focused"], ascending=[False, False, False]).reset_index(drop=True)


def render_signals_map(signals_df: pd.DataFrame, height: int = 680) -> None:
    if signals_df.empty:
        st.info("No dynamic hotspot signals available.")
        return
    center_lat = float(signals_df["lat"].mean())
    center_lon = float(signals_df["lon"].mean())
    focused = signals_df[signals_df["is_focused"] | signals_df["is_primary"]]
    if not focused.empty:
        center_lat = float(focused.iloc[0]["lat"])
        center_lon = float(focused.iloc[0]["lon"])
    layers = [pdk.Layer("ScatterplotLayer", data=signals_df, get_position='[lon, lat]', get_fill_color="color", get_radius="radius", pickable=True, auto_highlight=True)]
    deck = pdk.Deck(
        map_provider="carto",
        map_style="dark",
        initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=11.9, pitch=0),
        layers=layers,
        tooltip={"html": "<b>{name}</b><br/><b>{alert_level}</b> · {phase} · {signal_type}<br/>{message}<br/><b>Event:</b> {active_event}<br/><b>Layer:</b> {layer_group}<br/>{streets}"},
    )
    try:
        st.pydeck_chart(deck, use_container_width=True, height=height)
    except Exception:
        st.dataframe(signals_df[["name", "alert_level", "phase", "signal_type", "active_event", "layer_group", "streets", "lat", "lon"]], use_container_width=True, hide_index=True)
