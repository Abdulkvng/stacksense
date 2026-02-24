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
