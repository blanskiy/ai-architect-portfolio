"""
Model Benchmarking
Measure and compare inference performance across model variants.

Metrics measured:
- Latency (ms): Time per inference
- Throughput (samples/sec): Inferences per second
- Memory usage (MB): GPU/CPU memory
- Model size (MB): File size on disk
- Accuracy: Model output quality
"""

import os
import time
import gc
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Callable
from dataclasses import dataclass, field
import statistics

import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkConfig:
    """Configuration for benchmarking."""
    # Number of warmup iterations (not counted in results)
    warmup_iterations: int = 10
    
    # Number of measured iterations
    num_iterations: int = 100
    
    # Batch sizes to test
    batch_sizes: List[int] = field(default_factory=lambda: [1, 8, 32])
    
    # Whether to measure memory usage
    measure_memory: bool = True
    
    # Whether to measure accuracy
    measure_accuracy: bool = False
    
    # Device to run on
    device: str = "cpu"


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""
    model_name: str
    batch_size: int
    
    # Latency metrics (ms)
    latency_mean: float
    latency_std: float
    latency_min: float
    latency_max: float
    latency_p50: float
    latency_p95: float
    latency_p99: float
    
    # Throughput
    throughput: float  # samples/sec
    
    # Memory (MB)
    memory_mb: Optional[float] = None
    
    # Model size (MB)
    model_size_mb: Optional[float] = None
    
    # Accuracy (if measured)
    accuracy: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_name": self.model_name,
            "batch_size": self.batch_size,
            "latency_mean_ms": round(self.latency_mean, 3),
            "latency_std_ms": round(self.latency_std, 3),
            "latency_p50_ms": round(self.latency_p50, 3),
            "latency_p95_ms": round(self.latency_p95, 3),
            "latency_p99_ms": round(self.latency_p99, 3),
            "throughput_samples_sec": round(self.throughput, 1),
            "memory_mb": round(self.memory_mb, 1) if self.memory_mb else None,
            "model_size_mb": round(self.model_size_mb, 2) if self.model_size_mb else None,
        }


