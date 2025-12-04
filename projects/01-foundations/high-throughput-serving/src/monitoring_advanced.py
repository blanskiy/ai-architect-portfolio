"""
Advanced Monitoring & Alerting Module
Week 3 Day 15: SLOs, Dashboards, and Alerts
"""

import time
import random
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import json


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status"""
    FIRING = "firing"
    RESOLVED = "resolved"


@dataclass
class SLODefinition:
    """Defines a Service Level Objective"""
    name: str
    description: str
    target: float  # Target percentage (e.g., 99.0 for 99%)
    window_minutes: int  # Measurement window
    sli_type: str  # "latency", "availability", "throughput"
    threshold: Optional[float] = None  # For latency SLOs (e.g., 500ms)
    
    def __str__(self):
        if self.sli_type == "latency":
            return f"{self.name}: {self.target}% of requests < {self.threshold}ms"
        elif self.sli_type == "availability":
            return f"{self.name}: {self.target}% success rate"
        else:
            return f"{self.name}: {self.target}% target"


@dataclass
class Alert:
    """Represents an alert"""
    name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    timestamp: datetime
    value: float
    threshold: float
    labels: Dict = field(default_factory=dict)
    
    def to_dict(self):
        return {
            "name": self.name,
            "severity": self.severity.value,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "threshold": self.threshold,
            "labels": self.labels
        }


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: datetime
    value: float
    labels: Dict = field(default_factory=dict)


class MetricsCollector:
    """
    Collects and stores metrics for monitoring.
    Supports histograms, counters, and gauges.
    """
    
    def __init__(self, retention_minutes: int = 60):
        self.retention = timedelta(minutes=retention_minutes)
        self.metrics: Dict[str, List[MetricPoint]] = {
            "request_latency_ms": [],
            "request_count": [],
            "error_count": [],
            "model_load_time_ms": [],
            "batch_size": [],
            "cache_hits": [],
            "cache_misses": [],
            "memory_usage_mb": [],
            "cpu_usage_percent": [],
            "inference_time_ms": [],
        }
        self.start_time = datetime.now()
    
    def record(self, metric_name: str, value: float, labels: Dict = None):
        """Record a metric value"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        
        point = MetricPoint(
            timestamp=datetime.now(),
            value=value,
            labels=labels or {}
        )
        self.metrics[metric_name].append(point)
        self._cleanup(metric_name)
    
    def _cleanup(self, metric_name: str):
        """Remove old data points"""
        cutoff = datetime.now() - self.retention
        self.metrics[metric_name] = [
            p for p in self.metrics[metric_name] 
            if p.timestamp > cutoff
        ]
    
    def get_values(self, metric_name: str, minutes: int = 5) -> List[float]:
        """Get metric values for the last N minutes"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [
            p.value for p in self.metrics.get(metric_name, [])
            if p.timestamp > cutoff
        ]
    
    def get_percentile(self, metric_name: str, percentile: float, minutes: int = 5) -> float:
        """Calculate percentile for a metric"""
        values = self.get_values(metric_name, minutes)
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def get_rate(self, metric_name: str, minutes: int = 5) -> float:
        """Calculate rate (events per second)"""
        values = self.get_values(metric_name, minutes)
        if not values:
            return 0.0
        return len(values) / (minutes * 60)
    
    def get_sum(self, metric_name: str, minutes: int = 5) -> float:
        """Get sum of metric values"""
        return sum(self.get_values(metric_name, minutes))
    
    def get_avg(self, metric_name: str, minutes: int = 5) -> float:
        """Get average of metric values"""
        values = self.get_values(metric_name, minutes)
        return statistics.mean(values) if values else 0.0


class SLOMonitor:
    """
    Monitors Service Level Objectives and calculates error budgets.
    """
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.slos: Dict[str, SLODefinition] = {}
        
    def register_slo(self, slo: SLODefinition):
        """Register an SLO to monitor"""
        self.slos[slo.name] = slo
        print(f"📊 Registered SLO: {slo}")
    
    def check_slo(self, slo_name: str) -> Dict:
        """Check if an SLO is being met"""
        slo = self.slos.get(slo_name)
        if not slo:
            return {"error": f"SLO '{slo_name}' not found"}
        
        if slo.sli_type == "latency":
            return self._check_latency_slo(slo)
        elif slo.sli_type == "availability":
            return self._check_availability_slo(slo)
        else:
            return {"error": f"Unknown SLI type: {slo.sli_type}"}
    
    def _check_latency_slo(self, slo: SLODefinition) -> Dict:
        """Check latency SLO"""
        latencies = self.collector.get_values("request_latency_ms", slo.window_minutes)
        
        if not latencies:
            return {
                "slo": slo.name,
                "status": "NO_DATA",
                "message": "No data available"
            }
        
        good_requests = sum(1 for l in latencies if l < slo.threshold)
        total_requests = len(latencies)
        current_percentage = (good_requests / total_requests) * 100
        
        is_met = current_percentage >= slo.target
        error_budget_remaining = current_percentage - slo.target
        
        return {
            "slo": slo.name,
            "target": f"{slo.target}% < {slo.threshold}ms",
            "current": f"{current_percentage:.2f}%",
            "is_met": is_met,
            "status": "✅ MET" if is_met else "❌ VIOLATED",
            "good_requests": good_requests,
            "total_requests": total_requests,
            "error_budget_remaining": f"{error_budget_remaining:.2f}%",
            "window_minutes": slo.window_minutes
        }
    
    def _check_availability_slo(self, slo: SLODefinition) -> Dict:
        """Check availability SLO"""
        requests = self.collector.get_sum("request_count", slo.window_minutes)
        errors = self.collector.get_sum("error_count", slo.window_minutes)
        
        if requests == 0:
            return {
                "slo": slo.name,
                "status": "NO_DATA",
                "message": "No data available"
            }
        
        success_rate = ((requests - errors) / requests) * 100
        is_met = success_rate >= slo.target
        error_budget_remaining = success_rate - slo.target
        
        return {
            "slo": slo.name,
            "target": f"{slo.target}% success rate",
            "current": f"{success_rate:.2f}%",
            "is_met": is_met,
            "status": "✅ MET" if is_met else "❌ VIOLATED",
            "total_requests": int(requests),
            "errors": int(errors),
            "error_budget_remaining": f"{error_budget_remaining:.2f}%",
            "window_minutes": slo.window_minutes
        }
    
    def get_all_slo_status(self) -> List[Dict]:
        """Get status of all registered SLOs"""
        return [self.check_slo(name) for name in self.slos.keys()]


class AlertManager:
    """
    Manages alerts based on metric thresholds.
    """
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.alert_rules: List[Dict] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_handlers: List[Callable] = []
    
    def add_rule(self, name: str, metric: str, condition: str, 
                 threshold: float, severity: AlertSeverity,
                 duration_minutes: int = 1):
        """Add an alerting rule"""
        self.alert_rules.append({
            "name": name,
            "metric": metric,
            "condition": condition,  # "gt", "lt", "gte", "lte"
            "threshold": threshold,
            "severity": severity,
            "duration_minutes": duration_minutes
        })
        print(f"🔔 Added alert rule: {name} ({metric} {condition} {threshold})")
    
    def add_notification_handler(self, handler: Callable):
        """Add a function to call when alerts fire"""
        self.notification_handlers.append(handler)
    
    def evaluate_rules(self) -> List[Alert]:
        """Evaluate all alert rules and return any firing alerts"""
        new_alerts = []
        
        for rule in self.alert_rules:
            value = self._get_metric_value(rule["metric"], rule["duration_minutes"])
            is_firing = self._check_condition(value, rule["condition"], rule["threshold"])
            
            alert_key = rule["name"]
            
            if is_firing:
                if alert_key not in self.active_alerts:
                    # New alert firing
                    alert = Alert(
                        name=rule["name"],
                        severity=rule["severity"],
                        status=AlertStatus.FIRING,
                        message=f"{rule['metric']} is {value:.2f} (threshold: {rule['threshold']})",
                        timestamp=datetime.now(),
                        value=value,
                        threshold=rule["threshold"]
                    )
                    self.active_alerts[alert_key] = alert
                    self.alert_history.append(alert)
                    new_alerts.append(alert)
                    self._notify(alert)
            else:
                if alert_key in self.active_alerts:
                    # Alert resolved
                    alert = self.active_alerts[alert_key]
                    alert.status = AlertStatus.RESOLVED
                    alert.message = f"Resolved: {rule['metric']} is now {value:.2f}"
                    self._notify(alert)
                    del self.active_alerts[alert_key]
        
        return new_alerts
    
    def _get_metric_value(self, metric: str, minutes: int) -> float:
        """Get aggregated metric value for alerting"""
        if "p99" in metric:
            base_metric = metric.replace("_p99", "")
            return self.collector.get_percentile(base_metric, 99, minutes)
        elif "p95" in metric:
            base_metric = metric.replace("_p95", "")
            return self.collector.get_percentile(base_metric, 95, minutes)
        elif "rate" in metric:
            base_metric = metric.replace("_rate", "")
            return self.collector.get_rate(base_metric, minutes)
        else:
            return self.collector.get_avg(metric, minutes)
    
    def _check_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Check if condition is met"""
        if condition == "gt":
            return value > threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "gte":
            return value >= threshold
        elif condition == "lte":
            return value <= threshold
        return False
    
    def _notify(self, alert: Alert):
        """Send notifications for an alert"""
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                print(f"Notification error: {e}")
    
    def get_active_alerts(self) -> List[Dict]:
        """Get all currently active alerts"""
        return [a.to_dict() for a in self.active_alerts.values()]


