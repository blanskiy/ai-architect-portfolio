# Project 4: Kubernetes Deployment for ML

Containerize and deploy ML models to Kubernetes with production-grade configurations.

## Overview

| Aspect | Details |
|--------|---------|
| **Purpose** | Deploy ML models at scale with high availability |
| **Key Components** | Docker, Kubernetes, Helm, AKS |
| **Features** | Auto-scaling, health checks, rolling updates, resource management |

## Why Kubernetes for ML?

### The Problem with Traditional Deployment

```
Traditional VM Deployment:          Kubernetes:
──────────────────────────          ─────────────────────────
Manual scaling                      Auto-scaling based on load
Single point of failure            Self-healing, replicas
Slow deployments                   Rolling updates, zero downtime
Resource waste                     Efficient bin-packing
Environment drift                  Immutable containers
```

### What Kubernetes Gives You

1. **Scalability**: Scale from 1 to 100 replicas automatically
2. **Reliability**: Self-healing, automatic restarts
3. **Zero-downtime deployments**: Rolling updates
4. **Resource efficiency**: Pack multiple services per node
5. **Portability**: Same deployment works anywhere

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        KUBERNETES CLUSTER (AKS)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         INGRESS CONTROLLER                           │  │
│   │                    (Load Balancer / API Gateway)                     │  │
│   └────────────────────────────────┬────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                           SERVICE                                    │  │
│   │                    (ClusterIP / LoadBalancer)                        │  │
│   └────────────────────────────────┬────────────────────────────────────┘  │
│                                    │                                        │
│              ┌─────────────────────┼─────────────────────┐                 │
│              │                     │                     │                 │
│              ▼                     ▼                     ▼                 │
│   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐       │
│   │      POD 1       │  │      POD 2       │  │      POD 3       │       │
│   │                  │  │                  │  │                  │       │
│   │  ┌────────────┐  │  │  ┌────────────┐  │  │  ┌────────────┐  │       │
│   │  │  ML Model  │  │  │  │  ML Model  │  │  │  │  ML Model  │  │       │
│   │  │ Container  │  │  │  │ Container  │  │  │  │ Container  │  │       │
│   │  └────────────┘  │  │  └────────────┘  │  │  └────────────┘  │       │
│   │                  │  │                  │  │                  │       │
│   │  CPU: 500m       │  │  CPU: 500m       │  │  CPU: 500m       │       │
│   │  Memory: 1Gi     │  │  Memory: 1Gi     │  │  Memory: 1Gi     │       │
│   └──────────────────┘  └──────────────────┘  └──────────────────┘       │
│              ▲                     ▲                     ▲                 │
│              │                     │                     │                 │
│              └─────────────────────┴─────────────────────┘                 │
│                                    │                                        │
│                     ┌──────────────┴──────────────┐                        │
│                     │  HORIZONTAL POD AUTOSCALER  │                        │
│                     │  Scale: 3-10 replicas       │                        │
│                     │  Target: 70% CPU            │                        │
│                     └─────────────────────────────┘                        │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                        CONFIGMAP / SECRETS                          │  │
│   │              (Model configs, API keys, credentials)                 │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
project4-k8s-deployment/
├── README.md
├── INTERVIEW_PREP.md
├── docker/
│   ├── Dockerfile                  # Multi-stage build for ML model
│   ├── Dockerfile.gpu              # GPU-enabled variant
│   └── .dockerignore
├── app/
│   ├── main.py                     # FastAPI inference server
│   ├── model.py                    # Model loading and prediction
│   └── requirements.txt
├── kubernetes/
│   ├── namespace.yaml              # Namespace isolation
│   ├── deployment.yaml             # Pod deployment config
│   ├── service.yaml                # Service exposure
│   ├── hpa.yaml                    # Horizontal Pod Autoscaler
│   ├── configmap.yaml              # Configuration
│   ├── secret.yaml                 # Sensitive data
│   ├── pdb.yaml                    # Pod Disruption Budget
│   └── ingress.yaml                # External access
├── helm/
│   └── ml-model/
│       ├── Chart.yaml
│       ├── values.yaml
│       ├── values-staging.yaml
│       ├── values-production.yaml
│       └── templates/
│           ├── deployment.yaml
│           ├── service.yaml
│           ├── hpa.yaml
│           ├── configmap.yaml
│           └── _helpers.tpl
└── scripts/
    ├── build.sh                    # Build Docker image
    ├── deploy.sh                   # Deploy to K8s
    └── rollback.sh                 # Rollback deployment
```

## Key Concepts

### 1. Health Probes

```yaml
livenessProbe:     # "Is the container alive?"
  httpGet:         # If fails → restart container
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:    # "Is the container ready for traffic?"
  httpGet:         # If fails → remove from load balancer
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

**Why both?**
- **Liveness**: Detects deadlocks, restarts stuck containers
- **Readiness**: Waits for model to load before sending traffic

### 2. Resource Management

```yaml
resources:
  requests:        # Minimum guaranteed
    cpu: "500m"    # 0.5 CPU cores
    memory: "1Gi"  # 1 GB RAM
  limits:          # Maximum allowed
    cpu: "2"       # 2 CPU cores
    memory: "4Gi"  # 4 GB RAM
```

**Why set both?**
- **Requests**: Scheduler uses this to place pods
- **Limits**: Prevents runaway containers from killing nodes

### 3. Horizontal Pod Autoscaler (HPA)

```yaml
spec:
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      targetAverageUtilization: 70
```

**How it works**:
- CPU > 70% → scale up
- CPU < 70% → scale down (after cooldown)
- Never go below 3 or above 10 replicas

### 4. Rolling Updates

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1        # Can add 1 extra pod during update
    maxUnavailable: 0  # Never have less than desired
```

**Zero-downtime deployment**:
1. Start new pod
2. Wait until ready
3. Shift traffic
4. Terminate old pod
5. Repeat

## Quick Start

### 1. Build Docker Image
```bash
cd docker
docker build -t ml-model:v1 .
docker tag ml-model:v1 myregistry.azurecr.io/ml-model:v1
docker push myregistry.azurecr.io/ml-model:v1
```

### 2. Deploy to Kubernetes
```bash
# Using raw manifests
kubectl apply -f kubernetes/

# Using Helm
helm install ml-model ./helm/ml-model \
  --namespace ml-production \
  --values helm/ml-model/values-production.yaml
```

### 3. Verify Deployment
```bash
kubectl get pods -n ml-production
kubectl get hpa -n ml-production
kubectl logs -f deployment/ml-model -n ml-production
```

### 4. Rollback if Needed
```bash
kubectl rollout undo deployment/ml-model -n ml-production
# Or with Helm
helm rollback ml-model 1 -n ml-production
```

## Interview Talking Points

### Q: "How do you deploy ML models to production?"

> "I containerize models with Docker using multi-stage builds for small images, then deploy to Kubernetes. The deployment includes health probes (liveness and readiness), resource limits, and HPA for auto-scaling. I use Helm for templated deployments across environments. Rolling updates ensure zero downtime."

### Q: "How do you handle model loading time?"

> "I use a readiness probe that only returns healthy after the model is loaded. Kubernetes won't send traffic until ready. I also set `initialDelaySeconds` to give the model time to load, and use preStop hooks to drain connections gracefully during shutdown."

### Q: "How do you scale ML inference?"

> "Horizontal Pod Autoscaler scales based on CPU/memory utilization. For ML-specific scaling, I can use custom metrics like request queue depth or inference latency via Prometheus Adapter. I set min replicas for baseline capacity and max to control costs."

---

*Project 4 - MLOps & Production*
