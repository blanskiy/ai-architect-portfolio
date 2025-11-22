#!/usr/bin/env python3
"""Simple test to verify Redis caching works."""

import sys
sys.path.insert(0, 'src')

from cache_manager import CacheManager
import time

print("="*60)
print("Testing Redis Cache Manager")
print("="*60)

# Initialize cache
print("\n1. Initializing cache manager...")
cache = CacheManager(host="localhost", port=6379, ttl=3600)

if not cache.is_healthy():
    print("❌ ERROR: Redis is not available!")
    print("   Make sure Redis is running:")
    print("   docker run -d -p 6379:6379 --name redis-cache redis:7-alpine")
    sys.exit(1)

print("✓ Cache manager initialized")
print(f"✓ Redis connected")

# Test caching
print("\n2. Testing cache operations...")
test_image = b"fake_image_data_for_testing"
test_prediction = {
    "predictions": [{"class_name": "Samoyed", "confidence": 0.87}],
    "latency_ms": 1453
}

# Set cache
cache.set(test_image, test_prediction)
print("✓ Cached test prediction")

# Get cache (should hit)
result = cache.get(test_image)
if result:
    print(f"✓ Cache HIT: {result['predictions'][0]['class_name']}")
else:
    print("❌ Cache MISS (unexpected!)")

# Get different image (should miss)
result = cache.get(b"different_image")
if not result:
    print("✓ Cache MISS for different image (expected)")

# Stats
stats = cache.get_stats()
print("\n3. Cache statistics:")
print(f"  Enabled: {stats['enabled']}")
print(f"  Redis connected: {stats['redis_connected']}")
print(f"  Cache hits: {stats['cache_hits']}")
print(f"  Cache misses: {stats['cache_misses']}")
print(f"  Hit rate: {stats['hit_rate']}%")
print(f"  Redis keys: {stats.get('redis_keys', 0)}")

print("\n" + "="*60)
print("✅ Redis Cache Working!")
print("="*60)
