"""
Model Optimization Pipeline
End-to-end pipeline for optimizing ML models for production.

Pipeline stages:
1. Export PyTorch → ONNX
2. Apply graph optimizations
3. Quantize (INT8 or FP16)
4. Benchmark performance
5. Validate accuracy

Usage:
    pipeline = OptimizationPipeline()
    
    results = pipeline.optimize(
        model=pytorch_model,
        input_shape=(1, 3, 224, 224),
        output_dir="optimized_models",
        quantization="int8",
        validate=True
    )
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

import torch
import torch.nn as nn
import numpy as np

from onnx_converter import ONNXConverter, ONNXExportConfig
from quantization import ModelQuantizer, QuantizationConfig, CalibrationDataReader
from pruning import ModelPruner, PruningConfig
from benchmark import ModelBenchmark, BenchmarkConfig, BenchmarkResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class OptimizationConfig:
    """Configuration for the optimization pipeline."""
    
    # ONNX export settings
    opset_version: int = 17
    dynamic_batch: bool = True
    
    # Quantization settings
    quantization: str = "int8"  # "none", "fp16", "int8", "dynamic", "static"
    use_calibration: bool = False
    calibration_samples: int = 100
    
    # Pruning settings
    enable_pruning: bool = False
    pruning_sparsity: float = 0.5
    
    # Optimization settings
    optimize_graph: bool = True
    
    # Benchmark settings
    benchmark_iterations: int = 100
    benchmark_batch_sizes: List[int] = field(default_factory=lambda: [1, 8, 32])
    
    # Validation settings
    validate_outputs: bool = True
    rtol: float = 1e-2  # Relaxed for quantized models
    atol: float = 1e-3


@dataclass
class OptimizationResult:
    """Results from the optimization pipeline."""
    
    # Paths
    original_model: str
    optimized_model: str
    
    # Size metrics
    original_size_mb: float
    optimized_size_mb: float
    compression_ratio: float
    
    # Performance metrics
    original_latency_ms: float
    optimized_latency_ms: float
    speedup: float
    
    # Accuracy metrics
    outputs_match: bool
    max_output_diff: float
    
    # Configuration used
    quantization_type: str
    pruning_enabled: bool
    pruning_sparsity: Optional[float]
    
    # Metadata
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def save(self, path: str):
        """Save results to JSON file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


