"""Security monitoring and alerting system for MandiMonitor.

This module provides real-time security monitoring, anomaly detection,
and alerting capabilities to protect against security threats.
"""

import time
import threading
import json
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

from .logging_config import SecurityEventLogger

logger = logging.getLogger(__name__)
security_logger = SecurityEventLogger()


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of security alerts."""
    BRUTE_FORCE = "brute_force"
    DDoS_ATTACK = "ddos_attack"
    SQL_INJECTION = "sql_injection"
    XSS_ATTACK = "xss_attack"
    RATE_LIMIT_BREACH = "rate_limit_breach"
    SUSPICIOUS_TRAFFIC = "suspicious_traffic"
    CONFIGURATION_CHANGE = "configuration_change"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


@dataclass
class SecurityAlert:
    """Security alert data structure."""
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    source_ip: Optional[str] = None
    user_id: Optional[str] = None
    mitigated: bool = False


@dataclass
class SecurityMetrics:
    """Security metrics for monitoring."""
    total_requests: int = 0
    blocked_requests: int = 0
    auth_failures: int = 0
    rate_limit_hits: int = 0
    suspicious_patterns: int = 0
    active_sessions: int = 0
    last_updated: Optional[datetime] = None


class SecurityMonitor:
    """Real-time security monitoring and alerting system."""

    def __init__(self):
        self.alerts: List[SecurityAlert] = []
        self.metrics = SecurityMetrics()
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None

        # Alert thresholds
        self.thresholds = {
            'auth_failures_per_minute': 5,
            'rate_limit_hits_per_minute': 10,
            'suspicious_patterns_per_minute': 3,
            'blocked_requests_per_minute': 20
        }

        # Time windows for analysis (in seconds)
        self.analysis_windows = {
            'short': 60,    # 1 minute
            'medium': 300,  # 5 minutes
            'long': 3600    # 1 hour
        }

        # Rolling data for trend analysis
        self.event_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # Alert callbacks
        self.alert_callbacks: List[Callable[[SecurityAlert], None]] = []

    def start_monitoring(self):
        """Start the security monitoring system."""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()

        logger.info("Security monitoring started")
        security_logger.log_security_event(
            "SECURITY_MONITORING_STARTED",
            "low",
            {"message": "Security monitoring system activated"}
        )

    def stop_monitoring(self):
        """Stop the security monitoring system."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        logger.info("Security monitoring stopped")

    def record_event(self, event_type: str, details: Dict[str, Any] = None,
                    source_ip: str = None, user_id: str = None):
        """Record a security event for analysis."""
        timestamp = datetime.now()

        # Update metrics
        self._update_metrics(event_type, details)

        # Store in history for trend analysis
        event_data = {
            'timestamp': timestamp,
            'type': event_type,
            'details': details or {},
            'source_ip': source_ip,
            'user_id': user_id
        }

        self.event_history[event_type].append(event_data)

        # Check for alerts
        self._check_alerts(event_type, event_data)

    def add_alert_callback(self, callback: Callable[[SecurityAlert], None]):
        """Add a callback for alert notifications."""
        self.alert_callbacks.append(callback)

    def get_metrics(self) -> Dict[str, Any]:
        """Get current security metrics."""
        return {
            'total_requests': self.metrics.total_requests,
            'blocked_requests': self.metrics.blocked_requests,
            'auth_failures': self.metrics.auth_failures,
            'rate_limit_hits': self.metrics.rate_limit_hits,
            'suspicious_patterns': self.metrics.suspicious_patterns,
            'active_sessions': self.metrics.active_sessions,
            'active_alerts': len([a for a in self.alerts if not a.mitigated]),
            'last_updated': self.metrics.last_updated.isoformat() if self.metrics.last_updated else None
        }

    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent security alerts."""
        recent_alerts = sorted(
            self.alerts[-limit:],
            key=lambda x: x.timestamp,
            reverse=True
        )

        return [
            {
                'alert_id': alert.alert_id,
                'type': alert.alert_type.value,
                'severity': alert.severity.value,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'source_ip': alert.source_ip,
                'user_id': alert.user_id,
                'mitigated': alert.mitigated
            }
            for alert in recent_alerts
        ]

    def mitigate_alert(self, alert_id: str):
        """Mark an alert as mitigated."""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.mitigated = True
                security_logger.log_security_event(
                    "ALERT_MITIGATED",
                    "low",
                    {
                        'alert_id': alert_id,
                        'alert_type': alert.alert_type.value
                    }
                )
                break

    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                self._perform_monitoring_checks()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

    def _perform_monitoring_checks(self):
        """Perform periodic monitoring checks."""
        now = datetime.now()

        # Analyze trends
        self._analyze_trends()

        # Check system health
        self._check_system_health()

        # Update metrics timestamp
        self.metrics.last_updated = now

    def _update_metrics(self, event_type: str, details: Dict[str, Any]):
        """Update security metrics based on event type."""
        if event_type == 'request':
            self.metrics.total_requests += 1
        elif event_type == 'blocked_request':
            self.metrics.blocked_requests += 1
        elif event_type == 'auth_failure':
            self.metrics.auth_failures += 1
        elif event_type == 'rate_limit_hit':
            self.metrics.rate_limit_hits += 1
        elif event_type == 'suspicious_pattern':
            self.metrics.suspicious_patterns += 1

    def _check_alerts(self, event_type: str, event_data: Dict[str, Any]):
        """Check if an event should trigger an alert."""
        alert = None

        if event_type == 'brute_force_attempt':
            alert = SecurityAlert(
                alert_id=f"alert_{int(time.time())}_{len(self.alerts)}",
                alert_type=AlertType.BRUTE_FORCE,
                severity=AlertSeverity.HIGH,
                message="Potential brute force attack detected",
                details=event_data['details'],
                timestamp=event_data['timestamp'],
                source_ip=event_data['source_ip']
            )

        elif event_type == 'ddos_pattern':
            alert = SecurityAlert(
                alert_id=f"alert_{int(time.time())}_{len(self.alerts)}",
                alert_type=AlertType.DDoS_ATTACK,
                severity=AlertSeverity.CRITICAL,
                message="DDoS attack pattern detected",
                details=event_data['details'],
                timestamp=event_data['timestamp'],
                source_ip=event_data['source_ip']
            )

        elif event_type == 'sql_injection_attempt':
            alert = SecurityAlert(
                alert_id=f"alert_{int(time.time())}_{len(self.alerts)}",
                alert_type=AlertType.SQL_INJECTION,
                severity=AlertSeverity.CRITICAL,
                message="SQL injection attempt detected",
                details=event_data['details'],
                timestamp=event_data['timestamp'],
                source_ip=event_data['source_ip']
            )

        if alert:
            self.alerts.append(alert)
            self._trigger_alert_callbacks(alert)

    def _analyze_trends(self):
        """Analyze security event trends for anomalies."""
        now = datetime.now()

        # Check for brute force patterns
        auth_failures = self._count_events_in_window('auth_failure', self.analysis_windows['short'])
        if auth_failures > self.thresholds['auth_failures_per_minute']:
            self.record_event('brute_force_attempt', {
                'failure_count': auth_failures,
                'time_window': self.analysis_windows['short']
            })

        # Check for DDoS patterns
        blocked_requests = self._count_events_in_window('blocked_request', self.analysis_windows['short'])
        if blocked_requests > self.thresholds['blocked_requests_per_minute']:
            self.record_event('ddos_pattern', {
                'blocked_count': blocked_requests,
                'time_window': self.analysis_windows['short']
            })

        # Check for rate limit abuse
        rate_limit_hits = self._count_events_in_window('rate_limit_hit', self.analysis_windows['short'])
        if rate_limit_hits > self.thresholds['rate_limit_hits_per_minute']:
            self.record_event('rate_limit_abuse', {
                'hit_count': rate_limit_hits,
                'time_window': self.analysis_windows['short']
            })

    def _count_events_in_window(self, event_type: str, window_seconds: int) -> int:
        """Count events of a specific type within a time window."""
        cutoff_time = datetime.now() - timedelta(seconds=window_seconds)
        return sum(
            1 for event in self.event_history[event_type]
            if event['timestamp'] > cutoff_time
        )

    def _check_system_health(self):
        """Check overall system security health."""
        # This could include checks for:
        # - File integrity
        # - Process monitoring
        # - Network connections
        # - System resource usage

        # For now, just log that health check was performed
        security_logger.log_security_event(
            "SYSTEM_HEALTH_CHECK",
            "low",
            {
                'active_alerts': len([a for a in self.alerts if not a.mitigated]),
                'total_events': sum(len(events) for events in self.event_history.values())
            }
        )

    def _trigger_alert_callbacks(self, alert: SecurityAlert):
        """Trigger alert notification callbacks."""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

        # Log the alert
        security_logger.log_security_event(
            "SECURITY_ALERT_TRIGGERED",
            alert.severity.value,
            {
                'alert_id': alert.alert_id,
                'alert_type': alert.alert_type.value,
                'message': alert.message,
                'source_ip': alert.source_ip,
                'user_id': alert.user_id
            },
            alert.user_id,
            alert.source_ip
        )


class AlertNotifier:
    """Alert notification system."""

    def __init__(self, monitor: SecurityMonitor):
        self.monitor = monitor
        self.monitor.add_alert_callback(self.handle_alert)

    def handle_alert(self, alert: SecurityAlert):
        """Handle incoming security alerts."""
        print(f"\n🚨 SECURITY ALERT 🚨")
        print(f"Type: {alert.alert_type.value}")
        print(f"Severity: {alert.severity.value}")
        print(f"Message: {alert.message}")
        print(f"Time: {alert.timestamp}")
        if alert.source_ip:
            print(f"Source IP: {alert.source_ip}")
        if alert.user_id:
            print(f"User ID: {alert.user_id}")
        print("-" * 50)

        # Here you could add:
        # - Email notifications
        # - Slack/Discord webhooks
        # - SMS alerts
        # - PagerDuty integration
        # - SIEM system integration

        # For now, just log to console and security log
        logger.warning(f"Security Alert: {alert.message}")

        # Send to external alerting system (placeholder)
        self._send_external_alert(alert)

    def _send_external_alert(self, alert: SecurityAlert):
        """Send alert to external monitoring system."""
        # Placeholder for external alerting
        # Could integrate with:
        # - PagerDuty
        # - OpsGenius
        # - Slack
        # - Email
        # - SMS

        alert_data = {
            'alert_id': alert.alert_id,
            'type': alert.alert_type.value,
            'severity': alert.severity.value,
            'message': alert.message,
            'timestamp': alert.timestamp.isoformat(),
            'details': alert.details
        }

        # In production, this would send to your alerting system
        logger.info(f"External alert sent: {json.dumps(alert_data)}")


# Global security monitor instance
_security_monitor: Optional[SecurityMonitor] = None
_alert_notifier: Optional[AlertNotifier] = None


def get_security_monitor() -> SecurityMonitor:
    """Get the global security monitor instance."""
    global _security_monitor
    if _security_monitor is None:
        _security_monitor = SecurityMonitor()
        _security_monitor.start_monitoring()

        # Initialize alert notifier
        global _alert_notifier
        _alert_notifier = AlertNotifier(_security_monitor)

    return _security_monitor


def record_security_event(event_type: str, details: Dict[str, Any] = None,
                         source_ip: str = None, user_id: str = None):
    """Convenience function to record security events."""
    monitor = get_security_monitor()
    monitor.record_event(event_type, details, source_ip, user_id)


def get_security_metrics() -> Dict[str, Any]:
    """Get current security metrics."""
    monitor = get_security_monitor()
    return monitor.get_metrics()


def get_security_alerts(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent security alerts."""
    monitor = get_security_monitor()
    return monitor.get_recent_alerts(limit)


# Initialize security monitoring when module is imported
def _initialize_security_monitoring():
    """Initialize security monitoring on module import."""
    try:
        monitor = get_security_monitor()
        logger.info("Security monitoring initialized")
    except Exception as e:
        logger.error(f"Failed to initialize security monitoring: {e}")


# Initialize on import
_initialize_security_monitoring()
