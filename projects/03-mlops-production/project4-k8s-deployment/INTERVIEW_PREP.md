# Kubernetes for ML - Interview Cheat Sheet

## Quick Framework (30-second answer)

> "I containerize ML models with multi-stage Docker builds, then deploy to Kubernetes with production-grade configs: **liveness/readiness probes** for health, **HPA** for auto-scaling based on CPU/memory, **resource limits** to prevent runaway containers, and **rolling updates** for zero-downtime deployments. I use Helm for templated deployments across environments."

---

## Docker Best Practices

### Multi-Stage Build

```dockerfile
# Stage 1: Build (large, with dev tools)
FROM python:3.11 as builder
RUN pip install -r requirements.txt

# Stage 2: Production (small, runtime only)
FROM python:3.11-slim as production
COPY --from=builder /opt/venv /opt/venv
```

**Why multi-stage?**
- Smaller images (100MB vs 2GB)
- No build tools in production
- Faster pulls and deploys

### Security Checklist

| Practice | Why |
|----------|-----|
| Run as non-root | Limit container compromise impact |
| Read-only filesystem | Prevent runtime modifications |
| Drop all capabilities | Minimize kernel access |
| Specific base image | Avoid `:latest` for reproducibility |

---

## Health Probes (Memorize!)

### Three Types

| Probe | Question | If Fails |
|-------|----------|----------|
| **Liveness** | "Is container alive?" | Restart container |
| **Readiness** | "Can it handle traffic?" | Remove from load balancer |
| **Startup** | "Has it started yet?" | Delay other probes |

### For ML Models

```yaml
# Model loading can take 30-60 seconds
startupProbe:
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 30  # 30 × 5s = 150s max

# After startup, check every 10s
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  periodSeconds: 10

# Remove from LB if model fails
readinessProbe:
  httpGet:
    path: /ready  # Checks model is loaded
    port: 8080
  periodSeconds: 5
```

---

## Resource Management

### Requests vs Limits

```yaml
resources:
  requests:      # Guaranteed minimum
    cpu: "500m"  # 0.5 cores
    memory: "1Gi"
  limits:        # Maximum allowed
    cpu: "2"     # 2 cores
    memory: "4Gi"
```

| Setting | Purpose |
|---------|---------|
| **Requests** | Scheduler uses to place pods |
| **Limits** | Prevents runaway containers |

### CPU Units

| Value | Meaning |
|-------|---------|
| `1` | 1 full CPU core |
| `500m` | 0.5 cores (millicores) |
| `100m` | 0.1 cores |

### Memory Exceeded?

- **Over limit**: Container is OOM-killed
- **Node full**: Pod evicted (lowest priority first)

---

## Horizontal Pod Autoscaler

### Basic Config

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### How It Works

```
Current CPU > 70% → Scale UP
Current CPU < 70% → Scale DOWN (after cooldown)
```

### Scaling Formula

```
desiredReplicas = ceil(currentReplicas × (currentMetric / targetMetric))

Example:
- 3 pods at 90% CPU, target 70%
- desiredReplicas = ceil(3 × 90/70) = ceil(3.86) = 4 pods
```

---

## Rolling Updates

### Strategy

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1        # Can have 1 extra pod
    maxUnavailable: 0  # Never have fewer pods