class OptimizationPipeline:
    """
    End-to-end model optimization pipeline.
    
    Takes a PyTorch model through:
    1. ONNX export
    2. Graph optimization
    3. Quantization
    4. Benchmarking
    5. Validation
    
    Usage:
        pipeline = OptimizationPipeline()
        
        result = pipeline.optimize(
            model=my_model,
            input_shape=(1, 3, 224, 224),
            output_dir="optimized_models"
        )
        
        print(f"Speedup: {result.speedup}x")
        print(f"Compression: {result.compression_ratio}x")
    """
    
    def __init__(self, config: Optional[OptimizationConfig] = None):
        self.config = config or OptimizationConfig()
        
        # Initialize components
        self.converter = ONNXConverter(ONNXExportConfig(
            opset_version=self.config.opset_version,
            dynamic_batch=self.config.dynamic_batch,
        ))
        
        self.quantizer = ModelQuantizer()
        self.pruner = ModelPruner()
        self.benchmark = ModelBenchmark()
    
    def optimize(
        self,
        model: nn.Module,
        input_shape: tuple,
        output_dir: str,
        model_name: str = "model",
        calibration_data: Optional[np.ndarray] = None,
        test_input: Optional[torch.Tensor] = None,
    ) -> OptimizationResult:
        """
        Run the full optimization pipeline.
        
        Args:
            model: PyTorch model
            input_shape: Input tensor shape
            output_dir: Directory to save optimized models
            model_name: Base name for output files
            calibration_data: Data for static quantization calibration
            test_input: Input for validation (random if not provided)
        
        Returns:
            OptimizationResult with all metrics
        """
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("=" * 60)
        logger.info("STARTING MODEL OPTIMIZATION PIPELINE")
        logger.info("=" * 60)
        
        # Prepare test input
        if test_input is None:
            test_input = torch.randn(*input_shape)
        
        # Step 1: Pruning (if enabled)
        if self.config.enable_pruning:
            logger.info("\nStep 1: Pruning")
            model = self._apply_pruning(model)
        else:
            logger.info("\nStep 1: Pruning (skipped)")
        
        # Step 2: Export to ONNX
        logger.info("\nStep 2: ONNX Export")
        onnx_path = str(output_path / f"{model_name}.onnx")
        self.converter.convert(model, onnx_path, input_shape)
        
        original_size = os.path.getsize(onnx_path) / (1024 * 1024)
        
        # Step 3: Graph Optimization
        if self.config.optimize_graph:
            logger.info("\nStep 3: Graph Optimization")
            optimized_onnx_path = str(output_path / f"{model_name}_optimized.onnx")
            self.converter.optimize_onnx_model(onnx_path, optimized_onnx_path)
            onnx_path = optimized_onnx_path
        else:
            logger.info("\nStep 3: Graph Optimization (skipped)")
        
        # Step 4: Quantization
        logger.info("\nStep 4: Quantization")
        final_model_path = self._apply_quantization(
            onnx_path,
            output_path,
            model_name,
            calibration_data,
        )
        
        optimized_size = os.path.getsize(final_model_path) / (1024 * 1024)
        
        # Step 5: Benchmark
        logger.info("\nStep 5: Benchmarking")
        original_benchmark = self.benchmark.benchmark_onnx(
            onnx_path,
            input_shape,
            batch_size=1,
        )
        
        optimized_benchmark = self.benchmark.benchmark_onnx(
            final_model_path,
            input_shape,
            batch_size=1,
        )
        
        # Step 6: Validation
        logger.info("\nStep 6: Validation")
        validation_result = self._validate_outputs(
            onnx_path,
            final_model_path,
            test_input.numpy(),
        )
        
        # Compile results
        result = OptimizationResult(
            original_model=onnx_path,
            optimized_model=final_model_path,
            original_size_mb=original_size,
            optimized_size_mb=optimized_size,
            compression_ratio=original_size / optimized_size,
            original_latency_ms=original_benchmark.latency_mean,
            optimized_latency_ms=optimized_benchmark.latency_mean,
            speedup=original_benchmark.latency_mean / optimized_benchmark.latency_mean,
            outputs_match=validation_result["outputs_match"],
            max_output_diff=validation_result["max_diff"],
            quantization_type=self.config.quantization,
            pruning_enabled=self.config.enable_pruning,
            pruning_sparsity=self.config.pruning_sparsity if self.config.enable_pruning else None,
            timestamp=datetime.now().isoformat(),
        )
        
        # Save results
        result.save(str(output_path / f"{model_name}_optimization_results.json"))
        
        # Print summary
        self._print_summary(result)
        
        return result
    
    def _apply_pruning(self, model: nn.Module) -> nn.Module:
        """Apply pruning to the model."""
        
        logger.info(f"  Applying {self.config.pruning_sparsity*100:.0f}% pruning")
        
        config = PruningConfig(sparsity=self.config.pruning_sparsity)
        pruner = ModelPruner(config)
        
        model = pruner.prune_model(model)
        pruner.remove_pruning_reparameterization(model)
        
        actual_sparsity = pruner.calculate_sparsity(model)
        logger.info(f"  Actual sparsity: {actual_sparsity*100:.1f}%")
        
        return model
    
    def _apply_quantization(
        self,
        onnx_path: str,
        output_path: Path,
        model_name: str,
        calibration_data: Optional[np.ndarray],
    ) -> str:
        """Apply quantization based on config."""
        
        quant_type = self.config.quantization.lower()
        
        if quant_type == "none":
            logger.info("  Quantization: None (skipped)")
            return onnx_path
        
        elif quant_type == "fp16":
            logger.info("  Quantization: FP16")
            output_file = str(output_path / f"{model_name}_fp16.onnx")
            self.quantizer.quantize_fp16(onnx_path, output_file)
            return output_file
        
        elif quant_type in ["int8", "dynamic"]:
            logger.info("  Quantization: INT8 (dynamic)")
            output_file = str(output_path / f"{model_name}_int8.onnx")
            self.quantizer.quantize_dynamic(onnx_path, output_file)
            return output_file
        
        elif quant_type == "static":
            if calibration_data is None:
                logger.warning("  No calibration data provided, falling back to dynamic")
                output_file = str(output_path / f"{model_name}_int8.onnx")
                self.quantizer.quantize_dynamic(onnx_path, output_file)
                return output_file
            
            logger.info("  Quantization: INT8 (static)")
            output_file = str(output_path / f"{model_name}_int8_static.onnx")
            
            # Create calibration reader
            reader = CalibrationDataReader.from_numpy(
                calibration_data[:self.config.calibration_samples]
            )
            
            self.quantizer.quantize_static(onnx_path, output_file, reader)
            return output_file
        
        else:
            logger.warning(f"  Unknown quantization type: {quant_type}, skipping")
            return onnx_path
    
    def _validate_outputs(
        self,
        original_path: str,
        optimized_path: str,
        test_input: np.ndarray,
    ) -> Dict[str, Any]:
        """Validate that optimized model produces similar outputs."""
        
        import onnxruntime as ort
        
        # Load models
        original_session = ort.InferenceSession(
            original_path, providers=['CPUExecutionProvider']
        )
        optimized_session = ort.InferenceSession(
            optimized_path, providers=['CPUExecutionProvider']
        )
        
        input_name = original_session.get_inputs()[0].name
        test_input = test_input.astype(np.float32)
        
        # Run inference
        original_output = original_session.run(None, {input_name: test_input})[0]
        optimized_output = optimized_session.run(None, {input_name: test_input})[0]
        
        # Compare outputs
        max_diff = np.max(np.abs(original_output - optimized_output))
        mean_diff = np.mean(np.abs(original_output - optimized_output))
        
        outputs_match = np.allclose(
            original_output,
            optimized_output,
            rtol=self.config.rtol,
            atol=self.config.atol,
        )
        
        if outputs_match:
            logger.info(f"  ✓ Outputs match (max diff: {max_diff:.6f})")
        else:
            logger.warning(f"  ✗ Outputs differ (max diff: {max_diff:.6f})")
        
        return {
            "outputs_match": outputs_match,
            "max_diff": float(max_diff),
            "mean_diff": float(mean_diff),
        }
    
    def _print_summary(self, result: OptimizationResult):
        """Print optimization summary."""
        
        print("\n" + "=" * 60)
        print("OPTIMIZATION SUMMARY")
        print("=" * 60)
        
        print(f"\n📦 Model Size:")
        print(f"   Original:   {result.original_size_mb:.2f} MB")
        print(f"   Optimized:  {result.optimized_size_mb:.2f} MB")
        print(f"   Compression: {result.compression_ratio:.2f}x")
        
        print(f"\n⚡ Performance:")
        print(f"   Original latency:   {result.original_latency_ms:.2f} ms")
        print(f"   Optimized latency:  {result.optimized_latency_ms:.2f} ms")
        print(f"   Speedup: {result.speedup:.2f}x")
        
        print(f"\n✓ Validation:")
        status = "✓ PASS" if result.outputs_match else "✗ FAIL"
        print(f"   Output match: {status}")
        print(f"   Max difference: {result.max_output_diff:.6f}")
        
        print(f"\n📁 Output:")
        print(f"   {result.optimized_model}")
        print("=" * 60)


