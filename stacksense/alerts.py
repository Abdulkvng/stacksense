"""
Alerting and webhook system for StackSense.
Triggers notifications when thresholds are exceeded.
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timedelta
from threading import Lock

import requests

from stacksense.logger.logger import get_logger


class AlertRule:
    """A single alert rule with conditions and actions."""

    def __init__(
        self,
        name: str,
        metric: str,
        threshold: float,
        operator: str = "gte",
        window: str = "1h",
        cooldown: str = "15m",
        action: Optional[Callable] = None,
    ):
        """
        Args:
            name: Human-readable rule name
            metric: Metric to check ("cost", "error_rate", "latency", "calls")
            threshold: Value that triggers the alert
            operator: Comparison operator ("gte", "lte", "gt", "lt", "eq")
            window: Time window to evaluate ("1h", "24h", "7d")
            cooldown: Minimum time between alerts for this rule
            action: Optional callback function(alert_data) to run
        """
        self.name = name
        self.metric = metric
        self.threshold = threshold
        self.operator = operator
        self.window = window
        self.cooldown = cooldown
        self.action = action
        self.last_triggered: Optional[datetime] = None

    def evaluate(self, value: float) -> bool:
        """Check if the value triggers this rule."""
        ops = {
            "gte": lambda v, t: v >= t,
            "lte": lambda v, t: v <= t,
            "gt": lambda v, t: v > t,
            "lt": lambda v, t: v < t,
            "eq": lambda v, t: v == t,
        }
        return ops.get(self.operator, ops["gte"])(value, self.threshold)

    def is_in_cooldown(self) -> bool:
        """Check if the rule is still in cooldown period."""
        if self.last_triggered is None:
            return False
        delta = _parse_duration(self.cooldown)
        return datetime.utcnow() - self.last_triggered < delta

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "metric": self.metric,
            "threshold": self.threshold,
            "operator": self.operator,
            "window": self.window,
            "cooldown": self.cooldown,
            "last_triggered": (self.last_triggered.isoformat() if self.last_triggered else None),
        }


class AlertManager:
    """
    Manages alert rules and dispatches notifications.

    Usage:
        from stacksense.alerts import AlertManager, AlertRule

        alerts = AlertManager(tracker=ss.tracker)

        # Alert when hourly cost exceeds $5
        alerts.add_rule(AlertRule(
            name="High cost alert",
            metric="cost",
            threshold=5.0,
            window="1h",
        ))

        # Add webhook
        alerts.add_webhook("https://hooks.slack.com/services/...")

        # Check alerts (call periodically or after each tracked call)
        alerts.check()
    """

    def __init__(self, tracker: Any):
        self.tracker = tracker
        self.logger = get_logger(__name__)
        self._rules: List[AlertRule] = []
        self._webhooks: List[str] = []
        self._callbacks: List[Callable] = []
        self._alert_history: List[Dict[str, Any]] = []
        self._lock = Lock()

    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        with self._lock:
            self._rules.append(rule)

    def remove_rule(self, name: str) -> None:
        """Remove an alert rule by name."""
        with self._lock:
            self._rules = [r for r in self._rules if r.name != name]

    def add_webhook(self, url: str) -> None:
        """Add a webhook URL for alert notifications."""
        self._webhooks.append(url)

    def add_callback(self, callback: Callable) -> None:
        """Add a callback function for alert notifications."""
        self._callbacks.append(callback)

    def check(self) -> List[Dict[str, Any]]:
        """
        Evaluate all rules against current metrics.

        Returns:
            List of triggered alerts
        """
        triggered = []

        with self._lock:
            from stacksense.analytics.analyzer import Analytics

            analytics = Analytics(tracker=self.tracker, db_manager=self.tracker.db_manager)

            for rule in self._rules:
                if rule.is_in_cooldown():
                    continue

                try:
                    summary = analytics.get_summary(timeframe=rule.window)
                    value = self._get_metric_value(summary, rule.metric)

                    if rule.evaluate(value):
                        alert = self._create_alert(rule, value)
                        rule.last_triggered = datetime.utcnow()
                        triggered.append(alert)
                        self._alert_history.append(alert)
                        self._dispatch(alert, rule)
                except Exception as e:
                    self.logger.error(f"Error evaluating rule '{rule.name}': {e}")

        return triggered

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get alert history."""
        return self._alert_history[-limit:]

    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all configured rules."""
        return [r.to_dict() for r in self._rules]

    def _get_metric_value(self, summary: Dict[str, Any], metric: str) -> float:
        metric_map = {
            "cost": "total_cost",
            "calls": "total_calls",
            "tokens": "total_tokens",
            "latency": "avg_latency",
            "error_rate": "error_rate",
        }
        key = metric_map.get(metric, metric)
        return float(summary.get(key, 0))

    def _create_alert(self, rule: AlertRule, value: float) -> Dict[str, Any]:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "rule": rule.name,
            "metric": rule.metric,
            "threshold": rule.threshold,
            "actual_value": value,
            "operator": rule.operator,
            "window": rule.window,
            "message": (
                f"Alert: {rule.name} - {rule.metric} is {value:.4f} "
                f"({rule.operator} {rule.threshold}) over {rule.window}"
            ),
        }

    def _dispatch(self, alert: Dict[str, Any], rule: AlertRule) -> None:
        """Send alert to all configured destinations."""
        # Fire rule-level callback
        if rule.action:
            try:
                rule.action(alert)
            except Exception as e:
                self.logger.error(f"Rule callback error: {e}")

        # Fire global callbacks
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Callback error: {e}")

        # Fire webhooks
        for url in self._webhooks:
            try:
                requests.post(
                    url,
                    json={
                        "text": alert["message"],
                        "alert": alert,
                    },
                    timeout=5,
                )
            except Exception as e:
                self.logger.error(f"Webhook error ({url}): {e}")


def _parse_duration(duration: str) -> timedelta:
    """Parse duration string like '1h', '15m', '7d' to timedelta."""
    unit = duration[-1]
    value = int(duration[:-1])
    if unit == "m":
        return timedelta(minutes=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    return timedelta(hours=1)