class ModelBenchmark:
    """
    Benchmarks ML model inference performance.
    
    Usage:
        benchmark = ModelBenchmark()
        
        # Benchmark a single model
        result = benchmark.benchmark_onnx(
            model_path="model.onnx",
            input_shape=(1, 3, 224, 224),
            num_iterations=100
        )
        
        # Compare multiple models
        results = benchmark.compare_models(
            models={
                "original": "model.onnx",
                "quantized": "model_int8.onnx",
            },
            input_shape=(1, 3, 224, 224)
        )
        
        benchmark.print_report(results)
    """
    
    def __init__(self, config: Optional[BenchmarkConfig] = None):
        self.config = config or BenchmarkConfig()
    
    def benchmark_onnx(
        self,
        model_path: str,
        input_shape: tuple,
        batch_size: int = 1,
        num_iterations: Optional[int] = None,
        warmup_iterations: Optional[int] = None,
    ) -> BenchmarkResult:
        """
        Benchmark an ONNX model.
        
        Args:
            model_path: Path to ONNX model
            input_shape: Input tensor shape (without batch dim or with batch=1)
            batch_size: Batch size for inference
            num_iterations: Number of iterations to measure
            warmup_iterations: Number of warmup iterations
        
        Returns:
            BenchmarkResult with performance metrics
        """
        
        import onnxruntime as ort
        
        num_iterations = num_iterations or self.config.num_iterations
        warmup_iterations = warmup_iterations or self.config.warmup_iterations
        
        logger.info(f"Benchmarking ONNX model: {model_path}")
        logger.info(f"  Batch size: {batch_size}, Iterations: {num_iterations}")
        
        # Prepare input
        if input_shape[0] == 1 or input_shape[0] == batch_size:
            # Batch dim already included
            full_shape = (batch_size,) + input_shape[1:]
        else:
            # No batch dim
            full_shape = (batch_size,) + input_shape
        
        input_data = np.random.randn(*full_shape).astype(np.float32)
        
        # Create session
        providers = ['CPUExecutionProvider']
        if self.config.device == "cuda":
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        
        session = ort.InferenceSession(model_path, providers=providers)
        input_name = session.get_inputs()[0].name
        
        # Warmup
        for _ in range(warmup_iterations):
            session.run(None, {input_name: input_data})
        
        # Benchmark
        latencies = []
        
        gc.collect()  # Clean up before measurement
        
        for _ in range(num_iterations):
            start = time.perf_counter()
            session.run(None, {input_name: input_data})
            end = time.perf_counter()
            
            latencies.append((end - start) * 1000)  # Convert to ms
        
        # Calculate statistics
        latencies_sorted = sorted(latencies)
        
        result = BenchmarkResult(
            model_name=Path(model_path).stem,
            batch_size=batch_size,
            latency_mean=statistics.mean(latencies),
            latency_std=statistics.stdev(latencies) if len(latencies) > 1 else 0,
            latency_min=min(latencies),
            latency_max=max(latencies),
            latency_p50=latencies_sorted[int(len(latencies) * 0.5)],
            latency_p95=latencies_sorted[int(len(latencies) * 0.95)],
            latency_p99=latencies_sorted[int(len(latencies) * 0.99)],
            throughput=batch_size * 1000 / statistics.mean(latencies),
            model_size_mb=os.path.getsize(model_path) / (1024 * 1024),
        )
        
        return result
    
    def benchmark_pytorch(
        self,
        model,
        input_shape: tuple,
        batch_size: int = 1,
        num_iterations: Optional[int] = None,
        warmup_iterations: Optional[int] = None,
        device: str = "cpu",
    ) -> BenchmarkResult:
        """
        Benchmark a PyTorch model.
        
        Args:
            model: PyTorch model
            input_shape: Input tensor shape
            batch_size: Batch size for inference
            num_iterations: Number of iterations
            warmup_iterations: Number of warmup iterations
            device: Device to run on
        
        Returns:
            BenchmarkResult with performance metrics
        """
        
        import torch
        
        num_iterations = num_iterations or self.config.num_iterations
        warmup_iterations = warmup_iterations or self.config.warmup_iterations
        
        logger.info(f"Benchmarking PyTorch model")
        logger.info(f"  Batch size: {batch_size}, Device: {device}")
        
        # Prepare model and input
        model = model.to(device)
        model.eval()
        
        full_shape = (batch_size,) + input_shape[1:] if input_shape[0] == 1 else (batch_size,) + input_shape
        input_tensor = torch.randn(*full_shape).to(device)
        
        # Warmup
        with torch.no_grad():
            for _ in range(warmup_iterations):
                _ = model(input_tensor)
        
        # Synchronize if CUDA
        if device == "cuda":
            torch.cuda.synchronize()
        
        # Benchmark
        latencies = []
        
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
        
        with torch.no_grad():
            for _ in range(num_iterations):
                if device == "cuda":
                    torch.cuda.synchronize()
                
                start = time.perf_counter()
                _ = model(input_tensor)
                
                if device == "cuda":
                    torch.cuda.synchronize()
                
                end = time.perf_counter()
                latencies.append((end - start) * 1000)
        
        # Calculate statistics
        latencies_sorted = sorted(latencies)
        
        # Estimate model size
        model_size = sum(p.numel() * p.element_size() for p in model.parameters()) / (1024 * 1024)
        
        result = BenchmarkResult(
            model_name="pytorch_model",
            batch_size=batch_size,
            latency_mean=statistics.mean(latencies),
            latency_std=statistics.stdev(latencies) if len(latencies) > 1 else 0,
            latency_min=min(latencies),
            latency_max=max(latencies),
            latency_p50=latencies_sorted[int(len(latencies) * 0.5)],
            latency_p95=latencies_sorted[int(len(latencies) * 0.95)],
            latency_p99=latencies_sorted[int(len(latencies) * 0.99)],
            throughput=batch_size * 1000 / statistics.mean(latencies),
            model_size_mb=model_size,
        )
        
        return result
    
    def compare_models(
        self,
        models: Dict[str, str],
        input_shape: tuple,
        batch_sizes: Optional[List[int]] = None,
    ) -> Dict[str, List[BenchmarkResult]]:
        """
        Compare multiple ONNX models.
        
        Args:
            models: Dict mapping model names to paths
            input_shape: Input tensor shape
            batch_sizes: List of batch sizes to test
        
        Returns:
            Dict mapping model names to list of results (one per batch size)
        """
        
        batch_sizes = batch_sizes or self.config.batch_sizes
        
        results = {}
        
        for model_name, model_path in models.items():
            logger.info(f"\nBenchmarking: {model_name}")
            results[model_name] = []
            
            for batch_size in batch_sizes:
                result = self.benchmark_onnx(
                    model_path=model_path,
                    input_shape=input_shape,
                    batch_size=batch_size,
                )
                result.model_name = model_name
                results[model_name].append(result)
        
        return results
    
    def print_report(
        self,
        results: Union[BenchmarkResult, Dict[str, List[BenchmarkResult]]],
        baseline_name: Optional[str] = None,
    ):
        """
        Print benchmark results as a formatted report.
        
        Args:
            results: Single result or dict of results from compare_models
            baseline_name: Name of baseline model for speedup calculation
        """
        
        print("\n" + "=" * 80)
        print("BENCHMARK REPORT")
        print("=" * 80)
        
        if isinstance(results, BenchmarkResult):
            self._print_single_result(results)
        else:
            self._print_comparison_report(results, baseline_name)
    
    def _print_single_result(self, result: BenchmarkResult):
        """Print a single benchmark result."""
        
        print(f"\nModel: {result.model_name}")
        print(f"Batch Size: {result.batch_size}")
        print("-" * 40)
        print(f"Latency (mean): {result.latency_mean:.2f} ms")
        print(f"Latency (std):  {result.latency_std:.2f} ms")
        print(f"Latency (p50):  {result.latency_p50:.2f} ms")
        print(f"Latency (p95):  {result.latency_p95:.2f} ms")
        print(f"Latency (p99):  {result.latency_p99:.2f} ms")
        print(f"Throughput:     {result.throughput:.1f} samples/sec")
        
        if result.model_size_mb:
            print(f"Model Size:     {result.model_size_mb:.2f} MB")
    
    def _print_comparison_report(
        self,
        results: Dict[str, List[BenchmarkResult]],
        baseline_name: Optional[str] = None,
    ):
        """Print comparison report for multiple models."""
        
        # Find baseline for speedup calculation
        if baseline_name is None:
            baseline_name = list(results.keys())[0]
        
        # Group by batch size
        batch_sizes = set()
        for model_results in results.values():
            for r in model_results:
                batch_sizes.add(r.batch_size)
        
        for batch_size in sorted(batch_sizes):
            print(f"\n{'─' * 80}")
            print(f"Batch Size: {batch_size}")
            print(f"{'─' * 80}")
            
            # Header
            print(f"{'Model':<20} {'Latency (ms)':<15} {'Throughput':<15} {'Size (MB)':<12} {'Speedup':<10}")
            print("-" * 80)
            
            # Get baseline latency for this batch size
            baseline_latency = None
            baseline_size = None
            for r in results.get(baseline_name, []):
                if r.batch_size == batch_size:
                    baseline_latency = r.latency_mean
                    baseline_size = r.model_size_mb
                    break
            
            # Print each model
            for model_name, model_results in results.items():
                for r in model_results:
                    if r.batch_size == batch_size:
                        speedup = baseline_latency / r.latency_mean if baseline_latency else 1.0
                        compression = baseline_size / r.model_size_mb if baseline_size and r.model_size_mb else 1.0
                        
                        print(f"{model_name:<20} "
                              f"{r.latency_mean:>6.2f} ± {r.latency_std:<5.2f} "
                              f"{r.throughput:>10.1f}/s   "
                              f"{r.model_size_mb or 0:>8.2f}    "
                              f"{speedup:>5.2f}x")
        
        # Summary
        print(f"\n{'=' * 80}")
        print("SUMMARY")
        print(f"{'=' * 80}")
        
        for model_name, model_results in results.items():
            if model_results:
                r = model_results[0]  # Use first batch size for summary
                print(f"{model_name}:")
                print(f"  - Size: {r.model_size_mb:.2f} MB")
                
                if baseline_name and model_name != baseline_name:
                    baseline_r = results[baseline_name][0]
                    speedup = baseline_r.latency_mean / r.latency_mean
                    compression = baseline_r.model_size_mb / r.model_size_mb if r.model_size_mb else 1
                    print(f"  - Speedup: {speedup:.2f}x vs {baseline_name}")
                    print(f"  - Compression: {compression:.2f}x vs {baseline_name}")


