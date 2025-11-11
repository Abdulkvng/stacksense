"""
Analytics and data analysis for metrics
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict


class Analytics:
    """
    Analyze and provide insights on tracked metrics.
    """
    
    def __init__(self, tracker):
        """
        Initialize analytics.
        
        Args:
            tracker: MetricsTracker instance
        """
        self.tracker = tracker
    
    def get_summary(self, timeframe: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metrics summary.
        
        Args:
            timeframe: Time period (e.g., "1h", "24h", "7d")
            
        Returns:
            Summary dictionary with key metrics
        """
        metrics = self.tracker.get_metrics()
        events = self.tracker.get_events()
        
        # Filter by timeframe if specified
        if timeframe:
            events = self._filter_by_timeframe(events, timeframe)
        
        # Calculate additional stats
        total_calls = metrics["total_calls"]
        avg_latency = self._calculate_avg_latency(events)
        error_rate = self._calculate_error_rate(events)
        
        return {
            "total_calls": total_calls,
            "total_tokens": metrics["total_tokens"],
            "total_cost": metrics["total_cost"],
            "avg_cost_per_call": metrics["total_cost"] / total_calls if total_calls > 0 else 0,
            "avg_latency": round(avg_latency, 2),
            "error_rate": round(error_rate, 2),
            "providers": list(metrics["by_provider"].keys()),
        }
    
    def get_cost_breakdown(self) -> Dict[str, float]:
        """
        Get cost breakdown by provider.
        
        Returns:
            Dictionary mapping provider to cost
        """
        metrics = self.tracker.get_metrics()
        
        breakdown = {}
        for provider, data in metrics["by_provider"].items():
            breakdown[provider] = round(data["cost"], 4)
        
        return breakdown
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        metrics = self.tracker.get_metrics()
        events = self.tracker.get_events()
        
        stats = {}
        
        for provider, data in metrics["by_provider"].items():
            calls = data["calls"]
            avg_latency = data["total_latency"] / calls if calls > 0 else 0
            
            stats[provider] = {
                "calls": calls,
                "avg_latency": round(avg_latency, 2),
                "total_tokens": data["tokens"],
                "avg_tokens_per_call": data["tokens"] // calls if calls > 0 else 0,
                "errors": data["errors"],
                "error_rate": (data["errors"] / calls * 100) if calls > 0 else 0,
            }
        
        return stats
    
    def get_usage_over_time(
        self,
        timeframe: str = "24h",
        interval: str = "1h"
    ) -> List[Dict[str, Any]]:
        """
        Get usage metrics over time.
        
        Args:
            timeframe: Time period to analyze
            interval: Bucket interval
            
        Returns:
            List of time-bucketed metrics
        """
        events = self.tracker.get_events()
        events = self._filter_by_timeframe(events, timeframe)
        
        # Group events by time buckets
        buckets = defaultdict(lambda: {
            "calls": 0,
            "tokens": 0,
            "cost": 0.0,
        })
        
        for event in events:
            if event.get("timestamp"):
                bucket_key = self._get_time_bucket(event["timestamp"], interval)
                buckets[bucket_key]["calls"] += 1
                buckets[bucket_key]["tokens"] += event.get("total_tokens", 0)
                buckets[bucket_key]["cost"] += event.get("cost", 0.0)
        
        # Convert to list and sort
        result = []
        for timestamp, data in sorted(buckets.items()):
            result.append({
                "timestamp": timestamp,
                **data
            })
        
        return result
    
    def get_top_models(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get most used models.
        
        Args:
            limit: Number of top models to return
            
        Returns:
            List of models with usage stats
        """
        events = self.tracker.get_events()
        
        model_stats = defaultdict(lambda: {
            "calls": 0,
            "tokens": 0,
            "cost": 0.0,
        })
        
        for event in events:
            model = event.get("model")
            if model:
                model_stats[model]["calls"] += 1
                model_stats[model]["tokens"] += event.get("total_tokens", 0)
                model_stats[model]["cost"] += event.get("cost", 0.0)
        
        # Sort by calls and take top N
        sorted_models = sorted(
            model_stats.items(),
            key=lambda x: x[1]["calls"],
            reverse=True
        )[:limit]
        
        return [
            {"model": model, **stats}
            for model, stats in sorted_models
        ]
    
    def _filter_by_timeframe(
        self,
        events: List[Dict[str, Any]],
        timeframe: str
    ) -> List[Dict[str, Any]]:
        """Filter events by timeframe."""
        if not timeframe:
            return events
        
        # Parse timeframe (e.g., "24h", "7d")
        delta = self._parse_timeframe(timeframe)
        cutoff = datetime.utcnow() - delta
        
        filtered = []
        for event in events:
            timestamp_str = event.get("timestamp")
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                if timestamp >= cutoff:
                    filtered.append(event)
        
        return filtered
    
    def _parse_timeframe(self, timeframe: str) -> timedelta:
        """Parse timeframe string to timedelta."""
        unit = timeframe[-1]
        value = int(timeframe[:-1])
        
        if unit == "h":
            return timedelta(hours=value)
        elif unit == "d":
            return timedelta(days=value)
        elif unit == "w":
            return timedelta(weeks=value)
        else:
            return timedelta(hours=24)
    
    def _calculate_avg_latency(self, events: List[Dict[str, Any]]) -> float:
        """Calculate average latency from events."""
        latencies = [e.get("latency", 0) for e in events if "latency" in e]
        return sum(latencies) / len(latencies) if latencies else 0.0
    
    def _calculate_error_rate(self, events: List[Dict[str, Any]]) -> float:
        """Calculate error rate as percentage."""
        if not events:
            return 0.0
        
        errors = sum(1 for e in events if not e.get("success", True))
        return (errors / len(events)) * 100
    
    def _get_time_bucket(self, timestamp_str: str, interval: str) -> str:
        """Get time bucket for a timestamp."""
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        
        # Round down to interval
        if interval == "1h":
            timestamp = timestamp.replace(minute=0, second=0, microsecond=0)
        elif interval == "1d":
            timestamp = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        
        return timestamp.isoformat()