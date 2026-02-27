"""
StackSense AI Gateway - Runtime Control Layer

Intercepts and optimizes all LLM requests with:
- Real-time provider selection
- Prompt optimization
- Cost forecasting
- Auto-throttling
- Semantic caching
- Quality tracking

Performance:
- Sync Gateway: 5-15ms overhead
- Async Gateway: 1-5ms overhead (production-optimized)
- Cache Hit: < 1ms overhead
"""

from stacksense.gateway.interceptor import AIGateway
from stacksense.gateway.interceptor_async import AsyncAIGateway
from stacksense.gateway.selective_gateway import SelectiveGateway, selective_intercept
from stacksense.gateway.smart_router import SmartRouter
from stacksense.gateway.prompt_optimizer import PromptOptimizer
from stacksense.gateway.cost_predictor import CostPredictor
from stacksense.gateway.throttler import RequestThrottler
from stacksense.gateway.cache import SemanticCache
from stacksense.gateway.quality_tracker import QualityTracker

__all__ = [
    "AIGateway",
    "AsyncAIGateway",  # Production-optimized async version
    "SelectiveGateway",  # Recommended: 60-80% load reduction
    "selective_intercept",
    "SmartRouter",
    "PromptOptimizer",
    "CostPredictor",
    "RequestThrottler",
    "SemanticCache",
    "QualityTracker",
]
