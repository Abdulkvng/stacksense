"""
Request Throttler - Auto-Throttling & Circuit Breakers

Protects against runaway costs and system overload:
- Rate limiting per user/feature/agent
- Circuit breakers for failing providers
- Adaptive throttling based on budget
- Agent loop detection
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import time

from stacksense.logger.logger import get_logger

logger = get_logger(__name__)


class RequestThrottler:
    """
    Intelligent request throttling and circuit breaking.

    Features:
    - Rate limits (requests per minute/hour)
    - Cost-based throttling
    - Circuit breakers for providers
    - Agent loop detection
    """

    def __init__(self, db_session=None, user_id: Optional[int] = None):
        self.db_session = db_session
        self.user_id = user_id

        # Request tracking
        self.request_windows = defaultdict(deque)  # scope -> timestamps
        self.cost_windows = defaultdict(deque)  # scope -> (timestamp, cost)

        # Circuit breaker state
        self.circuit_breakers = defaultdict(
            lambda: {
                "state": "closed",  # closed, open, half_open
                "failures": 0,
                "last_failure_time": None,
                "opened_at": None,
            }
        )

        # Agent loop detection
        self.agent_requests = defaultdict(deque)  # agent_id -> request_hashes

        # Default limits
        self.default_limits = {
            "requests_per_minute": 100,
            "requests_per_hour": 1000,
            "cost_per_minute": 1.0,  # $1/min
            "cost_per_hour": 10.0,  # $10/hour
        }

        logger.info(f"Request Throttler initialized for user {user_id}")

    def check_request(
        self,
        scope: str = "global",
        estimated_cost: float = 0.0,
        agent_id: Optional[str] = None,
        request_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check if request should be allowed or throttled.

        Args:
            scope: Throttling scope (global, feature, agent)
            estimated_cost: Estimated cost of this request
            agent_id: Agent identifier (for loop detection)
            request_hash: Hash of request content (for loop detection)

        Returns:
            dict: {
                "allowed": bool,
                "reason": str,
                "retry_after": int (seconds),
                "current_rate": float,
                "limit": float
            }
        """
        current_time = time.time()

        # Check 1: Rate limiting (requests per minute)
        rate_check = self._check_rate_limit(scope, current_time)
        if not rate_check["allowed"]:
            return rate_check

        # Check 2: Cost throttling
        cost_check = self._check_cost_limit(scope, estimated_cost, current_time)
        if not cost_check["allowed"]:
            return cost_check

        # Check 3: Agent loop detection
        if agent_id and request_hash:
            loop_check = self._check_agent_loop(agent_id, request_hash)
            if not loop_check["allowed"]:
                return loop_check

        # Check 4: Circuit breaker
        provider = scope if scope.startswith("provider_") else None
        if provider:
            circuit_check = self._check_circuit_breaker(provider)
            if not circuit_check["allowed"]:
                return circuit_check

        # All checks passed
        self._record_request(scope, estimated_cost, current_time)
        if agent_id and request_hash:
            self._record_agent_request(agent_id, request_hash)

        return {
            "allowed": True,
            "reason": "ok",
            "retry_after": 0,
            "current_rate": len(self.request_windows[scope]),
            "limit": self.default_limits["requests_per_minute"],
        }

    def _check_rate_limit(self, scope: str, current_time: float) -> Dict[str, Any]:
        """Check requests per minute limit."""
        window = self.request_windows[scope]

        # Remove old requests (older than 1 minute)
        cutoff = current_time - 60
        while window and window[0] < cutoff:
            window.popleft()

        # Check limit
        current_rate = len(window)
        limit = self.default_limits["requests_per_minute"]

        if current_rate >= limit:
            logger.warning(f"Rate limit exceeded: {scope} - {current_rate}/{limit} req/min")
            return {
                "allowed": False,
                "reason": "rate_limit_exceeded",
                "retry_after": 60,
                "current_rate": current_rate,
                "limit": limit,
            }

        return {"allowed": True}

    def _check_cost_limit(
        self, scope: str, estimated_cost: float, current_time: float
    ) -> Dict[str, Any]:
        """Check cost per minute limit."""
        window = self.cost_windows[scope]

        # Remove old costs (older than 1 minute)
        cutoff = current_time - 60
        while window and window[0][0] < cutoff:
            window.popleft()

        # Calculate current spend rate
        current_spend = sum(cost for _, cost in window)
        limit = self.default_limits["cost_per_minute"]

        # Check if adding this request would exceed limit
        projected_spend = current_spend + estimated_cost

        if projected_spend > limit:
            logger.warning(
                f"Cost limit exceeded: {scope} - ${projected_spend:.4f}/${limit:.2f} per min"
            )
            return {
                "allowed": False,
                "reason": "cost_limit_exceeded",
                "retry_after": 60,
                "current_rate": current_spend,
                "limit": limit,
            }

        return {"allowed": True}

    def _check_agent_loop(self, agent_id: str, request_hash: str) -> Dict[str, Any]:
        """
        Detect agent loops (same request repeated rapidly).

        Loop detected if:
        - Same request hash appears 3+ times in last 5 minutes
        - Requests are within 10 seconds of each other
        """
        window = self.agent_requests[agent_id]
        current_time = time.time()

        # Remove old requests (older than 5 minutes)
        cutoff = current_time - 300
        window = deque([r for r in window if r[0] > cutoff])
        self.agent_requests[agent_id] = window

        # Count occurrences of this request hash
        occurrences = [r for r in window if r[1] == request_hash]

        if len(occurrences) >= 3:
            # Check if they're rapid (within 10s intervals)
            timestamps = [r[0] for r in occurrences[-3:]]
            intervals = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]

            if all(interval < 10 for interval in intervals):
                logger.error(
                    f"Agent loop detected: {agent_id} - "
                    f"Same request {len(occurrences)} times in 5 min"
                )
                return {
                    "allowed": False,
                    "reason": "agent_loop_detected",
                    "retry_after": 300,  # 5 minutes
                    "current_rate": len(occurrences),
                    "limit": 3,
                }

        return {"allowed": True}

    def _check_circuit_breaker(self, provider: str) -> Dict[str, Any]:
        """
        Check circuit breaker state for provider.

        States:
        - CLOSED: Normal operation
        - OPEN: Provider failing, block requests
        - HALF_OPEN: Testing if provider recovered
        """
        breaker = self.circuit_breakers[provider]
        current_time = time.time()

        # Open → Half-Open transition (after 60s)
        if breaker["state"] == "open":
            opened_at = breaker.get("opened_at", 0)
            if current_time - opened_at > 60:
                breaker["state"] = "half_open"
                logger.info(f"Circuit breaker {provider}: OPEN → HALF_OPEN")

        # Check state
        if breaker["state"] == "open":
            logger.warning(f"Circuit breaker {provider}: OPEN - blocking request")
            return {
                "allowed": False,
                "reason": "circuit_breaker_open",
                "retry_after": 60,
                "current_rate": breaker["failures"],
                "limit": 5,
            }

        return {"allowed": True}

    def record_failure(self, provider: str):
        """
        Record provider failure.

        Opens circuit breaker after 5 failures in 60 seconds.
        """
        breaker = self.circuit_breakers[provider]
        current_time = time.time()

        breaker["failures"] += 1
        breaker["last_failure_time"] = current_time

        # Open circuit after 5 failures
        if breaker["failures"] >= 5 and breaker["state"] == "closed":
            breaker["state"] = "open"
            breaker["opened_at"] = current_time
            logger.error(
                f"Circuit breaker {provider}: CLOSED → OPEN " f"({breaker['failures']} failures)"
            )

    def record_success(self, provider: str):
        """
        Record provider success.

        Closes circuit breaker if in half-open state.
        Resets failure count.
        """
        breaker = self.circuit_breakers[provider]

        if breaker["state"] == "half_open":
            breaker["state"] = "closed"
            breaker["failures"] = 0
            logger.info(f"Circuit breaker {provider}: HALF_OPEN → CLOSED")
        elif breaker["state"] == "closed":
            # Decay failure count on success
            breaker["failures"] = max(0, breaker["failures"] - 1)

    def _record_request(self, scope: str, cost: float, timestamp: float):
        """Record request for rate limiting."""
        self.request_windows[scope].append(timestamp)
        self.cost_windows[scope].append((timestamp, cost))

    def _record_agent_request(self, agent_id: str, request_hash: str):
        """Record agent request for loop detection."""
        self.agent_requests[agent_id].append((time.time(), request_hash))

    def get_current_limits(self, scope: str = "global") -> Dict[str, Any]:
        """
        Get current usage against limits.

        Returns:
            dict: {
                "requests_per_minute": {"current": int, "limit": int},
                "cost_per_minute": {"current": float, "limit": float},
                "circuit_breakers": dict
            }
        """
        current_time = time.time()

        # Requests per minute
        request_window = self.request_windows[scope]
        cutoff = current_time - 60
        recent_requests = [t for t in request_window if t > cutoff]

        # Cost per minute
        cost_window = self.cost_windows[scope]
        recent_costs = [cost for t, cost in cost_window if t > cutoff]
        total_cost = sum(recent_costs)

        return {
            "requests_per_minute": {
                "current": len(recent_requests),
                "limit": self.default_limits["requests_per_minute"],
            },
            "cost_per_minute": {
                "current": total_cost,
                "limit": self.default_limits["cost_per_minute"],
            },
            "circuit_breakers": {
                provider: {"state": breaker["state"], "failures": breaker["failures"]}
                for provider, breaker in self.circuit_breakers.items()
            },
        }

    def set_limits(
        self, requests_per_minute: Optional[int] = None, cost_per_minute: Optional[float] = None
    ):
        """Update throttling limits."""
        if requests_per_minute is not None:
            self.default_limits["requests_per_minute"] = requests_per_minute
            logger.info(f"Updated rate limit: {requests_per_minute} req/min")

        if cost_per_minute is not None:
            self.default_limits["cost_per_minute"] = cost_per_minute
            logger.info(f"Updated cost limit: ${cost_per_minute:.2f}/min")
