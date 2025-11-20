"""
Logging infrastructure for StackSense
"""

import logging
import sys
from typing import Optional


def get_logger(name: str, debug: bool = False) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (usually __name__)
        debug: Enable debug logging

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # Set level
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger


class StackSenseLogger:
    """
    Enhanced logger with structured logging capabilities.
    """

    def __init__(self, name: str, debug: bool = False):
        """
        Initialize logger.

        Args:
            name: Logger name
            debug: Enable debug mode
        """
        self.logger = get_logger(name, debug)
        self.debug_mode = debug

    def info(self, message: str, **kwargs) -> None:
        """Log info message with optional structured data."""
        if kwargs:
            message = f"{message} | {self._format_kwargs(kwargs)}"
        self.logger.info(message)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with optional structured data."""
        if kwargs:
            message = f"{message} | {self._format_kwargs(kwargs)}"
        self.logger.debug(message)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with optional structured data."""
        if kwargs:
            message = f"{message} | {self._format_kwargs(kwargs)}"
        self.logger.warning(message)

    def error(self, message: str, **kwargs) -> None:
        """Log error message with optional structured data."""
        if kwargs:
            message = f"{message} | {self._format_kwargs(kwargs)}"
        self.logger.error(message)

    def _format_kwargs(self, kwargs: dict) -> str:
        """Format kwargs as key=value pairs."""
        return " ".join(f"{k}={v}" for k, v in kwargs.items())
