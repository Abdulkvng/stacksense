"""
Smart Router - Real-Time Provider Selection

Dynamically selects providers based on:
- Current latency (switches if provider is slow)
- Cost optimization (picks cheapest viable option)
- Quality requirements (maintains quality thresholds)
- Provider health (avoids failing providers)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
import time

from stacksense.logger.logger import get_logger

logger = get_logger(__name__)


class SmartRouter:
    """
    Real-time intelligent routing across LLM providers.

    Capabilities:
    - Switch providers if latency spikes
    - Drop to cheaper model if quality threshold met
    - Load balance across providers
    - Failover on errors
    """

    def __init__(self, db_session=None, user_id: Optional[int] = None):
        self.db_session = db_session
        self.user_id = user_id

        # Real-time provider performance tracking
        self.provider_stats = defaultdict(
            lambda: {
                "latencies": [],
                "errors": 0,
                "requests": 0,
                "last_latency": 0.0,
                "avg_latency": 0.0,
                "error_rate": 0.0,
                "last_error_time": None,
            }
        )

        # Model equivalency map (for tier dropping)
        self.model_tiers = {
            "gpt-4": {
                "tier": "premium",
                "cost": 0.00003,
                "quality": 1.0,
                "downgrades": ["gpt-4-turbo", "gpt-4o", "gpt-4o-mini"],
            },
            "gpt-4-turbo": {
                "tier": "high",
                "cost": 0.00001,
                "quality": 0.95,
                "downgrades": ["gpt-4o", "gpt-4o-mini"],
            },
            "gpt-4o": {
                "tier": "medium",
                "cost": 0.000005,
                "quality": 0.90,
                "downgrades": ["gpt-4o-mini"],
            },
            "gpt-4o-mini": {
                "tier": "budget",
                "cost": 0.00000015,
                "quality": 0.85,
                "downgrades": [],
            },
            "claude-3-opus": {
                "tier": "premium",
                "cost": 0.000015,
                "quality": 1.0,
                "downgrades": ["claude-3-sonnet", "claude-3-haiku"],
            },
            "claude-3-sonnet": {
                "tier": "high",
                "cost": 0.000003,
                "quality": 0.95,
                "downgrades": ["claude-3-haiku"],
            },
            "claude-3-haiku": {
                "tier": "budget",
                "cost": 0.00000025,
                "quality": 0.85,
                "downgrades": [],
            },
        }

        # Provider to model mapping
        self.provider_models = {
            "openai": ["gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini"],
            "anthropic": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
            "google": ["gemini-pro", "gemini-flash"],
        }

        logger.info("Smart Router initialized")

    def select_provider(
        self, model: str, messages: List[Dict[str, str]], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Select the best provider and model in real-time.

        Decision factors:
        1. Latency threshold - switch if current provider is slow
        2. Quality requirement - drop tier if acceptable
        3. Cost optimization - pick cheapest viable option
        4. Provider health - avoid failing providers

        Returns:
            dict: {
                "provider": str,
                "model": str,
                "switched": bool,
                "reason": str,
                "original_model": str,
                "estimated_latency": float,
                "estimated_cost": float
            }
        """
        context = context or {}
        original_model = model

        # Get current provider from model
        current_provider = self._get_provider_for_model(model)
        current_stats = self.provider_stats[current_provider]

        # Decision 1: Check if provider is experiencing latency spike
        latency_threshold = context.get("max_latency_ms", 2000)  # 2s default

        if current_stats["avg_latency"] > latency_threshold:
            # Switch to fastest alternative provider
            alternative = self._find_fastest_alternative(model)

            if alternative:
                logger.info(
                    f"Latency spike detected: {current_provider} "
                    f"({current_stats['avg_latency']:.0f}ms) → {alternative['provider']} "
                    f"({alternative['estimated_latency']:.0f}ms)"
                )

                return {
                    "provider": alternative["provider"],
                    "model": alternative["model"],
                    "switched": True,
                    "reason": f"latency_spike_{current_stats['avg_latency']:.0f}ms",
                    "original_model": original_model,
                    "estimated_latency": alternative["estimated_latency"],
                    "estimated_cost": alternative["estimated_cost"],
                }

        # Decision 2: Check if we can drop to cheaper tier
        quality_threshold = context.get("min_quality_score", 0.80)

        if model in self.model_tiers:
            model_info = self.model_tiers[model]

            # If model quality exceeds requirement, try downgrade
            if model_info["quality"] > quality_threshold:
                cheaper_option = self._find_cheaper_equivalent(model, quality_threshold)

                if cheaper_option:
                    logger.info(
                        f"Quality threshold met: {model} → {cheaper_option['model']} "
                        f"(saves {cheaper_option['cost_savings']:.1f}%)"
                    )

                    return {
                        "provider": cheaper_option["provider"],
                        "model": cheaper_option["model"],
                        "switched": True,
                        "reason": f"cost_optimization_{cheaper_option['cost_savings']:.0f}%_savings",
                        "original_model": original_model,
                        "estimated_latency": cheaper_option["estimated_latency"],
                        "estimated_cost": cheaper_option["estimated_cost"],
                    }

        # Decision 3: Check provider health (error rate)
        if current_stats["error_rate"] > 0.1:  # >10% error rate
            healthy_alternative = self._find_healthy_alternative(model)

            if healthy_alternative:
                logger.warning(
                    f"High error rate: {current_provider} "
                    f"({current_stats['error_rate']*100:.1f}%) → "
                    f"{healthy_alternative['provider']}"
                )

                return {
                    "provider": healthy_alternative["provider"],
                    "model": healthy_alternative["model"],
                    "switched": True,
                    "reason": f"provider_health_error_rate_{current_stats['error_rate']*100:.0f}%",
                    "original_model": original_model,
                    "estimated_latency": healthy_alternative["estimated_latency"],
                    "estimated_cost": healthy_alternative["estimated_cost"],
                }

        # No switch needed - use original
        return {
            "provider": current_provider,
            "model": model,
            "switched": False,
            "reason": "optimal_choice",
            "original_model": original_model,
            "estimated_latency": current_stats.get("avg_latency", 1000),
            "estimated_cost": self.model_tiers.get(model, {}).get("cost", 0.00001),
        }

    def record_performance(
        self, provider: str, model: str, latency: float, success: bool, cost: float
    ):
        """
        Record provider performance for future routing decisions.

        This builds up real-time performance data.
        """
        stats = self.provider_stats[provider]

        stats["requests"] += 1
        stats["last_latency"] = latency

        # Rolling window of last 100 latencies
        stats["latencies"].append(latency)
        if len(stats["latencies"]) > 100:
            stats["latencies"].pop(0)

        # Calculate average latency
        stats["avg_latency"] = sum(stats["latencies"]) / len(stats["latencies"])

        # Track errors
        if not success:
            stats["errors"] += 1
            stats["last_error_time"] = datetime.utcnow()

        # Calculate error rate
        stats["error_rate"] = stats["errors"] / stats["requests"]

        logger.debug(
            f"Provider performance updated: {provider} - "
            f"{stats['avg_latency']:.0f}ms avg, "
            f"{stats['error_rate']*100:.1f}% errors"
        )

    def _get_provider_for_model(self, model: str) -> str:
        """Determine provider from model name."""
        for provider, models in self.provider_models.items():
            if model in models:
                return provider

        # Fallback: guess from model name
        if "gpt" in model.lower():
            return "openai"
        elif "claude" in model.lower():
            return "anthropic"
        elif "gemini" in model.lower():
            return "google"

        return "unknown"

    def _find_fastest_alternative(self, current_model: str) -> Optional[Dict[str, Any]]:
        """Find fastest alternative provider with equivalent model."""
        current_tier = self.model_tiers.get(current_model, {}).get("tier")

        if not current_tier:
            return None

        # Find all models in same tier
        equivalent_models = [
            (model, info, self._get_provider_for_model(model))
            for model, info in self.model_tiers.items()
            if info["tier"] == current_tier and model != current_model
        ]

        if not equivalent_models:
            return None

        # Pick fastest based on current stats
        fastest = min(
            equivalent_models,
            key=lambda x: self.provider_stats[x[2]].get("avg_latency", float("inf")),
        )

        model, info, provider = fastest

        return {
            "model": model,
            "provider": provider,
            "estimated_latency": self.provider_stats[provider].get("avg_latency", 1000),
            "estimated_cost": info["cost"],
        }

    def _find_cheaper_equivalent(
        self, current_model: str, min_quality: float
    ) -> Optional[Dict[str, Any]]:
        """Find cheaper model that meets quality threshold."""
        if current_model not in self.model_tiers:
            return None

        current_info = self.model_tiers[current_model]
        downgrades = current_info.get("downgrades", [])

        # Find cheapest downgrade that meets quality requirement
        for downgrade_model in downgrades:
            downgrade_info = self.model_tiers.get(downgrade_model)

            if not downgrade_info:
                continue

            if downgrade_info["quality"] >= min_quality:
                provider = self._get_provider_for_model(downgrade_model)
                cost_savings = (
                    (current_info["cost"] - downgrade_info["cost"]) / current_info["cost"] * 100
                )

                return {
                    "model": downgrade_model,
                    "provider": provider,
                    "estimated_latency": self.provider_stats[provider].get("avg_latency", 1000),
                    "estimated_cost": downgrade_info["cost"],
                    "cost_savings": cost_savings,
                }

        return None

    def _find_healthy_alternative(self, current_model: str) -> Optional[Dict[str, Any]]:
        """Find healthy alternative provider."""
        current_provider = self._get_provider_for_model(current_model)
        current_tier = self.model_tiers.get(current_model, {}).get("tier")

        if not current_tier:
            return None

        # Find equivalent models from healthy providers
        for model, info in self.model_tiers.items():
            if info["tier"] != current_tier or model == current_model:
                continue

            provider = self._get_provider_for_model(model)
            stats = self.provider_stats[provider]

            # Check if provider is healthy
            if stats["error_rate"] < 0.05:  # <5% error rate
                return {
                    "model": model,
                    "provider": provider,
                    "estimated_latency": stats.get("avg_latency", 1000),
                    "estimated_cost": info["cost"],
                }

        return None
