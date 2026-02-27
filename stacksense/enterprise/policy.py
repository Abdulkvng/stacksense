"""
Enterprise Policy Engine

Enforce model allowlists, PII detection, data residency, and compliance rules.
"""

import re
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from stacksense.database.models import Policy
from stacksense.logger.logger import get_logger

logger = get_logger(__name__)


class PolicyEngine:
    """
    Enforce enterprise policies and compliance rules.
    """

    def __init__(self, db_session: Optional[Session] = None, user_id: Optional[int] = None):
        self.db_session = db_session
        self.user_id = user_id

    def check_policy(
        self,
        policy_type: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if data complies with policies.

        Args:
            policy_type: Type of policy to check
            data: Data to validate against policy

        Returns:
            dict: {
                "compliant": bool,
                "violations": List[str],
                "enforcement_level": str,
                "policy_name": str
            }
        """
        if not self.db_session or not self.user_id:
            return {
                "compliant": True,
                "violations": [],
                "enforcement_level": "advisory",
                "policy_name": None
            }

        # Get active policies of this type
        policies = (
            self.db_session.query(Policy)
            .filter(
                Policy.user_id == self.user_id,
                Policy.policy_type == policy_type,
                Policy.is_active == True
            )
            .all()
        )

        if not policies:
            return {
                "compliant": True,
                "violations": [],
                "enforcement_level": "advisory",
                "policy_name": None
            }

        all_violations = []
        enforcement_level = "advisory"

        for policy in policies:
            violations = self._evaluate_policy(policy, data)
            if violations:
                all_violations.extend(violations)
                if policy.enforcement_level == "blocking":
                    enforcement_level = "blocking"

        return {
            "compliant": len(all_violations) == 0,
            "violations": all_violations,
            "enforcement_level": enforcement_level,
            "policy_name": policies[0].name if policies else None
        }

    def _evaluate_policy(self, policy: Policy, data: Dict[str, Any]) -> List[str]:
        """Evaluate a specific policy against data."""
        violations = []

        if policy.policy_type == "model_allowlist":
            violations.extend(self._check_model_allowlist(policy.rules, data))
        elif policy.policy_type == "pii_detection":
            violations.extend(self._check_pii(policy.rules, data))
        elif policy.policy_type == "data_residency":
            violations.extend(self._check_data_residency(policy.rules, data))

        return violations

    def _check_model_allowlist(self, rules: Dict[str, Any], data: Dict[str, Any]) -> List[str]:
        """Check if model is in allowlist."""
        violations = []
        allowed_models = rules.get("allowed_models", [])
        model = data.get("model", "")

        if allowed_models and model not in allowed_models:
            violations.append(f"Model '{model}' not in allowlist: {allowed_models}")

        return violations

    def _check_pii(self, rules: Dict[str, Any], data: Dict[str, Any]) -> List[str]:
        """Basic PII detection in prompts."""
        violations = []
        prompt = data.get("prompt", "")

        # Basic regex patterns for PII
        patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
        }

        for pii_type, pattern in patterns.items():
            if re.search(pattern, prompt):
                violations.append(f"Potential {pii_type} detected in prompt")

        return violations

    def _check_data_residency(self, rules: Dict[str, Any], data: Dict[str, Any]) -> List[str]:
        """Check data residency requirements."""
        violations = []
        allowed_regions = rules.get("allowed_regions", [])
        provider = data.get("provider", "")

        # Map providers to regions (simplified)
        provider_regions = {
            "openai": "us",
            "anthropic": "us",
            "google": "us-eu"
        }

        provider_region = provider_regions.get(provider, "unknown")

        if allowed_regions and provider_region not in allowed_regions:
            violations.append(
                f"Provider '{provider}' region '{provider_region}' not in allowed regions: {allowed_regions}"
            )

        return violations

    def create_policy(
        self,
        name: str,
        policy_type: str,
        rules: Dict[str, Any],
        enforcement_level: str = "advisory"
    ) -> Policy:
        """Create a new policy."""
        if not self.db_session or not self.user_id:
            raise ValueError("Database session and user_id required")

        policy = Policy(
            user_id=self.user_id,
            name=name,
            policy_type=policy_type,
            rules=rules,
            enforcement_level=enforcement_level,
            is_active=True
        )

        self.db_session.add(policy)
        self.db_session.commit()
        self.db_session.refresh(policy)

        logger.info(f"Created policy '{name}' for user {self.user_id}")
        return policy

    def get_policies(self, policy_type: Optional[str] = None) -> List[Policy]:
        """Get all policies for the user."""
        if not self.db_session or not self.user_id:
            return []

        query = self.db_session.query(Policy).filter(Policy.user_id == self.user_id)

        if policy_type:
            query = query.filter(Policy.policy_type == policy_type)

        return query.all()

    def delete_policy(self, policy_id: int) -> bool:
        """Delete a policy."""
        if not self.db_session or not self.user_id:
            return False

        policy = (
            self.db_session.query(Policy)
            .filter(
                Policy.id == policy_id,
                Policy.user_id == self.user_id
            )
            .first()
        )

        if not policy:
            return False

        self.db_session.delete(policy)
        self.db_session.commit()

        logger.info(f"Deleted policy {policy_id} for user {self.user_id}")
        return True
