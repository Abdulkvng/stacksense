"""
Agent Tracking

Track multi-step agentic workflows, detect infinite loops, and manage token budgets.
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from stacksense.database.models import AgentRun
from stacksense.logger.logger import get_logger

logger = get_logger(__name__)


class AgentTracker:
    """
    Track and manage AI agent executions.
    """

    def __init__(self, db_session: Optional[Session] = None, user_id: Optional[int] = None):
        self.db_session = db_session
        self.user_id = user_id

    def start_run(
        self,
        agent_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start tracking a new agent run.

        Returns:
            str: run_id for tracking this execution
        """
        if not self.db_session or not self.user_id:
            raise ValueError("Database session and user_id required")

        run_id = str(uuid.uuid4())

        agent_run = AgentRun(
            user_id=self.user_id,
            agent_name=agent_name,
            run_id=run_id,
            status="running",
            total_steps=0,
            completed_steps=0,
            total_tokens=0,
            total_cost=0.0,
            total_latency=0.0,
            loop_detected=False,
            loop_count=0,
            metadata=metadata or {}
        )

        self.db_session.add(agent_run)
        self.db_session.commit()
        self.db_session.refresh(agent_run)

        logger.info(f"Started agent run: {agent_name} ({run_id})")
        return run_id

    def update_run(
        self,
        run_id: str,
        step_tokens: int = 0,
        step_cost: float = 0.0,
        step_latency: float = 0.0,
        status: Optional[str] = None,
        error: Optional[str] = None
    ) -> Optional[AgentRun]:
        """
        Update an agent run with step metrics.

        Returns:
            AgentRun or None if run not found
        """
        if not self.db_session or not self.user_id:
            return None

        agent_run = (
            self.db_session.query(AgentRun)
            .filter(
                AgentRun.run_id == run_id,
                AgentRun.user_id == self.user_id
            )
            .first()
        )

        if not agent_run:
            logger.warning(f"Agent run not found: {run_id}")
            return None

        # Update metrics
        agent_run.completed_steps += 1
        agent_run.total_tokens += step_tokens
        agent_run.total_cost += step_cost
        agent_run.total_latency += step_latency

        if status:
            agent_run.status = status

        if error:
            agent_run.error = error

        # Detect potential infinite loops
        if agent_run.completed_steps > 50:  # Threshold for loop detection
            agent_run.loop_detected = True
            agent_run.loop_count = agent_run.completed_steps
            logger.warning(f"Potential infinite loop detected in agent run {run_id}")

        self.db_session.commit()
        self.db_session.refresh(agent_run)

        return agent_run

    def complete_run(
        self,
        run_id: str,
        status: str = "completed",
        error: Optional[str] = None
    ) -> Optional[AgentRun]:
        """Mark an agent run as completed."""
        if not self.db_session or not self.user_id:
            return None

        agent_run = (
            self.db_session.query(AgentRun)
            .filter(
                AgentRun.run_id == run_id,
                AgentRun.user_id == self.user_id
            )
            .first()
        )

        if not agent_run:
            return None

        agent_run.status = status
        agent_run.end_time = datetime.utcnow()
        if error:
            agent_run.error = error

        self.db_session.commit()
        self.db_session.refresh(agent_run)

        logger.info(
            f"Completed agent run {run_id}: "
            f"{agent_run.completed_steps} steps, "
            f"${agent_run.total_cost:.4f}, "
            f"{agent_run.total_tokens} tokens"
        )

        return agent_run

    def get_run(self, run_id: str) -> Optional[AgentRun]:
        """Get details of a specific agent run."""
        if not self.db_session or not self.user_id:
            return None

        return (
            self.db_session.query(AgentRun)
            .filter(
                AgentRun.run_id == run_id,
                AgentRun.user_id == self.user_id
            )
            .first()
        )

    def get_runs(
        self,
        agent_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[AgentRun]:
        """Get agent runs with optional filtering."""
        if not self.db_session or not self.user_id:
            return []

        query = self.db_session.query(AgentRun).filter(AgentRun.user_id == self.user_id)

        if agent_name:
            query = query.filter(AgentRun.agent_name == agent_name)

        if status:
            query = query.filter(AgentRun.status == status)

        return query.order_by(AgentRun.start_time.desc()).limit(limit).all()

    def get_agent_stats(self, agent_name: str, days: int = 30) -> Dict[str, Any]:
        """Get aggregate stats for an agent."""
        if not self.db_session or not self.user_id:
            return {}

        from datetime import timedelta
        since = datetime.utcnow() - timedelta(days=days)

        runs = (
            self.db_session.query(AgentRun)
            .filter(
                AgentRun.user_id == self.user_id,
                AgentRun.agent_name == agent_name,
                AgentRun.start_time >= since
            )
            .all()
        )

        if not runs:
            return {
                "total_runs": 0,
                "completed_runs": 0,
                "failed_runs": 0,
                "total_cost": 0.0,
                "avg_cost_per_run": 0.0,
                "total_tokens": 0,
                "avg_tokens_per_run": 0,
                "loop_detections": 0
            }

        completed = [r for r in runs if r.status == "completed"]
        failed = [r for r in runs if r.status == "failed"]
        loops = [r for r in runs if r.loop_detected]

        total_cost = sum(r.total_cost for r in runs)
        total_tokens = sum(r.total_tokens for r in runs)

        return {
            "total_runs": len(runs),
            "completed_runs": len(completed),
            "failed_runs": len(failed),
            "total_cost": total_cost,
            "avg_cost_per_run": total_cost / len(runs) if runs else 0.0,
            "total_tokens": total_tokens,
            "avg_tokens_per_run": total_tokens / len(runs) if runs else 0,
            "loop_detections": len(loops)
        }
