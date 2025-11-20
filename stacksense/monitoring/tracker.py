"""
Metrics tracking and collection
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
from threading import Lock

from stacksense.logger.logger import get_logger


class MetricsTracker:
    """
    Tracks metrics for AI API calls including tokens, cost, latency, and errors.
    """

    # Pricing per 1M tokens (as of 2024)
    PRICING = {
        "openai": {
            "gpt-4": {"input": 30.0, "output": 60.0},
            "gpt-4-turbo": {"input": 10.0, "output": 30.0},
            "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
            "text-embedding-3-small": {"input": 0.02, "output": 0.0},
        },
        "anthropic": {
            "claude-3-5-sonnet": {"input": 3.0, "output": 15.0},
            "claude-3-opus": {"input": 15.0, "output": 75.0},
            "claude-3-haiku": {"input": 0.25, "output": 1.25},
        },
        "elevenlabs": {
            "default": {"characters": 0.30},  # per 1000 characters
        },
        "pinecone": {
            "default": {"queries": 0.0001},  # per query
        },
    }

    def __init__(self, settings, db_manager=None):
        """
        Initialize metrics tracker.

        Args:
            settings: StackSense settings object
            db_manager: Optional DatabaseManager instance for persistence
        """
        self.settings = settings
        self.logger = get_logger(__name__, debug=settings.debug)
        self._lock = Lock()
        self.db_manager = db_manager

        # Metrics storage
        self._events: List[Dict[str, Any]] = []
        self._metrics = {
            "total_calls": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "by_provider": defaultdict(
                lambda: {
                    "calls": 0,
                    "tokens": 0,
                    "cost": 0.0,
                    "errors": 0,
                    "total_latency": 0.0,
                }
            ),
        }

    def track_call(
        self,
        provider: str,
        model: str,
        tokens: Optional[Dict[str, int]] = None,
        latency: float = 0.0,
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Track an API call.

        Args:
            provider: Provider name (openai, anthropic, etc.)
            model: Model identifier
            tokens: Token usage dict with 'input' and 'output' keys
            latency: Call latency in milliseconds
            success: Whether the call succeeded
            error: Error message if failed
            metadata: Additional metadata
        """
        with self._lock:
            timestamp = datetime.utcnow().isoformat()

            # Calculate cost
            cost = 0.0
            total_tokens = 0
            if tokens:
                cost = self._calculate_cost(provider, model, tokens)
                total_tokens = tokens.get("input", 0) + tokens.get("output", 0)

            # Create event
            event = {
                "timestamp": timestamp,
                "provider": provider,
                "model": model,
                "tokens": tokens or {},
                "total_tokens": total_tokens,
                "cost": cost,
                "latency": latency,
                "success": success,
                "error": error,
                "metadata": metadata or {},
            }

            self._events.append(event)

            # Persist to database if enabled
            if self.settings.enable_database and self.db_manager:
                self._persist_event_to_db(event, metadata)

            # Update aggregated metrics
            self._metrics["total_calls"] += 1
            self._metrics["total_tokens"] += total_tokens
            self._metrics["total_cost"] += cost

            provider_metrics = self._metrics["by_provider"][provider]
            provider_metrics["calls"] += 1
            provider_metrics["tokens"] += total_tokens
            provider_metrics["cost"] += cost
            provider_metrics["total_latency"] += latency

            if not success:
                provider_metrics["errors"] += 1

            self.logger.debug(
                f"Tracked {provider} call: {model} | "
                f"Tokens: {total_tokens} | Cost: ${cost:.4f} | "
                f"Latency: {latency:.2f}ms"
            )

    def track_event(self, event_type: str, provider: str, metadata: Dict[str, Any]) -> None:
        """
        Track a custom event.

        Args:
            event_type: Type of event
            provider: Provider name
            metadata: Event metadata
        """
        with self._lock:
            event = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": event_type,
                "provider": provider,
                "metadata": metadata,
            }
            self._events.append(event)

            # Persist to database if enabled
            if self.settings.enable_database and self.db_manager:
                self._persist_event_to_db(event, metadata)

    def _persist_event_to_db(
        self, event: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Persist event to database.

        Args:
            event: Event dictionary
            metadata: Additional metadata
        """
        if not self.db_manager:
            return

        try:
            from stacksense.database.models import Event as EventModel

            # Parse timestamp
            timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))

            # Create database event
            db_event = EventModel(
                timestamp=timestamp,
                project_id=self.settings.project_id,
                environment=self.settings.environment,
                event_type=event.get("type", "api_call"),
                provider=event.get("provider", "unknown"),
                model=event.get("model"),
                input_tokens=event.get("tokens", {}).get("input", 0),
                output_tokens=event.get("tokens", {}).get("output", 0),
                total_tokens=event.get("total_tokens", 0),
                cost=event.get("cost", 0.0),
                latency=event.get("latency", 0.0),
                success=event.get("success", True),
                error=event.get("error"),
                metadata_=event.get("metadata", {}) or (metadata or {}),
                method=(
                    event.get("metadata", {}).get("method")
                    if isinstance(event.get("metadata"), dict)
                    else None
                ),
            )

            # Save to database
            with self.db_manager.get_session() as session:
                session.add(db_event)
                # Session commits automatically via context manager

        except Exception as e:
            # Don't fail tracking if database write fails
            self.logger.warning(f"Failed to persist event to database: {e}")

    def _calculate_cost(self, provider: str, model: str, tokens: Dict[str, int]) -> float:
        """Calculate cost for a call based on token usage."""
        provider_pricing = self.PRICING.get(provider, {})

        # Try to find exact model match
        model_pricing = None
        for model_key, pricing in provider_pricing.items():
            if model_key in model:
                model_pricing = pricing
                break

        if not model_pricing:
            # Use default if available
            model_pricing = provider_pricing.get("default", {})

        if not model_pricing:
            self.logger.warning(f"No pricing data for {provider}/{model}")
            return 0.0

        # Calculate cost
        cost = 0.0
        input_tokens = tokens.get("input", 0)
        output_tokens = tokens.get("output", 0)

        if "input" in model_pricing:
            cost += (input_tokens / 1_000_000) * model_pricing["input"]
        if "output" in model_pricing:
            cost += (output_tokens / 1_000_000) * model_pricing["output"]

        # Handle character-based pricing (e.g., ElevenLabs)
        if "characters" in model_pricing:
            chars = tokens.get("characters", 0)
            cost += (chars / 1000) * model_pricing["characters"]

        # Handle query-based pricing (e.g., Pinecone)
        if "queries" in model_pricing:
            queries = tokens.get("queries", 0)
            cost += queries * model_pricing["queries"]

        return cost

    def get_events(
        self, from_db: bool = False, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all tracked events.

        Args:
            from_db: If True, fetch from database instead of memory
            limit: Limit number of events returned

        Returns:
            List of event dictionaries
        """
        if from_db and self.settings.enable_database and self.db_manager:
            return self._get_events_from_db(limit=limit)

        with self._lock:
            events = self._events.copy()
            if limit:
                events = events[-limit:]  # Get most recent N events
            return events

    def _get_events_from_db(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get events from database."""
        try:
            from stacksense.database.models import Event as EventModel
            from sqlalchemy import desc

            with self.db_manager.get_session() as session:
                query = (
                    session.query(EventModel)
                    .filter(
                        EventModel.project_id == self.settings.project_id,
                        EventModel.environment == self.settings.environment,
                    )
                    .order_by(desc(EventModel.timestamp))
                )

                if limit:
                    query = query.limit(limit)

                events = query.all()
                return [event.to_dict() for event in events]
        except Exception as e:
            self.logger.error(f"Failed to fetch events from database: {e}")
            return []

    def get_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics."""
        with self._lock:
            return {
                "total_calls": self._metrics["total_calls"],
                "total_tokens": self._metrics["total_tokens"],
                "total_cost": round(self._metrics["total_cost"], 4),
                "by_provider": dict(self._metrics["by_provider"]),
            }

    def flush(self) -> None:
        """Flush events (send to API, clear local storage, etc.)."""
        with self._lock:
            if self._events:
                self.logger.info(f"Flushing {len(self._events)} events")

                # Send to API if configured
                if self.settings.api_key:
                    from stacksense.api.client import APIClient

                    api_client = APIClient(settings=self.settings)
                    api_client.send_events(self._events)

                # Clear in-memory events (database already has them)
                self._events.clear()

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._events.clear()
            self._metrics = {
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "by_provider": defaultdict(
                    lambda: {
                        "calls": 0,
                        "tokens": 0,
                        "cost": 0.0,
                        "errors": 0,
                        "total_latency": 0.0,
                    }
                ),
            }
            self.logger.info("Metrics reset")
