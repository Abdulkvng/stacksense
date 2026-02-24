"""
Tests for Settings configuration
"""

import os
import pytest
from stacksense.config.settings import Settings


def test_settings_defaults():
    """Test default settings values."""
    settings = Settings()
    assert settings.environment == "production"
    assert settings.auto_track is True
    assert settings.enable_database is True
    assert settings.debug is False


def test_settings_custom():
    """Test custom settings."""
    settings = Settings(
        api_key="test_key",
        project_id="test_project",
        environment="development",
        debug=True
    )
    assert settings.api_key == "test_key"
    assert settings.project_id == "test_project"
    assert settings.environment == "development"
    assert settings.debug is True


def test_settings_from_env(monkeypatch):
    """Test loading settings from environment variables."""
    monkeypatch.setenv("STACKSENSE_API_KEY", "env_key")
    monkeypatch.setenv("STACKSENSE_PROJECT_ID", "env_project")
    monkeypatch.setenv("STACKSENSE_ENVIRONMENT", "staging")
    monkeypatch.setenv("STACKSENSE_DEBUG", "true")
    
    settings = Settings.from_env()
    assert settings.api_key == "env_key"
    assert settings.project_id == "env_project"
    assert settings.environment == "staging"
    assert settings.debug is True


def test_settings_to_dict():
    """Test settings to dictionary conversion."""
    settings = Settings(project_id="test", environment="dev")
    result = settings.to_dict()
    assert "project_id" in result
    assert "environment" in result
    assert result["project_id"] == "test"
    assert result["environment"] == "dev"
