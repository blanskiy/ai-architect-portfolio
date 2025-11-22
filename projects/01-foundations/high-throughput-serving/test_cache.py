#!/usr/bin/env python3
"""Test caching performance."""

import requests
import time

API_URL = "http://localhost:8000"
IMAGE_PATH = "test-data/dog.jpg"

print("="*60)
print("Testing Cache Performance")
print("="*60)

# Test 1: First request (cache miss)
print("\n1. First request (cache MISS)...")
with open(IMAGE_PATH, 'rb') as f:
    files = {'file': ('dog.jpg', f, 'image/jpeg')}
    start = time.time()
    response = requests.post(f"{API_URL}/predict", files=files)
    first_time = (time.time() - start) * 1000

result = response.json()
print(f"  Latency: {first_time:.0f}ms")
print(f"  Cache hit: {result.get('cache_hit', False)}")
print(f"  Prediction: {result['predictions'][0]['class_name']}")

# Test 2: Second request (cache hit!)
print("\n2. Second request (cache HIT)...")
with open(IMAGE_PATH, 'rb') as f:
    files = {'file': ('dog.jpg', f, 'image/jpeg')}
    start = time.time()
    response = requests.post(f"{API_URL}/predict", files=files)
    second_time = (time.time() - start) * 1000

result = response.json()
print(f"  Latency: {second_time:.0f}ms")
print(f"  Cache hit: {result.get('cache_hit', False)}")
print(f"  Prediction: {result['predictions'][0]['class_name']}")

# Calculate improvement
improvement = first_time / second_time
print(f"\n🚀 Cache Performance:")
print(f"  First request:  {first_time:.0f}ms (cache miss)")
print(f"  Second request: {second_time:.0f}ms (cache hit)")
print(f"  Improvement:    {improvement:.1f}× faster!")

# Test 3: Cache stats
print("\n3. Cache statistics...")
response = requests.get(f"{API_URL}/cache/stats")
stats = response.json()
print(f"  Enabled: {stats['enabled']}")
print(f"  Cache hits: {stats['cache_hits']}")
print(f"  Cache misses: {stats['cache_misses']}")
print(f"  Hit rate: {stats['hit_rate']}%")
print(f"  Redis keys: {stats.get('redis_keys', 0)}")

print("\n" + "="*60)
print("Testing Complete!")
print("="*60)