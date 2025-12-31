# Project 2: Model Monitoring & Observability

Production monitoring for ML models: performance tracking, drift detection, and alerting.

## Overview

| Aspect | Details |
|--------|---------|
| **Purpose** | Detect model degradation before users notice |
| **Key Metrics** | Accuracy, latency, throughput, drift scores |
| **Tools** | Prometheus, Grafana, Evidently, Custom Python |
| **Alerts** | Slack/PagerDuty when thresholds breached |

## Why Model Monitoring?

### The Silent Failure Problem

```
Traditional Software:           ML Models:
─────────────────────          ─────────────────────
App crashes → Alert            Model degrades → ???
500 errors → Alert             Accuracy drops → ???
Timeout → Alert                Data shifts → ???

Software failures are LOUD     ML failures are SILENT
```

**ML models fail silently**: They keep returning predictions, just increasingly wrong ones.

### Real-World Example

```
Month 1: Model trained on summer data, 95% accuracy ✅
Month 4: Fall arrives, customer behavior changes
Month 5: Accuracy dropped to 78%, nobody noticed ❌
Month 6: Business complains about poor recommendations
Month 7: Finally investigate, retrain model

Cost: 3 months of degraded service
```

**With monitoring**: Alert at Month 4, retrain immediately.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MODEL MONITORING SYSTEM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Production Traffic                                                         │
│         │                                                                    │
│         ▼                                                                    │
│   ┌───────────┐     ┌───────────────┐     ┌───────────────┐                │
│   │  Model    │────►│  Prediction   │────►│   Response    │                │
│   │  Endpoint │     │  + Features   │     │   to User     │                │
│   └─────┬─────┘     └───────┬───────┘     └───────────────┘                │
│         │                   │                                               │
│         │    Log Everything │                                               │
│         ▼                   ▼                                               │
│   ┌─────────────────────────────────────┐                                  │
│   │         Monitoring Pipeline          │                                  │
│   │                                       │                                  │
│   │  ┌─────────────┐  ┌─────────────┐   │                                  │
│   │  │ Performance │  │    Drift    │   │                                  │
│   │  │  Metrics    │  │  Detection  │   │                                  │
│   │  │             │  │             │   │                                  │
│   │  │ • Latency   │  │ • Data Drift│   │                                  │
│   │  │ • Throughput│  │ • Pred Drift│   │                                  │
│   │  │ • Errors    │  │ • Concept   │   │                                  │
│   │  └──────┬──────┘  └──────┬──────┘   │                                  │
│   │         │                │          │                                  │
│   └─────────┼────────────────┼──────────┘                                  │
│             │                │                                              │
│             ▼                ▼                                              │
│   ┌─────────────────────────────────────┐                                  │
│   │           Prometheus                 │                                  │
│   │     (Time-series Database)          │                                  │
│   └─────────────────┬───────────────────┘                                  │
│                     │                                                       │
│         ┌───────────┴───────────┐                                          │
│         │                       │                                          │
│         ▼                       ▼                                          │
│   ┌───────────┐          ┌───────────┐                                     │
│   │  Grafana  │          │  Alerts   │                                     │
│   │ Dashboard │          │  (Slack)  │                                     │
│   └───────────┘          └───────────┘                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
project2-model-monitoring/
├── README.md
├── LEARNING_GUIDE.md
├── requirements.txt
├── src/
│   ├── metrics_collector.py      # Collect model metrics
│   ├── drift_detector.py         # Detect data/prediction drift
│   ├── performance_monitor.py    # Track latency, throughput
│   └── alerting.py               # Send alerts
├── dashboards/
│   └── grafana_model_health.json # Grafana dashboard config
├── alerts/
│   └── alert_rules.yaml          # Prometheus alert rules
├── configs/
│   └── monitoring_config.yaml    # Thresholds and settings
└── tests/
    └── test_drift_detection.py
```

## Three Types of Drift

### 1. Data Drift (Feature Drift)
**What**: Input feature distributions change over time.

```
Training Data:              Production Data:
─────────────              ─────────────────
age: mean=35, std=10       age: mean=45, std=15  ← DRIFT!
income: mean=$50K          income: mean=$75K     ← DRIFT!
```

**Cause**: Customer demographics changed, seasonality, market shifts.

**Detection**: Compare feature distributions using statistical tests (KS test, PSI).

### 2. Prediction Drift (Output Drift)
**What**: Model predictions distribution changes.

```
Training Period:            Production:
────────────────           ─────────────
70% class 0, 30% class 1   50% class 0, 50% class 1  ← DRIFT!
```

**Cause**: Could be data drift, or model is behaving differently.

**Detection**: Compare prediction distributions over time.

### 3. Concept Drift
**What**: The relationship between features and target changes.

```
Before COVID:                 After COVID:
─────────────                ─────────────
High travel spend → Affluent  High travel spend → Rare (lockdowns)
Same features, different meaning!
```

**Cause**: World changed, relationships no longer hold.

**Detection**: Monitor accuracy on labeled data (if available).

## Key Metrics

### Performance Metrics
| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `model_latency_p50` | Median response time | > 100ms |
| `model_latency_p99` | 99th percentile | > 500ms |
| `model_throughput` | Predictions/second | < 100 |
| `model_error_rate` | Failed predictions | > 1% |

### Drift Metrics
| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `data_drift_score` | Overall feature drift | > 0.1 |
| `prediction_drift_score` | Output distribution shift | > 0.15 |
| `feature_drift_*` | Per-feature drift scores | > 0.2 |

### Business Metrics
| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `conversion_rate` | Downstream business impact | -10% vs baseline |
| `revenue_per_prediction` | Value generated | -15% vs baseline |

## Quick Start

### 1. Install Dependencies
```bash
cd project2-model-monitoring
pip install -r requirements.txt
```

### 2. Run Drift Detection
```bash
python src/drift_detector.py \
    --reference-data data/training_sample.csv \
    --current-data data/production_sample.csv \
    --output-file drift_report.json
```

### 3. Start Metrics Collection
```bash
python src/metrics_collector.py \
    --endpoint-url https://model.azureml.net/score \
    --prometheus-port 8000
```

### 4. View Dashboard
```bash
# Start Grafana (Docker)
docker-compose up -d grafana

# Open http://localhost:3000
# Import dashboards/grafana_model_health.json
```

## Interview Talking Points

### Q: "How do you know when a model is degrading in production?"

> "I implement three-layer monitoring: **performance metrics** (latency, errors), **drift detection** (data and prediction distribution shifts), and **business metrics** (downstream impact). We use statistical tests like PSI and KS-test to detect drift before accuracy degrades. Alerts fire when drift scores exceed thresholds, triggering investigation or automatic retraining."

### Q: "What's the difference between data drift and concept drift?"

> "**Data drift** is when input distributions change—like customer age shifting from 35 to 45 on average. The model might still work if the relationship holds. **Concept drift** is when the relationship between features and target changes—like 'high income' meaning something different post-COVID. Concept drift is harder to detect without ground truth labels."

### Q: "How do you detect drift without labeled production data?"

> "For data drift, we compare feature distributions between training and production using statistical tests—no labels needed. For prediction drift, we monitor output distributions. For concept drift, we either sample production data for labeling, use proxy metrics (like click-through rate), or detect it indirectly through business metric degradation."

---

*Project 2 - MLOps & Production*
