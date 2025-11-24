# 🚢 Deployment Guide

Complete guide for deploying the high-throughput ML serving system to various environments.

---

## 📋 **Deployment Options**

| Platform | Best For | Complexity | Cost |
|----------|----------|------------|------|
| **Docker Compose** | Development, small deployments | Low | $ |
| **AWS ECS** | Production, AWS ecosystem | Medium | $$ |
| **Azure Container Instances** | Quick cloud deployment | Low | $$ |
| **Google Cloud Run** | Serverless, auto-scaling | Low | $$$ |
| **Kubernetes** | Large scale, multi-cloud | High | $$$ |

---

## 🐳 **Docker Compose (Local/Development)**

### **Quick Start**

```bash
# Clone repository
git clone <repository-url>
cd high-throughput-serving

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### **docker-compose.yml**

```yaml
version: '3.8'

services:
  # Redis cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
    restart: unless-stopped

  # ML API
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - LOG_LEVEL=INFO
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: unless-stopped

  # Prometheus (metrics)
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    restart: unless-stopped

  # Grafana (dashboards)
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  redis-data:
  prometheus-data:
  grafana-data:
```

### **Production Configuration**

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    build: .
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    environment:
      - REDIS_HOST=redis
      - LOG_LEVEL=INFO
      - JSON_LOGS=true
```

---

## ☁️ **AWS ECS Deployment**

### **Prerequisites**

```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure
```

### **Step 1: Push Image to ECR**

```bash
# Create ECR repository
aws ecr create-repository --repository-name ml-serving

# Get login credentials
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and tag
docker build -t ml-serving:latest .
docker tag ml-serving:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/ml-serving:latest

# Push
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/ml-serving:latest
```

### **Step 2: Create Task Definition**

```json
{
  "family": "ml-serving-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/ml-serving:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "REDIS_HOST", "value": "redis.xxxxx.cache.amazonaws.com"},
        {"name": "LOG_LEVEL", "value": "INFO"}
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      },
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ml-serving",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "api"
        }
      }
    }
  ]
}
```

### **Step 3: Create ECS Service**

```bash
# Create cluster
aws ecs create-cluster --cluster-name ml-serving-cluster

# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create service
aws ecs create-service \
  --cluster ml-serving-cluster \
  --service-name ml-api \
  --task-definition ml-serving-task \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxx],securityGroups=[sg-xxxxx],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=api,containerPort=8000"
```

### **Step 4: Setup ElastiCache Redis**

```bash
# Create Redis cluster
aws elasticache create-replication-group \
  --replication-group-id ml-cache \
  --replication-group-description "ML API Cache" \
  --engine redis \
  --cache-node-type cache.t3.micro \
  --num-cache-clusters 2 \
  --automatic-failover-enabled
```

### **Step 5: Configure Auto-scaling**

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/ml-serving-cluster/ml-api \
  --min-capacity 2 \
  --max-capacity 10

# Create scaling policy
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/ml-serving-cluster/ml-api \
  --policy-name cpu-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

---

## 🔷 **Azure Container Instances**

### **Step 1: Push to Azure Container Registry**

```bash
# Create resource group
az group create --name ml-serving-rg --location eastus

# Create container registry
az acr create --resource-group ml-serving-rg \
  --name mlservingacr --sku Basic

# Login to registry
az acr login --name mlservingacr

# Build and push
docker build -t mlservingacr.azurecr.io/ml-api:latest .
docker push mlservingacr.azurecr.io/ml-api:latest
```

### **Step 2: Deploy Container**

```bash
# Create container instance
az container create \
  --resource-group ml-serving-rg \
  --name ml-api \
  --image mlservingacr.azurecr.io/ml-api:latest \
  --cpu 2 \
  --memory 4 \
  --registry-login-server mlservingacr.azurecr.io \
  --registry-username <username> \
  --registry-password <password> \
  --dns-name-label ml-api-unique \
  --ports 8000 \
  --environment-variables \
    REDIS_HOST=ml-redis.redis.cache.windows.net \
    LOG_LEVEL=INFO
```

### **Step 3: Setup Azure Cache for Redis**

```bash
# Create Redis cache
az redis create \
  --name ml-redis \
  --resource-group ml-serving-rg \
  --location eastus \
  --sku Basic \
  --vm-size C1

# Get connection string
az redis list-keys --name ml-redis --resource-group ml-serving-rg
```

---

## ☸️ **Kubernetes Deployment**

### **deployment.yaml**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ml-api
  template:
    metadata:
      labels:
        app: ml-api
    spec:
      containers:
      - name: api
        image: <registry>/ml-serving:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_HOST
          value: redis-service
        - name: LOG_LEVEL
          value: INFO
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10

---
apiVersion: v1
kind: Service
metadata:
  name: ml-api-service
spec:
  selector:
    app: ml-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            memory: "1Gi"
            cpu: "0.5"

---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
spec:
  selector:
    app: redis
  ports:
  - protocol: TCP
    port: 6379
    targetPort: 6379
```

### **Auto-scaling**

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ml-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ml-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### **Deploy to Kubernetes**

```bash
# Apply configurations
kubectl apply -f deployment.yaml
kubectl apply -f hpa.yaml

# Check status
kubectl get pods
kubectl get services

# View logs
kubectl logs -f deployment/ml-api

# Scale manually
kubectl scale deployment ml-api --replicas=5
```

---

## 🌐 **Google Cloud Run**

### **Step 1: Build and Push**

```bash
# Set project
gcloud config set project <project-id>

