# 🏗️ System Architecture

This document explains the architectural decisions, design patterns, and technical choices in the high-throughput ML serving system.

---

## 📐 **System Overview**

### **Architecture Diagram**

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Load Balancer                              │
│                     (Nginx / ALB / Cloud LB)                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ├─────────────────────────┐
                             │                         │
                             ▼                         ▼
                    ┌─────────────────┐      ┌─────────────────┐
                    │   API Instance  │      │   API Instance  │
                    │    (Container)  │      │    (Container)  │
                    └────────┬────────┘      └────────┬────────┘
                             │                         │
                             └──────────┬──────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    │                                       │
                    ▼                                       ▼
         ┌─────────────────────┐              ┌─────────────────────┐
         │   Redis (Cache)     │              │  Prometheus         │
         │   • Primary         │              │  (Metrics)          │
         │   • Replica         │              └─────────────────────┘
         └─────────────────────┘
```

---

## 🎯 **Design Decisions**

### **1. FastAPI Framework**

**Choice**: FastAPI over Flask/Django

**Rationale**:
- **Performance**: ASGI-based, async support
- **Type Safety**: Pydantic validation
- **Documentation**: Auto-generated OpenAPI docs
- **Modern**: Python 3.10+ features

**Trade-offs**:
- ✅ High performance
- ✅ Excellent developer experience
- ❌ Smaller ecosystem than Flask
- ❌ Learning curve for async

---

### **2. Request Batching Strategy**

**Choice**: Dynamic batching with time-based and size-based triggers

**Implementation**:
```python
MAX_BATCH_SIZE = 8        # Batch when 8 requests arrive
MAX_WAIT_TIME = 50ms      # Or batch after 50ms timeout
```

**Rationale**:
- **GPU Efficiency**: ResNet-50 processes 8 images in 718ms vs 250ms×8=2000ms sequentially
- **Latency Trade-off**: 50ms wait acceptable for 2.8× throughput gain
- **Resource Utilization**: Better GPU saturation

**Optimization Data**:
| Batch Size | Time (ms) | Per-Image (ms) | Efficiency |
|------------|-----------|----------------|------------|
| 1 | 250 | 250 | 1.0× |
| 2 | 340 | 170 | 1.47× |
| 4 | 520 | 130 | 1.92× |
| 8 | 718 | 89 | 2.81× |
| 16 | 1100 | 69 | 3.62× |

**Why 8?**: Diminishing returns beyond batch size 8, increased latency variance.

---

### **3. Caching Strategy**

**Choice**: Redis with SHA-256 content hashing

**Key Generation**:
```python
cache_key = f"prediction:{sha256(image_bytes).hexdigest()}"
```

**Rationale**:
- **Content-based**: Identical images = same key (deduplication)
- **Fast**: SHA-256 in Python is ~1ms for typical images
- **Collision-resistant**: Cryptographic hash prevents false positives

**TTL Strategy**:
- **Default**: 1 hour (3600s)
- **Rationale**: Balance between cache hits and freshness
- **Configurable**: Adjust based on use case

**Alternative Considered**: Perceptual hashing
- **Pros**: Similar images would match
- **Cons**: Slower, requires additional library, potential false positives
- **Decision**: Content hash sufficient for most use cases

---

### **4. Async Architecture**

**Choice**: Async/await with asyncio

**Pattern**:
```python
async def predict(file: UploadFile):
    # Non-blocking file read
    contents = await file.read()
    
    # Non-blocking batch wait
    result = await batch_manager.add_to_batch(tensor)
    
    return result
```

**Benefits**:
- **Concurrency**: Handle 1000s of requests with minimal memory
- **I/O Efficiency**: Don't block on Redis/file operations
- **Scalability**: Single process handles many concurrent requests

**vs Threading**:
| Aspect | Async | Threading |
|--------|-------|-----------|
| Memory | ~KB per request | ~MB per thread |
| CPU | Single core | Multiple cores needed |
| Complexity | Higher | Lower |
| Scalability | Excellent | Good |

---

### **5. Monitoring Architecture**

**Choice**: Prometheus + Structured Logs

**Metrics Strategy**:
- **RED Method**: Rate, Errors, Duration
- **USE Method**: Utilization, Saturation, Errors
- **Custom**: Cache hit rate, batch size, queue depth

**Log Strategy**:
- **Format**: JSON for machine parsing
- **Context**: Request correlation IDs
- **Levels**: INFO (success), ERROR (failures), DEBUG (development)

**Why Not APM Tools** (DataDog, New Relic):
- ✅ Open source, self-hosted
- ✅ Standard protocol (Prometheus)
- ✅ No vendor lock-in
- ❌ Less sophisticated out-of-box

---

## 🔄 **Request Flow**

### **1. Cache Hit Path** (Fast Path)

```
Client Request
    ↓ (1-5ms)
