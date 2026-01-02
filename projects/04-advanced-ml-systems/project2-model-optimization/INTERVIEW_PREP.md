# Model Optimization - Interview Cheat Sheet

## Quick Framework (30-second answer)

> "I optimize models using a layered approach: First, **ONNX conversion** for 2-3x speedup through graph optimizations with zero accuracy loss. Then **INT8 quantization** for another 2-4x by reducing precision from 32-bit to 8-bit with typically <1% accuracy loss. If needed, **pruning** removes 50-90% of weights. Combined, these achieve 5-10x speedup. I always benchmark latency vs accuracy tradeoffs on validation data."

---

## Optimization Techniques Comparison

| Technique | Speedup | Size Reduction | Accuracy Loss | When to Use |
|-----------|---------|----------------|---------------|-------------|
| **ONNX** | 2-3x | ~Same | 0% | Always - free performance |
| **FP16** | 1.5-2x | 2x | ~0% | GPU inference |
| **INT8 Dynamic** | 2-4x | 4x | <1% | CPU inference, no calibration data |
| **INT8 Static** | 2-4x | 4x | <0.5% | Have calibration data |
| **Pruning 50%** | 2-3x | 2x | 1-2% | Need smaller model |
| **Pruning 90%** | 5-10x | 10x | 3-5% | Edge devices |
| **Distillation** | 5-20x | 5-20x | 2-5% | Can afford retraining |
| **TensorRT** | 3-6x | Varies | ~0% | NVIDIA GPUs |

---

## Decision Framework (Memorize!)

```
┌─────────────────────────────────────────────────────────────────┐
│                 WHICH OPTIMIZATION TO USE?                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  START: Export to ONNX (always)                                 │
│         ↓                                                        │
│  Need GPU inference?                                             │
│  ├── YES → TensorRT (NVIDIA) or FP16                            │
│  └── NO ↓                                                        │
│                                                                  │
│  Need CPU inference?                                             │
│  ├── YES → INT8 Quantization                                    │
│  │         ├── Have calibration data? → Static quantization    │
│  │         └── No calibration data? → Dynamic quantization      │
│  └── NO ↓                                                        │
│                                                                  │
│  Need smaller model?                                             │
│  ├── YES → Pruning + Quantization                               │
│  └── NO → Just ONNX + basic optimizations                       │
│                                                                  │
│  Need MUCH smaller (10x+)?                                       │
│  └── YES → Knowledge Distillation (requires retraining)         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## ONNX Conversion

### What it is
ONNX (Open Neural Network Exchange) is a standard format for ML models.

### Why it's faster
```
PyTorch Inference:               ONNX Runtime:
─────────────────────────────    ─────────────────────────────
Python overhead                  Native C++ execution
Dynamic graph                    Static optimized graph
No operator fusion               Conv + BN + ReLU → single op
No constant folding              Pre-computed constants
```

### Key Code
```python
# Export
torch.onnx.export(
    model, dummy_input, "model.onnx",
    opset_version=17,
    dynamic_axes={'input': {0: 'batch'}}  # Variable batch size
)

# Inference (2-3x faster)
import onnxruntime as ort
session = ort.InferenceSession("model.onnx")
output = session.run(None, {"input": data})
```

---

## Quantization

### What it is
Reduce numerical precision of weights and activations.

```
FP32:  [0.12345678, -0.87654321, ...]  32 bits per weight
        ↓ Quantization
INT8:  [12, -88, ...]                   8 bits per weight

Result: 4x smaller, 2-4x faster
```

### Types of Quantization

| Type | Description | Accuracy | Use Case |
|------|-------------|----------|----------|
| **Dynamic** | Weights quantized at load, activations at runtime | Good | No calibration data |
| **Static** | Both quantized using calibration data | Better | Have representative data |
| **QAT** | Simulated quantization during training | Best | Can retrain |

### Key Interview Point

> "Dynamic quantization is easiest - no calibration needed. Static quantization is more accurate because it calibrates activation ranges on representative data. QAT (quantization-aware training) gives best accuracy but requires retraining."

---

## Pruning

### What it is
Remove unimportant weights (set to zero or delete).

```
Original:     [0.5, 0.01, 0.8, 0.001, 0.3, 0.002]
After 50%:    [0.5, 0,    0.8, 0,     0.3, 0    ]  ← Smallest removed
```

### Types of Pruning

| Type | What's Removed | Speedup | Hardware |
|------|----------------|---------|----------|
| **Unstructured** | Individual weights | Needs sparse libs | Sparse matrix support |
| **Structured** | Entire filters/neurons | Direct speedup | Any hardware |

### Key Interview Point

> "Unstructured pruning achieves higher sparsity but needs sparse matrix libraries for speedup. Structured pruning removes entire channels, giving immediate speedup on any hardware but with less compression."

---

## Knowledge Distillation

### What it is
Train a small "student" model to mimic a large "teacher" model.

```
Teacher:  BERT-Large, 340M params, 99% accuracy
          ↓ Distillation
Student:  DistilBERT, 66M params, 97% accuracy

