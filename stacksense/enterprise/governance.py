"""
Governance & Audit Logs

Tam

per-evident audit trails for compliance and security.
"""

import hashlib
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from stacksense.database.models import AuditLog
from stacksense.logger.logger import get_logger

logger = get_logger(__name__)


class GovernanceEngine:
    """
    Manage governance, compliance, and audit logging.
    """

    def __init__(self, db_session: Optional[Session] = None, user_id: Optional[int] = None):
        self.db_session = db_session
        self.user_id = user_id

    def log_event(
        self,
        event_type: str,
        action: str,
        event_category: str = "access",
        severity: str = "info",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Create a tamper-proof audit log entry.

        Args:
            event_type: Type of event ('model_call', 'policy_violation', 'config_change')
            action: Action performed
            event_category: Category ('access', 'config', 'compliance', 'security')
            severity: 'info', 'warning', 'critical'
            resource_type: Type of resource accessed
            resource_id: Resource identifier
            details: Additional event details
            ip_address: Client IP address
            user_agent: Client user agent
        """
        if not self.db_session:
            raise ValueError("Database session required")

        # Create audit log entry
        audit_log = AuditLog(
            user_id=self.user_id,
            event_type=event_type,
            event_category=event_category,
            severity=severity,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            is_tamper_proof=True,
        )

        # Generate tamper-proof hash
        audit_log.hash_value = self._generate_hash(audit_log)

        self.db_session.add(audit_log)
        self.db_session.commit()
        self.db_session.refresh(audit_log)

        logger.info(f"Audit log created: {event_type} - {action}")
        return audit_log

    def _generate_hash(self, audit_log: AuditLog) -> str:
        """Generate SHA256 hash for tamper detection."""
        data = {
            "timestamp": audit_log.timestamp.isoformat() if audit_log.timestamp else None,
            "user_id": audit_log.user_id,
            "event_type": audit_log.event_type,
            "action": audit_log.action,
            "details": audit_log.details,
        }
        hash_input = json.dumps(data, sort_keys=True).encode("utf-8")
        return hashlib.sha256(hash_input).hexdigest()

    def verify_integrity(self, log_id: int) -> bool:
        """Verify that an audit log hasn't been tampered with."""
        if not self.db_session:
            return False

        audit_log = self.db_session.query(AuditLog).filter(AuditLog.id == log_id).first()

        if not audit_log or not audit_log.hash_value:
            return False

        expected_hash = self._generate_hash(audit_log)
        return audit_log.hash_value == expected_hash

    def get_logs(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        days: int = 30,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get audit logs with optional filtering."""
        if not self.db_session:
            return []

        since = datetime.utcnow() - timedelta(days=days)
        query = self.db_session.query(AuditLog).filter(AuditLog.timestamp >= since)

        if self.user_id:
            query = query.filter(AuditLog.user_id == self.user_id)

        if event_type:
            query = query.filter(AuditLog.event_type == event_type)

        if severity:
            query = query.filter(AuditLog.severity == severity)

        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

    def detect_violations(self, days: int = 7) -> List[Dict[str, Any]]:
        """Detect potential policy violations or security issues."""
        if not self.db_session:
            return []

        since = datetime.utcnow() - timedelta(days=days)

        # Get critical/warning events
        violations = (
            self.db_session.query(AuditLog)
            .filter(AuditLog.timestamp >= since, AuditLog.severity.in_(["warning", "critical"]))
            .order_by(AuditLog.timestamp.desc())
            .limit(50)
            .all()
        )

        return [
            {
                "id": v.id,
                "timestamp": v.timestamp.isoformat() if v.timestamp else None,
                "event_type": v.event_type,
                "severity": v.severity,
                "action": v.action,
                "details": v.details,
            }
            for v in violations
        ]
