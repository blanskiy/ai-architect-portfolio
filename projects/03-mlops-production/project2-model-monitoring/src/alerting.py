"""
Alerting Module
Sends alerts when model metrics breach thresholds.

Supports:
- Slack notifications
- Email (SMTP)
- PagerDuty
- Webhook (generic)

Usage:
    from alerting import AlertManager
    
    alert_manager = AlertManager(slack_webhook="https://hooks.slack.com/...")
    alert_manager.send_alert(
        severity="warning",
        title="Data Drift Detected",
        message="Feature 'age' drift score: 0.25 (threshold: 0.1)"
    )
"""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
from enum import Enum

import requests


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert data structure."""
    severity: str
    title: str
    message: str
    source: str
    timestamp: str
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    additional_data: Optional[dict] = None


class AlertChannel(ABC):
    """Abstract base class for alert channels."""
    
    @abstractmethod
    def send(self, alert: Alert) -> bool:
        """Send an alert. Returns True if successful."""
        pass


class SlackChannel(AlertChannel):
    """Send alerts to Slack."""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send(self, alert: Alert) -> bool:
        """Send alert to Slack webhook."""
        
        # Color based on severity
        colors = {
            'info': '#36a64f',      # Green
            'warning': '#ffcc00',   # Yellow
            'critical': '#ff0000',  # Red
        }
        color = colors.get(alert.severity, '#808080')
        
        # Build Slack message
        payload = {
            "attachments": [{
                "color": color,
                "title": f"🚨 {alert.title}",
                "text": alert.message,
                "fields": [
                    {"title": "Severity", "value": alert.severity.upper(), "short": True},
                    {"title": "Source", "value": alert.source, "short": True},
                ],
                "footer": f"Model Monitoring | {alert.timestamp}",
            }]
        }
        
        # Add optional fields
        if alert.model_name:
            payload["attachments"][0]["fields"].append({
                "title": "Model", 
                "value": f"{alert.model_name} ({alert.model_version})", 
                "short": True
            })
        
        if alert.metric_name:
            payload["attachments"][0]["fields"].append({
                "title": "Metric",
                "value": f"{alert.metric_name}: {alert.metric_value} (threshold: {alert.threshold})",
                "short": False
            })
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to send Slack alert: {e}")
            return False


class EmailChannel(AlertChannel):
    """Send alerts via email."""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        sender: str,
        recipients: list[str],
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender = sender
        self.recipients = recipients
        self.username = username
        self.password = password
    
    def send(self, alert: Alert) -> bool:
        """Send alert via email."""
        
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Build email
        msg = MIMEMultipart()
        msg['Subject'] = f"[{alert.severity.upper()}] {alert.title}"
        msg['From'] = self.sender
        msg['To'] = ', '.join(self.recipients)
        
        body = f"""
Model Monitoring Alert

Severity: {alert.severity.upper()}
Title: {alert.title}
Message: {alert.message}
Source: {alert.source}
Timestamp: {alert.timestamp}

