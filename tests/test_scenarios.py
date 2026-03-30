
from mobility_os.scenarios.loader import load_scenarios

def test_scenarios_load():
    scenarios = load_scenarios()
    assert "corridor_congestion" in scenarios
    assert "compound_extreme_day" in scenarios
    assert scenarios["corridor_congestion"].mode == "traffic"
