# Project 2: Model Optimization

Accelerate ML inference through ONNX conversion, quantization, pruning, and other optimization techniques.

## Overview

| Aspect | Details |
|--------|---------|
| **Purpose** | Reduce inference latency and model size for production |
| **Techniques** | ONNX, Quantization, Pruning, Distillation |
| **Goal** | 2-10x speedup with minimal accuracy loss |

## The Problem

### Why Optimize?

```
DEVELOPMENT                           PRODUCTION
─────────────────────────────────────────────────────────────
PyTorch model                         Need: <50ms latency
GPU with 24GB VRAM                    Have: CPU with 8GB RAM
Batch size: 32                        Batch size: 1
"It works!"                           "It's too slow!"

SOLUTION: Model Optimization
─────────────────────────────────────────────────────────────
• ONNX: 2-3x faster (optimized runtime)
• Quantization: 2-4x faster + 4x smaller (INT8)
• Pruning: 2-10x faster (remove weights)
• Distillation: 5-20x faster (smaller model)
```

## Optimization Techniques

### Decision Framework

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    WHICH OPTIMIZATION TO USE?                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Need cross-platform deployment?                                        │
│   └── YES → ONNX Conversion (no accuracy loss)                          │
│                                                                          │
│   Need faster CPU inference?                                             │
│   └── YES → Quantization INT8 (< 1% accuracy loss)                      │
│                                                                          │
│   Need smaller model size?                                               │
│   └── YES → Pruning + Quantization (1-3% accuracy loss)                 │
│                                                                          │
│   Need dramatically smaller/faster model?                                │
│   └── YES → Knowledge Distillation (2-5% accuracy loss)                 │
│                                                                          │
│   Deploying to NVIDIA GPU?                                               │
│   └── YES → TensorRT (no accuracy loss, GPU only)                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Comparison Table

| Technique | Speedup | Size Reduction | Accuracy Loss | Complexity |
|-----------|---------|----------------|---------------|------------|
| **ONNX** | 2-3x | None | None | Low |
| **FP16 Quantization** | 1.5-2x | 2x | ~0% | Low |
| **INT8 Quantization** | 2-4x | 4x | <1% | Medium |
| **Pruning (50%)** | 2-3x | 2x | 1-2% | Medium |
| **Pruning (90%)** | 5-10x | 10x | 2-5% | High |
| **Distillation** | 5-20x | 5-20x | 2-5% | High |
| **TensorRT** | 3-6x | Varies | ~0% | Medium |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    MODEL OPTIMIZATION PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ORIGINAL MODEL                                                         │
│   ┌─────────────────┐                                                   │
│   │  PyTorch Model  │                                                   │
│   │  ResNet-50      │                                                   │
│   │  98MB, 150ms    │                                                   │
│   └────────┬────────┘                                                   │
│            │                                                             │
│            ▼                                                             │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                    OPTIMIZATION STAGES                           │  │
│   │                                                                  │  │
│   │   Stage 1: ONNX Export                                          │  │
│   │   ┌─────────────────┐                                           │  │
│   │   │ torch.onnx.export│ → Graph optimizations, constant folding  │  │
│   │   │ 98MB, 80ms      │                                           │  │
│   │   └────────┬────────┘                                           │  │
│   │            │                                                     │  │
│   │   Stage 2: Quantization                                         │  │
│   │   ┌─────────────────┐                                           │  │
│   │   │ INT8 Quantize   │ → FP32 weights → INT8 weights            │  │
│   │   │ 25MB, 40ms      │                                           │  │
│   │   └────────┬────────┘                                           │  │
│   │            │                                                     │  │
│   │   Stage 3: Graph Optimization                                   │  │
│   │   ┌─────────────────┐                                           │  │
│   │   │ Operator Fusion │ → Conv+BN+ReLU → single op               │  │
│   │   │ 25MB, 35ms      │                                           │  │
│   │   └─────────────────┘                                           │  │
│   │                                                                  │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│   OPTIMIZED MODEL                                                        │
│   ┌─────────────────┐                                                   │
│   │  ONNX INT8      │                                                   │
│   │  25MB, 35ms     │  ← 4x smaller, 4x faster!                        │
│   └─────────────────┘                                                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
project2-model-optimization/
├── README.md
├── INTERVIEW_PREP.md
├── requirements.txt
├── src/
│   ├── onnx_converter.py       # PyTorch → ONNX conversion
│   ├── quantization.py         # INT8/FP16 quantization
│   ├── pruning.py              # Weight pruning
│   ├── distillation.py         # Knowledge distillation
│   ├── benchmark.py            # Performance benchmarking
│   └── optimization_pipeline.py # End-to-end pipeline
├── models/
│   └── sample_model.py         # Sample models for testing
├── tests/
│   ├── test_onnx.py
│   ├── test_quantization.py
│   └── test_accuracy.py
└── notebooks/
    └── optimization_demo.ipynb
