
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EventScheduleEntry(BaseModel):
    mod: int
    severity: float = 0.5
    range: Optional[List[int]] = None
    points: Optional[List[int]] = None


class ScenarioSpec(BaseModel):
    id: str
    title: str
    mode: str = "traffic"
    complexity: str = "medium"
    primary_hotspots: List[str] = Field(default_factory=list)
    trigger_events: List[str] = Field(default_factory=list)
    disturbances: Dict[str, Any] = Field(default_factory=dict)
    expected_subproblems: List[str] = Field(default_factory=list)
    recommended_interventions: List[str] = Field(default_factory=list)
    kpis: List[str] = Field(default_factory=list)
    event_schedule: Dict[str, EventScheduleEntry] = Field(default_factory=dict)
    shocks: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    note: str = ""
    twin_hotspots: Dict[str, str] = Field(default_factory=dict)
