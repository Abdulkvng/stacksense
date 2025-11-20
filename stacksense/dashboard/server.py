"""
Flask server for StackSense dashboard
"""

import os
from flask import Flask, jsonify, send_from_directory, request
from typing import Optional
from pathlib import Path

from stacksense.database import get_db_manager
from stacksense.database.models import Event, Metric
from sqlalchemy import func, desc, Integer
from datetime import datetime, timedelta


def create_app(db_manager=None, debug=False):
    """
    Create Flask application for StackSense dashboard.

    Args:
        db_manager: DatabaseManager instance
        debug: Enable debug mode

    Returns:
        Flask application
    """
    app = Flask(
        __name__,
        static_folder=Path(__file__).parent / "static",
        template_folder=Path(__file__).parent / "templates",
    )
    app.config["DEBUG"] = debug

    if not db_manager:
        db_manager = get_db_manager()

    @app.route("/")
    def index():
        """Serve dashboard HTML."""
        return send_from_directory(app.template_folder, "index.html")

    @app.route("/api/metrics/summary")
    def get_metrics_summary():
        """Get metrics summary."""
        try:
            timeframe = request.args.get("timeframe", "24h")

            with db_manager.get_session() as session:
                # Calculate timeframe
                delta = _parse_timeframe(timeframe)
                cutoff = datetime.utcnow() - delta

                # Get aggregated stats
                stats = (
                    session.query(
                        func.count(Event.id).label("total_calls"),
                        func.sum(Event.total_tokens).label("total_tokens"),
                        func.sum(Event.cost).label("total_cost"),
                        func.avg(Event.latency).label("avg_latency"),
                        func.sum(func.cast(~Event.success, Integer)).label("error_count"),
                    )
                    .filter(Event.timestamp >= cutoff)
                    .first()
                )

                total_calls = stats.total_calls or 0
                total_tokens = stats.total_tokens or 0
                total_cost = float(stats.total_cost or 0.0)
                avg_latency = float(stats.avg_latency or 0.0)
                error_count = stats.error_count or 0
                error_rate = (error_count / total_calls * 100) if total_calls > 0 else 0.0

                return jsonify(
                    {
                        "total_calls": total_calls,
                        "total_tokens": total_tokens,
                        "total_cost": round(total_cost, 4),
                        "avg_cost_per_call": (
                            round(total_cost / total_calls, 4) if total_calls > 0 else 0
                        ),
                        "avg_latency": round(avg_latency, 2),
                        "error_rate": round(error_rate, 2),
                    }
                )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/metrics/cost-breakdown")
    def get_cost_breakdown():
        """Get cost breakdown by provider."""
        try:
            timeframe = request.args.get("timeframe", "24h")
            delta = _parse_timeframe(timeframe)
            cutoff = datetime.utcnow() - delta

            with db_manager.get_session() as session:
                breakdown = (
                    session.query(Event.provider, func.sum(Event.cost).label("total_cost"))
                    .filter(Event.timestamp >= cutoff)
                    .group_by(Event.provider)
                    .all()
                )

                result = {provider: float(cost) for provider, cost in breakdown}
                return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/metrics/usage-over-time")
    def get_usage_over_time():
        """Get usage metrics over time."""
        try:
            timeframe = request.args.get("timeframe", "24h")
            interval = request.args.get("interval", "1h")

            delta = _parse_timeframe(timeframe)
            cutoff = datetime.utcnow() - delta

            with db_manager.get_session() as session:
                events = (
                    session.query(Event)
                    .filter(Event.timestamp >= cutoff)
                    .order_by(Event.timestamp)
                    .all()
                )

                # Group by time buckets
                buckets = {}
                for event in events:
                    bucket_key = _get_time_bucket(event.timestamp, interval)
                    if bucket_key not in buckets:
                        buckets[bucket_key] = {"calls": 0, "tokens": 0, "cost": 0.0}
                    buckets[bucket_key]["calls"] += 1
                    buckets[bucket_key]["tokens"] += event.total_tokens or 0
                    buckets[bucket_key]["cost"] += event.cost or 0.0

                result = [{"timestamp": k, **v} for k, v in sorted(buckets.items())]
                return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/events/recent")
    def get_recent_events():
        """Get recent events."""
        try:
            limit = int(request.args.get("limit", 50))

            with db_manager.get_session() as session:
                events = session.query(Event).order_by(desc(Event.timestamp)).limit(limit).all()

                result = [event.to_dict() for event in events]
                return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


def _parse_timeframe(timeframe: str) -> timedelta:
    """Parse timeframe string."""
    unit = timeframe[-1]
    value = int(timeframe[:-1])
    if unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    elif unit == "w":
        return timedelta(weeks=value)
    return timedelta(hours=24)


def _get_time_bucket(timestamp: datetime, interval: str) -> str:
    """Get time bucket for timestamp."""
    if interval == "1h":
        timestamp = timestamp.replace(minute=0, second=0, microsecond=0)
    elif interval == "1d":
        timestamp = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
    return timestamp.isoformat()


def run_server(host="127.0.0.1", port=5000, debug=False, db_manager=None):
    """
    Run the dashboard server.

    Args:
        host: Host to bind to
        port: Port to bind to
        debug: Enable debug mode
        db_manager: DatabaseManager instance
    """
    app = create_app(db_manager=db_manager, debug=debug)
    print(f"🚀 StackSense Dashboard running at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
