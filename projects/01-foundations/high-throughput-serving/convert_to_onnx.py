#!/usr/bin/env python3
"""
Convert PyTorch ResNet-50 model to ONNX format.

This script:
1. Loads pre-trained ResNet-50 from PyTorch
2. Exports to ONNX format with optimization
3. Validates the exported model
4. Saves to models/ directory
"""

import torch
import torchvision.models as models
import onnx
import time
import os
from pathlib import Path

def convert_to_onnx(
    model_name: str = "resnet50",
    batch_size: int = 8,
    output_path: str = "models/resnet50.onnx",
    opset_version: int = 14
):
    """
    Convert PyTorch model to ONNX format.
    
    Args:
        model_name: Name of torchvision model
        batch_size: Batch size for export
        output_path: Where to save ONNX model
        opset_version: ONNX opset version (14 is stable, widely supported)
    """
    print("="*60)
    print("PyTorch to ONNX Model Conversion")
    print("="*60)
    
    # Create models directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Load PyTorch model
    print(f"\n1. Loading {model_name} from PyTorch...")
    model = models.resnet50(pretrained=True)
    model.eval()
    print("   ✓ Model loaded")
    
    # Create dummy input (batch_size, channels, height, width)
    print(f"\n2. Creating dummy input (batch_size={batch_size})...")
    dummy_input = torch.randn(batch_size, 3, 224, 224)
    print(f"   ✓ Input shape: {dummy_input.shape}")
    
    # Test PyTorch inference first
    print(f"\n3. Testing PyTorch inference...")
    start = time.time()
    with torch.no_grad():
        pytorch_output = model(dummy_input)
    pytorch_time = (time.time() - start) * 1000
    print(f"   ✓ PyTorch inference: {pytorch_time:.2f}ms")
    print(f"   ✓ Output shape: {pytorch_output.shape}")
    
    # Export to ONNX
    print(f"\n4. Exporting to ONNX (opset {opset_version})...")
    start = time.time()
    
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,  # Optimization
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={
            'input': {0: 'batch_size'},
            'output': {0: 'batch_size'}
        }
    )
    
    export_time = (time.time() - start) * 1000
    print(f"   ✓ Export completed in {export_time:.2f}ms")
    
    # Check file size
    file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
    print(f"   ✓ Model saved to: {output_path}")
    print(f"   ✓ File size: {file_size:.2f} MB")
    
    # Validate ONNX model
    print(f"\n5. Validating ONNX model...")
    onnx_model = onnx.load(output_path)
    onnx.checker.check_model(onnx_model)
    print("   ✓ ONNX model is valid")
    
    # Print model info
    print(f"\n6. Model Information:")
    print(f"   - Input: {onnx_model.graph.input[0].name}")
    print(f"   - Output: {onnx_model.graph.output[0].name}")
    print(f"   - Opset version: {opset_version}")
    print(f"   - Dynamic batch: Yes")
    
    return output_path


def benchmark_onnx(
    onnx_path: str = "models/resnet50.onnx",
    batch_size: int = 8,
    num_runs: int = 10
):
    """
    Benchmark ONNX model inference.
    
    Args:
        onnx_path: Path to ONNX model
        batch_size: Batch size for inference
        num_runs: Number of benchmark runs
    """
    import onnxruntime as ort
    import numpy as np
    
    print("\n" + "="*60)
    print("ONNX Runtime Benchmarking")
    print("="*60)
    
    # Create ONNX Runtime session
    print(f"\n1. Creating ONNX Runtime session...")
    sess = ort.InferenceSession(onnx_path)
    print("   ✓ Session created")
    
    # Print session info
    print(f"\n2. Session Information:")
    print(f"   - Providers: {sess.get_providers()}")
    print(f"   - Input name: {sess.get_inputs()[0].name}")
    print(f"   - Output name: {sess.get_outputs()[0].name}")
    
    # Create dummy input
    dummy_input = np.random.randn(batch_size, 3, 224, 224).astype(np.float32)
    
    # Warm-up run
    print(f"\n3. Warm-up run...")
    _ = sess.run(None, {'input': dummy_input})
    print("   ✓ Warm-up complete")
    
    # Benchmark
    print(f"\n4. Running {num_runs} inference iterations...")
    times = []
    
    for i in range(num_runs):
        start = time.time()
        outputs = sess.run(None, {'input': dummy_input})
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
        
        if (i + 1) % 5 == 0:
            print(f"   Run {i+1}/{num_runs}: {elapsed:.2f}ms")
    
    # Statistics
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"\n5. Benchmark Results (batch_size={batch_size}):")
    print(f"   - Average: {avg_time:.2f}ms")
    print(f"   - Min: {min_time:.2f}ms")
    print(f"   - Max: {max_time:.2f}ms")
    print(f"   - Per-image: {avg_time/batch_size:.2f}ms")
    
    return avg_time


