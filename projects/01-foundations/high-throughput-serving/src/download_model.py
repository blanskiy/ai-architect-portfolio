#!/usr/bin/env python3
"""Download and test ResNet-50 model."""

import torch
import torchvision.models as models
from torchvision import transforms
from PIL import Image
import requests
from io import BytesIO

def download_model():
    """Download pre-trained ResNet-50."""
    print("Downloading ResNet-50...")
    model = models.resnet50(pretrained=True)
    model.eval()
    
    # Save model
    torch.save(model.state_dict(), "models/resnet50.pth")
    print("Model saved to models/resnet50.pth")
    
    return model

def test_model():
    """Test model with a sample image."""
    print("\nTesting model...")
    
    # Load model
    model = models.resnet50(pretrained=True)
    model.eval()
    
    # Download test image
    url = "https://github.com/pytorch/hub/raw/master/images/dog.jpg"
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))
    
    # Preprocess
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                           std=[0.229, 0.224, 0.225]),
    ])
    
    input_tensor = preprocess(img)
    input_batch = input_tensor.unsqueeze(0)
    
    # Inference
    with torch.no_grad():
        output = model(input_batch)
    
    # Get prediction
    _, predicted_idx = torch.max(output, 1)
    print(f"Predicted class index: {predicted_idx.item()}")
    print("Model works correctly!")
    
    return True

if __name__ == "__main__":
    download_model()
    test_model()