"""
ONNX Converter
Convert PyTorch models to ONNX format for optimized inference.

ONNX (Open Neural Network Exchange) provides:
- Cross-platform deployment (works on any hardware)
- Graph optimizations (constant folding, operator fusion)
- 2-3x speedup over native PyTorch inference
- No accuracy loss
"""

import os
import logging
from pathlib import Path
from typing import Optional, Union, Tuple, List, Dict, Any
from dataclasses import dataclass

import torch
import torch.nn as nn
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ONNXExportConfig:
    """Configuration for ONNX export."""
    opset_version: int = 17
    do_constant_folding: bool = True
    export_params: bool = True
    verbose: bool = False
    
    # Dynamic axes for variable batch size
    dynamic_batch: bool = True
    
    # Optimization level for ONNX Runtime
    # 0 = no optimization, 1 = basic, 2 = extended, 99 = all
    optimization_level: int = 99


class ONNXConverter:
    """
    Converts PyTorch models to ONNX format.
    
    Usage:
        converter = ONNXConverter()
        
        # Basic conversion
        converter.convert(
            model=my_model,
            output_path="model.onnx",
            input_shape=(1, 3, 224, 224)
        )
        
        # With validation
        converter.convert_and_validate(
            model=my_model,
            output_path="model.onnx",
            input_shape=(1, 3, 224, 224),
            test_input=sample_input
        )
    """
    
    def __init__(self, config: Optional[ONNXExportConfig] = None):
        self.config = config or ONNXExportConfig()
    
    def convert(
        self,
        model: nn.Module,
        output_path: str,
        input_shape: Tuple[int, ...],
        input_names: List[str] = None,
        output_names: List[str] = None,
    ) -> str:
        """
        Convert PyTorch model to ONNX format.
        
        Args:
            model: PyTorch model (must be in eval mode)
            output_path: Path to save ONNX model
            input_shape: Shape of input tensor (batch, channels, height, width)
            input_names: Names for input tensors
            output_names: Names for output tensors
        
        Returns:
            Path to saved ONNX model
        """
        
        logger.info(f"Converting model to ONNX: {output_path}")
        
        # Ensure model is in eval mode
        model.eval()
        
        # Create dummy input
        dummy_input = torch.randn(*input_shape)
        
        # Default names
        if input_names is None:
            input_names = ['input']
        if output_names is None:
            output_names = ['output']
        
        # Build dynamic axes
        dynamic_axes = None
        if self.config.dynamic_batch:
            dynamic_axes = {
                input_names[0]: {0: 'batch_size'},
                output_names[0]: {0: 'batch_size'},
            }
        
        # Create output directory
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Export to ONNX
        try:
            torch.onnx.export(
                model,
                dummy_input,
                output_path,
                export_params=self.config.export_params,
                opset_version=self.config.opset_version,
                do_constant_folding=self.config.do_constant_folding,
                input_names=input_names,
                output_names=output_names,
                dynamic_axes=dynamic_axes,
                verbose=self.config.verbose,
            )
            
            logger.info(f"Successfully exported ONNX model to {output_path}")
            
            # Get file size
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            logger.info(f"Model size: {size_mb:.2f} MB")
            
            return output_path
            
        except Exception as e:
            logger.error(f"ONNX export failed: {e}")
            raise
    
    def validate_onnx_model(self, onnx_path: str) -> bool:
        """
        Validate ONNX model structure.
        
        Args:
            onnx_path: Path to ONNX model
        
        Returns:
            True if model is valid
        """
        
        import onnx
        
        try:
            # Load and check model
            model = onnx.load(onnx_path)
            onnx.checker.check_model(model)
            
            logger.info(f"ONNX model validation passed: {onnx_path}")
            return True
            
        except Exception as e:
            logger.error(f"ONNX model validation failed: {e}")
            return False
    
    def convert_and_validate(
        self,
        model: nn.Module,
        output_path: str,
        input_shape: Tuple[int, ...],
        test_input: Optional[torch.Tensor] = None,
        rtol: float = 1e-3,
        atol: float = 1e-5,
    ) -> Dict[str, Any]:
        """
        Convert model and validate outputs match.
        
        Args:
            model: PyTorch model
            output_path: Path to save ONNX model
            input_shape: Input tensor shape
            test_input: Optional test input for validation
            rtol: Relative tolerance for output comparison
            atol: Absolute tolerance for output comparison
        
        Returns:
            Dict with conversion results and validation metrics
        """
        
        import onnxruntime as ort
        
        # Convert
        self.convert(model, output_path, input_shape)
        
        # Validate structure
        if not self.validate_onnx_model(output_path):
            return {"success": False, "error": "ONNX validation failed"}
        
        # Prepare test input
        if test_input is None:
            test_input = torch.randn(*input_shape)
        
        # Get PyTorch output
        model.eval()
        with torch.no_grad():
            pytorch_output = model(test_input).numpy()
        
        # Get ONNX output
        session = ort.InferenceSession(
            output_path,
            providers=['CPUExecutionProvider']
        )
        
        input_name = session.get_inputs()[0].name
        onnx_output = session.run(None, {input_name: test_input.numpy()})[0]
        
        # Compare outputs
        max_diff = np.max(np.abs(pytorch_output - onnx_output))
        mean_diff = np.mean(np.abs(pytorch_output - onnx_output))
        
        outputs_match = np.allclose(pytorch_output, onnx_output, rtol=rtol, atol=atol)
        
        result = {
            "success": True,
            "outputs_match": outputs_match,
            "max_difference": float(max_diff),
            "mean_difference": float(mean_diff),
            "model_path": output_path,
            "model_size_mb": os.path.getsize(output_path) / (1024 * 1024),
        }
        
        if outputs_match:
            logger.info(f"Output validation passed. Max diff: {max_diff:.6f}")
        else:
            logger.warning(f"Output validation failed. Max diff: {max_diff:.6f}")
        
        return result
    
    def optimize_onnx_model(
        self,
        input_path: str,
        output_path: str,
    ) -> str:
        """
        Apply ONNX graph optimizations.
        
        Optimizations include:
        - Constant folding
        - Redundant node elimination
        - Operator fusion
        
        Args:
            input_path: Path to input ONNX model
            output_path: Path to save optimized model
        
        Returns:
            Path to optimized model
        """
        
        import onnxruntime as ort
        from onnxruntime.transformers import optimizer
        
        logger.info(f"Optimizing ONNX model: {input_path}")
        
        # Create session options with optimization
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.optimized_model_filepath = output_path
        
        # Create session (this triggers optimization and saves)
        _ = ort.InferenceSession(
            input_path,
            sess_options,
            providers=['CPUExecutionProvider']
        )
        
        # Compare sizes
        original_size = os.path.getsize(input_path) / (1024 * 1024)
        optimized_size = os.path.getsize(output_path) / (1024 * 1024)
        
        logger.info(f"Original size: {original_size:.2f} MB")
        logger.info(f"Optimized size: {optimized_size:.2f} MB")
        logger.info(f"Size reduction: {(1 - optimized_size/original_size) * 100:.1f}%")
        
        return output_path
    
    def get_model_info(self, onnx_path: str) -> Dict[str, Any]:
        """
        Get information about ONNX model.
        
        Args:
            onnx_path: Path to ONNX model
        
        Returns:
            Dict with model information
        """
        
        import onnx
        
        model = onnx.load(onnx_path)
        
        # Count parameters
        total_params = 0
        for initializer in model.graph.initializer:
            params = 1
            for dim in initializer.dims:
                params *= dim
            total_params += params
        
        # Get input/output info
        inputs = []
        for inp in model.graph.input:
            shape = [d.dim_value for d in inp.type.tensor_type.shape.dim]
            inputs.append({"name": inp.name, "shape": shape})
        
        outputs = []
        for out in model.graph.output:
            shape = [d.dim_value for d in out.type.tensor_type.shape.dim]
            outputs.append({"name": out.name, "shape": shape})
        
        # Count operators
        op_counts = {}
        for node in model.graph.node:
            op_type = node.op_type
            op_counts[op_type] = op_counts.get(op_type, 0) + 1
        
        return {
            "opset_version": model.opset_import[0].version,
            "total_parameters": total_params,
            "inputs": inputs,
            "outputs": outputs,
            "operator_counts": op_counts,
            "num_nodes": len(model.graph.node),
            "file_size_mb": os.path.getsize(onnx_path) / (1024 * 1024),
        }