FastAPI Handler
    ↓ (1ms)
File Read & Hash
    ↓ (10-15ms)
Redis GET
    ↓ (1ms)
JSON Parse
    ↓ (1ms)
HTTP Response
────────────────
Total: ~20-25ms
```

### **2. Cache Miss Path** (Inference Path)

```
Client Request
    ↓ (1-5ms)
FastAPI Handler
    ↓ (1ms)
File Read & Hash
    ↓ (10ms)
Redis GET (miss)
    ↓ (5ms)
Image Preprocessing
    ↓ (0-50ms)
Batch Queue Wait
    ↓ (718ms)
Model Inference
    ↓ (5ms)
Post-processing
    ↓ (10ms)
Redis SET
    ↓ (1ms)
HTTP Response
─────────────────
Total: ~750-800ms
```

---

## 🧩 **Component Design**

### **Batch Manager**

**Responsibilities**:
1. Collect incoming requests
2. Trigger batches (time or size)
3. Run inference
4. Distribute results

**Concurrency Model**:
```python
# Producer-Consumer Pattern
queue = asyncio.Queue()

# Producers (API handlers)
await queue.put(request)

# Consumer (batch loop)
while True:
    batch = await collect_batch()
    results = model(batch)
    distribute_results(results)
```

**Design Choices**:
- **async.Future**: For request-response coordination
- **asyncio.Lock**: Thread-safe queue access
- **Background Task**: Continuous batch processing

---

### **Cache Manager**

**Responsibilities**:
1. Generate cache keys
2. Get/Set cached results
3. Track hit/miss statistics
4. Handle Redis failures gracefully

**Resilience**:
```python
try:
    cached = redis.get(key)
except RedisError:
    # Graceful degradation: proceed without cache
    logger.warning("Redis unavailable, proceeding with inference")
    cached = None
```

**Design Choices**:
- **Fail-safe**: System works without cache
- **Instrumented**: Track hit rates for optimization
- **Configurable**: TTL, connection timeouts

---

### **Logger Configuration**

**Structured Logging**:
```python
logger.info(
    "Request completed",
    extra={
        'request_id': 'abc123',
        'latency_ms': 540,
        'cache_hit': True
    }
)
```

**Output (JSON)**:
```json
{
  "timestamp": "2025-11-22T12:00:00Z",
  "level": "INFO",
  "message": "Request completed",
  "request_id": "abc123",
  "latency_ms": 540,
  "cache_hit": true
}
```

**Benefits**:
- Parseable by log aggregators (ELK, CloudWatch)
- Queryable by fields
- Correlation across services

---

## 🔐 **Security Considerations**

### **Input Validation**

- **File Type**: Only JPEG, PNG accepted
- **File Size**: Max 10MB limit
- **Rate Limiting**: (TODO) Implement per-IP limits

### **Cache Poisoning**

- **Mitigation**: Content-based keys (can't manipulate)
- **TTL**: Auto-expiration prevents stale data

### **Resource Exhaustion**

- **Queue Limits**: Max queue size prevents memory overflow
- **Timeouts**: Request timeouts prevent hanging
- **Docker Limits**: Memory/CPU limits in container

---

## 📈 **Scalability Design**

### **Horizontal Scaling**

```
Load Balancer
    ├─ Instance 1 (handling 1.85 RPS)
    ├─ Instance 2 (handling 1.85 RPS)
    ├─ Instance 3 (handling 1.85 RPS)
    └─ Instance N ...
