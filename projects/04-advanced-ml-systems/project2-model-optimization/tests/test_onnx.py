"""
Tests for ONNX Conversion
"""

import pytest
import torch
import torch.nn as nn
import numpy as np
from pathlib import Path
import sys
import tempfile

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'models'))

from onnx_converter import ONNXConverter, ONNXExportConfig, ONNXInferenceSession
from sample_model import SimpleCNN, SimpleImageClassifier


class TestONNXConverter:
    """Tests for ONNX conversion."""
    
    @pytest.fixture
    def simple_model(self):
        """Create a simple model for testing."""
        model = SimpleCNN(num_classes=10)
        model.eval()
        return model
    
    @pytest.fixture
    def converter(self):
        """Create converter instance."""
        return ONNXConverter()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for outputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_basic_conversion(self, simple_model, converter, temp_dir):
        """Test basic PyTorch to ONNX conversion."""
        output_path = f"{temp_dir}/model.onnx"
        
        result = converter.convert(
            model=simple_model,
            output_path=output_path,
            input_shape=(1, 3, 32, 32),
        )
        
        assert Path(output_path).exists()
        assert Path(output_path).stat().st_size > 0
    
    def test_output_validation(self, simple_model, converter, temp_dir):
        """Test that ONNX output matches PyTorch output."""
        output_path = f"{temp_dir}/model.onnx"
        test_input = torch.randn(1, 3, 32, 32)
        
        result = converter.convert_and_validate(
            model=simple_model,
            output_path=output_path,
            input_shape=(1, 3, 32, 32),
            test_input=test_input,
        )
        
        assert result["success"]
        assert result["outputs_match"]
        assert result["max_difference"] < 1e-4
    
    def test_dynamic_batch_size(self, simple_model, converter, temp_dir):
        """Test that model supports dynamic batch sizes."""
        output_path = f"{temp_dir}/model.onnx"
        
        converter.convert(
            model=simple_model,
            output_path=output_path,
            input_shape=(1, 3, 32, 32),
        )
        
        # Create session
        session = ONNXInferenceSession(output_path)
        
        # Test different batch sizes
        for batch_size in [1, 4, 8]:
            input_data = np.random.randn(batch_size, 3, 32, 32).astype(np.float32)
            output = session.predict(input_data)
            assert output.shape[0] == batch_size
    
    def test_model_info(self, simple_model, converter, temp_dir):
        """Test getting model information."""
        output_path = f"{temp_dir}/model.onnx"
        
        converter.convert(
            model=simple_model,
            output_path=output_path,
            input_shape=(1, 3, 32, 32),
        )
        
        info = converter.get_model_info(output_path)
        
        assert "total_parameters" in info
        assert info["total_parameters"] > 0
        assert "inputs" in info
        assert "outputs" in info
        assert "file_size_mb" in info
    
    def test_validation_fails_on_mismatch(self, converter, temp_dir):
        """Test that validation catches mismatched outputs."""
        # Create two different models
        model1 = SimpleCNN(num_classes=10)
        model1.eval()
        
        model2 = SimpleCNN(num_classes=5)  # Different output size
        model2.eval()
        
        path1 = f"{temp_dir}/model1.onnx"
        path2 = f"{temp_dir}/model2.onnx"
        
        converter.convert(model1, path1, (1, 3, 32, 32))
        converter.convert(model2, path2, (1, 3, 32, 32))
        
        # Models should have different outputs
        import onnxruntime as ort
        
        session1 = ort.InferenceSession(path1, providers=['CPUExecutionProvider'])
        session2 = ort.InferenceSession(path2, providers=['CPUExecutionProvider'])
        
        test_input = np.random.randn(1, 3, 32, 32).astype(np.float32)
        
        out1 = session1.run(None, {"input": test_input})[0]
        out2 = session2.run(None, {"input": test_input})[0]
        
        assert out1.shape != out2.shape


class TestONNXInferenceSession:
    """Tests for ONNX inference session wrapper."""
    
    @pytest.fixture
    def onnx_model_path(self, tmp_path):
        """Create an ONNX model for testing."""
        model = SimpleCNN(num_classes=10)
        model.eval()
        
        output_path = str(tmp_path / "test_model.onnx")
        
        converter = ONNXConverter()
        converter.convert(model, output_path, (1, 3, 32, 32))
        
        return output_path
    
    def test_single_prediction(self, onnx_model_path):
        """Test single sample prediction."""
        session = ONNXInferenceSession(onnx_model_path)
        
        input_data = np.random.randn(1, 3, 32, 32).astype(np.float32)
        output = session.predict(input_data)
        
        assert output.shape == (1, 10)
    
    def test_batch_prediction(self, onnx_model_path):
        """Test batch prediction."""
        session = ONNXInferenceSession(onnx_model_path)
        
        # Create list of inputs
        inputs = [np.random.randn(3, 32, 32).astype(np.float32) for _ in range(10)]
        
        outputs = session.predict_batch(inputs, batch_size=4)
        
        assert len(outputs) == 10
    
    def test_dtype_conversion(self, onnx_model_path):
        """Test that non-float32 inputs are converted."""
        session = ONNXInferenceSession(onnx_model_path)
        
        # Float64 input should be converted
        input_data = np.random.randn(1, 3, 32, 32).astype(np.float64)
        output = session.predict(input_data)
        
        assert output.shape == (1, 10)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
