"""
Tests for Replicate integration with StackSense
"""

import pytest
from unittest.mock import Mock
from stacksense.core.client import StackSense
from stacksense.monitoring.tracker import MetricsTracker


class MockReplicateMetrics:
    """Mock Replicate metrics object."""

    def __init__(self, input_token_count=100, output_token_count=50):
        self.input_token_count = input_token_count
        self.output_token_count = output_token_count
        self.predict_time = 1.5


class MockReplicatePrediction:
    """Mock Replicate prediction response."""

    def __init__(self, output="Replicate response.", input_tokens=100, output_tokens=50):
        self.id = "pred-replicate-test123"
        self.model = "meta/meta-llama-3-70b-instruct"
        self.status = "succeeded"
        self.output = output
        self.metrics = MockReplicateMetrics(
            input_token_count=input_tokens, output_token_count=output_tokens
        )


class MockReplicatePredictions:
    """Mock Replicate predictions object."""

    def __init__(self):
        self.call_count = 0

    def create(self, model="meta/meta-llama-3-70b-instruct", input=None, **kwargs):
        self.call_count += 1
        prompt = ""
        if input and isinstance(input, dict):
            prompt = input.get("prompt", "")
        input_tokens = max(10, len(prompt) // 4)
        return MockReplicatePrediction(
            output="Replicate model response.",
            input_tokens=input_tokens,
            output_tokens=50,
        )


class MockReplicateModels:
    """Mock Replicate models object."""

    def __init__(self):
        self.predictions = MockReplicatePredictions()


class MockReplicateClient:
    """Mock Replicate client for testing."""

    def __init__(self):
        self.predictions = MockReplicatePredictions()


def test_replicate_provider_detection():
    """Test that Replicate client is properly detected."""
    ss = StackSense(api_key="test_key", project_id="test_project")
    mock_client = Mock()
    mock_client.__class__.__module__ = "replicate.client"
    provider = ss._detect_provider(mock_client)
    assert provider == "replicate"


def test_replicate_prediction_tracking(stacksense_client):
    """Test tracking Replicate predictions."""
    mock_client = MockReplicateClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="replicate")

    response = monitored_client.predictions.create(
        model="meta/meta-llama-3-70b-instruct",
        input={"prompt": "Hello from Replicate!"},
    )

    assert response is not None
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["provider"] == "replicate"
    assert event["success"] is True
    assert event["tokens"]["input"] > 0
    assert event["tokens"]["output"] > 0


def test_replicate_multiple_calls(stacksense_client):
    """Test tracking multiple Replicate calls."""
    mock_client = MockReplicateClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="replicate")

    for i in range(5):
        monitored_client.predictions.create(
            model="meta/meta-llama-3-70b-instruct",
            input={"prompt": f"Message {i}"},
        )

    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["replicate"]["calls"] >= 5


def test_replicate_cost_calculation_llama_70b(settings, temp_db):
    """Test cost calculation for Llama 3 70B on Replicate."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    # meta/meta-llama-3-70b-instruct: $0.65/1M input, $2.75/1M output
    tracker.track_call(
        provider="replicate",
        model="meta/meta-llama-3-70b-instruct",
        tokens={"input": 1000, "output": 500},
        latency=2000.0,
        success=True,
    )

    metrics = tracker.get_metrics()
    # Expected: (1000/1M * $0.65) + (500/1M * $2.75) = $0.00065 + $0.001375 = $0.002025
    expected_cost = 0.002025
    assert abs(metrics["total_cost"] - expected_cost) < 0.001


def test_replicate_cost_calculation_llama_8b(settings, temp_db):
    """Test cost calculation for Llama 3 8B on Replicate."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    tracker.track_call(
        provider="replicate",
        model="meta/meta-llama-3-8b-instruct",
        tokens={"input": 1000, "output": 500},
        latency=500.0,
        success=True,
    )

    metrics = tracker.get_metrics()
    # Expected: (1000/1M * $0.05) + (500/1M * $0.25) = $0.00005 + $0.000125 = $0.000175
    expected_cost = 0.000175
    assert abs(metrics["total_cost"] - expected_cost) < 0.0001


def test_replicate_default_pricing(settings, temp_db):
    """Test default pricing for unknown Replicate models."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    tracker.track_call(
        provider="replicate",
        model="some-custom/model",
        tokens={"input": 1000, "output": 500},
        latency=1000.0,
        success=True,
    )

    metrics = tracker.get_metrics()
    # Expected: (1000/1M * $0.30) + (500/1M * $1.05) = $0.0003 + $0.000525 = $0.000825
    expected_cost = 0.000825
    assert abs(metrics["total_cost"] - expected_cost) < 0.0005


def test_replicate_error_tracking(stacksense_client):
    """Test tracking Replicate errors."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "replicate.client"

    mock_predictions = Mock()
    mock_predictions.create = Mock(side_effect=Exception("Model not found"))
    mock_client.predictions = mock_predictions

    monitored_client = stacksense_client.monitor(mock_client, provider="replicate")

    with pytest.raises(Exception, match="Model not found"):
        monitored_client.predictions.create(
            model="nonexistent/model",
            input={"prompt": "test"},
        )

    events = stacksense_client.tracker.get_events()
    event = events[-1]
    assert event["success"] is False
    assert "Model not found" in event["error"]


def test_replicate_latency_tracking(stacksense_client):
    """Test latency tracking for Replicate calls."""
    mock_client = MockReplicateClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="replicate")

    monitored_client.predictions.create(
        model="meta/meta-llama-3-70b-instruct",
        input={"prompt": "test"},
    )

    events = stacksense_client.tracker.get_events()
    event = events[-1]
    assert event["latency"] > 0


def test_replicate_analytics_integration(stacksense_client):
    """Test analytics with Replicate data."""
    mock_client = MockReplicateClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="replicate")

    for i in range(8):
        monitored_client.predictions.create(
            model="meta/meta-llama-3-70b-instruct",
            input={"prompt": f"Query {i}"},
        )

    cost_breakdown = stacksense_client.get_cost_breakdown()
    assert "replicate" in cost_breakdown
    assert cost_breakdown["replicate"] > 0
