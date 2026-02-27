"""
Pydantic schemas for input validation across all enterprise features.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, validator, Field
import math


class RoutingRuleCreate(BaseModel):
    """Schema for creating a routing rule."""
    name: str = Field(..., min_length=1, max_length=255)
    conditions: Dict[str, Any]
    target_model: str = Field(..., min_length=1, max_length=255)
    fallback_model: Optional[str] = Field(None, max_length=255)
    priority: int = Field(default=0, ge=0, le=1000)

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace only")
        return v.strip()

    @validator('target_model')
    def validate_target_model(cls, v):
        if not v.strip():
            raise ValueError("Target model cannot be empty")
        return v.strip()

    @validator('conditions')
    def validate_conditions(cls, v):
        if not isinstance(v, dict):
            raise ValueError("Conditions must be a dictionary")

        # Validate condition types
        allowed_keys = {
            'cost_threshold', 'task_complexity', 'prompt_length_min',
            'prompt_length_max', 'word_count_min', 'word_count_max'
        }

        for key in v.keys():
            if key not in allowed_keys:
                raise ValueError(f"Invalid condition key: {key}")

        # Validate numeric values
        if 'cost_threshold' in v:
            cost = v['cost_threshold']
            if not isinstance(cost, (int, float)) or cost <= 0 or not math.isfinite(cost):
                raise ValueError("cost_threshold must be positive finite number")

        return v


class RoutingRuleUpdate(BaseModel):
    """Schema for updating a routing rule."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    conditions: Optional[Dict[str, Any]] = None
    target_model: Optional[str] = Field(None, min_length=1, max_length=255)
    fallback_model: Optional[str] = Field(None, max_length=255)
    priority: Optional[int] = Field(None, ge=0, le=1000)
    is_active: Optional[bool] = None


class BudgetCreate(BaseModel):
    """Schema for creating a budget."""
    name: str = Field(..., min_length=1, max_length=255)
    scope: str = Field(..., pattern=r'^(global|team|feature|provider)$')
    scope_value: Optional[str] = Field(None, max_length=255)
    limit_amount: float = Field(..., gt=0)
    limit_period: str = Field(..., pattern=r'^(hourly|daily|weekly|monthly)$')
    action: str = Field(default="alert", pattern=r'^(block|downgrade|alert)$')
    downgrade_model: Optional[str] = Field(None, max_length=255)

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @validator('limit_amount')
    def validate_limit_amount(cls, v):
        if not math.isfinite(v):
            raise ValueError("Limit amount must be a finite number")
        if v > 1000000:  # $1M limit
            raise ValueError("Limit amount cannot exceed $1,000,000")
        return v

    @validator('downgrade_model')
    def validate_downgrade_model(cls, v, values):
        if values.get('action') == 'downgrade' and not v:
            raise ValueError("downgrade_model required when action is 'downgrade'")
        return v


class BudgetUpdate(BaseModel):
    """Schema for updating a budget."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    limit_amount: Optional[float] = Field(None, gt=0)
    action: Optional[str] = Field(None, pattern=r'^(block|downgrade|alert)$')
    downgrade_model: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class SLAConfigCreate(BaseModel):
    """Schema for creating SLA configuration."""
    name: str = Field(..., min_length=1, max_length=255)
    max_latency_ms: int = Field(..., gt=0, le=60000)  # Max 60 seconds
    min_success_rate: float = Field(..., ge=0.0, le=1.0)
    priority_level: str = Field(..., pattern=r'^(low|medium|high|critical)$')
    preferred_providers: Optional[List[str]] = None
    fallback_strategy: str = Field(default="most_reliable", pattern=r'^(fastest|cheapest|most_reliable)$')

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @validator('preferred_providers')
    def validate_providers(cls, v):
        if v is not None:
            if not isinstance(v, list):
                raise ValueError("preferred_providers must be a list")
            if len(v) > 10:
                raise ValueError("Maximum 10 preferred providers")
            for provider in v:
                if not isinstance(provider, str) or not provider.strip():
                    raise ValueError("All providers must be non-empty strings")
        return v


class AuditLogCreate(BaseModel):
    """Schema for creating audit log."""
    event_type: str = Field(..., min_length=1, max_length=100)
    action: str = Field(..., min_length=1, max_length=255)
    event_category: str = Field(default="access", pattern=r'^(access|config|compliance|security)$')
    severity: str = Field(default="info", pattern=r'^(info|warning|critical)$')
    resource_type: Optional[str] = Field(None, max_length=100)
    resource_id: Optional[str] = Field(None, max_length=255)
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = Field(None, max_length=45)
    user_agent: Optional[str] = Field(None, max_length=500)

    @validator('details')
    def validate_details(cls, v):
        if v is not None and not isinstance(v, dict):
            raise ValueError("details must be a dictionary")
        return v


class AgentRunCreate(BaseModel):
    """Schema for creating agent run."""
    agent_name: str = Field(..., min_length=1, max_length=255)
    metadata: Optional[Dict[str, Any]] = None

    @validator('agent_name')
    def validate_agent_name(cls, v):
        if not v.strip():
            raise ValueError("Agent name cannot be empty")
        return v.strip()


class AgentRunUpdate(BaseModel):
    """Schema for updating agent run."""
    step_tokens: int = Field(default=0, ge=0)
    step_cost: float = Field(default=0.0, ge=0.0)
    step_latency: float = Field(default=0.0, ge=0.0)
    status: Optional[str] = Field(None, pattern=r'^(running|completed|failed|timeout)$')
    error: Optional[str] = Field(None, max_length=5000)

    @validator('step_tokens', 'step_cost', 'step_latency')
    def validate_positive_finite(cls, v, field):
        if not math.isfinite(v):
            raise ValueError(f"{field.name} must be a finite number")
        return v


class PolicyCreate(BaseModel):
    """Schema for creating policy."""
    name: str = Field(..., min_length=1, max_length=255)
    policy_type: str = Field(..., pattern=r'^(model_allowlist|pii_detection|data_residency)$')
    rules: Dict[str, Any]
    enforcement_level: str = Field(default="advisory", pattern=r'^(advisory|blocking)$')

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @validator('rules')
    def validate_rules(cls, v, values):
        if not isinstance(v, dict):
            raise ValueError("Rules must be a dictionary")

        policy_type = values.get('policy_type')

        if policy_type == 'model_allowlist':
            if 'allowed_models' not in v:
                raise ValueError("model_allowlist policy requires 'allowed_models' in rules")
            if not isinstance(v['allowed_models'], list):
                raise ValueError("'allowed_models' must be a list")

        elif policy_type == 'data_residency':
            if 'allowed_regions' not in v:
                raise ValueError("data_residency policy requires 'allowed_regions' in rules")
            if not isinstance(v['allowed_regions'], list):
                raise ValueError("'allowed_regions' must be a list")

        return v


class PolicyUpdate(BaseModel):
    """Schema for updating policy."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    rules: Optional[Dict[str, Any]] = None
    enforcement_level: Optional[str] = Field(None, pattern=r'^(advisory|blocking)$')
    is_active: Optional[bool] = None
