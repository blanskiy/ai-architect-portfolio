"""
Tests for Statistical Engine
Tests z-test, t-test, sample size calculation, etc.

Usage:
    pytest tests/test_stats.py -v
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from stats_engine import (
    z_test_proportions,
    t_test_independent,
    calculate_sample_size,
    calculate_power,
    get_confidence_interval_proportion,
    chi_square_test,
)


class TestZTestProportions:
    """Tests for two-proportion z-test."""
    
    def test_identical_proportions_not_significant(self):
        """Same conversion rates should not be significant."""
        result = z_test_proportions(
            conversions_a=100, total_a=1000,
            conversions_b=100, total_b=1000
        )
        
        assert not result.significant
        assert result.p_value > 0.05
    
    def test_clearly_different_proportions_significant(self):
        """Very different conversion rates should be significant."""
        result = z_test_proportions(
            conversions_a=100, total_a=1000,  # 10%
            conversions_b=200, total_b=1000   # 20%
        )
        
        assert result.significant
        assert result.p_value < 0.001
    
    def test_marginal_difference_not_significant_with_small_sample(self):
        """Small difference with small sample should not be significant."""
        result = z_test_proportions(
            conversions_a=10, total_a=100,   # 10%
            conversions_b=12, total_b=100    # 12%
        )
        
        assert not result.significant
    
    def test_same_difference_significant_with_large_sample(self):
        """Same difference with large sample should be significant."""
        result = z_test_proportions(
            conversions_a=1000, total_a=10000,   # 10%
            conversions_b=1200, total_b=10000    # 12%
        )
        
        assert result.significant
    
    def test_effect_size_positive_when_treatment_higher(self):
        """Effect size should be positive when treatment > control."""
        result = z_test_proportions(
            conversions_a=100, total_a=1000,
            conversions_b=150, total_b=1000
        )
        
        assert result.effect_size > 0
    
    def test_effect_size_negative_when_treatment_lower(self):
        """Effect size should be negative when treatment < control."""
        result = z_test_proportions(
            conversions_a=150, total_a=1000,
            conversions_b=100, total_b=1000
        )
        
        assert result.effect_size < 0
    
    def test_confidence_interval_contains_zero_when_not_significant(self):
        """CI should contain zero when not significant."""
        result = z_test_proportions(
            conversions_a=100, total_a=1000,
            conversions_b=105, total_b=1000
        )
        
        ci_lower, ci_upper = result.confidence_interval
        
        if not result.significant:
            assert ci_lower <= 0 <= ci_upper


class TestTTestIndependent:
    """Tests for independent samples t-test."""
    
    def test_identical_distributions_not_significant(self):
        """Same distributions should not be significant."""
        np.random.seed(42)
        a = np.random.randn(100)
        b = np.random.randn(100)
        
        result = t_test_independent(list(a), list(b))
        
        assert not result.significant
    
    def test_shifted_distributions_significant(self):
        """Shifted distribution should be significant with enough samples."""
        np.random.seed(42)
        a = np.random.randn(500)
        b = np.random.randn(500) + 0.5  # Shifted by 0.5 std
        
        result = t_test_independent(list(a), list(b))
        
        assert result.significant
    
    def test_effect_size_cohens_d_interpretation(self):
        """Cohen's d should be reasonable."""
        np.random.seed(42)
        a = np.random.randn(100)
        b = np.random.randn(100) + 0.8  # Large effect
        
        result = t_test_independent(list(a), list(b))
        
        # Cohen's d should be approximately 0.8
        assert 0.5 < result.effect_size < 1.2


