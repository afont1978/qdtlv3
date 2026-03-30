
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
import numpy as np

from .models import TwinBase


@dataclass
class IntersectionTwin(TwinBase):
    avg_delay_s: float = 34.0
    ped_wait_s: float = 24.0
    risk_score: float = 0.32
    throughput_vph: float = 3200.0
    bus_priority_level: int = 1
    ped_protection_mode: int = 0

    def step(self, dt_h: float, context: Dict[str, Any]) -> None:
        demand = context["demand"]
        weather = context["weather"]
        events = context["active_events"]
        base_flow = float(demand["corridor_flow_vph"])
        ped_flow = float(demand["ped_flow_pph"])
        rain = float(weather["rain_intensity"])
        incident = any(ev["event_type"] == "incident" for ev in events)
        school = any(ev["event_type"] == "school_peak" for ev in events)

        delay = 14.0 + 0.0075 * base_flow + 0.012 * ped_flow + 12.0 * rain
        if incident:
            delay += 18.0
        if self.bus_priority_level > 1:
            delay -= 4.0
        self.avg_delay_s = float(np.clip(delay, 8.0, 180.0))
        self.ped_wait_s = float(np.clip(8.0 + 0.01 * ped_flow + 9.0 * self.ped_protection_mode, 5.0, 120.0))
        risk = 0.18 + 0.0026 * self.avg_delay_s + 0.002 * self.ped_wait_s + 0.05 * rain + (0.09 if school else 0.0)
        risk -= 0.06 * self.ped_protection_mode
        self.risk_score = float(np.clip(risk, 0.0, 1.0))
        self.throughput_vph = float(np.clip(base_flow * (0.88 - 0.07 * rain + 0.03 * self.bus_priority_level), 1200, 5000))

    def apply_dispatch(self, dispatch: Dict[str, Any], dt_h: float) -> None:
        self.bus_priority_level = int(dispatch.get("bus_priority_level", self.bus_priority_level))
        self.ped_protection_mode = int(dispatch.get("ped_protection_mode", self.ped_protection_mode))


@dataclass
class RoadCorridorTwin(TwinBase):
    avg_speed_kmh: float = 22.0
    travel_time_index: float = 1.35
    queue_spillback_risk: float = 0.18
    signal_coordination_mode: int = 1
    diversion_mode: int = 0

    def step(self, dt_h: float, context: Dict[str, Any]) -> None:
        demand = context["demand"]
        weather = context["weather"]
        events = context["active_events"]
        flow = float(demand["corridor_flow_vph"])
        rain = float(weather["rain_intensity"])
        incident = any(ev["event_type"] == "incident" for ev in events)
        event_release = any(ev["event_type"] == "event_release" for ev in events)
        pressure = 0.00022 * flow + 0.30 * rain + (0.35 if incident else 0.0) + (0.15 if event_release else 0.0)
        mitigation = 0.07 * self.signal_coordination_mode + 0.08 * self.diversion_mode
        self.avg_speed_kmh = float(np.clip(34.0 - 17.0 * pressure + 5.0 * mitigation, 6.0, 45.0))
        self.travel_time_index = float(np.clip(40.0 / max(self.avg_speed_kmh, 1e-6), 0.8, 5.0))
        self.queue_spillback_risk = float(np.clip(0.15 + 0.28 * pressure - 0.05 * self.diversion_mode, 0.0, 1.0))

    def apply_dispatch(self, dispatch: Dict[str, Any], dt_h: float) -> None:
        self.signal_coordination_mode = int(dispatch.get("signal_coordination_mode", self.signal_coordination_mode))
        self.diversion_mode = int(dispatch.get("diversion_mode", self.diversion_mode))


@dataclass
class BusCorridorTwin(TwinBase):
    bunching_index: float = 0.22
    commercial_speed_kmh: float = 12.8
    priority_level: int = 1
    holding_strategy: int = 0

    def step(self, dt_h: float, context: Dict[str, Any]) -> None:
        bus_ops = context["bus_ops"]
        weather = context["weather"]
        events = context["active_events"]
        headway_pressure = float(bus_ops["headway_pressure"])
        rain = float(weather["rain_intensity"])
        bunching_event = any(ev["event_type"] == "bus_bunching" for ev in events)
        control_gain = 0.09 * self.priority_level + 0.05 * self.holding_strategy
        self.bunching_index = float(np.clip(0.14 + 0.60 * headway_pressure + 0.10 * rain + (0.12 if bunching_event else 0.0) - control_gain, 0.0, 1.0))
        self.commercial_speed_kmh = float(np.clip(16.0 - 5.2 * self.bunching_index - 1.5 * rain + 0.8 * self.priority_level, 7.0, 20.0))

    def apply_dispatch(self, dispatch: Dict[str, Any], dt_h: float) -> None:
        self.priority_level = int(dispatch.get("bus_priority_level", self.priority_level))
        self.holding_strategy = int(dispatch.get("holding_strategy", self.holding_strategy))


