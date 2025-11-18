#!/usr/bin/env python3
"""Load testing script to measure batching performance."""

import requests
import time
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import statistics
import os

# Get correct path to test image
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
IMAGE_PATH = os.path.join(PROJECT_ROOT, "test-data", "dog.jpg")

API_URL = "http://localhost:8000/predict"


def send_request_sync(request_id):
    """Send a single synchronous request."""
    start = time.time()
    
    if not os.path.exists(IMAGE_PATH):
        return {
            'request_id': request_id,
            'status': 'failed',
            'error': f'Image not found at {IMAGE_PATH}'
        }
    
    with open(IMAGE_PATH, 'rb') as f:
        files = {'file': ('dog.jpg', f, 'image/jpeg')}
        response = requests.post(API_URL, files=files)
    
    latency = (time.time() - start) * 1000
    
    if response.status_code == 200:
        data = response.json()
        return {
            'request_id': request_id,
            'status': 'success',
            'latency_ms': latency,
            'inference_ms': data.get('inference_ms', 0),
            'top_prediction': data['predictions'][0]['class_name']
        }
    else:
        return {
            'request_id': request_id,
            'status': 'failed',
            'latency_ms': latency,
            'error': response.text
        }


async def send_request_async(session, request_id):
    """Send a single async request."""
    start = time.time()
    
    with open(IMAGE_PATH, 'rb') as f:
        data = aiohttp.FormData()
        data.add_field('file', f, filename='dog.jpg', content_type='image/jpeg')
        
        async with session.post(API_URL, data=data) as response:
            latency = (time.time() - start) * 1000
            
            if response.status == 200:
                result = await response.json()
                return {
                    'request_id': request_id,
                    'status': 'success',
                    'latency_ms': latency,
                    'inference_ms': result.get('inference_ms', 0),
                    'top_prediction': result['predictions'][0]['class_name']
                }
            else:
                return {
                    'request_id': request_id,
                    'status': 'failed',
                    'latency_ms': latency
                }


def test_sequential(num_requests=5):
    """Test sequential requests (no concurrency)."""
    print(f"\n{'='*60}")
    print(f"TEST 1: Sequential Requests (Baseline)")
    print(f"{'='*60}")
    print(f"Sending {num_requests} requests sequentially...")
    
    start_time = time.time()
    results = []
    
    for i in range(num_requests):
        result = send_request_sync(i)
        results.append(result)
        if result['status'] == 'success':
            print(f"  Request {i+1}/{num_requests}: {result['latency_ms']:.0f}ms - {result['top_prediction']}")
        else:
            print(f"  Request {i+1}/{num_requests}: FAILED - {result.get('error', 'Unknown')}")
    
    total_time = time.time() - start_time
    success_results = [r for r in results if r['status'] == 'success']
    
    if success_results:
        latencies = [r['latency_ms'] for r in success_results]
        print(f"\n📊 Results:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Successful: {len(success_results)}/{num_requests}")
        print(f"  Throughput: {len(success_results)/total_time:.2f} RPS")
        print(f"  Avg latency: {statistics.mean(latencies):.0f}ms")
        print(f"  Min latency: {min(latencies):.0f}ms")
        print(f"  Max latency: {max(latencies):.0f}ms")
    else:
        print("\n❌ No successful requests!")
    
    return results


async def test_concurrent_async(num_requests=10):
    """Test concurrent requests with asyncio."""
    print(f"\n{'='*60}")
    print(f"TEST 2: Concurrent Requests (With Batching)")
    print(f"{'='*60}")
    print(f"Sending {num_requests} requests concurrently...")
    
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        tasks = [send_request_async(session, i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    success_results = [r for r in results if r['status'] == 'success']
    
    if success_results:
        latencies = [r['latency_ms'] for r in success_results]
        inference_times = [r['inference_ms'] for r in success_results]
        
        for i, result in enumerate(results):
            if result['status'] == 'success':
                print(f"  Request {i+1}/{num_requests}: {result['latency_ms']:.0f}ms "
                      f"(inference: {result.get('inference_ms', 0):.0f}ms) - {result['top_prediction']}")
        
        print(f"\n📊 Results:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Successful: {len(success_results)}/{num_requests}")
        print(f"  Throughput: {len(success_results)/total_time:.2f} RPS")
        print(f"  Avg latency: {statistics.mean(latencies):.0f}ms")
        print(f"  Avg inference: {statistics.mean(inference_times):.0f}ms")
        print(f"  Min latency: {min(latencies):.0f}ms")
        print(f"  Max latency: {max(latencies):.0f}ms")
        
        # Calculate improvement
        baseline_rps = 1000 / statistics.mean(latencies)
        actual_rps = len(success_results) / total_time
        improvement = actual_rps / baseline_rps
        print(f"\n🚀 Throughput improvement: {improvement:.1f}× faster than sequential!")
    else:
        print("\n❌ No successful requests!")
    
    return results


def test_concurrent_threads(num_requests=10, num_workers=4):
    """Test concurrent requests with thread pool."""
    print(f"\n{'='*60}")
    print(f"TEST 3: Concurrent with ThreadPool ({num_workers} workers)")
    print(f"{'='*60}")
    print(f"Sending {num_requests} requests with {num_workers} threads...")
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(send_request_sync, range(num_requests)))
    
    total_time = time.time() - start_time
    success_results = [r for r in results if r['status'] == 'success']
    
    if success_results:
        latencies = [r['latency_ms'] for r in success_results]
        
        for i, result in enumerate(results):
            if result['status'] == 'success':
                print(f"  Request {i+1}/{num_requests}: {result['latency_ms']:.0f}ms - {result['top_prediction']}")
        
        print(f"\n📊 Results:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Successful: {len(success_results)}/{num_requests}")
        print(f"  Throughput: {len(success_results)/total_time:.2f} RPS")
        print(f"  Avg latency: {statistics.mean(latencies):.0f}ms")
        print(f"  Min latency: {min(latencies):.0f}ms")
        print(f"  Max latency: {max(latencies):.0f}ms")
    else:
        print("\n❌ No successful requests!")
    
    return results


def main():
    """Run all tests."""
    print("🚀 Starting Load Tests for Batching Performance")
    print("="*60)
    print(f"Image path: {IMAGE_PATH}")
    print(f"Image exists: {os.path.exists(IMAGE_PATH)}")
    print(f"API URL: {API_URL}")
    print("="*60)
    
    if not os.path.exists(IMAGE_PATH):
        print(f"\n❌ ERROR: Test image not found at {IMAGE_PATH}")
        print("Please ensure dog.jpg exists in test-data/ folder")
        return
    
    # Test API is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code != 200:
            print("\n❌ ERROR: API is not responding correctly")
            print("Make sure the API is running: python src\\api.py")
            return
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to API at http://localhost:8000")
        print("Make sure the API is running: python src\\api.py")
        return
    except requests.exceptions.Timeout:
        print("\n❌ ERROR: API connection timeout")
        return
    
    print("✅ API is running and healthy\n")
    
    # Test 1: Sequential (baseline)
    test_sequential(num_requests=5)
    
    time.sleep(2)  # Brief pause
    
    # Test 2: Concurrent with asyncio (batching)
    asyncio.run(test_concurrent_async(num_requests=10))
    
    time.sleep(2)  # Brief pause
    
    # Test 3: Concurrent with threads
    test_concurrent_threads(num_requests=10, num_workers=5)
    
    print(f"\n{'='*60}")
    print("✅ All tests complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    print("📦 Required package: aiohttp")
    print("Install with: pip install aiohttp\n")
    main()