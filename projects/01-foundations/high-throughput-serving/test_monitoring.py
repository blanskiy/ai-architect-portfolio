#!/usr/bin/env python3
"""Quick test script for monitoring endpoints."""

import requests
import json

API_URL = "http://localhost:8000"

print("="*60)
print("Testing Monitoring Endpoints")
print("="*60)

# Test 1: Send prediction
print("\n1. Testing /predict endpoint...")
try:
    with open("test-data/dog.jpg", "rb") as f:
        files = {"file": ("dog.jpg", f, "image/jpeg")}
        response = requests.post(f"{API_URL}/predict", files=files)
    
    if response.status_code == 200:
        print("✓ Prediction successful!")
        data = response.json()
        print(f"  Request ID: {data['request_id']}")
        print(f"  Top prediction: {data['predictions'][0]['class_name']}")
        print(f"  Confidence: {data['predictions'][0]['confidence']:.2%}")
        print(f"  Latency: {data['latency_ms']:.0f}ms")
        print(f"  Inference: {data['inference_ms']:.0f}ms")
    else:
        print(f"✗ Failed: {response.status_code}")
        print(f"  Error: {response.text}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 2: Check metrics
print("\n2. Testing /metrics endpoint...")
try:
    response = requests.get(f"{API_URL}/metrics")
    if response.status_code == 200:
        print("✓ Metrics available!")
        data = response.json()
        print(f"  Total requests: {data['requests']['total']}")
        print(f"  Success rate: {data['requests']['success_rate']:.1f}%")
        print(f"  Avg latency: {data['performance']['avg_latency_ms']:.0f}ms")
    else:
        print(f"✗ Failed: {response.status_code}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 3: Check Prometheus metrics
print("\n3. Testing /prometheus endpoint...")
try:
    response = requests.get(f"{API_URL}/prometheus")
    if response.status_code == 200:
        print("✓ Prometheus metrics available!")
        lines = response.text.split('\n')
        # Show first few metrics
        metric_lines = [l for l in lines if l and not l.startswith('#')][:5]
        print("  Sample metrics:")
        for line in metric_lines:
            print(f"    {line}")
    else:
        print(f"✗ Failed: {response.status_code}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 4: Health check
print("\n4. Testing /health endpoint...")
try:
    response = requests.get(f"{API_URL}/health")
    if response.status_code == 200:
        print("✓ Health check passed!")
        data = response.json()
        print(f"  Status: {data['status']}")
        print(f"  Model loaded: {data['model_loaded']}")
        print(f"  Batch manager: {data['batch_manager_active']}")
    else:
        print(f"✗ Failed: {response.status_code}")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "="*60)
print("Testing Complete!")
print("="*60)