@dataclass
class CurbZoneTwin(TwinBase):
    occupancy_rate: float = 0.66
    illegal_occupancy_rate: float = 0.14
    delivery_queue: float = 6.0
    enforcement_level: int = 1

    def step(self, dt_h: float, context: Dict[str, Any]) -> None:
        curb_ops = context["curb_ops"]
        demand = context["demand"]
        events = context["active_events"]
        delivery_pressure = float(curb_ops["delivery_pressure"])
        illegal_pressure = float(curb_ops["illegal_parking_pressure"])
        pickup_dropoff = float(curb_ops["pickup_dropoff_pressure"])
        ped_flow = float(demand["ped_flow_pph"])
        illegal_event = any(ev["event_type"] == "illegal_curb_occupation" for ev in events)
        wave_event = any(ev["event_type"] == "delivery_wave" for ev in events)
        enforcement = 0.08 * self.enforcement_level
        self.occupancy_rate = float(np.clip(0.42 + 0.55 * delivery_pressure + 0.15 * pickup_dropoff + (0.12 if wave_event else 0.0), 0.0, 1.0))
        self.illegal_occupancy_rate = float(np.clip(0.05 + 0.45 * illegal_pressure + (0.18 if illegal_event else 0.0) - enforcement, 0.0, 1.0))
        self.delivery_queue = float(np.clip(2.0 + 14.0 * delivery_pressure + 3.5 * self.occupancy_rate - 1.2 * self.enforcement_level, 0.0, 40.0))

    def apply_dispatch(self, dispatch: Dict[str, Any], dt_h: float) -> None:
        self.enforcement_level = int(dispatch.get("enforcement_level", self.enforcement_level))


@dataclass
class RiskHotspotTwin(TwinBase):
    risk_score: float = 0.34
    near_miss_index: float = 0.12
    pedestrian_exposure: float = 0.38
    bike_conflict_index: float = 0.20
    preventive_alert_level: int = 0
    speed_mitigation_mode: int = 0

    def step(self, dt_h: float, context: Dict[str, Any]) -> None:
        weather = context["weather"]
        demand = context["demand"]
        events = context["active_events"]
        ped_flow = float(demand["ped_flow_pph"])
        bike_flow = float(demand["bike_flow_pph"])
        rain = float(weather["rain_intensity"])
        school_flag = any(ev["event_type"] == "school_peak" for ev in events)
        mitigation = 0.08 * self.preventive_alert_level + 0.10 * self.speed_mitigation_mode
        self.pedestrian_exposure = float(np.clip(0.15 + ped_flow / 2500.0 + (0.18 if school_flag else 0.0), 0.0, 1.0))
        self.bike_conflict_index = float(np.clip(0.08 + bike_flow / 2200.0 + 0.12 * rain, 0.0, 1.0))
        self.near_miss_index = float(np.clip(0.04 + 0.18 * self.pedestrian_exposure + 0.12 * self.bike_conflict_index + 0.10 * rain - mitigation, 0.0, 1.0))
        self.risk_score = float(np.clip(0.10 + 0.45 * self.near_miss_index + 0.20 * self.pedestrian_exposure + 0.14 * self.bike_conflict_index, 0.0, 1.0))

    def apply_dispatch(self, dispatch: Dict[str, Any], dt_h: float) -> None:
        self.preventive_alert_level = int(dispatch.get("preventive_alert_level", self.preventive_alert_level))
        self.speed_mitigation_mode = int(dispatch.get("speed_mitigation_mode", self.speed_mitigation_mode))


@dataclass
class CityMobilitySystemTwin(TwinBase):
    def step(self, dt_h: float, context: Dict[str, Any]) -> None:
        return None

    def apply_dispatch(self, dispatch: Dict[str, Any], dt_h: float) -> None:
        return None
