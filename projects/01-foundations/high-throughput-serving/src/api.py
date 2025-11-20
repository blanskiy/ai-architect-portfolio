#!/usr/bin/env python3
"""FastAPI service for ResNet-50 model serving."""
import sys
import os
# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, Response
import torch
import torchvision.models as models
from torchvision import transforms
from PIL import Image
import io
import time
import uuid
from batch_manager import BatchManager

# Monitoring imports
from logger_config import setup_logging, get_logger, PerformanceLogger
from metrics import (
    MetricsTracker, track_inference, track_batch, 
    update_queue_length, get_metrics, model_load_time
)

# Setup structured logging
setup_logging(log_level="INFO", json_logs=False)  # Set to True for production JSON logs
logger = get_logger(__name__)

# Global counters
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
batch_manager = None

# ImageNet class labels (subset for demo)
IMAGENET_CLASSES = {
    0: "tench", 1: "goldfish", 2: "great white shark",
    207: "golden retriever", 208: "Labrador retriever",
    258: "Samoyed", 259: "Pomeranian", 260: "Chow",
    281: "tabby cat", 282: "tiger cat", 283: "Persian cat",
}


@app.on_event("startup")
async def startup():
    """Load model and start batch manager on application startup."""
    global model, preprocess, batch_manager
    
    logger.info("="*60)
    logger.info("🚀 Starting ResNet-50 Serving API")
    logger.info("="*60)
    
    with PerformanceLogger(logger, "model_loading"):
        start_time = time.time()
        
        # Load model
        logger.info("Loading ResNet-50 model...")
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
        model_load_time.set(elapsed)
        
        logger.info(
            "Model loaded successfully",
            extra={
                'model': 'ResNet-50',
                'load_time_seconds': round(elapsed, 2),
                'parameters': '25.5M'
            }
        )
    
    # Initialize and start batch manager
    batch_manager = BatchManager(max_batch_size=8, max_wait_time=0.05)
    batch_manager.start(model)
    
    logger.info(
        "Batch manager started",
        extra={
            'max_batch_size': 8,
            'max_wait_time_ms': 50
        }
    )
    
    logger.info("="*60)
    logger.info("✅ API Ready to Serve Requests")
    logger.info("="*60)


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    if batch_manager:
        batch_manager.stop()
    logger.info("Shutdown complete")


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
            "metrics": "/metrics",
            "prometheus": "/prometheus",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "batch_manager_active": batch_manager is not None,
        "timestamp": time.time()
    }


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """Predict image class using batched inference with full monitoring."""
    
    global request_count, success_count, error_count, total_latency
    
    request_id = str(uuid.uuid4())[:8]
    request_count += 1
    
    # Start metrics tracking
    with MetricsTracker("POST", "/predict"):
        
        if model is None:
            error_count += 1
            logger.error(
                "Model not loaded",
                extra={'request_id': request_id}
            )
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        try:
            overall_start = time.time()
            
            # Read and preprocess image
            contents = await file.read()
            file_size = len(contents)
            
            logger.info(
                "Request received",
                extra={
                    'request_id': request_id,
                    'uploaded_filename': file.filename,
                    'file_size_bytes': file_size
                }
            )
            
            # Preprocess
            image = Image.open(io.BytesIO(contents)).convert('RGB')
            input_tensor = preprocess(image)
            
            # Update queue metrics
            if batch_manager:
                update_queue_length(len(batch_manager.queue))
            
            # Add to batch and wait for result
            logger.info(
                "Adding to batch queue",
                extra={'request_id': request_id}
            )
            
            output, inference_time = await batch_manager.add_to_batch(input_tensor, request_id)
            
            # Track inference
            track_inference("resnet50", inference_time)
            
            # Get predictions
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
            
            total_latency_ms = (time.time() - overall_start) * 1000
            success_count += 1
            total_latency += total_latency_ms
            
            logger.info(
                "Request completed successfully",
                extra={
                    'request_id': request_id,
                    'top_prediction': predictions[0]['class_name'],
                    'confidence': predictions[0]['confidence'],
                    'total_latency_ms': round(total_latency_ms, 2),
                    'inference_ms': round(inference_time * 1000, 2),
                    'file_size_bytes': file_size
                }
            )
            
            return {
                "success": True,
                "request_id": request_id,
                "predictions": predictions,
                "latency_ms": round(total_latency_ms, 2),
                "inference_ms": round(inference_time * 1000, 2),
                "model": "ResNet-50",
                "batched": True
            }
            
        except Exception as e:
            error_count += 1
            logger.error(
                "Request failed",
                extra={
                    'request_id': request_id,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                exc_info=True
            )
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint."""
    avg_latency = total_latency / success_count if success_count > 0 else 0
    
    return {
        "service": "resnet50-serving",
        "model_loaded": model is not None,
        "batch_manager_active": batch_manager is not None,
        "requests": {
            "total": request_count,
            "successful": success_count,
            "failed": error_count,
            "success_rate": round(success_count / request_count * 100, 2) if request_count > 0 else 0
        },
        "performance": {
            "avg_latency_ms": round(avg_latency, 2),
            "total_latency_ms": round(total_latency, 2)
        },
        "timestamp": time.time()
    }


@app.get("/prometheus")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus format for scraping.
    """
    metrics_data, content_type = get_metrics()
    return Response(content=metrics_data, media_type=content_type)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )
