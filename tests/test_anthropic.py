"""
Comprehensive tests for Anthropic (Claude) integration with StackSense
"""

import pytest
from unittest.mock import Mock, MagicMock
from stacksense.core.client import StackSense
from stacksense.monitoring.tracker import MetricsTracker


class MockAnthropicUsage:
    """Mock Anthropic usage object."""

    def __init__(self, input_tokens=100, output_tokens=50):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class MockAnthropicContent:
    """Mock Anthropic content block."""

    def __init__(self, text="This is Claude's response.", type="text"):
        self.text = text
        self.type = type


class MockAnthropicMessage:
    """Mock Anthropic message response."""

    def __init__(
        self,
        content="Test response from Claude",
        input_tokens=100,
        output_tokens=50,
        model="claude-3-5-sonnet-20241022"
    ):
        self.id = "msg_test123"
        self.type = "message"
        self.role = "assistant"
        self.content = [MockAnthropicContent(text=content)]
        self.model = model
        self.stop_reason = "end_turn"
        self.usage = MockAnthropicUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )


class MockAnthropicMessages:
    """Mock Anthropic messages API."""

    def __init__(self):
        self.call_count = 0

    def create(self, model="claude-3-5-sonnet-20241022", messages=None, max_tokens=1024, **kwargs):
        """Mock create message."""
        self.call_count += 1

        # Calculate approximate tokens
        message_text = ""
        if messages:
            for msg in messages:
                message_text += msg.get("content", "")

        input_tokens = max(10, len(message_text) // 4)
        output_tokens = max(20, max_tokens // 20)

        return MockAnthropicMessage(
            content="This is a helpful response from Claude.",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model
        )


class MockAnthropicClient:
    """Mock Anthropic client for testing."""

    def __init__(self):
        self.messages = MockAnthropicMessages()


def test_anthropic_provider_detection():
    """Test that Anthropic client is properly detected."""
    ss = StackSense(api_key="test_key", project_id="test_project")

    mock_client = Mock()
    mock_client.__class__.__module__ = "anthropic.resources"

    provider = ss._detect_provider(mock_client)
    assert provider == "anthropic"


def test_anthropic_message_tracking(stacksense_client):
    """Test tracking Anthropic message completions."""
    mock_client = MockAnthropicClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="anthropic")

    # Create message
    response = monitored_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": "Hello Claude, how are you today?"}
        ]
    )

    # Verify response
    assert response is not None
    assert response.content[0].text is not None

    # Verify tracking
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["provider"] == "anthropic"
    assert "claude" in event["model"].lower()
    assert event["success"] is True
    assert event["tokens"]["input"] > 0
    assert event["tokens"]["output"] > 0
    assert event["cost"] > 0


def test_anthropic_claude_sonnet(stacksense_client):
    """Test tracking Claude 3.5 Sonnet."""
    mock_client = MockAnthropicClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="anthropic")

    response = monitored_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Test Sonnet"}]
    )

    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert "sonnet" in event["model"].lower()


def test_anthropic_claude_opus(stacksense_client):
    """Test tracking Claude 3 Opus (most capable/expensive)."""
    mock_client = MockAnthropicClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="anthropic")

    response = monitored_client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=2048,
        messages=[{"role": "user", "content": "Test Opus"}]
    )

    events = stacksense_client.tracker.get_events()
    event = events[-1]

    assert "claude-3-opus" in event["model"]


def test_anthropic_claude_haiku(stacksense_client):
    """Test tracking Claude 3 Haiku (fastest/cheapest)."""
    mock_client = MockAnthropicClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="anthropic")

    response = monitored_client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=512,
        messages=[{"role": "user", "content": "Test Haiku"}]
    )

    events = stacksense_client.tracker.get_events()
    event = events[-1]

    assert "claude-3-haiku" in event["model"]


def test_anthropic_multiple_messages(stacksense_client):
    """Test tracking multiple Anthropic message calls."""
    mock_client = MockAnthropicClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="anthropic")

    num_calls = 5
    for i in range(num_calls):
        monitored_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": f"Message {i}"}]
        )

    # Verify all tracked
    events = stacksense_client.tracker.get_events()
    anthropic_events = [e for e in events if e.get("provider") == "anthropic"]
    assert len(anthropic_events) >= num_calls

    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["anthropic"]["calls"] >= num_calls