def optimize_for_production(
    model: nn.Module,
    input_shape: tuple,
    output_dir: str = "production_models",
    target_speedup: float = 2.0,
    max_accuracy_loss: float = 0.01,
) -> OptimizationResult:
    """
    Convenience function for production optimization.
    
    Automatically selects optimization level based on targets.
    
    Args:
        model: PyTorch model
        input_shape: Input shape
        output_dir: Output directory
        target_speedup: Target speedup factor
        max_accuracy_loss: Maximum acceptable accuracy loss
    
    Returns:
        OptimizationResult
    """
    
    # Select quantization based on targets
    if target_speedup > 3:
        quantization = "int8"
        enable_pruning = True
        pruning_sparsity = 0.5
    elif target_speedup > 2:
        quantization = "int8"
        enable_pruning = False
        pruning_sparsity = 0.0
    else:
        quantization = "fp16"
        enable_pruning = False
        pruning_sparsity = 0.0
    
    config = OptimizationConfig(
        quantization=quantization,
        enable_pruning=enable_pruning,
        pruning_sparsity=pruning_sparsity,
    )
    
    pipeline = OptimizationPipeline(config)
    
    return pipeline.optimize(
        model=model,
        input_shape=input_shape,
        output_dir=output_dir,
    )


# Example usage
if __name__ == "__main__":
    import torchvision.models as models
    
    print("Model Optimization Pipeline")
    print("-" * 40)
    print("\nExample usage:")
    print("""
    # Load a model
    model = models.resnet18(pretrained=True)
    model.eval()
    
    # Run optimization pipeline
    pipeline = OptimizationPipeline()
    
    result = pipeline.optimize(
        model=model,
        input_shape=(1, 3, 224, 224),
        output_dir="optimized_models",
        model_name="resnet18"
    )
    
    print(f"Speedup: {result.speedup:.2f}x")
    print(f"Compression: {result.compression_ratio:.2f}x")
    """)
