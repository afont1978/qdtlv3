from __future__ import annotations

from typing import Any

import pandas as pd


def project_what_if(latest: dict[str, Any], focused_name: str | None, controls: dict[str, Any]) -> dict[str, Any]:
    if not latest:
        return {}
    proj = dict(latest)
    shock = controls.get("shock", "None")
    bus_priority = int(controls.get("bus_priority", 0))
    enforcement = int(controls.get("enforcement", 0))
    ped_protection = bool(controls.get("ped_protection", False))
    diversion = bool(controls.get("diversion", False))

    nsi = float(proj.get("network_speed_index", 0.0))
    cri = float(proj.get("corridor_reliability_index", 0.0))
    cds = float(proj.get("corridor_delay_s", 0.0))
    bbi = float(proj.get("bus_bunching_index", 0.0))
    bcs = float(proj.get("bus_commercial_speed_kmh", 0.0))
    cor = float(proj.get("curb_occupancy_rate", 0.0))
    icor = float(proj.get("illegal_curb_occupancy_rate", 0.0))
    dq = float(proj.get("delivery_queue", 0.0))
    rs = float(proj.get("risk_score", 0.0))
    nm = float(proj.get("near_miss_index", 0.0))
    pe = float(proj.get("pedestrian_exposure", 0.0))
    bc = float(proj.get("bike_conflict_index", 0.0))
    gd = float(proj.get("gateway_delay_index", 0.0))

    if shock == "Rain event":
        nsi -= 0.08; cri -= 0.06; cds += 8; bbi += 0.03; rs += 0.08; nm += 0.05; bc += 0.04
    elif shock == "Incident on corridor":
        nsi -= 0.15; cri -= 0.14; cds += 18; bbi += 0.06; rs += 0.10; gd += 0.07
    elif shock == "Delivery wave":
        cor += 0.10; icor += 0.08; dq += 4; rs += 0.03
    elif shock == "Gateway surge":
        gd += 0.16; nsi -= 0.06; cri -= 0.05; cds += 7
    elif shock == "Event release":
        nsi -= 0.10; cri -= 0.08; cds += 10; bbi += 0.05; gd += 0.08; pe += 0.07
    elif shock == "School peak":
        rs += 0.10; nm += 0.06; pe += 0.10; bc += 0.03

    if bus_priority > 0:
        nsi += 0.02 * bus_priority; cri += 0.03 * bus_priority; cds -= 2.5 * bus_priority
        bbi -= 0.05 * bus_priority; bcs += 0.8 * bus_priority
    if enforcement > 0:
        cor -= 0.02 * enforcement; icor -= 0.08 * enforcement; dq -= 1.2 * enforcement; rs -= 0.01 * enforcement
    if ped_protection:
        rs -= 0.07; nm -= 0.05; pe -= 0.04; nsi -= 0.02; cds += 2.5
    if diversion:
        nsi += 0.05; cri += 0.04; cds -= 4.0; gd -= 0.03; cor += 0.02

    proj["network_speed_index"] = float(max(0.0, min(1.3, nsi)))
    proj["corridor_reliability_index"] = float(max(0.0, min(1.3, cri)))
    proj["corridor_delay_s"] = float(max(0.0, cds))
    proj["bus_bunching_index"] = float(max(0.0, min(1.0, bbi)))
    proj["bus_commercial_speed_kmh"] = float(max(5.0, min(30.0, bcs)))
    proj["curb_occupancy_rate"] = float(max(0.0, min(1.0, cor)))
    proj["illegal_curb_occupancy_rate"] = float(max(0.0, min(1.0, icor)))
    proj["delivery_queue"] = float(max(0.0, dq))
    proj["risk_score"] = float(max(0.0, min(1.0, rs)))
    proj["near_miss_index"] = float(max(0.0, min(1.0, nm)))
    proj["pedestrian_exposure"] = float(max(0.0, min(1.0, pe)))
    proj["bike_conflict_index"] = float(max(0.0, min(1.0, bc)))
    proj["gateway_delay_index"] = float(max(0.0, min(1.0, gd)))

    step_score = (
        0.30 * proj["network_speed_index"]
        + 0.20 * proj["corridor_reliability_index"]
        + 0.15 * (1.0 - proj["bus_bunching_index"])
        + 0.15 * (1.0 - (0.55 * proj["curb_occupancy_rate"] + 0.45 * proj["illegal_curb_occupancy_rate"]))
        + 0.20 * (1.0 - proj["risk_score"])
    )
    proj["step_operational_score"] = float(step_score)
    proj["primary_hotspot_name"] = focused_name or proj.get("primary_hotspot_name")

    route = "CLASSICAL"
    reason = "Classical intervention package remains sufficient for this hotspot."
    subproblem = "local_control_problem"
    if shock in {"Delivery wave", "Gateway surge", "Event release"} or (bus_priority >= 2 and enforcement >= 1):
        route = "QUANTUM"
        reason = "Hybrid route suggested because the hotspot combines several discrete interventions with competing objectives."
        subproblem = "multimodal_redispatch_problem"
    if shock in {"School peak", "Rain event"} and ped_protection:
        route = "CLASSICAL"
        reason = "Classical route preferred because the package is safety-critical and latency sensitive."
        subproblem = "safety_protection_problem"

    rec_action = "Maintain current operational package"
    rec_priority = "Medium"
    rec_expected = "Stabilise the hotspot without major side effects."
    rec_owner = "Urban operations"

    if shock == "Incident on corridor":
        rec_action = "Deploy incident response corridor plan with selective diversion"
        rec_priority = "High"
        rec_owner = "Traffic control"
        rec_expected = "Contain delay propagation and queue spillback around the hotspot."
    elif shock == "Rain event":
        rec_action = "Enable pedestrian protection and temporary speed mitigation"
        rec_priority = "High"
        rec_owner = "Safety operations"
        rec_expected = "Lower risk and near-miss exposure, with a moderate penalty in corridor speed."
    elif shock == "School peak":
        rec_action = "Activate school-area protection package and crossing supervision logic"
        rec_priority = "High"
        rec_owner = "Safety operations"
        rec_expected = "Reduce pedestrian exposure and conflict around the hotspot during the peak window."
    elif shock == "Delivery wave":
        rec_action = "Tighten curbside enforcement and reallocate DUM slots"
        rec_priority = "High"
        rec_owner = "Logistics / curbside"
        rec_expected = "Reduce illegal curb use and delivery queue pressure in the selected hotspot."
    elif shock == "Gateway surge":
        rec_action = "Activate gateway staging and access metering package"
        rec_priority = "High"
        rec_owner = "Gateway operations"
        rec_expected = "Reduce gateway delay and smooth arrivals/departures across the selected access node."
    elif shock == "Event release":
        rec_action = "Launch event dispersal package with multimodal rebalancing"
        rec_priority = "High"
        rec_owner = "Event mobility"
        rec_expected = "Absorb the post-event surge with better corridor reliability and bus regularity."
    elif bus_priority >= 2:
        rec_action = "Increase bus priority and coordinated holding on the focused corridor"
        rec_priority = "Medium"
        rec_owner = "Transit operations"
        rec_expected = "Improve regularity and reduce bunching, with manageable side effects on general traffic."

    proj["what_if_route"] = route
    proj["what_if_reason"] = reason
    proj["what_if_subproblem"] = subproblem
    proj["recommended_action"] = rec_action
    proj["recommended_priority"] = rec_priority
    proj["recommended_expected_impact"] = rec_expected
    proj["recommended_owner"] = rec_owner
    return proj



def metric_delta_rows(before: dict[str, Any], after: dict[str, Any], keys: list[str]) -> pd.DataFrame:
    rows = []
    for k in keys:
        b = before.get(k)
        a = after.get(k)
        if b is None or a is None:
            continue
        rows.append({
            "Metric": k.replace("_", " ").title(),
            "Baseline": round(float(b), 4),
            "Projected": round(float(a), 4),
            "Delta": round(float(a) - float(b), 4),
        })
    return pd.DataFrame(rows)
