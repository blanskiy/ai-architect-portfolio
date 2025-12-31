"""
Multi-Armed Bandit Algorithms
Adaptive traffic allocation that balances exploration vs exploitation.

Algorithms:
- Epsilon-Greedy: Simple exploration with fixed probability
- Thompson Sampling: Bayesian approach, state-of-the-art for conversions
- UCB (Upper Confidence Bound): Optimistic exploration

When to use bandits vs A/B:
- A/B Testing: Need statistical rigor, one-time decision
- Bandits: Continuous optimization, minimize regret, many variants

Usage:
    bandit = ThompsonSampling(arms=["model_a", "model_b", "model_c"])
    
    # Select arm
    arm = bandit.select_arm()
    
    # Update with reward
    bandit.update(arm, reward=1)  # Success
    bandit.update(arm, reward=0)  # Failure
"""

import random
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class ArmStats:
    """Statistics for a single arm."""
    name: str
    pulls: int = 0
    successes: int = 0
    total_reward: float = 0.0
    
    @property
    def success_rate(self) -> float:
        return self.successes / self.pulls if self.pulls > 0 else 0.0
    
    @property
    def mean_reward(self) -> float:
        return self.total_reward / self.pulls if self.pulls > 0 else 0.0


class Bandit(ABC):
    """Abstract base class for bandit algorithms."""
    
    def __init__(self, arms: list[str]):
        self.arms = arms
        self.stats = {arm: ArmStats(name=arm) for arm in arms}
        self.total_pulls = 0
    
    @abstractmethod
    def select_arm(self) -> str:
        """Select an arm to pull."""
        pass
    
    def update(self, arm: str, reward: float):
        """Update statistics after observing reward."""
        self.stats[arm].pulls += 1
        self.stats[arm].total_reward += reward
        if reward > 0:
            self.stats[arm].successes += 1
        self.total_pulls += 1
    
    def get_best_arm(self) -> str:
        """Get the arm with highest observed success rate."""
        return max(self.arms, key=lambda a: self.stats[a].success_rate)
    
    def get_summary(self) -> dict:
        """Get summary of all arms."""
        return {
            arm: {
                'pulls': self.stats[arm].pulls,
                'successes': self.stats[arm].successes,
                'success_rate': self.stats[arm].success_rate,
                'mean_reward': self.stats[arm].mean_reward,
            }
            for arm in self.arms
        }
    
    def get_allocation_percentages(self) -> dict[str, float]:
        """Get current traffic allocation percentages."""
        if self.total_pulls == 0:
            return {arm: 1.0 / len(self.arms) for arm in self.arms}
        return {
            arm: self.stats[arm].pulls / self.total_pulls
            for arm in self.arms
        }


class EpsilonGreedy(Bandit):
    """
    Epsilon-Greedy Algorithm.
    
    With probability epsilon: explore (random arm)
    With probability 1-epsilon: exploit (best arm so far)
    
    Simple but effective. Epsilon typically 0.1 (10% exploration).
    
    Example:
        bandit = EpsilonGreedy(arms=["A", "B"], epsilon=0.1)
    """
    
    def __init__(self, arms: list[str], epsilon: float = 0.1):
        super().__init__(arms)
        self.epsilon = epsilon
    
    def select_arm(self) -> str:
        # Explore with probability epsilon
        if random.random() < self.epsilon:
            return random.choice(self.arms)
        
        # Exploit: choose best arm
        # Handle cold start: if any arm hasn't been pulled, pull it
        unpulled = [a for a in self.arms if self.stats[a].pulls == 0]
        if unpulled:
            return random.choice(unpulled)
        
        return self.get_best_arm()


class DecayingEpsilonGreedy(Bandit):
    """
    Epsilon-Greedy with decaying exploration.
    
    Epsilon decreases over time: epsilon(t) = epsilon_0 / (1 + decay * t)
    
    Explores more early, exploits more later.
    """
    
    def __init__(
        self,
        arms: list[str],
        epsilon_initial: float = 1.0,
        epsilon_min: float = 0.01,
        decay: float = 0.01,
    ):
        super().__init__(arms)
        self.epsilon_initial = epsilon_initial
        self.epsilon_min = epsilon_min
        self.decay = decay
    
    @property
    def epsilon(self) -> float:
        decayed = self.epsilon_initial / (1 + self.decay * self.total_pulls)
        return max(decayed, self.epsilon_min)
    
    def select_arm(self) -> str:
        if random.random() < self.epsilon:
            return random.choice(self.arms)
        
        unpulled = [a for a in self.arms if self.stats[a].pulls == 0]
        if unpulled:
            return random.choice(unpulled)
        
        return self.get_best_arm()


