# Project Metrics Template

Copy this into your README.md under Results section.

## Performance Metrics

### Model Performance
| Metric | Value | Target | Status | Notes |
|--------|-------|--------|--------|-------|
| Accuracy | X% | Y% | Status | |
| Precision | X | Y | Status | |
| Recall | X | Y | Status | |

### System Performance
| Metric | Value | Target | Status | Notes |
|--------|-------|--------|--------|-------|
| Throughput (RPS) | X | Y | Status | Requests per second |
| p50 Latency | Xms | Yms | Status | Median latency |
| p99 Latency | Xms | Yms | Status | 99th percentile |

### Cost Analysis
| Resource | Monthly Cost | Usage | Optimization |
|----------|--------------|-------|--------------|
| Azure ML Compute | X | Y hours | |
| Azure OpenAI | X | Y tokens | |
| TOTAL | X | | |

## Tips for Documenting Metrics

1. Be Specific: Do not say fast - say 45ms p99 latency
2. Show Trade-offs: Chose X over Y because...
3. Include Context: On Azure NC6s_v3 with 1 GPU...
4. Document Failures: Initial approach failed because...
5. Cost Consciousness: Always document Azure spend
