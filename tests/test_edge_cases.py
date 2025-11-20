"""
Edge case tests for StackSense - errors, timeouts, rate limits, and unusual scenarios
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import time
from stacksense.core.client import StackSense
from stacksense.monitoring.tracker import MetricsTracker


class RateLimitError(Exception):
    """Mock rate limit error."""
    pass


class TimeoutError(Exception):
    """Mock timeout error."""
    pass


class AuthenticationError(Exception):
    """Mock authentication error."""
    pass


def test_unknown_provider_detection(stacksense_client):
    """Test handling of unknown provider."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "some_unknown_library"

    provider = stacksense_client._detect_provider(mock_client)
    assert provider == "unknown"


def test_rate_limit_error_tracking(stacksense_client):
    """Test tracking rate limit errors."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "openai.resources"
    mock_client.chat = Mock()
    mock_client.chat.completions = Mock()
    mock_client.chat.completions.create = Mock(
        side_effect=RateLimitError("Rate limit exceeded. Please try again later.")
    )

    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    with pytest.raises(RateLimitError):
        monitored_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "test"}]
        )

    # Verify rate limit error tracked
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["success"] is False
    assert "rate limit" in event["error"].lower()

    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["openai"]["errors"] >= 1


def test_authentication_error_tracking(stacksense_client):
    """Test tracking authentication errors."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "anthropic.resources"
    mock_client.messages = Mock()
    mock_client.messages.create = Mock(
        side_effect=AuthenticationError("Invalid API key")
    )

    monitored_client = stacksense_client.monitor(mock_client, provider="anthropic")

    with pytest.raises(AuthenticationError):
        monitored_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": "test"}]
        )

    events = stacksense_client.tracker.get_events()
    event = events[-1]

    assert event["success"] is False
    assert "api key" in event["error"].lower()


def test_timeout_error_tracking(stacksense_client):
    """Test tracking timeout errors."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "openai.resources"
    mock_client.chat = Mock()
    mock_client.chat.completions = Mock()
    mock_client.chat.completions.create = Mock(
        side_effect=TimeoutError("Request timed out after 60 seconds")
    )

    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    with pytest.raises(TimeoutError):
        monitored_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "test"}]
        )

    events = stacksense_client.tracker.get_events()
    event = events[-1]

    assert event["success"] is False
    assert "timed out" in event["error"].lower() or "timeout" in event["error"].lower()


def test_network_error_tracking(stacksense_client):
    """Test tracking network errors."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "openai.resources"
    mock_client.chat = Mock()
    mock_client.chat.completions = Mock()
    mock_client.chat.completions.create = Mock(
        side_effect=ConnectionError("Failed to establish connection")
    )

    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    with pytest.raises(ConnectionError):
        monitored_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "test"}]
        )

    events = stacksense_client.tracker.get_events()
    event = events[-1]

    assert event["success"] is False
    assert "connection" in event["error"].lower()


def test_invalid_model_error(stacksense_client):
    """Test handling invalid model name."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "openai.resources"
    mock_client.chat = Mock()
    mock_client.chat.completions = Mock()
    mock_client.chat.completions.create = Mock(
        side_effect=ValueError("Invalid model: gpt-999")
    )

    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    with pytest.raises(ValueError):
        monitored_client.chat.completions.create(
            model="gpt-999",
            messages=[{"role": "user", "content": "test"}]
        )

    events = stacksense_client.tracker.get_events()
    event = events[-1]

    assert event["success"] is False


def test_empty_response_handling(stacksense_client):
    """Test handling of empty/null responses."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "openai.resources"

    # Mock response with no usage data
    mock_response = Mock()
    mock_response.usage = None
    mock_response.choices = []

    mock_client.chat = Mock()
    mock_client.chat.completions = Mock()
    mock_client.chat.completions.create = Mock(return_value=mock_response)

    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    response = monitored_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "test"}]
    )

    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    # Should handle gracefully with None tokens
    event = events[-1]
    assert event["success"] is True
    assert event["tokens"] is None or event["tokens"] == {}


def test_malformed_response(stacksense_client):
    """Test handling of malformed API responses."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "anthropic.resources"

    # Mock malformed response
    mock_response = Mock()
    mock_response.usage = "not an object"  # Wrong type
    mock_response.content = None

    mock_client.messages = Mock()
    mock_client.messages.create = Mock(return_value=mock_response)

    monitored_client = stacksense_client.monitor(mock_client, provider="anthropic")

    # Should not crash
    response = monitored_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{"role": "user", "content": "test"}]
    )

    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1


def test_very_large_token_count(settings, temp_db):
    """Test handling very large token counts."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    # Track call with massive token count
    tracker.track_call(
        provider="openai",
        model="gpt-4",
        tokens={"input": 100000, "output": 50000},
        latency=30000.0,
        success=True
    )

    metrics = tracker.get_metrics()
    assert metrics["total_tokens"] == 150000
    assert metrics["total_cost"] > 5.0  # Should be expensive


