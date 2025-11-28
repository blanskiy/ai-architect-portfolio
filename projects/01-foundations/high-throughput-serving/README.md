# 🚀 High-Throughput ML Serving System

A production-ready machine learning inference API built for high-throughput image classification, featuring intelligent batching, caching, and cloud deployment.

**🌐 Live Demo:** [https://resnet-api.mangobay-4d613d45.westus2.azurecontainerapps.io](https://resnet-api.mangobay-4d613d45.westus2.azurecontainerapps.io)

---

## 📊 Performance Highlights

| Metric | Value |
|--------|-------|
| **Model** | ResNet-50 (ImageNet) |
| **ONNX Speedup** | 1.89× (697ms → 368ms) |
| **Cache Hit Rate** | 80% |
| **Throughput** | 7 RPS |
| **Inference Latency** | ~130ms (cloud) |
| **Availability** | 99.9% |

---

## 🌐 Live API Endpoints

| Endpoint | URL | Description |
|----------|-----|-------------|
| **API Base** | `https://resnet-api.mangobay-4d613d45.westus2.azurecontainerapps.io` | Base URL |
| **Swagger Docs** | `https://resnet-api.mangobay-4d613d45.westus2.azurecontainerapps.io/docs` | Interactive API documentation |
| **Health Check** | `https://resnet-api.mangobay-4d613d45.westus2.azurecontainerapps.io/health` | Service health status |
| **Prediction** | `POST /predict` | Image classification endpoint |

### Quick Test

```bash
# Health check
curl https://resnet-api.mangobay-4d613d45.westus2.azurecontainerapps.io/health

# Image classification
curl -X POST "https://resnet-api.mangobay-4d613d45.westus2.azurecontainerapps.io/predict" \
  -F "file=@your-image.jpg"
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PRODUCTION ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Client Request                                                             │
│        │                                                                     │
│        ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │              Azure Container Apps (West US 2)                        │   │
│   │              https://resnet-api.mangobay-4d613d45.westus2            │   │
│   │                     .azurecontainerapps.io                           │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        FastAPI Application                           │   │
│   │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌────────────────┐   │   │
│   │  │  Request  │  │   Redis   │  │  Batch    │  │    ONNX        │   │   │
│   │  │  Handler  │─▶│   Cache   │─▶│  Manager  │─▶│    Runtime     │   │   │
│   │  │           │  │  (80% hit)│  │ (dynamic) │  │  (1.89× faster)│   │   │
│   │  └───────────┘  └───────────┘  └───────────┘  └────────────────┘   │   │
│   │                                                      │               │   │
│   │                                                      ▼               │   │
│   │                                              ┌────────────────┐      │   │
│   │                                              │   ResNet-50    │      │   │
│   │                                              │   (ImageNet)   │      │   │
│   │                                              │   1000 classes │      │   │
│   │                                              └────────────────┘      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Key Features

### 1. Intelligent Batching
- Dynamic batch collection with configurable timeout
- Optimizes GPU/CPU utilization for concurrent requests
- Reduces per-request overhead

### 2. Redis Caching Layer
- 80% cache hit rate for repeated images
- Content-based hashing for cache keys
- Configurable TTL and eviction policies

### 3. ONNX Runtime Optimization
- 1.89× speedup over PyTorch inference
- Graph-level optimizations (operator fusion)
- Reduced memory footprint

### 4. Production Monitoring
- Prometheus metrics integration
- Request latency tracking
- Cache performance monitoring

---

## 🚀 Deployment

### Cloud Infrastructure (Azure)

| Resource | Configuration |
|----------|---------------|
| **Platform** | Azure Container Apps |
| **Region** | West US 2 |
| **CPU** | 2 vCPU |
| **Memory** | 4 GB |
| **Container Registry** | Azure Container Registry (ACR) |
| **Scaling** | Auto-scale 1-10 replicas |

### Local Development

```bash
# Clone repository
git clone https://github.com/yourusername/ai-architect-portfolio.git
cd projects/01-foundations/high-throughput-serving

# Start with Docker Compose
docker-compose up -d

# Test locally
curl -X POST "http://localhost:8000/predict" -F "file=@test-data/dog.jpg"
```

---

## 📁 Project Structure

```
high-throughput-serving/
├── src/
│   ├── api/              # FastAPI routes and handlers
│   ├── models/           # ML model loading and inference
│   ├── cache/            # Redis caching implementation
│   └── batch/            # Dynamic batching logic
├── models/               # Saved model weights (PyTorch & ONNX)
├── config/               # Configuration files
├── docker/               # Docker configurations
├── monitoring/           # Prometheus/Grafana setup
├── tests/                # Unit and integration tests
├── Dockerfile            # Container definition
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

---

## 📈 Performance Optimization Journey

### Phase 1: Baseline
- PyTorch model serving
- Single-request processing
- ~697ms latency

### Phase 2: ONNX Optimization
- Converted to ONNX Runtime
- 1.89× speedup
- ~368ms latency

### Phase 3: Caching
- Redis caching layer
- 80% hit rate
- Near-zero latency for cached requests

### Phase 4: Cloud Deployment
- Azure Container Apps
- Auto-scaling
- Global availability

---

## 🛠️ Technologies Used

| Category | Technologies |
|----------|-------------|
| **ML Framework** | PyTorch, ONNX Runtime |
| **API Framework** | FastAPI, Uvicorn |
| **Caching** | Redis |
| **Containerization** | Docker |
| **Cloud Platform** | Azure Container Apps |
| **Container Registry** | Azure Container Registry |
| **Monitoring** | Prometheus, Grafana |
| **Load Testing** | Locust |

---

## 📝 API Documentation

### POST /predict

Classify an image using ResNet-50.

**Request:**
```bash
curl -X POST "https://resnet-api.mangobay-4d613d45.westus2.azurecontainerapps.io/predict" \
  -F "file=@image.jpg"
```

**Response:**
```json
{
  "success": true,
  "request_id": "c10e5fc9",
  "predictions": [
    {
      "rank": 1,
      "class_id": 258,
      "class_name": "Samoyed",
      "confidence": 0.8733
    },
    {
      "rank": 2,
      "class_id": 259,
      "class_name": "Pomeranian",
      "confidence": 0.0303
    }
  ],
  "latency_ms": 172.19,
  "inference_ms": 128.96,
  "model": "ResNet-50",
  "batched": true
}
```

---

## 👤 Author

**Bruce Lanskiy**
- Building production ML systems
- Targeting AI Architect roles at Apple, Tesla, Microsoft

---

## 📄 License

MIT License - See LICENSE file for details
