"""
Traffic Router
Deterministic traffic splitting for A/B tests.

Key features:
- Consistent hashing (same user always gets same variant)
- Supports multiple concurrent experiments
- Mutual exclusion (user in one experiment excluded from another)
- Gradual rollout support

Usage:
    router = TrafficRouter()
    router.register_experiment(experiment)
    variant = router.get_variant(user_id="user123", experiment_name="my-test")
"""

import hashlib
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from experiment import Experiment, ExperimentStatus


def stable_hash(value: str) -> int:
    """
    Generate a stable hash value between 0 and 99.
    
    Uses MD5 for consistency across platforms/sessions.
    Same input always produces same output.
    """
    hash_bytes = hashlib.md5(value.encode()).digest()
    # Use first 4 bytes as integer, mod 100
    hash_int = int.from_bytes(hash_bytes[:4], byteorder='big')
    return hash_int % 100


def stable_hash_float(value: str) -> float:
    """
    Generate a stable hash value between 0.0 and 1.0.
    """
    return stable_hash(value) / 100.0


@dataclass
class Assignment:
    """Record of a user's experiment assignment."""
    user_id: str
    experiment_name: str
    variant: str
    timestamp: str
    hash_value: int


class TrafficRouter:
    """
    Routes traffic to experiment variants deterministically.
    
    Features:
    - Consistent hashing: same user always gets same variant
    - Multiple experiments: route to different experiments independently
    - Mutual exclusion: optionally exclude users from multiple experiments
    - Override support: force specific users to specific variants
    
    Example:
        router = TrafficRouter()
        
        # Register experiment
        exp = Experiment(
            name="new-model-test",
            variants={"control": 0.9, "treatment": 0.1}
        )
        router.register_experiment(exp)
        
        # Get variant for user
        variant = router.get_variant("user123", "new-model-test")
        # Returns: "control" or "treatment" (deterministically)
    """
    
    def __init__(self, salt: str = ""):
        """
        Initialize router.
        
        Args:
            salt: Optional salt added to hashes (for security/uniqueness)
        """
        self.salt = salt
        self.experiments: dict[str, Experiment] = {}
        self.overrides: dict[str, dict[str, str]] = {}  # experiment -> user_id -> variant
        self.exclusions: dict[str, set[str]] = {}  # experiment -> set of excluded user_ids
    
    def register_experiment(self, experiment: Experiment):
        """Register an experiment for traffic routing."""
        self.experiments[experiment.name] = experiment
        self.overrides[experiment.name] = {}
        self.exclusions[experiment.name] = set()
    
    def _compute_hash(self, user_id: str, experiment_name: str) -> int:
        """Compute hash for user-experiment pair."""
        hash_input = f"{self.salt}:{experiment_name}:{user_id}"
        return stable_hash(hash_input)
    
    def _select_variant(self, hash_value: int, experiment: Experiment) -> str:
        """
        Select variant based on hash value and weights.
        
        Uses cumulative weights to divide the 0-99 hash space.
        
        Example with 90/10 split:
            hash 0-89   -> control (90%)
            hash 90-99  -> treatment (10%)
        """
        cumulative = 0
        
        for variant_name, variant in experiment.variants.items():
            cumulative += variant.weight * 100
            if hash_value < cumulative:
                return variant_name
        
        # Fallback to last variant (shouldn't happen with valid weights)
        return list(experiment.variants.keys())[-1]
    
    def get_variant(
        self,
        user_id: str,
        experiment_name: str,
        check_status: bool = True,
    ) -> Optional[str]:
        """
        Get variant assignment for a user.
        
        Args:
            user_id: Unique user identifier
            experiment_name: Name of the experiment
            check_status: If True, only return variant for running experiments
        
        Returns:
            Variant name, or None if user is excluded or experiment not running
        """
        
        # Check experiment exists
        experiment = self.experiments.get(experiment_name)
        if experiment is None:
            raise ValueError(f"Unknown experiment: {experiment_name}")
        
        # Check experiment status
        if check_status and experiment.status != ExperimentStatus.RUNNING:
            return None
        
        # Check exclusions
        if user_id in self.exclusions.get(experiment_name, set()):
            return None
        
        # Check overrides
        if user_id in self.overrides.get(experiment_name, {}):
            return self.overrides[experiment_name][user_id]
        
        # Compute hash and select variant
        hash_value = self._compute_hash(user_id, experiment_name)
        return self._select_variant(hash_value, experiment)
    
    def get_assignment(
        self,
        user_id: str,
        experiment_name: str,
    ) -> Optional[Assignment]:
        """Get full assignment details."""
        
        variant = self.get_variant(user_id, experiment_name)
        if variant is None:
            return None
        
        return Assignment(
            user_id=user_id,
            experiment_name=experiment_name,
            variant=variant,
            timestamp=datetime.now().isoformat(),
            hash_value=self._compute_hash(user_id, experiment_name),
        )
    
    def set_override(self, user_id: str, experiment_name: str, variant: str):
        """
        Force a user to a specific variant.
        
        Useful for:
        - Testing specific variants
        - QA/internal users
        - Customer support scenarios
        """
        if experiment_name not in self.experiments:
            raise ValueError(f"Unknown experiment: {experiment_name}")
        
        experiment = self.experiments[experiment_name]
        if variant not in experiment.variants:
            raise ValueError(f"Unknown variant: {variant}")
        
        self.overrides[experiment_name][user_id] = variant
    
    def remove_override(self, user_id: str, experiment_name: str):
        """Remove override for a user."""
        if experiment_name in self.overrides:
            self.overrides[experiment_name].pop(user_id, None)
    
    def exclude_user(self, user_id: str, experiment_name: str):
        """Exclude a user from an experiment."""
        if experiment_name not in self.exclusions:
            self.exclusions[experiment_name] = set()
        self.exclusions[experiment_name].add(user_id)
    
    def include_user(self, user_id: str, experiment_name: str):
        """Remove exclusion for a user."""
        if experiment_name in self.exclusions:
            self.exclusions[experiment_name].discard(user_id)
    
    def get_all_assignments(self, user_id: str) -> dict[str, str]:
        """Get all experiment assignments for a user."""
        assignments = {}
        
        for exp_name, experiment in self.experiments.items():
            if experiment.status == ExperimentStatus.RUNNING:
                variant = self.get_variant(user_id, exp_name)
                if variant is not None:
                    assignments[exp_name] = variant
        
        return assignments
    
    def simulate_distribution(
        self,
        experiment_name: str,
        n_users: int = 10000,
    ) -> dict[str, float]:
        """
        Simulate traffic distribution to verify weights.
        
        Useful for validating that hash function produces expected split.
        """
        variant_counts = {}
        
        for i in range(n_users):
            user_id = f"simulated_user_{i}"
            variant = self.get_variant(user_id, experiment_name, check_status=False)
            variant_counts[variant] = variant_counts.get(variant, 0) + 1
        
        # Convert to percentages
        return {
            variant: count / n_users
            for variant, count in variant_counts.items()
        }


