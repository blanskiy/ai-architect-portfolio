"""
Model Quantization
Reduce model precision for faster inference and smaller size.

Quantization converts weights from FP32 (32-bit float) to lower precision:
- FP16: 16-bit float, ~2x smaller, minimal accuracy loss
- INT8: 8-bit integer, ~4x smaller, <1% accuracy loss typically
- INT4: 4-bit integer, ~8x smaller, used for LLMs

Types of Quantization:
- Dynamic: Weights quantized at load time, activations at runtime
- Static: Both weights and activations quantized using calibration data
- QAT: Quantization-Aware Training, best accuracy but requires retraining
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuantizationType(Enum):
    """Types of quantization."""
    DYNAMIC = "dynamic"      # Quantize at runtime
    STATIC = "static"        # Quantize with calibration data
    QAT = "qat"              # Quantization-aware training


class QuantizationPrecision(Enum):
    """Quantization precision levels."""
    FP16 = "fp16"            # 16-bit float
    INT8 = "int8"            # 8-bit integer
    UINT8 = "uint8"          # 8-bit unsigned integer
    INT4 = "int4"            # 4-bit integer (for LLMs)


@dataclass
class QuantizationConfig:
    """Configuration for quantization."""
    precision: QuantizationPrecision = QuantizationPrecision.INT8
    quant_type: QuantizationType = QuantizationType.DYNAMIC
    
    # For static quantization
    calibration_samples: int = 100
    
    # Operators to quantize (None = all supported)
    operators_to_quantize: Optional[List[str]] = None
    
    # Operators to exclude from quantization
    operators_to_exclude: Optional[List[str]] = None
    
    # Per-channel quantization (better accuracy, slightly slower)
    per_channel: bool = True


class ModelQuantizer:
    """
    Quantizes ONNX models for faster inference.
    
    Usage:
        quantizer = ModelQuantizer()
        
        # Dynamic quantization (no calibration data needed)
        quantizer.quantize_dynamic(
            model_path="model.onnx",
            output_path="model_int8.onnx"
        )
        
        # Static quantization (needs calibration data)
        quantizer.quantize_static(
            model_path="model.onnx",
            output_path="model_int8_static.onnx",
            calibration_data=calibration_loader
        )
    """
    
    def __init__(self, config: Optional[QuantizationConfig] = None):
        self.config = config or QuantizationConfig()
    
    def quantize_dynamic(
        self,
        model_path: str,
        output_path: str,
        weight_type: str = "QInt8",
    ) -> Dict[str, Any]:
        """
        Apply dynamic quantization to ONNX model.
        
        Dynamic quantization:
        - Weights are quantized and stored as INT8
        - Activations are quantized dynamically at runtime
        - No calibration data needed
        - Good for models with varying input distributions
        
        Args:
            model_path: Path to input ONNX model
            output_path: Path to save quantized model
            weight_type: Weight quantization type (QInt8 or QUInt8)
        
        Returns:
            Dict with quantization results
        """
        
        from onnxruntime.quantization import quantize_dynamic, QuantType
        
        logger.info(f"Applying dynamic quantization to {model_path}")
        
        # Map string to QuantType
        quant_type = QuantType.QInt8 if weight_type == "QInt8" else QuantType.QUInt8
        
        # Create output directory
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Quantize
        quantize_dynamic(
            model_input=model_path,
            model_output=output_path,
            weight_type=quant_type,
            per_channel=self.config.per_channel,
            op_types_to_quantize=self.config.operators_to_quantize,
        )
        
        # Calculate size reduction
        original_size = os.path.getsize(model_path) / (1024 * 1024)
        quantized_size = os.path.getsize(output_path) / (1024 * 1024)
        
        result = {
            "original_size_mb": original_size,
            "quantized_size_mb": quantized_size,
            "compression_ratio": original_size / quantized_size,
            "size_reduction_pct": (1 - quantized_size / original_size) * 100,
            "quantization_type": "dynamic",
            "precision": weight_type,
            "output_path": output_path,
        }
        
        logger.info(f"Quantization complete:")
        logger.info(f"  Original size: {original_size:.2f} MB")
        logger.info(f"  Quantized size: {quantized_size:.2f} MB")
        logger.info(f"  Compression ratio: {result['compression_ratio']:.2f}x")
        
        return result
    
    def quantize_static(
        self,
        model_path: str,
        output_path: str,
        calibration_data_reader,
        quant_format: str = "QDQ",
    ) -> Dict[str, Any]:
        """
        Apply static quantization to ONNX model.
        
        Static quantization:
        - Requires calibration data to determine quantization ranges
        - Both weights and activations are quantized
        - Better performance than dynamic quantization
        - Best accuracy when calibration data represents production data
        
        Args:
            model_path: Path to input ONNX model
            output_path: Path to save quantized model
            calibration_data_reader: Data reader for calibration
            quant_format: Quantization format (QDQ or QOperator)
        
        Returns:
            Dict with quantization results
        """
        
        from onnxruntime.quantization import quantize_static, CalibrationMethod
        from onnxruntime.quantization import QuantFormat, QuantType
        
        logger.info(f"Applying static quantization to {model_path}")
        
        # Create output directory
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Determine format
        format_map = {
            "QDQ": QuantFormat.QDQ,
            "QOperator": QuantFormat.QOperator,
        }
        
        # Quantize
        quantize_static(
            model_input=model_path,
            model_output=output_path,
            calibration_data_reader=calibration_data_reader,
            quant_format=format_map.get(quant_format, QuantFormat.QDQ),
            per_channel=self.config.per_channel,
            weight_type=QuantType.QInt8,
            activation_type=QuantType.QUInt8,
            calibrate_method=CalibrationMethod.MinMax,
            op_types_to_quantize=self.config.operators_to_quantize,
        )
        
        # Calculate size reduction
        original_size = os.path.getsize(model_path) / (1024 * 1024)
        quantized_size = os.path.getsize(output_path) / (1024 * 1024)
        
        result = {
            "original_size_mb": original_size,
            "quantized_size_mb": quantized_size,
            "compression_ratio": original_size / quantized_size,
            "size_reduction_pct": (1 - quantized_size / original_size) * 100,
            "quantization_type": "static",
            "precision": "INT8",
            "output_path": output_path,
        }
        
        logger.info(f"Static quantization complete:")
        logger.info(f"  Compression ratio: {result['compression_ratio']:.2f}x")
        
        return result
    
    def quantize_fp16(
        self,
        model_path: str,
        output_path: str,
    ) -> Dict[str, Any]:
        """
        Convert model to FP16 precision.
        
        FP16 quantization:
        - Converts FP32 weights to FP16
        - ~2x smaller model
        - Minimal accuracy loss (usually <0.1%)
        - Works well on GPUs with FP16 support
        
        Args:
            model_path: Path to input ONNX model
            output_path: Path to save FP16 model
        
        Returns:
            Dict with conversion results
        """
        
        from onnxruntime.transformers import float16
        import onnx
        
        logger.info(f"Converting to FP16: {model_path}")
        
        # Load model
        model = onnx.load(model_path)
        
        # Convert to FP16
        model_fp16 = float16.convert_float_to_float16(
            model,
            keep_io_types=True,  # Keep input/output as FP32
        )
        
        # Save
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        onnx.save(model_fp16, output_path)
        
        # Calculate size reduction
        original_size = os.path.getsize(model_path) / (1024 * 1024)
        fp16_size = os.path.getsize(output_path) / (1024 * 1024)
        
        result = {
            "original_size_mb": original_size,
            "quantized_size_mb": fp16_size,
            "compression_ratio": original_size / fp16_size,
            "size_reduction_pct": (1 - fp16_size / original_size) * 100,
            "quantization_type": "fp16",
            "precision": "FP16",
            "output_path": output_path,
        }
        
        logger.info(f"FP16 conversion complete:")
        logger.info(f"  Compression ratio: {result['compression_ratio']:.2f}x")
        
        return result


class CalibrationDataReader:
    """
    Data reader for static quantization calibration.
    
    Usage:
        # Create from numpy arrays
        reader = CalibrationDataReader.from_numpy(
            data=calibration_inputs,
            input_name="input"
        )
        
        # Use for static quantization
        quantizer.quantize_static(
            model_path="model.onnx",
            output_path="model_int8.onnx",
            calibration_data_reader=reader
        )
    """
    
    def __init__(self, data_list: List[Dict[str, np.ndarray]]):
        """
        Initialize calibration data reader.
        
        Args:
            data_list: List of dicts mapping input names to numpy arrays
        """
        self.data_list = data_list
        self.index = 0
    
    def get_next(self) -> Optional[Dict[str, np.ndarray]]:
        """Get next calibration sample."""
        if self.index >= len(self.data_list):
            return None
        
        data = self.data_list[self.index]
        self.index += 1
        return data
    
    def rewind(self):
        """Reset to beginning of data."""
        self.index = 0
    
    @classmethod
    def from_numpy(
        cls,
        data: np.ndarray,
        input_name: str = "input",
    ) -> "CalibrationDataReader":
        """
        Create reader from numpy array.
        
        Args:
            data: Array of shape (N, ...) where N is number of samples
            input_name: Name of input tensor
        
        Returns:
            CalibrationDataReader instance
        """
        data_list = [{input_name: data[i:i+1].astype(np.float32)} 
                     for i in range(len(data))]
        return cls(data_list)
    
    @classmethod
    def from_dataloader(
        cls,
        dataloader,
        input_name: str = "input",
        num_samples: int = 100,
    ) -> "CalibrationDataReader":
        """
        Create reader from PyTorch DataLoader.
        
        Args:
            dataloader: PyTorch DataLoader
            input_name: Name of input tensor
            num_samples: Number of samples to use for calibration
        
        Returns:
            CalibrationDataReader instance
        """
        data_list = []
        count = 0
        
        for batch in dataloader:
            if isinstance(batch, (tuple, list)):
                inputs = batch[0]  # Assume first element is input
            else:
                inputs = batch
            
            # Convert each sample
            for i in range(len(inputs)):
                if count >= num_samples:
                    break
                    
                sample = inputs[i:i+1].numpy().astype(np.float32)
                data_list.append({input_name: sample})
                count += 1
            
            if count >= num_samples:
                break
        
        return cls(data_list)


class PyTorchQuantizer:
    """
    Quantizes PyTorch models directly (before ONNX export).
    
    This can provide better accuracy than post-export quantization
    because PyTorch can optimize quantization during export.
    """
    
    @staticmethod
    def quantize_dynamic_pytorch(
        model,
        dtype=None,
    ):
        """
        Apply dynamic quantization to PyTorch model.
        
        Args:
            model: PyTorch model
            dtype: Quantization dtype (default: qint8)
        
        Returns:
            Quantized PyTorch model
        """
        
        import torch
        
        if dtype is None:
            dtype = torch.qint8
        
        # Quantize linear and LSTM layers
        quantized_model = torch.quantization.quantize_dynamic(
            model,
            {torch.nn.Linear, torch.nn.LSTM, torch.nn.GRU},
            dtype=dtype
        )
        
        return quantized_model
    
    @staticmethod
    def prepare_qat(model, qconfig=None):
        """
        Prepare model for Quantization-Aware Training.
        
        QAT simulates quantization during training, resulting in
        better accuracy than post-training quantization.
        
        Args:
            model: PyTorch model
            qconfig: Quantization configuration
        
        Returns:
            Model prepared for QAT
        """
        
        import torch
        
        if qconfig is None:
            qconfig = torch.quantization.get_default_qat_qconfig('fbgemm')
        
        model.qconfig = qconfig
        
        # Fuse modules
        model_fused = torch.quantization.fuse_modules(
            model,
            [['conv', 'bn', 'relu']],  # Modules to fuse
            inplace=False
        )
        
        # Prepare for QAT
        model_prepared = torch.quantization.prepare_qat(model_fused)
        
        return model_prepared
    
    @staticmethod
    def convert_qat(model):
        """
        Convert QAT-trained model to quantized model.
        
        Call this after QAT training is complete.
        
        Args:
            model: QAT-prepared model after training
        
        Returns:
            Fully quantized model
        """
        
        import torch
        
        model.eval()
        quantized_model = torch.quantization.convert(model)
        
        return quantized_model


def compare_model_outputs(
    original_path: str,
    quantized_path: str,
    test_inputs: np.ndarray,
) -> Dict[str, float]:
    """
    Compare outputs between original and quantized models.
    
    Args:
        original_path: Path to original ONNX model
        quantized_path: Path to quantized ONNX model
        test_inputs: Test input data
    
    Returns:
        Dict with accuracy metrics
    """
    
    import onnxruntime as ort
    
    # Load models
    original_session = ort.InferenceSession(
        original_path, providers=['CPUExecutionProvider']
    )
    quantized_session = ort.InferenceSession(
        quantized_path, providers=['CPUExecutionProvider']
    )
    
    input_name = original_session.get_inputs()[0].name
    
    # Run inference
    all_diffs = []
    
    for i in range(len(test_inputs)):
        input_data = test_inputs[i:i+1].astype(np.float32)
        
        original_output = original_session.run(None, {input_name: input_data})[0]
        quantized_output = quantized_session.run(None, {input_name: input_data})[0]
        
        diff = np.abs(original_output - quantized_output)
        all_diffs.append(diff)
    
    all_diffs = np.concatenate(all_diffs)
    
    return {
        "max_absolute_error": float(np.max(all_diffs)),
        "mean_absolute_error": float(np.mean(all_diffs)),
        "std_absolute_error": float(np.std(all_diffs)),
        "relative_error_pct": float(np.mean(all_diffs) / (np.mean(np.abs(original_output)) + 1e-10) * 100),
    }


# Example usage
if __name__ == "__main__":
    # Example: Quantize an ONNX model
    quantizer = ModelQuantizer()
    
    # Assume we have a model at models/resnet18.onnx
    # result = quantizer.quantize_dynamic(
    #     model_path="models/resnet18.onnx",
    #     output_path="models/resnet18_int8.onnx"
    # )
    # print(f"Quantization result: {result}")
    
    print("Quantization module ready")
    print("Supported methods:")
    print("  - quantize_dynamic(): No calibration needed, good for varying inputs")
    print("  - quantize_static(): Best accuracy with calibration data")
    print("  - quantize_fp16(): ~2x smaller, minimal accuracy loss")
