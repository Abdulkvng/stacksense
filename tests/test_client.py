"""
Tests for StackSense client
"""

import pytest
from stacksense.core.client import StackSense


def test_client_initialization(stacksense_client):
    """Test client initialization."""
    assert stacksense_client is not None
    assert stacksense_client.settings is not None
    assert stacksense_client.tracker is not None
    assert stacksense_client.analytics is not None


def test_client_context_manager(settings, temp_db):
    """Test client as context manager."""
    with StackSense(
        api_key="test_key",
        project_id="test_project",
        environment="test"
    ) as client:
        client.db_manager = temp_db
        assert client is not None
    
    # Context manager should flush on exit


def test_get_metrics(stacksense_client, tracker):
    """Test getting metrics from client."""
    # Add some events
    tracker.track_call(
        provider="openai",
        model="gpt-4",
        tokens={"input": 10, "output": 20},
        latency=1000.0,
        success=True
    )
    
    metrics = stacksense_client.get_metrics()
    assert "total_calls" in metrics
    assert "total_cost" in metrics


def test_get_cost_breakdown(stacksense_client, tracker):
    """Test getting cost breakdown from client."""
    tracker.track_call(
        provider="openai",
        model="gpt-4",
        tokens={"input": 1000, "output": 500},
        latency=1000.0,
        success=True
    )
    
    breakdown = stacksense_client.get_cost_breakdown()
    assert isinstance(breakdown, dict)


def test_track_event(stacksense_client):
    """Test tracking custom event from client."""
    stacksense_client.track_event(
        event_type="test_event",
        provider="test",
        metadata={"key": "value"}
    )
    
    events = stacksense_client.tracker.get_events()
    assert len(events) == 1
    assert events[0]["type"] == "test_event"

