"""
Configuration and settings management
"""

import os
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class Settings:
    """
    StackSense configuration settings.
    """

    # API Configuration
    api_key: Optional[str] = None
    project_id: Optional[str] = field(
        default_factory=lambda: os.getenv("STACKSENSE_PROJECT_ID", "default")
    )
    api_base_url: str = "https://api.stacksense.io/v1"

    # Environment
    environment: str = "production"

    # Tracking Configuration
    auto_track: bool = True
    batch_size: int = 100
    flush_interval: int = 60  # seconds

    # Feature Flags
    enable_cost_tracking: bool = True
    enable_performance_tracking: bool = True
    enable_error_tracking: bool = True

    # Logging
    debug: bool = False
    log_level: str = "INFO"

    # Rate Limiting
    max_events_per_second: int = 1000

    # Retry Configuration
    max_retries: int = 3
    retry_delay: float = 1.0

    # Database Configuration
    enable_database: bool = field(
        default_factory=lambda: os.getenv("STACKSENSE_ENABLE_DB", "true").lower() == "true"
    )
    database_url: Optional[str] = field(default_factory=lambda: os.getenv("STACKSENSE_DB_URL"))
    database_echo: bool = False  # SQL query logging
    database_auto_create: bool = True  # Auto-create tables

    def __post_init__(self):
        """Validate settings after initialization."""
        if self.debug:
            self.log_level = "DEBUG"

        # Load from environment if not provided
        if not self.api_key:
            self.api_key = os.getenv("STACKSENSE_API_KEY")

    @classmethod
    def from_env(cls) -> "Settings":
        """
        Create settings from environment variables.

        Returns:
            Settings instance
        """
        return cls(
            api_key=os.getenv("STACKSENSE_API_KEY"),
            project_id=os.getenv("STACKSENSE_PROJECT_ID", "default"),
            environment=os.getenv("STACKSENSE_ENVIRONMENT", "production"),
            debug=os.getenv("STACKSENSE_DEBUG", "false").lower() == "true",
            enable_database=os.getenv("STACKSENSE_ENABLE_DB", "true").lower() == "true",
            database_url=os.getenv("STACKSENSE_DB_URL"),
            database_echo=os.getenv("STACKSENSE_DB_ECHO", "false").lower() == "true",
        )

    def to_dict(self) -> dict:
        """Convert settings to dictionary."""
        return {
            "project_id": self.project_id,
            "environment": self.environment,
            "auto_track": self.auto_track,
            "debug": self.debug,
        }
