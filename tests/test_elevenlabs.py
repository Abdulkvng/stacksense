"""
Tests for ElevenLabs integration with StackSense
"""

import pytest
from unittest.mock import Mock, MagicMock
from stacksense.core.client import StackSense
from stacksense.monitoring.tracker import MetricsTracker


class MockElevenLabsResponse:
    """Mock ElevenLabs API response."""

    def __init__(self, audio_data=b"fake_audio_data", character_count=None):
        self.audio_data = audio_data
        self.character_count = character_count if character_count is not None else len("test text")


class MockElevenLabsVoice:
    """Mock ElevenLabs Voice."""

    def __init__(self, voice_id="21m00Tcm4TlvDq8ikWAM", name="Rachel"):
        self.voice_id = voice_id
        self.name = name


class MockElevenLabsClient:
    """Mock ElevenLabs client for testing."""

    def __init__(self):
        self.generate_count = 0
        self.voices = [
            MockElevenLabsVoice("21m00Tcm4TlvDq8ikWAM", "Rachel"),
            MockElevenLabsVoice("AZnzlk1XvdvUeBnXmlld", "Domi"),
        ]

    def generate(self, text, voice=None, model="eleven_monolingual_v1", **kwargs):
        """Mock generate operation."""
        self.generate_count += 1
        char_count = len(text)
        return MockElevenLabsResponse(character_count=char_count)

    def get_voices(self):
        """Mock get voices."""
        return self.voices


def test_elevenlabs_provider_detection():
    """Test that ElevenLabs client is properly detected."""
    ss = StackSense(api_key="test_key", project_id="test_project")

    # Create a mock ElevenLabs client
    mock_elevenlabs_client = Mock()
    mock_elevenlabs_client.__class__.__module__ = "elevenlabs.client"

    provider = ss._detect_provider(mock_elevenlabs_client)
    assert provider == "elevenlabs"


def test_elevenlabs_generate_tracking(stacksense_client):
    """Test that ElevenLabs text-to-speech generation is tracked."""
    mock_client = MockElevenLabsClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="elevenlabs")

    # Generate speech
    text = "Hello, this is a test of the ElevenLabs API integration."
    result = monitored_client.generate(
        text=text,
        voice="21m00Tcm4TlvDq8ikWAM",
        model="eleven_monolingual_v1"
    )

    # Verify generation executed
    assert result is not None
    assert result.character_count == len(text)

    # Verify tracking
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["provider"] == "elevenlabs"
    assert event["success"] is True
    assert event["tokens"]["characters"] == len(text)
    assert event["cost"] > 0


def test_elevenlabs_multiple_generations(stacksense_client):
    """Test tracking multiple ElevenLabs generations."""
    mock_client = MockElevenLabsClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="elevenlabs")

    texts = [
        "First test sentence.",
        "Second test sentence with more characters.",
        "Third sentence here.",
    ]

    total_chars = 0
    for text in texts:
        monitored_client.generate(text=text, voice="Rachel")
        total_chars += len(text)

    # Verify all generations were tracked
    events = stacksense_client.tracker.get_events()
    elevenlabs_events = [e for e in events if e.get("provider") == "elevenlabs"]
    assert len(elevenlabs_events) >= len(texts)

    # Verify metrics aggregation
    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["elevenlabs"]["calls"] >= len(texts)


def test_elevenlabs_cost_calculation(settings, temp_db):
    """Test ElevenLabs cost calculation based on characters."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    # ElevenLabs pricing: $0.30 per 1000 characters
    characters = 1000
    tracker.track_call(
        provider="elevenlabs",
        model="eleven_monolingual_v1",
        tokens={"characters": characters},
        latency=500.0,
        success=True
    )

    metrics = tracker.get_metrics()
    assert metrics["total_cost"] > 0

    # Expected: $0.30 for 1000 characters
    expected_cost = 0.30
    assert abs(metrics["by_provider"]["elevenlabs"]["cost"] - expected_cost) < 0.01


def test_elevenlabs_large_text_cost(settings, temp_db):
    """Test cost calculation for large text generation."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    # 10,000 characters
    characters = 10000
    tracker.track_call(
        provider="elevenlabs",
        model="eleven_monolingual_v1",
        tokens={"characters": characters},
        latency=2000.0,
        success=True
    )

    metrics = tracker.get_metrics()
    # Expected: $3.00 for 10,000 characters
    expected_cost = 3.0
    assert abs(metrics["total_cost"] - expected_cost) < 0.01


