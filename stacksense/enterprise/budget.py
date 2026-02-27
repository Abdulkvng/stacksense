"""
Budget Enforcement & Circuit Breakers - PRODUCTION GRADE

Manages per-team, per-feature, or global spend limits with automatic
circuit breaking when limits are approached.

Phase 1 Fixes:
- Atomic updates for race condition prevention
- Transaction rollback handling
- Input validation with Pydantic
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import update

from stacksense.database.models import Budget
from stacksense.enterprise.schemas import BudgetCreate, BudgetUpdate
from stacksense.logger.logger import get_logger

logger = get_logger(__name__)


class BudgetEnforcer:
    """
    Enforce budget limits and trigger circuit breakers.

    Production-grade implementation with:
    - Atomic database updates
    - Proper transaction handling
    - Input validation
    """

    def __init__(self, db_session: Optional[Session] = None, user_id: Optional[int] = None):
        self.db_session = db_session
        self.user_id = user_id

    def check_budget(
        self,
        cost: float,
        scope: str = "global",
        scope_value: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if a cost would exceed budget limits.

        Args:
            cost: The cost to check
            scope: Budget scope ('global', 'team', 'feature', 'provider')
            scope_value: The specific scope value (team name, feature name, etc.)

        Returns:
            dict: {
                "allowed": bool,
                "action": str,  # 'allow', 'block', 'downgrade', 'alert'
                "downgrade_model": str or None,
                "budget_remaining": float,
                "budget_utilization": float,  # 0.0-1.0
                "message": str
            }
        """
        if not self.db_session or not self.user_id:
            return {
                "allowed": True,
                "action": "allow",
                "downgrade_model": None,
                "budget_remaining": float('inf'),
                "budget_utilization": 0.0,
                "message": "No budget enforcement configured"
            }

        try:
            # Find applicable budgets
            now = datetime.utcnow()
            budgets = (
                self.db_session.query(Budget)
                .filter(
                    Budget.user_id == self.user_id,
                    Budget.is_active == True,
                    Budget.scope == scope,
                    Budget.period_start <= now,
                    Budget.period_end >= now
                )
            )

            if scope_value:
                budgets = budgets.filter(Budget.scope_value == scope_value)

            budget = budgets.first()

            if not budget:
                return {
                    "allowed": True,
                    "action": "allow",
                    "downgrade_model": None,
                    "budget_remaining": float('inf'),
                    "budget_utilization": 0.0,
                    "message": f"No active budget found for {scope}/{scope_value}"
                }

            # Calculate budget status
            projected_spend = budget.current_spend + cost
            budget_remaining = budget.limit_amount - budget.current_spend
            budget_utilization = projected_spend / budget.limit_amount if budget.limit_amount > 0 else 0.0

            # Determine action based on utilization
            if projected_spend > budget.limit_amount:
                # Budget exceeded
                if budget.action == "block":
                    return {
                        "allowed": False,
                        "action": "block",
                        "downgrade_model": None,
                        "budget_remaining": budget_remaining,
                        "budget_utilization": budget_utilization,
                        "message": f"Budget limit exceeded for {scope}/{scope_value}"
                    }
                elif budget.action == "downgrade":
                    return {
                        "allowed": True,
                        "action": "downgrade",
                        "downgrade_model": budget.downgrade_model,
                        "budget_remaining": budget_remaining,
                        "budget_utilization": budget_utilization,
                        "message": f"Downgrading model due to budget limit"
                    }
                else:  # alert
                    return {
                        "allowed": True,
                        "action": "alert",
                        "downgrade_model": None,
                        "budget_remaining": budget_remaining,
                        "budget_utilization": budget_utilization,
                        "message": f"Budget limit exceeded - alerting only"
                    }

            elif budget_utilization >= 0.9:
                # Approaching limit (90%+)
                return {
                    "allowed": True,
                    "action": "alert",
                    "downgrade_model": None,
                    "budget_remaining": budget_remaining,
                    "budget_utilization": budget_utilization,
                    "message": f"Budget at {budget_utilization*100:.1f}% utilization"
                }

            else:
                return {
                    "allowed": True,
                    "action": "allow",
                    "downgrade_model": None,
                    "budget_remaining": budget_remaining,
                    "budget_utilization": budget_utilization,
                    "message": "Within budget limits"
                }

        except Exception as e:
            logger.error(f"Error checking budget: {e}", exc_info=True)
            # Fail open - allow request but log error
            return {
                "allowed": True,
                "action": "allow",
                "downgrade_model": None,
                "budget_remaining": 0.0,
                "budget_utilization": 0.0,
                "message": f"Budget check failed: {str(e)}"
            }

    def record_spend(
        self,
        cost: float,
        scope: str = "global",
        scope_value: Optional[str] = None
    ) -> bool:
        """
        Record actual spend against the budget using atomic update.

        CRITICAL FIX: Uses database-level atomic operation to prevent race conditions.

        Returns:
            bool: True if spend was recorded successfully
        """
        if not self.db_session or not self.user_id:
            return False

        try:
            now = datetime.utcnow()

            # ATOMIC UPDATE: Use SQLAlchemy update() with WHERE clause
            # This prevents race conditions from concurrent requests
            stmt = (
                update(Budget)
                .where(
                    Budget.user_id == self.user_id,
                    Budget.is_active == True,
                    Budget.scope == scope,
                    Budget.period_start <= now,
                    Budget.period_end >= now
                )
                .values(
                    current_spend=Budget.current_spend + cost,
                    updated_at=datetime.utcnow()
                )
                .returning(Budget)
            )

            if scope_value:
                stmt = stmt.where(Budget.scope_value == scope_value)

            result = self.db_session.execute(stmt)
            self.db_session.commit()

            budget = result.scalar_one_or_none()

            if not budget:
                logger.warning(f"No budget found to record spend for {scope}/{scope_value}")
                return False

            logger.info(
                f"Recorded ${cost:.4f} spend for {scope}/{scope_value}. "
                f"Total: ${budget.current_spend:.4f}/{budget.limit_amount:.2f}"
            )
            return True

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to record spend: {e}", exc_info=True)
            return False

    def create_budget(self, data: BudgetCreate) -> Budget:
        """
        Create a new budget with input validation.

        Args:
            data: Validated BudgetCreate schema

        Returns:
            Budget: Created budget instance

        Raises:
            ValueError: If validation fails or database error occurs
        """
        if not self.db_session or not self.user_id:
            raise ValueError("Database session and user_id required")

        try:
            # Calculate period boundaries
            now = datetime.utcnow()
            period_start, period_end = self._calculate_period(now, data.limit_period)

            budget = Budget(
                user_id=self.user_id,
                name=data.name,
                scope=data.scope,
                scope_value=data.scope_value,
                limit_amount=data.limit_amount,
                limit_period=data.limit_period,
                current_spend=0.0,
                period_start=period_start,
                period_end=period_end,
                action=data.action,
                downgrade_model=data.downgrade_model,
                is_active=True
            )

            self.db_session.add(budget)
            self.db_session.commit()
            self.db_session.refresh(budget)

            logger.info(f"Created budget '{data.name}' for user {self.user_id}")
            return budget

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to create budget: {e}", exc_info=True)
            raise ValueError(f"Failed to create budget: {str(e)}")

    def update_budget(self, budget_id: int, data: BudgetUpdate) -> Budget:
        """
        Update an existing budget with validation.

        Args:
            budget_id: ID of budget to update
            data: Validated BudgetUpdate schema

        Returns:
            Budget: Updated budget instance

        Raises:
            ValueError: If budget not found or update fails
        """
        if not self.db_session or not self.user_id:
            raise ValueError("Database session and user_id required")

        try:
            budget = (
                self.db_session.query(Budget)
                .filter(
                    Budget.id == budget_id,
                    Budget.user_id == self.user_id
                )
                .first()
            )

            if not budget:
                raise ValueError(f"Budget {budget_id} not found")

            # Update only provided fields
            update_data = data.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(budget, key, value)

            budget.updated_at = datetime.utcnow()

            self.db_session.commit()
            self.db_session.refresh(budget)

            logger.info(f"Updated budget {budget_id} for user {self.user_id}")
            return budget

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to update budget: {e}", exc_info=True)
            raise ValueError(f"Failed to update budget: {str(e)}")

    def _calculate_period(self, start_time: datetime, period: str) -> tuple:
        """Calculate period start and end times."""
        if period == "hourly":
            period_start = start_time.replace(minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(hours=1)
        elif period == "daily":
            period_start = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)
        elif period == "weekly":
            period_start = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
            period_start -= timedelta(days=period_start.weekday())
            period_end = period_start + timedelta(weeks=1)
        elif period == "monthly":
            period_start = start_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1)
        else:
            raise ValueError(f"Invalid period: {period}")

        return period_start, period_end

    def get_budgets(self, include_inactive: bool = False) -> List[Budget]:
        """Get all budgets for the user."""
        if not self.db_session or not self.user_id:
            return []

        try:
            query = self.db_session.query(Budget).filter(Budget.user_id == self.user_id)

            if not include_inactive:
                query = query.filter(Budget.is_active == True)

            return query.all()

        except Exception as e:
            logger.error(f"Failed to get budgets: {e}", exc_info=True)
            return []

    def reset_budget_period(self, budget_id: int) -> Optional[Budget]:
        """Reset a budget's period and spend."""
        if not self.db_session or not self.user_id:
            return None

        try:
            budget = (
                self.db_session.query(Budget)
                .filter(
                    Budget.id == budget_id,
                    Budget.user_id == self.user_id
                )
                .first()
            )

            if not budget:
                return None

            now = datetime.utcnow()
            period_start, period_end = self._calculate_period(now, budget.limit_period)

            budget.period_start = period_start
            budget.period_end = period_end
            budget.current_spend = 0.0
            budget.updated_at = now

            self.db_session.commit()
            self.db_session.refresh(budget)

            logger.info(f"Reset budget period for budget {budget_id}")
            return budget

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to reset budget period: {e}", exc_info=True)
            return None

    def delete_budget(self, budget_id: int) -> bool:
        """Delete a budget."""
        if not self.db_session or not self.user_id:
            return False

        try:
            budget = (
                self.db_session.query(Budget)
                .filter(
                    Budget.id == budget_id,
                    Budget.user_id == self.user_id
                )
                .first()
            )

            if not budget:
                return False

            self.db_session.delete(budget)
            self.db_session.commit()

            logger.info(f"Deleted budget {budget_id} for user {self.user_id}")
            return True

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to delete budget: {e}", exc_info=True)
            return False
