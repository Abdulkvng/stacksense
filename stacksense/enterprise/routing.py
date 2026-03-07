"""
Dynamic Model Routing - PRODUCTION GRADE

Routes prompts to the most cost-effective model based on task complexity,
cost thresholds, and latency requirements.

Phase 1 Fixes:
- Transaction rollback handling
- Input validation with Pydantic
- Proper error handling
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from stacksense.database.models import RoutingRule
from stacksense.enterprise.schemas import RoutingRuleCreate, RoutingRuleUpdate
from stacksense.logger.logger import get_logger

logger = get_logger(__name__)


class DynamicRouter:
    """
    Intelligent model routing based on conditions and business logic.

    Production-grade implementation with:
    - Proper transaction handling
    - Input validation
    - Error handling and logging
    """

    def __init__(self, db_session: Optional[Session] = None, user_id: Optional[int] = None):
        self.db_session = db_session
        self.user_id = user_id

    def route(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Route a prompt to the appropriate model based on active routing rules.

        Args:
            prompt: The input prompt
            context: Additional context for routing (cost_threshold, task_complexity, etc.)

        Returns:
            dict: {"model": str, "provider": str, "fallback": str, "reason": str}
        """
        if not self.db_session or not self.user_id:
            return {
                "model": None,
                "provider": None,
                "fallback": None,
                "reason": "No routing rules configured",
            }

        try:
            # Get active routing rules, ordered by priority
            rules = (
                self.db_session.query(RoutingRule)
                .filter(RoutingRule.user_id == self.user_id, RoutingRule.is_active == True)
                .order_by(RoutingRule.priority.desc())
                .all()
            )

            if not rules:
                return {
                    "model": None,
                    "provider": None,
                    "fallback": None,
                    "reason": "No active routing rules found",
                }

            # Evaluate rules in priority order
            context = context or {}
            context["prompt_length"] = len(prompt)
            context["word_count"] = len(prompt.split())

            for rule in rules:
                if self._evaluate_conditions(rule.conditions, context):
                    logger.info(f"Routing rule '{rule.name}' matched for user {self.user_id}")
                    return {
                        "model": rule.target_model,
                        "provider": self._extract_provider(rule.target_model),
                        "fallback": rule.fallback_model,
                        "reason": f"Matched rule: {rule.name}",
                        "rule_id": rule.id,
                    }

            return {
                "model": None,
                "provider": None,
                "fallback": None,
                "reason": "No matching routing rules",
            }

        except Exception as e:
            logger.error(f"Error during routing: {e}", exc_info=True)
            return {
                "model": None,
                "provider": None,
                "fallback": None,
                "reason": f"Routing error: {str(e)}",
            }

    def _evaluate_conditions(self, conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Evaluate if routing conditions match the current context.

        Supports:
        - cost_threshold: max cost per call
        - task_complexity: 'low', 'medium', 'high'
        - prompt_length_min/max: character count ranges
        - word_count_min/max: word count ranges
        """
        if not conditions:
            return True

        try:
            # Cost threshold check
            if "cost_threshold" in conditions:
                max_cost = conditions["cost_threshold"]
                estimated_cost = context.get("estimated_cost", 0)
                if estimated_cost > max_cost:
                    return False

            # Task complexity check
            if "task_complexity" in conditions:
                required_complexity = conditions["task_complexity"]
                actual_complexity = context.get("task_complexity", "medium")
                if required_complexity != actual_complexity:
                    return False

            # Prompt length checks
            if "prompt_length_min" in conditions:
                if context.get("prompt_length", 0) < conditions["prompt_length_min"]:
                    return False

            if "prompt_length_max" in conditions:
                if context.get("prompt_length", 0) > conditions["prompt_length_max"]:
                    return False

            # Word count checks
            if "word_count_min" in conditions:
                if context.get("word_count", 0) < conditions["word_count_min"]:
                    return False

            if "word_count_max" in conditions:
                if context.get("word_count", 0) > conditions["word_count_max"]:
                    return False

            return True

        except Exception as e:
            logger.error(f"Error evaluating conditions: {e}")
            return False

    def _extract_provider(self, model: str) -> Optional[str]:
        """Extract provider name from model string."""
        if not model:
            return None

        model_lower = model.lower()
        if "gpt" in model_lower or "openai" in model_lower:
            return "openai"
        elif "claude" in model_lower or "anthropic" in model_lower:
            return "anthropic"
        elif "gemini" in model_lower or "google" in model_lower:
            return "google"
        elif "llama" in model_lower:
            return "meta"
        else:
            return None

    def create_rule(self, data: RoutingRuleCreate) -> RoutingRule:
        """
        Create a new routing rule with validation.

        Args:
            data: Validated RoutingRuleCreate schema

        Returns:
            RoutingRule: Created rule instance

        Raises:
            ValueError: If validation fails or database error occurs
        """
        if not self.db_session or not self.user_id:
            raise ValueError("Database session and user_id required to create rules")

        try:
            rule = RoutingRule(
                user_id=self.user_id,
                name=data.name,
                conditions=data.conditions,
                target_model=data.target_model,
                fallback_model=data.fallback_model,
                priority=data.priority,
                is_active=True,
            )

            self.db_session.add(rule)
            self.db_session.commit()
            self.db_session.refresh(rule)

            logger.info(f"Created routing rule '{data.name}' for user {self.user_id}")
            return rule

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to create routing rule: {e}", exc_info=True)
            raise ValueError(f"Failed to create routing rule: {str(e)}")

    def get_rules(self) -> List[RoutingRule]:
        """Get all routing rules for the user."""
        if not self.db_session or not self.user_id:
            return []

        try:
            return (
                self.db_session.query(RoutingRule)
                .filter(RoutingRule.user_id == self.user_id)
                .order_by(RoutingRule.priority.desc())
                .all()
            )

        except Exception as e:
            logger.error(f"Failed to get routing rules: {e}", exc_info=True)
            return []

    def update_rule(self, rule_id: int, data: RoutingRuleUpdate) -> RoutingRule:
        """
        Update an existing routing rule with validation.

        Args:
            rule_id: ID of rule to update
            data: Validated RoutingRuleUpdate schema

        Returns:
            RoutingRule: Updated rule instance

        Raises:
            ValueError: If rule not found or update fails
        """
        if not self.db_session or not self.user_id:
            raise ValueError("Database session and user_id required")

        try:
            rule = (
                self.db_session.query(RoutingRule)
                .filter(RoutingRule.id == rule_id, RoutingRule.user_id == self.user_id)
                .first()
            )

            if not rule:
                raise ValueError(f"Routing rule {rule_id} not found")

            # Update only provided fields
            update_data = data.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(rule, key, value)

            rule.updated_at = datetime.utcnow()

            self.db_session.commit()
            self.db_session.refresh(rule)

            logger.info(f"Updated routing rule {rule_id} for user {self.user_id}")
            return rule

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to update routing rule: {e}", exc_info=True)
            raise ValueError(f"Failed to update routing rule: {str(e)}")

    def delete_rule(self, rule_id: int) -> bool:
        """Delete a routing rule."""
        if not self.db_session or not self.user_id:
            return False

        try:
            rule = (
                self.db_session.query(RoutingRule)
                .filter(RoutingRule.id == rule_id, RoutingRule.user_id == self.user_id)
                .first()
            )

            if not rule:
                return False

            self.db_session.delete(rule)
            self.db_session.commit()

            logger.info(f"Deleted routing rule {rule_id} for user {self.user_id}")
            return True

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to delete routing rule: {e}", exc_info=True)
            return False
