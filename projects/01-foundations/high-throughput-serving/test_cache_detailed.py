#!/usr/bin/env python3
"""Detailed cache performance test."""

import requests
import time

API_URL = "http://localhost:8000"
IMAGE_PATH = "test-data/dog.jpg"

print("="*60)
print("Detailed Cache Performance Test")
print("="*60)

# Read image once
with open(IMAGE_PATH, 'rb') as f:
    image_data = f.read()

# Test 1: First request (cache miss)
print("\n1. First request (cache MISS)...")
start = time.time()
response = requests.post(f"{API_URL}/predict", files={'file': ('dog.jpg', image_data, 'image/jpeg')})
first_time = (time.time() - start) * 1000

result = response.json()
print(f"  Total latency: {first_time:.0f}ms")
print(f"  Inference time: {result.get('inference_ms', 'N/A')}ms")
print(f"  Cache hit: {result.get('cache_hit', False)}")
print(f"  Prediction: {result['predictions'][0]['class_name']}")

# Small delay
time.sleep(0.5)

# Test 2: Second request (should be cache hit)
print("\n2. Second request (cache HIT)...")
start = time.time()
response = requests.post(f"{API_URL}/predict", files={'file': ('dog.jpg', image_data, 'image/jpeg')})
second_time = (time.time() - start) * 1000

result = response.json()
print(f"  Total latency: {second_time:.0f}ms")
print(f"  Cache latency: {result.get('cache_latency_ms', 'N/A')}ms")
print(f"  Cache hit: {result.get('cache_hit', False)}")
print(f"  Prediction: {result['predictions'][0]['class_name']}")

# Test 3: Third request (should also be cache hit)
print("\n3. Third request (cache HIT)...")
start = time.time()
response = requests.post(f"{API_URL}/predict", files={'file': ('dog.jpg', image_data, 'image/jpeg')})
third_time = (time.time() - start) * 1000

result = response.json()
print(f"  Total latency: {third_time:.0f}ms")
print(f"  Cache latency: {result.get('cache_latency_ms', 'N/A')}ms")
print(f"  Cache hit: {result.get('cache_hit', False)}")

# Calculate improvement
if second_time > 0:
    improvement = first_time / second_time
    print(f"\n🚀 Cache Performance:")
    print(f"  First request:  {first_time:.0f}ms (cache miss)")
    print(f"  Second request: {second_time:.0f}ms (cache hit)")
    print(f"  Third request:  {third_time:.0f}ms (cache hit)")
    print(f"  Improvement:    {improvement:.1f}× faster!")
    
    if second_time > 100:
        print(f"\n⚠️  WARNING: Cache hits are slower than expected (>100ms)")
        print(f"   Expected: 10-50ms, Got: {second_time:.0f}ms")
        print(f"   This might be due to network overhead or file reading")

# Test 4: Cache stats
print("\n4. Cache statistics...")
response = requests.get(f"{API_URL}/cache/stats")
stats = response.json()
print(f"  Enabled: {stats['enabled']}")
print(f"  Redis connected: {stats['redis_connected']}")
print(f"  Cache hits: {stats['cache_hits']}")
print(f"  Cache misses: {stats['cache_misses']}")
print(f"  Hit rate: {stats['hit_rate']}%")
print(f"  Redis keys: {stats.get('redis_keys', 0)}")

print("\n" + "="*60)
print("Testing Complete!")
print("="*60)
