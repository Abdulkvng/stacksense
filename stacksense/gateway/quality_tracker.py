"""
Quality Tracker - Auto-Tier Selection

Tracks response quality to enable smart tier dropping:
- Response length/completeness
- Error rates by model
- User feedback signals
- Cost-per-quality scoring
- Auto-tier recommendations
"""

from typing import Dict, Any, Optional, List
from collections import defaultdict
from datetime import datetime
import statistics

from stacksense.logger.logger import get_logger

logger = get_logger(__name__)


class QualityTracker:
    """
    Tracks LLM response quality for intelligent tier selection.

    Capabilities:
    - Quality scoring per model
    - Cost-per-quality analysis
    - Tier downgrade recommendations
    - Performance benchmarking
    """

    def __init__(self, db_session=None, user_id: Optional[int] = None):
        self.db_session = db_session
        self.user_id = user_id

        # Quality metrics by model
        self.model_metrics = defaultdict(lambda: {
            "response_count": 0,
            "avg_response_length": 0.0,
            "avg_latency": 0.0,
            "error_rate": 0.0,
            "quality_scores": [],  # Rolling window of quality scores
            "cost_per_response": 0.0,
            "last_updated": None
        })

        # Model tier hierarchy (for downgrade suggestions)
        self.tier_hierarchy = {
            "premium": ["gpt-4", "claude-3-opus"],
            "high": ["gpt-4-turbo", "claude-3-sonnet"],
            "medium": ["gpt-4o", "gemini-pro"],
            "budget": ["gpt-4o-mini", "claude-3-haiku", "gemini-flash"]
        }

        # Quality thresholds
        self.thresholds = {
            "excellent": 0.95,
            "good": 0.85,
            "acceptable": 0.70,
            "poor": 0.50
        }

        logger.info("Quality Tracker initialized")

    def track_response(
        self,
        model: str,
        response: Any,
        cost: float,
        latency: float,
        error: bool = False,
        user_feedback: Optional[float] = None
    ):
        """
        Track response quality metrics.

        Args:
            model: Model used
            response: Response content
            cost: Cost of request
            latency: Response latency in ms
            error: Whether request failed
            user_feedback: Optional user rating (0-1)
        """
        metrics = self.model_metrics[model]

        # Update counts
        metrics["response_count"] += 1

        # Calculate quality score
        quality_score = self._calculate_quality_score(
            response=response,
            latency=latency,
            error=error,
            user_feedback=user_feedback
        )

        # Update rolling quality scores (last 100 responses)
        metrics["quality_scores"].append(quality_score)
        if len(metrics["quality_scores"]) > 100:
            metrics["quality_scores"].pop(0)

        # Update averages
        if not error and response:
            response_length = len(str(response))
            metrics["avg_response_length"] = (
                (metrics["avg_response_length"] * (metrics["response_count"] - 1) + response_length) /
                metrics["response_count"]
            )

        metrics["avg_latency"] = (
            (metrics["avg_latency"] * (metrics["response_count"] - 1) + latency) /
            metrics["response_count"]
        )

        # Update error rate
        if error:
            error_count = metrics["error_rate"] * (metrics["response_count"] - 1) + 1
            metrics["error_rate"] = error_count / metrics["response_count"]

        # Update cost per response
        metrics["cost_per_response"] = (
            (metrics["cost_per_response"] * (metrics["response_count"] - 1) + cost) /
            metrics["response_count"]
        )

        metrics["last_updated"] = datetime.utcnow()

        logger.debug(
            f"Quality tracked: {model} - score={quality_score:.2f}, "
            f"latency={latency:.0f}ms, cost=${cost:.4f}"
        )

    def _calculate_quality_score(
        self,
        response: Any,
        latency: float,
        error: bool,
        user_feedback: Optional[float] = None
    ) -> float:
        """
        Calculate quality score (0-1).

        Factors:
        - Response completeness (length)
        - Latency (faster is better)
        - Error status
        - User feedback (if available)

        Returns:
            Quality score between 0 and 1
        """
        if error:
            return 0.0

        score = 1.0

        # User feedback override (if provided)
        if user_feedback is not None:
            return max(0.0, min(1.0, user_feedback))

        # Penalize very short responses (likely incomplete)
        if response:
            response_length = len(str(response))
            if response_length < 50:
                score *= 0.5  # Very short
            elif response_length < 200:
                score *= 0.8  # Short

        # Penalize high latency
        if latency > 5000:  # >5s
            score *= 0.7
        elif latency > 3000:  # >3s
            score *= 0.85
        elif latency > 2000:  # >2s
            score *= 0.95

        return max(0.0, min(1.0, score))

    def get_model_quality(self, model: str) -> Dict[str, Any]:
        """
        Get quality metrics for a model.

        Returns:
            dict: {
                "avg_quality": float,
                "quality_rating": str,
                "response_count": int,
                "error_rate": float,
                "avg_latency": float,
                "cost_per_response": float,
                "cost_per_quality": float
            }
        """
        metrics = self.model_metrics[model]

        if not metrics["quality_scores"]:
            return {
                "avg_quality": 0.0,
                "quality_rating": "unknown",
                "response_count": 0,
                "error_rate": 0.0,
                "avg_latency": 0.0,
                "cost_per_response": 0.0,
                "cost_per_quality": 0.0
            }

        # Calculate average quality
        avg_quality = statistics.mean(metrics["quality_scores"])

        # Determine rating
        if avg_quality >= self.thresholds["excellent"]:
            rating = "excellent"
        elif avg_quality >= self.thresholds["good"]:
            rating = "good"
        elif avg_quality >= self.thresholds["acceptable"]:
            rating = "acceptable"
        else:
            rating = "poor"

        # Cost per quality point
        cost_per_quality = (
            metrics["cost_per_response"] / avg_quality
            if avg_quality > 0
            else float('inf')
        )

        return {
            "avg_quality": avg_quality,
            "quality_rating": rating,
            "response_count": metrics["response_count"],
            "error_rate": metrics["error_rate"],
            "avg_latency": metrics["avg_latency"],
            "cost_per_response": metrics["cost_per_response"],
            "cost_per_quality": cost_per_quality
        }

    def recommend_tier_downgrade(
        self,
        current_model: str,
        min_quality_threshold: float = 0.85
    ) -> Optional[Dict[str, Any]]:
        """
        Recommend cheaper model if quality threshold is met.

        Args:
            current_model: Current model being used
            min_quality_threshold: Minimum acceptable quality

        Returns:
            dict with recommendation or None if no downgrade possible
        """
        current_quality = self.get_model_quality(current_model)

        # Check if current model meets quality threshold
        if current_quality["avg_quality"] < min_quality_threshold:
            return None  # Don't downgrade if already struggling

        # Find current tier
        current_tier = None
        for tier, models in self.tier_hierarchy.items():
            if current_model in models:
                current_tier = tier
                break

        if not current_tier:
            return None

        # Find cheaper tiers
        tier_order = ["premium", "high", "medium", "budget"]
        current_tier_index = tier_order.index(current_tier)

        # Check each cheaper tier
        for tier in tier_order[current_tier_index + 1:]:
            tier_models = self.tier_hierarchy[tier]

            # Find best model in this tier
            best_candidate = None
            best_quality = 0.0

            for candidate_model in tier_models:
                candidate_quality = self.get_model_quality(candidate_model)

                # Must have sufficient data and meet threshold
                if (candidate_quality["response_count"] >= 10 and
                    candidate_quality["avg_quality"] >= min_quality_threshold):

                    if candidate_quality["avg_quality"] > best_quality:
                        best_quality = candidate_quality["avg_quality"]
                        best_candidate = candidate_model

            # Found viable downgrade
            if best_candidate:
                candidate_quality = self.get_model_quality(best_candidate)
                cost_savings = (
                    (current_quality["cost_per_response"] - candidate_quality["cost_per_response"]) /
                    current_quality["cost_per_response"] * 100
                    if current_quality["cost_per_response"] > 0
                    else 0
                )

                logger.info(
                    f"Downgrade opportunity: {current_model} → {best_candidate} "
                    f"(quality: {current_quality['avg_quality']:.2f} → {best_quality:.2f}, "
                    f"saves {cost_savings:.1f}%)"
                )

                return {
                    "recommended_model": best_candidate,
                    "current_quality": current_quality["avg_quality"],
                    "recommended_quality": best_quality,
                    "quality_delta": best_quality - current_quality["avg_quality"],
                    "cost_savings": cost_savings,
                    "current_cost": current_quality["cost_per_response"],
                    "recommended_cost": candidate_quality["cost_per_response"]
                }

        return None

    def get_quality_leaderboard(self) -> List[Dict[str, Any]]:
        """
        Get models ranked by cost-per-quality.

        Returns:
            List of models sorted by best value (lowest cost per quality point)
        """
        leaderboard = []

        for model, metrics in self.model_metrics.items():
            if metrics["response_count"] < 5:
                continue  # Need minimum data

            quality_data = self.get_model_quality(model)

            leaderboard.append({
                "model": model,
                "avg_quality": quality_data["avg_quality"],
                "quality_rating": quality_data["quality_rating"],
                "cost_per_quality": quality_data["cost_per_quality"],
                "cost_per_response": quality_data["cost_per_response"],
                "response_count": quality_data["response_count"]
            })

        # Sort by cost-per-quality (lower is better)
        leaderboard.sort(key=lambda x: x["cost_per_quality"])

        return leaderboard

    def compare_models(
        self,
        model1: str,
        model2: str
    ) -> Dict[str, Any]:
        """
        Compare quality metrics between two models.

        Returns:
            dict: {
                "model1": quality metrics,
                "model2": quality metrics,
                "recommendation": str
            }
        """
        quality1 = self.get_model_quality(model1)
        quality2 = self.get_model_quality(model2)

        # Determine recommendation
        if quality1["cost_per_quality"] < quality2["cost_per_quality"]:
            recommendation = f"{model1} offers better value"
        elif quality2["cost_per_quality"] < quality1["cost_per_quality"]:
            recommendation = f"{model2} offers better value"
        else:
            recommendation = "Similar value"

        return {
            model1: quality1,
            model2: quality2,
            "recommendation": recommendation
        }

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get quality metrics for all tracked models."""
        return {
            model: self.get_model_quality(model)
            for model in self.model_metrics.keys()
        }
