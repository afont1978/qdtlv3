from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

ROUTE_COLORS = {
    "CLASSICAL": "#4E79A7",
    "QUANTUM": "#9C6ADE",
    "FALLBACK_CLASSICAL": "#F28E2B",
}


def metric_label(key: str) -> str:
    labels = {
        "network_speed_index": "Network speed index",
        "corridor_reliability_index": "Corridor reliability",
        "corridor_delay_s": "Corridor delay [s]",
        "bus_bunching_index": "Bus bunching",
        "bus_commercial_speed_kmh": "Bus commercial speed [km/h]",
        "curb_occupancy_rate": "Curb occupancy",
        "illegal_curb_occupancy_rate": "Illegal curb occupancy",
        "delivery_queue": "Delivery queue",
        "risk_score": "Risk score",
        "near_miss_index": "Near-miss index",
        "pedestrian_exposure": "Pedestrian exposure",
        "bike_conflict_index": "Bike conflict index",
        "gateway_delay_index": "Gateway delay",
        "step_operational_score": "Operational score",
    }
    return labels.get(key, key.replace("_", " ").title())



def make_line(df: pd.DataFrame, cols: list[str], title: str, y_title: str = "Index") -> go.Figure:
    fig = go.Figure()
    for col in cols:
        if col in df.columns:
            fig.add_trace(go.Scatter(x=df["step_id"], y=df[col], mode="lines", name=metric_label(col), line=dict(width=2)))
    fig.update_layout(
        title=title,
        template="plotly_dark",
        margin=dict(l=20, r=20, t=50, b=20),
        height=320,
        xaxis_title="Step",
        yaxis_title=y_title,
        legend=dict(orientation="h"),
    )
    return fig



def make_route_mix_chart(df: pd.DataFrame) -> go.Figure:
    if df.empty or "decision_route" not in df.columns:
        return go.Figure()
    rc = df["decision_route"].value_counts().reset_index()
    rc.columns = ["route", "count"]
    fig = px.pie(rc, names="route", values="count", hole=0.58, template="plotly_dark", title="Route mix", color="route", color_discrete_map=ROUTE_COLORS)
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), height=300, showlegend=True)
    return fig



def make_subsystem_score_chart(latest: dict[str, Any]) -> go.Figure:
    if not latest:
        return go.Figure()
    curb_pressure = 0.55 * float(latest.get("curb_occupancy_rate", 0.0) or 0.0) + 0.45 * float(latest.get("illegal_curb_occupancy_rate", 0.0) or 0.0)
    data = pd.DataFrame({
        "Subsystem": ["Traffic", "Transit", "Risk", "Logistics", "Gateway"],
        "Score": [
            float(latest.get("network_speed_index", 0.0) or 0.0),
            max(0.0, 1.0 - float(latest.get("bus_bunching_index", 0.0) or 0.0)),
            max(0.0, 1.0 - float(latest.get("risk_score", 0.0) or 0.0)),
            max(0.0, 1.0 - curb_pressure),
            max(0.0, 1.0 - float(latest.get("gateway_delay_index", 0.0) or 0.0)),
        ],
    })
    fig = px.bar(data, x="Score", y="Subsystem", orientation="h", template="plotly_dark", title="Subsystem scoreboard", color="Subsystem")
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), height=320, showlegend=False, xaxis_range=[0, 1.05])
    return fig



def make_alert_level_chart(signals_df: pd.DataFrame) -> go.Figure:
    if signals_df.empty:
        return go.Figure()
    counts = signals_df["alert_level"].value_counts().reindex(["Critical", "Alert", "Watch", "Normal"], fill_value=0).reset_index()
    counts.columns = ["Alert level", "Count"]
    fig = px.bar(
        counts,
        x="Alert level",
        y="Count",
        color="Alert level",
        template="plotly_dark",
        title="Alert level distribution",
        color_discrete_map={
            "Critical": "#d73232",
            "Alert": "#f57824",
            "Watch": "#f5be32",
            "Normal": "#46a050",
        },
    )
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), height=300, showlegend=False)
    return fig



def make_story_event_track(spec, active_event: str | None, step_id: int | None = None) -> go.Figure:
    events = list(spec.trigger_events or [])
    if not events:
        return go.Figure()
    plot_df = pd.DataFrame({"Order": list(range(1, len(events) + 1)), "Event": events})
    current_idx = 0
    if step_id is not None and len(events) > 0:
        current_idx = max(0, (int(step_id) - 1) % len(events))

    def classify_event(row) -> str:
        if active_event and row["Event"] == active_event:
            return "Active"
        if row.name == current_idx:
            return "Current"
        return "Scenario"

    plot_df["State"] = plot_df.apply(classify_event, axis=1)
    color_map = {"Scenario": "#5A78C9", "Current": "#9C6ADE", "Active": "#F29F05"}
    fig = px.scatter(
        plot_df,
        x="Order",
        y=[1] * len(plot_df),
        color="State",
        text="Event",
        template="plotly_dark",
        title="Scenario event sequence",
        color_discrete_map=color_map,
    )
    fig.update_traces(textposition="top center", marker=dict(size=18))
    fig.update_yaxes(visible=False, showticklabels=False)
    fig.update_xaxes(title="Event order")
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), height=260, showlegend=True)
    return fig



def make_story_disturbance_chart(spec) -> go.Figure:
    dist = spec.disturbances or {}
    rows = []
    for k, v in dist.items():
        try:
            rows.append({"Disturbance": str(k).replace("_", " ").title(), "Value": float(v)})
        except Exception:
            continue
    if not rows:
        return go.Figure()
    plot_df = pd.DataFrame(rows)
    fig = px.bar(plot_df, x="Disturbance", y="Value", template="plotly_dark", title="Disturbance profile")
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), height=260, showlegend=False)
    return fig



def make_delta_bar(delta_df: pd.DataFrame, top_n: int = 8) -> go.Figure:
    if delta_df.empty:
        return go.Figure()
    plot_df = delta_df.copy()
    plot_df["abs_delta"] = plot_df["Delta"].abs()
    plot_df = plot_df.sort_values("abs_delta", ascending=False).head(top_n)
    fig = px.bar(plot_df, x="Delta", y="Metric", orientation="h", template="plotly_dark", title="Metric deltas", color="Delta", color_continuous_scale="RdBu")
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), height=320, coloraxis_showscale=False)
    return fig



def make_scatter_compare(before: dict[str, Any], after: dict[str, Any], metrics: list[str], title: str = "Before vs projected") -> go.Figure:
    rows = []
    for m in metrics:
        if m in before and m in after:
            rows.append({"Metric": metric_label(m), "State": "Baseline", "Value": float(before[m])})
            rows.append({"Metric": metric_label(m), "State": "Projected", "Value": float(after[m])})
    plot_df = pd.DataFrame(rows)
    if plot_df.empty:
        return go.Figure()
    fig = px.bar(plot_df, x="Metric", y="Value", color="State", barmode="group", template="plotly_dark", title=title)
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), height=340)
    return fig
