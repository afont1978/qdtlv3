
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Optional

from mobility_os.domain.models import Hotspot


def default_hotspot_paths(explicit_path: Optional[str] = None) -> list[Path]:
    root = Path(__file__).resolve().parents[3]
    candidates: list[Path] = []
    if explicit_path:
        candidates.append(Path(explicit_path))
    candidates.extend([
        root / "data" / "hotspots" / "barcelona_mobility_hotspots.csv",
        Path.cwd() / "data" / "hotspots" / "barcelona_mobility_hotspots.csv",
        Path.cwd() / "barcelona_mobility_hotspots.csv",
    ])
    deduped: list[Path] = []
    seen: set[str] = set()
    for p in candidates:
        key = str(p)
        if key not in seen:
            seen.add(key)
            deduped.append(p)
    return deduped


def load_hotspots(explicit_path: Optional[str] = None) -> Dict[str, Hotspot]:
    for path in default_hotspot_paths(explicit_path):
        if path.exists():
            with path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                out: Dict[str, Hotspot] = {}
                for row in reader:
                    hs = Hotspot(
                        name=row["name"],
                        lat=float(row["lat"]),
                        lon=float(row["lon"]),
                        category=row["category"],
                        streets=row["streets"],
                        why=row["why"],
                    )
                    out[hs.name] = hs
                if out:
                    return out
    return {}
