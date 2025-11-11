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
        }
    }
    
    def __init__(self, settings):
        """
        Initialize metrics tracker.
        
        Args:
            settings: StackSense settings object
        """
        self.settings = settings
        self.logger = get_logger(__name__, debug=settings.debug)
        self._lock = Lock()
        
        # Metrics storage
        self._events: List[Dict[str, Any]] = []
        self._metrics = {
            "total_calls": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "by_provider": defaultdict(lambda: {
                "calls": 0,
                "tokens": 0,
                "cost": 0.0,
                "errors": 0,
                "total_latency": 0.0,
            })
        }
    
    def track_call(
        self,
        provider: str,
        model: str,
        tokens: Optional[Dict[str, int]] = None,
        latency: float = 0.0,
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
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
                "metadata": metadata or {}
            }
            
            self._events.append(event)
            
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
    
    def track_event(
        self,
        event_type: str,
        provider: str,
        metadata: Dict[str, Any]
    ) -> None:
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
                "metadata": metadata
            }
            self._events.append(event)
    
    def _calculate_cost(
        self,
        provider: str,
        model: str,
        tokens: Dict[str, int]
    ) -> float:
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
    
    def get_events(self) -> List[Dict[str, Any]]:
        """Get all tracked events."""
        with self._lock:
            return self._events.copy()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics."""
        with self._lock:
            return {
                "total_calls": self._metrics["total_calls"],
                "total_tokens": self._metrics["total_tokens"],
                "total_cost": round(self._metrics["total_cost"], 4),
                "by_provider": dict(self._metrics["by_provider"])
            }
    
    def flush(self) -> None:
        """Flush events (send to API, clear local storage, etc.)."""
        with self._lock:
            if self._events:
                self.logger.info(f"Flushing {len(self._events)} events")
                # TODO: Send to API
                self._events.clear()
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._events.clear()
            self._metrics = {
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "by_provider": defaultdict(lambda: {
                    "calls": 0,
                    "tokens": 0,
                    "cost": 0.0,
                    "errors": 0,
                    "total_latency": 0.0,
                })
            }
            self.logger.info("Metrics reset")