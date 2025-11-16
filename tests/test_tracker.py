"""
Tests for MetricsTracker
"""

import pytest
from datetime import datetime
from stacksense.monitoring.tracker import MetricsTracker


def test_tracker_initialization(tracker):
    """Test tracker initialization."""
    assert tracker is not None
    assert tracker.settings is not None
    assert len(tracker.get_events()) == 0


def test_track_call(tracker):
    """Test tracking an API call."""
    tracker.track_call(
        provider="openai",
        model="gpt-4",
        tokens={"input": 10, "output": 20},
        latency=1250.5,
        success=True
    )
    
    events = tracker.get_events()
    assert len(events) == 1
    assert events[0]["provider"] == "openai"
    assert events[0]["model"] == "gpt-4"
    assert events[0]["total_tokens"] == 30
    assert events[0]["latency"] == 1250.5
    assert events[0]["success"] is True


def test_track_call_with_error(tracker):
    """Test tracking a failed API call."""
    tracker.track_call(
        provider="openai",
        model="gpt-4",
        tokens=None,
        latency=500.0,
        success=False,
        error="Rate limit exceeded"
    )
    
    events = tracker.get_events()
    assert len(events) == 1
    assert events[0]["success"] is False
    assert events[0]["error"] == "Rate limit exceeded"


def test_cost_calculation(tracker):
    """Test cost calculation."""
    # Test OpenAI GPT-4 pricing
    tokens = {"input": 1000, "output": 500}
    cost = tracker._calculate_cost("openai", "gpt-4", tokens)
    assert cost > 0
    # GPT-4: $30/1M input, $60/1M output
    # Expected: (1000/1M * 30) + (500/1M * 60) = 0.03 + 0.03 = 0.06
    expected = (1000 / 1_000_000 * 30) + (500 / 1_000_000 * 60)
    assert abs(cost - expected) < 0.0001


def test_get_metrics(tracker):
    """Test getting aggregated metrics."""
    # Track multiple calls
    for i in range(5):
        tracker.track_call(
            provider="openai",
            model="gpt-4",
            tokens={"input": 10, "output": 20},
            latency=1000.0,
            success=True
        )
    
    metrics = tracker.get_metrics()
    assert metrics["total_calls"] == 5
    assert metrics["total_tokens"] == 150  # 5 * 30
    assert "by_provider" in metrics
    assert "openai" in metrics["by_provider"]


def test_track_event(tracker):
    """Test tracking a custom event."""
    tracker.track_event(
        event_type="custom_event",
        provider="system",
        metadata={"key": "value"}
    )
    
    events = tracker.get_events()
    assert len(events) == 1
    assert events[0]["type"] == "custom_event"
    assert events[0]["provider"] == "system"


def test_flush(tracker):
    """Test flushing events."""
    tracker.track_call(
        provider="openai",
        model="gpt-4",
        tokens={"input": 10, "output": 20},
        latency=1000.0,
        success=True
    )
    
    assert len(tracker.get_events()) == 1
    tracker.flush()
    # Events should be cleared from memory (but remain in database)
    assert len(tracker.get_events()) == 0


def test_reset(tracker):
    """Test resetting metrics."""
    tracker.track_call(
        provider="openai",
        model="gpt-4",
        tokens={"input": 10, "output": 20},
        latency=1000.0,
        success=True
    )
    
    metrics_before = tracker.get_metrics()
    assert metrics_before["total_calls"] > 0
    
    tracker.reset()
    
    metrics_after = tracker.get_metrics()
    assert metrics_after["total_calls"] == 0
    assert metrics_after["total_tokens"] == 0
    assert metrics_after["total_cost"] == 0.0