def measure_accuracy(
    model_path: str,
    dataloader,
    metric_fn: Callable,
    input_name: str = "input",
    is_onnx: bool = True,
) -> float:
    """
    Measure model accuracy on a dataset.
    
    Args:
        model_path: Path to model
        dataloader: DataLoader with (input, label) batches
        metric_fn: Function that takes (predictions, labels) and returns metric
        input_name: Name of input tensor
        is_onnx: Whether model is ONNX format
    
    Returns:
        Accuracy metric
    """
    
    import onnxruntime as ort
    
    if is_onnx:
        session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
        
        all_preds = []
        all_labels = []
        
        for batch in dataloader:
            inputs, labels = batch
            inputs = inputs.numpy().astype(np.float32)
            
            preds = session.run(None, {input_name: inputs})[0]
            
            all_preds.append(preds)
            all_labels.append(labels.numpy())
        
        all_preds = np.concatenate(all_preds)
        all_labels = np.concatenate(all_labels)
        
        return metric_fn(all_preds, all_labels)
    
    else:
        raise NotImplementedError("PyTorch accuracy measurement not implemented")


# Example usage
if __name__ == "__main__":
    benchmark = ModelBenchmark()
    
    print("Benchmark module ready")
    print("\nExample usage:")
    print("""
    # Benchmark single model
    result = benchmark.benchmark_onnx(
        model_path="model.onnx",
        input_shape=(1, 3, 224, 224)
    )
    
    # Compare models
    results = benchmark.compare_models(
        models={
            "original": "model.onnx",
            "int8": "model_int8.onnx",
        },
        input_shape=(1, 3, 224, 224)
    )
    
    benchmark.print_report(results, baseline_name="original")
    """)