def compare_pytorch_onnx(batch_size: int = 8, num_runs: int = 10):
    """
    Compare PyTorch vs ONNX Runtime performance.
    
    Args:
        batch_size: Batch size for comparison
        num_runs: Number of runs for averaging
    """
    import onnxruntime as ort
    import numpy as np
    
    print("\n" + "="*60)
    print("PyTorch vs ONNX Runtime Comparison")
    print("="*60)
    
    # Load PyTorch model
    print(f"\n1. Loading PyTorch model...")
    pytorch_model = models.resnet50(pretrained=True)
    pytorch_model.eval()
    print("   ✓ PyTorch model loaded")
    
    # Load ONNX model
    print(f"\n2. Loading ONNX model...")
    onnx_session = ort.InferenceSession("models/resnet50.onnx")
    print("   ✓ ONNX model loaded")
    
    # Benchmark PyTorch
    print(f"\n3. Benchmarking PyTorch (batch_size={batch_size})...")
    pytorch_times = []
    
    for i in range(num_runs):
        dummy_input = torch.randn(batch_size, 3, 224, 224)
        start = time.time()
        with torch.no_grad():
            _ = pytorch_model(dummy_input)
        elapsed = (time.time() - start) * 1000
        pytorch_times.append(elapsed)
    
    pytorch_avg = sum(pytorch_times) / len(pytorch_times)
    print(f"   ✓ PyTorch average: {pytorch_avg:.2f}ms")
    
    # Benchmark ONNX
    print(f"\n4. Benchmarking ONNX Runtime (batch_size={batch_size})...")
    onnx_times = []
    
    for i in range(num_runs):
        dummy_input = np.random.randn(batch_size, 3, 224, 224).astype(np.float32)
        start = time.time()
        _ = onnx_session.run(None, {'input': dummy_input})
        elapsed = (time.time() - start) * 1000
        onnx_times.append(elapsed)
    
    onnx_avg = sum(onnx_times) / len(onnx_times)
    print(f"   ✓ ONNX average: {onnx_avg:.2f}ms")
    
    # Comparison
    speedup = pytorch_avg / onnx_avg
    improvement = ((pytorch_avg - onnx_avg) / pytorch_avg) * 100
    
    print(f"\n5. Performance Comparison:")
    print(f"   {'Metric':<20} {'PyTorch':<15} {'ONNX Runtime':<15} {'Improvement':<15}")
    print(f"   {'-'*65}")
    print(f"   {'Batch time':<20} {pytorch_avg:>10.2f}ms {onnx_avg:>14.2f}ms {speedup:>10.2f}×")
    print(f"   {'Per-image time':<20} {pytorch_avg/batch_size:>10.2f}ms {onnx_avg/batch_size:>14.2f}ms {improvement:>10.1f}%")
    
    print(f"\n🚀 Result: ONNX Runtime is {speedup:.2f}× faster than PyTorch!")
    
    return {
        'pytorch_avg': pytorch_avg,
        'onnx_avg': onnx_avg,
        'speedup': speedup,
        'improvement_pct': improvement
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert PyTorch model to ONNX')
    parser.add_argument('--batch-size', type=int, default=8, help='Batch size for export')
    parser.add_argument('--output', type=str, default='models/resnet50.onnx', help='Output path')
    parser.add_argument('--benchmark', action='store_true', help='Run benchmarks')
    parser.add_argument('--compare', action='store_true', help='Compare PyTorch vs ONNX')
    
    args = parser.parse_args()
    
    # Convert model
    onnx_path = convert_to_onnx(
        batch_size=args.batch_size,
        output_path=args.output
    )
    
    # Benchmark if requested
    if args.benchmark:
        benchmark_onnx(onnx_path, batch_size=args.batch_size)
    
    # Compare if requested
    if args.compare:
        compare_pytorch_onnx(batch_size=args.batch_size)
    
    print("\n" + "="*60)
    print("✅ Conversion Complete!")
    print("="*60)
    print(f"\nNext steps:")
    print(f"1. Test ONNX model: python convert_to_onnx.py --benchmark")
    print(f"2. Compare performance: python convert_to_onnx.py --compare")
    print(f"3. Integrate into API: Update src/api.py to use ONNX Runtime")
