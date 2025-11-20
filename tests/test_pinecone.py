"""
Tests for Pinecone integration with StackSense
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from stacksense.core.client import StackSense
from stacksense.monitoring.tracker import MetricsTracker


class MockPineconeResponse:
    """Mock Pinecone query response."""

    def __init__(self, matches=None, namespace=""):
        self.matches = matches or []
        self.namespace = namespace


class MockPineconeIndex:
    """Mock Pinecone Index for testing."""

    def __init__(self):
        self.vectors = []
        self._query_count = 0
        self._upsert_count = 0

    def query(self, vector=None, top_k=10, namespace="", include_metadata=False, **kwargs):
        """Mock query operation."""
        self._query_count += 1
        matches = [
            {"id": f"vec-{i}", "score": 0.9 - (i * 0.1), "metadata": {}}
            for i in range(min(top_k, 5))
        ]
        return MockPineconeResponse(matches=matches, namespace=namespace)

    def upsert(self, vectors, namespace="", **kwargs):
        """Mock upsert operation."""
        self._upsert_count += 1
        self.vectors.extend(vectors)
        return {"upserted_count": len(vectors)}

    def delete(self, ids=None, delete_all=False, namespace="", **kwargs):
        """Mock delete operation."""
        if delete_all:
            deleted = len(self.vectors)
            self.vectors = []
            return {"deleted_count": deleted}
        elif ids:
            return {"deleted_count": len(ids)}
        return {"deleted_count": 0}

    def describe_index_stats(self):
        """Mock index stats."""
        return {
            "dimension": 1536,
            "index_fullness": 0.5,
            "total_vector_count": len(self.vectors),
            "namespaces": {}
        }


def test_pinecone_provider_detection():
    """Test that Pinecone client is properly detected."""
    ss = StackSense(api_key="test_key", project_id="test_project")

    # Create a mock Pinecone client
    mock_pinecone_client = Mock()
    mock_pinecone_client.__class__.__module__ = "pinecone.grpc"

    provider = ss._detect_provider(mock_pinecone_client)
    assert provider == "pinecone"


def test_pinecone_query_tracking(stacksense_client):
    """Test that Pinecone queries are properly tracked."""
    # Create mock Pinecone index
    mock_index = MockPineconeIndex()

    # Monitor the Pinecone index
    monitored_index = stacksense_client.monitor(mock_index, provider="pinecone")

    # Perform a query
    query_vector = [0.1] * 1536
    result = monitored_index.query(
        vector=query_vector,
        top_k=10,
        namespace="test-namespace",
        include_metadata=True
    )

    # Verify query executed
    assert result is not None
    assert len(result.matches) > 0

    # Verify tracking
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    # Check the latest event
    event = events[-1]
    assert event["provider"] == "pinecone"
    assert event["success"] is True
    assert event["tokens"]["queries"] == 1
    assert event["cost"] > 0  # Should have calculated cost


def test_pinecone_upsert_tracking(stacksense_client):
    """Test that Pinecone upsert operations are tracked."""
    mock_index = MockPineconeIndex()
    monitored_index = stacksense_client.monitor(mock_index, provider="pinecone")

    # Perform an upsert
    vectors = [
        ("vec-1", [0.1] * 1536, {"text": "test 1"}),
        ("vec-2", [0.2] * 1536, {"text": "test 2"}),
        ("vec-3", [0.3] * 1536, {"text": "test 3"}),
    ]

    result = monitored_index.upsert(vectors=vectors, namespace="test")

    # Verify upsert executed
    assert result["upserted_count"] == 3

    # Verify tracking
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["provider"] == "pinecone"
    assert event["success"] is True


def test_pinecone_multiple_queries(stacksense_client):
    """Test tracking multiple Pinecone queries."""
    mock_index = MockPineconeIndex()
    monitored_index = stacksense_client.monitor(mock_index, provider="pinecone")

    # Perform multiple queries
    query_vector = [0.1] * 1536
    num_queries = 5

    for i in range(num_queries):
        monitored_index.query(vector=query_vector, top_k=10)

    # Verify all queries were tracked
    events = stacksense_client.tracker.get_events()
    pinecone_events = [e for e in events if e.get("provider") == "pinecone"]
    assert len(pinecone_events) >= num_queries

    # Verify metrics aggregation
    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["pinecone"]["calls"] >= num_queries


def test_pinecone_cost_calculation(settings, temp_db):
    """Test Pinecone cost calculation."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    # Track a Pinecone query
    tracker.track_call(
        provider="pinecone",
        model="default",
        tokens={"queries": 1},
        latency=50.0,
        success=True
    )

    # Verify cost calculation
    metrics = tracker.get_metrics()
    assert metrics["total_cost"] > 0
    assert metrics["by_provider"]["pinecone"]["cost"] > 0

    # Pinecone pricing is $0.0001 per query
    expected_cost = 0.0001
    assert abs(metrics["by_provider"]["pinecone"]["cost"] - expected_cost) < 0.00001