Result: 5x smaller, 2x faster, only 2% accuracy loss
```

### How it works
```python
# Student learns from teacher's soft predictions
loss = α * hard_loss(student_pred, labels) + 
       (1-α) * soft_loss(student_pred, teacher_pred, temperature)
```

### Key Interview Point

> "Distillation works because the teacher's soft predictions contain more information than hard labels. A prediction of [0.7, 0.2, 0.1] tells the student that classes 2 and 3 are related, which hard labels [1, 0, 0] don't convey."

---

## Interview Questions & Answers

### Q: "How do you reduce inference latency by 10x?"

> "Layered approach: ONNX gives 2-3x through graph optimizations. INT8 quantization adds 2-4x by reducing precision. Pruning at 50% gives another 2x. Combined: 8-24x potential speedup. I benchmark each step to find the optimal tradeoff for the specific accuracy requirements."

### Q: "What's the accuracy-latency tradeoff?"

> "ONNX and TensorRT have zero accuracy loss. FP16 quantization typically <0.1% loss. INT8 quantization usually <1% loss. Pruning at 50% causes 1-2% loss, at 90% causes 3-5%. I always validate on held-out data and set acceptable thresholds before deploying."

### Q: "When would you use dynamic vs static quantization?"

> "Dynamic when I don't have representative calibration data - weights are quantized at load time, activations at runtime. Static when I have calibration data - both weights and activations are quantized based on observed ranges, giving better accuracy. Static is preferred when possible."

### Q: "How do you optimize for edge devices?"

> "Aggressive optimization: INT8 quantization (4x smaller), pruning 70-90% (3-10x smaller), possibly architecture changes like MobileNet instead of ResNet. I target specific hardware (ARM, Qualcomm) with their toolkits. Model size often matters more than latency on edge."

### Q: "What metrics do you track when optimizing?"

> "Five key metrics: (1) Latency - p50, p95, p99 in ms, (2) Throughput - samples/second, (3) Model size - MB on disk, (4) Memory usage - runtime RAM, (5) Accuracy - task-specific metric like F1 or mAP. I track all five across original and optimized models."

---

## Architecture Diagram (Draw This!)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    MODEL OPTIMIZATION PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   PyTorch Model                                                          │
│   ┌─────────────────┐                                                   │
│   │  ResNet-50      │  98 MB, 150ms                                     │
│   │  FP32 weights   │                                                   │
│   └────────┬────────┘                                                   │
│            │                                                             │
│            ▼                                                             │
│   ┌─────────────────┐                                                   │
│   │  ONNX Export    │  Graph optimization, operator fusion              │
│   │                 │  98 MB → 98 MB, 150ms → 80ms                      │
│   └────────┬────────┘                                                   │
│            │                                                             │
│            ▼                                                             │
│   ┌─────────────────┐                                                   │
│   │  INT8 Quantize  │  FP32 → INT8 weights                              │
│   │                 │  98 MB → 25 MB, 80ms → 35ms                       │
│   └────────┬────────┘                                                   │
│            │                                                             │
│            ▼                                                             │
│   ┌─────────────────┐                                                   │
│   │  Optimized      │                                                   │
│   │  ONNX Model     │  25 MB, 35ms                                      │
│   └─────────────────┘                                                   │
│                                                                          │
│   RESULTS:                                                               │
│   ├── Size: 98 MB → 25 MB (4x compression)                              │
│   ├── Latency: 150ms → 35ms (4.3x speedup)                              │
│   └── Accuracy: 99.1% → 98.8% (0.3% loss)                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Numbers to Memorize

| Metric | Typical Value |
|--------|---------------|
| ONNX speedup | 2-3x |
| INT8 size reduction | 4x |
| INT8 speedup | 2-4x |
| INT8 accuracy loss | <1% |
| FP16 size reduction | 2x |
| FP16 accuracy loss | ~0% |
| Pruning 50% speedup | 2x (structured) |
| Pruning accuracy loss | 1-2% (50%), 3-5% (90%) |
| Distillation compression | 5-20x |

---

## Red Flags to Avoid

❌ "We deployed without measuring accuracy on optimized model"

❌ "We use FP16 on CPU" (no speedup on most CPUs)

❌ "We pruned 90% and accuracy dropped 15%" (too aggressive)

❌ "We only measured latency, not throughput" (different for batched inference)

✅ "We benchmark p50, p95, p99 latency on production-like inputs"

✅ "We measure accuracy on held-out validation set after each optimization"

✅ "We profile memory usage for edge deployment"

✅ "We test with realistic batch sizes"

---

## Tools to Mention

| Tool | Purpose | Best For |
|------|---------|----------|
| **ONNX Runtime** | Cross-platform inference | General deployment |
| **TensorRT** | NVIDIA GPU optimization | NVIDIA GPUs |
| **OpenVINO** | Intel hardware optimization | Intel CPUs/GPUs |
| **TFLite** | Mobile/edge optimization | Android/iOS |
| **Core ML** | Apple device optimization | iOS/macOS |
| **ONNX Quantization** | INT8/FP16 quantization | CPU inference |
| **PyTorch Pruning** | Weight pruning | Research/experimentation |