Model: {alert.model_name or 'N/A'} ({alert.model_version or 'N/A'})
Metric: {alert.metric_name or 'N/A'}
Value: {alert.metric_value or 'N/A'}
Threshold: {alert.threshold or 'N/A'}
"""
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.username and self.password:
                    server.starttls()
                    server.login(self.username, self.password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Failed to send email alert: {e}")
            return False


class PagerDutyChannel(AlertChannel):
    """Send alerts to PagerDuty."""
    
    def __init__(self, integration_key: str):
        self.integration_key = integration_key
        self.api_url = "https://events.pagerduty.com/v2/enqueue"
    
    def send(self, alert: Alert) -> bool:
        """Send alert to PagerDuty."""
        
        # Map severity
        severity_map = {
            'info': 'info',
            'warning': 'warning',
            'critical': 'critical',
        }
        
        payload = {
            "routing_key": self.integration_key,
            "event_action": "trigger",
            "payload": {
                "summary": f"{alert.title}: {alert.message}",
                "severity": severity_map.get(alert.severity, 'warning'),
                "source": alert.source,
                "timestamp": alert.timestamp,
                "custom_details": {
                    "model_name": alert.model_name,
                    "model_version": alert.model_version,
                    "metric_name": alert.metric_name,
                    "metric_value": alert.metric_value,
                    "threshold": alert.threshold,
                }
            }
        }
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=10
            )
            return response.status_code == 202
        except Exception as e:
            print(f"Failed to send PagerDuty alert: {e}")
            return False


class WebhookChannel(AlertChannel):
    """Send alerts to generic webhook."""
    
    def __init__(self, webhook_url: str, headers: Optional[dict] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {"Content-Type": "application/json"}
    
    def send(self, alert: Alert) -> bool:
        """Send alert to webhook."""
        
        try:
            response = requests.post(
                self.webhook_url,
                json=asdict(alert),
                headers=self.headers,
                timeout=10
            )
            return 200 <= response.status_code < 300
        except Exception as e:
            print(f"Failed to send webhook alert: {e}")
            return False


class ConsoleChannel(AlertChannel):
    """Print alerts to console (for testing)."""
    
    def send(self, alert: Alert) -> bool:
        """Print alert to console."""
        
        severity_icons = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'critical': '🚨',
        }
        icon = severity_icons.get(alert.severity, '📢')
        
        print(f"\n{icon} ALERT: {alert.title}")
        print(f"   Severity: {alert.severity.upper()}")
        print(f"   Message: {alert.message}")
        print(f"   Source: {alert.source}")
        print(f"   Time: {alert.timestamp}")
        
        if alert.metric_name:
            print(f"   Metric: {alert.metric_name} = {alert.metric_value} (threshold: {alert.threshold})")
        
        return True


class AlertManager:
    """
    Manages alert routing and deduplication.
    
    Features:
    - Multiple alert channels
    - Severity-based routing
    - Alert deduplication (cooldown)
    - Alert history
    """
    
    def __init__(
        self,
        source: str = "model-monitoring",
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        cooldown_minutes: int = 15,
    ):
        self.source = source
        self.model_name = model_name
        self.model_version = model_version
        self.cooldown_minutes = cooldown_minutes
        
        self.channels: list[tuple[AlertChannel, list[str]]] = []  # (channel, severities)
        self.alert_history: list[Alert] = []
        self.last_alert_times: dict[str, datetime] = {}  # key -> last alert time
    
    def add_channel(
        self,
        channel: AlertChannel,
        severities: list[str] = None,
    ):
        """
        Add an alert channel.
        
        Args:
            channel: Alert channel instance
            severities: List of severities to route to this channel
                        (None = all severities)
        """
        severities = severities or ['info', 'warning', 'critical']
        self.channels.append((channel, severities))
    
    def _get_alert_key(self, alert: Alert) -> str:
        """Generate unique key for deduplication."""
        return f"{alert.severity}:{alert.title}:{alert.metric_name}"
    
    def _is_in_cooldown(self, alert: Alert) -> bool:
        """Check if alert is in cooldown period."""
        key = self._get_alert_key(alert)
        last_time = self.last_alert_times.get(key)
        
        if last_time is None:
            return False
        
        elapsed = (datetime.now() - last_time).total_seconds() / 60
        return elapsed < self.cooldown_minutes
    
    def send_alert(
        self,
        severity: str,
        title: str,
        message: str,
        metric_name: Optional[str] = None,
        metric_value: Optional[float] = None,
        threshold: Optional[float] = None,
        additional_data: Optional[dict] = None,
        force: bool = False,
    ) -> bool:
        """
        Send an alert to all configured channels.
        
        Args:
            severity: Alert severity (info, warning, critical)
            title: Alert title
            message: Alert message
            metric_name: Name of the metric that triggered alert
            metric_value: Current value of the metric
            threshold: Threshold that was breached
            additional_data: Any additional context
            force: Bypass cooldown
        
        Returns:
            True if alert was sent to at least one channel
        """
        
        alert = Alert(
            severity=severity,
            title=title,
            message=message,
            source=self.source,
            timestamp=datetime.now().isoformat(),
            model_name=self.model_name,
            model_version=self.model_version,
            metric_name=metric_name,
            metric_value=metric_value,
            threshold=threshold,
            additional_data=additional_data,
        )
        
        # Check cooldown
        if not force and self._is_in_cooldown(alert):
            print(f"Alert '{title}' is in cooldown, skipping")
            return False
        
        # Send to channels
        sent_count = 0
        for channel, severities in self.channels:
            if severity in severities:
                if channel.send(alert):
                    sent_count += 1
        
        # Update tracking
        if sent_count > 0:
            key = self._get_alert_key(alert)
            self.last_alert_times[key] = datetime.now()
            self.alert_history.append(alert)
        
        return sent_count > 0
    
    def send_drift_alert(
        self,
        drift_type: str,
        drift_score: float,
        threshold: float,
        feature_name: Optional[str] = None,
    ):
        """Convenience method for drift alerts."""
        
        severity = 'critical' if drift_score > threshold * 2 else 'warning'
        
        if feature_name:
            title = f"Feature Drift Detected: {feature_name}"
            message = f"Feature '{feature_name}' has drifted significantly from training distribution"
        else:
            title = f"{drift_type.title()} Drift Detected"
            message = f"Overall {drift_type} drift exceeds threshold"
        
        self.send_alert(
            severity=severity,
            title=title,
            message=message,
            metric_name=f"{drift_type}_drift_score",
            metric_value=drift_score,
            threshold=threshold,
        )
    
    def send_performance_alert(
        self,
        metric_name: str,
        metric_value: float,
        threshold: float,
        is_above_threshold: bool = True,
    ):
        """Convenience method for performance alerts."""
        
        comparison = "above" if is_above_threshold else "below"
        severity = 'critical' if abs(metric_value - threshold) > threshold * 0.5 else 'warning'
        
        self.send_alert(
            severity=severity,
            title=f"Performance Degradation: {metric_name}",
            message=f"{metric_name} is {comparison} acceptable threshold",
            metric_name=metric_name,
            metric_value=metric_value,
            threshold=threshold,
        )


def create_alert_manager_from_env() -> AlertManager:
    """Create AlertManager with channels from environment variables."""
    
    manager = AlertManager(
        source=os.getenv('ALERT_SOURCE', 'model-monitoring'),
        model_name=os.getenv('MODEL_NAME'),
        model_version=os.getenv('MODEL_VERSION'),
    )
    
    # Always add console for visibility
    manager.add_channel(ConsoleChannel())
    
    # Slack
    slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
    if slack_webhook:
        manager.add_channel(SlackChannel(slack_webhook))
    
    # PagerDuty (critical only)
    pagerduty_key = os.getenv('PAGERDUTY_INTEGRATION_KEY')
    if pagerduty_key:
        manager.add_channel(
            PagerDutyChannel(pagerduty_key),
            severities=['critical']
        )
    
    return manager


# Demo
if __name__ == '__main__':
    # Create manager with console output
    manager = AlertManager(
        source="demo-monitoring",
        model_name="stihl-sales-model",
        model_version="v4",
    )
    
    # Add console channel
    manager.add_channel(ConsoleChannel())
    
    # Send test alerts
    print("Sending test alerts...\n")
    
    manager.send_drift_alert(
        drift_type="data",
        drift_score=0.25,
        threshold=0.1,
        feature_name="customer_age",
    )
    
    manager.send_performance_alert(
        metric_name="latency_p95_ms",
        metric_value=150,
        threshold=100,
    )
    
    manager.send_alert(
        severity="info",
        title="Model Deployed",
        message="Model v4 successfully deployed to production",
    )
    
    print("\n✅ Demo complete")
