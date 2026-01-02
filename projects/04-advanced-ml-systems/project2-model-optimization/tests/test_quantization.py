"""
Tests for Model Quantization
"""

import pytest
import torch
import torch.nn as nn
import numpy as np
from pathlib import Path
import sys
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'models'))

from onnx_converter import ONNXConverter
from quantization import (
    ModelQuantizer,
    QuantizationConfig,
    CalibrationDataReader,
    compare_model_outputs,
)
from sample_model import SimpleCNN


class TestQuantization:
    """Tests for model quantization."""
    
    @pytest.fixture
    def onnx_model_path(self, tmp_path):
        """Create an ONNX model for testing."""
        model = SimpleCNN(num_classes=10)
        model.eval()
        
        output_path = str(tmp_path / "test_model.onnx")
        
        converter = ONNXConverter()
        converter.convert(model, output_path, (1, 3, 32, 32))
        
        return output_path
    
    @pytest.fixture
    def quantizer(self):
        """Create quantizer instance."""
        return ModelQuantizer()
    
    def test_dynamic_quantization(self, onnx_model_path, quantizer, tmp_path):
        """Test dynamic INT8 quantization."""
        output_path = str(tmp_path / "model_int8.onnx")
        
        result = quantizer.quantize_dynamic(
            model_path=onnx_model_path,
            output_path=output_path,
        )
        
        # Check output exists
        assert Path(output_path).exists()
        
        # Check size reduction
        assert result["compression_ratio"] > 1.0
        assert result["quantized_size_mb"] < result["original_size_mb"]
    
    def test_dynamic_quantization_size_reduction(self, onnx_model_path, quantizer, tmp_path):
        """Test that INT8 quantization reduces size by ~4x."""
        output_path = str(tmp_path / "model_int8.onnx")
        
        result = quantizer.quantize_dynamic(
            model_path=onnx_model_path,
            output_path=output_path,
        )
        
        # INT8 should give roughly 3-4x compression
        assert result["compression_ratio"] > 2.0
        assert result["compression_ratio"] < 5.0
    
    def test_quantized_model_inference(self, onnx_model_path, quantizer, tmp_path):
        """Test that quantized model can run inference."""
        import onnxruntime as ort
        
        output_path = str(tmp_path / "model_int8.onnx")
        quantizer.quantize_dynamic(onnx_model_path, output_path)
        
        # Run inference on quantized model
        session = ort.InferenceSession(output_path, providers=['CPUExecutionProvider'])
        input_name = session.get_inputs()[0].name
        
        test_input = np.random.randn(1, 3, 32, 32).astype(np.float32)
        output = session.run(None, {input_name: test_input})
        
        assert output[0].shape == (1, 10)
    
    def test_output_comparison(self, onnx_model_path, quantizer, tmp_path):
        """Test comparing original vs quantized outputs."""
        quantized_path = str(tmp_path / "model_int8.onnx")
        quantizer.quantize_dynamic(onnx_model_path, quantized_path)
        
        # Generate test data
        test_inputs = np.random.randn(10, 3, 32, 32).astype(np.float32)
        
        # Compare outputs
        metrics = compare_model_outputs(
            onnx_model_path,
            quantized_path,
            test_inputs,
        )
        
        # Quantization should have some error but not too much
        assert "max_absolute_error" in metrics
        assert "mean_absolute_error" in metrics
        
        # Typical INT8 quantization error
        assert metrics["mean_absolute_error"] < 1.0  # Should be small


class TestCalibrationDataReader:
    """Tests for calibration data reader."""
    
    def test_from_numpy(self):
        """Test creating reader from numpy array."""
        data = np.random.randn(100, 3, 32, 32).astype(np.float32)
        
        reader = CalibrationDataReader.from_numpy(data, input_name="input")
        
        # Should be able to iterate through data
        count = 0
        while reader.get_next() is not None:
            count += 1
        
        assert count == 100
    
    def test_rewind(self):
        """Test rewinding the reader."""
        data = np.random.randn(10, 3, 32, 32).astype(np.float32)
        
        reader = CalibrationDataReader.from_numpy(data, input_name="input")
        
        # Read all data
        while reader.get_next() is not None:
            pass
        
        # Rewind
        reader.rewind()
        
        # Should be able to read again
        sample = reader.get_next()
        assert sample is not None
        assert "input" in sample
    
    def test_correct_shape(self):
        """Test that samples have correct shape."""
        data = np.random.randn(10, 3, 32, 32).astype(np.float32)
        
        reader = CalibrationDataReader.from_numpy(data, input_name="input")
        
        sample = reader.get_next()
        
        assert sample["input"].shape == (1, 3, 32, 32)


class TestQuantizationAccuracy:
    """Tests for quantization accuracy impact."""
    
    @pytest.fixture
    def model_and_data(self, tmp_path):
        """Create model and test data."""
        model = SimpleCNN(num_classes=10)
        model.eval()
        
        # Export to ONNX
        onnx_path = str(tmp_path / "model.onnx")
        converter = ONNXConverter()
        converter.convert(model, onnx_path, (1, 3, 32, 32))
        
        # Generate test data
        test_data = np.random.randn(100, 3, 32, 32).astype(np.float32)
        
        return onnx_path, test_data, tmp_path
    
    def test_int8_accuracy_degradation(self, model_and_data):
        """Test that INT8 quantization has acceptable accuracy."""
        import onnxruntime as ort
        
        onnx_path, test_data, tmp_path = model_and_data
        
        # Quantize
        quantizer = ModelQuantizer()
        int8_path = str(tmp_path / "model_int8.onnx")
        quantizer.quantize_dynamic(onnx_path, int8_path)
        
        # Compare outputs
        original_session = ort.InferenceSession(onnx_path, providers=['CPUExecutionProvider'])
        int8_session = ort.InferenceSession(int8_path, providers=['CPUExecutionProvider'])
        
        input_name = original_session.get_inputs()[0].name
        
        # Calculate accuracy on classification task
        matches = 0
        for i in range(len(test_data)):
            input_sample = test_data[i:i+1]
            
            original_out = original_session.run(None, {input_name: input_sample})[0]
            int8_out = int8_session.run(None, {input_name: input_sample})[0]
            
            original_pred = np.argmax(original_out)
            int8_pred = np.argmax(int8_out)
            
            if original_pred == int8_pred:
                matches += 1
        
        accuracy = matches / len(test_data)
        
        # INT8 should preserve most predictions
        assert accuracy > 0.95, f"INT8 accuracy too low: {accuracy}"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
