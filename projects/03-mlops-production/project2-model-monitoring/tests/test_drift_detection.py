"""
Tests for Drift Detection Module
Tests PSI, KS, and Chi-Square drift detection methods.

Usage:
    pytest tests/test_drift_detection.py -v
"""

import pytest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from drift_detector import (
    calculate_psi,
    calculate_ks_statistic,
    calculate_chi_square,
    detect_feature_drift,
    detect_dataset_drift,
    detect_prediction_drift,
)


class TestPSI:
    """Tests for Population Stability Index calculation."""
    
    def test_identical_distributions_return_zero(self):
        """Identical distributions should have PSI ≈ 0."""
        np.random.seed(42)
        data = np.random.randn(1000)
        
        psi = calculate_psi(data, data)
        
        assert psi < 0.01, f"PSI should be ~0 for identical data, got {psi}"
    
    def test_similar_distributions_low_psi(self):
        """Similar distributions should have low PSI."""
        np.random.seed(42)
        reference = np.random.randn(1000)
        current = np.random.randn(1000)  # Same distribution, different samples
        
        psi = calculate_psi(reference, current)
        
        assert psi < 0.1, f"PSI should be low for similar distributions, got {psi}"
    
    def test_shifted_distribution_higher_psi(self):
        """Shifted distribution should have higher PSI."""
        np.random.seed(42)
        reference = np.random.randn(1000)
        current = np.random.randn(1000) + 2  # Shifted by 2 std
        
        psi = calculate_psi(reference, current)
        
        assert psi > 0.2, f"PSI should be high for shifted distribution, got {psi}"
    
    def test_different_variance_detectable(self):
        """Different variance should be detectable."""
        np.random.seed(42)
        reference = np.random.randn(1000)
        current = np.random.randn(1000) * 3  # 3x variance
        
        psi = calculate_psi(reference, current)
        
        assert psi > 0.1, f"PSI should detect variance change, got {psi}"


class TestKSStatistic:
    """Tests for Kolmogorov-Smirnov statistic."""
    
    def test_identical_distributions(self):
        """Identical distributions should have high p-value."""
        np.random.seed(42)
        data = np.random.randn(500)
        
        ks_stat, p_value = calculate_ks_statistic(data, data)
        
        assert p_value > 0.05, f"P-value should be > 0.05, got {p_value}"
        assert ks_stat < 0.1, f"KS stat should be low, got {ks_stat}"
    
    def test_similar_distributions_high_pvalue(self):
        """Similar distributions should have high p-value."""
        np.random.seed(42)
        reference = np.random.randn(500)
        np.random.seed(123)
        current = np.random.randn(500)
        
        ks_stat, p_value = calculate_ks_statistic(reference, current)
        
        # Should not reject null hypothesis (distributions are same)
        assert p_value > 0.01, f"P-value should be high, got {p_value}"
    
    def test_different_distributions_low_pvalue(self):
        """Different distributions should have low p-value."""
        np.random.seed(42)
        reference = np.random.randn(500)
        current = np.random.exponential(2, 500)  # Different distribution
        
        ks_stat, p_value = calculate_ks_statistic(reference, current)
        
        assert p_value < 0.05, f"P-value should be low, got {p_value}"


class TestChiSquare:
    """Tests for Chi-Square test on categorical data."""
    
    def test_identical_distributions(self):
        """Identical categorical distributions."""
        categories = ['A', 'B', 'C']
        np.random.seed(42)
        reference = pd.Series(np.random.choice(categories, 500, p=[0.5, 0.3, 0.2]))
        
        chi2, p_value = calculate_chi_square(reference, reference)
        
        assert p_value > 0.05, f"P-value should be > 0.05, got {p_value}"
    
    def test_different_distributions(self):
        """Different categorical distributions should be detected."""
        categories = ['A', 'B', 'C']
        np.random.seed(42)
        reference = pd.Series(np.random.choice(categories, 500, p=[0.5, 0.3, 0.2]))
        current = pd.Series(np.random.choice(categories, 500, p=[0.2, 0.3, 0.5]))  # Reversed
        
        chi2, p_value = calculate_chi_square(reference, current)
        
        assert p_value < 0.05, f"P-value should be low for different distributions, got {p_value}"


