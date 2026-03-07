"""
Tests for Perplexity AI integration with StackSense
"""

import pytest
from unittest.mock import Mock
from stacksense.core.client import StackSense
from stacksense.monitoring.tracker import MetricsTracker


class MockPerplexityUsage:
    """Mock Perplexity usage object."""

    def __init__(self, prompt_tokens=100, completion_tokens=50):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens


class MockPerplexityChoice:
    """Mock Perplexity choice object."""

    def __init__(self, text="Perplexity response."):
        self.index = 0
        self.message = MockPerplexityMessage(content=text)
        self.finish_reason = "stop"


class MockPerplexityMessage:
    """Mock Perplexity message object."""

    def __init__(self, content="Test response", role="assistant"):
        self.content = content
        self.role = role


class MockPerplexityChatCompletion:
    """Mock Perplexity chat completion response."""

    def __init__(self, content="Test response", prompt_tokens=100, completion_tokens=50):
        self.id = "cmpl-pplx-test123"
        self.model = "sonar-pro"
        self.choices = [MockPerplexityChoice(text=content)]
        self.usage = MockPerplexityUsage(
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        )
        self.citations = ["https://example.com"]


class MockPerplexityCompletions:
    """Mock Perplexity completions object."""

    def __init__(self):
        self.call_count = 0

    def create(self, model="sonar-pro", messages=None, **kwargs):
        self.call_count += 1
        message_text = ""
        if messages:
            for msg in messages:
                message_text += msg.get("content", "")
        prompt_tokens = max(10, len(message_text) // 4)
        return MockPerplexityChatCompletion(
            content="Perplexity search-augmented response.",
            prompt_tokens=prompt_tokens,
            completion_tokens=50,
        )


class MockPerplexityChat:
    """Mock Perplexity chat object."""

    def __init__(self):
        self.completions = MockPerplexityCompletions()


class MockPerplexityClient:
    """Mock Perplexity client for testing."""

    def __init__(self):
        self.chat = MockPerplexityChat()


def test_perplexity_provider_detection():
    """Test that Perplexity client is properly detected."""
    ss = StackSense(api_key="test_key", project_id="test_project")
    mock_client = Mock()
    mock_client.__class__.__module__ = "perplexity.resources"
    provider = ss._detect_provider(mock_client)
    assert provider == "perplexity"


def test_perplexity_chat_completion_tracking(stacksense_client):
    """Test tracking Perplexity chat completions."""
    mock_client = MockPerplexityClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="perplexity")

    response = monitored_client.chat.completions.create(
        model="sonar-pro",
        messages=[{"role": "user", "content": "What is quantum computing?"}],
    )

    assert response is not None
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["provider"] == "perplexity"
    assert event["model"] == "sonar-pro"
    assert event["success"] is True
    assert event["tokens"]["input"] > 0
    assert event["tokens"]["output"] > 0
    assert event["cost"] > 0


def test_perplexity_multiple_calls(stacksense_client):
    """Test tracking multiple Perplexity calls."""
    mock_client = MockPerplexityClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="perplexity")

    for i in range(5):
        monitored_client.chat.completions.create(
            model="sonar-pro",
            messages=[{"role": "user", "content": f"Search query {i}"}],
        )

    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["perplexity"]["calls"] >= 5


def test_perplexity_cost_calculation_sonar_pro(settings, temp_db):
    """Test cost calculation for Sonar Pro."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    # sonar-pro: $3/1M input, $15/1M output
    tracker.track_call(
        provider="perplexity",
        model="sonar-pro",
        tokens={"input": 1000, "output": 500},
        latency=1500.0,
        success=True,
    )

    metrics = tracker.get_metrics()
    # Expected: (1000/1M * $3) + (500/1M * $15) = $0.003 + $0.0075 = $0.0105
    expected_cost = 0.0105
    assert abs(metrics["total_cost"] - expected_cost) < 0.001


def test_perplexity_cost_calculation_sonar(settings, temp_db):
    """Test cost calculation for Sonar."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    # sonar: $1/1M input, $1/1M output
    tracker.track_call(
        provider="perplexity",
        model="sonar",
        tokens={"input": 1000, "output": 500},
        latency=800.0,
        success=True,
    )

    metrics = tracker.get_metrics()
    # Expected: (1000/1M * $1) + (500/1M * $1) = $0.001 + $0.0005 = $0.0015
    expected_cost = 0.0015
    assert abs(metrics["total_cost"] - expected_cost) < 0.0005


def test_perplexity_error_tracking(stacksense_client):
    """Test tracking Perplexity errors."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "perplexity.resources"

    mock_chat = Mock()
    mock_completions = Mock()
    mock_completions.create = Mock(side_effect=Exception("Invalid API key"))
    mock_chat.completions = mock_completions
    mock_client.chat = mock_chat

    monitored_client = stacksense_client.monitor(mock_client, provider="perplexity")

    with pytest.raises(Exception, match="Invalid API key"):
        monitored_client.chat.completions.create(
            model="sonar-pro",
            messages=[{"role": "user", "content": "test"}],
        )

    events = stacksense_client.tracker.get_events()
    event = events[-1]
    assert event["success"] is False
    assert "Invalid API key" in event["error"]


def test_perplexity_latency_tracking(stacksense_client):
    """Test latency tracking for Perplexity calls."""
    mock_client = MockPerplexityClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="perplexity")

    monitored_client.chat.completions.create(
        model="sonar-pro",
        messages=[{"role": "user", "content": "test"}],
    )

    events = stacksense_client.tracker.get_events()
    event = events[-1]
    assert event["latency"] > 0


@pytest.mark.parametrize(
    "model",
    ["sonar-pro", "sonar", "sonar-reasoning-pro", "sonar-reasoning"],
)
def test_perplexity_different_models(settings, temp_db, model):
    """Test cost calculation for different Perplexity models."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    tracker.track_call(
        provider="perplexity",
        model=model,
        tokens={"input": 1000, "output": 500},
        latency=100.0,
        success=True,
    )

    metrics = tracker.get_metrics()
    assert metrics["total_cost"] > 0


def test_perplexity_analytics_integration(stacksense_client):
    """Test analytics with Perplexity data."""
    mock_client = MockPerplexityClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="perplexity")

    for i in range(8):
        monitored_client.chat.completions.create(
            model="sonar-pro",
            messages=[{"role": "user", "content": f"Research query {i}"}],
        )

    cost_breakdown = stacksense_client.get_cost_breakdown()
    assert "perplexity" in cost_breakdown
    assert cost_breakdown["perplexity"] > 0
