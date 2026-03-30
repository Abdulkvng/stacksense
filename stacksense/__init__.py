"""
StackSense - AI Infrastructure Monitoring
Track usage, cost, and performance across AI APIs
"""

from typing import Any

__version__ = "0.1.0"
__author__ = "Abdulrahman Sadiq"
__license__ = "MIT"

__all__ = [
    "StackSense",
    "MetricsTracker",
    "Analytics",
    "Settings",
    "track",
]


def __getattr__(name: str) -> Any:
    if name == "StackSense":
        from stacksense.core.client import StackSense

        return StackSense
    if name == "MetricsTracker":
        from stacksense.monitoring.tracker import MetricsTracker

        return MetricsTracker
    if name == "Analytics":
        from stacksense.analytics.analyzer import Analytics

        return Analytics
    if name == "Settings":
        from stacksense.config.settings import Settings

        return Settings
    if name == "track":
        from stacksense.decorators import track

        return track
    raise AttributeError(f"module 'stacksense' has no attribute {name!r}")
