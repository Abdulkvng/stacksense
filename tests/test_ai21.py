"""
Tests for AI21 Labs (Jamba) integration with StackSense
"""

import pytest
from unittest.mock import Mock
from stacksense.core.client import StackSense
from stacksense.monitoring.tracker import MetricsTracker


class MockAI21Usage:
    """Mock AI21 usage object."""

    def __init__(self, prompt_tokens=100, completion_tokens=50):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class MockAI21Choice:
    """Mock AI21 choice object."""

    def __init__(self, text="This is a Jamba response."):
        self.index = 0
        self.message = MockAI21Message(content=text)
        self.finish_reason = "stop"


class MockAI21Message:
    """Mock AI21 message object."""

    def __init__(self, content="Test response", role="assistant"):
        self.content = content
        self.role = role


class MockAI21ChatCompletion:
    """Mock AI21 chat completion response."""

    def __init__(self, content="Test response", prompt_tokens=100, completion_tokens=50):
        self.id = "cmpl-ai21-test123"
        self.model = "jamba-1.5-mini"
        self.choices = [MockAI21Choice(text=content)]
        self.usage = MockAI21Usage(
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        )


class MockAI21Completions:
    """Mock AI21 completions object."""

    def __init__(self):
        self.call_count = 0

    def create(self, model="jamba-1.5-mini", messages=None, **kwargs):
        self.call_count += 1
        message_text = ""
        if messages:
            for msg in messages:
                message_text += msg.get("content", "")
        prompt_tokens = max(10, len(message_text) // 4)
        return MockAI21ChatCompletion(
            content="Jamba response.",
            prompt_tokens=prompt_tokens,
            completion_tokens=50,
        )


class MockAI21Chat:
    """Mock AI21 chat object."""

    def __init__(self):
        self.completions = MockAI21Completions()


class MockAI21Client:
    """Mock AI21 client for testing."""

    def __init__(self):
        self.chat = MockAI21Chat()


def test_ai21_provider_detection():
    """Test that AI21 client is properly detected."""
    ss = StackSense(api_key="test_key", project_id="test_project")
    mock_client = Mock()
    mock_client.__class__.__module__ = "ai21.resources"
    provider = ss._detect_provider(mock_client)
    assert provider == "ai21"


def test_ai21_chat_completion_tracking(stacksense_client):
    """Test tracking AI21 chat completions."""
    mock_client = MockAI21Client()
    monitored_client = stacksense_client.monitor(mock_client, provider="ai21")

    response = monitored_client.chat.completions.create(
        model="jamba-1.5-mini",
        messages=[{"role": "user", "content": "Hello Jamba!"}],
    )

    assert response is not None
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["provider"] == "ai21"
    assert event["model"] == "jamba-1.5-mini"
    assert event["success"] is True
    assert event["tokens"]["input"] > 0
    assert event["tokens"]["output"] > 0
    assert event["cost"] > 0


def test_ai21_multiple_calls(stacksense_client):
    """Test tracking multiple AI21 calls."""
    mock_client = MockAI21Client()
    monitored_client = stacksense_client.monitor(mock_client, provider="ai21")

    for i in range(5):
        monitored_client.chat.completions.create(
            model="jamba-1.5-mini",
            messages=[{"role": "user", "content": f"Message {i}"}],
        )

    events = stacksense_client.tracker.get_events()
    ai21_events = [e for e in events if e.get("provider") == "ai21"]
    assert len(ai21_events) >= 5

    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["ai21"]["calls"] >= 5


def test_ai21_cost_calculation_jamba_large(settings, temp_db):
    """Test cost calculation for Jamba 1.5 Large."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    # Jamba 1.5 Large: $2/1M input, $8/1M output
    tracker.track_call(
        provider="ai21",
        model="jamba-1.5-large",
        tokens={"input": 1000, "output": 500},
        latency=1000.0,
        success=True,
    )

    metrics = tracker.get_metrics()
    # Expected: (1000/1M * $2) + (500/1M * $8) = $0.002 + $0.004 = $0.006
    expected_cost = 0.006
    assert abs(metrics["total_cost"] - expected_cost) < 0.001


def test_ai21_cost_calculation_jamba_mini(settings, temp_db):
    """Test cost calculation for Jamba 1.5 Mini."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    # Jamba 1.5 Mini: $0.20/1M input, $0.40/1M output
    tracker.track_call(
        provider="ai21",
        model="jamba-1.5-mini",
        tokens={"input": 1000, "output": 500},
        latency=500.0,
        success=True,
    )

    metrics = tracker.get_metrics()
    # Expected: (1000/1M * $0.20) + (500/1M * $0.40) = $0.0002 + $0.0002 = $0.0004
    expected_cost = 0.0004
    assert abs(metrics["total_cost"] - expected_cost) < 0.0001


def test_ai21_error_tracking(stacksense_client):
    """Test tracking AI21 errors."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "ai21.resources"

    mock_chat = Mock()
    mock_completions = Mock()
    mock_completions.create = Mock(side_effect=Exception("Rate limit exceeded"))
    mock_chat.completions = mock_completions
    mock_client.chat = mock_chat

    monitored_client = stacksense_client.monitor(mock_client, provider="ai21")

    with pytest.raises(Exception, match="Rate limit exceeded"):
        monitored_client.chat.completions.create(
            model="jamba-1.5-mini",
            messages=[{"role": "user", "content": "test"}],
        )

    events = stacksense_client.tracker.get_events()
    event = events[-1]
    assert event["success"] is False
    assert "Rate limit exceeded" in event["error"]


def test_ai21_latency_tracking(stacksense_client):
    """Test latency tracking for AI21 calls."""
    mock_client = MockAI21Client()
    monitored_client = stacksense_client.monitor(mock_client, provider="ai21")

    monitored_client.chat.completions.create(
        model="jamba-1.5-mini",
        messages=[{"role": "user", "content": "test"}],
    )

    events = stacksense_client.tracker.get_events()
    event = events[-1]
    assert event["latency"] > 0


@pytest.mark.parametrize(
    "model",
    ["jamba-1.5-large", "jamba-1.5-mini", "jamba-instruct"],
)
def test_ai21_different_models(settings, temp_db, model):
    """Test cost calculation for different AI21 models."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    tracker.track_call(
        provider="ai21",
        model=model,
        tokens={"input": 1000, "output": 500},
        latency=100.0,
        success=True,
    )

    metrics = tracker.get_metrics()
    assert metrics["total_cost"] > 0
