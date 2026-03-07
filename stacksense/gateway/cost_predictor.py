"""
Cost Predictor - Monthly Overrun Forecasting

Predicts future costs and detects budget overruns before they happen:
- Monthly spend forecasting
- Trend analysis
- Anomaly detection
- Budget projection
- What-if scenarios
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

from stacksense.logger.logger import get_logger

logger = get_logger(__name__)


class CostPredictor:
    """
    Predicts and forecasts LLM costs.

    Capabilities:
    - Monthly overrun prediction
    - Trend-based forecasting
    - Cost scenario simulation
    - Anomaly detection
    """

    def __init__(self, db_session=None, user_id: Optional[int] = None):
        self.db_session = db_session
        self.user_id = user_id

        # Historical cost tracking
        self.daily_costs = defaultdict(float)  # date -> cost
        self.hourly_costs = defaultdict(float)  # hour -> cost
        self.model_costs = defaultdict(float)  # model -> cost

        logger.info("Cost Predictor initialized")

    def predict_monthly_cost(
        self, current_spend: float, days_elapsed: int, days_in_month: int = 30
    ) -> Dict[str, Any]:
        """
        Predict end-of-month cost based on current spend.

        Methods:
        1. Linear projection (simple)
        2. Trend-adjusted projection (if acceleration detected)

        Args:
            current_spend: Spend so far this month
            days_elapsed: Days elapsed in current month
            days_in_month: Total days in month

        Returns:
            dict: {
                "predicted_monthly_cost": float,
                "projection_method": str,
                "confidence": float,
                "days_remaining": int,
                "daily_average": float,
                "trend": str  # "accelerating", "stable", "decelerating"
            }
        """
        if days_elapsed == 0:
            return {
                "predicted_monthly_cost": 0.0,
                "projection_method": "insufficient_data",
                "confidence": 0.0,
                "days_remaining": days_in_month,
                "daily_average": 0.0,
                "trend": "unknown",
            }

        # Calculate daily average
        daily_average = current_spend / days_elapsed
        days_remaining = days_in_month - days_elapsed

        # Linear projection
        linear_prediction = current_spend + (daily_average * days_remaining)

        # Detect trend
        trend, trend_factor = self._detect_trend()

        # Trend-adjusted projection
        if trend == "accelerating":
            predicted_cost = linear_prediction * trend_factor
            method = "trend_adjusted_acceleration"
            confidence = 0.7
        elif trend == "decelerating":
            predicted_cost = linear_prediction * trend_factor
            method = "trend_adjusted_deceleration"
            confidence = 0.7
        else:
            predicted_cost = linear_prediction
            method = "linear_projection"
            confidence = 0.85

        logger.info(
            f"Monthly cost prediction: ${predicted_cost:.2f} " f"(method={method}, trend={trend})"
        )

        return {
            "predicted_monthly_cost": predicted_cost,
            "projection_method": method,
            "confidence": confidence,
            "days_remaining": days_remaining,
            "daily_average": daily_average,
            "trend": trend,
        }

    def check_budget_overrun(
        self,
        current_spend: float,
        monthly_budget: float,
        days_elapsed: int,
        days_in_month: int = 30,
    ) -> Dict[str, Any]:
        """
        Check if current trajectory will exceed monthly budget.

        Returns:
            dict: {
                "will_exceed": bool,
                "predicted_cost": float,
                "budget": float,
                "overage": float,
                "overage_percent": float,
                "days_until_exceeded": int or None,
                "recommended_action": str
            }
        """
        prediction = self.predict_monthly_cost(current_spend, days_elapsed, days_in_month)
        predicted_cost = prediction["predicted_monthly_cost"]

        will_exceed = predicted_cost > monthly_budget
        overage = max(0, predicted_cost - monthly_budget)
        overage_percent = (overage / monthly_budget * 100) if monthly_budget > 0 else 0

        # Estimate days until budget exceeded
        days_until_exceeded = None
        if will_exceed and prediction["daily_average"] > 0:
            budget_remaining = monthly_budget - current_spend
            days_until_exceeded = int(budget_remaining / prediction["daily_average"])

        # Recommend action
        if overage_percent > 50:
            action = "immediate_throttling_required"
        elif overage_percent > 20:
            action = "enable_cost_controls"
        elif overage_percent > 0:
            action = "monitor_closely"
        else:
            action = "on_track"

        if will_exceed:
            logger.warning(
                f"Budget overrun predicted: ${predicted_cost:.2f} > ${monthly_budget:.2f} "
                f"({overage_percent:.1f}% over)"
            )

        return {
            "will_exceed": will_exceed,
            "predicted_cost": predicted_cost,
            "budget": monthly_budget,
            "overage": overage,
            "overage_percent": overage_percent,
            "days_until_exceeded": days_until_exceeded,
            "recommended_action": action,
        }

    def simulate_scenario(
        self, scenario: Dict[str, Any], current_spend: float, days_elapsed: int
    ) -> Dict[str, Any]:
        """
        Simulate "what if" cost scenarios.

        Scenarios:
        - Switch to cheaper model
        - Enable prompt optimization
        - Reduce request rate
        - Mix of strategies

        Args:
            scenario: {
                "model_switch": {"from": "gpt-4", "to": "gpt-4o-mini"},
                "optimization_enabled": bool,
                "rate_reduction": float  # 0.0-1.0 (0.2 = 20% reduction)
            }

        Returns:
            dict: {
                "projected_cost": float,
                "savings": float,
                "savings_percent": float,
                "scenario_description": str
            }
        """
        daily_average = current_spend / days_elapsed if days_elapsed > 0 else 0
        days_remaining = 30 - days_elapsed

        # Start with baseline
        baseline_cost = current_spend + (daily_average * days_remaining)
        projected_daily = daily_average

        changes = []

        # Model switch savings
        if "model_switch" in scenario:
            switch = scenario["model_switch"]
            cost_reduction = self._estimate_model_switch_savings(
                switch.get("from"), switch.get("to")
            )
            projected_daily *= 1 - cost_reduction
            changes.append(f"switch {switch.get('from')} → {switch.get('to')}")

        # Optimization savings (15-30% typical)
        if scenario.get("optimization_enabled"):
            projected_daily *= 0.80  # 20% reduction
            changes.append("enable optimization")

        # Rate reduction
        if "rate_reduction" in scenario:
            reduction = scenario["rate_reduction"]
            projected_daily *= 1 - reduction
            changes.append(f"reduce rate by {reduction*100:.0f}%")

        # Calculate new projection
        projected_cost = current_spend + (projected_daily * days_remaining)
        savings = baseline_cost - projected_cost
        savings_percent = (savings / baseline_cost * 100) if baseline_cost > 0 else 0

        description = "Scenario: " + ", ".join(changes) if changes else "No changes"

        logger.info(
            f"Scenario simulation: {description} → "
            f"${projected_cost:.2f} (saves ${savings:.2f}, {savings_percent:.1f}%)"
        )

        return {
            "projected_cost": projected_cost,
            "savings": savings,
            "savings_percent": savings_percent,
            "scenario_description": description,
        }

    def detect_anomaly(self, current_cost: float, window_size: int = 7) -> Dict[str, Any]:
        """
        Detect cost anomalies (unexpected spikes).

        Uses moving average + standard deviation threshold.

        Returns:
            dict: {
                "is_anomaly": bool,
                "severity": str,  # "normal", "warning", "critical"
                "deviation": float,
                "expected_range": tuple
            }
        """
        if len(self.daily_costs) < window_size:
            return {
                "is_anomaly": False,
                "severity": "normal",
                "deviation": 0.0,
                "expected_range": (0.0, float("inf")),
            }

        # Get recent costs
        recent_costs = list(self.daily_costs.values())[-window_size:]

        # Calculate statistics
        mean = statistics.mean(recent_costs)
        stdev = statistics.stdev(recent_costs) if len(recent_costs) > 1 else 0

        # Expected range (mean ± 2 std dev)
        lower_bound = max(0, mean - 2 * stdev)
        upper_bound = mean + 2 * stdev

        # Check if current cost is anomaly
        is_anomaly = current_cost > upper_bound
        deviation = (current_cost - mean) / mean if mean > 0 else 0

        # Severity
        if deviation > 2.0:  # 200%+ over average
            severity = "critical"
        elif deviation > 0.5:  # 50%+ over average
            severity = "warning"
        else:
            severity = "normal"

        if is_anomaly:
            logger.warning(
                f"Cost anomaly detected: ${current_cost:.2f} "
                f"(expected: ${lower_bound:.2f}-${upper_bound:.2f})"
            )

        return {
            "is_anomaly": is_anomaly,
            "severity": severity,
            "deviation": deviation,
            "expected_range": (lower_bound, upper_bound),
        }

    def record_cost(self, date: datetime, cost: float, model: str):
        """Record cost for future predictions."""
        date_key = date.strftime("%Y-%m-%d")
        hour_key = date.strftime("%Y-%m-%d-%H")

        self.daily_costs[date_key] += cost
        self.hourly_costs[hour_key] += cost
        self.model_costs[model] += cost

    def _detect_trend(self) -> Tuple[str, float]:
        """
        Detect cost trend (accelerating, stable, decelerating).

        Returns:
            tuple: (trend_name, trend_factor)
        """
        if len(self.daily_costs) < 3:
            return "unknown", 1.0

        # Get last 7 days
        recent_costs = sorted(self.daily_costs.items())[-7:]
        costs = [c[1] for c in recent_costs]

        # Compare first half vs second half
        mid = len(costs) // 2
        first_half_avg = statistics.mean(costs[:mid]) if costs[:mid] else 0
        second_half_avg = statistics.mean(costs[mid:]) if costs[mid:] else 0

        if first_half_avg == 0:
            return "stable", 1.0

        # Calculate trend
        growth_rate = (second_half_avg - first_half_avg) / first_half_avg

        if growth_rate > 0.2:  # 20%+ growth
            return "accelerating", 1.2  # Expect 20% continued growth
        elif growth_rate < -0.2:  # 20%+ decline
            return "decelerating", 0.8  # Expect 20% continued decline
        else:
            return "stable", 1.0

    def _estimate_model_switch_savings(self, from_model: str, to_model: str) -> float:
        """
        Estimate cost savings from model switch.

        Returns:
            float: Savings as decimal (0.5 = 50% savings)
        """
        # Model pricing (simplified)
        pricing = {
            "gpt-4": 1.0,
            "gpt-4-turbo": 0.33,
            "gpt-4o": 0.17,
            "gpt-4o-mini": 0.005,
            "claude-3-opus": 0.50,
            "claude-3-sonnet": 0.10,
            "claude-3-haiku": 0.008,
        }

        from_cost = pricing.get(from_model, 1.0)
        to_cost = pricing.get(to_model, 1.0)

        savings = (from_cost - to_cost) / from_cost if from_cost > 0 else 0
        return max(0, savings)  # Never negative savings
