"""
Metrics Collector for Model Monitoring
Exposes model metrics to Prometheus for scraping.

Metrics exposed:
- model_prediction_latency_seconds (histogram)
- model_predictions_total (counter)
- model_prediction_errors_total (counter)
- model_prediction_value (gauge) - for regression
- model_prediction_class (counter) - for classification
- model_data_drift_score (gauge)
- model_prediction_drift_score (gauge)

Usage:
    python metrics_collector.py --prometheus-port 8000
"""

import argparse
import json
import time
import threading
from datetime import datetime
from collections import deque
from typing import Optional

# Prometheus client
try:
    from prometheus_client import (
        start_http_server,
        Counter,
        Histogram,
        Gauge,
        Summary,
        Info,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    print("⚠️ prometheus_client not installed. Install with: pip install prometheus-client")


class ModelMetricsCollector:
    """
    Collects and exposes model metrics for Prometheus.
    
    Usage:
        collector = ModelMetricsCollector(model_name="sales-predictor")
        collector.start_server(port=8000)
        
        # On each prediction:
        with collector.track_prediction():
            result = model.predict(features)
        collector.record_prediction(result, features)
    """
    
    def __init__(
        self,
        model_name: str,
        model_version: str = "unknown",
        enable_drift_tracking: bool = True,
        drift_window_size: int = 1000,
    ):
        self.model_name = model_name
        self.model_version = model_version
        self.enable_drift_tracking = enable_drift_tracking
        
        # Store recent predictions for drift calculation
        self.recent_predictions = deque(maxlen=drift_window_size)
        self.recent_features = deque(maxlen=drift_window_size)
        
        # Reference distributions (set from training data)
        self.reference_predictions = None
        self.reference_features = None
        
        if PROMETHEUS_AVAILABLE:
            self._init_metrics()
    
    def _init_metrics(self):
        """Initialize Prometheus metrics."""
        
        # Labels for all metrics
        labels = ['model_name', 'model_version']
        
        # Model info
        self.model_info = Info(
            'model',
            'Model information'
        )
        self.model_info.info({
            'name': self.model_name,
            'version': self.model_version,
            'started_at': datetime.now().isoformat(),
        })
        
        # Prediction latency (histogram with buckets)
        self.latency_histogram = Histogram(
            'model_prediction_latency_seconds',
            'Time spent processing prediction',
            labels,
            buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0)
        )
        
        # Total predictions counter
        self.predictions_total = Counter(
            'model_predictions_total',
            'Total number of predictions',
            labels + ['status']
        )
        
        # Prediction errors counter
        self.errors_total = Counter(
            'model_prediction_errors_total',
            'Total number of prediction errors',
            labels + ['error_type']
        )
        
        # Prediction value (for monitoring distribution)
        self.prediction_value = Gauge(
            'model_prediction_value',
            'Current prediction value (for regression)',
            labels
        )
        
        # Prediction class distribution
        self.prediction_class = Counter(
            'model_prediction_class_total',
            'Predictions by class',
            labels + ['predicted_class']
        )
        
        # Drift scores
        self.data_drift_score = Gauge(
            'model_data_drift_score',
            'Current data drift score',
            labels
        )
        
        self.prediction_drift_score = Gauge(
            'model_prediction_drift_score',
            'Current prediction drift score',
            labels
        )
        
        # Feature drift per feature
        self.feature_drift_score = Gauge(
            'model_feature_drift_score',
            'Drift score per feature',
            labels + ['feature_name']
        )
        
        # Request throughput
        self.throughput_gauge = Gauge(
            'model_throughput_requests_per_second',
            'Current throughput in requests per second',
            labels
        )
        
        # Initialize throughput tracking
        self._request_times = deque(maxlen=1000)
        self._throughput_thread = None
    
    def start_server(self, port: int = 8000):
        """Start Prometheus metrics HTTP server."""
        
        if not PROMETHEUS_AVAILABLE:
            print("⚠️ Cannot start server: prometheus_client not installed")
            return
        
        print(f"📊 Starting Prometheus metrics server on port {port}")
        start_http_server(port)
        
        # Start background thread for throughput calculation
        self._throughput_thread = threading.Thread(
            target=self._calculate_throughput_loop,
            daemon=True
        )
        self._throughput_thread.start()
        
        print(f"✅ Metrics available at http://localhost:{port}/metrics")
    
    def _calculate_throughput_loop(self):
        """Background thread to calculate throughput."""
        while True:
            time.sleep(5)
            self._update_throughput()
    
    def _update_throughput(self):
        """Calculate and update throughput gauge."""
        now = time.time()
        recent = [t for t in self._request_times if now - t < 60]  # Last 60 seconds
        throughput = len(recent) / 60 if recent else 0
        
        if PROMETHEUS_AVAILABLE:
            self.throughput_gauge.labels(
                model_name=self.model_name,
                model_version=self.model_version,
            ).set(throughput)
    
    def track_prediction(self):
        """Context manager for tracking prediction latency."""
        
        class PredictionTimer:
            def __init__(timer_self, collector):
                timer_self.collector = collector
                timer_self.start_time = None
            
            def __enter__(timer_self):
                timer_self.start_time = time.time()
                return timer_self
            
            def __exit__(timer_self, exc_type, exc_val, exc_tb):
                latency = time.time() - timer_self.start_time
                
                if PROMETHEUS_AVAILABLE:
                    timer_self.collector.latency_histogram.labels(
                        model_name=timer_self.collector.model_name,
                        model_version=timer_self.collector.model_version,
                    ).observe(latency)
                
                timer_self.collector._request_times.append(time.time())
                
                # Record success/failure
                status = 'error' if exc_type else 'success'
                if PROMETHEUS_AVAILABLE:
                    timer_self.collector.predictions_total.labels(
                        model_name=timer_self.collector.model_name,
                        model_version=timer_self.collector.model_version,
                        status=status,
                    ).inc()
                
                return False  # Don't suppress exceptions
        
        return PredictionTimer(self)
    
    def record_prediction(
        self,
        prediction: float | int | str,
        features: Optional[dict] = None,
        is_classification: bool = True,
    ):
        """
        Record a prediction for monitoring.
        
        Args:
            prediction: The model's prediction
            features: Input features (for drift detection)
            is_classification: Whether this is a classification task
        """
        
        if not PROMETHEUS_AVAILABLE:
            return
        
        # Record prediction value/class
        if is_classification:
            self.prediction_class.labels(
                model_name=self.model_name,
                model_version=self.model_version,
                predicted_class=str(prediction),
            ).inc()
        else:
            self.prediction_value.labels(
                model_name=self.model_name,
                model_version=self.model_version,
            ).set(float(prediction))
        
        # Store for drift detection
        if self.enable_drift_tracking:
            self.recent_predictions.append(prediction)
            if features:
                self.recent_features.append(features)
    
    def record_error(self, error_type: str):
        """Record a prediction error."""
        
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.errors_total.labels(
            model_name=self.model_name,
            model_version=self.model_version,
            error_type=error_type,
        ).inc()
    
    def set_reference_data(self, predictions: list, features: list[dict] = None):
        """
        Set reference (training) data for drift comparison.
        
        Args:
            predictions: List of predictions from training data
            features: List of feature dicts from training data
        """
        self.reference_predictions = predictions
        self.reference_features = features
    
    def update_drift_scores(self, data_drift: float, prediction_drift: float):
        """
        Update drift score gauges.
        
        Called periodically by drift detection job.
        """
        
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.data_drift_score.labels(
            model_name=self.model_name,
            model_version=self.model_version,
        ).set(data_drift)
        
        self.prediction_drift_score.labels(
            model_name=self.model_name,
            model_version=self.model_version,
        ).set(prediction_drift)
    
    def update_feature_drift(self, feature_name: str, drift_score: float):
        """Update drift score for a specific feature."""
        
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.feature_drift_score.labels(
            model_name=self.model_name,
            model_version=self.model_version,
            feature_name=feature_name,
        ).set(drift_score)
    
    def get_recent_predictions(self) -> list:
        """Get recent predictions for drift analysis."""
        return list(self.recent_predictions)
    
    def get_recent_features(self) -> list[dict]:
        """Get recent features for drift analysis."""
        return list(self.recent_features)


