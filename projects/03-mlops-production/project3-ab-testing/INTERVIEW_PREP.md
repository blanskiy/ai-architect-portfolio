# A/B Testing - Interview Cheat Sheet

## Quick Framework (30-second answer)

> "I implement A/B testing with three components: **traffic routing** using consistent hashing so users always see the same variant, **statistical analysis** using z-tests for conversion and t-tests for revenue, and **sample size calculation** upfront to ensure adequate power. I don't make decisions until we hit required sample size and p < 0.05. For continuous optimization with many variants, I use Thompson Sampling bandits."

---

## The Fundamentals

### What A/B Testing Answers

| Question | How |
|----------|-----|
| Is the new model better? | Compare conversion rates |
| How much better? | Calculate lift + confidence interval |
| Is it statistically significant? | p-value < 0.05 |
| Can we trust the result? | Check sample size and power |

### Key Terms (Memorize!)

| Term | Definition | Typical Value |
|------|------------|---------------|
| **p-value** | Probability result is due to chance | < 0.05 = significant |
| **Power** | Probability of detecting real effect | 80% |
| **Significance Level (α)** | False positive rate | 5% |
| **MDE** | Minimum Detectable Effect | 2-5% lift |
| **Confidence Interval** | Range likely containing true value | 95% CI |

---

## Traffic Splitting

### Consistent Hashing

```python
def get_variant(user_id, experiment_id):
    # Same user ALWAYS gets same variant
    hash_value = hash(f"{experiment_id}:{user_id}") % 100
    return "control" if hash_value < 90 else "treatment"
```

**Why consistent hashing?**
- User sees same experience across sessions
- No need to store assignments
- Deterministic and reproducible

**Why NOT random?**
- User could see different variants each visit
- Confuses the user
- Pollutes your data

---

## Statistical Tests

### When to Use What

| Metric Type | Example | Test |
|-------------|---------|------|
| Binary | Clicked/not clicked | Z-test for proportions |
| Continuous | Revenue per user | T-test |
| Count | Items purchased | Poisson test |
| Non-normal | Revenue (skewed) | Mann-Whitney U |

### The Z-Test for Proportions

```
H₀: p_treatment = p_control (no difference)
H₁: p_treatment ≠ p_control (there is a difference)

Z = (p_treatment - p_control) / SE

Where SE = sqrt(p_pooled × (1-p_pooled) × (1/n₁ + 1/n₂))
```

---

## Sample Size Calculation

### The Formula

```
n = (Z_α/2 + Z_β)² × 2p(1-p) / δ²

Where:
- Z_α/2 = 1.96 (for 95% confidence)
- Z_β = 0.84 (for 80% power)
- p = baseline conversion rate
- δ = minimum detectable effect (absolute)
```

### Quick Reference

| Baseline | MDE (relative) | Sample per Variant |
|----------|----------------|-------------------|
| 5% | 10% | ~31,000 |
| 10% | 5% | ~31,000 |
| 10% | 10% | ~8,000 |
| 20% | 5% | ~25,000 |

**Rule of thumb**: Detecting smaller effects needs MUCH more data.

---

## A/B vs Multi-Armed Bandits

### A/B Testing

```
Fixed split → Run to completion → Analyze → Winner takes all
```

**Pros**: Clear statistical interpretation, standard practice
**Cons**: "Regret" - traffic wasted on losing variant

### Multi-Armed Bandits

```
Start 50/50 → Shift traffic toward winner → Continuously optimize
```

**Pros**: Less regret, faster convergence
**Cons**: Harder to interpret statistically

### When to Use What

| Scenario | Approach |
|----------|----------|
| Major model change, need confidence | A/B Test |
| Many small variants to optimize | Bandit |
| One-time decision | A/B Test |
| Continuous optimization | Bandit |
| Regulatory/compliance requirements | A/B Test |

---

## Common Interview Questions

### Q: "How do you decide when an A/B test is done?"

> "I calculate required sample size BEFORE starting, based on baseline conversion, minimum detectable effect, and 80% power. The test runs until we hit that sample size. Then I check: (1) p-value < 0.05, (2) confidence interval doesn't cross zero, (3) no issues with sample ratio mismatch. I never peek early and make decisions—that inflates false positive rate."

### Q: "What if you check results early?"

