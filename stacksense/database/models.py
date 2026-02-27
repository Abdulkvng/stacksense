"""
Database models for StackSense
"""

from datetime import datetime
from typing import Dict, Any
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    JSON,
    Index,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Event(Base):
    """
    Event model for storing API call events.
    """

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    project_id = Column(String(255), nullable=False, index=True)
    environment = Column(String(50), nullable=False, index=True)

    # Event details
    event_type = Column(String(50), default="api_call", nullable=False)
    provider = Column(String(50), nullable=False, index=True)
    model = Column(String(255), nullable=True, index=True)

    # Metrics
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    latency = Column(Float, default=0.0)  # milliseconds

    # Status
    success = Column(Boolean, default=True, index=True)
    error = Column(Text, nullable=True)

    # Additional data
    metadata_ = Column("metadata", JSON, nullable=True)
    method = Column(String(255), nullable=True)

    # Indexes for common queries
    __table_args__ = (
        Index("idx_provider_timestamp", "provider", "timestamp"),
        Index("idx_project_env_timestamp", "project_id", "environment", "timestamp"),
        Index("idx_model_timestamp", "model", "timestamp"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "project_id": self.project_id,
            "environment": self.environment,
            "event_type": self.event_type,
            "provider": self.provider,
            "model": self.model,
            "tokens": {
                "input": self.input_tokens,
                "output": self.output_tokens,
            },
            "total_tokens": self.total_tokens,
            "cost": self.cost,
            "latency": self.latency,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata_ or {},
            "method": self.method,
        }


class Metric(Base):
    """
    Aggregated metrics model for storing pre-computed metrics.
    """

    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    project_id = Column(String(255), nullable=False, index=True)
    environment = Column(String(50), nullable=False, index=True)

    # Time period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    period_type = Column(String(20), nullable=False)  # 'hour', 'day', 'week', 'month'

    # Aggregated metrics
    provider = Column(String(50), nullable=True, index=True)
    model = Column(String(255), nullable=True, index=True)

    total_calls = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    avg_latency = Column(Float, default=0.0)
    error_count = Column(Integer, default=0)

    # Additional aggregated data
    metrics_data = Column(JSON, nullable=True)

    # Unique constraint to prevent duplicate metrics
    __table_args__ = (
        Index(
            "idx_unique_metric",
            "project_id",
            "environment",
            "provider",
            "model",
            "period_start",
            "period_end",
            unique=True,
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "project_id": self.project_id,
            "environment": self.environment,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "period_type": self.period_type,
            "provider": self.provider,
            "model": self.model,
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "avg_latency": self.avg_latency,
            "error_count": self.error_count,
            "metrics_data": self.metrics_data or {},
        }


class User(Base):
    """User account created via Google OAuth."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_sub = Column(String(255), nullable=False, unique=True, index=True)
    email = Column(String(320), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    avatar_url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    api_keys = relationship(
        "UserAPIKey",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert user model to API-safe dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }


class UserAPIKey(Base):
    """Encrypted API credentials owned by a user."""

    __tablename__ = "user_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider = Column(String(80), nullable=False, index=True)
    label = Column(String(120), nullable=False)
    encrypted_key = Column(Text, nullable=False)
    key_hint = Column(String(24), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        onupdate=datetime.utcnow,
    )

    user = relationship("User", back_populates="api_keys")

    __table_args__ = (
        UniqueConstraint("user_id", "provider", "label", name="uq_user_provider_label"),
        Index("idx_user_provider_active", "user_id", "provider", "is_active"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert API key model to API-safe dictionary."""
        return {
            "id": self.id,
            "provider": self.provider,
            "label": self.label,
            "key_hint": self.key_hint,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
<<<<<<< Updated upstream
=======


class RoutingRule(Base):
    """Dynamic routing rules for model selection."""

    __tablename__ = "routing_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Routing conditions
    conditions = Column(JSON, nullable=False)  # {'cost_threshold': 0.01, 'task_complexity': 'high'}
    target_model = Column(String(255), nullable=False)
    fallback_model = Column(String(255), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Performance indexes
    __table_args__ = (
        Index('idx_routing_user_active_priority', 'user_id', 'is_active', 'priority'),
        Index('idx_routing_created', 'created_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "priority": self.priority,
            "is_active": self.is_active,
            "conditions": self.conditions,
            "target_model": self.target_model,
            "fallback_model": self.fallback_model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Budget(Base):
    """Budget limits and circuit breakers."""

    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    scope = Column(String(50), nullable=False)  # 'global', 'team', 'feature', 'provider'
    scope_value = Column(String(255), nullable=True)  # team name, feature name, etc.

    # Budget limits
    limit_amount = Column(Float, nullable=False)
    limit_period = Column(String(20), nullable=False)  # 'hourly', 'daily', 'weekly', 'monthly'
    current_spend = Column(Float, default=0.0, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Actions when limit reached
    action = Column(String(50), nullable=False)  # 'block', 'downgrade', 'alert'
    downgrade_model = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Performance indexes - CRITICAL for budget checking at scale
    __table_args__ = (
        Index('idx_budget_user_active', 'user_id', 'is_active'),
        Index('idx_budget_scope_active', 'scope', 'is_active'),
        Index('idx_budget_period', 'period_start', 'period_end'),
        Index('idx_budget_user_scope_period', 'user_id', 'scope', 'scope_value', 'period_start', 'period_end'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "scope": self.scope,
            "scope_value": self.scope_value,
            "limit_amount": self.limit_amount,
            "limit_period": self.limit_period,
            "current_spend": self.current_spend,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "action": self.action,
            "downgrade_model": self.downgrade_model,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SLAConfig(Base):
    """SLA-aware routing configuration."""

    __tablename__ = "sla_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)

    # SLA requirements
    max_latency_ms = Column(Integer, nullable=False)  # P95 latency requirement
    min_success_rate = Column(Float, nullable=False)  # 0.0-1.0
    priority_level = Column(String(20), nullable=False)  # 'low', 'medium', 'high', 'critical'

    # Routing preferences
    preferred_providers = Column(JSON, nullable=True)  # ['openai', 'anthropic']
    fallback_strategy = Column(String(50), nullable=False)  # 'fastest', 'cheapest', 'most_reliable'
    is_active = Column(Boolean, default=True, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Performance indexes
    __table_args__ = (
        Index('idx_sla_user_active', 'user_id', 'is_active'),
        Index('idx_sla_priority', 'priority_level', 'is_active'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "max_latency_ms": self.max_latency_ms,
            "min_success_rate": self.min_success_rate,
            "priority_level": self.priority_level,
            "preferred_providers": self.preferred_providers,
            "fallback_strategy": self.fallback_strategy,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AuditLog(Base):
    """Governance and compliance audit logs."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    # Audit event details
    event_type = Column(String(100), nullable=False, index=True)  # 'model_call', 'policy_violation', 'config_change'
    event_category = Column(String(50), nullable=False)  # 'access', 'config', 'compliance', 'security'
    severity = Column(String(20), nullable=False)  # 'info', 'warning', 'critical'

    # Event data
    action = Column(String(255), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(255), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Compliance
    is_tamper_proof = Column(Boolean, default=True, nullable=False)
    hash_value = Column(String(64), nullable=True)  # SHA256 hash for tamper detection

    __table_args__ = (
        Index("idx_audit_user_timestamp", "user_id", "timestamp"),
        Index("idx_audit_event_type", "event_type", "timestamp"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "event_category": self.event_category,
            "severity": self.severity,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
        }


class AgentRun(Base):
    """Agent workflow tracking."""

    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name = Column(String(255), nullable=False, index=True)
    run_id = Column(String(255), nullable=False, unique=True, index=True)

    # Run details
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False)  # 'running', 'completed', 'failed', 'timeout'

    # Metrics
    total_steps = Column(Integer, default=0)
    completed_steps = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    total_latency = Column(Float, default=0.0)

    # Loop detection
    loop_detected = Column(Boolean, default=False)
    loop_count = Column(Integer, default=0)

    # Metadata
    run_metadata = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_agent_status", "agent_name", "status", "start_time"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "run_id": self.run_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "total_latency": self.total_latency,
            "loop_detected": self.loop_detected,
            "loop_count": self.loop_count,
            "metadata": self.metadata,
            "error": self.error,
        }


class Policy(Base):
    """Enterprise policy rules."""

    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    policy_type = Column(String(50), nullable=False)  # 'model_allowlist', 'pii_detection', 'data_residency'

    # Policy rules
    rules = Column(JSON, nullable=False)
    enforcement_level = Column(String(20), nullable=False)  # 'advisory', 'blocking'
    is_active = Column(Boolean, default=True, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Performance indexes
    __table_args__ = (
        Index('idx_policy_user_type_active', 'user_id', 'policy_type', 'is_active'),
        Index('idx_policy_enforcement', 'enforcement_level', 'is_active'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "policy_type": self.policy_type,
            "rules": self.rules,
            "enforcement_level": self.enforcement_level,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
>>>>>>> Stashed changes
