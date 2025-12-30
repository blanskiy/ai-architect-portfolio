# CI/CD Pipeline for ML - Complete Learning Guide

## Table of Contents
1. [Why CI/CD for ML?](#1-why-cicd-for-ml)
2. [Pipeline Overview](#2-pipeline-overview)
3. [Stage 1: Training Pipeline](#3-stage-1-training-pipeline)
4. [Stage 2: Evaluation Pipeline](#4-stage-2-evaluation-pipeline)
5. [Stage 3: Deployment Pipeline](#5-stage-3-deployment-pipeline)
6. [Model Registry Concepts](#6-model-registry-concepts)
7. [Quality Gates Deep Dive](#7-quality-gates-deep-dive)
8. [End-to-End Flow Example](#8-end-to-end-flow-example)
9. [Key Concepts Summary](#9-key-concepts-summary)

---

## 1. Why CI/CD for ML?

### Traditional Software CI/CD
```
Code Change → Build → Test → Deploy
```
- **Trigger**: Code changes only
- **Artifact**: Application binary
- **Validation**: Unit tests pass/fail (boolean)
- **Rollback**: Revert code commit

### ML CI/CD (What We Build)
```
Code OR Data Change → Train → Evaluate → Deploy
```
- **Trigger**: Code changes OR data changes OR schedule
- **Artifact**: Model file + metadata
- **Validation**: Quality metrics (statistical thresholds)
- **Rollback**: Swap model versions (not code)

### Key Differences

| Aspect | Software CI/CD | ML CI/CD |
|--------|---------------|----------|
| What triggers pipeline? | Code push | Code, data, schedule, drift |
| What is built? | Binary/container | Model artifact |
| How is quality measured? | Tests pass/fail | Accuracy ≥ threshold |
| What is versioned? | Code | Code + Data + Model |
| What is deployed? | Application | Model endpoint |
| How to rollback? | git revert | Swap model version |

### Why This Matters for Interviews

> "ML CI/CD is fundamentally different because we're dealing with **statistical artifacts** rather than deterministic code. A code change either works or doesn't—but a model can work 'somewhat well' or degrade gradually. That's why we need **quality gates with thresholds** rather than boolean pass/fail tests."

---

## 2. Pipeline Overview

### The Three Stages

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   STAGE 1: TRAIN          STAGE 2: EVALUATE         STAGE 3: DEPLOY        │
│   ================        ==================        ================        │
│                                                                             │
│   ┌─────────────┐         ┌─────────────┐          ┌─────────────┐         │
│   │ Load Data   │         │Load Champion│          │ Deploy to   │         │
│   │     ↓       │         │ (Current    │          │  Staging    │         │
│   │ Train Model │         │  Prod)      │          │     ↓       │         │
│   │     ↓       │         │     ↓       │          │ Smoke Tests │         │
│   │ Log Metrics │         │ Compare vs  │          │     ↓       │         │
│   │ to MLflow   │         │ Challenger  │          │ Deploy to   │         │
│   │     ↓       │         │ (New Model) │          │ Production  │         │
│   │ Register    │         │     ↓       │          │     ↓       │         │
│   │ Model       │         │Quality Gates│          │Traffic Shift│         │
│   └─────────────┘         └─────────────┘          └─────────────┘         │
│         │                       │                        │                  │
│         ▼                       ▼                        ▼                  │
│   Model in Registry       PASS → Continue           Model Serving          │
│   (Stage: None)           FAIL → Block              (100% Traffic)         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### What Triggers Each Stage?

| Stage | Triggered By | Automatic? |
|-------|--------------|------------|
| Train | Code push, schedule, manual | Yes |
| Evaluate | Training completion, PR | Yes |
| Deploy | Manual approval after evaluation | No (requires human) |

### Why Manual Deployment Approval?

Even if evaluation passes, we want a human to:
1. Review the evaluation report
2. Confirm timing is appropriate (not during peak hours)
3. Be available to monitor rollout
4. Take responsibility for production changes

---

## 3. Stage 1: Training Pipeline

### File: `.github/workflows/train.yml`

### Purpose
Train a new model and register it for evaluation.

### Step-by-Step Breakdown

#### Step 1: Checkout Code
```yaml
- name: Checkout code
  uses: actions/checkout@v4
```

**What it does**: Downloads your repository code to the GitHub Actions runner.

**Why needed**: The runner starts empty—it needs your training scripts, configs, etc.

**Outcome**: All files from your repo are now available at `/github/workspace/`

---

#### Step 2: Setup Python
```yaml
- name: Setup Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'
```

**What it does**: 
- Installs Python 3.11 on the runner
- Caches pip packages between runs (faster subsequent runs)

**Why needed**: GitHub runners don't have Python configured by default.

**Outcome**: `python` and `pip` commands are available.

---

#### Step 3: Install Dependencies
```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements.txt
```

**What it does**: Installs all packages listed in requirements.txt.

**Why needed**: Your training code depends on sklearn, mlflow, pandas, etc.

**Outcome**: All Python packages are installed and importable.

---

#### Step 4: Azure Login
```yaml
- name: Azure Login
  uses: azure/login@v2
  with:
    creds: ${{ secrets.AZURE_CREDENTIALS }}
```

**What it does**: Authenticates the runner with Azure using a service principal.

**Why needed**: 
- MLflow tracking server might be on Azure ML
- Model deployment will be to Azure

**Outcome**: Subsequent Azure commands will work without prompting for credentials.

**Secret format** (`AZURE_CREDENTIALS`):
```json
{
  "clientId": "xxx",
  "clientSecret": "xxx",
  "subscriptionId": "xxx",
  "tenantId": "xxx"
}
```

---

#### Step 5: Run Training
```yaml
- name: Run Training
  id: train
  run: |
    python src/train.py \
      --config configs/train_config.yaml \
      --experiment-name stihl-sales-model \
      --output-file training_output.json
    
    echo "run_id=$(jq -r '.run_id' training_output.json)" >> $GITHUB_OUTPUT
    echo "model_uri=$(jq -r '.model_uri' training_output.json)" >> $GITHUB_OUTPUT
    echo "accuracy=$(jq -r '.metrics.accuracy' training_output.json)" >> $GITHUB_OUTPUT
```

**What it does**:
1. Runs your training script with config
2. Saves results to JSON file
3. Extracts key values for downstream jobs

**Why `$GITHUB_OUTPUT`**: This passes values to later jobs in the workflow. Without this, the register job wouldn't know which model to register.

**Outcome**: 
- Model trained and logged to MLflow
- Metrics recorded (accuracy, latency, etc.)
- `training_output.json` contains:
  ```json
  {
    "run_id": "abc123",
    "model_uri": "runs:/abc123/model",
    "metrics": {
      "accuracy": 0.92,
      "f1_score": 0.89,
      "latency_p95_ms": 45
    }
  }
  ```

---

#### Step 6: Register Model (Conditional)
```yaml
register:
  needs: train
  if: ${{ needs.train.outputs.accuracy >= 0.85 }}
```

**What it does**: Only runs if accuracy ≥ 85%.

**Why conditional**: No point registering a bad model. This is a **preliminary gate**—not the full evaluation, but a quick filter.

**Outcome**: 
- If accuracy < 85%: Pipeline stops here. No model registered.
- If accuracy ≥ 85%: Model registered to MLflow Model Registry.

---

### Training Script Deep Dive (`src/train.py`)

```python
def train(config: dict, experiment_name: str) -> dict:
    # 1. Set MLflow experiment (groups related runs)
    mlflow.set_experiment(experiment_name)
    
    # 2. Load and split data
    X, y = load_data(config['data_path'])
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    
    # 3. Start MLflow run (creates unique run_id)
    with mlflow.start_run() as run:
        # 4. Log parameters (for reproducibility)
        mlflow.log_param('model_type', 'random_forest')
        mlflow.log_params(config['model_params'])
        
        # 5. Train model
        model = RandomForestClassifier(**config['model_params'])
        model.fit(X_train, y_train)
        
        # 6. Evaluate and log metrics
        metrics = evaluate_model(model, X_test, y_test)
        for name, value in metrics.items():
            mlflow.log_metric(name, value)
        
        # 7. Log model artifact
        mlflow.sklearn.log_model(model, "model")
        
        # 8. Return info for downstream jobs
        return {
            'run_id': run.info.run_id,
            'model_uri': f"runs:/{run.info.run_id}/model",
            'metrics': metrics
        }
```

**Key Concept - MLflow Tracking**:
```
Experiment: "stihl-sales-model"
├── Run: abc123 (trained Dec 30, accuracy=0.92)
│   ├── Parameters: {model_type: "rf", n_estimators: 100}
│   ├── Metrics: {accuracy: 0.92, latency_p95: 45ms}
│   └── Artifacts: model/, requirements.txt
├── Run: def456 (trained Dec 29, accuracy=0.89)
└── Run: ghi789 (trained Dec 28, accuracy=0.91)
```

---

## 4. Stage 2: Evaluation Pipeline

### File: `.github/workflows/evaluate.yml`

### Purpose
Compare the new "challenger" model against the current "champion" (production) model.

### The Champion vs Challenger Pattern

```
                    ┌─────────────────┐
                    │   Test Data     │
                    │   (Held Out)    │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
     ┌─────────────────┐          ┌─────────────────┐
     │    CHAMPION     │          │   CHALLENGER    │
     │  (Production)   │          │    (New)        │
     │                 │          │                 │
     │  Accuracy: 91%  │          │  Accuracy: 93%  │
     │  Latency: 50ms  │          │  Latency: 48ms  │
     └─────────────────┘          └─────────────────┘
              │                             │
              └──────────────┬──────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    COMPARE      │
                    │                 │
                    │ Challenger > Champion?
                    │ By how much?    │
                    │ Within limits?  │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
     ┌─────────────────┐          ┌─────────────────┐
     │      PASS       │          │      FAIL       │
     │                 │          │                 │
     │ → Continue to   │          │ → Block deploy  │
     │   deployment    │          │ → Notify team   │
     └─────────────────┘          └─────────────────┘
```

### Why Compare Against Champion?

**Not just**: "Is the new model good enough?" (absolute threshold)
**But also**: "Is it better than what we have?" (relative comparison)

**Example**:
- New model: 87% accuracy (passes 85% threshold)
- Current prod: 91% accuracy
- **Should we deploy?** NO! It's a regression.

---

### Step-by-Step Breakdown

#### Step 1: Load Champion Model
```yaml
- name: Load Champion Model
  run: |
    python src/get_champion.py \
      --model-name "stihl-sales-model" \
      --output-file champion_info.json
```

**What it does**: Gets the current production model from MLflow registry.

**MLflow Registry Stages**:
```
Model: "stihl-sales-model"
├── Version 3: Stage=Production  ← This is the CHAMPION
├── Version 2: Stage=Archived
└── Version 1: Stage=Archived
```

**Outcome**: `champion_info.json` contains:
```json
{
  "version": 3,
  "metrics": {"accuracy": 0.91},
  "model_uri": "models:/stihl-sales-model/Production"
}
```

---

#### Step 2: Evaluate Both Models
```yaml
- name: Evaluate Challenger
  run: |
    python src/evaluate.py \
      --challenger-uri "runs:/abc123/model" \
      --champion-model "models:/stihl-sales-model/Production" \
      --test-data "data/eval/"
```

**What it does**:
1. Loads challenger model (just trained)
2. Loads champion model (current production)
3. Runs both on same test data
4. Measures accuracy, latency, etc.

**Critical**: Uses HELD-OUT test data that was NOT used in training.

**Outcome**: `evaluation_results.json`:
```json
{
  "challenger": {
    "accuracy": 0.93,
    "latency_p95_ms": 48
  },
  "champion": {
    "accuracy": 0.91,
    "latency_p95_ms": 50
  },
  "comparison": {
    "accuracy_diff": +0.02,
    "challenger_is_better": true
  }
}
```

---

#### Step 3: Quality Gate Check
```yaml
- name: Quality Gate Check
  run: |
    python src/quality_gate.py \
      --results evaluation_results.json \
      --min-accuracy 0.85 \
      --max-accuracy-drop 0.01 \
      --max-latency-p95 100
```

**What it does**: Checks multiple conditions and passes/fails.

---

## 5. Quality Gates Deep Dive

### What is a Quality Gate?

A **checkpoint** that must pass before proceeding. Like a security guard checking IDs.

### Our Quality Gates

| Gate | Threshold | Type | Severity |
|------|-----------|------|----------|
| Minimum Accuracy | ≥ 85% | Absolute | Blocker |
| Accuracy Drop | ≤ 1% vs champion | Relative | Blocker |
| Latency P95 | ≤ 100ms | Absolute | Blocker |
| Model Size | ≤ 500MB | Absolute | Warning |

### Gate Types Explained

#### Absolute Gate
"Is the metric above/below a fixed threshold?"

```python
# Example: Minimum accuracy
if challenger_accuracy >= 0.85:
    PASS
else:
    FAIL  # "Model accuracy 0.82 is below minimum 0.85"
```

**Use case**: Setting a floor—"We never deploy models below this quality."

#### Relative Gate
"Is the metric better/worse than the current production?"

```python
# Example: Accuracy drop
accuracy_diff = challenger_accuracy - champion_accuracy

if accuracy_diff >= -0.01:  # Allow up to 1% drop
    PASS
else:
    FAIL  # "Model accuracy dropped 3% vs production"
```

**Use case**: Preventing regressions—"Don't make things worse."

### Severity Levels

#### Blocker
Pipeline STOPS. Model will NOT be deployed.

```python
if not passed and severity == 'blocker':
    sys.exit(1)  # GitHub Actions fails the job
```

#### Warning
Pipeline continues but team is notified.

```python
if not passed and severity == 'warning':
    print("⚠️ Warning: Model size exceeds recommendation")
    # Continue anyway
```

### Quality Gate Code Explained

```python
def check_quality_gates(results, thresholds):
    checks = []
    
    # Gate 1: Minimum accuracy (absolute)
    accuracy = results['challenger']['accuracy']
    checks.append({
        'name': 'minimum_accuracy',
        'passed': accuracy >= thresholds['min_accuracy'],
        'actual': accuracy,
        'threshold': thresholds['min_accuracy'],
        'severity': 'blocker',
        'message': f"Accuracy {accuracy:.2%} {'≥' if passed else '<'} {thresholds['min_accuracy']:.2%}"
    })
    
    # Gate 2: Accuracy drop (relative)
    accuracy_diff = results['comparison']['accuracy_diff']
    max_drop = -thresholds['max_accuracy_drop']
    checks.append({
        'name': 'accuracy_drop',
        'passed': accuracy_diff >= max_drop,
        'actual': accuracy_diff,
        'threshold': max_drop,
        'severity': 'blocker',
        'message': f"Accuracy diff {accuracy_diff:+.2%} {'≥' if passed else '<'} {max_drop:+.2%}"
    })
    
    # Final decision: ALL blockers must pass
    blockers_passed = all(c['passed'] for c in checks if c['severity'] == 'blocker')
    
    return blockers_passed, checks
```

### Gate Report Example

```
============================================================
🔒 QUALITY GATE REPORT
============================================================

✅ MINIMUM_ACCURACY
   Accuracy 93.0% ≥ 85.0%
   Severity: blocker

✅ ACCURACY_DROP
   Accuracy diff +2.0% ≥ -1.0%
   Severity: blocker

✅ LATENCY_P95
   Latency P95 48ms ≤ 100ms
   Severity: blocker

⚠️ MODEL_SIZE
   Model size 520MB > 500MB
   Severity: warning

------------------------------------------------------------
✅ QUALITY GATE: PASSED
   Model is approved for deployment
============================================================
```

---

## 6. Stage 3: Deployment Pipeline

### File: `.github/workflows/deploy.yml`

### Purpose
Safely deploy the approved model to production.

### Deployment Strategies

#### Strategy 1: Rolling Deployment
```
Old Model ████████████████ 100%
                ↓
Old Model ████████████     75%
New Model ████             25%
                ↓
Old Model ████████         50%
New Model ████████         50%
                ↓
Old Model ████             25%
New Model ████████████     75%
                ↓
New Model ████████████████ 100%
```

**Pros**: Simple, gradual
**Cons**: Both versions run simultaneously

#### Strategy 2: Blue-Green Deployment (What We Use)
```
Environment A (Blue):  Old Model ████████████████ 100%
Environment B (Green): New Model (standby)

                        ↓ Switch traffic

Environment A (Blue):  Old Model (standby, ready for rollback)
Environment B (Green): New Model ████████████████ 100%
```

**Pros**: Instant rollback, clean separation
**Cons**: Need 2x resources during transition

### Step-by-Step Breakdown

#### Step 1: Deploy to Staging
```yaml
deploy-staging:
  environment: staging  # GitHub Environment (can have protection rules)
```

**What it does**: Deploys model to a non-production endpoint for testing.

**Why staging first**: 
- Test in production-like environment
- Catch issues before affecting users
- Validate smoke tests pass

**Outcome**: Model running at `https://model-staging.azureml.net/score`

---

#### Step 2: Smoke Tests
```yaml
- name: Run Smoke Tests
  run: |
    python tests/smoke_test.py \
      --endpoint-url "${{ steps.deploy.outputs.endpoint_url }}"
```

**What are smoke tests?**
Quick sanity checks that the model is working at all.

```python
# Example smoke tests
def test_endpoint_responds():
    response = requests.post(endpoint_url, json=sample_input)
    assert response.status_code == 200

def test_returns_valid_prediction():
    response = requests.post(endpoint_url, json=sample_input)
    prediction = response.json()
    assert 'prediction' in prediction
    assert prediction['prediction'] in [0, 1]

def test_latency_acceptable():
    start = time.time()
    response = requests.post(endpoint_url, json=sample_input)
    latency = time.time() - start
    assert latency < 1.0  # Under 1 second
```

**Why smoke tests ≠ evaluation**:
- Evaluation: "Is the model accurate?"
- Smoke tests: "Is the deployment working?"

---

#### Step 3: Manual Approval Gate
```yaml
deploy-production:
  environment: production  # Requires manual approval in GitHub
```

**What it does**: Pauses the pipeline until a human approves.

**GitHub Environment Protection Rules**:
1. Go to repo Settings → Environments → production
2. Add "Required reviewers"
3. Optionally: Add wait timer, restrict branches

**Why manual approval**:
- Human judgment for timing (not during peak hours)
- Accountability (someone owns the decision)
- Last chance to catch issues

---

#### Step 4: Deploy to Production with Gradual Rollout
```yaml
- name: Gradual Traffic Rollout
  run: |
    for PERCENT in 10 50 100; do
      python src/update_traffic.py \
        --deployment-name new-deployment \
        --traffic-percent $PERCENT
      
      sleep 60  # Wait and monitor
      python src/check_health.py  # Verify metrics
    done
```

**Traffic Shifting Timeline**:
```
Time 0:00  - New model gets 10% traffic
            - Monitor error rates, latency
Time 1:00  - If healthy, increase to 50%
            - Monitor again
Time 2:00  - If healthy, increase to 100%
            - Old model now standby
```

**What to monitor during rollout**:
- Error rate (should not increase)
- Latency (should not increase)
- Prediction distribution (should be similar)

---

#### Step 5: Update Model Registry
```yaml
- name: Update Model Registry Stage
  run: |
    # Promote new model to Production
    python src/update_model_stage.py \
      --model-version 4 \
      --stage "Production"
    
    # Archive old model
    python src/update_model_stage.py \
      --model-version 3 \
      --stage "Archived"
```

**Before**:
```
Version 4: Stage=Staging   ← New model
Version 3: Stage=Production ← Old model
```

**After**:
```
Version 4: Stage=Production ← New model (now serving)
Version 3: Stage=Archived   ← Old model (kept for rollback)
```

---

## 7. Model Registry Concepts

### What is a Model Registry?

A **versioned database** of trained models with metadata.

```
MLflow Model Registry
│
├── Model: "stihl-sales-model"
│   ├── Version 1 (archived)
│   │   ├── Metrics: accuracy=0.85
│   │   ├── Created: 2024-12-01
│   │   └── Artifact: s3://bucket/models/v1/
│   │
│   ├── Version 2 (archived)
│   │   ├── Metrics: accuracy=0.89
│   │   ├── Created: 2024-12-15
│   │   └── Artifact: s3://bucket/models/v2/
│   │
│   ├── Version 3 (archived)
│   │   ├── Metrics: accuracy=0.91
│   │   ├── Created: 2024-12-28
│   │   └── Artifact: s3://bucket/models/v3/
│   │
│   └── Version 4 (production)  ← CURRENT
│       ├── Metrics: accuracy=0.93
│       ├── Created: 2024-12-30
│       └── Artifact: s3://bucket/models/v4/
│
└── Model: "another-model"
    └── ...
```

### Stage Transitions

```
        ┌──────────────────────────────────────────────┐
        │                                              │
        │    None ──────► Staging ──────► Production   │
        │      ▲            │                │         │
        │      │            │                │         │
        │      │            ▼                ▼         │
        │      │         (Failed)        Archived      │
        │      │            │                          │
        │      └────────────┘                          │
        │                                              │
        └──────────────────────────────────────────────┘

None:       Just trained, not yet evaluated
Staging:    Passed evaluation, awaiting deployment
Production: Currently serving traffic
Archived:   Previously in production, kept for rollback
```

### Why Keep Archived Models?

1. **Instant Rollback**: Switch back to v3 in seconds
2. **Comparison**: Compare new models against any previous version
3. **Debugging**: Reproduce issues from specific model version
4. **Audit Trail**: Track what was in production when

---

## 8. End-to-End Flow Example

### Scenario: Data Scientist Pushes Code Change

**Day 1, 9:00 AM**: Developer pushes improvement to `src/train.py`

```
git push origin main
```

**9:01 AM**: GitHub detects push, triggers `train.yml`

```
┌─────────────────────────────────────────┐
│ 🔄 Training Pipeline Started            │
│                                         │
│ ✅ Checkout code                        │
│ ✅ Setup Python 3.11                    │
│ ✅ Install dependencies                 │
│ ✅ Azure login                          │
│ 🔄 Running training...                  │
└─────────────────────────────────────────┘
```

**9:15 AM**: Training completes

```
┌─────────────────────────────────────────┐
│ 📊 Training Results                     │
│                                         │
│ Run ID: abc123                          │
│ Accuracy: 0.93                          │
│ F1 Score: 0.91                          │
│ Latency P95: 48ms                       │
│                                         │
│ ✅ Accuracy 0.93 ≥ 0.85 (threshold)     │
│ → Proceeding to registration            │
└─────────────────────────────────────────┘
```

**9:16 AM**: Model registered, evaluation triggered

```
┌─────────────────────────────────────────┐
│ 🔄 Evaluation Pipeline Started          │
│                                         │
│ Loading champion model (v3, acc=0.91)   │
│ Loading challenger model (acc=0.93)     │
│ Running evaluation on test set...       │
└─────────────────────────────────────────┘
```

**9:20 AM**: Evaluation completes

```
┌─────────────────────────────────────────┐
│ 🔒 QUALITY GATE REPORT                  │
│                                         │
│ ✅ Minimum accuracy: 93% ≥ 85%          │
│ ✅ Accuracy drop: +2% (improved!)       │
│ ✅ Latency P95: 48ms ≤ 100ms            │
│                                         │
│ ✅ QUALITY GATE: PASSED                 │
│                                         │
│ Model v4 approved for deployment        │
└─────────────────────────────────────────┘
```

**9:21 AM**: Slack notification sent to team

```
🎉 Model stihl-sales-model v4 passed evaluation!
   Accuracy: 93% (+2% vs production)
   Ready for deployment: [Approve] [View Details]
```

**10:00 AM**: ML Engineer reviews and approves deployment

```
┌─────────────────────────────────────────┐
│ 🚀 Deployment Pipeline Started          │
│                                         │
│ ✅ Deploy to staging                    │
│ ✅ Smoke tests passed                   │
│ ⏸️  Waiting for production approval...  │
└─────────────────────────────────────────┘
```

**10:05 AM**: Production deployment approved

```
┌─────────────────────────────────────────┐
│ 🚀 Production Deployment                │
│                                         │
│ ✅ Deploying to production (blue-green) │
│ ✅ Traffic: 10% to new model            │
│ ⏳ Monitoring for 60 seconds...         │
│ ✅ Health check passed                  │
│ ✅ Traffic: 50% to new model            │
│ ⏳ Monitoring for 60 seconds...         │
│ ✅ Health check passed                  │
│ ✅ Traffic: 100% to new model           │
│                                         │
│ 🎉 Deployment complete!                 │
│    Model v4 now serving all traffic     │
│    Model v3 archived (available for     │
│    rollback)                            │
└─────────────────────────────────────────┘
```

**10:10 AM**: Production serving new model

---

## 9. Key Concepts Summary

### Vocabulary to Remember

| Term | Definition |
|------|------------|
| **Champion** | Current production model |
| **Challenger** | New model being evaluated |
| **Quality Gate** | Checkpoint that blocks bad models |
| **Blue-Green** | Deployment with instant rollback |
| **MLflow Run** | Single training execution with metrics |
| **MLflow Experiment** | Collection of related runs |
| **Model Registry** | Versioned storage of model artifacts |
| **Stage** | Model lifecycle state (None/Staging/Production/Archived) |

### The Three Questions Every Gate Answers

1. **Absolute**: "Is this model good enough on its own?"
2. **Relative**: "Is this model better than what we have?"
3. **Operational**: "Can this model run in production?" (latency, size)

### Pipeline Philosophy

```
"Make deployment BORING by making it AUTOMATED and SAFE."
```

- **Automated**: No manual steps that can be forgotten
- **Safe**: Multiple gates, gradual rollout, instant rollback
- **Observable**: Every step logged, metrics tracked
- **Reproducible**: Any model version can be recreated

### Interview Soundbite

> "Our ML CI/CD pipeline has three stages: train, evaluate, deploy. Training is triggered by code changes or schedule. Evaluation compares the challenger against the current champion using quality gates—we check absolute thresholds AND relative performance. If gates pass, we deploy to staging for smoke tests, then production with gradual traffic rollout and one-click rollback. The whole philosophy is: make deployments boring by making them safe and automated."

---

## Quick Reference Card

```
┌────────────────────────────────────────────────────────────┐
│                    ML CI/CD CHEAT SHEET                    │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  TRIGGERS                                                  │
│  • Code push to main                                       │
│  • Scheduled (cron)                                        │
│  • Manual dispatch                                         │
│  • Data drift detected                                     │
│                                                            │
│  QUALITY GATES                                             │
│  • Min accuracy ≥ 85%          (blocker)                   │
│  • Accuracy drop ≤ 1%          (blocker)                   │
│  • Latency P95 ≤ 100ms         (blocker)                   │
│  • Model size ≤ 500MB          (warning)                   │
│                                                            │
│  MODEL STAGES                                              │
│  None → Staging → Production → Archived                    │
│                                                            │
│  DEPLOYMENT                                                │
│  Staging → Smoke Tests → Manual Approval → Production      │
│  Traffic: 10% → 50% → 100% (with monitoring)              │
│                                                            │
│  ROLLBACK                                                  │
│  One command: promote previous version back                │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

*This guide prepared for AI Architect Portfolio - Month 3*
