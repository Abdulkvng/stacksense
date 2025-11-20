"""
Main StackSense client for monitoring AI infrastructure
"""

import os
from typing import Any, Optional, Dict, List
from datetime import datetime

from stacksense.monitoring.tracker import MetricsTracker
from stacksense.analytics.analyzer import Analytics
from stacksense.config.settings import Settings
from stacksense.logger.logger import get_logger
from stacksense.api.client import APIClient


class StackSense:
    """
    Main StackSense client for monitoring AI API usage, cost, and performance.

    Usage:
        ss = StackSense(api_key="your_key")
        client = ss.monitor(openai.OpenAI())
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        environment: str = "production",
        auto_track: bool = True,
        debug: bool = False,
    ):
        """
        Initialize StackSense client.

        Args:
            api_key: StackSense API key (or set STACKSENSE_API_KEY env var)
            project_id: Project identifier (or set STACKSENSE_PROJECT_ID env var)
            environment: Environment name (production, staging, development)
            auto_track: Automatically track all API calls
            debug: Enable debug logging
        """
        self.settings = Settings(
            api_key=api_key or os.getenv("STACKSENSE_API_KEY"),
            project_id=project_id or os.getenv("STACKSENSE_PROJECT_ID"),
            environment=environment,
            auto_track=auto_track,
            debug=debug,
        )

        self.logger = get_logger(__name__, debug=debug)

        # Initialize database if enabled
        self.db_manager = None
        if self.settings.enable_database:
            try:
                from stacksense.database.connection import get_db_manager

                self.db_manager = get_db_manager(
                    database_url=self.settings.database_url,
                    echo=self.settings.database_echo,
                    create_tables=self.settings.database_auto_create,
                )
                self.logger.info("Database initialized")
            except Exception as e:
                self.logger.warning(
                    f"Failed to initialize database: {e}. Continuing without database."
                )

        self.tracker = MetricsTracker(settings=self.settings, db_manager=self.db_manager)
        self.analytics = Analytics(tracker=self.tracker, db_manager=self.db_manager)
        self.api_client = APIClient(settings=self.settings)

        self._monitored_clients: List[Any] = []

        self.logger.info(f"StackSense initialized for project: {self.settings.project_id}")

    def monitor(self, client: Any, provider: Optional[str] = None) -> Any:
        """
        Wrap an AI API client to enable monitoring.

        Args:
            client: The API client to monitor (e.g., openai.OpenAI())
            provider: Provider name (auto-detected if None)

        Returns:
            Wrapped client with monitoring enabled
        """
        if provider is None:
            provider = self._detect_provider(client)

        self.logger.info(f"Monitoring {provider} client")

        # Wrap the client with our monitoring proxy
        wrapped_client = self._wrap_client(client, provider)
        self._monitored_clients.append(wrapped_client)

        return wrapped_client

    def _detect_provider(self, client: Any) -> str:
        """Auto-detect the provider from the client type."""
        client_type = type(client).__module__

        if "openai" in client_type:
            return "openai"
        elif "anthropic" in client_type:
            return "anthropic"
        elif "elevenlabs" in client_type:
            return "elevenlabs"
        elif "pinecone" in client_type:
            return "pinecone"
        else:
            return "unknown"

    def _wrap_client(self, client: Any, provider: str) -> Any:
        """Wrap client with monitoring proxy."""
        from stacksense.utils.helpers import ClientProxy

        return ClientProxy(client, self.tracker, provider)

    def track_event(
        self, event_type: str, provider: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Manually track a custom event.

        Args:
            event_type: Type of event (e.g., "api_call", "error")
            provider: Provider name
            metadata: Additional event metadata
        """
        self.tracker.track_event(event_type=event_type, provider=provider, metadata=metadata or {})

    def get_metrics(self, timeframe: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current metrics summary.

        Args:
            timeframe: Time period (e.g., "1h", "24h", "7d")

        Returns:
            Dictionary with metrics summary
        """
        return self.analytics.get_summary(timeframe=timeframe)

    def get_cost_breakdown(self) -> Dict[str, float]:
        """Get cost breakdown by provider."""
        return self.analytics.get_cost_breakdown()

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return self.analytics.get_performance_stats()

    def create_dashboard(self, output: str = "dashboard.html", timeframe: str = "7d") -> str:
        """
        Generate an HTML dashboard with metrics visualizations.

        Args:
            output: Output file path
            timeframe: Time period to display

        Returns:
            Path to generated dashboard
        """
        try:
            from stacksense.analytics.dashboard import create_dashboard

            return create_dashboard(self.analytics, output=output, timeframe=timeframe)
        except ImportError:
            self.logger.error(
                "Dashboard feature requires additional dependencies. "
                "Install with: pip install stacksense[dashboard]"
            )
            raise

    def flush(self) -> None:
        """Flush any pending metrics to the API."""
        self.tracker.flush()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - flush metrics."""
        self.flush()
        return False