def test_anthropic_cost_calculation_sonnet(settings, temp_db):
    """Test cost calculation for Claude 3.5 Sonnet."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    # Claude 3.5 Sonnet: $3/1M input, $15/1M output
    tracker.track_call(
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
        tokens={"input": 1000, "output": 500},
        latency=1000.0,
        success=True
    )

    metrics = tracker.get_metrics()
    # Expected: (1000/1M * $3) + (500/1M * $15) = $0.003 + $0.0075 = $0.0105
    expected_cost = 0.0105
    assert abs(metrics["total_cost"] - expected_cost) < 0.001


def test_anthropic_cost_calculation_opus(settings, temp_db):
    """Test cost calculation for Claude 3 Opus."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    # Claude 3 Opus: $15/1M input, $75/1M output
    tracker.track_call(
        provider="anthropic",
        model="claude-3-opus-20240229",
        tokens={"input": 1000, "output": 500},
        latency=2000.0,
        success=True
    )

    metrics = tracker.get_metrics()
    # Expected: (1000/1M * $15) + (500/1M * $75) = $0.015 + $0.0375 = $0.0525
    expected_cost = 0.0525
    assert abs(metrics["total_cost"] - expected_cost) < 0.001


def test_anthropic_cost_calculation_haiku(settings, temp_db):
    """Test cost calculation for Claude 3 Haiku."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    # Claude 3 Haiku: $0.25/1M input, $1.25/1M output
    tracker.track_call(
        provider="anthropic",
        model="claude-3-haiku-20240307",
        tokens={"input": 1000, "output": 500},
        latency=500.0,
        success=True
    )

    metrics = tracker.get_metrics()
    # Expected: (1000/1M * $0.25) + (500/1M * $1.25) = $0.00025 + $0.000625 = $0.000875
    expected_cost = 0.000875
    assert abs(metrics["total_cost"] - expected_cost) < 0.0001


def test_anthropic_error_tracking(stacksense_client):
    """Test tracking Anthropic errors."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "anthropic.resources"

    # Create mock that raises error
    mock_messages = Mock()
    mock_messages.create = Mock(side_effect=Exception("Invalid API key"))
    mock_client.messages = mock_messages

    monitored_client = stacksense_client.monitor(mock_client, provider="anthropic")

    # Attempt call that will fail
    with pytest.raises(Exception, match="Invalid API key"):
        monitored_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": "test"}]
        )

    # Verify error tracked
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["success"] is False
    assert "Invalid API key" in event["error"]

    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["anthropic"]["errors"] >= 1


def test_anthropic_latency_tracking(stacksense_client):
    """Test latency tracking for Anthropic calls."""
    mock_client = MockAnthropicClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="anthropic")

    monitored_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{"role": "user", "content": "test"}]
    )

    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["latency"] > 0

    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["anthropic"]["total_latency"] > 0


def test_anthropic_multi_turn_conversation(stacksense_client):
    """Test tracking multi-turn conversation."""
    mock_client = MockAnthropicClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="anthropic")

    # Multi-turn conversation
    response = monitored_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2048,
        messages=[
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language..."},
            {"role": "user", "content": "Can you give me an example?"}
        ]
    )

    events = stacksense_client.tracker.get_events()
    event = events[-1]

    # Should track input tokens from all messages
    assert event["tokens"]["input"] > 0


def test_anthropic_system_prompt(stacksense_client):
    """Test tracking with system prompt."""
    mock_client = MockAnthropicClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="anthropic")

    response = monitored_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        system="You are a helpful coding assistant specialized in Python.",
        messages=[{"role": "user", "content": "Write a function"}]
    )

    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1


def test_anthropic_long_context(stacksense_client):
    """Test tracking with long context (Claude supports 200K tokens)."""
    mock_client = MockAnthropicClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="anthropic")

    # Simulate long context
    long_content = "This is a long document. " * 500

    response = monitored_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        messages=[{"role": "user", "content": long_content}]
    )

    events = stacksense_client.tracker.get_events()
    event = events[-1]

    # Should have many input tokens
    assert event["tokens"]["input"] > 500


