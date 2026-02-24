"""Smoke test for StackSense without external API keys."""

from stacksense import StackSense


def test_simple_stack_smoke(monkeypatch):
    """Verify core tracking and analytics flows run end-to-end."""
    monkeypatch.setenv("STACKSENSE_ENABLE_DB", "false")

    ss = StackSense(project_id="test-project", environment="development", debug=True)

    for i in range(3):
        ss.tracker.track_call(
            provider="openai",
            model="gpt-4",
            tokens={"input": 100 + i * 10, "output": 50 + i * 5},
            latency=1000 + i * 100,
            success=True,
        )

    ss.track_event(
        event_type="test_event",
        provider="system",
        metadata={"test": True, "timestamp": "2024-01-15"},
    )

    metrics = ss.get_metrics()
    assert metrics["total_calls"] == 3
    assert metrics["total_tokens"] == (100 + 50) + (110 + 55) + (120 + 60)
    assert metrics["total_cost"] >= 0
    assert "openai" in metrics["providers"]

    breakdown = ss.get_cost_breakdown()
    assert "openai" in breakdown
    assert breakdown["openai"] >= 0

    perf = ss.get_performance_stats()
    assert "openai" in perf
    assert perf["openai"]["calls"] == 3

    events = ss.tracker.get_events()
    assert len(events) >= 4
