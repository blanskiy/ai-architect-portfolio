#!/usr/bin/env python3
"""
Locust load testing for ResNet-50 serving API.

Usage:
    Basic: locust -f tests/locust/locustfile.py
    Headless: locust -f tests/locust/locustfile.py --headless -u 10 -r 2 -t 60s
"""

from locust import HttpUser, task, between, events
import os
import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get test image path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
IMAGE_PATH = os.path.join(PROJECT_ROOT, "test-data", "dog.jpg")

# Verify image exists
if not os.path.exists(IMAGE_PATH):
    logger.error(f"Test image not found at {IMAGE_PATH}")
    raise FileNotFoundError(f"Test image not found: {IMAGE_PATH}")

logger.info(f"Test image found: {IMAGE_PATH}")


class ResNetUser(HttpUser):
    """
    Simulates a user making prediction requests to the ResNet-50 API.
    
    User behavior:
    - Waits 1-3 seconds between requests (realistic user behavior)
    - Sends image for prediction
    - Tracks success/failure
    """
    
    # Wait time between requests (simulates think time)
    wait_time = between(1, 3)  # Random wait 1-3 seconds
    
    # Store metrics
    request_count = 0
    success_count = 0
    failure_count = 0
    
    def on_start(self):
        """Called when a user starts. Setup goes here."""
        logger.info(f"User {id(self)} starting...")
        
        # Test health endpoint first
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                logger.info("API health check passed")
            else:
                logger.error(f"API health check failed: {response.status_code}")
                response.failure("Health check failed")
    
    @task(10)  # Weight: 10 (more common)
    def predict_image(self):
        """
        Main task: Send image for prediction.
        Weight 10 = runs 10× more often than other tasks.
        """
        ResNetUser.request_count += 1
        
        with open(IMAGE_PATH, 'rb') as image_file:
            files = {'file': ('dog.jpg', image_file, 'image/jpeg')}
            
            with self.client.post(
                "/predict",
                files=files,
                catch_response=True,
                name="predict"  # Groups requests in UI
            ) as response:
                
                if response.status_code == 200:
                    ResNetUser.success_count += 1
                    data = response.json()
                    
                    # Validate response structure
                    if 'predictions' in data and len(data['predictions']) > 0:
                        top_prediction = data['predictions'][0]['class_name']
                        confidence = data['predictions'][0]['confidence']
                        latency = data.get('latency_ms', 0)
                        
                        logger.debug(
                            f"Success: {top_prediction} "
                            f"({confidence:.2%}) in {latency:.0f}ms"
                        )
                        response.success()
                    else:
                        logger.warning("Response missing predictions")
                        response.failure("Invalid response structure")
                        ResNetUser.failure_count += 1
                else:
                    ResNetUser.failure_count += 1
                    logger.error(f"Request failed: {response.status_code}")
                    response.failure(f"Got status {response.status_code}")
    
    @task(1)  # Weight: 1 (less common)
    def check_health(self):
        """
        Secondary task: Check API health.
        Weight 1 = runs 1/10th as often as predict_image.
        """
        with self.client.get("/health", catch_response=True, name="health") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check returned {response.status_code}")
    
    @task(1)  # Weight: 1
    def check_metrics(self):
        """
        Secondary task: Check metrics endpoint.
        """
        with self.client.get("/metrics", catch_response=True, name="metrics") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Metrics returned {response.status_code}")


# Event handlers for custom metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    logger.info("="*60)
    logger.info("🚀 Locust Load Test Starting")
    logger.info("="*60)
    logger.info(f"Test image: {IMAGE_PATH}")
    logger.info(f"Target: {environment.host}")
    logger.info("="*60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops. Print summary."""
    logger.info("="*60)
    logger.info("✅ Locust Load Test Complete")
    logger.info("="*60)
    logger.info(f"Total requests: {ResNetUser.request_count}")
    logger.info(f"Successful: {ResNetUser.success_count}")
    logger.info(f"Failed: {ResNetUser.failure_count}")
    
    if ResNetUser.request_count > 0:
        success_rate = (ResNetUser.success_count / ResNetUser.request_count) * 100
        logger.info(f"Success rate: {success_rate:.2f}%")
    
    logger.info("="*60)


# Custom load shape (optional - for advanced testing)
from locust import LoadTestShape

class StepLoadShape(LoadTestShape):
    """
    A step load shape that gradually increases load.
    
    Steps:
    1. 1 user for 30s (warmup)
    2. 5 users for 60s (light load)
    3. 10 users for 60s (medium load)
    4. 20 users for 60s (heavy load)
    5. Stop
    """
    
    step_time = 30  # seconds per step
    step_load = [1, 5, 10, 20]  # users per step
    spawn_rate = 2  # users to spawn per second
    time_limit = 210  # total test time (30+60+60+60)
    
    def tick(self):
        """
        Returns (user_count, spawn_rate) at the current time.
        Return None to stop the test.
        """
        run_time = self.get_run_time()
        
        if run_time > self.time_limit:
            return None  # Stop test
        
        # Calculate current step
        current_step = int(run_time / self.step_time)
        
        if current_step < len(self.step_load):
            return (self.step_load[current_step], self.spawn_rate)
        
        return None