# Build with Cloud Build
gcloud builds submit --tag gcr.io/<project-id>/ml-api

# Or use local Docker
docker build -t gcr.io/<project-id>/ml-api:latest .
docker push gcr.io/<project-id>/ml-api:latest
```

### **Step 2: Deploy**

```bash
# Deploy to Cloud Run
gcloud run deploy ml-api \
  --image gcr.io/<project-id>/ml-api:latest \
  --platform managed \
  --region us-central1 \
  --memory 4Gi \
  --cpu 2 \
  --timeout 60s \
  --concurrency 80 \
  --max-instances 10 \
  --min-instances 1 \
  --set-env-vars REDIS_HOST=10.x.x.x,LOG_LEVEL=INFO \
  --allow-unauthenticated
```

### **Step 3: Setup Memorystore (Redis)**

```bash
# Create Redis instance
gcloud redis instances create ml-cache \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_7_0

# Get IP address
gcloud redis instances describe ml-cache --region=us-central1
```

---

## 🔧 **Environment Configuration**

### **Environment Variables**

```bash
# API Configuration
PORT=8000
HOST=0.0.0.0
LOG_LEVEL=INFO
JSON_LOGS=true

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=<password>  # if needed
CACHE_TTL=3600
CACHE_ENABLED=true

# Batch Manager
MAX_BATCH_SIZE=8
MAX_WAIT_TIME=0.05

# Model Configuration
MODEL_NAME=resnet50
DEVICE=cpu  # or cuda

# Monitoring
ENABLE_PROMETHEUS=true
METRICS_PORT=9090
```

### **.env.example**

```bash
# Copy this to .env and fill in values
REDIS_HOST=localhost
REDIS_PASSWORD=
LOG_LEVEL=INFO
MAX_BATCH_SIZE=8
```

---

## 📊 **Monitoring Setup**

### **Prometheus Configuration**

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ml-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: /prometheus
```

### **Grafana Dashboards**

```bash
# Import dashboard
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @monitoring/grafana-dashboard.json
```

---

## 🔒 **Security Best Practices**

### **1. API Security**

```python
# Add API key authentication
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.post("/predict")
async def predict(
    file: UploadFile,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # Verify API key
    if credentials.credentials != os.getenv("API_KEY"):
        raise HTTPException(status_code=401)
    ...
```

### **2. Network Security**

```bash
# Docker network isolation
docker network create --driver bridge ml-network

# Run containers in isolated network
docker run --network ml-network redis
docker run --network ml-network api
```

### **3. Secrets Management**

```bash
# AWS Secrets Manager
aws secretsmanager create-secret \
  --name ml-api-redis-password \
  --secret-string "your-redis-password"

# Kubernetes secrets
kubectl create secret generic redis-password \
  --from-literal=password='your-redis-password'
```

---

## 📈 **Scaling Guidelines**

### **Vertical Scaling**

| Load | Instance Type | Cost/Month |
|------|---------------|------------|
| <2 RPS | t3.medium (2 CPU, 4GB) | $30 |
| 2-10 RPS | t3.large (2 CPU, 8GB) | $60 |
| 10-50 RPS | c5.xlarge (4 CPU, 8GB) | $122 |
| 50+ RPS | c5.2xlarge (8 CPU, 16GB) | $245 |

### **Horizontal Scaling**

```
Load → Instances
─────────────────
0-7 RPS → 1
7-35 RPS → 5
35-70 RPS → 10
70-350 RPS → 50
```

---

## 🚨 **Troubleshooting**

### **Container Won't Start**

```bash
# Check logs
docker logs <container-id>

# Common issues:
# 1. Port already in use
docker ps  # Check what's using port 8000

# 2. Redis connection failed
docker exec -it redis-cache redis-cli ping

# 3. Model download failed
# Ensure internet connectivity
```

### **High Latency**

```bash
# Check cache hit rate
curl http://localhost:8000/cache/stats

# If low hit rate:
# - Increase cache TTL
# - Check Redis memory

# Check queue depth
curl http://localhost:8000/metrics | grep queue_length

# If high queue depth:
# - Increase batch size
# - Add more instances
```

### **Out of Memory**

```bash
# Check container memory
docker stats

# Solutions:
# - Increase container memory limit
# - Reduce batch size
# - Clear Redis cache
```

---

## 📋 **Pre-deployment Checklist**

- [ ] Build and test Docker image locally
- [ ] Configure environment variables
- [ ] Setup Redis instance
- [ ] Configure monitoring (Prometheus/Grafana)
- [ ] Setup logging aggregation
- [ ] Configure auto-scaling
- [ ] Setup health checks
- [ ] Configure alerts
- [ ] Test with load testing
- [ ] Document rollback procedure

---

## 🔄 **CI/CD Pipeline**

### **GitHub Actions**

```yaml
# .github/workflows/deploy.yml
name: Deploy ML API

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build Docker image
        run: docker build -t ml-api:${{ github.sha }} .
      
      - name: Run tests
        run: |
          docker run ml-api:${{ github.sha}} pytest
      
      - name: Push to registry
        run: |
          docker tag ml-api:${{ github.sha }} <registry>/ml-api:latest
          docker push <registry>/ml-api:latest
      
      - name: Deploy to ECS
        run: |
          aws ecs update-service --cluster ml-cluster --service ml-api --force-new-deployment
```

---

<div align="center">

**Ready for production deployment**

[← Back to README](README.md)

</div>
