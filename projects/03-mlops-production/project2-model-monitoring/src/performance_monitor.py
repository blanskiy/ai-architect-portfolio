"""
Performance Monitor
Monitors model endpoint health and performance metrics.

Tracks:
- Latency (P50, P95, P99)
- Throughput (requests/second)
- Error rates
- Availability (uptime)

Usage:
    python performance_monitor.py --endpoint-url https://model.azureml.net/score
"""

import argparse
import json
import time
import statistics
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import deque
from typing import Optional
import threading

import requests


@dataclass
class PerformanceMetrics:
    """Current performance metrics snapshot."""
    timestamp: str
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_mean_ms: float
    throughput_rps: float
    error_rate_percent: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    uptime_percent: float
    
    
@dataclass
class HealthStatus:
    """Overall health status."""
    status: str  # 'healthy', 'degraded', 'unhealthy'
    checks: dict
    timestamp: str


class PerformanceMonitor:
    """
    Monitors model endpoint performance.
    
    Features:
    - Periodic health checks
    - Latency tracking with percentiles
    - Error rate monitoring
    - Throughput calculation
    - Health status aggregation
    """
    
    def __init__(
        self,
        endpoint_url: str,
        check_interval_seconds: int = 10,
        window_size: int = 100,
        latency_threshold_ms: float = 100,
        error_rate_threshold: float = 5.0,
    ):
        self.endpoint_url = endpoint_url
        self.check_interval = check_interval_seconds
        self.window_size = window_size
        self.latency_threshold = latency_threshold_ms
        self.error_rate_threshold = error_rate_threshold
        
        # Metrics storage
        self.latencies = deque(maxlen=window_size)
        self.errors = deque(maxlen=window_size)
        self.request_times = deque(maxlen=window_size)
        
        # Uptime tracking
        self.start_time = datetime.now()
        self.downtime_seconds = 0
        self.last_check_time = None
        self.last_status = 'unknown'
        
        # Sample request for health checks
        self.sample_request = {
            "features": [0.5, 0.3, 0.2, 0.1, 0.4]
        }
        
        # Thread control
        self._running = False
        self._monitor_thread = None
    
    def check_health(self) -> tuple[bool, float, Optional[str]]:
        """
        Perform a single health check.
        
        Returns:
            (is_healthy, latency_ms, error_message)
        """
        
        try:
            start_time = time.time()
            
            response = requests.post(
                self.endpoint_url,
                json=self.sample_request,
                timeout=5.0,
                headers={"Content-Type": "application/json"}
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                return True, latency_ms, None
            else:
                return False, latency_ms, f"HTTP {response.status_code}"
        
        except requests.exceptions.Timeout:
            return False, 5000.0, "Timeout"
        except requests.exceptions.ConnectionError:
            return False, 0.0, "Connection Error"
        except Exception as e:
            return False, 0.0, str(e)
    
    def record_check(self, is_healthy: bool, latency_ms: float):
        """Record health check result."""
        
        now = datetime.now()
        
        # Record latency
        if latency_ms > 0:
            self.latencies.append(latency_ms)
        
        # Record error
        self.errors.append(0 if is_healthy else 1)
        
        # Record request time for throughput
        self.request_times.append(time.time())
        
        # Track downtime
        if self.last_check_time:
            interval = (now - self.last_check_time).total_seconds()
            if not is_healthy:
                self.downtime_seconds += interval
        
        self.last_check_time = now
        self.last_status = 'healthy' if is_healthy else 'unhealthy'
    
    def get_metrics(self) -> PerformanceMetrics:
        """Calculate current performance metrics."""
        
        latency_list = list(self.latencies)
        error_list = list(self.errors)
        
        # Latency percentiles
        if latency_list:
            sorted_latencies = sorted(latency_list)
            n = len(sorted_latencies)
            
            latency_p50 = sorted_latencies[int(n * 0.50)]
            latency_p95 = sorted_latencies[int(n * 0.95)] if n > 1 else sorted_latencies[-1]
            latency_p99 = sorted_latencies[int(n * 0.99)] if n > 1 else sorted_latencies[-1]
            latency_mean = statistics.mean(latency_list)
        else:
            latency_p50 = latency_p95 = latency_p99 = latency_mean = 0.0
        
        # Error rate
        total_requests = len(error_list)
        failed_requests = sum(error_list)
        successful_requests = total_requests - failed_requests
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0.0
        
        # Throughput (requests in last 60 seconds)
        now = time.time()
        recent_requests = [t for t in self.request_times if now - t < 60]
        throughput = len(recent_requests) / 60 if recent_requests else 0.0
        
        # Uptime
        total_time = (datetime.now() - self.start_time).total_seconds()
        uptime = ((total_time - self.downtime_seconds) / total_time * 100) if total_time > 0 else 100.0
        
        return PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            latency_p50_ms=round(latency_p50, 2),
            latency_p95_ms=round(latency_p95, 2),
            latency_p99_ms=round(latency_p99, 2),
            latency_mean_ms=round(latency_mean, 2),
            throughput_rps=round(throughput, 2),
            error_rate_percent=round(error_rate, 2),
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            uptime_percent=round(uptime, 2),
        )
    
    def get_health_status(self) -> HealthStatus:
        """Get overall health status with individual checks."""
        
        metrics = self.get_metrics()
        
        checks = {
            'latency': {
                'status': 'pass' if metrics.latency_p95_ms <= self.latency_threshold else 'fail',
                'value': metrics.latency_p95_ms,
                'threshold': self.latency_threshold,
                'message': f"P95 latency: {metrics.latency_p95_ms}ms (threshold: {self.latency_threshold}ms)"
            },
            'error_rate': {
                'status': 'pass' if metrics.error_rate_percent <= self.error_rate_threshold else 'fail',
                'value': metrics.error_rate_percent,
                'threshold': self.error_rate_threshold,
                'message': f"Error rate: {metrics.error_rate_percent}% (threshold: {self.error_rate_threshold}%)"
            },
            'availability': {
                'status': 'pass' if metrics.uptime_percent >= 99.0 else 'warn' if metrics.uptime_percent >= 95.0 else 'fail',
                'value': metrics.uptime_percent,
                'threshold': 99.0,
                'message': f"Uptime: {metrics.uptime_percent}%"
            },
        }
        
        # Determine overall status
        failed_checks = sum(1 for c in checks.values() if c['status'] == 'fail')
        warn_checks = sum(1 for c in checks.values() if c['status'] == 'warn')
        
        if failed_checks > 0:
            overall_status = 'unhealthy'
        elif warn_checks > 0:
            overall_status = 'degraded'
        else:
            overall_status = 'healthy'
        
        return HealthStatus(
            status=overall_status,
            checks=checks,
            timestamp=datetime.now().isoformat(),
        )
    
    def start_monitoring(self):
        """Start background monitoring thread."""
        
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        print(f"📡 Started monitoring {self.endpoint_url}")
        print(f"   Check interval: {self.check_interval}s")
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        print("⏹️ Monitoring stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        
        while self._running:
            is_healthy, latency_ms, error = self.check_health()
            self.record_check(is_healthy, latency_ms)
            
            if not is_healthy:
                print(f"⚠️ Health check failed: {error}")
            
            time.sleep(self.check_interval)


def print_dashboard(monitor: PerformanceMonitor):
    """Print a simple text-based dashboard."""
    
    import os
    
    while True:
        # Clear screen
        os.system('cls' if os.name == 'nt' else 'clear')
        
        metrics = monitor.get_metrics()
        health = monitor.get_health_status()
        
        # Status icon
        status_icons = {'healthy': '🟢', 'degraded': '🟡', 'unhealthy': '🔴'}
        status_icon = status_icons.get(health.status, '⚪')
        
        print("=" * 60)
        print(f"       MODEL PERFORMANCE DASHBOARD")
        print("=" * 60)
        print(f"\n  Status: {status_icon} {health.status.upper()}")
        print(f"  Endpoint: {monitor.endpoint_url}")
        print(f"  Last Update: {metrics.timestamp}")
        
        print(f"\n{'─' * 60}")
        print("  LATENCY")
        print(f"{'─' * 60}")
        print(f"  P50:  {metrics.latency_p50_ms:>8.2f} ms")
        print(f"  P95:  {metrics.latency_p95_ms:>8.2f} ms {'⚠️' if metrics.latency_p95_ms > monitor.latency_threshold else '✅'}")
        print(f"  P99:  {metrics.latency_p99_ms:>8.2f} ms")
        print(f"  Mean: {metrics.latency_mean_ms:>8.2f} ms")
        
        print(f"\n{'─' * 60}")
        print("  THROUGHPUT & ERRORS")
        print(f"{'─' * 60}")
        print(f"  Throughput:  {metrics.throughput_rps:>6.2f} req/s")
        print(f"  Error Rate:  {metrics.error_rate_percent:>6.2f}% {'⚠️' if metrics.error_rate_percent > monitor.error_rate_threshold else '✅'}")
        print(f"  Total:       {metrics.total_requests:>6} requests")
        print(f"  Failed:      {metrics.failed_requests:>6} requests")
        
        print(f"\n{'─' * 60}")
        print("  AVAILABILITY")
        print(f"{'─' * 60}")
        print(f"  Uptime: {metrics.uptime_percent:.2f}%")
        
        print(f"\n{'─' * 60}")
        print("  HEALTH CHECKS")
        print(f"{'─' * 60}")
        for check_name, check_data in health.checks.items():
            status_icon = '✅' if check_data['status'] == 'pass' else '⚠️' if check_data['status'] == 'warn' else '❌'
            print(f"  {status_icon} {check_name}: {check_data['message']}")
        
        print("\n" + "=" * 60)
        print("  Press Ctrl+C to exit")
        
        time.sleep(5)


def main():
    parser = argparse.ArgumentParser(description='Model performance monitor')
    parser.add_argument('--endpoint-url', type=str, 
                        default='http://localhost:8080/predict',
                        help='Model endpoint URL')
    parser.add_argument('--check-interval', type=int, default=10,
                        help='Health check interval in seconds')
    parser.add_argument('--latency-threshold', type=float, default=100,
                        help='P95 latency threshold in ms')
    parser.add_argument('--error-threshold', type=float, default=5.0,
                        help='Error rate threshold in percent')
    parser.add_argument('--output-file', type=str, default=None,
                        help='Output file for metrics JSON')
    parser.add_argument('--dashboard', action='store_true',
                        help='Show live dashboard')
    
    args = parser.parse_args()
    
    # Create monitor
    monitor = PerformanceMonitor(
        endpoint_url=args.endpoint_url,
        check_interval_seconds=args.check_interval,
        latency_threshold_ms=args.latency_threshold,
        error_rate_threshold=args.error_threshold,
    )
    
    # Start monitoring
    monitor.start_monitoring()
    
    try:
        if args.dashboard:
            print_dashboard(monitor)
        else:
            print("\n📊 Monitoring started. Press Ctrl+C to stop and see results.\n")
            while True:
                time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n⏹️ Stopping monitor...")
    
    finally:
        monitor.stop_monitoring()
        
        # Print final metrics
        metrics = monitor.get_metrics()
        health = monitor.get_health_status()
        
        print("\n" + "=" * 60)
        print("FINAL METRICS")
        print("=" * 60)
        print(json.dumps(asdict(metrics), indent=2))
        
        print("\nHEALTH STATUS")
        print("=" * 60)
        print(json.dumps(asdict(health), indent=2))
        
        # Save to file if requested
        if args.output_file:
            with open(args.output_file, 'w') as f:
                json.dump({
                    'metrics': asdict(metrics),
                    'health': asdict(health),
                }, f, indent=2)
            print(f"\n📁 Results saved to: {args.output_file}")


if __name__ == '__main__':
    main()