class ThompsonSampling(Bandit):
    """
    Thompson Sampling (Bayesian Bandit).
    
    For each arm, maintain a Beta distribution of success probability.
    Sample from each distribution, pick the arm with highest sample.
    
    Naturally balances exploration/exploitation.
    State-of-the-art for conversion rate optimization.
    
    Math:
    - Prior: Beta(alpha=1, beta=1) = Uniform
    - After s successes and f failures: Beta(alpha=1+s, beta=1+f)
    - Sample from each Beta, pick highest
    
    Example:
        bandit = ThompsonSampling(arms=["model_a", "model_b"])
    """
    
    def __init__(
        self,
        arms: list[str],
        prior_alpha: float = 1.0,
        prior_beta: float = 1.0,
    ):
        super().__init__(arms)
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta
    
    def _get_posterior_params(self, arm: str) -> tuple[float, float]:
        """Get Beta distribution parameters for an arm."""
        alpha = self.prior_alpha + self.stats[arm].successes
        beta = self.prior_beta + (self.stats[arm].pulls - self.stats[arm].successes)
        return alpha, beta
    
    def select_arm(self) -> str:
        samples = {}
        
        for arm in self.arms:
            alpha, beta = self._get_posterior_params(arm)
            samples[arm] = np.random.beta(alpha, beta)
        
        return max(samples, key=samples.get)
    
    def get_probabilities(self) -> dict[str, float]:
        """
        Get probability each arm is the best (via simulation).
        
        Useful for understanding confidence in each arm.
        """
        n_simulations = 10000
        wins = {arm: 0 for arm in self.arms}
        
        for _ in range(n_simulations):
            samples = {}
            for arm in self.arms:
                alpha, beta = self._get_posterior_params(arm)
                samples[arm] = np.random.beta(alpha, beta)
            
            winner = max(samples, key=samples.get)
            wins[winner] += 1
        
        return {arm: wins[arm] / n_simulations for arm in self.arms}


class UCB(Bandit):
    """
    Upper Confidence Bound (UCB1).
    
    Pick arm with highest: mean + exploration_bonus
    Exploration bonus = sqrt(2 * ln(total_pulls) / arm_pulls)
    
    "Optimism in the face of uncertainty" - explore uncertain arms.
    
    Example:
        bandit = UCB(arms=["A", "B", "C"])
    """
    
    def __init__(self, arms: list[str], c: float = 2.0):
        """
        Args:
            arms: List of arm names
            c: Exploration constant (higher = more exploration)
        """
        super().__init__(arms)
        self.c = c
    
    def _ucb_score(self, arm: str) -> float:
        """Calculate UCB score for an arm."""
        if self.stats[arm].pulls == 0:
            return float('inf')  # Never pulled = infinite potential
        
        mean = self.stats[arm].success_rate
        exploration = math.sqrt(self.c * math.log(self.total_pulls) / self.stats[arm].pulls)
        
        return mean + exploration
    
    def select_arm(self) -> str:
        return max(self.arms, key=self._ucb_score)


class SoftmaxBandit(Bandit):
    """
    Softmax (Boltzmann) exploration.
    
    Probability of selecting arm proportional to exp(mean / temperature).
    
    Temperature controls exploration:
    - High temperature: more uniform (explore)
    - Low temperature: more greedy (exploit)
    """
    
    def __init__(self, arms: list[str], temperature: float = 0.1):
        super().__init__(arms)
        self.temperature = temperature
    
    def select_arm(self) -> str:
        # Handle cold start
        unpulled = [a for a in self.arms if self.stats[a].pulls == 0]
        if unpulled:
            return random.choice(unpulled)
        
        # Softmax probabilities
        means = [self.stats[arm].success_rate for arm in self.arms]
        exp_values = [math.exp(m / self.temperature) for m in means]
        total = sum(exp_values)
        probabilities = [e / total for e in exp_values]
        
        return random.choices(self.arms, weights=probabilities, k=1)[0]


# ============================================================================
# CONTEXTUAL BANDIT (simple version)
# ============================================================================