def test_anthropic_with_database_persistence(settings, temp_db):
    """Test Anthropic events persisted to database."""
    from stacksense.database.models import Event as EventModel

    client = StackSense(
        api_key="test_key",
        project_id="test_project",
        environment="test"
    )
    client.db_manager = temp_db
    client.tracker.db_manager = temp_db

    mock_client = MockAnthropicClient()
    monitored_client = client.monitor(mock_client, provider="anthropic")

    monitored_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{"role": "user", "content": "test"}]
    )

    # Verify in database
    with temp_db.get_session() as session:
        events = session.query(EventModel).filter(
            EventModel.provider == "anthropic"
        ).all()

        assert len(events) >= 1
        event = events[-1]
        assert event.provider == "anthropic"
        assert event.success is True


def test_anthropic_analytics_integration(stacksense_client):
    """Test analytics with Anthropic data."""
    mock_client = MockAnthropicClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="anthropic")

    # Generate activity
    for i in range(8):
        monitored_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": f"Query {i}"}]
        )

    metrics = stacksense_client.get_metrics()
    assert "total_calls" in metrics
    assert metrics["total_calls"] >= 8

    cost_breakdown = stacksense_client.get_cost_breakdown()
    assert "anthropic" in cost_breakdown
    assert cost_breakdown["anthropic"] > 0


def test_anthropic_max_tokens_variations(stacksense_client):
    """Test with different max_tokens settings."""
    mock_client = MockAnthropicClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="anthropic")

    max_tokens_values = [256, 512, 1024, 2048, 4096]

    for max_tokens in max_tokens_values:
        monitored_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": "test"}]
        )

    events = stacksense_client.tracker.get_events()
    anthropic_events = [e for e in events if e.get("provider") == "anthropic"]
    assert len(anthropic_events) >= len(max_tokens_values)


@pytest.mark.parametrize("model,input_tokens,output_tokens", [
    ("claude-3-5-sonnet-20241022", 1000, 500),
    ("claude-3-opus-20240229", 1000, 500),
    ("claude-3-haiku-20240307", 1000, 500),
])
def test_anthropic_cost_comparison(settings, temp_db, model, input_tokens, output_tokens):
    """Test cost comparison across different Claude models."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    tracker.track_call(
        provider="anthropic",
        model=model,
        tokens={"input": input_tokens, "output": output_tokens},
        latency=100.0,
        success=True
    )

    metrics = tracker.get_metrics()
    cost = metrics["total_cost"]

    # Opus should be most expensive
    if "opus" in model:
        assert cost > 0.04
    # Haiku should be cheapest
    elif "haiku" in model:
        assert cost < 0.002
    # Sonnet in the middle
    else:
        assert 0.005 < cost < 0.02


def test_anthropic_streaming_disabled(stacksense_client):
    """Test that non-streaming messages are tracked."""
    mock_client = MockAnthropicClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="anthropic")

    response = monitored_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{"role": "user", "content": "test"}],
        stream=False
    )

    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1


def test_anthropic_temperature_variations(stacksense_client):
    """Test with different temperature settings."""
    mock_client = MockAnthropicClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="anthropic")

    temperatures = [0.0, 0.5, 1.0]

    for temp in temperatures:
        monitored_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            temperature=temp,
            messages=[{"role": "user", "content": "test"}]
        )

    events = stacksense_client.tracker.get_events()
    anthropic_events = [e for e in events if e.get("provider") == "anthropic"]
    assert len(anthropic_events) >= len(temperatures)


def test_anthropic_concurrent_requests_simulation(stacksense_client):
    """Test tracking multiple concurrent-like requests."""
    mock_client = MockAnthropicClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="anthropic")

    # Simulate rapid requests
    for i in range(15):
        monitored_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": f"Request {i}"}]
        )

    # All should be tracked
    events = stacksense_client.tracker.get_events()
    anthropic_events = [e for e in events if e.get("provider") == "anthropic"]
    assert len(anthropic_events) >= 15

    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["anthropic"]["calls"] >= 15


def test_anthropic_zero_output_tokens(stacksense_client):
    """Test edge case with minimal output."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "anthropic.resources"

    # Mock response with minimal tokens
    mock_response = MockAnthropicMessage(
        content="",
        input_tokens=10,
        output_tokens=1
    )

    mock_messages = Mock()
    mock_messages.create = Mock(return_value=mock_response)
    mock_client.messages = mock_messages

    monitored_client = stacksense_client.monitor(mock_client, provider="anthropic")

    response = monitored_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1,
        messages=[{"role": "user", "content": "Hi"}]
    )

    events = stacksense_client.tracker.get_events()
    event = events[-1]

    assert event["tokens"]["input"] >= 0
    assert event["tokens"]["output"] >= 0