```

### Zero-Downtime Flow

```
1. Create new pod (v2)
2. Wait for readiness probe ✓
3. Add to load balancer
4. Remove old pod (v1) from LB
5. Terminate old pod
6. Repeat until all updated
```

---

## Common Interview Questions

### Q: "How do you deploy ML models to production?"

> "I use Docker with multi-stage builds for small images, deploy to Kubernetes with Deployment resources. Key configs: readiness probe that checks model is loaded, resource limits to prevent OOM, HPA for auto-scaling. I use Helm for environment-specific deployments (staging/production)."

### Q: "What's the difference between liveness and readiness probes?"

> "Liveness asks 'is the container alive?' - if it fails, K8s restarts the container. Readiness asks 'can it handle traffic?' - if it fails, K8s removes it from the load balancer but doesn't restart. For ML, readiness is critical because model loading takes time - we don't want traffic until the model is ready."

### Q: "How do you handle model loading time?"

> "I use a startup probe with a high failure threshold (e.g., 30 failures × 5 seconds = 150 second window). The readiness probe endpoint checks if the model is actually loaded in memory. Until readiness passes, Kubernetes won't send traffic. I also use preStop hooks to drain connections before shutdown."

### Q: "How do you scale ML inference?"

> "HPA scales based on CPU or memory. For ML-specific scaling, I use custom metrics via Prometheus Adapter - like request queue depth or P95 latency. For GPU workloads, I scale on nvidia.com/gpu utilization. I set conservative scale-down policies (5 minute cooldown) to avoid thrashing."

### Q: "How do you ensure high availability?"

> "Three layers: (1) Multiple replicas with Pod Anti-Affinity to spread across nodes, (2) Pod Disruption Budget to prevent too many pods going down during maintenance, (3) Multi-zone deployment with topology spread constraints. I also use preStop hooks for graceful shutdown."

### Q: "How do you handle configuration across environments?"

> "Helm with environment-specific values files: values-staging.yaml, values-production.yaml. Sensitive data in Kubernetes Secrets (or external secret stores like Azure Key Vault). ConfigMaps for non-sensitive config. The deployment template references these, so same chart works everywhere."

---

## Architecture to Draw

```
┌─────────────────────────────────────────────────────┐
│                  KUBERNETES CLUSTER                  │
├─────────────────────────────────────────────────────┤
│                                                      │
│   INGRESS                                            │
│   ┌─────────────────────────────────────────────┐   │
│   │  TLS termination, rate limiting, routing    │   │
│   └─────────────────────┬───────────────────────┘   │
│                         │                           │
│   SERVICE               ▼                           │
│   ┌─────────────────────────────────────────────┐   │
│   │  Load balancing across pods                 │   │
│   └─────────────────────┬───────────────────────┘   │
│                         │                           │
│        ┌────────────────┼────────────────┐         │
│        │                │                │         │
│        ▼                ▼                ▼         │
│   ┌─────────┐      ┌─────────┐      ┌─────────┐   │
│   │  POD 1  │      │  POD 2  │      │  POD 3  │   │
│   │         │      │         │      │         │   │
│   │ Model   │      │ Model   │      │ Model   │   │
│   │ v1.0.0  │      │ v1.0.0  │      │ v1.0.0  │   │
│   └─────────┘      └─────────┘      └─────────┘   │
│        │                │                │         │
│        └────────────────┴────────────────┘         │
│                         │                           │
│   HPA ──────────────────┴───────────────────────   │
│   Scale 3-10 based on CPU (target 70%)             │
│                                                      │
│   CONFIGMAP          SECRETS           PVC          │
│   ┌─────────┐      ┌─────────┐      ┌─────────┐   │
│   │ Config  │      │ Creds   │      │ Models  │   │
│   └─────────┘      └─────────┘      └─────────┘   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## Key Commands

```bash
# Deploy
kubectl apply -f kubernetes/
helm install ml-model ./helm/ml-model -f values-production.yaml

# Check status
kubectl get pods -n ml-production
kubectl get hpa -n ml-production
kubectl describe pod <pod-name>

# Logs
kubectl logs -f deployment/ml-model
kubectl logs <pod-name> --previous  # Crashed container logs

# Scale manually
kubectl scale deployment/ml-model --replicas=5

# Rollback
kubectl rollout undo deployment/ml-model
helm rollback ml-model 1
```

---

## Numbers to Remember

| Resource | Typical ML Value |
|----------|------------------|
| CPU request | 500m - 1 core |
| CPU limit | 2-4 cores |
| Memory request | 1-2 Gi |
| Memory limit | 4-8 Gi |
| Min replicas | 3 (HA) |
| Max replicas | 10-20 |
| HPA CPU target | 70% |
| Startup timeout | 2-5 minutes |
