# Project 3: A/B Testing Framework for ML

Safe model rollout with statistical rigor and experimentation infrastructure.

## Overview

| Aspect | Details |
|--------|---------|
| **Purpose** | Safely compare model versions in production |
| **Key Concepts** | Feature flags, statistical significance, traffic splitting |
| **Methods** | A/B testing, multi-armed bandits, sequential testing |
| **Outcome** | Data-driven model promotion decisions |

## Why A/B Testing for ML?

### The Problem

```
Traditional Deployment:              A/B Testing:
────────────────────────            ────────────────────────
Deploy new model to 100%            Deploy to 5% of traffic
Hope it works                       Measure impact
Find out Monday it broke            Statistical proof it's better
                                    Gradual rollout to 100%
```

### Key Questions A/B Testing Answers

1. **Is the new model actually better?** (Not just on test set, but in production)
2. **How much better?** (Effect size and confidence interval)
3. **Is the difference statistically significant?** (Not just random noise)
4. **What's the business impact?** (Revenue, conversion, engagement)

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        A/B TESTING FRAMEWORK                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   User Request                                                               │
│        │                                                                     │
│        ▼                                                                     │
│   ┌──────────────┐                                                          │
│   │   Traffic    │                                                          │
│   │   Router     │                                                          │
│   └───────┬──────┘                                                          │
│           │                                                                  │
│           │  Feature Flag + User Hash                                       │
│           │                                                                  │
│     ┌─────┴─────┐                                                           │
│     │           │                                                           │
│     ▼           ▼                                                           │
│ ┌────────┐  ┌────────┐                                                      │
│ │Control │  │Treatment│                                                     │
│ │Model A │  │Model B  │                                                     │
│ │ (95%)  │  │  (5%)   │                                                     │
│ └───┬────┘  └───┬────┘                                                      │
│     │           │                                                           │
│     └─────┬─────┘                                                           │
│           │                                                                  │
│           ▼                                                                  │
│   ┌──────────────┐                                                          │
│   │   Log Event  │                                                          │
│   │  (user, variant, outcome)                                               │
│   └───────┬──────┘                                                          │
│           │                                                                  │
│           ▼                                                                  │
│   ┌──────────────┐     ┌──────────────┐                                    │
│   │  Experiment  │────►│  Statistical │                                    │
│   │   Tracker    │     │   Analysis   │                                    │
│   └──────────────┘     └──────────────┘                                    │
│                               │                                             │
│                               ▼                                             │
│                        Winner Decision                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
project3-ab-testing/
├── README.md
├── INTERVIEW_PREP.md
├── requirements.txt
├── src/
│   ├── experiment.py           # Experiment definition and management
│   ├── traffic_router.py       # Traffic splitting logic
│   ├── stats_engine.py         # Statistical significance testing
│   ├── bandit.py               # Multi-armed bandit algorithms
│   └── analysis.py             # Results analysis and reporting
├── configs/
│   └── experiment_config.yaml  # Experiment definitions
├── examples/
│   └── run_experiment.py       # End-to-end example
└── tests/
    ├── test_stats.py
    └── test_router.py
```

## Key Concepts

### 1. Traffic Splitting

Consistently route users to the same variant:

```python
def get_variant(user_id: str, experiment_id: str) -> str:
    # Hash ensures same user always gets same variant
    hash_value = hash(f"{user_id}:{experiment_id}") % 100
    
    if hash_value < 95:  # 95% traffic
        return "control"
    else:                 # 5% traffic
        return "treatment"
```

**Why hashing?**
- User sees same variant across sessions
- No need to store assignments
- Deterministic and reproducible

### 2. Statistical Significance

**Null Hypothesis**: There is no difference between models.

**Goal**: Reject null hypothesis with confidence (typically 95%).

```
p-value < 0.05  →  Statistically significant difference
p-value ≥ 0.05  →  Cannot conclude there's a difference
```

### 3. Sample Size Calculation

Before running experiment, calculate required sample size:

```
n = (Z_α/2 + Z_β)² × 2σ² / δ²

Where:
- Z_α/2 = 1.96 for 95% confidence
- Z_β = 0.84 for 80% power
- σ = standard deviation of metric
- δ = minimum detectable effect
```

**Example**: Detect 2% conversion lift with baseline 10%
```
n ≈ 3,900 per variant
Total: 7,800 users needed
```

### 4. Metrics

| Metric Type | Example | Statistical Test |
|-------------|---------|------------------|
| **Conversion** (binary) | Clicked/not clicked | Chi-square, Z-test |
| **Revenue** (continuous) | $ per user | t-test, Mann-Whitney |
| **Count** | Items purchased | Poisson test |

## Methods Comparison

### A/B Testing (Fixed Horizon)
```
Run experiment for fixed duration
Analyze at the end
Winner takes all traffic
```
**Pros**: Simple, well-understood
**Cons**: Waste traffic on losing variant

### Multi-Armed Bandit
```
Start 50/50
Shift traffic toward better performer
Continuously optimize
```
**Pros**: Less regret, faster convergence
**Cons**: Harder to interpret statistically

### Sequential Testing
```
Analyze continuously
Stop early if clear winner
Adjust for multiple comparisons
```
**Pros**: Faster decisions when effect is large
**Cons**: More complex statistics

## Quick Start

### 1. Define Experiment
```python
from src.experiment import Experiment

exp = Experiment(
    name="new-sales-model-v4",
    variants={
        "control": {"model": "v3", "weight": 0.9},
        "treatment": {"model": "v4", "weight": 0.1}
    },
    primary_metric="conversion_rate",
    min_detectable_effect=0.02,
)
```

### 2. Route Traffic
```python
from src.traffic_router import TrafficRouter

router = TrafficRouter(experiment=exp)
variant = router.get_variant(user_id="user123")
# Returns: "control" or "treatment"
```

### 3. Log Outcomes
```python
from src.experiment import ExperimentTracker

tracker = ExperimentTracker(experiment=exp)
tracker.log_event(
    user_id="user123",
    variant="treatment",
    converted=True,
    revenue=49.99
)
```

### 4. Analyze Results
```python
from src.analysis import analyze_experiment

results = analyze_experiment(exp)
print(results.summary())
# Control: 10.2% conversion (n=9,000)
# Treatment: 11.8% conversion (n=1,000)
# Lift: +15.7%
# p-value: 0.023 ✓ Significant
# Recommendation: Deploy treatment
```

## Interview Talking Points

### Q: "How do you safely roll out a new model?"

> "I use A/B testing with gradual rollout. Start with 5-10% traffic to treatment, measure key metrics (conversion, revenue, latency), and check for statistical significance. If treatment wins with p < 0.05 and no regression in guardrail metrics, gradually increase to 100%. Feature flags make rollback instant if issues arise."

### Q: "How do you know when you have enough data?"

> "I calculate required sample size upfront based on baseline conversion rate, minimum detectable effect (usually 2-5%), desired power (80%), and significance level (5%). For example, detecting a 2% lift on 10% baseline conversion needs about 4,000 users per variant. I won't make decisions until we hit that sample size."

### Q: "What's the difference between A/B testing and multi-armed bandits?"

> "A/B testing fixes traffic split for the experiment duration—good for clean statistical interpretation. Multi-armed bandits dynamically shift traffic toward the winner—reduces 'regret' but makes significance harder to calculate. I use A/B for major model changes where I need statistical rigor, and bandits for optimizing many small variants continuously."

---

*Project 3 - MLOps & Production*