```

## Key Concepts

### 1. ONNX (Open Neural Network Exchange)

**What**: Standard format for ML models, runs on optimized runtimes.

```python
# Export PyTorch to ONNX
torch.onnx.export(
    model,
    dummy_input,
    "model.onnx",
    opset_version=17,
    input_names=['input'],
    output_names=['output'],
    dynamic_axes={'input': {0: 'batch_size'}}
)

# Run with ONNX Runtime (2-3x faster)
import onnxruntime as ort
session = ort.InferenceSession("model.onnx")
output = session.run(None, {"input": input_data})
```

**Why faster?**
- Graph optimizations (constant folding, dead code elimination)
- Operator fusion (Conv + BatchNorm + ReLU → single op)
- Hardware-specific optimizations

### 2. Quantization

**What**: Reduce precision from FP32 → INT8 (or FP16).

```
FP32: 32 bits per weight → High precision, large, slow
FP16: 16 bits per weight → Good precision, 2x smaller, ~2x faster
INT8:  8 bits per weight → Slightly less precision, 4x smaller, 2-4x faster
```

**Types of Quantization:**

| Type | When Applied | Accuracy | Speed |
|------|--------------|----------|-------|
| **Dynamic** | Runtime | Good | Moderate |
| **Static** | After calibration | Better | Fast |
| **QAT** | During training | Best | Fast |

### 3. Pruning

**What**: Remove unimportant weights (set to zero).

```
Original weights:  [0.5, 0.01, 0.8, 0.001, 0.3]
After 40% pruning: [0.5, 0,    0.8, 0,     0.3]  ← Small weights removed

Result: Sparse matrix → faster computation with sparse libraries
```

**Pruning Strategies:**
- **Magnitude pruning**: Remove smallest weights
- **Structured pruning**: Remove entire neurons/filters
- **Gradual pruning**: Prune incrementally during training

### 4. Knowledge Distillation

**What**: Train small "student" model to mimic large "teacher" model.

```
Teacher (BERT-Large):  340M params, 99% accuracy
Student (DistilBERT):   66M params, 97% accuracy  ← 5x smaller, 2% accuracy drop
```

## Quick Start

### 1. Basic ONNX Conversion
```python
from src.onnx_converter import ONNXConverter

converter = ONNXConverter()
converter.convert(
    model=pytorch_model,
    output_path="model.onnx",
    input_shape=(1, 3, 224, 224)
)
```

### 2. Quantize Model
```python
from src.quantization import ModelQuantizer

quantizer = ModelQuantizer()
quantized_model = quantizer.quantize_dynamic(
    model_path="model.onnx",
    output_path="model_int8.onnx"
)
```

### 3. Benchmark Performance
```python
from src.benchmark import ModelBenchmark

benchmark = ModelBenchmark()
results = benchmark.compare_models(
    models={
        "original": "model.pth",
        "onnx": "model.onnx",
        "quantized": "model_int8.onnx",
    },
    input_shape=(1, 3, 224, 224),
    num_iterations=100
)
benchmark.print_report(results)
```

## Interview Talking Points

### Q: "How do you reduce inference latency by 10x?"

> "I use a combination of techniques: First, **ONNX conversion** for 2-3x speedup through graph optimizations. Then **INT8 quantization** for another 2-4x by reducing precision with minimal accuracy loss. If needed, **pruning** removes 50-90% of weights. Combined, these can achieve 10x+ speedup. I always benchmark accuracy vs latency tradeoffs on a validation set."

### Q: "What's the tradeoff between model size and accuracy?"

> "It depends on the technique. ONNX and TensorRT have no accuracy loss. FP16 quantization loses ~0%. INT8 quantization typically loses <1%. Pruning at 50% loses 1-2%, at 90% loses 3-5%. Distillation depends on student architecture. I always measure on held-out data before deploying."

### Q: "When would you use each optimization technique?"

> "ONNX for any production deployment - it's free performance. Quantization when deploying to CPU or edge devices. Pruning when model size is critical. Distillation when you need dramatically smaller models and can afford retraining. TensorRT specifically for NVIDIA GPUs."

---

*Project 2 - Advanced ML Systems*
