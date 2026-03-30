
from __future__ import annotations

from typing import Dict, List
import math
import numpy as np

from mobility_os.domain.models import ScenarioContext, ScenarioEvent
from mobility_os.scenarios.schema import ScenarioSpec


class ScenarioEngine:
    def __init__(self, scenarios: Dict[str, ScenarioSpec], rng: np.random.Generator):
        self.scenarios = scenarios
        self.rng = rng

    def build_context(self, scenario_id: str, step_id: int) -> ScenarioContext:
        spec = self.scenarios[scenario_id]
        hour = (step_id % 288) / 12.0
        peak = 1.0 if 7.0 <= hour <= 10.0 or 17.0 <= hour <= 20.0 else 0.0
        rain_intensity = 0.0
        visibility = 0.95
        corridor_flow = 3600.0 + 1200.0 * peak + 450.0 * math.sin(hour / 24.0 * 2 * math.pi) + self.rng.normal(0, 120)
        ped_flow = 550.0 + 320.0 * peak + 120.0 * math.sin((hour + 2.0) / 24.0 * 2 * math.pi) + self.rng.normal(0, 40)
        bike_flow = 280.0 + 120.0 * math.sin((hour - 1.5) / 24.0 * 2 * math.pi) + self.rng.normal(0, 25)
        headway_pressure = 0.35 + 0.25 * peak + self.rng.normal(0, 0.03)
        delivery_pressure = 0.30 + 0.22 * (10.0 <= hour <= 15.0) + self.rng.normal(0, 0.03)
        illegal_pressure = 0.18 + 0.10 * (11.0 <= hour <= 14.0) + self.rng.normal(0, 0.02)
        pickup_dropoff_pressure = 0.22 + 0.18 * peak + self.rng.normal(0, 0.02)
        gateway_surge = 0.15 + 0.18 * peak + self.rng.normal(0, 0.02)

        # apply continuous disturbances when present
        d = spec.disturbances or {}
        corridor_flow *= d.get("corridor_flow_multiplier", 1.0)
        ped_flow *= d.get("ped_flow_multiplier", 1.0)
        bike_flow *= d.get("bike_flow_multiplier", 1.0)
        headway_pressure += d.get("bus_headway_pressure_add", 0.0)
        delivery_pressure += d.get("delivery_pressure_add", 0.0)
        illegal_pressure += d.get("illegal_parking_pressure_add", 0.0)
        pickup_dropoff_pressure += d.get("pickup_dropoff_pressure_add", 0.0)
        gateway_surge += d.get("gateway_surge_add", 0.0)
        rain_intensity = max(rain_intensity, d.get("rain_intensity", 0.0))
        visibility = min(visibility, d.get("visibility", 1.0))

        ctx = ScenarioContext(
            scenario=scenario_id,
            mode=spec.mode,
            weather={"rain_intensity": float(np.clip(rain_intensity, 0.0, 1.0)), "visibility": float(np.clip(visibility, 0.2, 1.0))},
            demand={
                "corridor_flow_vph": float(max(1400.0, corridor_flow)),
                "ped_flow_pph": float(max(100.0, ped_flow)),
                "bike_flow_pph": float(max(60.0, bike_flow)),
            },
            bus_ops={
                "priority_requests": int(max(0, round(2 + 4 * peak + self.rng.normal(0, 1.0)))),
                "headway_pressure": float(np.clip(headway_pressure, 0.0, 1.0)),
            },
            curb_ops={
                "delivery_pressure": float(np.clip(delivery_pressure, 0.0, 1.0)),
                "illegal_parking_pressure": float(np.clip(illegal_pressure, 0.0, 1.0)),
                "pickup_dropoff_pressure": float(np.clip(pickup_dropoff_pressure, 0.0, 1.0)),
            },
            gateway_ops={"surge_factor": float(np.clip(gateway_surge, 0.0, 1.0))},
            active_events=[],
            scenario_note=spec.note,
        )
        ctx.active_events = self._active_events(spec, step_id)
        self._apply_event_shocks(ctx, spec)
        return ctx

    def _active_events(self, spec: ScenarioSpec, step_id: int) -> List[ScenarioEvent]:
        events: List[ScenarioEvent] = []
        for event_name, schedule in spec.event_schedule.items():
            mod = int(schedule.mod)
            idx = step_id % mod
            active = False
            if schedule.range:
                start, end = schedule.range
                active = start <= idx <= end
            elif schedule.points:
                active = idx in schedule.points
            if active:
                events.append(ScenarioEvent(
                    event_type=event_name,
                    severity=float(schedule.severity),
                    start_step=step_id,
                    end_step=step_id,
                    payload={},
                ))
        return events

    def _apply_event_shocks(self, ctx: ScenarioContext, spec: ScenarioSpec) -> None:
        for ev in ctx.active_events:
            shock = dict(spec.shocks.get(ev.event_type, {}))
            ctx.demand["corridor_flow_vph"] *= shock.get("corridor_flow_multiplier", 1.0)
            ctx.demand["ped_flow_pph"] *= shock.get("ped_flow_multiplier", 1.0)
            ctx.bus_ops["headway_pressure"] = min(1.0, ctx.bus_ops["headway_pressure"] + shock.get("headway_pressure_add", 0.0))
            ctx.bus_ops["priority_requests"] += int(shock.get("priority_requests_add", 0))
            ctx.curb_ops["delivery_pressure"] = min(1.0, ctx.curb_ops["delivery_pressure"] + shock.get("delivery_pressure_add", 0.0))
            ctx.curb_ops["illegal_parking_pressure"] = min(1.0, ctx.curb_ops["illegal_parking_pressure"] + shock.get("illegal_parking_pressure_add", 0.0))
            ctx.curb_ops["pickup_dropoff_pressure"] = min(1.0, ctx.curb_ops["pickup_dropoff_pressure"] + shock.get("pickup_dropoff_pressure_add", 0.0))
            ctx.gateway_ops["surge_factor"] = min(1.0, ctx.gateway_ops["surge_factor"] + shock.get("gateway_surge_add", 0.0))
            ctx.weather["rain_intensity"] = max(ctx.weather["rain_intensity"], float(shock.get("rain_intensity", 0.0)))
            ctx.weather["visibility"] = min(ctx.weather["visibility"], float(shock.get("visibility", 1.0)))
