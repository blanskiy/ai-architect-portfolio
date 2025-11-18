#!/usr/bin/env python3
"""FastAPI service for ResNet-50 model serving."""
import sys
import os
# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import torch
import torchvision.models as models
from torchvision import transforms
from PIL import Image
import io
import time
import logging
from batch_manager import BatchManager
import uuid



# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global counters - ADD THESE!
request_count = 0
success_count = 0
error_count = 0
total_latency = 0.0

# Initialize FastAPI
app = FastAPI(
    title="ResNet-50 Model Serving API",
    description="High-throughput image classification service",
    version="1.0.0"
)

# Global variables
model = None
preprocess = None

# Add after the global variables section
batch_manager = None

@app.on_event("startup")
async def load_model():
    """Load model and start batch manager on application startup."""
    global model, preprocess, batch_manager
    
    logger.info("Loading ResNet-50 model...")
    start_time = time.time()
    
    # Load model
    model = models.resnet50(pretrained=True)
    model.eval()
    
    # Setup preprocessing
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        ),
    ])
    
    elapsed = time.time() - start_time
    logger.info(f"Model loaded successfully in {elapsed:.2f} seconds")
    
    # Initialize and start batch manager
    batch_manager = BatchManager(max_batch_size=8, max_wait_time=0.05)
    batch_manager.start(model)
    logger.info("Batch manager started")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    if batch_manager:
        batch_manager.stop()
    logger.info("Shutdown complete")

# ImageNet class labels (subset for demo)
IMAGENET_CLASSES = {
    0: "tench", 1: "goldfish", 2: "great white shark",
    207: "golden retriever", 208: "Labrador retriever",
    258: "Samoyed", 259: "Pomeranian", 260: "Chow",
    281: "tabby cat", 282: "tiger cat", 283: "Persian cat",
    # Add more as needed
}

@app.on_event("startup")
async def load_model():
    """Load model on application startup."""
    global model, preprocess
    
    logger.info("Loading ResNet-50 model...")
    start_time = time.time()
    
    # Load model
    model = models.resnet50(pretrained=True)
    model.eval()
    
    # Setup preprocessing
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        ),
    ])
    
    elapsed = time.time() - start_time
    logger.info(f"Model loaded successfully in {elapsed:.2f} seconds")

@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "service": "ResNet-50 Model Serving",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "predict": "/predict (POST)",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "timestamp": time.time()
    }

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """Predict image class using batched inference."""
    
    global request_count, success_count, error_count, total_latency
    
    request_count += 1
    request_id = str(uuid.uuid4())[:8]  # Short unique ID
    
    if model is None:
        error_count += 1
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        start_time = time.time()
        
        # Read and preprocess image
        contents = await file.read()
        logger.info(f"[{request_id}] Received file: {file.filename}, size: {len(contents)} bytes")
        
        image = Image.open(io.BytesIO(contents)).convert('RGB')
        input_tensor = preprocess(image)
        
        # Add to batch and wait for result
        logger.info(f"[{request_id}] Adding to batch queue")
        output, inference_time = await batch_manager.add_to_batch(input_tensor, request_id)
        
        # Get top 5 predictions
        probabilities = torch.nn.functional.softmax(output, dim=0)
        top5_prob, top5_catid = torch.topk(probabilities, 5)
        
        predictions = []
        for i in range(5):
            class_id = top5_catid[i].item()
            class_name = IMAGENET_CLASSES.get(class_id, f"class_{class_id}")
            confidence = top5_prob[i].item()
            
            predictions.append({
                "rank": i + 1,
                "class_id": class_id,
                "class_name": class_name,
                "confidence": round(confidence, 4)
            })
        
        total_latency_ms = (time.time() - start_time) * 1000
        success_count += 1
        total_latency += total_latency_ms
        
        logger.info(f"[{request_id}] Success! Top: {predictions[0]['class_name']}, "
                   f"Total latency: {total_latency_ms:.2f}ms, "
                   f"Inference: {inference_time*1000:.2f}ms")
        
        return {
            "success": True,
            "predictions": predictions,
            "latency_ms": round(total_latency_ms, 2),
            "inference_ms": round(inference_time * 1000, 2),
            "request_id": request_id,
            "model": "ResNet-50",
            "batched": True
        }
        
    except Exception as e:
        error_count += 1
        logger.error(f"[{request_id}] Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint (placeholder for Prometheus)."""
    return {
        "service": "resnet50-serving",
        "model_loaded": model is not None,
        "uptime_seconds": time.time()
        # TODO: Add request counters, latency histograms
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )