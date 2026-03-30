
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from mobility_os.domain.models import MobilityDispatchProblem
from mobility_os.solvers.classical import ClassicalMobilitySolver
from mobility_os.solvers.quantum_mock import MockQuantumMobilitySolver


class MobilityHybridOrchestrator:
    def __init__(self, seed: int = 42):
        self.classical = ClassicalMobilitySolver()
        self.quantum = MockQuantumMobilitySolver(seed=seed)

    def choose_route(self, problem: MobilityDispatchProblem) -> Tuple[str, str]:
        event = problem.metadata.get("active_event")
        risk = float(problem.metadata.get("risk_score", 0.0))
        bunching = float(problem.metadata.get("bus_bunching_index", 0.0))
        curb_pressure = float(problem.metadata.get("curb_pressure_index", 0.0))
        gateway_pressure = float(problem.metadata.get("gateway_delay_index", 0.0))
        if problem.mode == "safety" and (risk > 0.58 or event in {"school_peak", "incident"}):
            return "CLASSICAL", "Classical selected because the step is in immediate safety protection mode."
        if problem.complexity_score < 4.7 or problem.discrete_ratio < 0.40:
            return "CLASSICAL", "Classical selected because the decision space is still limited."
        if event in {"delivery_wave", "illegal_curb_occupation", "gateway_surge", "event_release", "bus_bunching"}:
            return "QUANTUM", "Quantum selected because the step combines multiple discrete urban control actions."
        if problem.mode == "logistics" and curb_pressure > 0.52:
            return "QUANTUM", "Quantum selected because curbside allocation and enforcement are under high pressure."
        if problem.mode == "gateway" and gateway_pressure > 0.52:
            return "QUANTUM", "Quantum selected because access coordination across multiple resources is required."
        if problem.mode == "traffic" and bunching > 0.30 and problem.complexity_score > 5.3:
            return "QUANTUM", "Quantum selected because corridor coordination and bus priority conflict across several actions."
        return "CLASSICAL", "Classical selected because the step remains manageable with deterministic coordination."

    def solve(self, state: Dict[str, Any], problem: MobilityDispatchProblem) -> Dict[str, Any]:
        route, reason = self.choose_route(problem)
        if route == "CLASSICAL":
            dispatch, breakdown, confidence = self.classical.solve(state, problem)
            return {
                "route": "CLASSICAL",
                "route_reason": reason,
                "dispatch": dispatch,
                "objective_breakdown": breakdown,
                "confidence": confidence,
                "exec_ms": 48,
                "latency_breach": False,
                "fallback_triggered": False,
                "fallback_reasons": [],
                "qre_json": None,
                "result_json": None,
            }

        dispatch, breakdown, confidence, qre, result = self.quantum.solve(state, problem)
        exec_ms = int(result["backend"]["queue_ms"] + result["backend"]["exec_ms"])
        latency_limit_ms = 1100 if problem.mode in {"gateway", "event"} else 900
        latency_breach = exec_ms > latency_limit_ms
        fallback_reasons: List[str] = []
        fallback_triggered = False
        if latency_breach:
            fallback_triggered = True
            fallback_reasons.append("SLA_BREACH")
        if confidence < 0.73:
            fallback_triggered = True
            fallback_reasons.append("LOW_CONFIDENCE")

        if fallback_triggered:
            dispatch, breakdown, confidence = self.classical.solve(state, problem)
            return {
                "route": "FALLBACK_CLASSICAL",
                "route_reason": "Fallback to classical because the hybrid attempt breached SLA or confidence constraints.",
                "dispatch": dispatch,
                "objective_breakdown": breakdown,
                "confidence": confidence,
                "exec_ms": exec_ms,
                "latency_breach": latency_breach,
                "fallback_triggered": True,
                "fallback_reasons": fallback_reasons,
                "qre_json": json.dumps(qre, ensure_ascii=False),
                "result_json": json.dumps(result, ensure_ascii=False),
            }

        return {
            "route": "QUANTUM",
            "route_reason": reason,
            "dispatch": dispatch,
            "objective_breakdown": breakdown,
            "confidence": confidence,
            "exec_ms": exec_ms,
            "latency_breach": latency_breach,
            "fallback_triggered": False,
            "fallback_reasons": [],
            "qre_json": json.dumps(qre, ensure_ascii=False),
            "result_json": json.dumps(result, ensure_ascii=False),
        }
