"""
Tests for database functionality
"""

import pytest
from datetime import datetime
from stacksense.database.models import Event
from stacksense.database.connection import DatabaseManager


def test_database_connection(temp_db):
    """Test database connection."""
    assert temp_db is not None
    assert temp_db.health_check() is True


def test_create_tables(temp_db):
    """Test table creation."""
    # Tables should already be created by fixture
    with temp_db.get_session() as session:
        # Try to query events table
        result = session.query(Event).limit(1).all()
        assert isinstance(result, list)


def test_insert_event(temp_db):
    """Test inserting an event."""
    with temp_db.get_session() as session:
        event = Event(
            timestamp=datetime.utcnow(),
            project_id="test_project",
            environment="test",
            provider="openai",
            model="gpt-4",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            cost=0.001,
            latency=1000.0,
            success=True
        )
        session.add(event)
        session.commit()
        
        # Verify insertion
        events = session.query(Event).filter(
            Event.project_id == "test_project"
        ).all()
        assert len(events) == 1
        assert events[0].provider == "openai"
        assert events[0].total_tokens == 30


def test_query_events(temp_db):
    """Test querying events."""
    # Insert test events
    with temp_db.get_session() as session:
        for i in range(5):
            event = Event(
                timestamp=datetime.utcnow(),
                project_id="test_project",
                environment="test",
                provider="openai",
                model="gpt-4",
                total_tokens=30,
                cost=0.001,
                success=True
            )
            session.add(event)
        session.commit()
    
    # Query events
    with temp_db.get_session() as session:
        events = session.query(Event).filter(
            Event.project_id == "test_project"
        ).all()
        assert len(events) == 5


def test_event_to_dict(temp_db):
    """Test event to_dict method."""
    with temp_db.get_session() as session:
        event = Event(
            timestamp=datetime.utcnow(),
            project_id="test_project",
            environment="test",
            provider="openai",
            model="gpt-4",
            total_tokens=30,
            cost=0.001,
            success=True
        )
        session.add(event)
        session.commit()
        
        event_dict = event.to_dict()
        assert isinstance(event_dict, dict)
        assert "provider" in event_dict
        assert "model" in event_dict
        assert event_dict["provider"] == "openai"

