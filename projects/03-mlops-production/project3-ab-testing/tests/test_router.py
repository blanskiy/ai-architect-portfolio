"""
Tests for Traffic Router
Tests consistent hashing, traffic splitting, overrides, etc.

Usage:
    pytest tests/test_router.py -v
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from traffic_router import (
    TrafficRouter,
    stable_hash,
    stable_hash_float,
    get_ab_variant,
)
from experiment import Experiment, ExperimentStatus


class TestStableHash:
    """Tests for stable hashing function."""
    
    def test_same_input_same_output(self):
        """Same input should always produce same output."""
        input_str = "user123:experiment456"
        
        hash1 = stable_hash(input_str)
        hash2 = stable_hash(input_str)
        hash3 = stable_hash(input_str)
        
        assert hash1 == hash2 == hash3
    
    def test_output_in_range(self):
        """Hash should be between 0 and 99."""
        for i in range(100):
            hash_val = stable_hash(f"test_input_{i}")
            assert 0 <= hash_val <= 99
    
    def test_different_inputs_different_outputs(self):
        """Different inputs should generally produce different outputs."""
        hashes = [stable_hash(f"user_{i}") for i in range(100)]
        unique_hashes = set(hashes)
        
        # Should have reasonable variety (not all same)
        assert len(unique_hashes) > 10
    
    def test_distribution_roughly_uniform(self):
        """Hash distribution should be roughly uniform."""
        n_samples = 10000
        hashes = [stable_hash(f"user_{i}") for i in range(n_samples)]
        
        # Count how many fall in each decile
        decile_counts = [0] * 10
        for h in hashes:
            decile_counts[h // 10] += 1
        
        # Each decile should have roughly 10% (1000 ± 200)
        for count in decile_counts:
            assert 800 < count < 1200


class TestTrafficRouter:
    """Tests for TrafficRouter class."""
    
    @pytest.fixture
    def experiment(self):
        """Create a test experiment."""
        exp = Experiment(
            name="test-experiment",
            variants={
                "control": 0.9,
                "treatment": 0.1,
            },
            primary_metric="conversion_rate",
        )
        exp.start()
        return exp
    
    @pytest.fixture
    def router(self, experiment):
        """Create a router with the test experiment."""
        router = TrafficRouter()
        router.register_experiment(experiment)
        return router
    
    def test_consistent_assignment(self, router):
        """Same user should always get same variant."""
        user_id = "user_123"
        
        variant1 = router.get_variant(user_id, "test-experiment")
        variant2 = router.get_variant(user_id, "test-experiment")
        variant3 = router.get_variant(user_id, "test-experiment")
        
        assert variant1 == variant2 == variant3
    
    def test_traffic_split_approximately_correct(self, router):
        """Traffic should split according to weights."""
        n_users = 10000
        variant_counts = {"control": 0, "treatment": 0}
        
        for i in range(n_users):
            variant = router.get_variant(f"user_{i}", "test-experiment")
            variant_counts[variant] += 1
        
        # Control should be ~90%, treatment ~10%
        control_pct = variant_counts["control"] / n_users
        treatment_pct = variant_counts["treatment"] / n_users
        
        assert 0.85 < control_pct < 0.95
        assert 0.05 < treatment_pct < 0.15
    
    def test_override_works(self, router):
        """Override should force specific variant."""
        user_id = "special_user"
        
        # Get natural assignment
        natural_variant = router.get_variant(user_id, "test-experiment")
        
        # Set override to opposite
        override_variant = "treatment" if natural_variant == "control" else "control"
        router.set_override(user_id, "test-experiment", override_variant)
        
        # Should now get override variant
        assert router.get_variant(user_id, "test-experiment") == override_variant
    
    def test_exclusion_works(self, router):
        """Excluded user should get None."""
        user_id = "excluded_user"
        
        # Should get a variant initially
        assert router.get_variant(user_id, "test-experiment") is not None
        
        # Exclude user
        router.exclude_user(user_id, "test-experiment")
        
        # Should now get None
        assert router.get_variant(user_id, "test-experiment") is None
        
        # Re-include
        router.include_user(user_id, "test-experiment")
        
        # Should get variant again
        assert router.get_variant(user_id, "test-experiment") is not None
    
    def test_stopped_experiment_returns_none(self, router, experiment):
        """Stopped experiment should return None."""
        user_id = "user_123"
        
        # Running experiment returns variant
        assert router.get_variant(user_id, "test-experiment") is not None
        
        # Stop experiment
        experiment.pause()
        
        # Should return None
        assert router.get_variant(user_id, "test-experiment") is None
    
    def test_unknown_experiment_raises(self, router):
        """Unknown experiment should raise error."""
        with pytest.raises(ValueError):
            router.get_variant("user_123", "nonexistent-experiment")
    
    def test_simulate_distribution(self, router):
        """Simulation should match expected weights."""
        distribution = router.simulate_distribution("test-experiment", n_users=10000)
        
        assert 0.85 < distribution["control"] < 0.95
        assert 0.05 < distribution["treatment"] < 0.15
        
        # Should sum to 1
        assert abs(sum(distribution.values()) - 1.0) < 0.01


class TestMultiVariant:
    """Tests for experiments with more than 2 variants."""
    
    def test_three_variant_split(self):
        """Three-way split should work correctly."""
        exp = Experiment(
            name="three-way",
            variants={
                "control": 0.6,
                "treatment_a": 0.2,
                "treatment_b": 0.2,
            },
            primary_metric="conversion_rate",
        )
        exp.start()
        
        router = TrafficRouter()
        router.register_experiment(exp)
        
        # Simulate distribution
        dist = router.simulate_distribution("three-way", n_users=10000)
        
        assert 0.55 < dist["control"] < 0.65
        assert 0.15 < dist["treatment_a"] < 0.25
        assert 0.15 < dist["treatment_b"] < 0.25


class TestGetABVariant:
    """Tests for simple get_ab_variant function."""
    
    def test_consistent_assignment(self):
        """Same user/experiment should get same variant."""
        for _ in range(3):
            variant = get_ab_variant("user_123", "exp_456", control_weight=0.5)
            assert variant in ["control", "treatment"]
        
        # Should be consistent
        variants = [get_ab_variant("user_123", "exp_456", control_weight=0.5) for _ in range(10)]
        assert len(set(variants)) == 1
    
    def test_different_users_get_different_variants(self):
        """Different users should sometimes get different variants."""
        variants = [get_ab_variant(f"user_{i}", "exp", control_weight=0.5) for i in range(100)]
        
        # Should have both variants
        assert "control" in variants
        assert "treatment" in variants
    
    def test_weight_affects_distribution(self):
        """Higher control weight should mean more control assignments."""
        n = 10000
        
        high_control = sum(
            1 for i in range(n) 
            if get_ab_variant(f"user_{i}", "exp", control_weight=0.9) == "control"
        ) / n
        
        low_control = sum(
            1 for i in range(n) 
            if get_ab_variant(f"user_{i}", "exp", control_weight=0.1) == "control"
        ) / n
        
        assert high_control > 0.85
        assert low_control < 0.15


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
