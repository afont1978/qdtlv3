
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

Mode = Literal["traffic", "safety", "logistics", "gateway", "event", "transit"]
Route = Literal["CLASSICAL", "QUANTUM", "FALLBACK_CLASSICAL"]
AssetType = Literal[
    "intersection",
    "road_corridor",
    "bus_corridor",
    "curb_zone",
    "risk_hotspot",
    "city_mobility_system",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Hotspot:
    name: str
    lat: float
    lon: float
    category: str
    streets: str
    why: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TwinBase:
    twin_id: str
    asset_type: AssetType
    name: str
    ts: str
    enabled: bool = True
    alarms: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> Dict[str, Any]:
        return asdict(self)

    def step(self, dt_h: float, context: Dict[str, Any]) -> None:
        raise NotImplementedError

    def apply_dispatch(self, dispatch: Dict[str, Any], dt_h: float) -> None:
        raise NotImplementedError


@dataclass
class ScenarioEvent:
    event_type: str
    severity: float
    start_step: int
    end_step: int
    payload: Dict[str, Any]

    def is_active(self, step_id: int) -> bool:
        return self.start_step <= step_id <= self.end_step


@dataclass
class ScenarioContext:
    scenario: str
    mode: Mode
    weather: Dict[str, Any]
    demand: Dict[str, Any]
    bus_ops: Dict[str, Any]
    curb_ops: Dict[str, Any]
    gateway_ops: Dict[str, Any]
    active_events: List[ScenarioEvent] = field(default_factory=list)
    scenario_note: str = ""


@dataclass
class MobilityDispatchProblem:
    step_id: int
    mode: Mode
    scenario: str
    objective_name: str
    constraints: Dict[str, Any]
    objective_terms: Dict[str, float]
    complexity_score: float
    discrete_ratio: float
    horizon_steps: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MobilityExecRecord:
    step_id: int
    ts: str
    mode: str
    scenario: str
    active_event: Optional[str]
    network_speed_index: float
    corridor_reliability_index: float
    corridor_delay_s: float
    bus_bunching_index: float
    bus_commercial_speed_kmh: float
    bus_priority_requests: int
    curb_occupancy_rate: float
    illegal_curb_occupancy_rate: float
    delivery_queue: float
    risk_score: float
    near_miss_index: float
    pedestrian_exposure: float
    bike_conflict_index: float
    gateway_delay_index: float
    step_operational_score: float
    cumulative_operational_score: float
    decision_route: Route
    decision_confidence: float
    exec_ms: int
    latency_breach: bool
    fallback_triggered: bool
    fallback_reasons: List[str]
    route_reason: str
    complexity_score: float
    discrete_ratio: float
    primary_hotspot_name: str
    primary_hotspot_lat: float
    primary_hotspot_lon: float
    scenario_note: str
    qre_json: Optional[str] = None
    result_json: Optional[str] = None
    dispatch_json: Optional[str] = None
    objective_breakdown_json: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