def test_pinecone_multiple_queries_cost(settings, temp_db):
    """Test cost calculation for multiple Pinecone queries."""
    tracker = MetricsTracker(settings=settings, db_manager=temp_db)

    num_queries = 100

    # Track multiple queries
    for _ in range(num_queries):
        tracker.track_call(
            provider="pinecone",
            model="default",
            tokens={"queries": 1},
            latency=50.0,
            success=True
        )

    # Verify total cost
    metrics = tracker.get_metrics()
    expected_cost = num_queries * 0.0001  # $0.0001 per query
    assert abs(metrics["total_cost"] - expected_cost) < 0.0001


def test_pinecone_error_tracking(stacksense_client):
    """Test tracking Pinecone errors."""
    mock_index = Mock()
    mock_index.__class__.__module__ = "pinecone.grpc"

    # Make query raise an exception
    mock_index.query = Mock(side_effect=Exception("Connection timeout"))

    monitored_index = stacksense_client.monitor(mock_index, provider="pinecone")

    # Attempt query that will fail
    with pytest.raises(Exception, match="Connection timeout"):
        monitored_index.query(vector=[0.1] * 1536, top_k=10)

    # Verify error was tracked
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["success"] is False
    assert "Connection timeout" in event["error"]

    # Verify error count in metrics
    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["pinecone"]["errors"] >= 1


def test_pinecone_latency_tracking(stacksense_client):
    """Test latency tracking for Pinecone operations."""
    mock_index = MockPineconeIndex()
    monitored_index = stacksense_client.monitor(mock_index, provider="pinecone")

    # Perform query
    monitored_index.query(vector=[0.1] * 1536, top_k=10)

    # Verify latency was tracked
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["latency"] > 0  # Should have some latency

    # Verify latency in aggregated metrics
    metrics = stacksense_client.tracker.get_metrics()
    assert metrics["by_provider"]["pinecone"]["total_latency"] > 0


def test_pinecone_with_database_persistence(settings, temp_db):
    """Test that Pinecone events are persisted to database."""
    from stacksense.database.models import Event as EventModel

    # Create client with database
    client = StackSense(
        api_key="test_key",
        project_id="test_project",
        environment="test"
    )
    client.db_manager = temp_db
    client.tracker.db_manager = temp_db

    mock_index = MockPineconeIndex()
    monitored_index = client.monitor(mock_index, provider="pinecone")

    # Perform query
    monitored_index.query(vector=[0.1] * 1536, top_k=5)

    # Verify event in database
    with temp_db.get_session() as session:
        events = session.query(EventModel).filter(
            EventModel.provider == "pinecone"
        ).all()

        assert len(events) >= 1
        event = events[-1]
        assert event.provider == "pinecone"
        assert event.success is True
        assert event.cost > 0


def test_pinecone_analytics_integration(stacksense_client):
    """Test analytics with Pinecone data."""
    mock_index = MockPineconeIndex()
    monitored_index = stacksense_client.monitor(mock_index, provider="pinecone")

    # Generate some activity
    for _ in range(10):
        monitored_index.query(vector=[0.1] * 1536, top_k=5)

    # Get metrics through client
    metrics = stacksense_client.get_metrics()

    assert "total_calls" in metrics
    assert metrics["total_calls"] >= 10

    # Get cost breakdown
    cost_breakdown = stacksense_client.get_cost_breakdown()
    assert "pinecone" in cost_breakdown
    assert cost_breakdown["pinecone"] > 0


def test_pinecone_namespace_handling(stacksense_client):
    """Test that namespace information is tracked in metadata."""
    mock_index = MockPineconeIndex()
    monitored_index = stacksense_client.monitor(mock_index, provider="pinecone")

    # Query with specific namespace
    namespace = "production-vectors"
    monitored_index.query(
        vector=[0.1] * 1536,
        top_k=10,
        namespace=namespace
    )

    # Verify tracking
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1


def test_pinecone_batch_operations(stacksense_client):
    """Test tracking batch operations."""
    mock_index = MockPineconeIndex()
    monitored_index = stacksense_client.monitor(mock_index, provider="pinecone")

    # Perform batch upsert
    vectors = [(f"vec-{i}", [0.1 * i] * 1536, {"index": i}) for i in range(100)]
    result = monitored_index.upsert(vectors=vectors)

    # Verify operation completed
    assert result["upserted_count"] == 100

    # Verify tracking
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["provider"] == "pinecone"
    assert event["success"] is True


@pytest.mark.parametrize("operation,method_name", [
    ("query", "query"),
    ("upsert", "upsert"),
    ("delete", "delete"),
])
def test_pinecone_different_operations(stacksense_client, operation, method_name):
    """Test tracking different Pinecone operations."""
    mock_index = MockPineconeIndex()
    monitored_index = stacksense_client.monitor(mock_index, provider="pinecone")

    # Execute operation
    if operation == "query":
        monitored_index.query(vector=[0.1] * 1536, top_k=10)
    elif operation == "upsert":
        monitored_index.upsert(vectors=[("vec-1", [0.1] * 1536, {})])
    elif operation == "delete":
        monitored_index.delete(ids=["vec-1"])

    # Verify tracking
    events = stacksense_client.tracker.get_events()
    assert len(events) >= 1

    event = events[-1]
    assert event["provider"] == "pinecone"
    assert event["metadata"]["method"] == method_name
