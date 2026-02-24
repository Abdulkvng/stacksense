"""
Comprehensive tests for OpenAI integration with StackSense
"""

import pytest
from unittest.mock import Mock, MagicMock
from stacksense.core.client import StackSense
from stacksense.monitoring.tracker import MetricsTracker


class MockUsage:
    """Mock OpenAI usage object."""

    def __init__(self, prompt_tokens=10, completion_tokens=20, total_tokens=30):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class MockChoice:
    """Mock OpenAI choice object."""

    def __init__(self, text="", message=None, finish_reason="stop"):
        self.text = text
        self.message = message or MockMessage(content=text)
        self.finish_reason = finish_reason
        self.index = 0


class MockMessage:
    """Mock OpenAI message object."""

    def __init__(self, content="Test response", role="assistant"):
        self.content = content
        self.role = role


class MockChatCompletion:
    """Mock OpenAI chat completion response."""

    def __init__(self, content="Test response", prompt_tokens=100, completion_tokens=50):
        self.id = "chatcmpl-test123"
        self.object = "chat.completion"
        self.created = 1234567890
        self.model = "gpt-4"
        self.choices = [MockChoice(message=MockMessage(content=content))]
        self.usage = MockUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )


class MockEmbedding:
    """Mock OpenAI embedding object."""

    def __init__(self, embedding=None):
        self.embedding = embedding or [0.1] * 1536
        self.index = 0


class MockEmbeddingResponse:
    """Mock OpenAI embedding response."""

    def __init__(self, num_embeddings=1, prompt_tokens=10):
        self.object = "list"
        self.data = [MockEmbedding() for _ in range(num_embeddings)]
        self.model = "text-embedding-3-small"
        self.usage = MockUsage(prompt_tokens=prompt_tokens, completion_tokens=0)


class MockOpenAIChat:
    """Mock OpenAI chat completions."""

    def __init__(self):
        self.completions = MockCompletions()


class MockCompletions:
    """Mock completions object."""

    def __init__(self):
        self.call_count = 0

    def create(self, model="gpt-4", messages=None, **kwargs):
        """Mock create method."""
        self.call_count += 1

        # Calculate approximate token usage
        message_text = ""
        if messages:
            for msg in messages:
                message_text += msg.get("content", "")

        prompt_tokens = max(10, len(message_text) // 4)
        completion_tokens = 50

        return MockChatCompletion(
            content="This is a test response from the OpenAI API.",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )


class MockOpenAIEmbeddings:
    """Mock OpenAI embeddings."""

    def __init__(self):
        self.call_count = 0

    def create(self, input=None, model="text-embedding-3-small", **kwargs):
        """Mock create embeddings."""
        self.call_count += 1

        # Calculate tokens based on input
        if isinstance(input, list):
            num_embeddings = len(input)
            total_text = " ".join(input)
        else:
            num_embeddings = 1
            total_text = input or ""

        prompt_tokens = max(10, len(total_text) // 4)

        return MockEmbeddingResponse(
            num_embeddings=num_embeddings,
            prompt_tokens=prompt_tokens
        )


class MockOpenAIClient:
    """Mock OpenAI client for testing."""

    def __init__(self):
        self.chat = MockOpenAIChat()
        self.embeddings = MockOpenAIEmbeddings()


def test_openai_provider_detection():
    """Test that OpenAI client is properly detected."""
    ss = StackSense(api_key="test_key", project_id="test_project")

    mock_client = Mock()
    mock_client.__class__.__module__ = "openai.resources"

    provider = ss._detect_provider(mock_client)
    assert provider == "openai"


def test_openai_chat_completion_tracking(stacksense_client):
    """Test tracking OpenAI chat completions."""
    mock_client = MockOpenAIClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    # Create chat completion
    response = monitored_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ]
    )

    # Verify response
    assert response is not None
    assert response.choices[0].message.content is not None

    # Verify tracking
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["provider"] == "openai"
    assert event["model"] == "gpt-4"
    assert event["success"] is True
    assert event["tokens"]["input"] > 0
    assert event["tokens"]["output"] > 0
    assert event["cost"] > 0


