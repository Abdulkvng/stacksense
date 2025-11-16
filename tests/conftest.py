"""
Pytest configuration and fixtures
"""

import pytest
import os
import tempfile
from pathlib import Path

from stacksense.config.settings import Settings
from stacksense.database.connection import DatabaseManager, reset_db_manager
from stacksense.monitoring.tracker import MetricsTracker
from stacksense.analytics.analyzer import Analytics
from stacksense.core.client import StackSense


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()
    
    db_manager = DatabaseManager(
        database_url=f"sqlite:///{db_path}",
        echo=False
    )
    db_manager.create_tables()
    
    yield db_manager
    
    # Cleanup
    reset_db_manager()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        api_key="test_key",
        project_id="test_project",
        environment="test",
        enable_database=True,
        debug=False
    )


@pytest.fixture
def tracker(settings, temp_db):
    """Create a MetricsTracker instance."""
    return MetricsTracker(settings=settings, db_manager=temp_db)


@pytest.fixture
def analytics(tracker, temp_db):
    """Create an Analytics instance."""
    return Analytics(tracker=tracker, db_manager=temp_db)


@pytest.fixture
def stacksense_client(settings, temp_db):
    """Create a StackSense client instance."""
    client = StackSense(
        api_key=settings.api_key,
        project_id=settings.project_id,
        environment=settings.environment,
        debug=settings.debug
    )
    # Override db_manager with test database
    client.db_manager = temp_db
    client.tracker.db_manager = temp_db
    client.analytics.db_manager = temp_db
    return client

