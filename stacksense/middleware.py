"""
Framework middleware for automatic request-level AI tracking.
Supports FastAPI, Flask, and Django.
"""

import time
from typing import Any, Optional

from stacksense.core.client import StackSense


class FastAPIMiddleware:
    """
    FastAPI/Starlette middleware for tracking AI usage per request.

    Usage:
        from stacksense.middleware import FastAPIMiddleware

        app = FastAPI()
        ss = StackSense()
        app.add_middleware(FastAPIMiddleware, stacksense=ss)
    """

    def __init__(self, app: Any, stacksense: Optional[StackSense] = None):
        self.app = app
        self.ss = stacksense or StackSense()

    async def __call__(self, scope: dict, receive: Any, send: Any):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        path = scope.get("path", "unknown")
        method = scope.get("method", "GET")

        status_code = 200

        async def send_wrapper(message: dict):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            status_code = 500
            self.ss.track_event(
                event_type="http_error",
                provider="application",
                metadata={
                    "path": path,
                    "method": method,
                    "error": str(e),
                },
            )
            raise
        finally:
            latency = (time.time() - start_time) * 1000
            self.ss.track_event(
                event_type="http_request",
                provider="application",
                metadata={
                    "path": path,
                    "method": method,
                    "status_code": status_code,
                    "latency_ms": round(latency, 2),
                },
            )


class FlaskMiddleware:
    """
    Flask middleware (extension) for tracking AI usage per request.

    Usage:
        from stacksense.middleware import FlaskMiddleware

        app = Flask(__name__)
        ss = StackSense()
        FlaskMiddleware(app, stacksense=ss)
    """

    def __init__(self, app: Any = None, stacksense: Optional[StackSense] = None):
        self.ss = stacksense or StackSense()
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Any):
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        app.teardown_request(self._teardown_request)

    def _before_request(self):
        from flask import request, g

        g._stacksense_start_time = time.time()

    def _after_request(self, response: Any) -> Any:
        from flask import request, g

        start_time = getattr(g, "_stacksense_start_time", None)
        if start_time:
            latency = (time.time() - start_time) * 1000
            self.ss.track_event(
                event_type="http_request",
                provider="application",
                metadata={
                    "path": request.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "latency_ms": round(latency, 2),
                },
            )
        return response

    def _teardown_request(self, exception: Optional[Exception]):
        if exception:
            from flask import request

            self.ss.track_event(
                event_type="http_error",
                provider="application",
                metadata={
                    "path": request.path,
                    "method": request.method,
                    "error": str(exception),
                },
            )


class DjangoMiddleware:
    """
    Django middleware for tracking AI usage per request.

    Usage in settings.py:
        MIDDLEWARE = [
            ...
            'stacksense.middleware.DjangoMiddleware',
        ]

        STACKSENSE_INSTANCE = StackSense()  # or configure via env vars
    """

    def __init__(self, get_response: Any):
        self.get_response = get_response
        self.ss = StackSense()

    def __call__(self, request: Any) -> Any:
        start_time = time.time()

        response = self.get_response(request)

        latency = (time.time() - start_time) * 1000
        self.ss.track_event(
            event_type="http_request",
            provider="application",
            metadata={
                "path": request.path,
                "method": request.method,
                "status_code": response.status_code,
                "latency_ms": round(latency, 2),
            },
        )

        return response

    def process_exception(self, request: Any, exception: Exception):
        self.ss.track_event(
            event_type="http_error",
            provider="application",
            metadata={
                "path": request.path,
                "method": request.method,
                "error": str(exception),
            },
        )
        return None