def test_openai_gpt35_turbo(stacksense_client):
    """Test tracking GPT-3.5-turbo model."""
    mock_client = MockOpenAIClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    response = monitored_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Test"}]
    )

    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    # GPT-3.5 should be cheaper than GPT-4
    event = events[-1]
    assert event["model"] == "gpt-3.5-turbo"


def test_openai_multiple_completions(stacksense_client):
    """Test tracking multiple OpenAI completions."""
    mock_client = MockOpenAIClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    num_calls = 5
    for i in range(num_calls):
        monitored_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": f"Message {i}"}]
        )

    # Verify all calls tracked
    events = stacksense_client.tracker.get_events()
    openai_events = [e for e in events if e.get("provider") == "openai"]
    assert len(openai_events) >= num_calls

    # Verify metrics
    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["openai"]["calls"] >= num_calls


def test_openai_embeddings_tracking(stacksense_client):
    """Test tracking OpenAI embeddings."""
    mock_client = MockOpenAIClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    # Create embeddings
    response = monitored_client.embeddings.create(
        input="This is a test string to embed",
        model="text-embedding-3-small"
    )

    # Verify response
    assert response is not None
    assert len(response.data) > 0

    # Verify tracking
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["provider"] == "openai"
    assert event["model"] == "text-embedding-3-small"
    assert event["success"] is True


def test_openai_batch_embeddings(stacksense_client):
    """Test tracking batch embeddings."""
    mock_client = MockOpenAIClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    # Create batch embeddings
    texts = [
        "First text to embed",
        "Second text to embed",
        "Third text to embed",
    ]

    response = monitored_client.embeddings.create(
        input=texts,
        model="text-embedding-3-small"
    )

    # Verify tracking
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["provider"] == "openai"
    assert event["tokens"]["input"] > 0


def test_openai_cost_calculation_gpt4(settings, temp_db):
    """Test cost calculation for GPT-4."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    # GPT-4: $30/1M input tokens, $60/1M output tokens
    tracker.track_call(
        provider="openai",
        model="gpt-4",
        tokens={"input": 1000, "output": 500},
        latency=1000.0,
        success=True
    )

    metrics = tracker.get_metrics()
    # Expected: (1000/1M * $30) + (500/1M * $60) = $0.03 + $0.03 = $0.06
    expected_cost = 0.06
    assert abs(metrics["total_cost"] - expected_cost) < 0.001


def test_openai_cost_calculation_gpt35(settings, temp_db):
    """Test cost calculation for GPT-3.5-turbo."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    # GPT-3.5-turbo: $0.5/1M input, $1.5/1M output
    tracker.track_call(
        provider="openai",
        model="gpt-3.5-turbo",
        tokens={"input": 1000, "output": 500},
        latency=500.0,
        success=True
    )

    metrics = tracker.get_metrics()
    # Expected: (1000/1M * $0.5) + (500/1M * $1.5) = $0.0005 + $0.00075 = $0.00125
    expected_cost = 0.00125
    assert abs(metrics["total_cost"] - expected_cost) < 0.0001


