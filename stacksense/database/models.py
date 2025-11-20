"""
Database models for StackSense
"""

from datetime import datetime
from typing import Optional, Dict, Any
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
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

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
    metadata = Column(JSON, nullable=True)
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
            "metadata": self.metadata or {},
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
