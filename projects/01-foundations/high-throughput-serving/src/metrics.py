#!/usr/bin/env python3
"""
Production metrics collection using Prometheus.

Metrics tracked:
- Request count
- Request duration
- Request size
- Error rates
- Model inference time
- Batch sizes
- Queue lengths
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from typing import Optional
import time


# Request metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

request_size = Histogram(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint']
)

response_size = Histogram(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint']
)

# Model-specific metrics
model_inference_duration = Histogram(
    'model_inference_duration_seconds',
    'Model inference duration in seconds',
    ['model_name'],
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
)

batch_size = Histogram(
    'batch_size',
    'Number of requests in batch',
    buckets=[1, 2, 4, 8, 16, 32]
)

queue_length = Gauge(
    'batch_queue_length',
    'Current length of batch queue'
)

# Error metrics
error_count = Counter(
    'errors_total',
    'Total errors',
    ['error_type', 'endpoint']
)

# System metrics
active_requests = Gauge(
    'active_requests',
    'Number of requests currently being processed'
)

model_load_time = Gauge(
    'model_load_time_seconds',
    'Time taken to load the model'
)


class MetricsTracker:
    """Helper class for tracking request metrics."""
    
    def __init__(self, method: str, endpoint: str):
        """
        Initialize metrics tracker.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
        """
        self.method = method
        self.endpoint = endpoint
        self.start_time = None
        self.request_size_bytes = 0
    
    def __enter__(self):
        """Start tracking."""
        self.start_time = time.time()
        active_requests.inc()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End tracking and record metrics."""
        duration = time.time() - self.start_time
        
        # Record duration
        request_duration.labels(
            method=self.method,
            endpoint=self.endpoint
        ).observe(duration)
        
        # Record status
        if exc_type is None:
            status = '200'
        elif exc_type.__name__ == 'HTTPException':
            status = str(getattr(exc_val, 'status_code', '500'))
        else:
            status = '500'
        
        request_count.labels(
            method=self.method,
            endpoint=self.endpoint,
            status=status
        ).inc()
        
        # Record errors
        if exc_type is not None:
            error_count.labels(
                error_type=exc_type.__name__,
                endpoint=self.endpoint
            ).inc()
        
        active_requests.dec()
        
        return False  # Don't suppress exceptions
    
    def set_request_size(self, size: int):
        """Record request size."""
        self.request_size_bytes = size
        request_size.labels(
            method=self.method,
            endpoint=self.endpoint
        ).observe(size)
    
    def set_response_size(self, size: int):
        """Record response size."""
        response_size.labels(
            method=self.method,
            endpoint=self.endpoint
        ).observe(size)


def track_inference(model_name: str, duration_seconds: float):
    """
    Track model inference time.
    
    Args:
        model_name: Name of the model
        duration_seconds: Inference duration in seconds
    """
    model_inference_duration.labels(model_name=model_name).observe(duration_seconds)


def track_batch(size: int):
    """
    Track batch size.
    
    Args:
        size: Number of requests in batch
    """
    batch_size.observe(size)


def update_queue_length(length: int):
    """
    Update batch queue length.
    
    Args:
        length: Current queue length
    """
    queue_length.set(length)


def get_metrics() -> tuple:
    """
    Get current metrics in Prometheus format.
    
    Returns:
        Tuple of (metrics_data, content_type)
    """
    return generate_latest(), CONTENT_TYPE_LATEST


# Example usage
if __name__ == "__main__":
    # Track a request
    with MetricsTracker("POST", "/predict") as tracker:
        tracker.set_request_size(1024 * 100)  # 100KB
        time.sleep(0.5)  # Simulate work
        tracker.set_response_size(512)
    
    # Track inference
    track_inference("resnet50", 0.85)
    
    # Track batch
    track_batch(4)
    
    # Update queue
    update_queue_length(3)
    
    # Print metrics
    print("Metrics:")
    print(generate_latest().decode('utf-8'))
