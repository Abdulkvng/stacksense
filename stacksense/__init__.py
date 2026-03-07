"""
StackSense - AI Infrastructure Monitoring
Track usage, cost, and performance across AI APIs
"""

__version__ = "0.1.0"
__author__ = "Abdulrahman Sadiq"
__license__ = "MIT"

from stacksense.core.client import StackSense
from stacksense.monitoring.tracker import MetricsTracker
from stacksense.analytics.analyzer import Analytics
from stacksense.config.settings import Settings
from stacksense.decorators import track

__all__ = [
    "StackSense",
    "MetricsTracker",
    "Analytics",
    "Settings",
    "track",
]
