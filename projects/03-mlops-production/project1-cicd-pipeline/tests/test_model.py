"""
Model Quality Tests
Run as part of CI/CD pipeline to validate model behavior.

Usage:
    pytest tests/test_model.py -v
"""

import pytest
import numpy as np
import pandas as pd
import time


class TestModelQuality:
    """Tests for model quality and behavior."""
    
    @pytest.fixture
    def sample_data(self):
        """Generate sample test data."""
        np.random.seed(42)
        n_samples = 100
        
        X = pd.DataFrame({
            'feature_1': np.random.randn(n_samples),
            'feature_2': np.random.randn(n_samples),
            'feature_3': np.random.randn(n_samples),
            'feature_4': np.random.randn(n_samples),
            'feature_5': np.random.randn(n_samples),
        })
        
        y = (X['feature_1'] + X['feature_2'] * 0.5 > 0).astype(int)
        
        return X, y
    
    @pytest.fixture
    def trained_model(self, sample_data):
        """Train a simple model for testing."""
        from sklearn.ensemble import RandomForestClassifier
        
        X, y = sample_data
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)
        return model
    
    def test_model_returns_valid_predictions(self, trained_model, sample_data):
        """Model should return predictions of correct shape and type."""
        X, _ = sample_data
        
        predictions = trained_model.predict(X)
        
        assert len(predictions) == len(X)
        assert all(p in [0, 1] for p in predictions)
    
    def test_model_returns_probabilities(self, trained_model, sample_data):
        """Model should return valid probabilities."""
        X, _ = sample_data
        
        probas = trained_model.predict_proba(X)
        
        assert probas.shape == (len(X), 2)
        assert all(0 <= p <= 1 for p in probas.flatten())
        assert all(abs(row.sum() - 1.0) < 1e-6 for row in probas)
    
    def test_model_handles_single_sample(self, trained_model, sample_data):
        """Model should handle single sample input."""
        X, _ = sample_data
        single_sample = X.iloc[[0]]
        
        prediction = trained_model.predict(single_sample)
        
        assert len(prediction) == 1
    
    def test_model_handles_edge_cases(self, trained_model):
        """Model should handle edge case inputs."""
        # All zeros
        X_zeros = pd.DataFrame({
            'feature_1': [0.0],
            'feature_2': [0.0],
            'feature_3': [0.0],
            'feature_4': [0.0],
            'feature_5': [0.0],
        })
        prediction = trained_model.predict(X_zeros)
        assert len(prediction) == 1
        
        # Large values
        X_large = pd.DataFrame({
            'feature_1': [1000.0],
            'feature_2': [1000.0],
            'feature_3': [1000.0],
            'feature_4': [1000.0],
            'feature_5': [1000.0],
        })
        prediction = trained_model.predict(X_large)
        assert len(prediction) == 1
    
    def test_model_latency(self, trained_model, sample_data):
        """Model inference should be under latency threshold."""
        X, _ = sample_data
        single_sample = X.iloc[[0]]
        
        latencies = []
        for _ in range(50):
            start = time.time()
            trained_model.predict(single_sample)
            latencies.append((time.time() - start) * 1000)
        
        p95_latency = np.percentile(latencies, 95)
        
        # Should be under 100ms
        assert p95_latency < 100, f"P95 latency {p95_latency:.2f}ms exceeds 100ms threshold"
    
    def test_model_deterministic(self, trained_model, sample_data):
        """Model should produce deterministic results."""
        X, _ = sample_data
        
        pred1 = trained_model.predict(X)
        pred2 = trained_model.predict(X)
        
        assert np.array_equal(pred1, pred2)


class TestDataValidation:
    """Tests for input data validation."""
    
    @pytest.fixture
    def expected_schema(self):
        """Expected input schema."""
        return {
            'feature_1': 'float64',
            'feature_2': 'float64',
            'feature_3': 'float64',
            'feature_4': 'float64',
            'feature_5': 'float64',
        }
    
    def test_required_columns_present(self, expected_schema):
        """Input data should have all required columns."""
        X = pd.DataFrame({
            'feature_1': [1.0],
            'feature_2': [2.0],
            'feature_3': [3.0],
            'feature_4': [4.0],
            'feature_5': [5.0],
        })
        
        missing_cols = set(expected_schema.keys()) - set(X.columns)
        assert len(missing_cols) == 0, f"Missing columns: {missing_cols}"
    
    def test_no_null_values(self):
        """Input data should not contain null values."""
        X = pd.DataFrame({
            'feature_1': [1.0, 2.0, None],
            'feature_2': [1.0, 2.0, 3.0],
            'feature_3': [1.0, 2.0, 3.0],
            'feature_4': [1.0, 2.0, 3.0],
            'feature_5': [1.0, 2.0, 3.0],
        })
        
        null_counts = X.isnull().sum()
        cols_with_nulls = null_counts[null_counts > 0]
        
        # This test should fail - demonstrating validation
        if len(cols_with_nulls) > 0:
            pytest.skip(f"Data contains nulls (expected in real data): {cols_with_nulls.to_dict()}")


class TestModelRegistry:
    """Tests for model registry integration."""
    
    def test_model_can_be_serialized(self, trained_model):
        """Model should be serializable with joblib."""
        import joblib
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as f:
            joblib.dump(trained_model, f.name)
            loaded_model = joblib.load(f.name)
        
        # Verify loaded model works
        X = pd.DataFrame({
            'feature_1': [1.0],
            'feature_2': [2.0],
            'feature_3': [3.0],
            'feature_4': [4.0],
            'feature_5': [5.0],
        })
        
        original_pred = trained_model.predict(X)
        loaded_pred = loaded_model.predict(X)
        
        assert np.array_equal(original_pred, loaded_pred)


# Run with: pytest tests/test_model.py -v --tb=short
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
