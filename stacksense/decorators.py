"""
Decorator API for StackSense tracking.
"""

import time
import functools
from typing import Any, Callable, Optional

from stacksense.monitoring.tracker import MetricsTracker
from stacksense.config.settings import Settings

# Module-level default tracker (lazily initialized)
_default_tracker: Optional[MetricsTracker] = None


def _get_default_tracker() -> MetricsTracker:
    global _default_tracker
    if _default_tracker is None:
        settings = Settings.from_env()
        db_manager = None
        if settings.enable_database:
            try:
                from stacksense.database.connection import get_db_manager

                db_manager = get_db_manager(
                    database_url=settings.database_url,
                    echo=settings.database_echo,
                    create_tables=settings.database_auto_create,
                )
            except Exception:
                pass
        _default_tracker = MetricsTracker(settings=settings, db_manager=db_manager)
    return _default_tracker


def track(
    provider: str = "custom",
    model: str = "custom",
    tracker: Optional[MetricsTracker] = None,
) -> Callable:
    """
    Decorator to track function execution as an API call.

    Usage:
        @stacksense.track(provider="openai", model="gpt-4o")
        def my_ai_call(prompt):
            return openai_client.chat.completions.create(...)

        @stacksense.track()
        def my_function():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            t = tracker or _get_default_tracker()
            start_time = time.time()
            success = True
            error = None
            result = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                latency = (time.time() - start_time) * 1000
                tokens = _extract_tokens_from_result(result, provider) if result else None
                t.track_call(
                    provider=provider,
                    model=model,
                    tokens=tokens,
                    latency=latency,
                    success=success,
                    error=error,
                    metadata={"method": func.__name__, "decorator": True},
                )

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            t = tracker or _get_default_tracker()
            start_time = time.time()
            success = True
            error = None
            result = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                latency = (time.time() - start_time) * 1000
                tokens = _extract_tokens_from_result(result, provider) if result else None
                t.track_call(
                    provider=provider,
                    model=model,
                    tokens=tokens,
                    latency=latency,
                    success=success,
                    error=error,
                    metadata={"method": func.__name__, "decorator": True},
                )

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def _extract_tokens_from_result(result: Any, provider: str) -> Optional[dict]:
    """Try to extract token usage from a result object."""
    if result is None:
        return None

    try:
        if hasattr(result, "usage"):
            usage = result.usage
            if hasattr(usage, "prompt_tokens"):
                return {
                    "input": usage.prompt_tokens,
                    "output": getattr(usage, "completion_tokens", 0),
                }
            if hasattr(usage, "input_tokens"):
                return {
                    "input": usage.input_tokens,
                    "output": getattr(usage, "output_tokens", 0),
                }
    except Exception:
        pass

    return None
