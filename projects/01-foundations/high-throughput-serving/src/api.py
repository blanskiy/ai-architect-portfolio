#!/usr/bin/env python3
"""FastAPI service for ResNet-50 model serving with Redis caching."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import Response
import torch
import torchvision.models as models
from torchvision import transforms
from PIL import Image
import io
import time
import uuid
from batch_manager import BatchManager
from logger_config import setup_logging, get_logger, PerformanceLogger
from metrics import (
    MetricsTracker, track_inference, track_batch, 
    update_queue_length, get_metrics, model_load_time
)
from cache_manager import CacheManager

setup_logging(log_level="INFO", json_logs=False)
logger = get_logger(__name__)

request_count = 0
success_count = 0
error_count = 0
total_latency = 0.0

app = FastAPI(
    title="ResNet-50 Model Serving API",
    description="High-throughput image classification service with caching",
    version="2.0.0"
)

model = None
preprocess = None
batch_manager = None
cache_manager = None

IMAGENET_CLASSES = {
    0: "tench", 1: "goldfish", 2: "great white shark",
    207: "golden retriever", 208: "Labrador retriever",
    258: "Samoyed", 259: "Pomeranian", 260: "Chow",
    281: "tabby cat", 282: "tiger cat", 283: "Persian cat",
}

@app.on_event("startup")
async def startup():
    global model, preprocess, batch_manager, cache_manager
    
    logger.info("="*60)
    logger.info("🚀 Starting ResNet-50 Serving API with Caching")
    logger.info("="*60)
    
    with PerformanceLogger(logger, "model_loading"):
        start_time = time.time()
        logger.info("Loading ResNet-50 model...")
        model = models.resnet50(pretrained=True)
        model.eval()
        
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
        logger.info("Model loaded successfully", extra={
            'model': 'ResNet-50',
            'load_time_seconds': round(elapsed, 2)
        })
    
    batch_manager = BatchManager(max_batch_size=8, max_wait_time=0.05)
    batch_manager.start(model)
    logger.info("Batch manager started")
    
    cache_manager = CacheManager(host="localhost", port=6379, ttl=3600, enabled=True)
    if cache_manager.is_healthy():
        logger.info("✅ Cache manager initialized and connected to Redis")
    else:
        logger.warning("⚠️  Cache manager initialized but Redis not available - caching disabled")
    
    logger.info("="*60)
    logger.info("✅ API Ready to Serve Requests")
    logger.info("="*60)

@app.on_event("shutdown")
async def shutdown():
    if batch_manager:
        batch_manager.stop()
    logger.info("Shutdown complete")

@app.get("/")
async def root():
    return {
        "service": "ResNet-50 Model Serving with Caching",
        "version": "2.0.0",
        "status": "running",
        "features": ["batching", "caching", "monitoring"],
        "endpoints": {
            "health": "/health",
            "predict": "/predict (POST)",
            "metrics": "/metrics",
            "prometheus": "/prometheus",
            "cache_stats": "/cache/stats",
            "cache_clear": "/cache/clear (POST)"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "batch_manager_active": batch_manager is not None,
        "cache_available": cache_manager.is_healthy() if cache_manager else False,
        "timestamp": time.time()
    }

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    global request_count, success_count, error_count, total_latency
    
    request_id = str(uuid.uuid4())[:8]
    request_count += 1
    
    with MetricsTracker("POST", "/predict"):
        if model is None:
            error_count += 1
            logger.error("Model not loaded", extra={'request_id': request_id})
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        try:
            overall_start = time.time()
            contents = await file.read()
            file_size = len(contents)
            
            # Check cache first
            cached_result = cache_manager.get(contents) if cache_manager else None
            
            if cached_result:
                # Cache HIT!
                cache_latency = (time.time() - overall_start) * 1000
                success_count += 1
                total_latency += cache_latency
                
                logger.info("✅ Cache HIT - returning cached result", extra={
                    'request_id': request_id,
                    'cache_latency_ms': round(cache_latency, 2)
                })
                
                cached_result['cache_hit'] = True
                cached_result['cache_latency_ms'] = round(cache_latency, 2)
                cached_result['request_id'] = request_id
                return cached_result
            
            # Cache MISS - run inference
            logger.info("❌ Cache MISS - running inference", extra={
                'request_id': request_id,
                'uploaded_filename': file.filename,
                'file_size_bytes': file_size
            })
            
            image = Image.open(io.BytesIO(contents)).convert('RGB')
            input_tensor = preprocess(image)
            
            if batch_manager:
                update_queue_length(len(batch_manager.queue))
            
            output, inference_time = await batch_manager.add_to_batch(input_tensor, request_id)
            track_inference("resnet50", inference_time)
            
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
            
            result = {
                "success": True,
                "request_id": request_id,
                "predictions": predictions,
                "latency_ms": round(total_latency_ms, 2),
                "inference_ms": round(inference_time * 1000, 2),
                "model": "ResNet-50",
                "batched": True,
                "cache_hit": False
            }
            
            # Cache the result
            if cache_manager:
                cache_manager.set(contents, result, ttl=3600)
                logger.info("💾 Cached result for future requests", extra={'request_id': request_id})
            
            logger.info("Request completed successfully", extra={
                'request_id': request_id,
                'top_prediction': predictions[0]['class_name'],
                'total_latency_ms': round(total_latency_ms, 2),
                'inference_ms': round(inference_time * 1000, 2)
            })
            
            return result
            
        except Exception as e:
            error_count += 1
            logger.error("Request failed", extra={
                'request_id': request_id,
                'error_type': type(e).__name__,
                'error_message': str(e)
            }, exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def metrics():
    avg_latency = total_latency / success_count if success_count > 0 else 0
    
    metrics_data = {
        "service": "resnet50-serving",
        "model_loaded": model is not None,
        "batch_manager_active": batch_manager is not None,
        "cache_available": cache_manager.is_healthy() if cache_manager else False,
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
    
    if cache_manager:
        metrics_data['cache'] = cache_manager.get_stats()
    
    return metrics_data

@app.get("/prometheus")
async def prometheus_metrics():
    metrics_data, content_type = get_metrics()
    return Response(content=metrics_data, media_type=content_type)

@app.get("/cache/stats")
async def cache_stats():
    if cache_manager:
        return cache_manager.get_stats()
    return {"enabled": False, "message": "Cache not initialized"}

@app.post("/cache/clear")
async def clear_cache():
    if cache_manager:
        success = cache_manager.clear_all()
        return {
            "success": success,
            "message": "Cache cleared" if success else "Cache clear failed"
        }
    return {"success": False, "message": "Cache not initialized"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
