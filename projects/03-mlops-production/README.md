# MLOps & Production

Production-grade ML operations covering the full lifecycle from training to deployment and monitoring.

## Projects

| Project | Description | Key Technologies |
|---------|-------------|------------------|
| [Project 1: CI/CD Pipeline](./project1-cicd-pipeline/) | Automated ML training and deployment | GitHub Actions, MLflow, Azure ML |
| [Project 2: Model Monitoring](./project2-model-monitoring/) | Observability and drift detection | Prometheus, Grafana, Evidently |
| [Project 3: A/B Testing](./project3-ab-testing/) | Experimentation framework | Feature flags, statistical analysis |
| [Project 4: K8s Deployment](./project4-k8s-deployment/) | Kubernetes ML deployment | Docker, Helm, AKS |

## MLOps Maturity Model

```
Level 0: Manual          → Scripts, notebooks, manual deployment
Level 1: ML Pipeline     → Automated training, manual deployment
Level 2: CI/CD Pipeline  → Automated training AND deployment  ← WE BUILD THIS
Level 3: Full MLOps      → Continuous training, monitoring, retraining
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MLOps Pipeline                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐         │
│   │  Source  │───►│  Train   │───►│ Evaluate │───►│  Deploy  │         │
│   │  Control │    │          │    │  & Gate  │    │          │         │
│   └──────────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘         │
│        │               │               │               │                │
│        ▼               ▼               ▼               ▼                │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐         │
│   │  GitHub  │    │  MLflow  │    │  Test    │    │ Azure ML │         │
│   │          │    │ Tracking │    │  Suite   │    │ Endpoint │         │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘         │
│                                                                          │
│   ┌──────────────────────────────────────────────────────────┐         │
│   │                    Monitoring Layer                       │         │
│   │  • Model Performance  • Data Drift  • System Metrics     │         │
│   └──────────────────────────────────────────────────────────┘         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Interview Value

These projects demonstrate:

1. **CI/CD Pipeline**: "How do you automate ML deployments?"
2. **Monitoring**: "How do you detect model degradation in production?"
3. **A/B Testing**: "How do you safely roll out new models?"
4. **Kubernetes**: "How do you scale ML inference?"

---

*Month 3 - AI Architect Portfolio*
