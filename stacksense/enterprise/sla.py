"""
SLA-Aware Routing

Routes requests based on latency requirements and SLA guarantees.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from stacksense.database.models import SLAConfig, Event
from stacksense.logger.logger import get_logger

logger = get_logger(__name__)


class SLARouter:
    """
    Route requests based on SLA requirements.
    """

    def __init__(self, db_session: Optional[Session] = None, user_id: Optional[int] = None):
        self.db_session = db_session
        self.user_id = user_id

    def route_by_sla(
        self, priority_level: str = "medium", max_latency_ms: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Route based on SLA requirements.

        Returns:
            dict: {
                "provider": str,
                "model": str,
                "estimated_latency": float,
                "success_rate": float,
                "reason": str
            }
        """
        if not self.db_session or not self.user_id:
            return {
                "provider": None,
                "model": None,
                "estimated_latency": 0.0,
                "success_rate": 0.0,
                "reason": "No SLA configuration found",
            }

        # Get SLA config
        sla_config = (
            self.db_session.query(SLAConfig)
            .filter(
                SLAConfig.user_id == self.user_id,
                SLAConfig.is_active == True,
                SLAConfig.priority_level == priority_level,
            )
            .first()
        )

        if not sla_config:
            return {
                "provider": None,
                "model": None,
                "estimated_latency": 0.0,
                "success_rate": 0.0,
                "reason": f"No SLA config for priority {priority_level}",
            }

        # Get provider performance stats
        provider_stats = self._get_provider_performance()

        # Filter by SLA requirements
        max_latency = max_latency_ms or sla_config.max_latency_ms
        min_success = sla_config.min_success_rate

        viable_providers = [
            p
            for p in provider_stats
            if p["p95_latency"] <= max_latency and p["success_rate"] >= min_success
        ]

        if not viable_providers:
            logger.warning(f"No providers meet SLA requirements for {priority_level}")
            return {
                "provider": None,
                "model": None,
                "estimated_latency": 0.0,
                "success_rate": 0.0,
                "reason": "No providers meet SLA requirements",
            }

        # Select based on fallback strategy
        strategy = sla_config.fallback_strategy
        if strategy == "fastest":
            selected = min(viable_providers, key=lambda x: x["p95_latency"])
        elif strategy == "cheapest":
            selected = min(viable_providers, key=lambda x: x["avg_cost"])
        else:  # most_reliable
            selected = max(viable_providers, key=lambda x: x["success_rate"])

        return {
            "provider": selected["provider"],
            "model": selected["model"],
            "estimated_latency": selected["p95_latency"],
            "success_rate": selected["success_rate"],
            "reason": f"Selected by {strategy} strategy",
        }

    def _get_provider_performance(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent performance stats for all providers."""
        if not self.db_session:
            return []

        since = datetime.utcnow() - timedelta(days=days)

        # Query performance by provider and model
        stats = (
            self.db_session.query(
                Event.provider,
                Event.model,
                func.avg(Event.latency).label("avg_latency"),
                func.avg(Event.cost).label("avg_cost"),
                func.count(Event.id).label("total_calls"),
                func.sum(func.cast(Event.success, func.Integer())).label("success_count"),
            )
            .filter(Event.timestamp >= since)
            .group_by(Event.provider, Event.model)
            .all()
        )

        results = []
        for stat in stats:
            success_rate = stat.success_count / stat.total_calls if stat.total_calls > 0 else 0.0
            # Estimate P95 as avg * 1.5 (simplified)
            p95_latency = stat.avg_latency * 1.5 if stat.avg_latency else 0.0

            results.append(
                {
                    "provider": stat.provider,
                    "model": stat.model,
                    "avg_latency": stat.avg_latency or 0.0,
                    "p95_latency": p95_latency,
                    "avg_cost": stat.avg_cost or 0.0,
                    "success_rate": success_rate,
                    "total_calls": stat.total_calls,
                }
            )

        return results

    def create_sla_config(
        self,
        name: str,
        max_latency_ms: int,
        min_success_rate: float,
        priority_level: str = "medium",
        fallback_strategy: str = "most_reliable",
        preferred_providers: Optional[List[str]] = None,
    ) -> SLAConfig:
        """Create a new SLA configuration."""
        if not self.db_session or not self.user_id:
            raise ValueError("Database session and user_id required")

        config = SLAConfig(
            user_id=self.user_id,
            name=name,
            max_latency_ms=max_latency_ms,
            min_success_rate=min_success_rate,
            priority_level=priority_level,
            preferred_providers=preferred_providers,
            fallback_strategy=fallback_strategy,
            is_active=True,
        )

        self.db_session.add(config)
        self.db_session.commit()
        self.db_session.refresh(config)

        logger.info(f"Created SLA config '{name}' for user {self.user_id}")
        return config