class ONNXInferenceSession:
    """
    Wrapper for ONNX Runtime inference.
    
    Usage:
        session = ONNXInferenceSession("model.onnx")
        output = session.predict(input_array)
    """
    
    def __init__(
        self,
        model_path: str,
        providers: List[str] = None,
        num_threads: int = None,
    ):
        """
        Initialize ONNX Runtime session.
        
        Args:
            model_path: Path to ONNX model
            providers: Execution providers (default: CPU)
            num_threads: Number of threads for inference
        """
        
        import onnxruntime as ort
        
        if providers is None:
            # Check for GPU availability
            available_providers = ort.get_available_providers()
            if 'CUDAExecutionProvider' in available_providers:
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            else:
                providers = ['CPUExecutionProvider']
        
        # Session options
        sess_options = ort.SessionOptions()
        if num_threads:
            sess_options.intra_op_num_threads = num_threads
            sess_options.inter_op_num_threads = num_threads
        
        # Enable optimizations
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        self.session = ort.InferenceSession(
            model_path,
            sess_options,
            providers=providers
        )
        
        # Get input/output names
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [o.name for o in self.session.get_outputs()]
        
        logger.info(f"Loaded ONNX model: {model_path}")
        logger.info(f"Providers: {self.session.get_providers()}")
    
    def predict(self, input_data: np.ndarray) -> np.ndarray:
        """
        Run inference.
        
        Args:
            input_data: Input array
        
        Returns:
            Model output
        """
        
        # Ensure correct dtype
        if input_data.dtype != np.float32:
            input_data = input_data.astype(np.float32)
        
        outputs = self.session.run(
            self.output_names,
            {self.input_name: input_data}
        )
        
        return outputs[0]
    
    def predict_batch(
        self,
        inputs: List[np.ndarray],
        batch_size: int = 32,
    ) -> List[np.ndarray]:
        """
        Run batched inference.
        
        Args:
            inputs: List of input arrays
            batch_size: Batch size for inference
        
        Returns:
            List of outputs
        """
        
        outputs = []
        
        for i in range(0, len(inputs), batch_size):
            batch = inputs[i:i + batch_size]
            batch_array = np.stack(batch)
            batch_output = self.predict(batch_array)
            outputs.extend(batch_output)
        
        return outputs


# Example usage
if __name__ == "__main__":
    import torchvision.models as models
    
    # Load a pretrained model
    model = models.resnet18(pretrained=True)
    model.eval()
    
    # Convert to ONNX
    converter = ONNXConverter()
    
    result = converter.convert_and_validate(
        model=model,
        output_path="models/resnet18.onnx",
        input_shape=(1, 3, 224, 224),
    )
    
    print(f"Conversion result: {result}")
    
    # Get model info
    info = converter.get_model_info("models/resnet18.onnx")
    print(f"Model info: {info}")
