import requests
import json

print("="*50)
print("Testing ResNet-50 Serving API")
print("="*50)

# Test 1: Root
print("\n1. Testing root endpoint...")
try:
    response = requests.get("http://localhost:8000/")
    print(" Status:", response.status_code)
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(" Error:", e)

# Test 2: Health
print("\n2. Testing health endpoint...")
try:
    response = requests.get("http://localhost:8000/health")
    print(" Status:", response.status_code)
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(" Error:", e)

# Test 3: Prediction
print("\n3. Testing prediction endpoint...")
try:
    with open("test-data/dog.jpg", "rb") as f:
        files = {"file": f}
        response = requests.post("http://localhost:8000/predict", files=files)
        print(" Status:", response.status_code)
        result = response.json()
        print(json.dumps(result, indent=2))
        print(f"\n Top prediction: {result['predictions'][0]['class_name']} ({result['predictions'][0]['confidence']*100:.1f}%)")
        print(f" Latency: {result['latency_ms']} ms")
except Exception as e:
    print(" Error:", e)

# Test 4: Metrics
print("\n4. Testing metrics endpoint...")
try:
    response = requests.get("http://localhost:8000/metrics")
    print(" Status:", response.status_code)
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(" Error:", e)

print("\n" + "="*50)
print("Testing Complete!")
print("="*50)
