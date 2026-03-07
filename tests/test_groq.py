"""
Tests for Groq integration with StackSense
"""

import pytest
from unittest.mock import Mock
from stacksense.core.client import StackSense
from stacksense.monitoring.tracker import MetricsTracker


class MockGroqUsage:
    """Mock Groq usage object."""

    def __init__(self, prompt_tokens=100, completion_tokens=50):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens


class MockGroqChoice:
    """Mock Groq choice object."""

    def __init__(self, text="Groq response."):
        self.index = 0
        self.message = MockGroqMessage(content=text)
        self.finish_reason = "stop"


class MockGroqMessage:
    """Mock Groq message object."""

    def __init__(self, content="Test response", role="assistant"):
        self.content = content
        self.role = role


class MockGroqChatCompletion:
    """Mock Groq chat completion response."""

    def __init__(self, content="Test response", prompt_tokens=100, completion_tokens=50):
        self.id = "cmpl-groq-test123"
        self.model = "llama-3.3-70b-versatile"
        self.choices = [MockGroqChoice(text=content)]
        self.usage = MockGroqUsage(
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        )


class MockGroqCompletions:
    """Mock Groq completions object."""

    def __init__(self):
        self.call_count = 0

    def create(self, model="llama-3.3-70b-versatile", messages=None, **kwargs):
        self.call_count += 1
        message_text = ""
        if messages:
            for msg in messages:
                message_text += msg.get("content", "")
        prompt_tokens = max(10, len(message_text) // 4)
        return MockGroqChatCompletion(
            content="Groq fast response.",
            prompt_tokens=prompt_tokens,
            completion_tokens=50,
        )


class MockGroqChat:
    """Mock Groq chat object."""

    def __init__(self):
        self.completions = MockGroqCompletions()


class MockGroqClient:
    """Mock Groq client for testing."""

    def __init__(self):
        self.chat = MockGroqChat()


def test_groq_provider_detection():
    """Test that Groq client is properly detected."""
    ss = StackSense(api_key="test_key", project_id="test_project")
    mock_client = Mock()
    mock_client.__class__.__module__ = "groq.resources"
    provider = ss._detect_provider(mock_client)
    assert provider == "groq"


def test_groq_chat_completion_tracking(stacksense_client):
    """Test tracking Groq chat completions."""
    mock_client = MockGroqClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="groq")

    response = monitored_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "Hello from Groq!"}],
    )

    assert response is not None
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["provider"] == "groq"
    assert event["model"] == "llama-3.3-70b-versatile"
    assert event["success"] is True
    assert event["tokens"]["input"] > 0
    assert event["tokens"]["output"] > 0
    assert event["cost"] > 0


def test_groq_multiple_calls(stacksense_client):
    """Test tracking multiple Groq calls."""
    mock_client = MockGroqClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="groq")

    for i in range(5):
        monitored_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": f"Message {i}"}],
        )

    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["groq"]["calls"] >= 5


def test_groq_cost_calculation_llama_70b(settings, temp_db):
    """Test cost calculation for Llama 3.3 70B on Groq."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    # llama-3.3-70b-versatile: $0.59/1M input, $0.79/1M output
    tracker.track_call(
        provider="groq",
        model="llama-3.3-70b-versatile",
        tokens={"input": 1000, "output": 500},
        latency=100.0,
        success=True,
    )

    metrics = tracker.get_metrics()
    # Expected: (1000/1M * $0.59) + (500/1M * $0.79) = $0.00059 + $0.000395 = $0.000985
    expected_cost = 0.000985
    assert abs(metrics["total_cost"] - expected_cost) < 0.0001


def test_groq_cost_calculation_llama_8b(settings, temp_db):
    """Test cost calculation for Llama 3.1 8B on Groq."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    # llama-3.1-8b-instant: $0.05/1M input, $0.08/1M output
    tracker.track_call(
        provider="groq",
        model="llama-3.1-8b-instant",
        tokens={"input": 1000, "output": 500},
        latency=50.0,
        success=True,
    )

    metrics = tracker.get_metrics()
    # Expected: (1000/1M * $0.05) + (500/1M * $0.08) = $0.00005 + $0.00004 = $0.00009
    expected_cost = 0.00009
    assert abs(metrics["total_cost"] - expected_cost) < 0.00005


def test_groq_cost_calculation_mixtral(settings, temp_db):
    """Test cost calculation for Mixtral on Groq."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    tracker.track_call(
        provider="groq",
        model="mixtral-8x7b-32768",
        tokens={"input": 1000, "output": 500},
        latency=80.0,
        success=True,
    )

    metrics = tracker.get_metrics()
    # Expected: (1000/1M * $0.24) + (500/1M * $0.24) = $0.00024 + $0.00012 = $0.00036
    expected_cost = 0.00036
    assert abs(metrics["total_cost"] - expected_cost) < 0.0001


def test_groq_error_tracking(stacksense_client):
    """Test tracking Groq errors."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "groq.resources"

    mock_chat = Mock()
    mock_completions = Mock()
    mock_completions.create = Mock(side_effect=Exception("Service unavailable"))
    mock_chat.completions = mock_completions
    mock_client.chat = mock_chat

    monitored_client = stacksense_client.monitor(mock_client, provider="groq")

    with pytest.raises(Exception, match="Service unavailable"):
        monitored_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "test"}],
        )

    events = stacksense_client.tracker.get_events()
    event = events[-1]
    assert event["success"] is False
    assert "Service unavailable" in event["error"]


def test_groq_latency_tracking(stacksense_client):
    """Test latency tracking for Groq calls."""
    mock_client = MockGroqClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="groq")

    monitored_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "test"}],
    )

    events = stacksense_client.tracker.get_events()
    event = events[-1]
    assert event["latency"] > 0


@pytest.mark.parametrize(
    "model",
    ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
)
def test_groq_different_models(settings, temp_db, model):
    """Test cost calculation for different Groq models."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    tracker.track_call(
        provider="groq",
        model=model,
        tokens={"input": 1000, "output": 500},
        latency=100.0,
        success=True,
    )

    metrics = tracker.get_metrics()
    assert metrics["total_cost"] > 0


def test_groq_analytics_integration(stacksense_client):
    """Test analytics with Groq data."""
    mock_client = MockGroqClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="groq")

    for i in range(10):
        monitored_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": f"Query {i}"}],
        )

    cost_breakdown = stacksense_client.get_cost_breakdown()
    assert "groq" in cost_breakdown
    assert cost_breakdown["groq"] > 0
