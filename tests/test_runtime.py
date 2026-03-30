
from mobility_os.runtime.runtime import MobilityRuntime

def test_runtime_step_generates_record():
    rt = MobilityRuntime("corridor_congestion", seed=42)
    rec = rt.step()
    assert rec.step_id == 1
    assert rec.scenario == "corridor_congestion"
    assert rec.decision_route in {"CLASSICAL", "QUANTUM", "FALLBACK_CLASSICAL"}