class MonitoringDashboard:
    """
    Creates a text-based monitoring dashboard.
    """
    
    def __init__(self, collector: MetricsCollector, 
                 slo_monitor: SLOMonitor,
                 alert_manager: AlertManager):
        self.collector = collector
        self.slo_monitor = slo_monitor
        self.alert_manager = alert_manager
    
    def render(self) -> str:
        """Render the dashboard as text"""
        lines = []
        lines.append("=" * 80)
        lines.append("📊 ML API MONITORING DASHBOARD")
        lines.append(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        
        # Active Alerts Section
        lines.append("\n🚨 ACTIVE ALERTS")
        lines.append("-" * 40)
        alerts = self.alert_manager.get_active_alerts()
        if alerts:
            for alert in alerts:
                icon = "🔴" if alert["severity"] == "critical" else "🟡"
                lines.append(f"{icon} [{alert['severity'].upper()}] {alert['name']}")
                lines.append(f"   {alert['message']}")
        else:
            lines.append("✅ No active alerts")
        
        # SLO Status Section
        lines.append("\n📈 SLO STATUS")
        lines.append("-" * 40)
        for slo_status in self.slo_monitor.get_all_slo_status():
            if "error" not in slo_status and slo_status.get("status") != "NO_DATA":
                icon = "✅" if slo_status.get("is_met") else "❌"
                lines.append(f"{icon} {slo_status['slo']}: {slo_status['current']} (target: {slo_status['target']})")
                lines.append(f"   Error Budget Remaining: {slo_status['error_budget_remaining']}")
        
        # Key Metrics Section
        lines.append("\n📉 KEY METRICS (Last 5 min)")
        lines.append("-" * 40)
        
        # Latency metrics
        p50 = self.collector.get_percentile("request_latency_ms", 50, 5)
        p95 = self.collector.get_percentile("request_latency_ms", 95, 5)
        p99 = self.collector.get_percentile("request_latency_ms", 99, 5)
        lines.append(f"Latency:    p50={p50:.1f}ms  p95={p95:.1f}ms  p99={p99:.1f}ms")
        
        # Request rate
        req_rate = self.collector.get_rate("request_count", 5)
        lines.append(f"Throughput: {req_rate:.2f} req/sec")
        
        # Error rate
        errors = self.collector.get_sum("error_count", 5)
        requests = self.collector.get_sum("request_count", 5)
        error_rate = (errors / requests * 100) if requests > 0 else 0
        lines.append(f"Error Rate: {error_rate:.2f}%")
        
        # Cache hit rate
        hits = self.collector.get_sum("cache_hits", 5)
        misses = self.collector.get_sum("cache_misses", 5)
        cache_total = hits + misses
        cache_rate = (hits / cache_total * 100) if cache_total > 0 else 0
        lines.append(f"Cache Hit:  {cache_rate:.1f}%")
        
        # Inference time
        avg_inference = self.collector.get_avg("inference_time_ms", 5)
        lines.append(f"Inference:  {avg_inference:.1f}ms avg")
        
        lines.append("\n" + "=" * 80)
        
        return "\n".join(lines)


def console_alert_handler(alert: Alert):
    """Simple console alert handler"""
    icon = "🔴" if alert.severity == AlertSeverity.CRITICAL else "🟡" if alert.severity == AlertSeverity.WARNING else "ℹ️"
    status = "FIRING" if alert.status == AlertStatus.FIRING else "RESOLVED"
    print(f"\n{icon} ALERT {status}: {alert.name}")
    print(f"   {alert.message}")


def simulate_traffic(collector: MetricsCollector, num_requests: int = 100):
    """Simulate API traffic for demo"""
    print(f"\n🔄 Simulating {num_requests} requests...")
    
    for i in range(num_requests):
        # Simulate request latency (mostly good, some slow)
        if random.random() < 0.95:
            latency = random.gauss(100, 20)  # Normal: ~100ms
        else:
            latency = random.gauss(600, 100)  # Slow: ~600ms
        
        collector.record("request_latency_ms", max(latency, 10))
        collector.record("request_count", 1)
        
        # Simulate errors (2% error rate)
        if random.random() < 0.02:
            collector.record("error_count", 1)
        
        # Simulate cache
        if random.random() < 0.8:
            collector.record("cache_hits", 1)
        else:
            collector.record("cache_misses", 1)
        
        # Simulate inference time
        inference_time = random.gauss(70, 15)
        collector.record("inference_time_ms", max(inference_time, 20))
        
        if (i + 1) % 25 == 0:
            print(f"   Processed {i + 1} requests...")
    
    print("✅ Simulation complete!")


def main():
    """Main demo function"""
    print("=" * 80)
    print("🎯 ADVANCED MONITORING & ALERTING DEMO")
    print("=" * 80)
    
    # Initialize components
    collector = MetricsCollector(retention_minutes=60)
    slo_monitor = SLOMonitor(collector)
    alert_manager = AlertManager(collector)
    
    # Register SLOs
    print("\n📊 Registering SLOs...")
    slo_monitor.register_slo(SLODefinition(
        name="Latency SLO",
        description="99% of requests should complete in under 500ms",
        target=99.0,
        window_minutes=5,
        sli_type="latency",
        threshold=500
    ))
    
    slo_monitor.register_slo(SLODefinition(
        name="Availability SLO",
        description="99.9% of requests should succeed",
        target=99.9,
        window_minutes=5,
        sli_type="availability"
    ))
    
    # Register Alert Rules
    print("\n🔔 Registering Alert Rules...")
    alert_manager.add_rule(
        name="High Latency",
        metric="request_latency_ms_p99",
        condition="gt",
        threshold=500,
        severity=AlertSeverity.WARNING,
        duration_minutes=1
    )
    
    alert_manager.add_rule(
        name="Critical Latency",
        metric="request_latency_ms_p99",
        condition="gt",
        threshold=1000,
        severity=AlertSeverity.CRITICAL,
        duration_minutes=1
    )
    
    alert_manager.add_rule(
        name="High Error Rate",
        metric="error_count_rate",
        condition="gt",
        threshold=0.05,  # 5% error rate
        severity=AlertSeverity.CRITICAL,
        duration_minutes=1
    )
    
    alert_manager.add_rule(
        name="Low Cache Hit Rate",
        metric="cache_hits",
        condition="lt",
        threshold=50,
        severity=AlertSeverity.WARNING,
        duration_minutes=1
    )
    
    # Add notification handler
    alert_manager.add_notification_handler(console_alert_handler)
    
    # Create dashboard
    dashboard = MonitoringDashboard(collector, slo_monitor, alert_manager)
    
    # Simulate traffic
    simulate_traffic(collector, num_requests=100)
    
    # Evaluate alerts
    print("\n🔍 Evaluating alert rules...")
    alert_manager.evaluate_rules()
    
    # Render dashboard
    print(dashboard.render())
    
    # Print SLO details
    print("\n📋 DETAILED SLO REPORT")
    print("-" * 40)
    for slo_status in slo_monitor.get_all_slo_status():
        print(json.dumps(slo_status, indent=2))
    
    print("\n✅ Demo complete!")
    print("\nKey Takeaways:")
    print("  1. SLIs measure what matters (latency, availability)")
    print("  2. SLOs set targets for SLIs (99% < 500ms)")
    print("  3. Error budgets show how much room you have")
    print("  4. Alerts notify when thresholds are breached")
    print("  5. Dashboards provide at-a-glance visibility")


if __name__ == "__main__":
    main()