"""
StackSense - AI Infrastructure Monitoring
Track usage, cost, and performance across AI APIs
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__license__ = "MIT"

from stacksense.core.client import StackSense
from stacksense.monitoring.tracker import MetricsTracker
from stacksense.analytics.analyzer import Analytics
from stacksense.config.settings import Settings

__all__ = [
    "StackSense",
    "MetricsTracker",
    "Analytics",
    "Settings",
]

# stacksense/core/__init__.py
"""Core client functionality"""
from stacksense.core.client import StackSense

__all__ = ["StackSense"]


# stacksense/monitoring/__init__.py
"""Monitoring and tracking"""
from stacksense.monitoring.tracker import MetricsTracker

__all__ = ["MetricsTracker"]


# stacksense/analytics/__init__.py
"""Analytics and insights"""
from stacksense.analytics.analyzer import Analytics

__all__ = ["Analytics"]


# stacksense/api/__init__.py
"""API client"""
from stacksense.api.client import APIClient

__all__ = ["APIClient"]


# stacksense/config/__init__.py
"""Configuration management"""
from stacksense.config.settings import Settings

__all__ = ["Settings"]


# stacksense/logger/__init__.py
"""Logging infrastructure"""
from stacksense.logger.logger import get_logger, StackSenseLogger

__all__ = ["get_logger", "StackSenseLogger"]


# stacksense/utils/__init__.py
"""Utility functions"""
from stacksense.utils.helpers import (
    ClientProxy,
    format_cost,
    format_tokens,
    parse_model_name,
    calculate_rate_limit,
    estimate_cost,
)

__all__ = [
    "ClientProxy",
    "format_cost",
    "format_tokens",
    "parse_model_name",
    "calculate_rate_limit",
    "estimate_cost",
]