def test_negative_latency_protection(settings, temp_db):
    """Test protection against negative latency values."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    # Attempt to track with negative latency (shouldn't happen but testing edge case)
    tracker.track_call(
        provider="openai",
        model="gpt-4",
        tokens={"input": 100, "output": 50},
        latency=-100.0,  # Invalid
        success=True
    )

    metrics = tracker.get_metrics()
    # Should still track, even with weird latency
    assert metrics["total_calls"] == 1


def test_concurrent_tracking_safety(stacksense_client):
    """Test that concurrent tracking doesn't cause issues."""
    from threading import Thread

    mock_client = Mock()
    mock_client.__class__.__module__ = "openai.resources"

    def make_call():
        """Simulate API call."""
        stacksense_client.tracker.track_call(
            provider="openai",
            model="gpt-4",
            tokens={"input": 10, "output": 20},
            latency=100.0,
            success=True
        )

    # Create multiple threads
    threads = []
    num_threads = 10

    for _ in range(num_threads):
        thread = Thread(target=make_call)
        threads.append(thread)
        thread.start()

    # Wait for all to complete
    for thread in threads:
        thread.join()

    # All calls should be tracked
    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["total_calls"] >= num_threads


def test_special_characters_in_error_messages(stacksense_client):
    """Test handling errors with special characters."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "openai.resources"
    mock_client.chat = Mock()
    mock_client.chat.completions = Mock()
    mock_client.chat.completions.create = Mock(
        side_effect=Exception("Error with special chars: 你好 émojis 🚀 <html>")
    )

    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    with pytest.raises(Exception):
        monitored_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "test"}]
        )

    events = stacksense_client.tracker.get_events()
    event = events[-1]

    # Should handle special characters in error
    assert event["success"] is False
    assert event["error"] is not None


def test_empty_tokens_dict(settings, temp_db):
    """Test handling empty tokens dictionary."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    tracker.track_call(
        provider="openai",
        model="gpt-4",
        tokens={},  # Empty
        latency=100.0,
        success=True
    )

    metrics = tracker.get_metrics()
    assert metrics["total_calls"] == 1
    assert metrics["total_tokens"] == 0
    assert metrics["total_cost"] == 0


def test_none_tokens(settings, temp_db):
    """Test handling None tokens."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    tracker.track_call(
        provider="openai",
        model="gpt-4",
        tokens=None,
        latency=100.0,
        success=True
    )

    metrics = tracker.get_metrics()
    assert metrics["total_calls"] == 1
    assert metrics["total_tokens"] == 0


def test_missing_model_pricing(settings, temp_db):
    """Test handling model with no pricing data."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    tracker.track_call(
        provider="newprovider",
        model="unknown-model-v1",
        tokens={"input": 1000, "output": 500},
        latency=100.0,
        success=True
    )

    metrics = tracker.get_metrics()
    # Should track but with $0 cost
    assert metrics["total_calls"] == 1
    assert metrics["total_cost"] == 0


def test_rapid_successive_calls(stacksense_client):
    """Test handling rapid successive API calls."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "openai.resources"

    def mock_create(**kwargs):
        return Mock(usage=Mock(prompt_tokens=10, completion_tokens=20))

    mock_client.chat = Mock()
    mock_client.chat.completions = Mock()
    mock_client.chat.completions.create = Mock(side_effect=mock_create)

    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    # Make many rapid calls
    for i in range(50):
        monitored_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": f"msg {i}"}]
        )

    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["total_calls"] >= 50


def test_provider_with_custom_token_field(stacksense_client):
    """Test provider with non-standard token field."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "custom_provider"

    # Response with non-standard fields
    mock_response = Mock()
    mock_response.custom_usage = Mock(tokens_used=100)

    mock_client.generate = Mock(return_value=mock_response)

    monitored_client = stacksense_client.monitor(mock_client, provider="unknown")

    response = monitored_client.generate(prompt="test")

    # Should still track even if tokens not extracted
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1


