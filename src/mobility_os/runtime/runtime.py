
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from mobility_os.domain.models import MobilityDispatchProblem, MobilityExecRecord, utc_now_iso
from mobility_os.domain.twins import (
    BusCorridorTwin,
    CityMobilitySystemTwin,
    CurbZoneTwin,
    IntersectionTwin,
    RiskHotspotTwin,
    RoadCorridorTwin,
)
from mobility_os.io.hotspot_repo import load_hotspots
from mobility_os.orchestration.hybrid import MobilityHybridOrchestrator
from mobility_os.scenarios.engine import ScenarioEngine
from mobility_os.scenarios.loader import load_scenarios


class MobilityRuntime:
    def __init__(self, scenario: str = "corridor_congestion", seed: int = 42, hotspots_csv: Optional[str] = None):
        self.scenario = scenario
        self.seed = int(seed)
        self.rng = np.random.default_rng(self.seed)
        self.step_id = 0
        self.cumulative_operational_score = 0.0
        self.hotspots = load_hotspots(hotspots_csv)
        self.scenarios = load_scenarios()
        if scenario not in self.scenarios:
            self.scenario = next(iter(self.scenarios))
        self.engine = ScenarioEngine(self.scenarios, self.rng)
        self.orchestrator = MobilityHybridOrchestrator(seed=self.seed)
        self.records: List[MobilityExecRecord] = []
        self._build_twins()

    def _build_twins(self) -> None:
        ts = utc_now_iso()
        self.twins = {
            "intersection": IntersectionTwin("intersection", "intersection", "Main Intersection", ts),
            "road_corridor": RoadCorridorTwin("road_corridor", "road_corridor", "Primary Corridor", ts),
            "bus_corridor": BusCorridorTwin("bus_corridor", "bus_corridor", "Bus Corridor", ts),
            "curb_zone": CurbZoneTwin("curb_zone", "curb_zone", "Curb Zone", ts),
            "risk_hotspot": RiskHotspotTwin("risk_hotspot", "risk_hotspot", "Risk Hotspot", ts),
            "city_mobility_system": CityMobilitySystemTwin("city_mobility_system", "city_mobility_system", "City Mobility System", ts),
        }
        self._attach_hotspots()

    def _attach_hotspots(self) -> None:
        spec = self.scenarios[self.scenario]
        for twin_id, hotspot_name in spec.twin_hotspots.items():
            if twin_id not in self.twins:
                continue
            hotspot = self.hotspots.get(hotspot_name)
            meta = {"scenario_hotspot_name": hotspot_name, "scenario_note": spec.note}
            if hotspot is not None:
                meta.update({"hotspot_name": hotspot.name, "lat": hotspot.lat, "lon": hotspot.lon, "category": hotspot.category, "streets": hotspot.streets, "why": hotspot.why})
            self.twins[twin_id].metadata.update(meta)

    def get_context(self):
        return self.engine.build_context(self.scenario, self.step_id)

    def update_telemetry(self, ctx) -> None:
        dt_h = 5.0 / 60.0
        ctx_dict = {
            "weather": ctx.weather,
            "demand": ctx.demand,
            "bus_ops": ctx.bus_ops,
            "curb_ops": ctx.curb_ops,
            "gateway_ops": ctx.gateway_ops,
            "active_events": [asdict(e) for e in ctx.active_events],
        }
        for twin in self.twins.values():
            twin.ts = utc_now_iso()
        self.twins["intersection"].step(dt_h, ctx_dict)
        self.twins["road_corridor"].step(dt_h, ctx_dict)
        self.twins["bus_corridor"].step(dt_h, ctx_dict)
        self.twins["curb_zone"].step(dt_h, ctx_dict)
        self.twins["risk_hotspot"].step(dt_h, ctx_dict)

    def aggregate_state(self, ctx) -> Dict[str, Any]:
        inter = self.twins["intersection"]
        corridor = self.twins["road_corridor"]
        bus = self.twins["bus_corridor"]
        curb = self.twins["curb_zone"]
        risk = self.twins["risk_hotspot"]
        spec = self.scenarios[self.scenario]
        primary_name = spec.primary_hotspots[0] if spec.primary_hotspots else next(iter(self.hotspots))
        primary = self.hotspots.get(primary_name)
        active_event = ctx.active_events[0].event_type if ctx.active_events else None
        network_speed_index = float(np.clip(corridor.avg_speed_kmh / 32.0, 0.0, 1.2))
        corridor_reliability_index = float(np.clip(1.0 / corridor.travel_time_index, 0.0, 1.2))
        curb_pressure_index = float(np.clip(0.55 * curb.occupancy_rate + 0.45 * curb.illegal_occupancy_rate, 0.0, 1.0))
        gateway_delay_index = float(np.clip(0.18 + 0.65 * ctx.gateway_ops["surge_factor"] + 0.12 * corridor.queue_spillback_risk, 0.0, 1.0))
        return {
            "ts": utc_now_iso(),
            "mode": ctx.mode,
            "scenario": ctx.scenario,
            "scenario_note": ctx.scenario_note,
            "active_event": active_event,
            "network_speed_index": network_speed_index,
            "corridor_reliability_index": corridor_reliability_index,
            "corridor_delay_s": corridor.travel_time_index * 75.0,
            "bus_bunching_index": bus.bunching_index,
            "bus_commercial_speed_kmh": bus.commercial_speed_kmh,
            "bus_priority_requests": ctx.bus_ops["priority_requests"],
            "curb_occupancy_rate": curb.occupancy_rate,
            "illegal_curb_occupancy_rate": curb.illegal_occupancy_rate,
            "delivery_queue": curb.delivery_queue,
            "curb_pressure_index": curb_pressure_index,
            "risk_score": risk.risk_score,
            "near_miss_index": risk.near_miss_index,
            "pedestrian_exposure": risk.pedestrian_exposure,
            "bike_conflict_index": risk.bike_conflict_index,
            "gateway_delay_index": gateway_delay_index,
            "primary_hotspot_name": primary_name,
            "primary_hotspot_lat": primary.lat if primary else 41.3851,
            "primary_hotspot_lon": primary.lon if primary else 2.1734,
        }

    def build_problem(self, state: Dict[str, Any], ctx) -> MobilityDispatchProblem:
        discrete_vars = 8
        continuous_vars = 2
        event_bonus = 0.0
        if state["active_event"] in {"delivery_wave", "illegal_curb_occupation", "gateway_surge", "event_release", "bus_bunching"}:
            event_bonus += 1.5
        if state["active_event"] in {"school_peak", "rain_event"}:
            event_bonus += 0.8
        coupling_bonus = 0.0
        if state["gateway_delay_index"] > 0.50:
            coupling_bonus += 0.9
        if state["curb_pressure_index"] > 0.55:
            coupling_bonus += 0.8
        mode_bonus = {"traffic": 0.7, "safety": 0.4, "logistics": 1.0, "gateway": 1.0, "event": 1.2, "transit": 0.9}[ctx.mode]
        complexity = discrete_vars * 0.55 + continuous_vars * 0.15 + event_bonus + coupling_bonus + mode_bonus
        discrete_ratio = discrete_vars / (discrete_vars + continuous_vars)
        constraints = {
            "network_speed_index": state["network_speed_index"],
            "corridor_reliability_index": state["corridor_reliability_index"],
            "bus_bunching_index": state["bus_bunching_index"],
            "curb_pressure_index": state["curb_pressure_index"],
            "risk_score": state["risk_score"],
            "gateway_delay_index": state["gateway_delay_index"],
        }
        objective_terms = {
            "delay_penalty_weight": 1.0,
            "bunching_penalty_weight": 1.0,
            "risk_penalty_weight": 1.2,
            "curb_penalty_weight": 0.9,
            "gateway_penalty_weight": 0.8,
        }
        metadata = {
            "active_event": state["active_event"],
            "risk_score": state["risk_score"],
            "bus_bunching_index": state["bus_bunching_index"],
            "curb_pressure_index": state["curb_pressure_index"],
            "gateway_delay_index": state["gateway_delay_index"],
            "primary_hotspot_name": state["primary_hotspot_name"],
        }
        return MobilityDispatchProblem(
            step_id=self.step_id,
            mode=ctx.mode,
            scenario=ctx.scenario,
            objective_name="min_delay_risk_and_logistics_conflict",
            constraints=constraints,
            objective_terms=objective_terms,
            complexity_score=complexity,
            discrete_ratio=discrete_ratio,
            horizon_steps=12,
            metadata=metadata,
        )

    def validate_dispatch(self, dispatch: Dict[str, Any]) -> Dict[str, Any]:
        dispatch = dict(dispatch)
        dispatch["bus_priority_level"] = int(np.clip(dispatch.get("bus_priority_level", 1), 0, 3))
        dispatch["signal_coordination_mode"] = int(np.clip(dispatch.get("signal_coordination_mode", 1), 0, 3))
        dispatch["enforcement_level"] = int(np.clip(dispatch.get("enforcement_level", 1), 0, 2))
        dispatch["ped_protection_mode"] = int(np.clip(dispatch.get("ped_protection_mode", 0), 0, 1))
        dispatch["speed_mitigation_mode"] = int(np.clip(dispatch.get("speed_mitigation_mode", 0), 0, 1))
        dispatch["preventive_alert_level"] = int(np.clip(dispatch.get("preventive_alert_level", 0), 0, 2))
        return dispatch

    def apply_dispatch(self, dispatch: Dict[str, Any], dt_h: float = 5.0 / 60.0) -> None:
        self.twins["intersection"].apply_dispatch(dispatch, dt_h)
        self.twins["road_corridor"].apply_dispatch(dispatch, dt_h)
        self.twins["bus_corridor"].apply_dispatch(dispatch, dt_h)
        self.twins["curb_zone"].apply_dispatch(dispatch, dt_h)
        self.twins["risk_hotspot"].apply_dispatch(dispatch, dt_h)

    def compute_record(self, state: Dict[str, Any], decision: Dict[str, Any], problem: MobilityDispatchProblem) -> MobilityExecRecord:
        step_operational_score = (
            0.30 * state["network_speed_index"] +
            0.20 * state["corridor_reliability_index"] +
            0.15 * (1.0 - state["bus_bunching_index"]) +
            0.15 * (1.0 - state["curb_pressure_index"]) +
            0.20 * (1.0 - state["risk_score"])
        )
        self.cumulative_operational_score += step_operational_score
        return MobilityExecRecord(
            step_id=self.step_id,
            ts=utc_now_iso(),
            mode=state["mode"],
            scenario=state["scenario"],
            active_event=state["active_event"],
            network_speed_index=state["network_speed_index"],
            corridor_reliability_index=state["corridor_reliability_index"],
            corridor_delay_s=state["corridor_delay_s"],
            bus_bunching_index=state["bus_bunching_index"],
            bus_commercial_speed_kmh=state["bus_commercial_speed_kmh"],
            bus_priority_requests=state["bus_priority_requests"],
            curb_occupancy_rate=state["curb_occupancy_rate"],
            illegal_curb_occupancy_rate=state["illegal_curb_occupancy_rate"],
            delivery_queue=state["delivery_queue"],
            risk_score=state["risk_score"],
            near_miss_index=state["near_miss_index"],
            pedestrian_exposure=state["pedestrian_exposure"],
            bike_conflict_index=state["bike_conflict_index"],
            gateway_delay_index=state["gateway_delay_index"],
            step_operational_score=step_operational_score,
            cumulative_operational_score=self.cumulative_operational_score,
            decision_route=decision["route"],
            decision_confidence=decision["confidence"],
            exec_ms=decision["exec_ms"],
            latency_breach=decision["latency_breach"],
            fallback_triggered=decision["fallback_triggered"],
            fallback_reasons=decision["fallback_reasons"],
            route_reason=decision["route_reason"],
            complexity_score=problem.complexity_score,
            discrete_ratio=problem.discrete_ratio,
            primary_hotspot_name=state["primary_hotspot_name"],
            primary_hotspot_lat=state["primary_hotspot_lat"],
            primary_hotspot_lon=state["primary_hotspot_lon"],
            scenario_note=state["scenario_note"],
            qre_json=decision["qre_json"],
            result_json=decision["result_json"],
            dispatch_json=json.dumps(decision["dispatch"], ensure_ascii=False),
            objective_breakdown_json=json.dumps(decision["objective_breakdown"], ensure_ascii=False),
        )

    def step(self, dt_h: float = 5.0 / 60.0) -> MobilityExecRecord:
        self.step_id += 1
        ctx = self.get_context()
        self.update_telemetry(ctx)
        state = self.aggregate_state(ctx)
        problem = self.build_problem(state, ctx)
        decision = self.orchestrator.solve(state, problem)
        decision["dispatch"] = self.validate_dispatch(decision["dispatch"])
        self.apply_dispatch(decision["dispatch"], dt_h)
        record = self.compute_record(state, decision, problem)
        self.records.append(record)
        return record

    def dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([r.to_dict() for r in self.records])

    def latest_state(self) -> Dict[str, Any]:
        if not self.records:
            return {}
        return self.records[-1].to_dict()

    def twin_snapshot(self) -> Dict[str, Dict[str, Any]]:
        return {k: v.snapshot() for k, v in self.twins.items()}

    def reset(self) -> None:
        self.__init__(scenario=self.scenario, seed=self.seed)


def run_demo(steps: int = 48, scenario: str = "corridor_congestion", seed: int = 42) -> pd.DataFrame:
    rt = MobilityRuntime(scenario=scenario, seed=seed)
    for _ in range(steps):
        rt.step()
    return rt.dataframe()
