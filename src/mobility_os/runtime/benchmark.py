
from __future__ import annotations

from dataclasses import asdict
from typing import Iterable, List
import pandas as pd

from mobility_os.runtime.runtime import MobilityRuntime


def benchmark_runs(scenarios: Iterable[str], seeds: Iterable[int], steps: int = 48) -> pd.DataFrame:
    rows: List[dict] = []
    for scenario in scenarios:
        for seed in seeds:
            rt = MobilityRuntime(scenario=scenario, seed=seed)
            for _ in range(steps):
                rt.step()
            df = rt.dataframe()
            rows.append({
                "scenario": scenario,
                "seed": seed,
                "steps": steps,
                "avg_operational_score": float(df["step_operational_score"].mean()),
                "avg_exec_ms": float(df["exec_ms"].mean()),
                "quantum_share": float((df["decision_route"] == "QUANTUM").mean()),
                "fallback_share": float(df["fallback_triggered"].mean()),
                "avg_risk": float(df["risk_score"].mean()),
            })
    return pd.DataFrame(rows)
