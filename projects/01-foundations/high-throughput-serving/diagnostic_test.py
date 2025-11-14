import requests
import os

print("Diagnostic Test")
print("="*50)

# Check if file exists
image_path = "test-data/dog.jpg"
if not os.path.exists(image_path):
    print(f"ERROR: {image_path} does not exist!")
    print("Please run:")
    print('Invoke-WebRequest -Uri "https://github.com/pytorch/hub/raw/master/images/dog.jpg" -OutFile "test-data/dog.jpg"')
    exit(1)

print(f" Image file exists: {image_path}")
print(f"  Size: {os.path.getsize(image_path)} bytes")

# Test prediction
print("\nTesting prediction...")
try:
    with open(image_path, "rb") as f:
        files = {"file": ("dog.jpg", f, "image/jpeg")}
        response = requests.post("http://localhost:8000/predict", files=files)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"\nResponse Body:")
        print(response.text)
        
        if response.status_code == 200:
            import json
            result = response.json()
            print("\n SUCCESS!")
            print(json.dumps(result, indent=2))
        else:
            print("\n FAILED")
            
except Exception as e:
    print(f" Exception: {e}")
    import traceback
    traceback.print_exc()
