
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from mobility_os.scenarios.schema import ScenarioSpec


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _scenario_paths() -> tuple[Path, Path, Path]:
    root = _root()
    return (
        root / "data" / "scenarios" / "scenario_library.json",
        root / "data" / "scenarios" / "scenario_library_high_complexity_v2.json",
        root / "data" / "scenarios" / "scenario_meta.json",
    )


def load_scenarios() -> Dict[str, ScenarioSpec]:
    base_path, high_path, meta_path = _scenario_paths()
    base_data = json.loads(base_path.read_text(encoding="utf-8"))
    high_data = json.loads(high_path.read_text(encoding="utf-8"))
    meta_data = json.loads(meta_path.read_text(encoding="utf-8"))

    specs: Dict[str, ScenarioSpec] = {}
    for sid, payload in base_data.items():
        meta = meta_data.get(sid, {})
        specs[sid] = ScenarioSpec(
            id=sid,
            title=meta.get("title", sid.replace("_", " ").title()),
            mode=payload.get("mode", "traffic"),
            complexity=meta.get("complexity", "medium"),
            primary_hotspots=meta.get("primary_hotspots", []),
            trigger_events=list(payload.get("event_schedule", {}).keys()),
            event_schedule=payload.get("event_schedule", {}),
            shocks=payload.get("shocks", {}),
            note=meta.get("note", ""),
            twin_hotspots=meta.get("twin_hotspots", {}),
        )

    for item in high_data.get("scenarios", []):
        sid = item["id"]
        meta = meta_data.get(sid, {})
        specs[sid] = ScenarioSpec(
            id=sid,
            title=item.get("title", sid.replace("_", " ").title()),
            mode=item.get("modes", ["traffic"])[0],
            complexity=item.get("complexity", "high"),
            primary_hotspots=item.get("primary_hotspots", []),
            trigger_events=item.get("trigger_events", []),
            disturbances=item.get("disturbances", {}),
            expected_subproblems=item.get("expected_subproblems", []),
            recommended_interventions=item.get("recommended_interventions", []),
            kpis=item.get("kpis", []),
            note=meta.get("note", item.get("operational_goal", "")),
            twin_hotspots=meta.get("twin_hotspots", {}),
        )
    return specs
