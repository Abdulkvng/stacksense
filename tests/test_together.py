"""
Tests for Together AI integration with StackSense
"""

import pytest
from unittest.mock import Mock
from stacksense.core.client import StackSense
from stacksense.monitoring.tracker import MetricsTracker


class MockTogetherUsage:
    """Mock Together AI usage object."""

    def __init__(self, prompt_tokens=100, completion_tokens=50):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens


class MockTogetherChoice:
    """Mock Together AI choice object."""

    def __init__(self, text="Together AI response."):
        self.index = 0
        self.message = MockTogetherMessage(content=text)
        self.finish_reason = "stop"


class MockTogetherMessage:
    """Mock Together AI message object."""

    def __init__(self, content="Test response", role="assistant"):
        self.content = content
        self.role = role


class MockTogetherChatCompletion:
    """Mock Together AI chat completion response."""

    def __init__(self, content="Test response", prompt_tokens=100, completion_tokens=50):
        self.id = "cmpl-together-test123"
        self.model = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
        self.choices = [MockTogetherChoice(text=content)]
        self.usage = MockTogetherUsage(
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        )


class MockTogetherCompletions:
    """Mock Together completions object."""

    def __init__(self):
        self.call_count = 0

    def create(self, model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", messages=None, **kwargs):
        self.call_count += 1
        message_text = ""
        if messages:
            for msg in messages:
                message_text += msg.get("content", "")
        prompt_tokens = max(10, len(message_text) // 4)
        return MockTogetherChatCompletion(
            content="Together AI response.",
            prompt_tokens=prompt_tokens,
            completion_tokens=50,
        )


class MockTogetherChat:
    """Mock Together chat object."""

    def __init__(self):
        self.completions = MockTogetherCompletions()


class MockTogetherClient:
    """Mock Together AI client for testing."""

    def __init__(self):
        self.chat = MockTogetherChat()


def test_together_provider_detection():
    """Test that Together AI client is properly detected."""
    ss = StackSense(api_key="test_key", project_id="test_project")
    mock_client = Mock()
    mock_client.__class__.__module__ = "together.resources"
    provider = ss._detect_provider(mock_client)
    assert provider == "together"


def test_together_chat_completion_tracking(stacksense_client):
    """Test tracking Together AI chat completions."""
    mock_client = MockTogetherClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="together")

    response = monitored_client.chat.completions.create(
        model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        messages=[{"role": "user", "content": "Hello Llama!"}],
    )

    assert response is not None
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["provider"] == "together"
    assert event["success"] is True
    assert event["tokens"]["input"] > 0
    assert event["tokens"]["output"] > 0
    assert event["cost"] > 0


def test_together_multiple_calls(stacksense_client):
    """Test tracking multiple Together AI calls."""
    mock_client = MockTogetherClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="together")

    for i in range(5):
        monitored_client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
            messages=[{"role": "user", "content": f"Message {i}"}],
        )

    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["together"]["calls"] >= 5


def test_together_cost_calculation_llama_405b(settings, temp_db):
    """Test cost calculation for Llama 3.1 405B on Together."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    tracker.track_call(
        provider="together",
        model="meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
        tokens={"input": 1000, "output": 500},
        latency=1000.0,
        success=True,
    )

    metrics = tracker.get_metrics()
    # Expected: (1000/1M * $3.50) + (500/1M * $3.50) = $0.0035 + $0.00175 = $0.00525
    expected_cost = 0.00525
    assert abs(metrics["total_cost"] - expected_cost) < 0.001


def test_together_cost_calculation_llama_8b(settings, temp_db):
    """Test cost calculation for Llama 3.1 8B on Together."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    tracker.track_call(
        provider="together",
        model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        tokens={"input": 1000, "output": 500},
        latency=200.0,
        success=True,
    )

    metrics = tracker.get_metrics()
    # Expected: (1000/1M * $0.18) + (500/1M * $0.18) = $0.00018 + $0.00009 = $0.00027
    expected_cost = 0.00027
    assert abs(metrics["total_cost"] - expected_cost) < 0.0001


def test_together_error_tracking(stacksense_client):
    """Test tracking Together AI errors."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "together.resources"

    mock_chat = Mock()
    mock_completions = Mock()
    mock_completions.create = Mock(side_effect=Exception("API key invalid"))
    mock_chat.completions = mock_completions
    mock_client.chat = mock_chat

    monitored_client = stacksense_client.monitor(mock_client, provider="together")

    with pytest.raises(Exception, match="API key invalid"):
        monitored_client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
            messages=[{"role": "user", "content": "test"}],
        )

    events = stacksense_client.tracker.get_events()
    event = events[-1]
    assert event["success"] is False


def test_together_latency_tracking(stacksense_client):
    """Test latency tracking for Together AI calls."""
    mock_client = MockTogetherClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="together")

    monitored_client.chat.completions.create(
        model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        messages=[{"role": "user", "content": "test"}],
    )

    events = stacksense_client.tracker.get_events()
    event = events[-1]
    assert event["latency"] > 0


def test_together_analytics_integration(stacksense_client):
    """Test analytics with Together AI data."""
    mock_client = MockTogetherClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="together")

    for i in range(8):
        monitored_client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
            messages=[{"role": "user", "content": f"Query {i}"}],
        )

    cost_breakdown = stacksense_client.get_cost_breakdown()
    assert "together" in cost_breakdown
    assert cost_breakdown["together"] > 0