def test_tracker_reset_functionality(settings, temp_db):
    """Test resetting tracker metrics."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    # Add some data
    for _ in range(5):
        tracker.track_call(
            provider="openai",
            model="gpt-4",
            tokens={"input": 100, "output": 50},
            latency=100.0,
            success=True
        )

    metrics = tracker.get_metrics()
    assert metrics["total_calls"] == 5

    # Reset
    tracker.reset()

    metrics_after = tracker.get_metrics()
    assert metrics_after["total_calls"] == 0
    assert metrics_after["total_tokens"] == 0
    assert metrics_after["total_cost"] == 0


def test_metadata_persistence_with_special_types(settings, temp_db):
    """Test metadata with various data types."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    metadata = {
        "string": "value",
        "number": 42,
        "float": 3.14,
        "boolean": True,
        "none": None,
        "list": [1, 2, 3],
        "nested": {"key": "value"}
    }

    tracker.track_call(
        provider="openai",
        model="gpt-4",
        tokens={"input": 10, "output": 20},
        latency=100.0,
        success=True,
        metadata=metadata
    )

    events = tracker.get_events()
    assert len(events) == 1
    # Metadata should be preserved
    assert events[0]["metadata"] is not None


def test_extremely_long_error_message(stacksense_client):
    """Test handling of very long error messages."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "openai.resources"

    # Very long error message
    long_error = "Error: " + ("x" * 10000)

    mock_client.chat = Mock()
    mock_client.chat.completions = Mock()
    mock_client.chat.completions.create = Mock(side_effect=Exception(long_error))

    monitored_client = stacksense_client.monitor(mock_client, provider="openai")

    with pytest.raises(Exception):
        monitored_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "test"}]
        )

    events = stacksense_client.tracker.get_events()
    event = events[-1]

    # Should handle long error
    assert event["success"] is False
    assert len(event["error"]) > 100


def test_zero_cost_operations(settings, temp_db):
    """Test operations with zero cost (like free tier usage)."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    tracker.track_call(
        provider="free_provider",
        model="free-model",
        tokens={"input": 1000, "output": 500},
        latency=100.0,
        success=True
    )

    metrics = tracker.get_metrics()
    assert metrics["total_calls"] == 1
    assert metrics["total_cost"] == 0  # No cost


def test_multiple_errors_same_provider(stacksense_client):
    """Test tracking multiple errors from same provider."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "openai.resources"

    errors = [
        "Rate limit exceeded",
        "Invalid request",
        "Server error",
        "Timeout",
    ]

    mock_client.chat = Mock()
    mock_client.chat.completions = Mock()

    for error_msg in errors:
        mock_client.chat.completions.create = Mock(side_effect=Exception(error_msg))

        monitored_client = stacksense_client.monitor(mock_client, provider="openai")

        with pytest.raises(Exception):
            monitored_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": "test"}]
            )

    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["openai"]["errors"] >= len(errors)


def test_mixed_success_and_failure(stacksense_client):
    """Test tracking mix of successful and failed calls."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "openai.resources"

    call_results = [
        Mock(usage=Mock(prompt_tokens=10, completion_tokens=20)),
        Exception("Error"),
        Mock(usage=Mock(prompt_tokens=15, completion_tokens=25)),
        Exception("Another error"),
        Mock(usage=Mock(prompt_tokens=20, completion_tokens=30)),
    ]

    for i, result in enumerate(call_results):
        if isinstance(result, Exception):
            mock_client.chat = Mock()
            mock_client.chat.completions = Mock()
            mock_client.chat.completions.create = Mock(side_effect=result)

            monitored_client = stacksense_client.monitor(mock_client, provider="openai")

            with pytest.raises(Exception):
                monitored_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": f"test {i}"}]
                )
        else:
            mock_client.chat = Mock()
            mock_client.chat.completions = Mock()
            mock_client.chat.completions.create = Mock(return_value=result)

            monitored_client = stacksense_client.monitor(mock_client, provider="openai")

            monitored_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": f"test {i}"}]
            )

    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["openai"]["calls"] >= 5
    assert metrics["by_provider"]["openai"]["errors"] >= 2


@pytest.mark.parametrize("invalid_latency", [-1, -100, -9999, float('-inf')])
def test_invalid_latency_values(settings, temp_db, invalid_latency):
    """Test handling of various invalid latency values."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    tracker.track_call(
        provider="openai",
        model="gpt-4",
        tokens={"input": 10, "output": 20},
        latency=invalid_latency,
        success=True
    )

    # Should not crash
    metrics = tracker.get_metrics()
    assert metrics["total_calls"] == 1