def simulate_predictions(collector: ModelMetricsCollector, num_predictions: int = 100):
    """Simulate predictions for demo purposes."""
    
    import random
    import numpy as np
    
    print(f"\n🔄 Simulating {num_predictions} predictions...")
    
    for i in range(num_predictions):
        # Simulate features
        features = {
            'feature_1': random.gauss(0, 1),
            'feature_2': random.gauss(0, 1),
            'feature_3': random.gauss(0, 1),
        }
        
        # Simulate prediction with tracking
        with collector.track_prediction():
            # Simulate some latency
            time.sleep(random.uniform(0.01, 0.1))
            
            # Simulate occasional errors
            if random.random() < 0.02:  # 2% error rate
                collector.record_error('timeout')
                continue
            
            # Make prediction
            prediction = random.choice([0, 1])
        
        # Record prediction
        collector.record_prediction(prediction, features)
        
        if (i + 1) % 20 == 0:
            print(f"   Completed {i + 1}/{num_predictions} predictions")
    
    # Update some drift scores
    collector.update_drift_scores(
        data_drift=random.uniform(0.05, 0.15),
        prediction_drift=random.uniform(0.03, 0.12),
    )
    
    for feature in ['feature_1', 'feature_2', 'feature_3']:
        collector.update_feature_drift(feature, random.uniform(0.02, 0.18))
    
    print("✅ Simulation complete")


def main():
    parser = argparse.ArgumentParser(description='Model metrics collector')
    parser.add_argument('--model-name', type=str, default='stihl-sales-model',
                        help='Model name for labeling')
    parser.add_argument('--model-version', type=str, default='v1',
                        help='Model version')
    parser.add_argument('--prometheus-port', type=int, default=8000,
                        help='Port for Prometheus metrics')
    parser.add_argument('--simulate', action='store_true',
                        help='Simulate predictions for demo')
    
    args = parser.parse_args()
    
    # Create collector
    collector = ModelMetricsCollector(
        model_name=args.model_name,
        model_version=args.model_version,
    )
    
    # Start Prometheus server
    collector.start_server(port=args.prometheus_port)
    
    if args.simulate:
        # Run simulation
        while True:
            simulate_predictions(collector)
            print("\n⏳ Waiting 30 seconds before next batch...")
            time.sleep(30)
    else:
        print("\n📡 Collector running. Metrics available at:")
        print(f"   http://localhost:{args.prometheus_port}/metrics")
        print("\nPress Ctrl+C to stop")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Shutting down")


if __name__ == '__main__':
    main()