class ContextualEpsilonGreedy:
    """
    Simple contextual bandit using epsilon-greedy with separate models per arm.
    
    For each arm, maintain a logistic regression model that predicts reward
    given context. Select arm with highest predicted reward (with exploration).
    
    Context could be: user features, time of day, device type, etc.
    """
    
    def __init__(self, arms: list[str], n_features: int, epsilon: float = 0.1):
        self.arms = arms
        self.n_features = n_features
        self.epsilon = epsilon
        
        # Simple linear model: weights per arm
        self.weights = {arm: np.zeros(n_features) for arm in arms}
        self.learning_rate = 0.1
        
        # Stats
        self.pulls = {arm: 0 for arm in arms}
    
    def select_arm(self, context: np.ndarray) -> str:
        """Select arm given context features."""
        
        # Explore
        if random.random() < self.epsilon:
            return random.choice(self.arms)
        
        # Exploit: predict reward for each arm
        predictions = {}
        for arm in self.arms:
            # Sigmoid of linear combination
            z = np.dot(self.weights[arm], context)
            predictions[arm] = 1 / (1 + np.exp(-z))
        
        return max(predictions, key=predictions.get)
    
    def update(self, arm: str, context: np.ndarray, reward: float):
        """Update model for arm given observed reward."""
        
        # Prediction
        z = np.dot(self.weights[arm], context)
        pred = 1 / (1 + np.exp(-z))
        
        # Gradient update (logistic regression)
        error = reward - pred
        self.weights[arm] += self.learning_rate * error * context
        
        self.pulls[arm] += 1


# ============================================================================
# SIMULATION UTILITIES
# ============================================================================

def simulate_bandit(
    bandit: Bandit,
    true_probabilities: dict[str, float],
    n_rounds: int = 1000,
) -> dict:
    """
    Simulate bandit performance.
    
    Args:
        bandit: Bandit algorithm instance
        true_probabilities: True success probability for each arm
        n_rounds: Number of rounds to simulate
    
    Returns:
        Simulation results including regret
    """
    
    best_arm = max(true_probabilities, key=true_probabilities.get)
    best_prob = true_probabilities[best_arm]
    
    cumulative_reward = 0
    cumulative_regret = 0
    history = []
    
    for t in range(n_rounds):
        # Select arm
        arm = bandit.select_arm()
        
        # Generate reward
        reward = 1 if random.random() < true_probabilities[arm] else 0
        
        # Update bandit
        bandit.update(arm, reward)
        
        # Track metrics
        cumulative_reward += reward
        regret = best_prob - true_probabilities[arm]
        cumulative_regret += regret
        
        history.append({
            'round': t,
            'arm': arm,
            'reward': reward,
            'cumulative_reward': cumulative_reward,
            'cumulative_regret': cumulative_regret,
        })
    
    return {
        'final_summary': bandit.get_summary(),
        'best_arm_selected': bandit.get_best_arm(),
        'true_best_arm': best_arm,
        'correct': bandit.get_best_arm() == best_arm,
        'cumulative_reward': cumulative_reward,
        'cumulative_regret': cumulative_regret,
        'allocation': bandit.get_allocation_percentages(),
    }


# Example usage
if __name__ == '__main__':
    print("=" * 60)
    print("MULTI-ARMED BANDIT SIMULATION")
    print("=" * 60)
    
    # True probabilities (unknown to bandit)
    true_probs = {
        "model_a": 0.10,  # 10% conversion
        "model_b": 0.12,  # 12% conversion (best)
        "model_c": 0.08,  # 8% conversion
    }
    
    print("\nTrue probabilities (hidden from bandit):")
    for arm, prob in true_probs.items():
        print(f"  {arm}: {prob:.0%}")
    
    # Test different algorithms
    algorithms = {
        "Epsilon-Greedy (ε=0.1)": EpsilonGreedy(list(true_probs.keys()), epsilon=0.1),
        "Thompson Sampling": ThompsonSampling(list(true_probs.keys())),
        "UCB": UCB(list(true_probs.keys())),
    }
    
    print("\n" + "-" * 60)
    print("RESULTS AFTER 1000 ROUNDS")
    print("-" * 60)
    
    for name, bandit in algorithms.items():
        results = simulate_bandit(bandit, true_probs, n_rounds=1000)
        
        print(f"\n{name}:")
        print(f"  Identified best arm: {results['best_arm_selected']} "
              f"({'✓ Correct' if results['correct'] else '✗ Wrong'})")
        print(f"  Cumulative reward: {results['cumulative_reward']}")
        print(f"  Cumulative regret: {results['cumulative_regret']:.1f}")
        print(f"  Traffic allocation:")
        for arm, pct in results['allocation'].items():
            print(f"    {arm}: {pct:.1%}")
