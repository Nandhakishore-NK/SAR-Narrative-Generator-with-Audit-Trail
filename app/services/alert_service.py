"""
Alert Service - System alerts, notifications, and escalation management.
Handles both in-app alerts and (optionally) email notifications.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.models.database import SystemAlert, AlertSeverity, SessionLocal
from app.config import settings

logger = logging.getLogger(__name__)

ALERT_TYPES = {
    "NEW_HIGH_SEVERITY_CASE": ("HIGH", "New HIGH Severity Case Requires Review"),
    "NEW_CRITICAL_CASE": ("CRITICAL", "CRITICAL: Immediate SAR Action Required"),
    "SAR_OVERDUE": ("HIGH", "SAR Filing Overdue - Regulatory Deadline Approaching"),
    "NARRATIVE_GENERATED": ("LOW", "SAR Narrative Successfully Generated"),
    "SAR_APPROVED": ("MEDIUM", "SAR Narrative Approved - Ready for Filing"),
    "SAR_REJECTED": ("MEDIUM", "SAR Narrative Rejected - Revision Required"),
    "SAR_FILED": ("LOW", "SAR Successfully Filed with NCA"),
    "HIGH_RISK_CUSTOMER": ("HIGH", "High Risk Customer Activity Detected"),
    "SANCTIONS_HIT": ("CRITICAL", "CRITICAL: Potential Sanctions Match Detected"),
    "PEP_ACTIVITY": ("HIGH", "PEP Customer - Suspicious Activity Flagged"),
    "MULTIPLE_CASES_SAME_CUSTOMER": ("HIGH", "Multiple SAR Cases Opened for Same Customer"),
    "SYSTEM_ERROR": ("CRITICAL", "System Error - Requires Immediate Attention"),
    "BULK_PROCESSING_COMPLETE": ("LOW", "Bulk SAR Processing Batch Completed"),
}


class AlertService:

    def create_alert(
        self,
        alert_type: str,
        message: str,
        case_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        severity: Optional[str] = None,
        send_email: bool = False
    ) -> Optional[SystemAlert]:
        """Create a new system alert."""
        db: Session = SessionLocal()
        try:
            if not severity:
                severity = ALERT_TYPES.get(alert_type, ("MEDIUM", "Alert"))[0]
            title = ALERT_TYPES.get(alert_type, ("MEDIUM", alert_type))[1]
            alert = SystemAlert(
                alert_type=alert_type,
                severity=AlertSeverity(severity),
                title=title,
                message=message,
                case_id=case_id,
                customer_id=customer_id,
                is_read=False,
                sent_via_email=False,
                created_at=datetime.utcnow()
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            logger.info(f"ALERT [{severity}] {alert_type}: {message[:80]}")
            if send_email and severity in ["HIGH", "CRITICAL"]:
                self._send_email_alert(alert)
                alert.sent_via_email = True
                db.commit()
            return alert
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            db.rollback()
            return None
        finally:
            db.close()

    def get_unread_alerts(self, limit: int = 50) -> List[SystemAlert]:
        """Get unread system alerts ordered by severity."""
        db: Session = SessionLocal()
        try:
            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            alerts = db.query(SystemAlert)\
                .filter(SystemAlert.is_read == False)\
                .order_by(SystemAlert.created_at.desc())\
                .limit(limit)\
                .all()
            return sorted(alerts, key=lambda a: severity_order.get(a.severity.value if hasattr(a.severity, 'value') else a.severity, 3))
        finally:
            db.close()

    def get_all_alerts(self, limit: int = 100, severity_filter: Optional[str] = None) -> List[SystemAlert]:
        """Get all alerts with optional severity filter."""
        db: Session = SessionLocal()
        try:
            q = db.query(SystemAlert).order_by(SystemAlert.created_at.desc())
            if severity_filter:
                q = q.filter(SystemAlert.severity == AlertSeverity(severity_filter))
            return q.limit(limit).all()
        finally:
            db.close()

    def mark_read(self, alert_id: int) -> bool:
        """Mark an alert as read."""
        db: Session = SessionLocal()
        try:
            alert = db.query(SystemAlert).filter(SystemAlert.id == alert_id).first()
            if alert:
                alert.is_read = True
                db.commit()
                return True
            return False
        finally:
            db.close()

    def mark_all_read(self) -> int:
        """Mark all alerts as read. Returns count."""
        db: Session = SessionLocal()
        try:
            count = db.query(SystemAlert).filter(SystemAlert.is_read == False).update({"is_read": True})
            db.commit()
            return count
        finally:
            db.close()

    def resolve_alert(self, alert_id: int, resolved_by: str) -> bool:
        """Resolve an alert."""
        db: Session = SessionLocal()
        try:
            alert = db.query(SystemAlert).filter(SystemAlert.id == alert_id).first()
            if alert:
                alert.is_read = True
                alert.resolved_at = datetime.utcnow()
                alert.resolved_by = resolved_by
                db.commit()
                return True
            return False
        finally:
            db.close()

    def get_alert_summary(self) -> Dict[str, int]:
        """Get alert counts by severity."""
        db: Session = SessionLocal()
        try:
            total = db.query(SystemAlert).filter(SystemAlert.is_read == False).count()
            critical = db.query(SystemAlert).filter(SystemAlert.severity == AlertSeverity.CRITICAL, SystemAlert.is_read == False).count()
            high = db.query(SystemAlert).filter(SystemAlert.severity == AlertSeverity.HIGH, SystemAlert.is_read == False).count()
            medium = db.query(SystemAlert).filter(SystemAlert.severity == AlertSeverity.MEDIUM, SystemAlert.is_read == False).count()
            low = db.query(SystemAlert).filter(SystemAlert.severity == AlertSeverity.LOW, SystemAlert.is_read == False).count()
            return {"total": total, "critical": critical, "high": high, "medium": medium, "low": low}
        finally:
            db.close()

    def _send_email_alert(self, alert: SystemAlert) -> bool:
        """Send email notification for high/critical alerts."""
        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            logger.info("SMTP not configured; email alert skipped.")
            return False
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{alert.severity.value}] SAR System Alert: {alert.title}"
            msg["From"] = settings.ALERT_FROM_EMAIL
            msg["To"] = settings.ALERT_TO_EMAIL
            html_body = f"""
            <html><body>
            <h2 style="color:{'red' if alert.severity.value == 'CRITICAL' else 'orange'}">
                [{alert.severity.value}] {alert.title}
            </h2>
            <p><strong>Alert Type:</strong> {alert.alert_type}</p>
            <p><strong>Message:</strong> {alert.message}</p>
            <p><strong>Case ID:</strong> {alert.case_id or 'N/A'}</p>
            <p><strong>Customer ID:</strong> {alert.customer_id or 'N/A'}</p>
            <p><strong>Time:</strong> {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            <hr/>
            <p style="color:gray;font-size:12px;">
                This is an automated alert from the SAR Narrative Generator System.
                Please do not reply to this email.
            </p>
            </body></html>
            """
            msg.attach(MIMEText(html_body, "html"))
            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.sendmail(settings.ALERT_FROM_EMAIL, settings.ALERT_TO_EMAIL, msg.as_string())
            logger.info(f"Email alert sent for {alert.alert_type}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False


alert_service = AlertService()
