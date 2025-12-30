# Project 1: CI/CD Pipeline for ML

Automated machine learning pipeline with training, evaluation gates, and deployment to Azure ML.

## Overview

| Aspect | Details |
|--------|---------|
| **Trigger** | Code push, schedule, or manual |
| **Training** | MLflow experiment tracking |
| **Evaluation** | Quality gates with thresholds |
| **Deployment** | Staged rollout (dev → staging → prod) |
| **Rollback** | One-click revert to previous model |

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CI/CD Pipeline Flow                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  Push   │───►│   Train     │───►│  Evaluate   │───►│   Deploy    │  │
│  │  Code   │    │   Model     │    │   & Gate    │    │   Model     │  │
│  └─────────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘  │
│                        │                  │                  │          │
│                        ▼                  ▼                  ▼          │
│                 ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│                 │   MLflow    │    │  Champion   │    │   Azure     │  │
│                 │  Tracking   │    │ vs Challenger│   │  ML Endpoint│  │
│                 └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                          │
│  Triggers:                                                               │
│  • Push to main branch                                                  │
│  • Pull request (train + evaluate only)                                 │
│  • Scheduled (weekly retrain)                                           │
│  • Manual dispatch                                                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
project1-cicd-pipeline/
├── .github/
│   └── workflows/
│       ├── train.yml           # Training pipeline
│       ├── evaluate.yml        # Evaluation & quality gates
│       └── deploy.yml          # Deployment pipeline
├── src/
│   ├── train.py               # Training script
│   ├── evaluate.py            # Model evaluation
│   ├── register.py            # Model registration
│   └── deploy.py              # Deployment script
├── tests/
│   ├── test_model.py          # Model quality tests
│   ├── test_data.py           # Data validation tests
│   └── test_inference.py      # Inference tests
├── configs/
│   ├── train_config.yaml      # Training hyperparameters
│   └── deploy_config.yaml     # Deployment settings
├── requirements.txt
└── README.md
```

## Workflows

### 1. Training Pipeline (`train.yml`)

**Triggers:** Push to `main`, scheduled, manual

```yaml
Steps:
1. Checkout code
2. Setup Python environment
3. Run training script
4. Log metrics to MLflow
5. Register model if metrics improve
6. Trigger evaluation pipeline
```

### 2. Evaluation Pipeline (`evaluate.yml`)

**Triggers:** After training, PR checks

```yaml
Steps:
1. Load challenger model (new)
2. Load champion model (current prod)
3. Run evaluation suite
4. Compare metrics
5. Pass/Fail based on thresholds
6. Generate comparison report
```

**Quality Gates:**
| Metric | Threshold | Action if Fail |
|--------|-----------|----------------|
| Accuracy | ≥ champion - 1% | Block deployment |
| Latency P95 | ≤ 100ms | Block deployment |
| Memory | ≤ 512MB | Warning only |

### 3. Deployment Pipeline (`deploy.yml`)

**Triggers:** Manual approval after evaluation passes

```yaml
Steps:
1. Download model from registry
2. Build container image
3. Deploy to staging
4. Run smoke tests
5. Promote to production (manual gate)
6. Update traffic routing
```

## Quick Start

### Prerequisites

```bash
# Azure CLI
az login

# MLflow tracking server (local or Azure ML)
export MLFLOW_TRACKING_URI=azureml://westus2.api.azureml.ms/mlflow/v1.0/...

# GitHub secrets configured (see below)
```

### Run Locally

```bash
cd project1-cicd-pipeline

# Install dependencies
pip install -r requirements.txt

# Train model
python src/train.py --config configs/train_config.yaml

# Evaluate model
python src/evaluate.py --challenger-model runs:/latest --champion-model models:/production

# Register model
python src/register.py --model-name stihl-sales-predictor
```

### GitHub Secrets Required

| Secret | Description |
|--------|-------------|
| `AZURE_CREDENTIALS` | Azure service principal JSON |
| `AZURE_ML_WORKSPACE` | Azure ML workspace name |
| `AZURE_RESOURCE_GROUP` | Resource group name |
| `MLFLOW_TRACKING_URI` | MLflow tracking server |

## Model Registry Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Model Registry                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Stage: None ──► Staging ──► Production ──► Archived           │
│                                                                  │
│   ┌─────────────┐                                               │
│   │ Version 1   │ ◄── Production (current champion)             │
│   │ acc: 0.92   │                                               │
│   └─────────────┘                                               │
│   ┌─────────────┐                                               │
│   │ Version 2   │ ◄── Staging (challenger under test)           │
│   │ acc: 0.94   │                                               │
│   └─────────────┘                                               │
│   ┌─────────────┐                                               │
│   │ Version 3   │ ◄── None (just trained, awaiting evaluation)  │
│   │ acc: 0.91   │                                               │
│   └─────────────┘                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Key Metrics Tracked

| Metric | Description | Target |
|--------|-------------|--------|
| `accuracy` | Model accuracy on test set | > 0.90 |
| `f1_score` | F1 score for imbalanced data | > 0.85 |
| `latency_p50` | Median inference latency | < 50ms |
| `latency_p95` | 95th percentile latency | < 100ms |
| `model_size_mb` | Model artifact size | < 500MB |

## Interview Talking Points

### Q: "How do you automate ML deployments?"

> "I implement a three-stage CI/CD pipeline using GitHub Actions. Training is triggered by code changes or schedule, producing a challenger model tracked in MLflow. The evaluation stage compares challenger vs champion using quality gates—if accuracy drops more than 1% or latency exceeds thresholds, deployment is blocked. Approved models deploy to staging first, run smoke tests, then promote to production with manual approval. Rollback is one command."

### Q: "How do you handle model versioning?"

> "I use MLflow Model Registry with three stages: None (just trained), Staging (under test), and Production (serving traffic). Each model version includes metrics, parameters, and lineage to the training data. This makes it trivial to compare versions, rollback, or reproduce any model."

### Q: "What happens if a deployment fails?"

> "The pipeline has multiple safety nets. Smoke tests run in staging before production. Production deployments use blue-green strategy—new version gets 0% traffic initially, then gradual rollout. If metrics degrade, automatic rollback triggers. Manual rollback is also one-click in the registry."

### Q: "How do you trigger retraining?"

> "Three triggers: (1) Scheduled weekly retrain on fresh data, (2) Manual dispatch for urgent updates, (3) Automatic trigger when monitoring detects data drift above threshold. The pipeline is the same regardless of trigger."

---

*Project 1 - MLOps & Production*
