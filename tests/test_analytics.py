"""
Tests for Analytics
"""

import pytest
from stacksense.analytics.analyzer import Analytics


def test_analytics_initialization(analytics):
    """Test analytics initialization."""
    assert analytics is not None
    assert analytics.tracker is not None


def test_get_summary(analytics, tracker):
    """Test getting metrics summary."""
    # Add some events
    for i in range(10):
        tracker.track_call(
            provider="openai",
            model="gpt-4",
            tokens={"input": 10, "output": 20},
            latency=1000.0,
            success=True
        )
    
    summary = analytics.get_summary()
    assert summary["total_calls"] == 10
    assert summary["total_tokens"] > 0
    assert summary["total_cost"] >= 0
    assert "avg_latency" in summary
    assert "error_rate" in summary


def test_get_cost_breakdown(analytics, tracker):
    """Test getting cost breakdown by provider."""
    # Add events from different providers
    tracker.track_call(
        provider="openai",
        model="gpt-4",
        tokens={"input": 1000, "output": 500},
        latency=1000.0,
        success=True
    )
    
    tracker.track_call(
        provider="anthropic",
        model="claude-3-5-sonnet",
        tokens={"input": 1000, "output": 500},
        latency=1000.0,
        success=True
    )
    
    breakdown = analytics.get_cost_breakdown()
    assert "openai" in breakdown
    assert "anthropic" in breakdown
    assert breakdown["openai"] > 0
    assert breakdown["anthropic"] > 0


def test_get_performance_stats(analytics, tracker):
    """Test getting performance statistics."""
    # Add events with different latencies
    for latency in [100, 200, 300]:
        tracker.track_call(
            provider="openai",
            model="gpt-4",
            tokens={"input": 10, "output": 20},
            latency=latency,
            success=True
        )
    
    stats = analytics.get_performance_stats()
    assert "openai" in stats
    assert stats["openai"]["calls"] == 3
    assert stats["openai"]["avg_latency"] > 0
    assert stats["openai"]["errors"] == 0


def test_get_summary_with_timeframe(analytics, tracker):
    """Test getting summary with timeframe filter."""
    tracker.track_call(
        provider="openai",
        model="gpt-4",
        tokens={"input": 10, "output": 20},
        latency=1000.0,
        success=True
    )
    
    summary = analytics.get_summary(timeframe="1h")
    assert "total_calls" in summary
    assert summary["total_calls"] >= 0


def test_get_top_models(analytics, tracker):
    """Test getting top models."""
    # Add events with different models
    models = ["gpt-4", "gpt-3.5-turbo", "gpt-4"]
    for model in models:
        tracker.track_call(
            provider="openai",
            model=model,
            tokens={"input": 10, "output": 20},
            latency=1000.0,
            success=True
        )
    
    top_models = analytics.get_top_models(limit=5)
    assert len(top_models) > 0
    assert top_models[0]["model"] in models

