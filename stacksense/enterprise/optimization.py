"""
Cost Optimization Engine

Analyzes token usage, identifies waste, and recommends optimizations.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from stacksense.database.models import Event
from stacksense.logger.logger import get_logger

logger = get_logger(__name__)


class CostOptimizer:
    """
    Identify cost optimization opportunities.
    """

    def __init__(self, db_session: Optional[Session] = None, project_id: Optional[str] = None):
        self.db_session = db_session
        self.project_id = project_id

    def analyze_waste(self, days: int = 7) -> Dict[str, Any]:
        """
        Analyze token waste and inefficiencies.

        Returns:
            dict: {
                "total_spend": float,
                "estimated_waste": float,
                "waste_percentage": float,
                "recommendations": List[dict]
            }
        """
        if not self.db_session or not self.project_id:
            return {
                "total_spend": 0.0,
                "estimated_waste": 0.0,
                "waste_percentage": 0.0,
                "recommendations": []
            }

        since = datetime.utcnow() - timedelta(days=days)

        # Get events for analysis
        events = (
            self.db_session.query(Event)
            .filter(
                Event.project_id == self.project_id,
                Event.timestamp >= since,
                Event.success == True
            )
            .all()
        )

        if not events:
            return {
                "total_spend": 0.0,
                "estimated_waste": 0.0,
                "waste_percentage": 0.0,
                "recommendations": []
            }

        total_spend = sum(e.cost for e in events)
        recommendations = []

        # Detect high token usage
        avg_tokens = sum(e.total_tokens for e in events) / len(events) if events else 0
        high_token_events = [e for e in events if e.total_tokens > avg_tokens * 2]

        if high_token_events:
            waste_cost = sum(e.cost for e in high_token_events)
            recommendations.append({
                "type": "high_token_usage",
                "severity": "medium",
                "impact": waste_cost,
                "count": len(high_token_events),
                "message": f"{len(high_token_events)} calls used 2x+ average tokens",
                "suggestion": "Review prompts for redundant context or use smaller models"
            })

        # Detect high error rates
        error_events = (
            self.db_session.query(Event)
            .filter(
                Event.project_id == self.project_id,
                Event.timestamp >= since,
                Event.success == False
            )
            .all()
        )

        if error_events:
            error_cost = sum(e.cost for e in error_events)
            error_rate = len(error_events) / (len(events) + len(error_events))
            if error_rate > 0.05:  # >5% error rate
                recommendations.append({
                    "type": "high_error_rate",
                    "severity": "high",
                    "impact": error_cost,
                    "count": len(error_events),
                    "error_rate": error_rate,
                    "message": f"{error_rate*100:.1f}% error rate wasting ${error_cost:.2f}",
                    "suggestion": "Investigate and fix common errors to reduce retry costs"
                })

        # Detect expensive model overuse
        model_costs = {}
        for event in events:
            model = event.model or "unknown"
            if model not in model_costs:
                model_costs[model] = {"count": 0, "cost": 0.0}
            model_costs[model]["count"] += 1
            model_costs[model]["cost"] += event.cost

        if model_costs:
            most_expensive = max(model_costs.items(), key=lambda x: x[1]["cost"])
            if most_expensive[1]["cost"] / total_spend > 0.5:  # >50% of total spend
                recommendations.append({
                    "type": "expensive_model_overuse",
                    "severity": "medium",
                    "impact": most_expensive[1]["cost"],
                    "model": most_expensive[0],
                    "count": most_expensive[1]["count"],
                    "message": f"{most_expensive[0]} accounts for {most_expensive[1]['cost']/total_spend*100:.1f}% of spend",
                    "suggestion": "Consider using cheaper models for simpler tasks"
                })

        estimated_waste = sum(r["impact"] for r in recommendations)
        waste_percentage = (estimated_waste / total_spend * 100) if total_spend > 0 else 0

        return {
            "total_spend": total_spend,
            "estimated_waste": estimated_waste,
            "waste_percentage": waste_percentage,
            "recommendations": sorted(recommendations, key=lambda x: x["impact"], reverse=True)
        }

    def suggest_model_downgrade(self, current_model: str, task_complexity: str = "medium") -> Optional[str]:
        """
        Suggest a cheaper model for the given task complexity.
        """
        model_tiers = {
            "high": ["gpt-4-turbo", "claude-opus-4", "gpt-4"],
            "medium": ["gpt-3.5-turbo", "claude-sonnet-3.5", "gpt-3.5"],
            "low": ["gpt-3.5-turbo-0125", "claude-haiku-3"]
        }

        current_lower = current_model.lower()

        # Find current tier
        current_tier = None
        for tier, models in model_tiers.items():
            if any(m.lower() in current_lower for m in models):
                current_tier = tier
                break

        if not current_tier:
            return None

        # Suggest downgrade based on task complexity
        if task_complexity == "low" and current_tier in ["high", "medium"]:
            return model_tiers["low"][0]
        elif task_complexity == "medium" and current_tier == "high":
            return model_tiers["medium"][0]

        return None