class MultiExperimentRouter(TrafficRouter):
    """
    Extended router with mutual exclusion support.
    
    Ensures users aren't in multiple conflicting experiments.
    """
    
    def __init__(self, salt: str = ""):
        super().__init__(salt)
        self.exclusion_groups: dict[str, set[str]] = {}  # group_name -> set of experiment names
    
    def create_exclusion_group(self, group_name: str, experiment_names: list[str]):
        """
        Create a group of mutually exclusive experiments.
        
        Users assigned to one experiment in the group are excluded from others.
        """
        self.exclusion_groups[group_name] = set(experiment_names)
    
    def get_variant(
        self,
        user_id: str,
        experiment_name: str,
        check_status: bool = True,
    ) -> Optional[str]:
        """Get variant with mutual exclusion checking."""
        
        # Check if user is already in a conflicting experiment
        for group_name, experiments in self.exclusion_groups.items():
            if experiment_name in experiments:
                # Check if user is in any other experiment in this group
                for other_exp in experiments:
                    if other_exp != experiment_name and other_exp in self.experiments:
                        other_variant = super().get_variant(user_id, other_exp, check_status=False)
                        if other_variant is not None:
                            # User is in conflicting experiment, exclude from this one
                            return None
        
        return super().get_variant(user_id, experiment_name, check_status)


# Convenience function for simple use case
def get_ab_variant(
    user_id: str,
    experiment_id: str,
    control_weight: float = 0.5,
) -> str:
    """
    Simple A/B variant assignment.
    
    Args:
        user_id: User identifier
        experiment_id: Experiment identifier
        control_weight: Proportion of traffic for control (0.0 to 1.0)
    
    Returns:
        "control" or "treatment"
    """
    hash_value = stable_hash(f"{experiment_id}:{user_id}")
    threshold = control_weight * 100
    
    return "control" if hash_value < threshold else "treatment"


# Example usage
if __name__ == '__main__':
    from experiment import Experiment
    
    # Create experiment
    exp = Experiment(
        name="model-v4-test",
        variants={
            "control": 0.9,
            "treatment": 0.1,
        },
        primary_metric="conversion_rate",
    )
    exp.start()
    
    # Create router
    router = TrafficRouter(salt="my-app-salt")
    router.register_experiment(exp)
    
    # Test consistent assignment
    print("Testing consistent assignment:")
    for _ in range(3):
        variant = router.get_variant("user_123", "model-v4-test")
        print(f"  user_123 -> {variant}")
    
    # Test distribution
    print("\nSimulated distribution (10,000 users):")
    dist = router.simulate_distribution("model-v4-test", n_users=10000)
    for variant, pct in dist.items():
        print(f"  {variant}: {pct:.1%}")
    
    # Test override
    print("\nTesting override:")
    router.set_override("special_user", "model-v4-test", "treatment")
    variant = router.get_variant("special_user", "model-v4-test")
    print(f"  special_user (overridden) -> {variant}")
    
    # Simple function
    print("\nSimple get_ab_variant:")
    for i in range(5):
        variant = get_ab_variant(f"user_{i}", "quick-test", control_weight=0.8)
        print(f"  user_{i} -> {variant}")
