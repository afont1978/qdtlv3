
from __future__ import annotations

from typing import Dict, Tuple

from mobility_os.domain.models import MobilityDispatchProblem


class ClassicalMobilitySolver:
    def solve(self, state: Dict[str, float], problem: MobilityDispatchProblem) -> Tuple[Dict[str, int | float], Dict[str, float], float]:
        risk = state["risk_score"]
        bunching = state["bus_bunching_index"]
        curb_pressure = state["curb_pressure_index"]
        speed_index = state["network_speed_index"]
        active_event = state["active_event"]

        dispatch = {
            "bus_priority_level": 1,
            "holding_strategy": 0,
            "signal_coordination_mode": 1,
            "diversion_mode": 0,
            "enforcement_level": 1,
            "ped_protection_mode": 0,
            "speed_mitigation_mode": 0,
            "preventive_alert_level": 0,
        }

        if problem.mode == "safety" or risk > 0.62:
            dispatch["ped_protection_mode"] = 1
            dispatch["speed_mitigation_mode"] = 1
            dispatch["preventive_alert_level"] = 2

        if bunching > 0.35:
            dispatch["bus_priority_level"] = 2
            dispatch["holding_strategy"] = 1

        if speed_index < 0.62:
            dispatch["signal_coordination_mode"] = 2
            dispatch["diversion_mode"] = 1

        if curb_pressure > 0.55:
            dispatch["enforcement_level"] = 2

        if active_event == "incident":
            dispatch["diversion_mode"] = 2
            dispatch["signal_coordination_mode"] = 3

        objective_breakdown = {
            "delay_penalty": state["corridor_delay_s"] * 0.08,
            "bunching_penalty": bunching * 8.0,
            "risk_penalty": risk * 14.0,
            "curb_penalty": curb_pressure * 7.0,
            "gateway_penalty": state["gateway_delay_index"] * 4.0,
        }
        confidence = 0.86 if problem.mode in {"safety", "traffic"} else 0.80
        return dispatch, objective_breakdown, confidence