class TestFeatureDrift:
    """Tests for single feature drift detection."""
    
    def test_no_drift_detected(self):
        """No drift should be detected for stable feature."""
        np.random.seed(42)
        reference = pd.Series(np.random.randn(500))
        np.random.seed(123)
        current = pd.Series(np.random.randn(500))
        
        result = detect_feature_drift(reference, current, "test_feature")
        
        assert not result.drift_detected, "Should not detect drift"
        assert result.drift_score < 0.1, f"Drift score should be low, got {result.drift_score}"
    
    def test_drift_detected(self):
        """Drift should be detected for shifted feature."""
        np.random.seed(42)
        reference = pd.Series(np.random.randn(500))
        current = pd.Series(np.random.randn(500) + 3)  # Shifted
        
        result = detect_feature_drift(reference, current, "test_feature")
        
        assert result.drift_detected, "Should detect drift"
        assert result.drift_score > 0.1, f"Drift score should be high, got {result.drift_score}"
    
    def test_categorical_feature(self):
        """Should handle categorical features."""
        np.random.seed(42)
        categories = ['A', 'B', 'C']
        reference = pd.Series(np.random.choice(categories, 500))
        current = pd.Series(np.random.choice(categories, 500))
        
        result = detect_feature_drift(
            reference, current, "cat_feature",
            method='chi2'
        )
        
        assert result.test_method == 'Chi-Square'
        assert isinstance(result.drift_score, float)


class TestDatasetDrift:
    """Tests for full dataset drift detection."""
    
    @pytest.fixture
    def sample_datasets(self):
        """Generate sample reference and current datasets."""
        np.random.seed(42)
        n_samples = 500
        
        reference_df = pd.DataFrame({
            'feature_1': np.random.randn(n_samples),
            'feature_2': np.random.randn(n_samples),
            'feature_3': np.random.randn(n_samples),
        })
        
        current_df = pd.DataFrame({
            'feature_1': np.random.randn(n_samples),
            'feature_2': np.random.randn(n_samples),
            'feature_3': np.random.randn(n_samples),
        })
        
        return reference_df, current_df
    
    def test_no_overall_drift(self, sample_datasets):
        """No drift should be detected for stable data."""
        reference_df, current_df = sample_datasets
        
        report = detect_dataset_drift(reference_df, current_df)
        
        assert not report.overall_drift_detected
        assert report.overall_drift_score < 0.1
        assert report.num_features_drifted == 0
    
    def test_partial_drift(self):
        """Should detect drift in specific features."""
        np.random.seed(42)
        n_samples = 500
        
        reference_df = pd.DataFrame({
            'feature_1': np.random.randn(n_samples),
            'feature_2': np.random.randn(n_samples),
            'feature_3': np.random.randn(n_samples),
        })
        
        current_df = pd.DataFrame({
            'feature_1': np.random.randn(n_samples),
            'feature_2': np.random.randn(n_samples) + 5,  # Drifted!
            'feature_3': np.random.randn(n_samples),
        })
        
        report = detect_dataset_drift(reference_df, current_df)
        
        # Find drifted feature
        drifted_features = [
            r['feature_name'] for r in report.feature_results 
            if r['drift_detected']
        ]
        
        assert 'feature_2' in drifted_features
        assert report.num_features_drifted >= 1
    
    def test_report_structure(self, sample_datasets):
        """Report should have correct structure."""
        reference_df, current_df = sample_datasets
        
        report = detect_dataset_drift(reference_df, current_df)
        
        assert hasattr(report, 'timestamp')
        assert hasattr(report, 'overall_drift_score')
        assert hasattr(report, 'overall_drift_detected')
        assert hasattr(report, 'num_features_drifted')
        assert hasattr(report, 'total_features')
        assert hasattr(report, 'feature_results')
        assert len(report.feature_results) == 3


class TestPredictionDrift:
    """Tests for prediction drift detection."""
    
    def test_classification_no_drift(self):
        """No drift in classification predictions."""
        np.random.seed(42)
        reference = np.random.choice([0, 1], 500, p=[0.7, 0.3])
        np.random.seed(123)
        current = np.random.choice([0, 1], 500, p=[0.7, 0.3])
        
        result = detect_prediction_drift(reference, current)
        
        assert not result.drift_detected
        assert result.drift_score < 0.15
    
    def test_classification_drift_detected(self):
        """Drift should be detected when class distribution shifts."""
        np.random.seed(42)
        reference = np.random.choice([0, 1], 500, p=[0.7, 0.3])
        current = np.random.choice([0, 1], 500, p=[0.3, 0.7])  # Reversed!
        
        result = detect_prediction_drift(reference, current)
        
        assert result.drift_detected
        assert result.drift_score > 0.1
    
    def test_regression_no_drift(self):
        """No drift in regression predictions."""
        np.random.seed(42)
        reference = np.random.randn(500) * 10 + 100
        np.random.seed(123)
        current = np.random.randn(500) * 10 + 100
        
        result = detect_prediction_drift(reference, current)
        
        assert not result.drift_detected


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