class TestSampleSizeCalculation:
    """Tests for sample size calculation."""
    
    def test_higher_mde_needs_smaller_sample(self):
        """Larger MDE should require smaller sample."""
        result_small_mde = calculate_sample_size(
            baseline_rate=0.10,
            min_detectable_effect=0.05  # 5% relative
        )
        
        result_large_mde = calculate_sample_size(
            baseline_rate=0.10,
            min_detectable_effect=0.20  # 20% relative
        )
        
        assert result_small_mde['n_per_variant'] > result_large_mde['n_per_variant']
    
    def test_higher_power_needs_larger_sample(self):
        """Higher power should require larger sample."""
        result_80_power = calculate_sample_size(
            baseline_rate=0.10,
            min_detectable_effect=0.10,
            power=0.80
        )
        
        result_90_power = calculate_sample_size(
            baseline_rate=0.10,
            min_detectable_effect=0.10,
            power=0.90
        )
        
        assert result_90_power['n_per_variant'] > result_80_power['n_per_variant']
    
    def test_known_sample_size_scenario(self):
        """Test against known calculation."""
        # 10% baseline, detect 10% relative lift (10% -> 11%)
        # Should need roughly 15,000-16,000 per variant
        result = calculate_sample_size(
            baseline_rate=0.10,
            min_detectable_effect=0.10,
            power=0.80
        )
        
        # Approximate expected value
        assert 10000 < result['n_per_variant'] < 20000


class TestPowerCalculation:
    """Tests for power calculation."""
    
    def test_power_increases_with_sample_size(self):
        """Power should increase with sample size."""
        power_small = calculate_power(
            baseline_rate=0.10,
            treatment_rate=0.11,
            n_per_variant=1000
        )
        
        power_large = calculate_power(
            baseline_rate=0.10,
            treatment_rate=0.11,
            n_per_variant=10000
        )
        
        assert power_large > power_small
    
    def test_power_increases_with_effect_size(self):
        """Power should increase with larger effect."""
        power_small_effect = calculate_power(
            baseline_rate=0.10,
            treatment_rate=0.11,
            n_per_variant=5000
        )
        
        power_large_effect = calculate_power(
            baseline_rate=0.10,
            treatment_rate=0.15,
            n_per_variant=5000
        )
        
        assert power_large_effect > power_small_effect
    
    def test_power_between_zero_and_one(self):
        """Power should always be between 0 and 1."""
        power = calculate_power(
            baseline_rate=0.10,
            treatment_rate=0.12,
            n_per_variant=5000
        )
        
        assert 0 <= power <= 1


class TestConfidenceInterval:
    """Tests for confidence interval calculation."""
    
    def test_ci_contains_true_proportion(self):
        """CI should contain the observed proportion."""
        successes = 100
        total = 1000
        observed = successes / total
        
        ci_lower, ci_upper = get_confidence_interval_proportion(
            successes, total, method='wilson'
        )
        
        assert ci_lower <= observed <= ci_upper
    
    def test_ci_narrows_with_larger_sample(self):
        """CI should be narrower with larger sample."""
        ci_small = get_confidence_interval_proportion(50, 100)
        ci_large = get_confidence_interval_proportion(500, 1000)
        
        width_small = ci_small[1] - ci_small[0]
        width_large = ci_large[1] - ci_large[0]
        
        assert width_large < width_small
    
    def test_extreme_proportions_handled(self):
        """Should handle 0% and 100% conversion."""
        # 0% conversion
        ci_zero = get_confidence_interval_proportion(0, 100)
        assert ci_zero[0] >= 0
        assert ci_zero[1] > 0
        
        # 100% conversion
        ci_full = get_confidence_interval_proportion(100, 100)
        assert ci_full[0] < 1
        assert ci_full[1] <= 1


class TestChiSquare:
    """Tests for chi-square test."""
    
    def test_similar_tables_not_significant(self):
        """Similar contingency tables should not be significant."""
        # Control: 900 no, 100 yes
        # Treatment: 890 no, 110 yes
        table = [[900, 100], [890, 110]]
        
        result = chi_square_test(table)
        
        # Small difference, likely not significant
        assert result.p_value > 0.01
    
    def test_different_tables_significant(self):
        """Very different tables should be significant."""
        # Control: 900 no, 100 yes
        # Treatment: 700 no, 300 yes
        table = [[900, 100], [700, 300]]
        
        result = chi_square_test(table)
        
        assert result.significant
        assert result.p_value < 0.001


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
