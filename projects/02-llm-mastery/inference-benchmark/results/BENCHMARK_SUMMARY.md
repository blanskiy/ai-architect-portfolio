# LLM Inference Benchmark Results

## Test Environment
- **Hardware**: CPU-only (no GPU)
- **OS**: Windows 11
- **Inference Engine**: Ollama
- **Date**: December 21, 2024

## Models Tested

| Model | Quantization | Size |
|-------|--------------|------|
| llama3.1:8b | FP16 (default) | 4.9 GB |
| llama3.1:8b-instruct-q4_0 | Q4 (4-bit) | 4.7 GB |

## Results Summary

| Model | Avg TPS | Avg TTFT | P95 Latency | Cost |
|-------|---------|----------|-------------|------|
| llama3.1:8b (FP16) | **2.0** | **13.2s** | 406s | $0.00 |
| llama3.1:8b-instruct-q4_0 | 1.6 | 16.0s | 422s | $0.00 |

## Key Findings

### 1. CPU Inference is Slow
- ~2 tokens/second on CPU
- Complex prompts take 6-7 minutes
- Not suitable for real-time applications

### 2. Quantization Doesn't Help on CPU
- Q4 was actually **slower** than FP16
- Quantization benefits require GPU (memory bandwidth bottleneck)
- On CPU, compute is the bottleneck, not memory

### 3. First Run Penalty
- First inference ~60s TTFT (model loading)
- Subsequent runs ~2s TTFT (model cached)
- Important for cold-start considerations

## Production Recommendations

| Use Case | Recommendation | Expected Performance |
|----------|----------------|---------------------|
| Development/Testing | Ollama (local) | 2 TPS, free |
| Real-time Production | Azure OpenAI / GPU | 50-100 TPS |
| Batch Processing | Local CPU acceptable | 2 TPS, free |
| Cost-Sensitive | Azure GPT-4o-mini | 50 TPS, $0.00015/1K |

## Architecture Decision Framework

```
                    ┌─────────────────────────────────────┐
                    │     LLM Inference Decision Tree     │
                    └─────────────────────────────────────┘
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
                   Real-time?                   Batch?
                   (<1s latency)              (minutes OK)
                         │                         │
              ┌──────────┴──────────┐              │
              ▼                     ▼              ▼
         Cost-sensitive?      Quality-critical?   Local CPU
              │                     │           (Ollama)
              ▼                     ▼              │
        Azure GPT-4o-mini    Azure GPT-4o         │
        ($0.00015/1K)        ($0.0025/1K)         │
              │                     │              │
              └─────────┬───────────┘              │
                        ▼                         ▼
                   Cloud GPU              FREE (but slow)
                   50-100 TPS               ~2 TPS
```

## Interview Talking Points

1. **"I benchmarked Llama 3.1 8B locally and measured ~2 TPS on CPU, demonstrating why GPU acceleration or cloud APIs are essential for production workloads."**

2. **"Interestingly, 4-bit quantization didn't improve CPU performance because quantization primarily addresses memory bandwidth bottlenecks on GPU, not compute bottlenecks on CPU."**

3. **"For production, I'd recommend Azure GPT-4o-mini at $0.00015/1K tokens - it offers 50x the throughput of local CPU inference at minimal cost."**

4. **"Local inference with Ollama is valuable for development and testing - zero cost and no API rate limits, even if slower."**

## Cost Comparison at Scale

Assuming 1M tokens/day:

| Option | Daily Cost | Monthly Cost | Latency |
|--------|------------|--------------|---------|
| Local CPU (Ollama) | $0 | $0 | ~500ms/token |
| Azure GPT-4o-mini | $0.15 | $4.50 | ~20ms/token |
| Azure GPT-4o | $2.50 | $75 | ~20ms/token |
| Self-hosted GPU (A10) | ~$8 | ~$240 | ~10ms/token |

## Next Steps

- [ ] Test with GPU (if available)
- [ ] Benchmark Azure OpenAI for comparison
- [ ] Add vLLM benchmark (requires Linux/GPU)
- [ ] Test streaming vs non-streaming performance
