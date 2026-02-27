"""
AI Gateway - Core Request Interceptor

Intercepts every LLM request and applies runtime controls:
1. Budget checking → block/downgrade if exceeded
2. Prompt optimization → reduce tokens
3. Cache lookup → return cached response if available
4. Smart routing → select best provider based on latency/cost/quality
5. Execution → with retry and fallback
6. Tracking → metrics and learning
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import time

from stacksense.logger.logger import get_logger
from stacksense.enterprise.budget import BudgetEnforcer
from stacksense.enterprise.monitoring import monitor

logger = get_logger(__name__)


class AIGateway:
    """
    Core AI Gateway that intercepts and controls all LLM requests.

    This is the runtime control layer that transforms StackSense
    from monitoring to an AI operating system.
    """

    def __init__(
        self,
        db_session=None,
        user_id: Optional[int] = None,
        enable_cache: bool = True,
        enable_optimization: bool = True,
        enable_smart_routing: bool = True
    ):
        self.db_session = db_session
        self.user_id = user_id
        self.enable_cache = enable_cache
        self.enable_optimization = enable_optimization
        self.enable_smart_routing = enable_smart_routing

        # Initialize components (lazy loaded)
        self._budget_enforcer = None
        self._smart_router = None
        self._prompt_optimizer = None
        self._cache = None
        self._throttler = None
        self._quality_tracker = None

        logger.info(f"AI Gateway initialized for user {user_id}")

    @property
    def budget_enforcer(self):
        """Lazy load budget enforcer."""
        if self._budget_enforcer is None and self.db_session and self.user_id:
            self._budget_enforcer = BudgetEnforcer(
                db_session=self.db_session,
                user_id=self.user_id
            )
        return self._budget_enforcer

    @property
    def smart_router(self):
        """Lazy load smart router."""
        if self._smart_router is None and self.enable_smart_routing:
            from stacksense.gateway.smart_router import SmartRouter
            self._smart_router = SmartRouter(
                db_session=self.db_session,
                user_id=self.user_id
            )
        return self._smart_router

    @property
    def prompt_optimizer(self):
        """Lazy load prompt optimizer."""
        if self._prompt_optimizer is None and self.enable_optimization:
            from stacksense.gateway.prompt_optimizer import PromptOptimizer
            self._prompt_optimizer = PromptOptimizer()
        return self._prompt_optimizer

    @property
    def cache(self):
        """Lazy load semantic cache."""
        if self._cache is None and self.enable_cache:
            from stacksense.gateway.cache import SemanticCache
            self._cache = SemanticCache()
        return self._cache

    @property
    def throttler(self):
        """Lazy load request throttler."""
        if self._throttler is None:
            from stacksense.gateway.throttler import RequestThrottler
            self._throttler = RequestThrottler(
                db_session=self.db_session,
                user_id=self.user_id
            )
        return self._throttler

    @property
    def quality_tracker(self):
        """Lazy load quality tracker."""
        if self._quality_tracker is None:
            from stacksense.gateway.quality_tracker import QualityTracker
            self._quality_tracker = QualityTracker(
                db_session=self.db_session,
                user_id=self.user_id
            )
        return self._quality_tracker

    def intercept(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Intercept and control an LLM request.

        Pipeline:
        1. Check throttling
        2. Check budget
        3. Optimize prompt
        4. Check cache
        5. Smart route
        6. Execute
        7. Track quality
        8. Cache result

        Args:
            messages: Chat messages
            model: Requested model
            **kwargs: Additional parameters

        Returns:
            dict: Response with potential modifications
        """
        start_time = time.time()

        try:
            # Step 1: Check throttling
            throttle_result = self._check_throttling()
            if not throttle_result["allowed"]:
                return self._throttled_response(throttle_result)

            # Step 2: Check budget
            estimated_cost = self._estimate_cost(messages, model)
            budget_result = self._check_budget(estimated_cost)

            if not budget_result["allowed"]:
                if budget_result["action"] == "block":
                    return self._blocked_response(budget_result)
                elif budget_result["action"] == "downgrade":
                    model = budget_result["downgrade_model"]
                    logger.info(f"Budget enforced downgrade to {model}")

            # Step 3: Optimize prompt (if enabled)
            original_messages = messages
            if self.enable_optimization and self.prompt_optimizer:
                optimization_result = self.prompt_optimizer.optimize(messages, model)
                if optimization_result["optimized"]:
                    messages = optimization_result["messages"]
                    logger.info(
                        f"Prompt optimized: {optimization_result['original_tokens']} → "
                        f"{optimization_result['optimized_tokens']} tokens "
                        f"({optimization_result['savings_percent']:.1f}% reduction)"
                    )

            # Step 4: Check cache (if enabled)
            if self.enable_cache and self.cache:
                cache_key = self.cache.generate_key(messages, model)
                cached_response = self.cache.get(cache_key)

                if cached_response:
                    logger.info(f"Cache hit for {model}")
                    monitor.track_request("cache_hit", str(self.user_id), time.time() - start_time)
                    return {
                        "response": cached_response,
                        "from_cache": True,
                        "cost": 0.0,
                        "model": model
                    }

            # Step 5: Smart routing (if enabled)
            selected_provider = None
            selected_model = model

            if self.enable_smart_routing and self.smart_router:
                routing_result = self.smart_router.select_provider(
                    model=model,
                    messages=messages,
                    context=kwargs
                )

                if routing_result["switched"]:
                    selected_provider = routing_result["provider"]
                    selected_model = routing_result["model"]
                    logger.info(
                        f"Smart routing: {model} → {selected_model} "
                        f"(reason: {routing_result['reason']})"
                    )

            # Step 6: Execute request (this would call the actual LLM)
            # For now, this is a placeholder - actual execution happens in the client
            execution_result = {
                "model": selected_model,
                "provider": selected_provider,
                "messages": messages,
                "optimized": messages != original_messages,
                "intercepted": True,
                "budget_action": budget_result.get("action"),
                "estimated_cost": estimated_cost
            }

            # Step 7: Track quality (post-execution)
            # This would happen after getting the response

            # Step 8: Cache result (post-execution)
            # This would happen after getting the response

            duration = time.time() - start_time
            monitor.track_request("gateway_intercept", str(self.user_id), duration)

            return execution_result

        except Exception as e:
            logger.error(f"Gateway interception failed: {e}", exc_info=True)
            # Fail open - allow request to proceed
            return {
                "model": model,
                "messages": messages,
                "intercepted": False,
                "error": str(e)
            }

    def _check_throttling(self) -> Dict[str, Any]:
        """Check if request should be throttled."""
        if not self.throttler:
            return {"allowed": True}

        return self.throttler.check_request()

    def _check_budget(self, estimated_cost: float) -> Dict[str, Any]:
        """Check budget constraints."""
        if not self.budget_enforcer:
            return {"allowed": True, "action": "allow"}

        return self.budget_enforcer.check_budget(
            cost=estimated_cost,
            scope="global"
        )

    def _estimate_cost(self, messages: List[Dict[str, str]], model: str) -> float:
        """Estimate request cost."""
        # Simple estimation based on message length
        # In production, use actual token counting
        total_chars = sum(len(m.get("content", "")) for m in messages)
        estimated_tokens = total_chars // 4  # Rough estimate

        # Model-specific pricing (simplified)
        pricing = {
            "gpt-4": 0.00003,  # $0.03 per 1k tokens
            "gpt-4-turbo": 0.00001,
            "gpt-4o": 0.000005,
            "gpt-4o-mini": 0.00000015,
            "claude-3-opus": 0.000015,
            "claude-3-sonnet": 0.000003,
            "claude-3-haiku": 0.00000025,
        }

        rate = pricing.get(model, 0.00001)  # Default rate
        return estimated_tokens * rate

    def _throttled_response(self, throttle_result: Dict[str, Any]) -> Dict[str, Any]:
        """Return throttled response."""
        logger.warning(f"Request throttled: {throttle_result['reason']}")
        return {
            "error": "rate_limit_exceeded",
            "message": throttle_result.get("message", "Too many requests"),
            "retry_after": throttle_result.get("retry_after", 60),
            "intercepted": True
        }

    def _blocked_response(self, budget_result: Dict[str, Any]) -> Dict[str, Any]:
        """Return budget blocked response."""
        logger.warning(f"Request blocked by budget: {budget_result['message']}")
        return {
            "error": "budget_exceeded",
            "message": budget_result["message"],
            "budget_remaining": budget_result["budget_remaining"],
            "budget_utilization": budget_result["budget_utilization"],
            "intercepted": True
        }

    def post_execution_tracking(
        self,
        request: Dict[str, Any],
        response: Any,
        actual_cost: float,
        latency: float
    ):
        """
        Track metrics after request execution.

        This updates:
        - Quality scores
        - Cache (if enabled)
        - Cost tracking
        - Provider performance
        """
        try:
            # Track quality
            if self.quality_tracker:
                self.quality_tracker.track_response(
                    model=request.get("model"),
                    response=response,
                    cost=actual_cost,
                    latency=latency
                )

            # Cache response
            if self.enable_cache and self.cache and response:
                cache_key = self.cache.generate_key(
                    request.get("messages", []),
                    request.get("model", "")
                )
                self.cache.set(cache_key, response, ttl=3600)  # 1 hour TTL

            # Record actual spend
            if self.budget_enforcer:
                self.budget_enforcer.record_spend(
                    cost=actual_cost,
                    scope="global"
                )

            # Update provider performance stats
            if self.smart_router:
                self.smart_router.record_performance(
                    provider=request.get("provider"),
                    model=request.get("model"),
                    latency=latency,
                    success=True,
                    cost=actual_cost
                )

        except Exception as e:
            logger.error(f"Post-execution tracking failed: {e}", exc_info=True)