```

**Shared State**: Redis (cache)
**Stateless API**: No local state, can scale infinitely

### **Vertical Scaling**

- **GPU**: Add GPU support → 10-20× faster inference
- **CPU**: More cores → More concurrent requests
- **Memory**: Larger batch sizes → Better GPU utilization

### **Bottleneck Analysis**

| Load | Bottleneck | Solution |
|------|------------|----------|
| Low (<2 RPS) | None | Single instance sufficient |
| Medium (2-10 RPS) | CPU inference | Add GPU or scale horizontally |
| High (>10 RPS) | Redis | Redis Cluster or additional replicas |
| Very High (>100 RPS) | Network/Load Balancer | CDN for static content |

---

## 🛠️ **Technology Choices**

### **Core Stack**

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **API Framework** | FastAPI | Performance, async, type safety |
| **ML Framework** | PyTorch | Industry standard, model zoo |
| **Cache** | Redis | Fast, reliable, ubiquitous |
| **Container** | Docker | Standard, portable, reproducible |
| **Metrics** | Prometheus | Industry standard, powerful |
| **Load Testing** | Locust | Python-based, distributed |

### **Alternatives Considered**

**API Framework**:
- Flask: Too slow, no async
- Django: Too heavy, not designed for ML
- gRPC: Considered for future (faster but more complex)

**Cache**:
- Memcached: No persistence, less features
- DynamoDB: Higher latency, cloud-only
- Local memory: No sharing across instances

**ML Framework**:
- TensorFlow: Considered, PyTorch more Pythonic
- ONNX: Future optimization planned

---

## 🔬 **Performance Tuning**

### **Batch Size Tuning**

Tested batch sizes 1-32:
- **Result**: 8 is optimal for ResNet-50 on CPU
- **Why**: Diminishing returns after 8, increased variance

### **Wait Time Tuning**

Tested 10ms-500ms:
- **Result**: 50ms balances latency and throughput
- **Why**: Allows 2-4 requests to batch without excessive wait

### **Cache TTL Tuning**

Tested 5min-24hours:
- **Result**: 1 hour is default
- **Why**: Balance memory usage and hit rate
- **Recommendation**: Adjust per use case

---

## 📊 **Monitoring Strategy**

### **Metrics to Track**

**Golden Signals**:
1. **Latency**: P50, P95, P99 response times
2. **Traffic**: Requests per second
3. **Errors**: Error rate, error types
4. **Saturation**: Queue depth, cache memory

**Business Metrics**:
1. **Cache Hit Rate**: Optimize for >70%
2. **Batch Efficiency**: Average batch size
3. **Cost**: Inference count (relates to compute cost)

### **Alerting Rules**

```yaml
# Error rate too high
alert: HighErrorRate
expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
for: 5m

# Latency too high
alert: HighLatency
expr: histogram_quantile(0.95, http_request_duration_seconds) > 2
for: 10m

# Cache hit rate low
alert: LowCacheHitRate
expr: cache_hit_rate < 0.5
for: 30m
```

---

## 🚀 **Future Architecture**

### **Planned Improvements**

1. **gRPC API**: 50% lower latency than REST
2. **GPU Support**: 10-20× faster inference
3. **Model Registry**: Versioning and A/B testing
4. **Distributed Caching**: Redis Cluster for HA
5. **Auto-scaling**: Dynamic based on queue depth

### **Architecture Evolution**

```
Current: Single-region, single model
    ↓
Phase 2: Multi-model support, model versioning
    ↓
Phase 3: Multi-region, geo-routing
    ↓
Phase 4: Real-time learning, model updates
```

---

## 📚 **References**

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PyTorch Serving Best Practices](https://pytorch.org/serve/)
- [Redis Caching Strategies](https://redis.io/topics/lru-cache)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [ML Systems Design Patterns](https://github.com/eugeneyan/ml-design-patterns)

---

## 🤔 **Design Philosophy**

**Principles**:
1. **Simplicity First**: Start simple, optimize when needed
2. **Measure Everything**: Make decisions based on data
3. **Fail Gracefully**: Degrade functionality, not availability
4. **Production-Ready**: Monitoring, logging, error handling from day 1

**Trade-offs Made**:
- Latency vs Throughput: Chose throughput (batching)
- Complexity vs Performance: Worth it for 5× improvement
- Memory vs Speed: Caching uses memory for speed
- Development Time vs Perfection: Ship working solution, iterate

---

<div align="center">

**Architecture designed for production ML workloads**

[← Back to README](README.md) | [View Performance →](PERFORMANCE.md)

</div>
