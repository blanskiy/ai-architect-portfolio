# Month 4: Advanced ML Systems

Production-grade feature engineering and model optimization for enterprise ML.

## Learning Objectives

By the end of this month, you will be able to:

1. **Design and implement feature stores** for consistent feature serving
2. **Optimize models** for production inference (ONNX, quantization, pruning)
3. **Build vector search systems** for embeddings and similarity
4. **Implement caching strategies** for low-latency serving

---

## Projects Overview

| Project | Focus | Key Technologies |
|---------|-------|------------------|
| **Project 1: Feature Store** | Feature engineering & serving | Feast, Redis, Online/Offline |
| **Project 2: Model Optimization** | Inference acceleration | ONNX, Quantization, TensorRT |
| **Project 3: Vector Database** | Embedding search | FAISS, Pinecone patterns, ANN |
| **Project 4: Caching & Serving** | Low-latency inference | Redis, Request batching, Edge |

---

## Project 1: Feature Store

### Why Feature Stores?

```
WITHOUT Feature Store:              WITH Feature Store:
─────────────────────────           ─────────────────────────
Training: SQL query A               Training: feast.get_features()
Serving: SQL query B (different!)   Serving: feast.get_features()
         ↓                                   ↓
    Training/Serving SKEW!              CONSISTENCY ✓
```

### The Problem It Solves

1. **Training-Serving Skew**: Features computed differently in training vs production
2. **Feature Duplication**: Same features rebuilt across teams
3. **Point-in-Time Correctness**: Avoiding data leakage in training
4. **Low-Latency Serving**: Pre-computed features for real-time inference

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Feature View** | Logical grouping of related features |
| **Entity** | Primary key for feature lookup (user_id, product_id) |
| **Offline Store** | Historical features for training (Parquet, BigQuery) |
| **Online Store** | Low-latency features for serving (Redis, DynamoDB) |
| **Materialization** | Moving features from offline → online store |

---

## Project 2: Model Optimization

### Optimization Techniques

| Technique | Speedup | Accuracy Loss | Use Case |
|-----------|---------|---------------|----------|
| **ONNX Conversion** | 2-3x | None | Cross-platform deployment |
| **Quantization (INT8)** | 2-4x | <1% | Edge devices, CPU inference |
| **Pruning** | 2-10x | 1-3% | Reduce model size |
| **Distillation** | 5-20x | 2-5% | Smaller student model |
| **TensorRT** | 3-6x | None | NVIDIA GPU optimization |

### When to Use What

```
Need: Cross-platform compatibility → ONNX
Need: CPU inference speedup       → Quantization
Need: Smaller model size          → Pruning + Quantization
Need: GPU inference speedup       → TensorRT
Need: Much smaller model          → Knowledge Distillation
```

---

## Project 3: Vector Database

### Use Cases

- **Semantic Search**: Find similar documents/products
- **RAG**: Retrieve context for LLM generation
- **Recommendations**: Similar items based on embeddings
- **Anomaly Detection**: Find outliers in embedding space

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Embedding** | Dense vector representation of data |
| **ANN (Approximate Nearest Neighbor)** | Fast similarity search |
| **HNSW** | Graph-based index for fast search |
| **IVF** | Inverted file index for large datasets |
| **Product Quantization** | Compress vectors for memory efficiency |

---

## Project 4: Caching & Serving Patterns

### Latency Targets

| Tier | Latency | Pattern |
|------|---------|---------|
| **Real-time** | <10ms | Pre-computed, cached |
| **Near real-time** | <100ms | Feature store + simple model |
| **Batch** | Minutes | Complex models, batch scoring |

### Caching Strategies

```
Request → Cache Check → Hit? → Return cached result
                    ↓ Miss
              Model Inference → Cache result → Return
```

---

## Skills You'll Demonstrate

### For AI Architect Interviews

1. **Feature Store Design**
   - "How do you ensure training-serving consistency?"
   - "How do you handle point-in-time correctness?"

2. **Model Optimization**
   - "How do you reduce inference latency by 10x?"
   - "What's the tradeoff between model size and accuracy?"

3. **Vector Search**
   - "How do you scale semantic search to billions of vectors?"
   - "What index type would you use for 100M vectors?"

4. **System Design**
   - "Design a recommendation system serving 10K QPS"
   - "How do you handle cache invalidation for ML?"

---

## Prerequisites

- Month 1-3 completed
- Understanding of ML training/serving
- Basic Redis/caching concepts helpful

---

## Let's Build!

Starting with **Project 1: Feature Store** - the foundation for consistent ML features.
