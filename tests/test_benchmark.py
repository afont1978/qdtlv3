
from mobility_os.runtime.benchmark import benchmark_runs

def test_benchmark_runs():
    df = benchmark_runs(["corridor_congestion"], [42], steps=4)
    assert len(df) == 1
    assert "avg_operational_score" in df.columns
