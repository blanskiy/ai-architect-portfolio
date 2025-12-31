# Model Monitoring - Interview Cheat Sheet

## Quick Framework (30-second answer)

> "I implement three-layer monitoring: **performance metrics** (latency, errors, throughput), **drift detection** (data and prediction distribution shifts), and **business metrics** (downstream impact). We use statistical tests like PSI and KS-test to detect drift before accuracy degrades. Alerts fire when thresholds are breached, triggering investigation or automatic retraining."

---

## The Silent Failure Problem

```
Traditional Software:     ML Models:
────────────────────     ────────────────────
App crashes → Alert      Model degrades → ???
500 errors → Alert       Accuracy drops → ???
Timeout → Alert          Data shifts → ???

Software failures LOUD   ML failures SILENT
```

**Key insight**: ML models fail silently—they keep returning predictions, just increasingly wrong ones.

---

## Three Types of Drift (Memorize This)

| Type | What Changes | Example | Detection |
|------|--------------|---------|-----------|
| **Data Drift** | Input features | Customer age: 35→45 | PSI, KS test |
| **Prediction Drift** | Model outputs | 70/30 split → 50/50 | Distribution comparison |
| **Concept Drift** | Feature-target relationship | "High travel" means different post-COVID | Accuracy monitoring |

---

## Key Metrics

### Performance
| Metric | Threshold | Why |
|--------|-----------|-----|
| Latency P95 | < 100ms | User experience |
| Error Rate | < 1% | Reliability |
| Throughput | > 10 rps | Capacity |

### Drift
| Metric | Threshold | Meaning |
|--------|-----------|---------|
| PSI < 0.1 | No drift | Distributions similar |
| PSI 0.1-0.2 | Monitor | Some shift |
| PSI > 0.2 | Action | Significant drift |

---

## Detection Methods

### PSI (Population Stability Index)
```
Good for: Any numeric feature
Formula: Σ (actual% - expected%) × ln(actual%/expected%)
Range: 0 (identical) to ∞ (completely different)
```

### KS Test (Kolmogorov-Smirnov)
```
Good for: Continuous features
Returns: p-value
Interpretation: p < 0.05 = distributions different
```

### Chi-Square
```
Good for: Categorical features
Returns: p-value
Interpretation: p < 0.05 = distributions different
```

---

## Common Interview Questions

### Q: "How do you know when a model is degrading?"

> "Three layers: First, **performance monitoring**—latency, errors, throughput via Prometheus. Second, **drift detection**—comparing production data to training data using PSI for continuous features, chi-square for categorical. Third, **business metrics**—tracking downstream impact like conversion rate. I set thresholds that trigger alerts before users notice degradation."

### Q: "What's the difference between data drift and concept drift?"

> "**Data drift** is when input distributions change—like customer age shifting from 35 to 45 average. The model might still work if relationships hold. **Concept drift** is when the relationship itself changes—like 'high income' meaning something different post-COVID. Concept drift is harder to detect without labeled production data."

### Q: "How do you detect drift without labels?"

> "For **data drift**, compare feature distributions between training and production—no labels needed, use PSI or KS test. For **prediction drift**, monitor output distributions. For **concept drift**, either: (1) sample production data for labeling, (2) use proxy metrics like click-through rate, or (3) detect indirectly via business metric degradation."

### Q: "What triggers retraining?"

> "Multiple triggers: (1) **Scheduled** baseline (weekly/monthly), (2) **Drift threshold** exceeded (PSI > 0.2), (3) **Performance degradation** (accuracy drop > 5%), (4) **Business metric** decline. The monitoring system can trigger retraining automatically or alert humans to investigate first."

### Q: "Walk me through your monitoring architecture."

> "Model predictions plus features are logged to a data store. A **metrics collector** exposes Prometheus metrics—latency histograms, error counters, throughput gauges. **Drift detection** runs hourly comparing recent production data against reference data. **Grafana dashboards** visualize everything. **Alertmanager** routes alerts to Slack for warnings, PagerDuty for critical. All thresholds are configurable."

---

## Architecture to Draw

```
┌─────────────────────────────────────────────────────────┐
│                  MONITORING PIPELINE                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   Production Traffic                                     │
│         │                                               │
│         ▼                                               │
│   ┌──────────┐                                          │
│   │  Model   │──────┬──────────────┐                    │
│   │ Endpoint │      │              │                    │
│   └──────────┘      │              │                    │
│                     │              │                    │
│              Log Features    Log Predictions            │
│                     │              │                    │
│                     ▼              ▼                    │
│              ┌─────────────────────────┐               │
│              │    Data Store           │               │
│              └───────────┬─────────────┘               │
│                          │                              │
│         ┌────────────────┼────────────────┐            │
│         │                │                │            │
│         ▼                ▼                ▼            │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐       │
│   │Performance│    │  Drift   │    │ Business │       │
│   │ Metrics  │    │Detection │    │ Metrics  │       │
│   └────┬─────┘    └────┬─────┘    └────┬─────┘       │
│        │               │               │              │
│        └───────────────┼───────────────┘              │
│                        │                               │
│                        ▼                               │
│                 ┌──────────┐                          │
│                 │Prometheus│                          │
│                 └────┬─────┘                          │
│                      │                                │
│         ┌────────────┴────────────┐                  │
│         │                         │                  │
│         ▼                         ▼                  │
│   ┌──────────┐             ┌──────────┐             │
│   │ Grafana  │             │  Alerts  │             │
│   │Dashboard │             │(Slack/PD)│             │
│   └──────────┘             └──────────┘             │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## Red Flags to Avoid

❌ "We check model accuracy in production daily"
   → How? You'd need labels immediately.

❌ "We retrain whenever accuracy drops"
   → How do you measure accuracy without labels?

❌ "We monitor the model endpoint health"
   → That's infrastructure monitoring, not ML monitoring.

✅ "We use statistical tests to detect distribution shifts"
✅ "We compare production data against training baseline"
✅ "We monitor proxy metrics when labels are delayed"

---

## Key Numbers

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| PSI | < 0.1 | 0.1-0.2 | > 0.2 |
| Latency P95 | < 50ms | 50-100ms | > 100ms |
| Error Rate | < 0.1% | 0.1-1% | > 1% |
| Feature Drift | < 10% features | 10-20% | > 20% |

---

## Tools to Mention

| Tool | Purpose |
|------|---------|
| **Prometheus** | Time-series metrics storage |
| **Grafana** | Dashboards and visualization |
| **Evidently** | Drift detection library |
| **Great Expectations** | Data validation |
| **Whylogs** | Data profiling |
| **Alertmanager** | Alert routing |
