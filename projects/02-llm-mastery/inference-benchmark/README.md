# LLM Inference Benchmark

Comparing inference performance across different LLM serving options for AI Architect role preparation.

## Inference Engines Compared

| Engine | Type | Quantization | Cost Model |
|--------|------|--------------|------------|
| Azure OpenAI (GPT-4o-mini) | Cloud API | N/A | Pay-per-token |
| Azure OpenAI (GPT-4o) | Cloud API | N/A | Pay-per-token |
| Ollama (Llama 3.1 8B) | Local | FP16, Q8, Q4 | Free (compute) |
| Databricks (Llama 3.3 70B) | Cloud API | N/A | Pay-per-token |

## Metrics Measured

- **Tokens per second (TPS)**: Output generation speed
- **Time to first token (TTFT)**: Latency before response starts
- **Total latency**: End-to-end response time
- **Memory usage**: GPU/RAM consumption (local only)
- **Cost per 1K tokens**: Normalized cost comparison

## Setup

### Prerequisites
```bash
pip install -r requirements.txt
```

### Ollama Setup (Local)
```bash
# Install Ollama
winget install Ollama.Ollama

# Pull models
ollama pull llama3.1:8b
ollama pull llama3.1:8b-instruct-q4_0
ollama pull llama3.1:8b-instruct-q8_0
```

### Azure OpenAI Setup
```bash
# Set environment variables
export AZURE_OPENAI_ENDPOINT="your-endpoint"
export AZURE_OPENAI_API_KEY="your-key"
```

## Running Benchmarks

```bash
python benchmark_inference.py --all
python benchmark_inference.py --engine ollama --model llama3.1:8b
python benchmark_inference.py --engine azure --model gpt-4o-mini
```

## Results

See `results/benchmark_results.json` for raw data and `notebooks/analysis.ipynb` for visualizations.

## Key Findings

### Latency vs Cost Trade-off
```
                    Latency (TTFT)    Cost/1K tokens    Best For
                    ──────────────    ──────────────    ────────
Azure GPT-4o        ~500ms            $0.005            Quality-critical
Azure GPT-4o-mini   ~300ms            $0.00015          Cost-sensitive production
Ollama Q4           ~100ms            Free              Development/testing
Ollama Q8           ~150ms            Free              Better quality local
Databricks Llama    ~400ms            $0.001            Databricks ecosystem
```

### When to Use Each

| Scenario | Recommended Engine | Reason |
|----------|-------------------|--------|
| Development/Testing | Ollama (local) | Free, fast iteration |
| Production (cost-sensitive) | Azure GPT-4o-mini | Best cost/performance |
| Production (quality-critical) | Azure GPT-4o | Highest quality |
| Databricks ecosystem | Databricks Llama | Integrated, governed |
| Offline/Air-gapped | Ollama + Q4 | No network required |

## Quantization Deep Dive

### What is Quantization?
Reduces model precision to decrease memory and increase speed:

```
FP32 (32-bit) → FP16 (16-bit) → INT8 (8-bit) → INT4 (4-bit)
     ↓              ↓               ↓              ↓
  Baseline      2x smaller       4x smaller     8x smaller
  Baseline      ~1.5x faster     ~2x faster     ~3x faster
  100% quality  99% quality      97% quality    90-95% quality
```

### Ollama Quantization Options
- `q4_0`: 4-bit quantization, fastest, smallest
- `q4_1`: 4-bit with better accuracy
- `q5_0`, `q5_1`: 5-bit balance
- `q8_0`: 8-bit, near-original quality
- `fp16`: Half precision, best quality

## Architecture Considerations

### For Interview Discussion

**Q: How would you choose an inference engine for production?**

Consider:
1. **Latency requirements**: Real-time (<100ms) vs batch
2. **Cost budget**: Per-token costs at scale
3. **Quality needs**: Task complexity determines model size
4. **Data privacy**: Can data leave your environment?
5. **Scale**: Requests per second requirements
6. **Integration**: Existing cloud/platform ecosystem

**Q: When would you use quantization?**

Use quantization when:
- Deploying to edge/mobile devices
- Cost optimization is critical
- Latency is more important than marginal quality
- Running multiple models on same hardware

Avoid quantization when:
- Quality is paramount (medical, legal)
- Model is already small (7B or less may degrade significantly)
- You have abundant compute resources

## Portfolio Value

This project demonstrates:
- Understanding of LLM inference optimization
- Practical benchmarking skills
- Cost/performance trade-off analysis
- Production deployment considerations
