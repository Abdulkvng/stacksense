"""
Data export utilities for StackSense metrics.
Supports CSV, JSON, and webhook/external service push.
"""

import csv
import json
import io
from typing import Any, Dict, List, Optional
from datetime import datetime

from stacksense.monitoring.tracker import MetricsTracker
from stacksense.analytics.analyzer import Analytics
from stacksense.logger.logger import get_logger


class Exporter:
    """
    Export StackSense metrics and events to various formats.

    Usage:
        exporter = Exporter(ss.tracker)
        exporter.to_csv("metrics.csv")
        exporter.to_json("metrics.json")
        data = exporter.to_dict()
    """

    def __init__(self, tracker: MetricsTracker):
        self.tracker = tracker
        self.analytics = Analytics(tracker=tracker, db_manager=tracker.db_manager)
        self.logger = get_logger(__name__)

    def to_csv(
        self,
        filepath: str,
        from_db: bool = False,
        limit: Optional[int] = None,
    ) -> str:
        """
        Export events to CSV file.

        Args:
            filepath: Output file path
            from_db: Fetch from database if available
            limit: Limit number of events

        Returns:
            Path to written file
        """
        events = self.tracker.get_events(from_db=from_db, limit=limit)

        if not events:
            self.logger.warning("No events to export")
            return filepath

        fieldnames = [
            "timestamp",
            "provider",
            "model",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "cost",
            "latency",
            "success",
            "error",
            "method",
        ]

        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()

            for event in events:
                row = {
                    "timestamp": event.get("timestamp", ""),
                    "provider": event.get("provider", ""),
                    "model": event.get("model", ""),
                    "input_tokens": event.get("tokens", {}).get("input", 0),
                    "output_tokens": event.get("tokens", {}).get("output", 0),
                    "total_tokens": event.get("total_tokens", 0),
                    "cost": event.get("cost", 0.0),
                    "latency": event.get("latency", 0.0),
                    "success": event.get("success", True),
                    "error": event.get("error", ""),
                    "method": event.get("metadata", {}).get("method", ""),
                }
                writer.writerow(row)

        self.logger.info(f"Exported {len(events)} events to {filepath}")
        return filepath

    def to_json(
        self,
        filepath: str,
        from_db: bool = False,
        limit: Optional[int] = None,
        include_summary: bool = True,
    ) -> str:
        """
        Export events and summary to JSON file.

        Args:
            filepath: Output file path
            from_db: Fetch from database if available
            limit: Limit number of events
            include_summary: Include analytics summary

        Returns:
            Path to written file
        """
        data = self.to_dict(from_db=from_db, limit=limit, include_summary=include_summary)

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

        self.logger.info(f"Exported data to {filepath}")
        return filepath

    def to_dict(
        self,
        from_db: bool = False,
        limit: Optional[int] = None,
        include_summary: bool = True,
    ) -> Dict[str, Any]:
        """
        Export events and summary as a dictionary.

        Args:
            from_db: Fetch from database if available
            limit: Limit number of events
            include_summary: Include analytics summary

        Returns:
            Dictionary with events and optional summary
        """
        events = self.tracker.get_events(from_db=from_db, limit=limit)

        result: Dict[str, Any] = {
            "exported_at": datetime.utcnow().isoformat(),
            "event_count": len(events),
            "events": events,
        }

        if include_summary:
            result["summary"] = self.analytics.get_summary(from_db=from_db)
            result["cost_breakdown"] = self.analytics.get_cost_breakdown()
            result["top_models"] = self.analytics.get_top_models()

        return result

    def to_csv_string(
        self,
        from_db: bool = False,
        limit: Optional[int] = None,
    ) -> str:
        """Export events to CSV string (useful for APIs/downloads)."""
        events = self.tracker.get_events(from_db=from_db, limit=limit)

        output = io.StringIO()
        fieldnames = [
            "timestamp",
            "provider",
            "model",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "cost",
            "latency",
            "success",
            "error",
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for event in events:
            row = {
                "timestamp": event.get("timestamp", ""),
                "provider": event.get("provider", ""),
                "model": event.get("model", ""),
                "input_tokens": event.get("tokens", {}).get("input", 0),
                "output_tokens": event.get("tokens", {}).get("output", 0),
                "total_tokens": event.get("total_tokens", 0),
                "cost": event.get("cost", 0.0),
                "latency": event.get("latency", 0.0),
                "success": event.get("success", True),
                "error": event.get("error", ""),
            }
            writer.writerow(row)

        return output.getvalue()
