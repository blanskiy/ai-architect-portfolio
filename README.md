# 🚀 AI Architect Portfolio: High-Throughput ML Serving System

[![CI/CD Pipeline](https://github.com/blanskiy/ai-architect-portfolio/actions/workflows/ci.yaml/badge.svg)](https://github.com/blanskiy/ai-architect-portfolio/actions)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/kubernetes-deployed-326CE5.svg)](https://kubernetes.io/)

## 🌐 Live Production API

**Azure Cloud Deployment:**
```
https://resnet-api.mangobay-4d613d45.westus2.azurecontainerapps.io
```

### Quick Test
```bash
# Health check
curl https://resnet-api.mangobay-4d613d45.westus2.azurecontainerapps.io/health

# Image classification
curl -X POST "https://resnet-api.mangobay-4d613d45.westus2.azurecontainerapps.io/predict" \
  -F "file=@your-image.jpg"
```

---

## 📊 Project Overview

A **production-grade ML inference system** built from scratch over 4 weeks, demonstrating enterprise ML engineering skills:

| Component | Technology | Achievement |
|-----------|------------|-------------|
| **Model** | ResNet-50 (ImageNet) | 1000-class classification |
| **Framework** | PyTorch → ONNX | 1.89× speedup |
| **API** | FastAPI + Async | 7 RPS throughput |
| **Caching** | Redis | 80% hit rate |
| **Container** | Docker | Production-ready |
| **Orchestration** | Kubernetes | Auto-scaling 1-10 pods |
| **Cloud** | Azure Container Apps | Live deployment |
| **CI/CD** | GitHub Actions | Automated testing |
| **MLOps** | MLflow | Model versioning |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PRODUCTION ML SERVING SYSTEM                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Client Request                                                            │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │              AZURE CONTAINER APPS (West US 2)                        │  │
│   │        https://resnet-api.mangobay-4d613d45.westus2...              │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    KUBERNETES CLUSTER                                │  │
│   │   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐            │  │
│   │   │  Pod 1  │   │  Pod 2  │   │  Pod 3  │   │  ...    │            │  │
│   │   │ FastAPI │   │ FastAPI │   │ FastAPI │   │         │            │  │
│   │   └─────────┘   └─────────┘   └─────────┘   └─────────┘            │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    FASTAPI APPLICATION                               │  │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │  │
│   │   │   Request   │  │   Redis     │  │   Batch     │                │  │
│   │   │   Handler   │──│   Cache     │──│   Manager   │                │  │
│   │   │   (Async)   │  │  (80% hit)  │  │  (Dynamic)  │                │  │
│   │   └─────────────┘  └─────────────┘  └─────────────┘                │  │
│   │                           │                                          │  │
│   │                           ▼                                          │  │
│   │                    ┌─────────────┐                                   │  │
│   │                    │ ONNX Runtime│                                   │  │
│   │                    │ (1.89x fast)│                                   │  │
│   │                    └─────────────┘                                   │  │
│   │                           │                                          │  │
│   │                           ▼                                          │  │
│   │                    ┌─────────────┐                                   │  │
│   │                    │  ResNet-50  │                                   │  │
│   │                    │ (ImageNet)  │                                   │  │
│   │                    └─────────────┘                                   │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Performance Metrics

| Metric | Value | Details |
|--------|-------|---------|
| **ONNX Speedup** | 1.89× | PyTorch: 697ms → ONNX: 368ms |
| **Cache Hit Rate** | 80% | Content-based hashing |
| **Throughput** | 7 RPS | With batching enabled |
| **P50 Latency** | ~100ms | Typical inference |
| **P99 Latency** | ~200ms | Worst case |
| **Model Size** | 97.79 MB | FP32 baseline |
| **Quantized Size** | 48.90 MB | FP16 (50% reduction) |
| **Distributed Speedup** | 9.3× | 4 workers vs 1 worker |

---

## 📁 Project Structure

```
high-throughput-serving/
├── src/
│   ├── api.py                    # FastAPI application
│   ├── batch_manager.py          # Dynamic batching
│   ├── cache_manager.py          # Redis caching
│   ├── download_model.py         # Model downloading
│   ├── metrics.py                # Prometheus metrics
│   ├── ab_testing.py             # A/B testing & canary
│   ├── monitoring_advanced.py    # SLOs & alerting
│   ├── model_optimization.py     # Quantization
│   ├── distributed_inference.py  # Worker pools
│   ├── feature_store.py          # Feature management
│   └── ml_pipeline.py            # Pipeline orchestration
├── k8s/
│   ├── deployment.yaml           # K8s deployment
│   ├── service.yaml              # K8s service
│   └── canary-deployment.yaml    # Canary releases
├── docker/
│   └── Dockerfile                # Container definition
├── tests/
│   ├── test_api.py               # Integration tests
│   └── test_unit.py              # Unit tests
├── .github/
│   └── workflows/
│       └── ci.yaml               # CI/CD pipeline
├── models/                       # Model artifacts
├── mlruns/                       # MLflow tracking
├── requirements.txt              # Python dependencies
├── requirements-ci.txt           # CI dependencies
└── README.md                     # This file
```

---

## 🛠️ Technologies Used

### ML/AI
- **PyTorch** - Deep learning framework
- **ONNX Runtime** - Optimized inference
- **ResNet-50** - Image classification model
- **MLflow** - Model versioning & registry

### Backend
- **FastAPI** - High-performance async API
- **Redis** - Distributed caching
- **Prometheus** - Metrics collection
- **Uvicorn** - ASGI server

### DevOps
- **Docker** - Containerization
- **Kubernetes** - Container orchestration
- **GitHub Actions** - CI/CD automation
- **Azure Container Apps** - Cloud deployment

### Monitoring
- **SLOs/SLIs** - Service level objectives
- **Custom Alerting** - Threshold-based alerts
- **Performance Dashboards** - Real-time metrics

---

## 🚀 Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/blanskiy/ai-architect-portfolio.git
cd ai-architect-portfolio/projects/01-foundations/high-throughput-serving

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Download model
python src/download_model.py

# Run API
uvicorn src.api:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
# Build image
docker build -t resnet-serving:latest .

# Run container
docker run -p 8000:8000 resnet-serving:latest
```

### Kubernetes

```bash
# Deploy to cluster
kubectl apply -f k8s/deployment.yaml -n ml-serving
kubectl apply -f k8s/service.yaml -n ml-serving

# Check status
kubectl get pods -n ml-serving
```

---

## 📖 API Documentation

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/predict` | POST | Image classification |
| `/metrics` | GET | Prometheus metrics |
| `/docs` | GET | Swagger UI |

### Example Request

```bash
curl -X POST "http://localhost:8000/predict" \
  -F "file=@dog.jpg"
```

### Example Response

```json
{
  "success": true,
  "request_id": "c10e5fc9",
  "predictions": [
    {"rank": 1, "class_id": 258, "class_name": "Samoyed", "confidence": 0.8733},
    {"rank": 2, "class_id": 259, "class_name": "Pomeranian", "confidence": 0.0303}
  ],
  "latency_ms": 172.19,
  "inference_ms": 128.96,
  "model": "ResNet-50",
  "batched": true
}
```

---

## 📚 4-Week Learning Journey

### Week 1: ML Foundations
- ✅ ResNet-50 model integration
- ✅ FastAPI REST API
- ✅ Dynamic batching (up to 32 images)
- ✅ Redis caching (80% hit rate)
- ✅ Prometheus monitoring

### Week 2: Production Ready
- ✅ Docker containerization
- ✅ Performance optimization
- ✅ ONNX Runtime (1.89× speedup)
- ✅ Azure cloud deployment
- ✅ Live production URL

### Week 3: MLOps & Kubernetes
- ✅ Kubernetes deployment
- ✅ CI/CD with GitHub Actions
- ✅ MLflow model versioning
- ✅ A/B testing & canary deployments
- ✅ SLOs, SLIs, and alerting

### Week 4: Advanced Systems
- ✅ Model quantization (50% size reduction)
- ✅ Distributed inference (9.3× throughput)
- ✅ Feature store implementation
- ✅ ML pipeline orchestration
- ✅ Portfolio completion

---

## 🎯 Key Achievements

1. **Production Deployment** - Live API on Azure with auto-scaling
2. **Performance Optimization** - 1.89× speedup with ONNX
3. **Distributed Systems** - 9.3× throughput with 4 workers
4. **MLOps Pipeline** - End-to-end automation with CI/CD
5. **Enterprise Patterns** - Feature stores, A/B testing, SLOs

---

## 👤 Author

**Bruce Lanskiy**
- GitHub: [@blanskiy](https://github.com/blanskiy)
- Target Companies: Apple, Tesla, Microsoft

---

## 📄 License

This project is for educational and portfolio purposes.
