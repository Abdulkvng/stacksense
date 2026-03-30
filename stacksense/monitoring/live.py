"""
Live monitoring and metrics collection for the open-source dashboard.

This module intentionally contains the runtime metrics surface that the
public dashboard needs, without bundling private runtime control features.
"""

from collections import defaultdict
from datetime import datetime, UTC
import threading
import time
from typing import Any, Dict, List, Optional

try:
    from prometheus_client import (
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    class Counter:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            pass

    class Histogram:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def observe(self, *args, **kwargs):
            pass

    class Gauge:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def set(self, *args, **kwargs):
            pass

        def inc(self, *args, **kwargs):
            pass

        def dec(self, *args, **kwargs):
            pass

    class Summary:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def observe(self, *args, **kwargs):
            pass


from stacksense.logger.logger import get_logger

logger = get_logger(__name__)


registry = CollectorRegistry() if PROMETHEUS_AVAILABLE else None

requests_total = Counter(
    "stacksense_requests_total",
    "Total requests by feature",
    ["feature", "user_id", "status"],
    registry=registry,
)

request_latency = Histogram(
    "stacksense_request_duration_seconds",
    "Request latency in seconds",
    ["feature", "user_id"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0],
    registry=registry,
)

request_errors = Counter(
    "stacksense_request_errors_total",
    "Total request errors",
    ["feature", "error_type"],
    registry=registry,
)

system_health = Gauge(
    "stacksense_system_health",
    "System health status (1=healthy, 0=unhealthy)",
    ["component"],
    registry=registry,
)


class LiveMonitor:
    """Thread-safe metrics collector used by the dashboard."""

    def __init__(self):
        self._lock = threading.RLock()
        self._alerts: List[Dict[str, Any]] = []
        self._health_checks: Dict[str, Dict[str, Any]] = {}
        self._request_counts = defaultdict(int)

        self._health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._health_thread.start()

        logger.info("Live monitoring initialized")

    def track_request(self, feature: str, user_id: str, duration: float, status: str = "success"):
        requests_total.labels(feature=feature, user_id=user_id, status=status).inc()
        request_latency.labels(feature=feature, user_id=user_id).observe(duration)
        self._request_counts[feature] += 1

    def track_error(self, feature: str, error_type: str):
        request_errors.labels(feature=feature, error_type=error_type).inc()

    def set_component_health(self, component: str, healthy: bool):
        system_health.labels(component=component).set(1 if healthy else 0)
        self._health_checks[component] = {
            "healthy": healthy,
            "last_check": datetime.now(UTC).isoformat(),
        }

    def _health_check_loop(self):
        while True:
            try:
                self.set_component_health("database", True)

                unhealthy = [
                    component
                    for component, status in self._health_checks.items()
                    if not status["healthy"]
                ]

                if unhealthy:
                    self._add_alert(
                        severity="critical",
                        message=f"Unhealthy components: {', '.join(unhealthy)}",
                        components=unhealthy,
                    )

                time.sleep(30)
            except Exception as exc:
                logger.error(f"Health check error: {exc}")
                time.sleep(60)

    def _add_alert(self, severity: str, message: str, **metadata):
        with self._lock:
            alert = {
                "timestamp": datetime.now(UTC).isoformat(),
                "severity": severity,
                "message": message,
                "metadata": metadata,
            }
            self._alerts.append(alert)

            if len(self._alerts) > 1000:
                self._alerts = self._alerts[-1000:]

            logger.warning(f"ALERT [{severity}]: {message}")

    def get_alerts(self, limit: int = 100, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            alerts = self._alerts[-limit:]
            if severity:
                alerts = [alert for alert in alerts if alert["severity"] == severity]
            return alerts

    def clear_alerts(self):
        with self._lock:
            self._alerts = []

    def get_metrics(self) -> bytes:
        if PROMETHEUS_AVAILABLE and registry:
            return generate_latest(registry)
        return b""

    def get_metrics_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "prometheus_available": PROMETHEUS_AVAILABLE,
            "alerts_count": len(self._alerts),
            "health_checks": self._health_checks,
            "request_counts": dict(self._request_counts),
        }


monitor = LiveMonitor()


def track_operation(feature: str):
    """Decorator to track operation latency and failures."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            user_id = kwargs.get("user_id") or (
                args[0].user_id if args and hasattr(args[0], "user_id") else "unknown"
            )

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                monitor.track_request(feature, str(user_id), duration, "success")
                return result
            except Exception as exc:
                duration = time.time() - start
                monitor.track_request(feature, str(user_id), duration, "error")
                monitor.track_error(feature, type(exc).__name__)
                raise

        return wrapper

    return decorator
