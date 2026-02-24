"""
Helper utilities and functions
"""

import time
import functools
import asyncio
from typing import Any, Callable, Dict, Optional


class ClientProxy:
    """
    Proxy wrapper for AI API clients to enable automatic tracking.
    """

    def __init__(self, client: Any, tracker: Any, provider: str):
        """
        Initialize client proxy.

        Args:
            client: Original API client
            tracker: MetricsTracker instance
            provider: Provider name
        """
        self._client = client
        self._tracker = tracker
        self._provider = provider

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to wrapped client."""
        attr = getattr(self._client, name)

        # If it's a callable, check if we should wrap it
        if callable(attr):
            # For OpenAI: chat.completions.create pattern
            # We need to return a proxy that continues wrapping
            if not self._is_api_method(name):
                # Return another proxy to continue the chain
                return ClientProxy(attr, self._tracker, self._provider)
            else:
                # This is the final API method, wrap it
                return self._wrap_method(attr, name)

        # If it's not callable, check if it's an object we should proxy
        if hasattr(attr, "__dict__") or hasattr(attr, "__call__"):
            return ClientProxy(attr, self._tracker, self._provider)

        return attr

    def __call__(self, *args, **kwargs):
        """Handle direct calls to the proxy (for when the method itself is called)."""
        if callable(self._client):
            # Get the method name from the client
            method_name = getattr(self._client, "__name__", "unknown")

            # Check if this looks like an API method
            if self._is_api_method(method_name) or "create" in method_name.lower():
                return self._wrap_method(self._client, method_name)(*args, **kwargs)

            return self._client(*args, **kwargs)
        return self._client

    def _is_api_method(self, name: str) -> bool:
        """Check if method name suggests an API call."""
        api_methods = [
            "create",
            "generate",
            "complete",
            "embed",
            "query",
            "search",
            "insert",
            "upsert",
            "delete",
            "send",
            "invoke",
            "run",
            "execute",
        ]
        name_lower = name.lower()
        return any(method in name_lower for method in api_methods)

    def _wrap_method(self, method: Callable, method_name: str) -> Callable:
        """Wrap a method to track metrics."""

        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error = None
            tokens = None
            model = kwargs.get("model", "unknown")

            try:
                # Make the actual API call
                result = method(*args, **kwargs)

                if kwargs.get("stream") is True:
                    return self._handle_stream(result, start_time, model, method_name)

                # Extract metrics from response
                tokens = self._extract_tokens(result, self._provider)

                return result

            except Exception as e:
                success = False
                error = str(e)
                raise

            finally:
                # Calculate latency
                latency = (time.time() - start_time) * 1000  # ms

                # Track the call only if not streaming (streams track themselves when they end)
                if not kwargs.get("stream"):
                    self._tracker.track_call(
                        provider=self._provider,
                        model=model,
                        tokens=tokens,
                        latency=latency,
                        success=success,
                        error=error,
                        metadata={"method": method_name},
                    )

        return wrapper

    def _extract_tokens(self, response: Any, provider: str) -> Optional[Dict[str, int]]:
        """Extract token usage from API response."""
        try:
            if provider == "openai":
                if hasattr(response, "usage"):
                    return {
                        "input": response.usage.prompt_tokens,
                        "output": response.usage.completion_tokens,
                    }

            elif provider == "anthropic":
                if hasattr(response, "usage"):
                    return {
                        "input": response.usage.input_tokens,
                        "output": response.usage.output_tokens,
                    }

            elif provider == "elevenlabs":
                # Character-based usage
                if hasattr(response, "character_count"):
                    return {"characters": response.character_count}

            elif provider == "pinecone":
                # Query-based usage
                return {"queries": 1}

        except Exception:
            pass

        return None

    def _handle_stream(self, response_generator: Any, start_time: float, model: str, method_name: str) -> Any:
        """Handle streaming response and track metrics when stream finishes."""
        chunks = []
        try:
            for chunk in response_generator:
                chunks.append(chunk)
                yield chunk
        finally:
            latency = (time.time() - start_time) * 1000  # ms
            
            # Extract tokens depending on provider from chunks
            tokens = self._extract_stream_tokens(chunks, self._provider)
            
            self._tracker.track_call(
                provider=self._provider,
                model=model,
                tokens=tokens,
                latency=latency,
                success=True,
                error=None,
                metadata={"method": method_name, "stream": True},
            )

    def _extract_stream_tokens(self, chunks: list, provider: str) -> Optional[Dict[str, int]]:
        """Extract or estimate tokens from streaming chunks."""
        if not chunks:
            return {"input": 0, "output": 0}
            
        if provider == "openai":
            last_chunk = chunks[-1]
            if hasattr(last_chunk, "usage") and last_chunk.usage:
                return {
                    "input": getattr(last_chunk.usage, "prompt_tokens", 0),
                    "output": getattr(last_chunk.usage, "completion_tokens", 0),
                }
            return {"input": 0, "output": len(chunks)}
            
        elif provider == "anthropic":
            input_tokens = 0
            output_tokens = 0
            for chunk in chunks:
                if hasattr(chunk, "type"):
                    if chunk.type == "message_start" and hasattr(chunk, "message") and hasattr(chunk.message, "usage"):
                        input_tokens += getattr(chunk.message.usage, "input_tokens", 0)
                    elif chunk.type == "message_delta" and hasattr(chunk, "usage"):
                        output_tokens += getattr(chunk.usage, "output_tokens", 0)
            if input_tokens > 0 or output_tokens > 0:
                return {"input": input_tokens, "output": output_tokens}
            return {"input": 0, "output": len(chunks)}
            
        return None


class AsyncClientProxy(ClientProxy):
    """
    Async proxy wrapper for AI API clients to enable automatic tracking.
    """
    
    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._client, name)
        
        if callable(attr):
            if not self._is_api_method(name):
                return AsyncClientProxy(attr, self._tracker, self._provider)
            else:
                return self._wrap_method(attr, name)
                
        if hasattr(attr, "__dict__") or hasattr(attr, "__call__"):
            return AsyncClientProxy(attr, self._tracker, self._provider)
            
        return attr
        
    def _wrap_method(self, method: Callable, method_name: str) -> Callable:
        """Wrap an async method to track metrics."""
        
        @functools.wraps(method)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error = None
            tokens = None
            model = kwargs.get("model", "unknown")

            try:
                result = await method(*args, **kwargs)

                if kwargs.get("stream") is True:
                    return self._handle_async_stream(result, start_time, model, method_name)

                tokens = self._extract_tokens(result, self._provider)
                return result

            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                if not kwargs.get("stream"):
                    latency = (time.time() - start_time) * 1000
                    self._tracker.track_call(
                        provider=self._provider,
                        model=model,
                        tokens=tokens,
                        latency=latency,
                        success=success,
                        error=error,
                        metadata={"method": method_name},
                    )

        return wrapper
        
    async def _handle_async_stream(self, response_generator: Any, start_time: float, model: str, method_name: str) -> Any:
        """Handle async streaming response."""
        chunks = []
        try:
            async for chunk in response_generator:
                chunks.append(chunk)
                yield chunk
        finally:
            latency = (time.time() - start_time) * 1000
            tokens = self._extract_stream_tokens(chunks, self._provider)
            
            self._tracker.track_call(
                provider=self._provider,
                model=model,
                tokens=tokens,
                latency=latency,
                success=True,
                error=None,
                metadata={"method": method_name, "stream": True},
            )


def format_cost(cost: float) -> str:
    """
    Format cost for display.

    Args:
        cost: Cost value

    Returns:
        Formatted string
    """
    if cost < 0.01:
        return f"${cost:.4f}"
    return f"${cost:.2f}"


def format_tokens(tokens: int) -> str:
    """
    Format token count for display.

    Args:
        tokens: Number of tokens

    Returns:
        Formatted string
    """
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.2f}M"
    elif tokens >= 1_000:
        return f"{tokens / 1_000:.2f}K"
    return str(tokens)


def parse_model_name(model: str) -> Dict[str, str]:
    """
    Parse model name into components.

    Args:
        model: Model identifier

    Returns:
        Dictionary with provider, model_name, version
    """
    parts = model.split("-")

    result = {"provider": "unknown", "model_name": model, "version": None}

    if "gpt" in model.lower():
        result["provider"] = "openai"
    elif "claude" in model.lower():
        result["provider"] = "anthropic"

    return result


def calculate_rate_limit(calls: int, timeframe_seconds: int) -> float:
    """
    Calculate calls per second rate.

    Args:
        calls: Number of calls
        timeframe_seconds: Time period in seconds

    Returns:
        Calls per second
    """
    if timeframe_seconds == 0:
        return 0.0
    return calls / timeframe_seconds