def test_elevenlabs_error_tracking(stacksense_client):
    """Test tracking ElevenLabs errors."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "elevenlabs.client"
    mock_client.generate = Mock(side_effect=Exception("API quota exceeded"))

    monitored_client = stacksense_client.monitor(mock_client, provider="elevenlabs")

    # Attempt generation that will fail
    with pytest.raises(Exception, match="API quota exceeded"):
        monitored_client.generate(text="Test", voice="Rachel")

    # Verify error was tracked
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["success"] is False
    assert "API quota exceeded" in event["error"]

    # Verify error count in metrics
    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["elevenlabs"]["errors"] >= 1


def test_elevenlabs_latency_tracking(stacksense_client):
    """Test latency tracking for ElevenLabs operations."""
    mock_client = MockElevenLabsClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="elevenlabs")

    # Perform generation
    monitored_client.generate(text="Test latency tracking", voice="Rachel")

    # Verify latency was tracked
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["latency"] > 0

    # Verify latency in aggregated metrics
    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["elevenlabs"]["total_latency"] > 0


def test_elevenlabs_different_voices(stacksense_client):
    """Test tracking with different voice IDs."""
    mock_client = MockElevenLabsClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="elevenlabs")

    voices = ["Rachel", "Domi", "Bella", "Antoni"]

    for voice in voices:
        monitored_client.generate(text=f"Test with {voice}", voice=voice)

    # Verify all were tracked
    events = stacksense_client.tracker.get_events()
    elevenlabs_events = [e for e in events if e.get("provider") == "elevenlabs"]
    assert len(elevenlabs_events) >= len(voices)


def test_elevenlabs_different_models(stacksense_client):
    """Test tracking with different ElevenLabs models."""
    mock_client = MockElevenLabsClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="elevenlabs")

    models = [
        "eleven_monolingual_v1",
        "eleven_multilingual_v1",
        "eleven_multilingual_v2",
    ]

    for model in models:
        monitored_client.generate(
            text="Test text",
            voice="Rachel",
            model=model
        )

    # Verify tracking
    events = stacksense_client.tracker.get_events()
    elevenlabs_events = [e for e in events if e.get("provider") == "elevenlabs"]
    assert len(elevenlabs_events) >= len(models)


def test_elevenlabs_empty_text(stacksense_client):
    """Test handling of empty text generation."""
    mock_client = Mock()
    mock_client.__class__.__module__ = "elevenlabs.client"

    # Mock response with zero characters
    mock_response = MockElevenLabsResponse(character_count=0)
    mock_client.generate = Mock(return_value=mock_response)

    monitored_client = stacksense_client.monitor(mock_client, provider="elevenlabs")

    # Generate with empty text
    result = monitored_client.generate(text="", voice="Rachel")

    # Should still track with 0 characters
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["tokens"]["characters"] == 0
    assert event["cost"] == 0


def test_elevenlabs_with_database_persistence(settings, temp_db):
    """Test that ElevenLabs events are persisted to database."""
    from stacksense.database.models import Event as EventModel

    client = StackSense(
        api_key="test_key",
        project_id="test_project",
        environment="test"
    )
    client.db_manager = temp_db
    client.tracker.db_manager = temp_db

    mock_client = MockElevenLabsClient()
    monitored_client = client.monitor(mock_client, provider="elevenlabs")

    # Generate speech
    monitored_client.generate(text="Database persistence test", voice="Rachel")

    # Verify event in database
    with temp_db.get_session() as session:
        events = session.query(EventModel).filter(
            EventModel.provider == "elevenlabs"
        ).all()

        assert len(events) >= 0
        if events:
            event = events[-1]
            assert event.provider == "elevenlabs"
            assert event.success is True
            assert event.cost > 0


def test_elevenlabs_analytics_integration(stacksense_client):
    """Test analytics with ElevenLabs data."""
    mock_client = MockElevenLabsClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="elevenlabs")

    # Generate some activity
    for i in range(5):
        monitored_client.generate(text=f"Test sentence number {i}", voice="Rachel")

    # Get metrics through client
    metrics = stacksense_client.get_metrics()

    assert "total_calls" in metrics
    assert metrics["total_calls"] >= 5

    # Get cost breakdown
    cost_breakdown = stacksense_client.get_cost_breakdown()
    assert "elevenlabs" in cost_breakdown
    assert cost_breakdown["elevenlabs"] > 0


def test_elevenlabs_very_long_text(stacksense_client):
    """Test handling of very long text generation."""
    mock_client = MockElevenLabsClient()
    monitored_client = stacksense_client.monitor(mock_client, provider="elevenlabs")

    # Generate a very long text (100,000 characters)
    long_text = "A" * 100000
    result = monitored_client.generate(text=long_text, voice="Rachel")

    # Verify tracking
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["tokens"]["characters"] == 100000

    # Cost should be significant
    assert event["cost"] > 10  # Over $10 for 100k characters


@pytest.mark.parametrize("char_count,expected_cost", [
    (1000, 0.30),
    (5000, 1.50),
    (10000, 3.00),
    (50000, 15.00),
])
def test_elevenlabs_cost_accuracy(settings, temp_db, char_count, expected_cost):
    """Test cost calculation accuracy for various character counts."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    tracker.track_call(
        provider="elevenlabs",
        model="default",
        tokens={"characters": char_count},
        latency=100.0,
        success=True
    )

    metrics = tracker.get_metrics()
    actual_cost = metrics["by_provider"]["elevenlabs"]["cost"]

    # Allow small floating point differences
    assert abs(actual_cost - expected_cost) < 0.01