> "Peeking inflates Type I error (false positives). If you check 10 times during an experiment at α=0.05, your actual false positive rate can be 30%+. Solutions: (1) Pre-register analysis time, don't peek, (2) Use sequential testing with adjusted thresholds (like O'Brien-Fleming), (3) Use Bayesian methods that don't have the peeking problem."

### Q: "How do you handle multiple variants?"

> "Multiple comparisons inflate false positives. If testing 5 variants, probability of at least one false positive: 1 - 0.95⁵ = 23%. Solutions: (1) Bonferroni correction: α' = α/n = 0.01 per test, (2) Control false discovery rate (FDR), (3) Use a single omnibus test first (ANOVA), then post-hoc tests."

### Q: "What's a sample ratio mismatch (SRM)?"

> "SRM is when actual traffic split differs significantly from intended split. If you expected 50/50 but got 55/45, something is wrong—maybe a bug in assignment, or certain users can't see treatment. I always run a chi-square test on sample sizes before trusting results. SRM invalidates the experiment."

### Q: "How do you handle novelty effects?"

> "Novelty effect is when treatment wins initially because it's 'new', but effect fades. Solutions: (1) Run experiment long enough (2+ weeks), (2) Look at cohorts over time—does lift persist for users who've been exposed longer?, (3) Exclude first few days from analysis."

### Q: "Explain Thompson Sampling"

> "It's a Bayesian bandit algorithm. For each arm, maintain a Beta distribution of success probability (starts as uniform prior). Each round: sample from each distribution, pick highest sample. After observing outcome, update the posterior. It naturally balances exploration (uncertain arms get sampled) and exploitation (good arms get sampled more)."

---

## Architecture Diagram

```
┌───────────────────────────────────────────────────────┐
│                   USER REQUEST                        │
└───────────────────────┬───────────────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  Traffic Router │
              │                 │
              │  hash(user_id)  │
              │  → variant      │
              └────────┬────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
         ▼                           ▼
   ┌──────────┐               ┌──────────┐
   │ Control  │               │Treatment │
   │ Model A  │               │ Model B  │
   │  (90%)   │               │  (10%)   │
   └────┬─────┘               └────┬─────┘
        │                          │
        └──────────┬───────────────┘
                   │
                   ▼
          ┌────────────────┐
          │ Log: user_id,  │
          │ variant,       │
          │ outcome        │
          └───────┬────────┘
                  │
                  ▼
          ┌────────────────┐
          │  Statistical   │
          │   Analysis     │
          │                │
          │ p-value, CI,   │
          │ power          │
          └───────┬────────┘
                  │
                  ▼
          ┌────────────────┐
          │  DECISION:     │
          │  Deploy or     │
          │  Keep Control  │
          └────────────────┘
```

---

## Key Numbers to Memorize

| Metric | Value | Meaning |
|--------|-------|---------|
| p < 0.05 | Significant | 5% chance of false positive |
| Power = 80% | Standard | 80% chance of detecting real effect |
| CI doesn't cross 0 | Significant | Effect is reliably non-zero |
| Z = 1.96 | 95% confidence | Critical value for 2-tailed test |
| Z = 1.64 | 90% confidence | Less stringent threshold |

---

## Red Flags to Avoid

❌ "We saw significance after 2 days, so we stopped"
   → Peeking problem, inflated false positive rate

❌ "We ran 10 variants and 3 were significant"
   → Multiple comparisons problem, 2-3 false positives expected

❌ "Treatment had 55% of traffic but we expected 50%"
   → Sample ratio mismatch, experiment may be invalid

❌ "We rolled out immediately after significance"
   → Consider novelty effects, seasonal effects, run longer

✅ "We pre-registered sample size and analysis plan"
✅ "We corrected for multiple comparisons"
✅ "We verified sample ratio before analyzing"
✅ "We ran for full 2 weeks to avoid novelty effects"

---

## Quick Decision Framework

```
1. Did we hit required sample size?
   NO  → Keep running
   YES → Continue

2. Is there sample ratio mismatch?
   YES → Investigate, possibly invalidate
   NO  → Continue

3. Is p-value < 0.05?
   NO  → No significant difference, keep control
   YES → Continue

4. Is confidence interval entirely positive?
   NO  → Effect could be negative, be cautious
   YES → Treatment wins, deploy
```
