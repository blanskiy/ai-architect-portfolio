# 🚀 AI Architect Portfolio

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Azure](https://img.shields.io/badge/Azure-AI%20%7C%20Databricks-0078D4.svg)](https://azure.microsoft.com/)
[![MLOps](https://img.shields.io/badge/MLOps-Production%20Ready-green.svg)](https://mlops.community/)

**End-to-end AI/ML/LLM architecture portfolio demonstrating enterprise-grade systems on Azure + Databricks**

---

## 📊 Portfolio Overview

| Month | Focus Area | Projects | Lines of Code |
|-------|------------|----------|---------------|
| **Month 1** | ML Systems & Serving | Production API, ONNX, Caching | ~3,000 |
| **Month 2** | LLMs & Data Engineering | Transformers, RAG, Azure AI Foundry | ~4,500 |
| **Month 3** | MLOps & Production | CI/CD, Monitoring, A/B Testing, K8s | ~4,800 |
| **Month 4** | Advanced ML Systems | Feature Store, Model Optimization | ~6,800+ |
| **Total** | | **15+ Projects** | **~19,000+** |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ENTERPRISE AI ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   DATA LAYER                          AI/ML LAYER                          │
│   ┌─────────────────┐                ┌─────────────────┐                   │
│   │ Databricks      │                │ Azure AI Foundry│                   │
│   │ Unity Catalog   │◄──────────────►│ GPT-4 / OpenAI  │                   │
│   │ Delta Lake      │                │ Embeddings      │                   │
│   └─────────────────┘                └─────────────────┘                   │
│          │                                   │                              │
│          ▼                                   ▼                              │
│   ┌─────────────────┐                ┌─────────────────┐                   │
│   │ ADLS Gen2       │                │ LanceDB         │                   │
│   │ Lakehouse       │                │ Vector Store    │                   │
│   └─────────────────┘                └─────────────────┘                   │
│                                                                             │
│   MLOPS LAYER                        SERVING LAYER                         │
│   ┌─────────────────┐                ┌─────────────────┐                   │
│   │ MLflow          │                │ FastAPI         │                   │
│   │ Feast           │                │ ONNX Runtime    │                   │
│   │ GitHub Actions  │                │ Redis Cache     │                   │
│   └─────────────────┘                └─────────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
ai-architect-portfolio/
├── projects/
│   ├── 03-azure-ai-foundry/           # Azure AI Foundry Labs
│   │   ├── lab5-evaluation/           # RAG Evaluation with LLM-as-Judge
│   │   ├── lab7-mcp/                  # MCP Server Integration
│   │   └── lab8-prompt-engineering/   # Prompt Engineering Patterns
│   │
│   ├── 03-mlops-production/           # MLOps Projects
│   │   ├── project1-cicd-pipeline/    # GitHub Actions ML Pipeline
│   │   ├── project2-model-monitoring/ # Drift Detection & Alerts
│   │   ├── project3-ab-testing/       # Statistical A/B Testing
│   │   └── project4-k8s-deployment/   # Kubernetes + Helm
│   │
│   ├── 03-nlp-transformers/           # NLP & Transformers
│   │   ├── attention-mechanism/       # Self-Attention Implementation
│   │   └── rag-lancedb/               # Hybrid RAG with LanceDB
│   │
│   ├── 04-advanced-ml-systems/        # Advanced ML
│   │   ├── project1-feature-store/    # Feast Feature Store
│   │   └── project2-model-optimization/ # ONNX, Quantization, Pruning
│   │
│   └── 04-databricks-enterprise/      # Databricks Integration
│       └── stihl-inventory-ai/        # STIHL Sales Analytics
│
├── architecture-diagrams/             # System Design Diagrams
├── certifications/                    # Certification Materials
├── notes/                             # Learning Notes
└── roadmap/                           # Career Roadmap
```

---

## 🎯 Key Projects

### 1. Feature Store with Feast
**Location:** `projects/04-advanced-ml-systems/project1-feature-store/`

Production feature store implementation with offline/online serving, point-in-time joins, and Redis online store.

| Component | Technology |
|-----------|------------|
| Feature Store | Feast |
| Offline Store | Parquet/Delta |
| Online Store | Redis |
| Registry | SQLite → Production DB |

### 2. Model Optimization Pipeline
**Location:** `projects/04-advanced-ml-systems/project2-model-optimization/`

Complete model optimization toolkit for production deployment.

| Technique | Speedup | Size Reduction |
|-----------|---------|----------------|
| ONNX Conversion | 2-3x | Same |
| INT8 Quantization | 2-4x | 4x |
| FP16 Quantization | 1.5-2x | 2x |
| Structured Pruning | 2-3x | 2x |

### 3. MLOps CI/CD Pipeline
**Location:** `projects/03-mlops-production/project1-cicd-pipeline/`

GitHub Actions workflow for ML with experiment tracking, model validation, and blue-green deployment.

```yaml
Stages: Lint → Test → Train → Validate → Deploy (Blue/Green)
```

### 4. RAG with LanceDB
**Location:** `projects/03-nlp-transformers/rag-lancedb/`

Hybrid RAG system with vector + full-text search on Azure ADLS Gen2.

| Component | Technology |
|-----------|------------|
| Vector Store | LanceDB |
| Embeddings | Azure OpenAI |
| Storage | ADLS Gen2 |
| Search | Hybrid (Vector + BM25) |

### 5. Azure AI Foundry Integration
**Location:** `projects/03-azure-ai-foundry/`

Enterprise AI labs including RAG evaluation, MCP servers, and prompt engineering.

---

## 🛠️ Technologies

### AI/ML
- **Frameworks:** PyTorch, ONNX Runtime, Hugging Face Transformers
- **Feature Store:** Feast
- **Experiment Tracking:** MLflow
- **Vector DB:** LanceDB

### Cloud & Data
- **Azure:** AI Foundry, ADLS Gen2, Container Apps
- **Databricks:** Unity Catalog, Delta Lake, Workflows
- **Storage:** Delta Lake, Parquet, Lance

### MLOps
- **CI/CD:** GitHub Actions
- **Containers:** Docker, Kubernetes, Helm
- **Monitoring:** Prometheus, Custom Drift Detection
- **Caching:** Redis

### APIs & Serving
- **Framework:** FastAPI
- **Optimization:** ONNX, Quantization
- **Deployment:** Azure Container Apps, Kubernetes

---

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/blanskiy/ai-architect-portfolio.git
cd ai-architect-portfolio

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Explore projects
cd projects/04-advanced-ml-systems/project1-feature-store
```

---

## 📚 Learning Journey

### Month 1: ML Foundations
- ✅ ResNet-50 inference API
- ✅ ONNX optimization (1.89x speedup)
- ✅ Redis caching (80% hit rate)
- ✅ Docker containerization

### Month 2: LLMs & Data Engineering
- ✅ Transformer architecture (self-attention)
- ✅ RAG with LanceDB + Azure OpenAI
- ✅ Azure AI Foundry labs (evaluation, agents)
- ✅ Databricks Unity Catalog integration

### Month 3: MLOps
- ✅ CI/CD pipeline with GitHub Actions
- ✅ Model monitoring & drift detection
- ✅ A/B testing framework
- ✅ Kubernetes deployment with Helm

### Month 4: Advanced Systems
- ✅ Feature Store with Feast
- ✅ Model Optimization (ONNX, Quantization, Pruning)
- 🔄 Vector Database (Advanced Patterns)
- ⏳ Caching & Serving Optimization

---

## 🎯 Target Roles

| Company | Role | Focus Areas |
|---------|------|-------------|
| Microsoft | AI Platform Architect | Azure AI, MLOps, Enterprise Scale |
| Apple | ML Infrastructure | Model Optimization, Feature Stores |
| Tesla | AI Systems Engineer | Real-time ML, Edge Deployment |

---

## 📈 Key Metrics

| Metric | Achievement |
|--------|-------------|
| Total Lines of Code | 19,000+ |
| Projects Completed | 15+ |
| Azure Services Used | 8+ |
| Interview Topics Covered | 50+ |

---

## 👤 Author

**Bruce Lanskiy**
- GitHub: [@blanskiy](https://github.com/blanskiy)
- LinkedIn: [Connect](https://linkedin.com/in/blanskiy)

---

## 📄 License

This project is for educational and portfolio purposes.
