"""
ML Model Inference Server
FastAPI application for serving ML model predictions.

Features:
- Health checks (liveness and readiness)
- Graceful shutdown
- Request validation
- Metrics endpoint
- Structured logging
"""

import os
import time
import signal
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from model import ModelManager, PredictionInput, PredictionOutput


# ============================================================================
# Configuration
# ============================================================================

class Config:
    """Application configuration from environment variables."""
    MODEL_PATH: str = os.getenv("MODEL_PATH", "/app/models")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "model.joblib")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    PORT: int = int(os.getenv("PORT", "8080"))
    WORKERS: int = int(os.getenv("WORKERS", "4"))


# ============================================================================
# Logging Setup
# ============================================================================

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
)
logger = logging.getLogger(__name__)


# ============================================================================
# Application State
# ============================================================================

class AppState:
    """Global application state."""
    model_manager: Optional[ModelManager] = None
    is_ready: bool = False
    is_shutting_down: bool = False
    request_count: int = 0
    error_count: int = 0
    total_latency: float = 0.0


state = AppState()


# ============================================================================
# Lifecycle Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown logic.
    """
    # Startup
    logger.info("Starting ML inference server...")
    
    try:
        # Load model
        state.model_manager = ModelManager(
            model_path=Config.MODEL_PATH,
            model_name=Config.MODEL_NAME,
        )
        state.model_manager.load_model()
        state.is_ready = True
        logger.info("Model loaded successfully. Server is ready.")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        # Don't set is_ready = True, readiness probe will fail
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down ML inference server...")
    state.is_shutting_down = True
    
    # Give time for load balancer to stop sending traffic
    await asyncio.sleep(5)
    
    # Cleanup
    if state.model_manager:
        state.model_manager.unload_model()
    
    logger.info("Server shutdown complete.")


# Need asyncio for shutdown delay
import asyncio


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="ML Model Inference API",
    description="Production ML model serving endpoint",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    message: str


class ReadyResponse(BaseModel):
    """Readiness check response."""
    status: str
    model_loaded: bool
    message: str


class MetricsResponse(BaseModel):
    """Metrics endpoint response."""
    request_count: int
    error_count: int
    average_latency_ms: float
    model_name: str
    is_ready: bool


class PredictRequest(BaseModel):
    """Prediction request body."""
    features: list[float] = Field(..., min_length=1, description="Input features")
    
    class Config:
        json_schema_extra = {
            "example": {
                "features": [0.5, 0.3, 0.2, 0.8, 0.1]
            }
        }


class PredictResponse(BaseModel):
    """Prediction response body."""
    prediction: float | int | list
    probability: Optional[list[float]] = None
    model_version: str
    latency_ms: float


# ============================================================================
# Health Check Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Liveness probe endpoint.
    
    Returns 200 if the container is alive.
    Kubernetes uses this to detect deadlocks and restart the container.
    """
    if state.is_shutting_down:
        raise HTTPException(status_code=503, detail="Server is shutting down")
    
    return HealthResponse(
        status="healthy",
        message="Service is alive"
    )


@app.get("/ready", response_model=ReadyResponse, tags=["Health"])
async def readiness_check():
    """
    Readiness probe endpoint.
    
    Returns 200 only when the model is loaded and ready to serve.
    Kubernetes uses this to know when to send traffic.
    """
    if state.is_shutting_down:
        raise HTTPException(status_code=503, detail="Server is shutting down")
    
    if not state.is_ready:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded yet"
        )
    
    return ReadyResponse(
        status="ready",
        model_loaded=True,
        message="Model loaded and ready to serve"
    )


# ============================================================================
# Metrics Endpoint
# ============================================================================

@app.get("/metrics", response_model=MetricsResponse, tags=["Monitoring"])
async def metrics():
    """
    Metrics endpoint for monitoring.
    
    Returns request counts, error rates, and latency statistics.
    """
    avg_latency = (
        state.total_latency / state.request_count 
        if state.request_count > 0 else 0.0
    )
    
    return MetricsResponse(
        request_count=state.request_count,
        error_count=state.error_count,
        average_latency_ms=avg_latency,
        model_name=Config.MODEL_NAME,
        is_ready=state.is_ready,
    )


# ============================================================================
# Prediction Endpoint
# ============================================================================

@app.post("/predict", response_model=PredictResponse, tags=["Inference"])
async def predict(request: PredictRequest):
    """
    Make a prediction using the loaded model.
    
    Args:
        request: PredictRequest with input features
    
    Returns:
        PredictResponse with prediction and metadata
    """
    if not state.is_ready:
        raise HTTPException(
            status_code=503,
            detail="Model not ready"
        )
    
    start_time = time.time()
    
    try:
        # Create input
        model_input = PredictionInput(features=request.features)
        
        # Get prediction
        output = state.model_manager.predict(model_input)
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Update metrics
        state.request_count += 1
        state.total_latency += latency_ms
        
        return PredictResponse(
            prediction=output.prediction,
            probability=output.probability,
            model_version=output.model_version,
            latency_ms=round(latency_ms, 2),
        )
    
    except Exception as e:
        state.error_count += 1
        logger.error(f"Prediction error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )


@app.post("/predict/batch", tags=["Inference"])
async def predict_batch(requests: list[PredictRequest]):
    """
    Batch prediction endpoint.
    
    More efficient for multiple predictions.
    """
    if not state.is_ready:
        raise HTTPException(status_code=503, detail="Model not ready")
    
    start_time = time.time()
    
    try:
        results = []
        for req in requests:
            model_input = PredictionInput(features=req.features)
            output = state.model_manager.predict(model_input)
            results.append({
                "prediction": output.prediction,
                "probability": output.probability,
            })
        
        latency_ms = (time.time() - start_time) * 1000
        state.request_count += len(requests)
        state.total_latency += latency_ms
        
        return {
            "predictions": results,
            "count": len(results),
            "latency_ms": round(latency_ms, 2),
        }
    
    except Exception as e:
        state.error_count += 1
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/", tags=["Info"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "ML Model Inference API",
        "version": "1.0.0",
        "status": "ready" if state.is_ready else "loading",
        "endpoints": {
            "health": "/health",
            "readiness": "/ready",
            "metrics": "/metrics",
            "predict": "/predict",
            "docs": "/docs",
        }
    }


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=Config.PORT,
        workers=Config.WORKERS,
        log_level=Config.LOG_LEVEL.lower(),
    )