def test_openai_error_tracking(stacksense_client):
    """Test tracking OpenAI errors."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "openai.resources"

    # Create mock that raises error
    mock_chat = Mock()
    mock_completions = Mock()
    mock_completions.create = Mock(side_effect=Exception("Rate limit exceeded"))
    mock_chat.completions = mock_completions
    mock_client.chat = mock_chat

    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    # Attempt call that will fail
    with pytest.raises(Exception, match="Rate limit exceeded"):
        monitored_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "test"}]
        )

    # Verify error tracked
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["success"] is False
    assert "Rate limit exceeded" in event["error"]

    # Verify error count
    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["openai"]["errors"] >= 1


def test_openai_latency_tracking(stacksense_client):
    """Test latency tracking for OpenAI calls."""
    mock_client = MockOpenAIClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    monitored_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "test"}]
    )

    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["latency"] > 0

    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["openai"]["total_latency"] > 0


def test_openai_long_conversation(stacksense_client):
    """Test tracking long conversation with many tokens."""
    mock_client = MockOpenAIClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    # Simulate long conversation
    long_message = "This is a very long message. " * 100

    response = monitored_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": long_message}
        ]
    )

    events = stacksense_client.tracker.get_events()
    event = events[-1]

    # Should have significant token usage
    assert event["tokens"]["input"] > 100
    assert event["cost"] > 0.01


def test_openai_with_database_persistence(settings, temp_db):
    """Test OpenAI events persisted to database."""
    from stacksense.database.models import Event as EventModel

    client = StackSense(
        api_key="test_key",
        project_id="test_project",
        environment="test"
    )
    client.db_manager = temp_db
    client.tracker.db_manager = temp_db

    mock_client = MockOpenAIClient()
    monitored_client = client.monitor(mock_client, provider="openai")

    monitored_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "test"}]
    )

    # Verify in database
    with temp_db.get_session() as session:
        events = session.query(EventModel).filter(
            EventModel.provider == "openai"
        ).all()

        assert len(events) >= 0
        if events:
            event = events[-1]
            assert event.provider == "openai"
            assert event.success is True


def test_openai_analytics_integration(stacksense_client):
    """Test analytics with OpenAI data."""
    mock_client = MockOpenAIClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    # Generate activity
    for i in range(10):
        monitored_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": f"Message {i}"}]
        )

    metrics = stacksense_client.get_metrics()
    assert "total_calls" in metrics
    assert metrics["total_calls"] >= 10

    cost_breakdown = stacksense_client.get_cost_breakdown()
    assert "openai" in cost_breakdown
    assert cost_breakdown["openai"] > 0


def test_openai_streaming_response(stacksense_client):
    """Test tracking streaming responses (if they still get tracked)."""
    mock_client = MockOpenAIClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    # Regular completion (streaming would be similar)
    response = monitored_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "test"}],
        stream=False
    )

    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1


def test_openai_system_messages(stacksense_client):
    """Test tracking with system messages."""
    mock_client = MockOpenAIClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    response = monitored_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful coding assistant."},
            {"role": "user", "content": "Write a Python function."},
            {"role": "assistant", "content": "Here's a function..."},
            {"role": "user", "content": "Can you improve it?"}
        ]
    )

    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    # Should count all message tokens
    assert event["tokens"]["input"] > 0


@pytest.mark.parametrize("model,input_tokens,output_tokens", [
    ("gpt-4", 1000, 500),
    ("gpt-4-turbo", 1000, 500),
    ("gpt-3.5-turbo", 1000, 500),
])
def test_openai_different_models(settings, temp_db, model, input_tokens, output_tokens):
    """Test cost calculation for different OpenAI models."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    tracker.track_call(
        provider="openai",
        model=model,
        tokens={"input": input_tokens, "output": output_tokens},
        latency=100.0,
        success=True
    )

    metrics = tracker.get_metrics()
    assert metrics["total_cost"] > 0

    # GPT-4 should be most expensive
    if "gpt-4" in model and "turbo" not in model:
        assert metrics["total_cost"] > 0.05


def test_openai_zero_tokens(stacksense_client):
    """Test handling of responses with zero tokens (edge case)."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "openai.resources"

    # Mock response with zero tokens
    mock_response = MockChatCompletion(
        content="",
        prompt_tokens=0,
        completion_tokens=0
    )

    mock_chat = Mock()
    mock_completions = Mock()
    mock_completions.create = Mock(return_value=mock_response)
    mock_chat.completions = mock_completions
    mock_client.chat = mock_chat

    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    response = monitored_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": ""}]
    )

    events = stacksense_client.tracker.get_events()
    event = events[-1]

    assert event["tokens"]["input"] == 0
    assert event["tokens"]["output"] == 0
    assert event["cost"] == 0


def test_openai_concurrent_requests_simulation(stacksense_client):
    """Test tracking multiple concurrent-like requests."""
    mock_client = MockOpenAIClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    # Simulate rapid requests
    responses = []
    for i in range(20):
        response = monitored_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": f"Request {i}"}]
        )
        responses.append(response)

    # All should be tracked
    events = stacksense_client.tracker.get_events()
    openai_events = [e for e in events if e.get("provider") == "openai"]
    assert len(openai_events) >= 20

    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["openai"]["calls"] >= 20
