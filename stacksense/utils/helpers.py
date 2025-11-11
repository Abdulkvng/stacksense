"""
Helper utilities and functions
"""

import time
import functools
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
        
        # If it's a method that makes API calls, wrap it
        if callable(attr) and self._is_api_method(name):
            return self._wrap_method(attr, name)
        
        return attr
    
    def _is_api_method(self, name: str) -> bool:
        """Check if method name suggests an API call."""
        api_methods = [
            "create", "generate", "complete", "embed",
            "query", "search", "insert", "upsert",
            "send", "invoke"
        ]
        return any(method in name.lower() for method in api_methods)
    
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
                
                # Track the call
                self._tracker.track_call(
                    provider=self._provider,
                    model=model,
                    tokens=tokens,
                    latency=latency,
                    success=success,
                    error=error,
                    metadata={"method": method_name}
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
    
    result = {
        "provider": "unknown",
        "model_name": model,
        "version": None
    }
    
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


def estimate_cost(tokens: int, model: str, provider: str) -> float:
    """
    Estimate cost for a given token count.
    
    Args:
        tokens: Number of tokens
        model: Model name
        provider: Provider name
        
    Returns:
        Estimated cost
    """
    # Simplified cost estimation
    # In practice, this would use the pricing from tracker
    base_rates = {
        "openai": {"gpt-4": 0.03, "gpt-3.5": 0.002},
        "anthropic": {"claude-3": 0.015},
    }
    
    provider_rates = base_rates.get(provider, {})
    
    for model_key, rate in provider_rates.items():
        if model_key in model.lower():
            return (tokens / 1000) * rate
    
    return 0.0