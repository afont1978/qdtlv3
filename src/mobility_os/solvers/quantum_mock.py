
from __future__ import annotations

import json
from typing import Dict, Tuple
import numpy as np

from mobility_os.domain.models import MobilityDispatchProblem
from mobility_os.solvers.classical import ClassicalMobilitySolver


class MockQuantumMobilitySolver:
    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def solve(self, state: Dict[str, float], problem: MobilityDispatchProblem) -> Tuple[Dict[str, int | float], Dict[str, float], float, Dict[str, object], Dict[str, object]]:
        classical = ClassicalMobilitySolver()
        dispatch, obj, _ = classical.solve(state, problem)

        event = state["active_event"]
        if event in {"delivery_wave", "illegal_curb_occupation"}:
            dispatch["enforcement_level"] = 2
            obj["curb_penalty"] *= 0.83
        if event in {"bus_bunching", "demand_spike", "event_release"}:
            dispatch["bus_priority_level"] = min(3, int(dispatch["bus_priority_level"]) + 1)
            dispatch["holding_strategy"] = 1
            dispatch["signal_coordination_mode"] = max(2, int(dispatch["signal_coordination_mode"]))
            obj["bunching_penalty"] *= 0.85
        if event in {"school_peak", "rain_event"}:
            dispatch["ped_protection_mode"] = 1
            dispatch["speed_mitigation_mode"] = 1
            dispatch["preventive_alert_level"] = 2
            obj["risk_penalty"] *= 0.86

        confidence = 0.75 + 0.10 * self.rng.random()
        qre = {
            "qre_version": "1.0",
            "mode": problem.mode,
            "scenario": problem.scenario,
            "objective_name": problem.objective_name,
            "complexity_score": problem.complexity_score,
            "discrete_ratio": problem.discrete_ratio,
            "constraints": problem.constraints,
            "active_event": problem.metadata.get("active_event"),
        }
        result = {
            "status": "SUCCEEDED",
            "backend": {
                "provider": "SIM_QPU",
                "backend_id": "sim-mobility-qpu",
                "queue_ms": int(220 + 420 * self.rng.random()),
                "exec_ms": int(150 + 180 * self.rng.random()),
            },
            "solution": {"dispatch": dispatch, "confidence": confidence},
        }
        return dispatch, obj, confidence, qre, result
