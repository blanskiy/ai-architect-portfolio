"""
Model Manager
Handles model loading, prediction, and lifecycle.

Supports:
- Joblib/Pickle models (scikit-learn)
- ONNX models (cross-platform)
- PyTorch models
- Model versioning
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional, Any, Union
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PredictionInput:
    """Input for model prediction."""
    features: list[float]
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array."""
        return np.array(self.features).reshape(1, -1)


@dataclass
class PredictionOutput:
    """Output from model prediction."""
    prediction: Union[float, int, list]
    probability: Optional[list[float]] = None
    model_version: str = "unknown"


class ModelManager:
    """
    Manages ML model lifecycle.
    
    Responsibilities:
    - Load model from disk or remote storage
    - Provide prediction interface
    - Handle model versioning
    - Graceful unloading
    
    Usage:
        manager = ModelManager(model_path="/app/models", model_name="model.joblib")
        manager.load_model()
        
        input_data = PredictionInput(features=[0.5, 0.3, 0.2])
        output = manager.predict(input_data)
    """
    
    def __init__(
        self,
        model_path: str,
        model_name: str = "model.joblib",
        model_version: str = "v1",
    ):
        self.model_path = Path(model_path)
        self.model_name = model_name
        self.model_version = model_version
        self.model: Optional[Any] = None
        self.model_type: Optional[str] = None
        self._is_loaded = False
    
    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._is_loaded
    
    def load_model(self):
        """
        Load model from disk.
        
        Automatically detects model type based on file extension.
        """
        model_file = self.model_path / self.model_name
        
        if not model_file.exists():
            # For demo/testing, create a simple model
            logger.warning(f"Model file not found: {model_file}. Creating demo model.")
            self._create_demo_model()
            return
        
        extension = model_file.suffix.lower()
        
        logger.info(f"Loading model from {model_file}")
        
        try:
            if extension in ['.joblib', '.pkl', '.pickle']:
                self._load_sklearn_model(model_file)
            elif extension == '.onnx':
                self._load_onnx_model(model_file)
            elif extension in ['.pt', '.pth']:
                self._load_pytorch_model(model_file)
            else:
                raise ValueError(f"Unsupported model format: {extension}")
            
            self._is_loaded = True
            logger.info(f"Model loaded successfully. Type: {self.model_type}")
        
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def _load_sklearn_model(self, model_file: Path):
        """Load scikit-learn model."""
        import joblib
        
        self.model = joblib.load(model_file)
        self.model_type = "sklearn"
    
    def _load_onnx_model(self, model_file: Path):
        """Load ONNX model."""
        import onnxruntime as ort
        
        self.model = ort.InferenceSession(
            str(model_file),
            providers=['CPUExecutionProvider']
        )
        self.model_type = "onnx"
    
    def _load_pytorch_model(self, model_file: Path):
        """Load PyTorch model."""
        import torch
        
        self.model = torch.jit.load(model_file)
        self.model.eval()
        self.model_type = "pytorch"
    
    def _create_demo_model(self):
        """Create a simple demo model for testing."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.datasets import make_classification
        import joblib
        
        logger.info("Creating demo RandomForest model...")
        
        # Generate synthetic data
        X, y = make_classification(
            n_samples=1000,
            n_features=5,
            n_informative=3,
            n_redundant=1,
            random_state=42
        )
        
        # Train simple model
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)
        
        # Save model
        self.model_path.mkdir(parents=True, exist_ok=True)
        model_file = self.model_path / self.model_name
        joblib.dump(model, model_file)
        
        # Load it back
        self.model = model
        self.model_type = "sklearn"
        self._is_loaded = True
        
        logger.info(f"Demo model created and saved to {model_file}")
    
    def predict(self, input_data: PredictionInput) -> PredictionOutput:
        """
        Make prediction using loaded model.
        
        Args:
            input_data: PredictionInput with features
        
        Returns:
            PredictionOutput with prediction and probabilities
        """
        if not self._is_loaded:
            raise RuntimeError("Model not loaded")
        
        features = input_data.to_array()
        
        if self.model_type == "sklearn":
            return self._predict_sklearn(features)
        elif self.model_type == "onnx":
            return self._predict_onnx(features)
        elif self.model_type == "pytorch":
            return self._predict_pytorch(features)
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
    
    def _predict_sklearn(self, features: np.ndarray) -> PredictionOutput:
        """Prediction for sklearn models."""
        prediction = self.model.predict(features)[0]
        
        # Get probabilities if available
        probability = None
        if hasattr(self.model, 'predict_proba'):
            probability = self.model.predict_proba(features)[0].tolist()
        
        return PredictionOutput(
            prediction=int(prediction) if isinstance(prediction, (np.integer, int)) else float(prediction),
            probability=probability,
            model_version=self.model_version,
        )
    
    def _predict_onnx(self, features: np.ndarray) -> PredictionOutput:
        """Prediction for ONNX models."""
        input_name = self.model.get_inputs()[0].name
        
        # ONNX expects float32
        features = features.astype(np.float32)
        
        outputs = self.model.run(None, {input_name: features})
        prediction = outputs[0][0]
        
        # Second output is usually probabilities
        probability = None
        if len(outputs) > 1:
            probability = outputs[1][0].tolist()
        
        return PredictionOutput(
            prediction=prediction.item() if hasattr(prediction, 'item') else prediction,
            probability=probability,
            model_version=self.model_version,
        )
    
    def _predict_pytorch(self, features: np.ndarray) -> PredictionOutput:
        """Prediction for PyTorch models."""
        import torch
        
        with torch.no_grad():
            tensor = torch.FloatTensor(features)
            output = self.model(tensor)
            
            # Assuming classification with softmax
            probabilities = torch.softmax(output, dim=1)
            prediction = torch.argmax(probabilities, dim=1)
            
            return PredictionOutput(
                prediction=prediction.item(),
                probability=probabilities[0].tolist(),
                model_version=self.model_version,
            )
    
    def unload_model(self):
        """Unload model and free resources."""
        logger.info("Unloading model...")
        
        if self.model_type == "pytorch":
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        
        self.model = None
        self._is_loaded = False
        
        logger.info("Model unloaded")
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "model_type": self.model_type,
            "model_path": str(self.model_path),
            "is_loaded": self._is_loaded,
        }


# ============================================================================
# Model Registry Integration (optional)
# ============================================================================

class ModelRegistry:
    """
    Interface to MLflow Model Registry or similar.
    
    Can download models from registry instead of loading from disk.
    """
    
    def __init__(self, registry_uri: str):
        self.registry_uri = registry_uri
    
    def download_model(
        self,
        model_name: str,
        version: str = "latest",
        destination: str = "/app/models"
    ) -> str:
        """
        Download model from registry.
        
        Returns path to downloaded model.
        """
        # This would integrate with MLflow or Azure ML
        # For now, just return the expected path
        import mlflow
        
        mlflow.set_tracking_uri(self.registry_uri)
        
        if version == "latest":
            model_uri = f"models:/{model_name}/Production"
        else:
            model_uri = f"models:/{model_name}/{version}"
        
        local_path = mlflow.artifacts.download_artifacts(model_uri, dst_path=destination)
        
        return local_path


# Example usage
if __name__ == "__main__":
    # Test the model manager
    manager = ModelManager(
        model_path="./models",
        model_name="model.joblib",
        model_version="v1"
    )
    
    # Load model (will create demo if not exists)
    manager.load_model()
    
    # Make prediction
    input_data = PredictionInput(features=[0.5, 0.3, 0.2, 0.8, 0.1])
    output = manager.predict(input_data)
    
    print(f"Prediction: {output.prediction}")
    print(f"Probability: {output.probability}")
    print(f"Model Version: {output.model_version}")
    
    # Get model info
    print(f"Model Info: {manager.get_model_info()}")
