# CI/CD for ML - Interview Cheat Sheet

## Quick Framework (30-second answer)

> "I implement a three-stage CI/CD pipeline: **Train → Evaluate → Deploy**. Training is triggered by code changes or schedule, producing a challenger model tracked in MLflow. The evaluation stage compares challenger vs champion using **quality gates**—if accuracy drops more than 1% or latency exceeds thresholds, deployment is blocked. Approved models deploy to staging first, then production with **blue-green rollout** and manual approval."

---

## Key Components to Mention

| Stage | What Happens | Tools |
|-------|--------------|-------|
| **Train** | Model training, metric logging | GitHub Actions, MLflow |
| **Evaluate** | Champion vs Challenger comparison | pytest, custom gates |
| **Deploy** | Staged rollout with traffic shifting | Azure ML, Kubernetes |

---

## Quality Gates (Memorize These)

| Gate | Threshold | Action |
|------|-----------|--------|
| Min Accuracy | ≥ 85% | Block if below |
| Accuracy Drop | ≤ 1% vs champion | Block if exceeds |
| Latency P95 | ≤ 100ms | Block if exceeds |
| Model Size | ≤ 500MB | Warning only |

---

## Common Interview Questions

### Q: "How do you automate ML deployments?"

> "Three-stage pipeline with quality gates. Training produces artifacts tracked in MLflow. Evaluation compares new model against production using held-out test set. If gates pass, we deploy to staging for smoke tests, then production with gradual traffic rollout. Key difference from software CI/CD: we gate on **model quality metrics**, not just tests passing."

### Q: "What's different about ML CI/CD vs software CI/CD?"

> "Three key differences:
> 1. **Data changes matter** - need to retrain when data drifts, not just code
> 2. **Quality gates are statistical** - accuracy thresholds, not boolean tests
> 3. **Rollback is model-level** - swap model versions, not code versions
> 4. **Champion/Challenger pattern** - always compare against production baseline"

### Q: "How do you handle model versioning?"

> "MLflow Model Registry with three stages: None (just trained), Staging (under test), Production (serving). Each version captures metrics, parameters, and data lineage. Promotion is explicit - must pass evaluation to move from Staging to Production. Previous production versions are archived, not deleted."

### Q: "What triggers retraining?"

> "Four triggers:
> 1. **Scheduled** - weekly/monthly baseline
> 2. **Code change** - push to main branch
> 3. **Data drift** - monitoring detects distribution shift
> 4. **Manual** - emergency or ad-hoc"

### Q: "How do you ensure safe deployments?"

> "Multiple layers:
> 1. **Quality gates** block bad models before staging
> 2. **Smoke tests** validate in staging environment
> 3. **Blue-green deployment** - new version gets 0% traffic initially
> 4. **Gradual rollout** - 10% → 50% → 100% with monitoring
> 5. **One-click rollback** - revert to previous version in seconds"

### Q: "How do you handle model rollback?"

> "Two mechanisms:
> 1. **Automatic** - if metrics degrade during rollout, traffic shifts back
> 2. **Manual** - single command to promote previous version back to production
> 
> Both are fast because we keep previous deployments warm (blue-green pattern)."

---

## Architecture Diagram to Draw

```
Code Push
    │
    ▼
┌─────────┐     ┌─────────────┐     ┌─────────────┐
│  Train  │────►│  Evaluate   │────►│   Deploy    │
│         │     │ (Quality    │     │ (Blue-Green)│
│ MLflow  │     │   Gates)    │     │             │
└─────────┘     └─────────────┘     └─────────────┘
    │                 │                    │
    ▼                 ▼                    ▼
 Model            Pass/Fail           Staging→Prod
 Registry          Report              Rollout
```

---

## Red Flags to Avoid

❌ "We deploy models manually after training"
❌ "We don't compare against the current production model"
❌ "Rollback requires retraining"
❌ "We deploy directly to production"

✅ "Automated pipeline with quality gates"
✅ "Champion vs challenger evaluation"
✅ "Instant rollback to previous version"
✅ "Staged deployment with gradual traffic"

---

## Metrics to Track (Production)

| Metric | Purpose |
|--------|---------|
| Prediction latency (P50, P95) | User experience |
| Prediction throughput | Capacity planning |
| Model accuracy (online) | Quality monitoring |
| Feature drift | Data distribution changes |
| Prediction drift | Output distribution changes |

---

## Cost Considerations

| Approach | Pros | Cons |
|----------|------|------|
| **GitHub Actions** | Free for public repos, simple | Limited compute for training |
| **Azure ML Pipelines** | Managed, scalable | ~$0.10/pipeline-hour |
| **Self-hosted runners** | Full control | Ops overhead |

"For most projects, GitHub Actions for orchestration + Azure ML for compute gives best balance of cost and capability."
