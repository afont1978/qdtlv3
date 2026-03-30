
from mobility_os.domain.models import MobilityDispatchProblem
from mobility_os.orchestration.hybrid import MobilityHybridOrchestrator

def test_safety_prefers_classical():
    orch = MobilityHybridOrchestrator(seed=42)
    problem = MobilityDispatchProblem(
        step_id=1,
        mode="safety",
        scenario="school_area_risk",
        objective_name="test",
        constraints={},
        objective_terms={},
        complexity_score=7.0,
        discrete_ratio=0.8,
        horizon_steps=12,
        metadata={"active_event": "school_peak", "risk_score": 0.7, "bus_bunching_index": 0.1, "curb_pressure_index": 0.2, "gateway_delay_index": 0.2},
    )
    route, _ = orch.choose_route(problem)
    assert route == "CLASSICAL"
